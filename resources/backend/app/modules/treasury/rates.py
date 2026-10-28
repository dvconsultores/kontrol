"""Spec 013 · maestros financieros — la autoridad de la tasa.

La Spec 038 dejó de inventar tasas y con eso destapó que **nadie las registra**.
Este módulo es la frontera: aquí se decide qué monedas existen, de qué fuentes
vienen las tasas, qué par expresa cada observación y cómo se resuelve una tasa
para un momento dado —incluida la respuesta «no la hay»—.

Lo que **no** se hace aquí: mover dinero, convertir cuentas ni guardar la
instantánea de una operación. Eso es de la 038, que consume `resolve_rate` y
congela el resultado. Tampoco se llama a ninguna web: el acceso externo es de
la 048.

Semántica canónica del par, escrita una sola vez y respetada en todas partes:

    **1 unidad de `base` = `rate` unidades de `quote`.**

Con `base = USD`, `quote = VES` y `rate = 100`, un dólar son cien bolívares.
Antes esto lo suponía el código, con `("VED", "VES")` cableado dentro del
dominio de un producto que se vende como parametrizable.
"""

from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.core.integrity import es_violacion_unica
from app.modules.organization.models import Company
from app.modules.treasury.models import (
    Currency,
    ExchangeRate,
    ExchangeRateImportBatch,
    ExchangeRatePolicy,
    ExchangeRateSource,
)
from app.shared.clock import hoy_de_negocio, zona_de_negocio

#: Escala por omisión de la tasa. Es lo que `Numeric(14, 6)` viene aplicando
#: desde siempre; queda como valor heredado **declarado**, y la política puede
#: cambiarlo. No es una decisión de este módulo: es lo que había.
_ESCALA_HEREDADA = 6


def _dec(valor: Any) -> Decimal:
    """Todo número entra como `Decimal`. Nunca por `float`."""
    if valor is None:
        return Decimal(0)
    return valor if isinstance(valor, Decimal) else Decimal(str(valor))


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED",
                           message=f"La empresa es obligatoria para {obj}.", status_code=422)
    return str(company_id)


def _momento(valor: date | datetime | None) -> datetime:
    """Un instante **siempre en UTC**.

    Una fecha suelta empieza a regir a las cero del día de negocio en Caracas.
    SQLite guarda la hora de pared y descarta el desfase; por eso el contrato
    del módulo normaliza a UTC todo instante que persiste, para que PostgreSQL
    y SQLite guarden lo mismo.

    - `None` → ahora en UTC.
    - `datetime` con zona → el mismo instante en UTC.
    - `datetime` sin zona → la API lo interpreta como UTC.
    - `date` → las 00:00 de Caracas de ese día, normalizado a UTC.
    """
    if valor is None:
        return datetime.now(UTC)
    if isinstance(valor, datetime):
        return valor.astimezone(UTC) if valor.tzinfo else valor.replace(tzinfo=UTC)
    # El día es el del calendario de negocio, no el de UTC: sus cero horas son las
    # cero de Caracas (POLICY-CLOCK-LOCAL). Interpretarlo en UTC dejaba la tasa de
    # hoy fuera del día de hoy durante las cuatro horas de diferencia.
    return datetime(valor.year, valor.month, valor.day,
                    tzinfo=zona_de_negocio()).astimezone(UTC)


def _momento_consulta(valor: date | datetime | None) -> datetime:
    """El instante **siempre en UTC** hasta el que mirar cuando se pregunta por un día.

    Preguntar «qué tasa rige el día D» no es preguntar «qué regía a las cero de
    D»: la del día se publica a media mañana. Si la consulta se quedara en el
    comienzo del día, una tasa registrada hoy no serviría para una operación de
    hoy —que es exactamente lo que pasaba— y el sistema diría que falta una
    tasa que está delante.

    Una fecha se mira hasta el final de su día en Caracas; un instante concreto,
    tal cual. SQLite guarda la hora de pared y descarta el desfase; por eso todo
    resultado se normaliza a UTC.
    """
    if valor is None:
        return datetime.now(UTC)
    if isinstance(valor, datetime):
        return valor.astimezone(UTC) if valor.tzinfo else valor.replace(tzinfo=UTC)
    return datetime(valor.year, valor.month, valor.day, 23, 59, 59, 999999,
                    tzinfo=zona_de_negocio()).astimezone(UTC)


# --------------------------------------------------------------------------- #
# Monedas
# --------------------------------------------------------------------------- #
def moneda_por_codigo(db: Session, company_id: str, codigo: str) -> Currency | None:
    """La moneda **activa** de ese código.

    Se ordena por antigüedad a propósito. Antes esto era un `.first()` sin
    orden sobre una tabla sin unicidad: con dos «USD» en la misma empresa, la
    resolución elegía una al azar y las tasas de la otra quedaban invisibles.
    La unicidad la garantiza ahora el índice; el orden es el cinturón.
    """
    return db.execute(
        select(Currency).where(
            Currency.company_id == company_id,
            Currency.code == codigo,
            Currency.status == "ACTIVE")
        .order_by(Currency.created_at, Currency.id)).scalars().first()


