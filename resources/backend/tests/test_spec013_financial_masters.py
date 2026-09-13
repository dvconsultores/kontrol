"""Spec 013 · maestros financieros — la tasa tiene par, fuente y procedencia.

La 038 dejó de inventar tasas. Al hacerlo destapó que nadie las registra, y que
lo poco que había no se sostenía: dos monedas con el mismo código convivían y la
resolución elegía una al azar; dos tasas del mismo día convivían y el desempate
lo decidía PostgreSQL; y una fila no decía contra qué moneda cotizaba.

Lo que estas pruebas defienden, por orden de gravedad: que **falta de tasa no es
tasa uno**, que nadie derive una cotización sin permiso y sin decirlo, y que
corregir una tasa no reescriba la operación que ya usó la anterior.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.treasury import rates as rz
from app.modules.treasury import service as tz
from app.modules.treasury.models import ExchangeRate

pytest_plugins = ("tests.conftest_multicompany",)


def _moneda(db, company_id, codigo):
    """Una moneda del maestro. Si ya está activa, se reutiliza."""
    ya = rz.moneda_por_codigo(db, company_id, codigo)
    if ya is not None:
        return ya
    cur = tz.create_currency(db, company_id=company_id, code=codigo, name=codigo, actor="qa")
    db.flush()
    return cur


def _codigo() -> str:
    """Un código de moneda que no choca con el de otra prueba."""
    return f"Z{uuid4().hex[:5].upper()}"


def _fuente(db, mundo, *, code=None, prioridad=100, manual=True, company_id=None):
    return rz.create_source(db, company_id=company_id or mundo.company_a,
                            code=code or f"SRC-{uuid4().hex[:6]}", name="Fuente de prueba",
                            source_type="OFFICIAL", allows_manual=manual, priority=prioridad,
                            authority_reference="Pendiente de validación legal (D0-07)",
                            actor="qa")


def _sin_politica(db, mundo, company_id=None):
    """La base del arnés es compartida: otra prueba pudo dejar política activa."""
    from sqlalchemy import select

    from app.modules.treasury.models import ExchangeRatePolicy
    for p in db.execute(select(ExchangeRatePolicy).where(
            ExchangeRatePolicy.company_id == (company_id or mundo.company_a),
            ExchangeRatePolicy.status == "ACTIVE")).scalars().all():
        p.status = "SUPERSEDED"
    db.flush()


def _politica(db, mundo, *, inversion=False, triangulacion=False, puente=None,
              max_age=None, aprobacion=False, company_id=None):
    cid = company_id or mundo.company_a
    _sin_politica(db, mundo, cid)
    p = rz.create_policy(db, company_id=cid, policy_code=f"RP-{uuid4().hex[:6]}",
                         effective_from=date(2020, 1, 1), allow_inversion=inversion,
                         allow_triangulation=triangulacion, triangulation_currency=puente,
                         max_age_days=max_age, require_rate_approval=aprobacion,
                         authority_reference="Pendiente de validación legal (D0-07)",
                         actor="qa")
    rz.activate_policy(db, company_id=cid, policy_id=str(p.id), actor="qa")
    db.flush()
    return p


# =========================================================================== #
# El par se dice, no se supone
# =========================================================================== #
def test_la_observacion_guarda_su_par_explicito(mundo):
    """«1 base = rate quote». Antes el par lo suponía el código."""
    db = mundo.factory()
    try:
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code, rate="100.00",
                               effective_at=date.today(), source_id=str(fuente.id),
                               actor="tesorero")
        db.flush()
        assert str(obs.base_currency_id) == str(base.id)
        assert str(obs.quote_currency_id) == str(quote.id)
        assert Decimal(str(obs.rate)) == Decimal("100.00")
        assert obs.effective_at is not None and obs.effective_at.tzinfo is not None
    finally:
        db.close()


def test_una_moneda_no_cotiza_contra_si_misma(mundo):
    db = mundo.factory()
    try:
        c = _moneda(db, mundo.company_a, _codigo())
        with pytest.raises(KontrolError) as exc:
            rz.register_rate(db, company_id=mundo.company_a, base_code=c.code,
                             quote_code=c.code, rate="1", effective_at=date.today(),
                             actor="qa")
        assert exc.value.code == "INVALID_PAIR"
    finally:
        db.close()


# =========================================================================== #
# Falta de tasa no es tasa uno
# =========================================================================== #
def test_sin_observacion_el_par_no_se_resuelve(mundo):
    """`MISSING_RATE`. Nunca uno: el uno parece un número correcto."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        a = _moneda(db, mundo.company_a, _codigo())
        b = _moneda(db, mundo.company_a, _codigo())
        with pytest.raises(ConflictError) as exc:
            rz.resolve_rate(db, company_id=mundo.company_a, base_code=a.code,
                            quote_code=b.code, effective_at=date.today())
        assert exc.value.code == "MISSING_RATE"
    finally:
        db.close()


def test_la_misma_moneda_es_identidad_sin_fila_de_mercado(mundo):
    db = mundo.factory()
    try:
        c = _moneda(db, mundo.company_a, _codigo())
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=c.code,
                            quote_code=c.code, effective_at=date.today())
        assert r.rate == Decimal(1)
        assert r.identity is True
        assert r.observation_id is None, "inventó una fila de mercado para la identidad"
        assert r.source_code == "SAME_CURRENCY_IDENTITY"
    finally:
        db.close()


def test_la_resolucion_devuelve_la_procedencia_entera(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="100.00", effective_at=date.today(),
                         source_id=str(fuente.id), actor="tesorero")
        db.flush()
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code, effective_at=date.today())
        assert r.rate == Decimal("100.000000")
        assert r.source_code == fuente.code
        assert r.rate_type == "REFERENCE"
        assert r.observation_id is not None
        assert r.derived is None, "derivó una tasa que estaba registrada directa"
    finally:
        db.close()


# =========================================================================== #
# La fecha manda
# =========================================================================== #
def test_una_tasa_de_manana_no_valora_una_operacion_de_ayer(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        ayer = date.today() - timedelta(days=1)
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="100.00", effective_at=ayer,
                         source_id=str(fuente.id), actor="qa")
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="120.00",
                         effective_at=date.today() + timedelta(days=1),
                         source_id=str(fuente.id), actor="qa")
        db.flush()
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code, effective_at=ayer)
        assert r.rate == Decimal("100.000000"), "usó una tasa futura para una fecha pasada"
    finally:
        db.close()