def _exigir_moneda(db: Session, company_id: str, codigo: str) -> Currency:
    cur = moneda_por_codigo(db, company_id, codigo)
    if cur is None:
        raise ConflictError(code="CURRENCY_INACTIVE",
                            message=f"La moneda {codigo} no existe o no está activa.",
                            details={"currency": codigo})
    return cur


def moneda_funcional(db: Session, company_id: str) -> str:
    """La que la **empresa declara**, no la que suponga el código."""
    empresa = db.get(Company, str(company_id))
    if empresa is None or not empresa.functional_currency:
        raise ConflictError(code="FUNCTIONAL_CURRENCY_UNDEFINED",
                            message="La empresa no declara moneda funcional.")
    return empresa.functional_currency


def asegurar_moneda_funcional(db: Session, company_id: str,
                              actor: str | None = None) -> Currency:
    """La fila de maestro de la moneda que la empresa declara.

    Si no existe, se crea. No es información nueva: la empresa **ya declaró**
    su moneda funcional en `companies.functional_currency`, y sin una fila de
    maestro el par no es expresable —«1 USD = 100 ???»—. Es la misma decisión
    que tomó la migración `0056` para las filas que ya existían.

    Solo la usa el camino corto de compatibilidad. Cuando alguien nombra las dos
    monedas de forma explícita, las dos tienen que existir: ahí no se inventa
    nada.
    """
    codigo = moneda_funcional(db, company_id)
    ya = moneda_por_codigo(db, company_id, codigo)
    if ya is not None:
        return ya
    # Buscar y crear no es atómico. Dos registros simultáneos en una empresa
    # nueva pasan ambos la búsqueda: decide el índice único parcial de monedas
    # activas, y quien pierde relee la que creó el otro en vez de devolver un 500.
    try:
        with db.begin_nested():
            db.add(Currency(company_id=str(company_id), code=codigo, name=codigo,
                            decimal_places=2, status="ACTIVE",
                            created_by=actor or "spec013:functional"))
            db.flush()
    except IntegrityError as e:
        if not es_violacion_unica(e, "uq_currencies_company_code_active"):
            raise
    cur = moneda_por_codigo(db, company_id, codigo)
    if cur is None:  # pragma: no cover - imposible tras insertar o perder la carrera
        raise ConflictError(code="FUNCTIONAL_CURRENCY_UNAVAILABLE",
                            message="No fue posible obtener la moneda funcional.")
    return cur


# --------------------------------------------------------------------------- #
# Fuentes
# --------------------------------------------------------------------------- #
def create_source(db: Session, *, company_id: str, code: str, name: str,
                  source_type: str = "MANUAL", authority_reference: str | None = None,
                  provider_code: str | None = None, allows_manual: bool = True,
                  priority: int = 100, effective_from: date | None = None,
                  actor: str | None = None) -> ExchangeRateSource:
    company_id = _company(company_id, obj="fuente de tasa")
    repetida = db.execute(select(ExchangeRateSource).where(
        ExchangeRateSource.company_id == company_id,
        ExchangeRateSource.code == code)).scalars().first()
    if repetida is not None:
        raise ConflictError(code="SOURCE_CODE_TAKEN",
                            message=f"Ya existe una fuente con el código {code}.")
    fuente = ExchangeRateSource(
        company_id=company_id, code=code, name=name, source_type=source_type,
        authority_reference=authority_reference, provider_code=provider_code,
        allows_manual=allows_manual, priority=priority, effective_from=effective_from,
        status="ACTIVE", created_by=actor)
    # La comprobación de arriba y esta inserción no son atómicas: dos altas
    # simultáneas del mismo código pasan ambas. Decide el índice único, y quien
    # pierde recibe el mismo `SOURCE_CODE_TAKEN` que si hubiera llegado tarde.
    try:
        with db.begin_nested():
            db.add(fuente)
            db.flush()
    except IntegrityError as e:
        if not es_violacion_unica(e, "uq_rate_sources_company_code"):
            raise
        raise ConflictError(code="SOURCE_CODE_TAKEN",
                            message=f"Ya existe una fuente con el código {code}.") from None
    return fuente


def set_source_status(db: Session, *, company_id: str, source_id: str, status: str,
                      actor: str | None = None) -> ExchangeRateSource:
    """Desactivar una fuente no borra su historia: deja de producir tasas nuevas."""
    fuente = _exigir_fuente(db, company_id, source_id)
    if status not in ("ACTIVE", "DISABLED"):
        raise KontrolError(code="INVALID_SOURCE_STATUS",
                           message="Una fuente está activa o desactivada.", status_code=422)
    fuente.status = status
    fuente.updated_at = datetime.now(UTC)
    db.flush()
    return fuente


def _exigir_fuente(db: Session, company_id: str, source_id: str) -> ExchangeRateSource:
    fuente = db.get(ExchangeRateSource, str(source_id))
    if fuente is None or str(fuente.company_id) != str(company_id):
        raise NotFoundError(code="RATE_SOURCE_NOT_FOUND", message="Fuente de tasa no encontrada")
    return fuente


def fuente_por_codigo(db: Session, company_id: str, code: str) -> ExchangeRateSource | None:
    return db.execute(select(ExchangeRateSource).where(
        ExchangeRateSource.company_id == company_id,
        ExchangeRateSource.code == code)).scalars().first()


def fuente_por_texto(db: Session, company_id: str, texto: str | None,
                     actor: str | None = None) -> ExchangeRateSource:
    """La fuente que nombra ese texto libre, creándola si aún no está.

    Antes de la 013 la procedencia de una tasa era una cadena suelta en la fila.
    Esa cadena siempre quiso decir de dónde venía el número, así que se asciende
    a fuente del maestro la primera vez que aparece. Lo que no se hace es
    fingir autoridad: la referencia queda declarada como lo que es.
    """
    if not (texto or "").strip():
        return fuente_por_omision(db, company_id, actor)
    codigo = texto.strip().upper()[:64]
    ya = fuente_por_codigo(db, company_id, codigo)
    if ya is not None:
        return ya
    try:
        return create_source(
            db, company_id=company_id, code=codigo, name=texto.strip(), source_type="MANUAL",
            authority_reference="Declarada al registrar una tasa; autoridad sin verificar",
            priority=500, actor=actor)
    except ConflictError as e:
        # Otra petición la creó entre la búsqueda y el alta: es la misma fuente.
        ganadora = fuente_por_codigo(db, company_id, codigo)
        if e.code != "SOURCE_CODE_TAKEN" or ganadora is None:
            raise
        return ganadora


def fuente_por_omision(db: Session, company_id: str, actor: str | None = None) -> ExchangeRateSource:
    """La fuente que recibe lo que se registra sin decir de dónde viene.

    Existe para que el camino antiguo —`set_exchange_rate` sin fuente— siga
    funcionando sin fingir una autoridad que nadie declaró.
    """
    fuente = fuente_por_codigo(db, company_id, "LEGACY")
    if fuente is None:
        try:
            fuente = create_source(
                db, company_id=company_id, code="LEGACY", name="Origen sin declarar",
                source_type="MANUAL",
                authority_reference="Sin fuente declarada: registrada sin indicar procedencia",
                priority=900, actor=actor)
        except ConflictError as e:
            # Otra petición la creó entre la búsqueda y el alta.
            fuente = fuente_por_codigo(db, company_id, "LEGACY")
            if e.code != "SOURCE_CODE_TAKEN" or fuente is None:
                raise
    return fuente


# --------------------------------------------------------------------------- #
# Política de resolución
#
# Distinta de `TreasuryFxPolicy`, que es la de operación y es de la Spec 038:
# aquélla decide si se puede convertir; ésta, de dónde sale el número.
# --------------------------------------------------------------------------- #
def create_policy(db: Session, *, company_id: str, policy_code: str,
                  effective_from: date, allow_inversion: bool = False,
                  allow_triangulation: bool = False, triangulation_currency: str | None = None,
                  max_age_days: int | None = None, carry_forward: bool = True,
                  require_rate_approval: bool = False, rate_scale: int = _ESCALA_HEREDADA,
                  authority_reference: str | None = None,
                  actor: str | None = None) -> ExchangeRatePolicy:
    company_id = _company(company_id, obj="política de tasa")
    previas = db.execute(select(ExchangeRatePolicy).where(
        ExchangeRatePolicy.company_id == company_id,
        ExchangeRatePolicy.policy_code == policy_code)).scalars().all()
    politica = ExchangeRatePolicy(
        company_id=company_id, policy_code=policy_code,
        version=max((p.version for p in previas), default=0) + 1,
        allow_inversion=allow_inversion, allow_triangulation=allow_triangulation,
        triangulation_currency=triangulation_currency, max_age_days=max_age_days,
        carry_forward=carry_forward, require_rate_approval=require_rate_approval,
        rate_scale=rate_scale, authority_reference=authority_reference,
        effective_from=effective_from, status="DRAFT", created_by=actor)
    # La versión es «la mayor más uno», y dos altas simultáneas del mismo código
    # calculan la misma. Decide el índice único; quien pierde puede reintentar.
    try:
        with db.begin_nested():
            db.add(politica)
            db.flush()
    except IntegrityError as e:
        if not es_violacion_unica(e, "uq_rate_policies_company_code_version"):
            raise
        raise ConflictError(
            code="RATE_POLICY_VERSION_CONFLICT",
            message="Otra versión de esa política se creó a la vez; vuelva a intentarlo.") from None
    return politica