def test_la_tasa_caduca_cuando_la_politica_lo_dice(mundo):
    """Sin política no hay tope, y eso es lo que había: una tasa de 2020
    valorando una operación de 2026 sin que nada avisara."""
    db = mundo.factory()
    try:
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        _politica(db, mundo)
        vieja = date.today() - timedelta(days=90)
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="100.00", effective_at=vieja,
                         source_id=str(fuente.id), actor="qa")
        db.flush()
        # Sin tope: se arrastra, que es lo que hay que hacer un domingo.
        assert rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code).rate == Decimal("100.000000")

        _politica(db, mundo, max_age=7)
        with pytest.raises(ConflictError) as exc:
            rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code)
        assert exc.value.code == "STALE_RATE"
    finally:
        db.close()


# =========================================================================== #
# Derivar es una decisión económica
# =========================================================================== #
def test_sin_politica_no_se_invierte_una_tasa(mundo):
    """Había tasa USD→VED y se respondía VED→USD con `1/tasa`, sin decirlo."""
    db = mundo.factory()
    try:
        _politica(db, mundo, inversion=False)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="100.00", effective_at=date.today(),
                         source_id=str(fuente.id), actor="qa")
        db.flush()
        with pytest.raises(ConflictError) as exc:
            rz.resolve_rate(db, company_id=mundo.company_a, base_code=quote.code,
                            quote_code=base.code, effective_at=date.today())
        assert exc.value.code == "INVERSION_NOT_ALLOWED"
        assert exc.value.details["available_pair"] == f"{base.code}/{quote.code}"
    finally:
        db.close()


def test_con_politica_se_invierte_y_queda_dicho(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo, inversion=True)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code, rate="100.00",
                               effective_at=date.today(), source_id=str(fuente.id), actor="qa")
        db.flush()
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=quote.code,
                            quote_code=base.code, effective_at=date.today())
        assert r.rate == Decimal("0.010000")
        assert r.derived == "INVERSE", "derivó sin dejar constancia"
        assert r.derived_from == (str(obs.id),)
    finally:
        db.close()


def test_sin_politica_no_se_triangula(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo, triangulacion=False)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        a = _moneda(db, mundo.company_a, _codigo())
        b = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        for cur, valor in ((a, "100.00"), (b, "50.00")):
            rz.register_rate(db, company_id=mundo.company_a, base_code=cur.code,
                             quote_code=funcional, rate=valor, effective_at=date.today(),
                             source_id=str(fuente.id), actor="qa")
        db.flush()
        with pytest.raises(ConflictError) as exc:
            rz.resolve_rate(db, company_id=mundo.company_a, base_code=a.code,
                            quote_code=b.code, effective_at=date.today())
        assert exc.value.code == "MISSING_RATE"
    finally:
        db.close()


def test_con_politica_se_triangula_y_queda_dicho(mundo):
    db = mundo.factory()
    try:
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        _politica(db, mundo, triangulacion=True, puente=funcional)
        a = _moneda(db, mundo.company_a, _codigo())
        b = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        for cur, valor in ((a, "100.00"), (b, "50.00")):
            rz.register_rate(db, company_id=mundo.company_a, base_code=cur.code,
                             quote_code=funcional, rate=valor, effective_at=date.today(),
                             source_id=str(fuente.id), actor="qa")
        db.flush()
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=a.code,
                            quote_code=b.code, effective_at=date.today())
        assert r.rate == Decimal("2.000000")
        assert r.derived == "TRIANGULATION"
        assert len(r.derived_from) == 2
    finally:
        db.close()


# =========================================================================== #
# La historia no se reescribe
# =========================================================================== #
def test_corregir_una_tasa_sucede_a_la_anterior(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        vieja = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                                 quote_code=quote.code, rate="100.00",
                                 effective_at=date.today(), source_id=str(fuente.id),
                                 actor="qa")
        db.flush()
        vieja_id, importe_viejo = str(vieja.id), Decimal(str(vieja.rate))

        nueva = rz.correct_rate(db, company_id=mundo.company_a, observation_id=vieja_id,
                                rate="120.00", reason="La fuente publicó una corrección",
                                actor="qa")
        db.flush()
        anterior = db.get(ExchangeRate, vieja_id)
        assert anterior.status == "SUPERSEDED"
        assert Decimal(str(anterior.rate)) == importe_viejo, "reescribió el importe histórico"
        assert str(nueva.supersedes_id) == vieja_id
        assert nueva.version == vieja.version + 1

        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code, effective_at=date.today())
        assert r.rate == Decimal("120.000000")
    finally:
        db.close()


def test_corregir_exige_motivo(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code, rate="100.00",
                               effective_at=date.today(), actor="qa")
        db.flush()
        with pytest.raises(KontrolError) as exc:
            rz.correct_rate(db, company_id=mundo.company_a, observation_id=str(obs.id),
                            rate="120", reason="   ", actor="qa")
        assert exc.value.code == "CORRECTION_REASON_REQUIRED"
    finally:
        db.close()


# =========================================================================== #
# Las fuentes
# =========================================================================== #
def test_una_fuente_desactivada_no_produce_tasas_pero_conserva_historia(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code, rate="100.00",
                               effective_at=date.today(), source_id=str(fuente.id), actor="qa")
        db.flush()
        rz.set_source_status(db, company_id=mundo.company_a, source_id=str(fuente.id),
                             status="DISABLED", actor="qa")
        db.flush()

        with pytest.raises(ConflictError) as exc:
            rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code, effective_at=date.today())
        assert exc.value.code == "MISSING_RATE"
        assert db.get(ExchangeRate, str(obs.id)) is not None, "la desactivación borró historia"

        with pytest.raises(ConflictError) as exc2:
            rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                             quote_code=quote.code, rate="110", effective_at=date.today(),
                             source_id=str(fuente.id), actor="qa")
        assert exc2.value.code == "SOURCE_DISABLED"
    finally:
        db.close()


def test_entre_dos_fuentes_manda_la_prioridad_no_el_orden_de_la_tabla(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        floja = _fuente(db, mundo, prioridad=900)
        buena = _fuente(db, mundo, prioridad=10)
        hoy = date.today()
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="900.00", effective_at=hoy,
                         source_id=str(floja.id), actor="qa")
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="10.00", effective_at=hoy,
                         source_id=str(buena.id), actor="qa")
        db.flush()
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code, effective_at=hoy)
        assert r.rate == Decimal("10.000000"), "el desempate no siguió la prioridad"
        assert r.source_code == buena.code
    finally:
        db.close()