def activate_policy(db: Session, *, company_id: str, policy_id: str,
                    actor: str | None = None) -> ExchangeRatePolicy:
    politica = db.get(ExchangeRatePolicy, str(policy_id))
    if politica is None or str(politica.company_id) != str(company_id):
        raise NotFoundError(code="RATE_POLICY_NOT_FOUND", message="Política de tasa no encontrada")
    for otra in db.execute(select(ExchangeRatePolicy).where(
            ExchangeRatePolicy.company_id == company_id,
            ExchangeRatePolicy.status == "ACTIVE")).scalars().all():
        otra.status = "SUPERSEDED"
        otra.effective_to = politica.effective_from
    db.flush()
    politica.status = "ACTIVE"
    politica.updated_at = datetime.now(UTC)
    db.flush()
    return politica


def active_policy(db: Session, company_id: str,
                  on_date: date | None = None) -> ExchangeRatePolicy | None:
    dia = on_date or hoy_de_negocio()
    return db.execute(select(ExchangeRatePolicy).where(
        ExchangeRatePolicy.company_id == company_id,
        ExchangeRatePolicy.status == "ACTIVE",
        ExchangeRatePolicy.effective_from <= dia)
        .order_by(ExchangeRatePolicy.effective_from.desc(),
                  ExchangeRatePolicy.version.desc())).scalars().first()


# --------------------------------------------------------------------------- #
# Registro de observaciones
# --------------------------------------------------------------------------- #
def register_rate(db: Session, *, company_id: str, base_code: str, quote_code: str,
                  rate: Decimal | str, effective_at: date | datetime,
                  source_id: str | None = None, rate_type: str = "REFERENCE",
                  published_at: datetime | None = None, reason: str | None = None,
                  source_reference: str | None = None, authority_reference: str | None = None,
                  provider_observation_id: str | None = None,
                  import_batch_id: str | None = None,
                  actor: str | None = None) -> ExchangeRate:
    """Registra una cotización. **1 base = `rate` quote.**"""
    company_id = _company(company_id, obj="tasa")
    valor = _dec(rate)
    if valor <= 0:
        raise KontrolError(code="INVALID_RATE",
                           message="La tasa debe ser positiva.", status_code=422,
                           field_errors={"rate": ["Debe ser mayor que cero."]})
    if base_code == quote_code:
        raise KontrolError(
            code="INVALID_PAIR",
            message="Una moneda no cotiza contra sí misma: eso es la identidad, no una tasa.",
            status_code=422)
    base = _exigir_moneda(db, company_id, base_code)
    quote = _exigir_moneda(db, company_id, quote_code)
    fuente = (_exigir_fuente(db, company_id, source_id) if source_id
              else fuente_por_omision(db, company_id, actor))
    if fuente.status != "ACTIVE":
        raise ConflictError(code="SOURCE_DISABLED",
                            message=f"La fuente {fuente.code} está desactivada.")
    politica = active_policy(db, company_id)
    if not fuente.allows_manual and import_batch_id is None and provider_observation_id is None:
        raise ConflictError(code="MANUAL_RATE_NOT_ALLOWED",
                            message=f"La fuente {fuente.code} no admite carga manual.")

    momento = _momento(effective_at)
    repetida = db.execute(select(ExchangeRate).where(
        ExchangeRate.company_id == company_id,
        ExchangeRate.base_currency_id == str(base.id),
        ExchangeRate.quote_currency_id == str(quote.id),
        ExchangeRate.source_id == str(fuente.id),
        ExchangeRate.rate_type == rate_type,
        ExchangeRate.effective_at == momento,
        ExchangeRate.status != "SUPERSEDED")).scalars().first()
    if repetida is not None:
        raise ConflictError(
            code="DUPLICATE_OBSERVATION",
            message="Ya hay una observación para ese par, fuente, tipo y momento.",
            details={"observation_id": str(repetida.id), "rate": str(repetida.rate)})

    pendiente = bool(politica and politica.require_rate_approval
                     and provider_observation_id is None)
    obs = ExchangeRate(
        company_id=company_id,
        # Compatibilidad con la 038: su instantánea apunta a esta fila y su
        # lectura antigua usa `currency_id`/`rate_date`.
        currency_id=str(base.id), rate_date=hoy_de_negocio(momento),
        rate=valor, source=source_reference or fuente.code,
        base_currency_id=str(base.id), quote_currency_id=str(quote.id),
        source_id=str(fuente.id), rate_type=rate_type,
        effective_at=momento, published_at=published_at, observed_at=datetime.now(UTC),
        status="PENDING_APPROVAL" if pendiente else "ACTIVE", version=1,
        provider_observation_id=provider_observation_id, import_batch_id=import_batch_id,
        source_reference=source_reference, authority_reference=authority_reference,
        entered_by=actor, reason=reason, created_by=actor)
    # La comprobación de `repetida` y esta inserción no son atómicas. Decide
    # `uq_exchange_rates_observation`, y quien pierde la carrera recibe el mismo
    # `DUPLICATE_OBSERVATION` que si hubiera llegado tarde, no un 500.
    try:
        with db.begin_nested():
            db.add(obs)
            db.flush()
    except IntegrityError as e:
        if not es_violacion_unica(e, "uq_exchange_rates_observation"):
            raise
        raise ConflictError(
            code="DUPLICATE_OBSERVATION",
            message="Ya hay una observación para ese par, fuente, tipo y momento.") from None
    return obs


def approve_rate(db: Session, *, company_id: str, observation_id: str,
                 actor: str | None = None) -> ExchangeRate:
    """Aprobar es de otra persona. Quien registró no firma lo suyo."""
    obs = _exigir_observacion(db, company_id, observation_id)
    if obs.status != "PENDING_APPROVAL":
        raise ConflictError(code="RATE_NOT_PENDING",
                            message="Esa observación no está pendiente de aprobación.")
    if actor and obs.entered_by and str(actor) == str(obs.entered_by):
        raise ConflictError(
            code="SELF_APPROVAL_FORBIDDEN",
            message="Quien registra una tasa no puede aprobarla.")
    obs.status = "ACTIVE"
    obs.approved_by = actor
    obs.updated_at = datetime.now(UTC)
    db.flush()
    return obs


def correct_rate(db: Session, *, company_id: str, observation_id: str,
                 rate: Decimal | str, reason: str, actor: str | None = None) -> ExchangeRate:
    """Una corrección **sucede** a la anterior; no la reescribe.

    La operación que ya usó la tasa vieja sigue apuntando a la fila vieja: por
    eso la original se conserva marcada y nunca se toca su importe.
    """
    if not (reason or "").strip():
        raise KontrolError(code="CORRECTION_REASON_REQUIRED",
                           message="Corregir una tasa exige motivo.", status_code=422)
    vieja = _exigir_observacion(db, company_id, observation_id)
    if vieja.status == "SUPERSEDED":
        # Corregir otra vez la original crearía una segunda «versión siguiente»
        # que choca con la que ya existe: un 500 sin necesidad de concurrencia.
        # Se corrige la versión vigente, no la sustituida.
        raise ConflictError(code="RATE_ALREADY_SUPERSEDED",
                            message="Esa tasa ya fue corregida: corrija la versión vigente.",
                            details={"observation_id": str(vieja.id)})
    valor = _dec(rate)
    if valor <= 0:
        raise KontrolError(code="INVALID_RATE", message="La tasa debe ser positiva.",
                           status_code=422)
    vieja.status = "SUPERSEDED"
    vieja.updated_at = datetime.now(UTC)
    db.flush()
    nueva = ExchangeRate(
        company_id=str(vieja.company_id), currency_id=str(vieja.currency_id),
        rate_date=vieja.rate_date, rate=valor, source=vieja.source,
        base_currency_id=vieja.base_currency_id, quote_currency_id=vieja.quote_currency_id,
        source_id=vieja.source_id, rate_type=vieja.rate_type,
        effective_at=vieja.effective_at, published_at=vieja.published_at,
        observed_at=datetime.now(UTC), status="ACTIVE", version=vieja.version + 1,
        supersedes_id=str(vieja.id), source_reference=vieja.source_reference,
        authority_reference=vieja.authority_reference, entered_by=actor,
        reason=reason, created_by=actor)
    # Dos correcciones simultáneas de la misma tasa pasan ambas la comprobación
    # de estado; decide el índice único y quien pierde no recibe un 500.
    try:
        with db.begin_nested():
            db.add(nueva)
            db.flush()
    except IntegrityError as e:
        if not es_violacion_unica(e, "uq_exchange_rates_observation"):
            raise
        raise ConflictError(code="RATE_ALREADY_SUPERSEDED",
                            message="Esa tasa ya fue corregida: corrija la versión vigente.",
                            details={"observation_id": str(vieja.id)}) from None
    return nueva


def _exigir_observacion(db: Session, company_id: str, observation_id: str) -> ExchangeRate:
    obs = db.get(ExchangeRate, str(observation_id))
    if obs is None or str(obs.company_id) != str(company_id):
        raise NotFoundError(code="RATE_OBSERVATION_NOT_FOUND", message="Observación no encontrada")
    return obs


# --------------------------------------------------------------------------- #
# Resolución
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class RateResolution:
    """El resultado de resolver una tasa, con toda su procedencia.

    `derived` dice si el número salió de una fila tal cual (`None`), de
    invertir otra (`INVERSE`) o de cruzar dos (`TRIANGULATION`). La 038 lo
    guarda en su instantánea: sin ese dato, reconstruir una operación diría
    «usó la tasa 40» cuando usó 0,025.
    """

    rate: Decimal
    base_code: str
    quote_code: str
    effective_at: datetime
    observation_id: str | None = None
    source_code: str | None = None
    rate_type: str | None = None
    published_at: datetime | None = None
    observed_at: datetime | None = None
    version: int | None = None
    status: str | None = None
    derived: str | None = None
    derived_from: tuple[str, ...] = ()
    identity: bool = False