def test_dos_observaciones_en_las_mismas_coordenadas_no_conviven(mundo):
    db = mundo.factory()
    try:
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        hoy = date.today()
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="100.00", effective_at=hoy,
                         source_id=str(fuente.id), actor="qa")
        db.flush()
        with pytest.raises(ConflictError) as exc:
            rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                             quote_code=quote.code, rate="200.00", effective_at=hoy,
                             source_id=str(fuente.id), actor="qa")
        assert exc.value.code == "DUPLICATE_OBSERVATION"
    finally:
        db.close()


# =========================================================================== #
# El dinero, exacto
# =========================================================================== #
def test_la_tasa_no_pasa_por_coma_flotante(mundo):
    """`0,1 + 0,2` y sus amigos: si algo se convierte a `float`, se nota."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="0.300000", effective_at=date.today(),
                         source_id=str(fuente.id), actor="qa")
        db.flush()
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code)
        assert r.rate == Decimal("0.100000") + Decimal("0.200000")
        assert isinstance(r.rate, Decimal)
        assert r.rate * Decimal("3") == Decimal("0.900000")
    finally:
        db.close()


def test_la_tasa_conserva_todos_sus_decimales(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="36.123456", effective_at=date.today(),
                         source_id=str(fuente.id), actor="qa")
        db.commit()
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code)
        assert r.rate == Decimal("36.123456"), "la tasa perdió decimales por el camino"
    finally:
        db.close()


@pytest.mark.parametrize("valor", ["0", "-1", "0.000000"])
def test_una_tasa_no_positiva_se_rechaza(mundo, valor):
    db = mundo.factory()
    try:
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        with pytest.raises(KontrolError) as exc:
            rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                             quote_code=quote.code, rate=valor, effective_at=date.today(),
                             actor="qa")
        assert exc.value.code == "INVALID_RATE"
    finally:
        db.close()


# =========================================================================== #
# Multiempresa
# =========================================================================== #
def test_la_tasa_de_una_empresa_no_resuelve_en_otra(mundo):
    db = mundo.factory()
    try:
        codigo = _codigo()
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, codigo)
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=quote.code, rate="100.00", effective_at=date.today(),
                         source_id=str(fuente.id), actor="qa")
        # La empresa B tiene las mismas monedas y ninguna tasa.
        _moneda(db, mundo.company_b, codigo)
        _moneda(db, mundo.company_b, rz.moneda_funcional(db, mundo.company_b))
        db.flush()
        with pytest.raises(ConflictError) as exc:
            rz.resolve_rate(db, company_id=mundo.company_b, base_code=codigo,
                            quote_code=rz.moneda_funcional(db, mundo.company_b),
                            effective_at=date.today())
        assert exc.value.code == "MISSING_RATE"
    finally:
        db.close()


def test_no_se_corrige_una_observacion_de_otra_empresa(mundo):
    db = mundo.factory()
    try:
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code, rate="100.00",
                               effective_at=date.today(), actor="qa")
        db.commit()
        with pytest.raises(NotFoundError):
            rz.correct_rate(db, company_id=mundo.company_b, observation_id=str(obs.id),
                            rate="1", reason="Desde otra empresa", actor="x")
    finally:
        db.close()


def test_no_se_usa_una_fuente_de_otra_empresa(mundo):
    db = mundo.factory()
    try:
        ajena = _fuente(db, mundo, company_id=mundo.company_b)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        db.flush()
        with pytest.raises(NotFoundError):
            rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                             quote_code=quote.code, rate="100", effective_at=date.today(),
                             source_id=str(ajena.id), actor="qa")
    finally:
        db.close()


# =========================================================================== #
# Aprobación
# =========================================================================== #
def test_con_politica_de_aprobacion_la_tasa_nace_pendiente_y_no_resuelve(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo, aprobacion=True)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code, rate="100.00",
                               effective_at=date.today(), source_id=str(fuente.id),
                               actor="cajero")
        db.flush()
        assert obs.status == "PENDING_APPROVAL"
        with pytest.raises(ConflictError) as exc:
            rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code)
        assert exc.value.code == "MISSING_RATE", "una tasa sin aprobar se usó igual"

        rz.approve_rate(db, company_id=mundo.company_a, observation_id=str(obs.id),
                        actor="jefe")
        db.flush()
        assert rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code).rate == Decimal("100.000000")
    finally:
        db.close()


def test_quien_registra_una_tasa_no_la_aprueba(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo, aprobacion=True)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code, rate="100.00",
                               effective_at=date.today(), actor="cajero")
        db.flush()
        with pytest.raises(ConflictError) as exc:
            rz.approve_rate(db, company_id=mundo.company_a, observation_id=str(obs.id),
                            actor="cajero")
        assert exc.value.code == "SELF_APPROVAL_FORBIDDEN"
    finally:
        db.close()


# =========================================================================== #
# Importación
# =========================================================================== #
def _csv(filas: list[str]) -> str:
    cabecera = "base_currency,quote_currency,rate,effective_at"
    return "\n".join([cabecera, *filas]) + "\n"


def test_importar_crea_las_tasas_y_reimportar_no_duplica(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        a, b = _moneda(db, mundo.company_a, _codigo()), _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        hoy = date.today().isoformat()
        contenido = _csv([f"{a.code},{funcional},100.00,{hoy}",
                          f"{b.code},{funcional},50.00,{hoy}"])
        r = rz.import_rates(db, company_id=mundo.company_a, contenido=contenido,
                            source_id=str(fuente.id), filename="tasas.csv", actor="qa")
        db.flush()
        assert r["imported"] == 2 and r["rejected"] == 0

        with pytest.raises(ConflictError) as exc:
            rz.import_rates(db, company_id=mundo.company_a, contenido=contenido,
                            source_id=str(fuente.id), filename="tasas.csv", actor="qa")
        assert exc.value.code == "IMPORT_DUPLICATE"
    finally:
        db.close()


def test_ninguna_fila_invalida_se_descarta_en_silencio(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        buena = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        hoy = date.today().isoformat()
        contenido = _csv([
            f"{buena.code},{funcional},100.00,{hoy}",
            f"{buena.code},{funcional},0,{hoy}",
            f"{buena.code},{funcional},-5,{hoy}",
            f"NOEXISTE,{funcional},10,{hoy}",
            f"{buena.code},{funcional},10,no-es-fecha",
        ])
        r = rz.import_rates(db, company_id=mundo.company_a, contenido=contenido,
                            source_id=str(fuente.id), filename="sucio.csv", actor="qa")
        db.flush()
        assert r["imported"] == 1
        assert r["rejected"] == 4, "alguna fila inválida desapareció sin decirlo"
        codigos = {e["code"] for e in r["errors"]}
        assert "INVALID_RATE" in codigos and "CURRENCY_INACTIVE" in codigos
        assert all("row" in e and e["row"] >= 2 for e in r["errors"])
        assert r["status"] == "COMPLETED_WITH_ERRORS"
    finally:
        db.close()


def test_el_proveedor_no_duplica_la_misma_observacion(mundo):
    """Contrato para la Spec 048: aquí se acepta lo normalizado, no se busca."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        base = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        lote = [{"provider_observation_id": "prov-1", "base_currency": base.code,
                 "quote_currency": funcional, "rate": "100.00",
                 "effective_at": date.today()}]
        r1 = rz.ingest_provider_observations(db, company_id=mundo.company_a,
                                             source_id=str(fuente.id),
                                             observaciones=lote, actor="qa")
        db.flush()
        r2 = rz.ingest_provider_observations(db, company_id=mundo.company_a,
                                             source_id=str(fuente.id),
                                             observaciones=lote, actor="qa")
        db.flush()
        assert r1["accepted"] == 1
        assert r2["accepted"] == 0 and r2["duplicated"] == 1
        recargada = db.get(type(fuente), str(fuente.id))
        assert recargada.last_success_at is not None
    finally:
        db.close()