def _observacion(db: Session, company_id: str, base: Currency, quote: Currency,
                 momento: datetime, rate_type: str | None,
                 source_code: str | None) -> ExchangeRate | None:
    """La observación vigente de ese par en ese momento.

    Se busca **con fecha**: `effective_at <= momento`. Una tasa de mañana no
    valora una operación de ayer. Y el desempate es explícito —momento, después
    versión, después antigüedad— porque antes lo decidía el orden que le
    apeteciera a PostgreSQL.
    """
    consulta = select(ExchangeRate).where(
        ExchangeRate.company_id == company_id,
        ExchangeRate.base_currency_id == str(base.id),
        ExchangeRate.quote_currency_id == str(quote.id),
        ExchangeRate.status == "ACTIVE",
        ExchangeRate.effective_at.is_not(None),
        ExchangeRate.effective_at <= momento)
    if rate_type:
        consulta = consulta.where(ExchangeRate.rate_type == rate_type)
    fuentes = select(ExchangeRateSource.id).where(
        ExchangeRateSource.company_id == company_id,
        ExchangeRateSource.status == "ACTIVE")
    if source_code:
        fuentes = fuentes.where(ExchangeRateSource.code == source_code)
    consulta = consulta.where(ExchangeRate.source_id.in_(fuentes))
    filas = db.execute(
        consulta.order_by(ExchangeRate.effective_at.desc(),
                          ExchangeRate.version.desc(),
                          ExchangeRate.created_at.desc())).scalars().all()
    if not filas:
        return None
    # La prioridad de la fuente la manda el maestro, no el orden de la tabla.
    prioridades = {
        str(f.id): f.priority
        for f in db.execute(select(ExchangeRateSource).where(
            ExchangeRateSource.company_id == company_id)).scalars().all()}
    primera = filas[0].effective_at
    delmismo = [f for f in filas if f.effective_at == primera]
    delmismo.sort(key=lambda f: (prioridades.get(str(f.source_id), 10_000),
                                 -f.version))
    return delmismo[0]


def _caducada(politica: ExchangeRatePolicy | None, obs: ExchangeRate,
              momento: datetime) -> bool:
    if politica is None or politica.max_age_days is None:
        return False
    return obs.effective_at is not None and \
        (momento - obs.effective_at) > timedelta(days=politica.max_age_days)


def resolve_rate(db: Session, *, company_id: str, base_code: str, quote_code: str,
                 effective_at: date | datetime | None = None, rate_type: str | None = None,
                 source_code: str | None = None) -> RateResolution:
    """La tasa que convierte `base` en `quote` en ese momento.

    Si no hay ninguna, **falla**. Nunca devuelve uno: entre monedas distintas,
    que falte la tasa y que la tasa sea uno son cosas distintas, y confundirlas
    fue exactamente el defecto que la 038 tuvo que corregir.
    """
    company_id = _company(company_id, obj="resolver una tasa")
    momento = _momento_consulta(effective_at)

    # Identidad: no es una cotización de mercado y no necesita fila.
    if base_code == quote_code:
        return RateResolution(rate=Decimal(1), base_code=base_code, quote_code=quote_code,
                              effective_at=momento, identity=True,
                              source_code="SAME_CURRENCY_IDENTITY")

    base = _exigir_moneda(db, company_id, base_code)
    quote = _exigir_moneda(db, company_id, quote_code)
    politica = active_policy(db, company_id, hoy_de_negocio(momento))

    directa = _observacion(db, company_id, base, quote, momento, rate_type, source_code)
    if directa is not None:
        if _caducada(politica, directa, momento):
            raise ConflictError(
                code="STALE_RATE",
                message="La tasa disponible excede la antigüedad que permite la política.",
                details={"base": base_code, "quote": quote_code,
                         "effective_at": directa.effective_at.isoformat(),
                         "max_age_days": politica.max_age_days if politica else None})
        return _resolucion(directa, base_code, quote_code, db)

    # Inversa: usar USD→VES para responder VES→USD es una decisión económica.
    inversa = _observacion(db, company_id, quote, base, momento, rate_type, source_code)
    if inversa is not None:
        if politica is None or not politica.allow_inversion:
            raise ConflictError(
                code="INVERSION_NOT_ALLOWED",
                message="Hay tasa en el sentido contrario, pero la política no permite invertirla.",
                details={"base": base_code, "quote": quote_code,
                         "available_pair": f"{quote_code}/{base_code}"})
        if _caducada(politica, inversa, momento):
            raise ConflictError(code="STALE_RATE",
                                message="La tasa inversa excede la antigüedad permitida.")
        escala = politica.rate_scale if politica else _ESCALA_HEREDADA
        valor = (Decimal(1) / _dec(inversa.rate)).quantize(Decimal(1).scaleb(-escala))
        return RateResolution(
            rate=valor, base_code=base_code, quote_code=quote_code,
            effective_at=inversa.effective_at or momento,
            observation_id=str(inversa.id), source_code=_codigo_fuente(db, inversa),
            rate_type=inversa.rate_type, published_at=inversa.published_at,
            observed_at=inversa.observed_at, version=inversa.version, status=inversa.status,
            derived="INVERSE", derived_from=(str(inversa.id),))

    # Triangulación: cruzar dos cotizaciones también lo es.
    if politica is not None and politica.allow_triangulation:
        puente_code = politica.triangulation_currency or moneda_funcional(db, company_id)
        if puente_code not in (base_code, quote_code):
            puente = moneda_por_codigo(db, company_id, puente_code)
            if puente is not None:
                a = _observacion(db, company_id, base, puente, momento, rate_type, source_code)
                b = _observacion(db, company_id, quote, puente, momento, rate_type, source_code)
                if a is not None and b is not None and _dec(b.rate) > 0:
                    escala = politica.rate_scale
                    valor = (_dec(a.rate) / _dec(b.rate)).quantize(Decimal(1).scaleb(-escala))
                    return RateResolution(
                        rate=valor, base_code=base_code, quote_code=quote_code,
                        effective_at=min(a.effective_at or momento, b.effective_at or momento),
                        source_code=f"{_codigo_fuente(db, a)}+{_codigo_fuente(db, b)}",
                        rate_type=rate_type, derived="TRIANGULATION",
                        derived_from=(str(a.id), str(b.id)))

    raise ConflictError(
        code="MISSING_RATE",
        message="No hay tasa registrada para ese par en esa fecha.",
        details={"base": base_code, "quote": quote_code,
                 "effective_at": momento.isoformat(),
                 "rate_type": rate_type, "source": source_code})