# =========================================================================== #
# La Spec 038 consume el contrato
# =========================================================================== #
def test_la_tesoreria_obtiene_la_tasa_real_y_congela_su_procedencia(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        base = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)

        # Antes de registrar nada: la operación se bloquea.
        with pytest.raises(ConflictError) as exc:
            tz.capture_rate_snapshot(db, company_id=mundo.company_a,
                                     source_currency=base.code, target_currency=funcional,
                                     actor="tesorero")
        assert exc.value.code == "RATE_NOT_AVAILABLE"

        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=funcional, rate="100.00",
                               effective_at=date.today(), source_id=str(fuente.id), actor="qa")
        db.flush()
        snap = tz.capture_rate_snapshot(db, company_id=mundo.company_a,
                                        source_currency=base.code, target_currency=funcional,
                                        actor="tesorero")
        db.flush()
        assert Decimal(str(snap.rate)) == Decimal("100.00000000")
        assert str(snap.exchange_rate_id) == str(obs.id)
        assert snap.rate_source == fuente.code
        assert snap.derivation is None
    finally:
        db.close()


def test_corregir_la_tasa_no_cambia_la_operacion_que_uso_la_anterior(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        base = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=funcional, rate="100.00",
                               effective_at=date.today(), source_id=str(fuente.id), actor="qa")
        db.flush()
        snap = tz.capture_rate_snapshot(db, company_id=mundo.company_a,
                                        source_currency=base.code, target_currency=funcional,
                                        actor="tesorero")
        db.flush()
        rz.correct_rate(db, company_id=mundo.company_a, observation_id=str(obs.id),
                        rate="120.00", reason="Corrección de la fuente", actor="qa")
        db.flush()

        assert Decimal(str(snap.rate)) == Decimal("100.00000000"), \
            "la corrección revaluó una operación pasada"
        assert str(snap.exchange_rate_id) == str(obs.id)
        assert db.get(ExchangeRate, str(obs.id)) is not None
        nueva = tz.capture_rate_snapshot(db, company_id=mundo.company_a,
                                         source_currency=base.code, target_currency=funcional,
                                         actor="tesorero")
        db.flush()
        assert Decimal(str(nueva.rate)) == Decimal("120.00000000")
    finally:
        db.close()


def test_la_tesoreria_marca_la_tasa_derivada_en_su_instantanea(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo, inversion=True)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        base = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=funcional, rate="100.00",
                               effective_at=date.today(), source_id=str(fuente.id), actor="qa")
        db.flush()
        snap = tz.capture_rate_snapshot(db, company_id=mundo.company_a,
                                        source_currency=funcional, target_currency=base.code,
                                        actor="tesorero")
        db.flush()
        assert Decimal(str(snap.rate)) == Decimal("0.01000000")
        assert snap.derivation == "INVERSE", "guardó una tasa derivada como si fuera directa"
        assert snap.derived_from == str(obs.id)
        assert snap.exchange_rate_id is None, \
            "apuntó a la fila directa, que dice otro número"
    finally:
        db.close()


def test_el_camino_antiguo_sigue_funcionando_y_ya_escribe_el_par(mundo):
    """`set_exchange_rate` es la puerta de compatibilidad, no un atajo sin par."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        quote = _moneda(db, mundo.company_a, funcional)
        base = _moneda(db, mundo.company_a, _codigo())
        obs = tz.set_exchange_rate(db, company_id=mundo.company_a, currency_id=str(base.id),
                                   rate_date=date.today(), rate=Decimal("100.00"),
                                   source="BCV", actor="qa")
        db.flush()
        assert str(obs.base_currency_id) == str(base.id)
        assert str(obs.quote_currency_id) == str(quote.id)
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=funcional)
        assert r.rate == Decimal("100.000000")
    finally:
        db.close()


def test_la_moneda_funcional_no_se_cotiza_contra_si_misma_por_el_camino_antiguo(mundo):
    db = mundo.factory()
    try:
        funcional = rz.moneda_funcional(db, mundo.company_a)
        propia = _moneda(db, mundo.company_a, funcional)
        db.flush()
        with pytest.raises(KontrolError) as exc:
            tz.set_exchange_rate(db, company_id=mundo.company_a, currency_id=str(propia.id),
                                 rate_date=date.today(), rate=Decimal("1"), actor="qa")
        assert exc.value.code == "INVALID_PAIR"
    finally:
        db.close()


def test_la_moneda_funcional_sale_de_la_empresa_no_del_codigo(mundo):
    """Antes `("VED", "VES")` estaba escrito dentro del dominio de un producto
    que se vende como parametrizable.

    La empresa la declara y la columna es obligatoria, así que ninguna se queda
    sin ella: la garantía es de la base, más fuerte que una comprobación. Lo que
    sí puede pasar es que alguien pregunte por una empresa que no existe, y ahí
    el sistema se niega en vez de suponer la moneda del país de quien escribió
    el código.
    """
    from sqlalchemy.exc import IntegrityError

    from app.modules.organization.models import Company

    db = mundo.factory()
    try:
        empresa = db.get(Company, mundo.company_a)
        assert rz.moneda_funcional(db, mundo.company_a) == empresa.functional_currency

        with pytest.raises(ConflictError) as exc:
            rz.moneda_funcional(db, str(uuid4()))
        assert exc.value.code == "FUNCTIONAL_CURRENCY_UNDEFINED"
    finally:
        db.close()

    otra = mundo.factory()
    try:
        empresa = otra.get(Company, mundo.company_a)
        empresa.functional_currency = None
        with pytest.raises(IntegrityError):
            otra.flush()
    finally:
        otra.rollback()
        otra.close()


def test_una_moneda_de_otra_empresa_no_sirve_para_registrar_aqui(mundo):
    """La guardia de empresa del maestro, aislada.

    Sin ella, pedir «la moneda ZZ» desde la empresa B devuelve la fila de la A
    —el filtro de la consulta de tasas tapaba el fallo— y la observación de B
    acabaría apuntando a una moneda que no es suya. La otra guardia protege el
    resultado; ésta protege el dato.
    """
    db = mundo.factory()
    try:
        codigo = _codigo()
        propia_a = _moneda(db, mundo.company_a, codigo)
        _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        db.flush()

        # En B esa moneda no existe: el sistema se niega en vez de coger la de A.
        with pytest.raises(ConflictError) as exc:
            rz.resolve_rate(db, company_id=mundo.company_b, base_code=codigo,
                            quote_code=rz.moneda_funcional(db, mundo.company_b))
        assert exc.value.code == "CURRENCY_INACTIVE"

        with pytest.raises(ConflictError) as exc2:
            rz.register_rate(db, company_id=mundo.company_b, base_code=codigo,
                             quote_code=rz.moneda_funcional(db, mundo.company_b),
                             rate="100", effective_at=date.today(), actor="qa")
        assert exc2.value.code == "CURRENCY_INACTIVE"

        # Y la moneda de A sigue siendo de A.
        assert str(propia_a.company_id) == str(mundo.company_a)
        assert rz.moneda_por_codigo(db, mundo.company_b, codigo) is None
    finally:
        db.close()


def test_el_arrastre_toma_la_ultima_anterior_no_la_primera(mundo):
    """Arrastrar es coger la más reciente de las que ya regían, no una cualquiera.

    Un domingo no hay cotización y se usa la del viernes. Si el orden se
    invierte, se usa la del año pasado: la consulta devuelve un número igual de
    plausible y nadie lo nota.
    """
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        for dias, valor in ((30, "100.00"), (10, "110.00"), (1, "120.00")):
            rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                             quote_code=quote.code, rate=valor,
                             effective_at=date.today() - timedelta(days=dias),
                             source_id=str(fuente.id), actor="qa")
        db.flush()
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=quote.code, effective_at=date.today())
        assert r.rate == Decimal("120.000000"), "arrastró una tasa más vieja que la vigente"

        # Y consultando una fecha intermedia, la que regía entonces.
        media = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                                quote_code=quote.code,
                                effective_at=date.today() - timedelta(days=5))
        assert media.rate == Decimal("110.000000")
    finally:
        db.close()


# =========================================================================== #
# Concurrencia y volumen — contra PostgreSQL de verdad
# =========================================================================== #
def test_dos_registros_simultaneos_no_crean_dos_observaciones(mundo):
    """Carrera forzada: la segunda pasa la comprobación y choca en el índice.

    Lo que se exige no es solo que quede una fila, sino que quien pierde reciba
    `DUPLICATE_OBSERVATION`. Antes esta prueba aceptaba también `IntegrityError`
    como «rechazo»: a nivel de servicio lo parece, pero por la API es un 500.
    """
    from sqlalchemy import func, select

    from tests.concurrency import carrera

    preparar = mundo.factory()
    try:
        _politica(preparar, mundo)
        base = _moneda(preparar, mundo.company_a, _codigo())
        quote = _moneda(preparar, mundo.company_a,
                        rz.moneda_funcional(preparar, mundo.company_a))
        fuente = _fuente(preparar, mundo)
        preparar.commit()
        base_code, quote_code, fuente_id = base.code, quote.code, str(fuente.id)
    finally:
        preparar.close()

    hoy = date.today()

    def registrar(sesion):
        return rz.register_rate(sesion, company_id=mundo.company_a, base_code=base_code,
                                quote_code=quote_code, rate="100.00", effective_at=hoy,
                                source_id=fuente_id, actor="qa")

    _, segundo = carrera(mundo.factory, registrar, registrar)
    assert isinstance(segundo, ConflictError), f"quien perdió recibió {segundo!r}"
    assert segundo.code == "DUPLICATE_OBSERVATION"

    comprobar = mundo.factory()
    try:
        cuantas = comprobar.execute(
            select(func.count()).select_from(ExchangeRate).where(
                ExchangeRate.company_id == mundo.company_a,
                ExchangeRate.source_id == fuente_id,
                ExchangeRate.rate_date == hoy)).scalar()
        assert cuantas == 1, "quedaron dos observaciones para las mismas coordenadas"
    finally:
        comprobar.close()


def test_dos_altas_simultaneas_de_la_misma_fuente_no_dan_un_500(mundo):
    from tests.concurrency import carrera

    codigo = f"RACE-{uuid4().hex[:6]}"

    def alta(sesion):
        return rz.create_source(sesion, company_id=mundo.company_a, code=codigo,
                                name="Carrera", actor="qa")

    _, segundo = carrera(mundo.factory, alta, alta)
    assert isinstance(segundo, ConflictError), f"quien perdió recibió {segundo!r}"
    assert segundo.code == "SOURCE_CODE_TAKEN"


def test_la_fuente_nombrada_por_texto_es_la_misma_aunque_lleguen_dos_a_la_vez(mundo):
    """El camino corto no debe fallar: si otra petición la creó, es la misma."""
    from tests.concurrency import carrera

    texto = f"banco-{uuid4().hex[:6]}"

    def pedir(sesion):
        return str(rz.fuente_por_texto(sesion, mundo.company_a, texto, actor="qa").id)

    primero, segundo = carrera(mundo.factory, pedir, pedir)
    assert not isinstance(segundo, Exception), f"el camino corto falló: {segundo!r}"
    assert segundo == primero


def test_la_moneda_funcional_se_asegura_una_sola_vez_aunque_lleguen_dos(mundo):
    """En una empresa nueva, dos registros a la vez no pueden crear dos «VED»."""
    from sqlalchemy import func, select

    from app.modules.treasury.models import Currency
    from tests.concurrency import carrera, empresa_nueva

    empresa = empresa_nueva(mundo.factory, mundo.t1, uuid4().hex[:10])

    def asegurar(sesion):
        return str(rz.asegurar_moneda_funcional(sesion, empresa, actor="qa").id)

    primero, segundo = carrera(mundo.factory, asegurar, asegurar)
    assert not isinstance(segundo, Exception), f"asegurar la moneda falló: {segundo!r}"
    assert segundo == primero

    db = mundo.factory()
    try:
        activas = db.execute(select(func.count()).select_from(Currency).where(
            Currency.company_id == empresa, Currency.code == "VED",
            Currency.status == "ACTIVE")).scalar()
        assert activas == 1
    finally:
        db.close()


def test_subir_dos_veces_a_la_vez_el_mismo_fichero_no_da_un_500(mundo):
    from tests.concurrency import carrera

    preparar = mundo.factory()
    try:
        _politica(preparar, mundo)
        funcional = rz.moneda_funcional(preparar, mundo.company_a)
        _moneda(preparar, mundo.company_a, funcional)
        base = _moneda(preparar, mundo.company_a, _codigo())
        fuente = _fuente(preparar, mundo)
        preparar.commit()
        fuente_id = str(fuente.id)
        contenido = ("base_currency,quote_currency,rate,effective_at\n"
                     f"{base.code},{funcional},100.00,{date.today().isoformat()}\n")
    finally:
        preparar.close()

    def subir(sesion):
        return rz.import_rates(sesion, company_id=mundo.company_a, contenido=contenido,
                               source_id=fuente_id, filename="carrera.csv", actor="qa")

    _, segundo = carrera(mundo.factory, subir, subir)
    assert isinstance(segundo, ConflictError), f"quien perdió recibió {segundo!r}"
    assert segundo.code == "IMPORT_DUPLICATE"


def test_dos_versiones_simultaneas_de_la_misma_politica_no_dan_un_500(mundo):
    from tests.concurrency import carrera

    codigo = f"RACEPOL-{uuid4().hex[:6]}"

    def alta(sesion):
        return rz.create_policy(sesion, company_id=mundo.company_a, policy_code=codigo,
                                effective_from=date(2020, 1, 1), actor="qa")

    _, segundo = carrera(mundo.factory, alta, alta)
    assert isinstance(segundo, ConflictError), f"quien perdió recibió {segundo!r}"
    assert segundo.code == "RATE_POLICY_VERSION_CONFLICT"


def test_corregir_dos_veces_la_misma_tasa_original_no_da_un_500(mundo):
    """Sin concurrencia: la segunda corrección de la original chocaba siempre."""
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        obs = rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code, rate="100.00",
                               effective_at=date.today(), actor="qa")
        db.flush()
        rz.correct_rate(db, company_id=mundo.company_a, observation_id=str(obs.id),
                        rate="110.00", reason="Primera corrección", actor="qa")
        db.flush()
        with pytest.raises(ConflictError) as exc:
            rz.correct_rate(db, company_id=mundo.company_a, observation_id=str(obs.id),
                            rate="120.00", reason="Otra vez sobre la original", actor="qa")
        assert exc.value.code == "RATE_ALREADY_SUPERSEDED"
    finally:
        db.close()


def test_dos_correcciones_simultaneas_de_la_misma_tasa_no_dan_un_500(mundo):
    from tests.concurrency import carrera

    preparar = mundo.factory()
    try:
        _politica(preparar, mundo)
        base = _moneda(preparar, mundo.company_a, _codigo())
        quote = _moneda(preparar, mundo.company_a, rz.moneda_funcional(preparar, mundo.company_a))
        obs = rz.register_rate(preparar, company_id=mundo.company_a, base_code=base.code,
                               quote_code=quote.code, rate="100.00",
                               effective_at=date.today(), actor="qa")
        preparar.commit()
        obs_id = str(obs.id)
    finally:
        preparar.close()

    def corregir(sesion):
        return rz.correct_rate(sesion, company_id=mundo.company_a, observation_id=obs_id,
                               rate="130.00", reason="Carrera de correcciones", actor="qa")

    _, segundo = carrera(mundo.factory, corregir, corregir)
    assert isinstance(segundo, ConflictError), f"quien perdió recibió {segundo!r}"
    assert segundo.code == "RATE_ALREADY_SUPERSEDED"


def test_el_universo_de_tasas_se_recorre_entero_por_paginas(mundo):
    """237 observaciones: la última página también existe.

    Es el defecto del selector de almacén de la 031 y del de clientes de la 037,
    trasladado aquí antes de que ocurra: un tope inventado deja fuera lo que no
    cabe, y nada avisa.
    """
    db = mundo.factory()
    try:
        _politica(db, mundo)
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        for i in range(237):
            rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                             quote_code=quote.code, rate=Decimal("100") + Decimal(i),
                             effective_at=datetime.now(UTC) - timedelta(hours=i + 1),
                             source_id=str(fuente.id), actor="qa")
        db.commit()

        from sqlalchemy import func, select
        total = db.execute(select(func.count()).select_from(ExchangeRate).where(
            ExchangeRate.company_id == mundo.company_a,
            ExchangeRate.source_id == str(fuente.id))).scalar()
        assert total == 237

        vistas: set[str] = set()
        pagina, tam = 1, 100
        while True:
            filas = db.execute(
                select(ExchangeRate).where(
                    ExchangeRate.company_id == mundo.company_a,
                    ExchangeRate.source_id == str(fuente.id))
                .order_by(ExchangeRate.effective_at.desc(), ExchangeRate.id)
                .limit(tam).offset((pagina - 1) * tam)).scalars().all()
            if not filas:
                break
            vistas.update(str(f.id) for f in filas)
            pagina += 1
        assert len(vistas) == 237, "el recorrido por páginas perdió observaciones"
    finally:
        db.close()


# =========================================================================== #
# La API
# =========================================================================== #
def test_la_api_resuelve_y_dice_lo_que_significa(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        base = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        db.commit()
        base_code, fuente_id = base.code, str(fuente.id)
    finally:
        db.close()

    r = mundo.post("/treasury/exchange-rates/observations", "admin", mundo.company_a,
                   {"base_currency": base_code, "quote_currency": funcional,
                    "rate": "100.000000",
                    "effective_at": datetime.now(UTC).isoformat(),
                    "source_id": fuente_id})
    assert r.status_code == 200, r.text
    assert r.json()["base_currency"] == base_code

    q = mundo.get(f"/treasury/exchange-rates/resolve?base_currency={base_code}"
                  f"&quote_currency={funcional}", "admin", mundo.company_a)
    assert q.status_code == 200, q.text
    cuerpo = q.json()
    assert Decimal(cuerpo["rate"]) == Decimal("100.000000")
    assert cuerpo["meaning"] == f"1 {base_code} = 100.000000 {funcional}"
    assert cuerpo["derived"] is None
    assert cuerpo["observation_id"]


def test_la_api_no_inventa_una_tasa_que_falta(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        a, b = _moneda(db, mundo.company_a, _codigo()), _moneda(db, mundo.company_a, _codigo())
        db.commit()
        ca, cb = a.code, b.code
    finally:
        db.close()
    r = mundo.get(f"/treasury/exchange-rates/resolve?base_currency={ca}&quote_currency={cb}",
                  "admin", mundo.company_a)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "MISSING_RATE"


def test_la_api_devuelve_la_identidad_sin_fila_de_mercado(mundo):
    db = mundo.factory()
    try:
        c = _moneda(db, mundo.company_a, _codigo())
        db.commit()
        codigo = c.code
    finally:
        db.close()
    r = mundo.get(f"/treasury/exchange-rates/resolve?base_currency={codigo}"
                  f"&quote_currency={codigo}", "admin", mundo.company_a)
    assert r.status_code == 200, r.text
    assert Decimal(r.json()["rate"]) == Decimal(1)
    assert r.json()["identity"] is True
    assert r.json()["observation_id"] is None


def test_la_api_importa_y_detalla_cada_fila_rechazada(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        buena = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        db.commit()
        codigo, fuente_id = buena.code, str(fuente.id)
    finally:
        db.close()

    hoy = date.today().isoformat()
    contenido = ("base_currency,quote_currency,rate,effective_at\n"
                 f"{codigo},{funcional},100.00,{hoy}\n"
                 f"{codigo},{funcional},0,{hoy}\n"
                 f"NOEXISTE,{funcional},10,{hoy}\n")
    r = mundo.post("/treasury/exchange-rates/import", "admin", mundo.company_a,
                   {"source_id": fuente_id, "content": contenido, "filename": "t.csv"})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["imported"] == 1 and cuerpo["rejected"] == 2
    assert {e["code"] for e in cuerpo["errors"]} == {"INVALID_RATE", "CURRENCY_INACTIVE"}

    otra = mundo.post("/treasury/exchange-rates/import", "admin", mundo.company_a,
                      {"source_id": fuente_id, "content": contenido, "filename": "t.csv"})
    assert otra.status_code == 409 and otra.json()["code"] == "IMPORT_DUPLICATE"


def test_la_api_pagina_el_historico_con_el_contrato_real(mundo):
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        base = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        for i in range(120):
            rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                             quote_code=funcional, rate=Decimal("10") + Decimal(i),
                             effective_at=datetime.now(UTC) - timedelta(hours=i + 1),
                             source_id=str(fuente.id), actor="qa")
        db.commit()
        fuente_id = str(fuente.id)
    finally:
        db.close()

    vistas: set[str] = set()
    pagina = 1
    while True:
        r = mundo.get(f"/treasury/exchange-rates/observations?source_id={fuente_id}"
                      f"&page={pagina}&page_size=100", "admin", mundo.company_a)
        assert r.status_code == 200, r.text
        cuerpo = r.json()
        assert cuerpo["page_size"] <= 100, "el tope de página se ignoró"
        if not cuerpo["items"]:
            break
        vistas.update(x["id"] for x in cuerpo["items"])
        if len(vistas) >= cuerpo["total"]:
            break
        pagina += 1
    assert len(vistas) == 120, "el recorrido por páginas dejó fuera observaciones"


def test_la_api_no_deja_ver_las_fuentes_de_otra_empresa(mundo):
    db = mundo.factory()
    try:
        propia = _fuente(db, mundo, code=f"SOLA-{uuid4().hex[:6]}")
        db.commit()
        codigo = propia.code
    finally:
        db.close()
    r = mundo.get("/treasury/rate-sources", "admin", mundo.company_b)
    assert r.status_code == 200, r.text
    assert codigo not in [f["code"] for f in r.json()["items"]]


def test_la_tasa_de_hoy_sirve_para_una_operacion_de_hoy(mundo):
    """Preguntar por un día es preguntar por el día entero.

    La tasa del día se publica a media mañana. Si la consulta se quedara en el
    comienzo del día, una tasa registrada hoy a las diez no valdría para una
    operación fechada hoy, y el sistema diría que falta una tasa que está
    delante. Es lo que pasaba, y lo encontró la prueba de punta a punta.
    """
    db = mundo.factory()
    try:
        _politica(db, mundo)
        funcional = rz.moneda_funcional(db, mundo.company_a)
        _moneda(db, mundo.company_a, funcional)
        base = _moneda(db, mundo.company_a, _codigo())
        fuente = _fuente(db, mundo)
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=funcional, rate="40.00",
                         effective_at=datetime.now(UTC), source_id=str(fuente.id), actor="qa")
        db.flush()

        # Consultando por la fecha, sin hora: tiene que encontrarla.
        r = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                            quote_code=funcional, effective_at=date.today())
        assert r.rate == Decimal("40.000000")

        # Y la tesorería, que consulta por fecha, también.
        snap = tz.capture_rate_snapshot(db, company_id=mundo.company_a,
                                        source_currency=base.code, target_currency=funcional,
                                        on_date=date.today(), actor="tesorero")
        db.flush()
        assert Decimal(str(snap.rate)) == Decimal("40.00000000")

        # Pero una tasa de mañana sigue sin valorar hoy.
        rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                         quote_code=funcional, rate="99.00",
                         effective_at=datetime.now(UTC) + timedelta(days=1),
                         source_id=str(fuente.id), actor="qa")
        db.flush()
        hoy = rz.resolve_rate(db, company_id=mundo.company_a, base_code=base.code,
                              quote_code=funcional, effective_at=date.today())
        assert hoy.rate == Decimal("40.000000"), "una tasa de mañana valoró hoy"
    finally:
        db.close()


# =========================================================================== #
# Deriva ORM ↔ migración
# =========================================================================== #
#: La unicidad y la validación de la 013, con los nombres que fija la `0056`.
_RESTRICCIONES_013 = {
    "currencies": {"uq_currencies_company_code_active"},
    "exchange_rate_sources": {"uq_rate_sources_company_code"},
    "exchange_rate_policies": {"uq_rate_policies_company_code_version"},
    "exchange_rate_import_batches": {"uq_rate_import_company_hash"},
    "exchange_rates": {"uq_exchange_rates_observation", "ix_exchange_rates_effective_at",
                       "ck_exchange_rates_rate_positive"},
}


def test_los_modelos_declaran_la_misma_unicidad_que_la_migracion():
    """Si una restricción vive solo en la migración, las pruebas no la tienen.

    Pasó en este mismo ciclo: los cinco índices únicos de la 013 estaban solo en
    la `0056`. La base que las pruebas construyen desde los modelos no los tenía,
    ninguna prueba ejerció la unicidad, y una carrera forzada insertó dos veces
    lo que en producción el índice habría rechazado. Esta guardia compara los
    dos lados por nombre.
    """
    import pathlib

    import app.main  # noqa: F401 - registra todos los modelos
    from app.core.database import Base

    migracion = (pathlib.Path(__file__).resolve().parents[1] / "alembic" / "versions"
                 / "0056_spec013_financial_masters.py").read_text()
    for tabla, esperadas in _RESTRICCIONES_013.items():
        t = Base.metadata.tables[tabla]
        declaradas = {i.name for i in t.indexes} | {c.name for c in t.constraints if c.name}
        # La convención `ck_%(table_name)s_%(constraint_name)s` antepone el
        # prefijo también al nombre ya prefijado: igual en el ORM que en Alembic.
        declaradas |= {n.replace(f"ck_{tabla}_ck_", "ck_", 1) for n in declaradas}
        for nombre in esperadas:
            assert nombre in declaradas, f"{tabla}: el modelo no declara {nombre}"
            assert nombre in migracion, f"{tabla}: la migración no crea {nombre}"


def test_la_base_de_pruebas_tiene_de_verdad_la_unicidad_de_la_013(mundo):
    """No basta con declararla: la base contra la que corren las pruebas la tiene."""
    from sqlalchemy import text

    db = mundo.factory()
    try:
        nombres = set(db.execute(text(
            "SELECT indexname FROM pg_indexes WHERE tablename = ANY(:t) "
            "UNION SELECT conname FROM pg_constraint "
            "WHERE conrelid::regclass::text = ANY(:t)"),
            {"t": list(_RESTRICCIONES_013)}).scalars().all())
    finally:
        db.close()
    nombres |= {n.replace("ck_exchange_rates_ck_", "ck_", 1) for n in nombres}
    faltan = {n for grupo in _RESTRICCIONES_013.values() for n in grupo} - nombres
    assert not faltan, f"la base de pruebas no tiene: {sorted(faltan)}"


# =========================================================================== #
# Una colisión única no es cualquier error de integridad
# =========================================================================== #
def test_el_clasificador_distingue_la_violacion_unica_de_un_check_y_de_una_foranea(mundo):
    """Con errores reales de PostgreSQL, no con dobles."""
    from sqlalchemy.exc import IntegrityError

    from app.core.integrity import es_violacion_unica

    db = mundo.factory()
    try:
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        fuente = _fuente(db, mundo)
        db.flush()

        errores = {}
        for nombre, fila in {
            "unica": lambda: rz.ExchangeRateSource(company_id=mundo.company_a, code=fuente.code,
                                                   name="repetida", status="ACTIVE"),
            "check": lambda: ExchangeRate(company_id=mundo.company_a, currency_id=str(base.id),
                                          rate_date=date.today(), rate=Decimal("0"),
                                          base_currency_id=str(base.id),
                                          quote_currency_id=str(quote.id),
                                          source_id=str(fuente.id), effective_at=datetime.now(UTC)),
            "foranea": lambda: ExchangeRate(company_id=mundo.company_a, currency_id=str(base.id),
                                            rate_date=date.today(), rate=Decimal("1"),
                                            base_currency_id=str(base.id),
                                            quote_currency_id=str(quote.id),
                                            source_id=str(uuid4()), effective_at=datetime.now(UTC)),
        }.items():
            try:
                with db.begin_nested():
                    db.add(fila())
                    db.flush()
            except IntegrityError as e:
                errores[nombre] = e
        assert set(errores) == {"unica", "check", "foranea"}, f"no se provocó: {errores}"
        assert es_violacion_unica(errores["unica"], "uq_rate_sources_company_code")
        assert not es_violacion_unica(errores["unica"], "uq_exchange_rates_observation")
        assert not es_violacion_unica(errores["check"], "uq_exchange_rates_observation")
        assert not es_violacion_unica(errores["foranea"], "uq_exchange_rates_observation")
    finally:
        db.rollback()
        db.close()


def test_registrar_no_disfraza_de_duplicado_un_error_que_no_lo_es(mundo, monkeypatch):
    """Una clave foránea rota no es «ya existe»: el error real no se esconde."""
    import types

    from sqlalchemy.exc import IntegrityError

    db = mundo.factory()
    try:
        base = _moneda(db, mundo.company_a, _codigo())
        quote = _moneda(db, mundo.company_a, rz.moneda_funcional(db, mundo.company_a))
        db.flush()
        fantasma = types.SimpleNamespace(id=str(uuid4()), code="FANTASMA", status="ACTIVE",
                                         allows_manual=True)
        monkeypatch.setattr(rz, "_exigir_fuente", lambda *_a, **_k: fantasma)
        with pytest.raises(IntegrityError):
            rz.register_rate(db, company_id=mundo.company_a, base_code=base.code,
                             quote_code=quote.code, rate="10.00", effective_at=date.today(),
                             source_id=fantasma.id, actor="qa")
    finally:
        db.rollback()
        db.close()


def test_la_fuente_conserva_y_devuelve_su_identidad_entera(mundo):
    """FR-013-004: una fuente es algo más que su código.

    La verificación de trazabilidad del cierre encontró que ninguna prueba
    comprobaba que la autoridad, el proveedor, la admisión de carga manual, la
    prioridad y la vigencia se guardan y se devuelven. La prioridad decide qué
    fuente gana; si se perdiera por el camino, el desempate volvería a ser el
    orden de la tabla sin que nada lo dijera.
    """
    codigo = f"IDF-{uuid4().hex[:6]}"
    esperado = {"name": "Banco Central (prueba)", "source_type": "OFFICIAL",
                "authority_reference": "Pendiente de validación legal (D0-07)",
                "provider_code": "PROV-X", "allows_manual": False, "priority": 7,
                "effective_from": "2026-01-01", "status": "ACTIVE"}
    cuerpo = {k: v for k, v in esperado.items() if k != "status"}
    r = mundo.post("/treasury/rate-sources", "admin", mundo.company_a, {"code": codigo, **cuerpo})
    assert r.status_code == 200, r.text
    listado = mundo.get("/treasury/rate-sources", "admin", mundo.company_a)
    assert listado.status_code == 200, listado.text
    guardada = next(f for f in listado.json()["items"] if f["code"] == codigo)
    for campo, valor in esperado.items():
        assert r.json()[campo] == valor, f"la respuesta del alta perdió {campo}"
        assert guardada[campo] == valor, f"lo guardado perdió {campo}"