def _codigo_fuente(db: Session, obs: ExchangeRate) -> str | None:
    if not obs.source_id:
        return obs.source
    fuente = db.get(ExchangeRateSource, str(obs.source_id))
    return fuente.code if fuente else obs.source


def _resolucion(obs: ExchangeRate, base_code: str, quote_code: str,
                db: Session) -> RateResolution:
    return RateResolution(
        rate=_dec(obs.rate), base_code=base_code, quote_code=quote_code,
        effective_at=obs.effective_at or _momento(obs.rate_date),
        observation_id=str(obs.id), source_code=_codigo_fuente(db, obs),
        rate_type=obs.rate_type, published_at=obs.published_at,
        observed_at=obs.observed_at, version=obs.version, status=obs.status)


# --------------------------------------------------------------------------- #
# Importación
# --------------------------------------------------------------------------- #
_COLUMNAS = ("base_currency", "quote_currency", "rate", "effective_at")


def import_rates(db: Session, *, company_id: str, contenido: bytes | str,
                 source_id: str, rate_type: str = "REFERENCE",
                 filename: str | None = None,
                 actor: str | None = None) -> dict:
    """Carga un fichero de tasas. Reimportar el mismo no duplica nada.

    Ninguna fila inválida se descarta en silencio: cada una vuelve con su
    número de línea, su campo y su motivo.
    """
    company_id = _company(company_id, obj="importar tasas")
    crudo = contenido.encode() if isinstance(contenido, str) else contenido
    huella = hashlib.sha256(crudo).hexdigest()
    previo = db.execute(select(ExchangeRateImportBatch).where(
        ExchangeRateImportBatch.company_id == company_id,
        ExchangeRateImportBatch.content_hash == huella)).scalars().first()
    if previo is not None:
        raise ConflictError(
            code="IMPORT_DUPLICATE",
            message="Ese mismo fichero ya se importó.",
            details={"batch_id": str(previo.id), "imported": previo.imported_count})

    fuente = _exigir_fuente(db, company_id, source_id)
    if fuente.status != "ACTIVE":
        raise ConflictError(code="SOURCE_DISABLED",
                            message=f"La fuente {fuente.code} está desactivada.")

    lector = csv.DictReader(io.StringIO(crudo.decode("utf-8-sig")))
    faltan = [c for c in _COLUMNAS if c not in (lector.fieldnames or [])]
    if faltan:
        raise KontrolError(code="IMPORT_COLUMNS_MISSING",
                           message=f"Faltan columnas: {', '.join(faltan)}.", status_code=422)

    lote = ExchangeRateImportBatch(
        company_id=company_id, source_id=str(fuente.id), rate_type=rate_type,
        filename=filename, content_hash=huella, status="COMPLETED", created_by=actor)
    # Dos subidas simultáneas del mismo fichero pasan ambas la búsqueda del hash;
    # decide el índice único y la perdedora recibe `IMPORT_DUPLICATE`.
    try:
        with db.begin_nested():
            db.add(lote)
            db.flush()
    except IntegrityError as e:
        if not es_violacion_unica(e, "uq_rate_import_company_hash"):
            raise
        raise ConflictError(code="IMPORT_DUPLICATE",
                            message="Ese mismo fichero ya se importó.") from None

    errores: list[dict] = []
    importadas = 0
    total = 0
    for numero, fila in enumerate(lector, start=2):
        total += 1
        try:
            momento = _momento(_fecha(fila["effective_at"]))
            register_rate(
                db, company_id=company_id,
                base_code=(fila["base_currency"] or "").strip().upper(),
                quote_code=(fila["quote_currency"] or "").strip().upper(),
                rate=(fila["rate"] or "").strip(), effective_at=momento,
                source_id=str(fuente.id), rate_type=rate_type,
                source_reference=(fila.get("source_reference") or "").strip() or None,
                import_batch_id=str(lote.id), actor=actor)
            importadas += 1
        except KontrolError as e:
            errores.append({"row": numero, "code": e.code, "message": e.message,
                            "value": {c: fila.get(c) for c in _COLUMNAS}})
        except (ValueError, KeyError, TypeError) as e:
            errores.append({"row": numero, "code": "INVALID_ROW", "message": str(e),
                            "value": {c: fila.get(c) for c in _COLUMNAS}})

    lote.row_count = total
    lote.imported_count = importadas
    lote.rejected_count = len(errores)
    lote.status = "COMPLETED" if not errores else "COMPLETED_WITH_ERRORS"
    db.flush()
    return {"batch_id": str(lote.id), "rows": total, "imported": importadas,
            "rejected": len(errores), "status": lote.status, "errors": errores}


def _fecha(texto: str) -> date | datetime:
    """Interpreta una fecha del CSV en el calendario de negocio.

    El CSV lo escribe una persona en Venezuela: una hora sin zona es hora de
    Caracas (FR-001-249). Una fecha suelta se deja como `date`; `_momento` la
    llevará a las 00:00 de Caracas.
    """
    limpio = (texto or "").strip()
    if not limpio:
        raise ValueError("La fecha de vigencia es obligatoria.")
    if "T" not in limpio and " " not in limpio:
        return date.fromisoformat(limpio)
    valor = datetime.fromisoformat(limpio)
    if valor.tzinfo is None:
        return valor.replace(tzinfo=zona_de_negocio())
    return valor


# --------------------------------------------------------------------------- #
# Contrato para la Spec 048
# --------------------------------------------------------------------------- #
def ingest_provider_observations(db: Session, *, company_id: str, source_id: str,
                                 observaciones: list[dict],
                                 actor: str | None = None) -> dict:
    """Recibe tasas ya **normalizadas** por un adaptador externo de la Spec 048.

    Aquí no se llama a ninguna web ni se interpreta el formato de nadie: la
    integración es de la 048 y este módulo solo acepta el resultado. Mientras no
    exista un canal oficial estable, la operación vive de la carga manual y del
    fichero, que es lo honesto.
    """
    company_id = _company(company_id, obj="ingesta de tasas")
    fuente = _exigir_fuente(db, company_id, source_id)
    if fuente.status != "ACTIVE":
        raise ConflictError(code="SOURCE_DISABLED",
                            message=f"La fuente {fuente.code} está desactivada.")
    aceptadas, repetidas, rechazadas = 0, 0, []
    for o in observaciones:
        identificador = o.get("provider_observation_id")
        if identificador:
            ya = db.execute(select(ExchangeRate).where(
                ExchangeRate.company_id == company_id,
                ExchangeRate.source_id == str(fuente.id),
                ExchangeRate.provider_observation_id == str(identificador))).scalars().first()
            if ya is not None:
                repetidas += 1
                continue
        try:
            register_rate(
                db, company_id=company_id, base_code=o["base_currency"],
                quote_code=o["quote_currency"], rate=o["rate"],
                effective_at=_momento(o.get("effective_at")),
                published_at=o.get("published_at"), source_id=str(fuente.id),
                rate_type=o.get("rate_type", "REFERENCE"),
                provider_observation_id=str(identificador) if identificador else None,
                source_reference=o.get("source_reference"), actor=actor)
            aceptadas += 1
        except KontrolError as e:
            rechazadas.append({"code": e.code, "message": e.message, "value": o})
    fuente.last_sync_at = datetime.now(UTC)
    if not rechazadas:
        fuente.last_success_at = fuente.last_sync_at
        fuente.last_error = None
    else:
        fuente.last_error = rechazadas[0]["message"][:1000]
    db.flush()
    return {"accepted": aceptadas, "duplicated": repetidas,
            "rejected": len(rechazadas), "errors": rechazadas}
