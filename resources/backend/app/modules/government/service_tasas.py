"""Servicio de tasas oficiales BCV (TRE-09)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentLink, DocumentVersion
from app.modules.government.models import (
    ESTADOS_TASA,
    MONEDAS_TASA,
    GovernmentOfficialExchangeRate,
)
from app.modules.government.monedas import canonical_currency
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_sod import usuarios_equivalentes
from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from app.shared.clock import instante_actual

ENTIDAD = "GovernmentOfficialExchangeRate"


def _auditar(db: Session, ctx: CompanyContext, tasa: GovernmentOfficialExchangeRate, accion: str, after: dict[str, Any]) -> None:
    record_audit(
        db,
        action=accion,
        entity_type=ENTIDAD,
        entity_id=str(tasa.id),
        tenant_id=ctx.tenant_id,
        company_id=ctx.company_id,
        user_id=ctx.user_id,
        after=after,
    )


def _tasa(
    db: Session,
    ctx: CompanyContext,
    tasa_id: str,
    bloquear: bool = False,
) -> GovernmentOfficialExchangeRate:
    stmt = select(GovernmentOfficialExchangeRate).where(
        GovernmentOfficialExchangeRate.company_id == ctx.company_id,
        GovernmentOfficialExchangeRate.id == tasa_id,
    )
    if bloquear:
        stmt = stmt.with_for_update()
    tasa = db.execute(stmt).scalar_one_or_none()
    if tasa is None:
        raise NotFoundError("GOV_OFFICIAL_RATE_NOT_FOUND", "La tasa oficial no existe")
    return tasa


def _salida(tasa: GovernmentOfficialExchangeRate, nombres: dict[str, str]) -> dict[str, Any]:
    return {
        "id": str(tasa.id),
        "moneda": tasa.moneda,
        "moneda_cotizacion": tasa.moneda_cotizacion,
        "fecha_efectiva": tasa.fecha_efectiva.isoformat(),
        "valor": str(tasa.valor),
        "fuente": tasa.fuente,
        "fuente_referencia": tasa.fuente_referencia,
        "publicada_en": tasa.publicada_en.isoformat() if tasa.publicada_en else None,
        "estado": tasa.estado,
        "version": tasa.version,
        "sustituye_id": str(tasa.sustituye_id) if tasa.sustituye_id else None,
        "motivo_correccion": tasa.motivo_correccion,
        "capturada_por": nombres.get(tasa.capturada_por or "", ""),
        "capturada_en": tasa.capturada_en,
        "aprobada_por": nombres.get(tasa.aprobada_por or "", "") if tasa.aprobada_por else None,
        "aprobada_en": tasa.aprobada_en,
        "evidencia_documento_id": str(tasa.evidencia_documento_id) if tasa.evidencia_documento_id else None,
        "evidencia_sha256": tasa.evidencia_sha256,
        "sustituida_en": tasa.sustituida_en,
        "anulada_por": nombres.get(tasa.anulada_por or "", "") if tasa.anulada_por else None,
        "anulada_en": tasa.anulada_en,
        "motivo_anulacion": tasa.motivo_anulacion,
    }


def _hay(
    db: Session,
    ctx: CompanyContext,
    moneda: str,
    fecha: date,
    estado: str,
) -> bool:
    stmt = select(GovernmentOfficialExchangeRate.id).where(
        GovernmentOfficialExchangeRate.company_id == ctx.company_id,
        GovernmentOfficialExchangeRate.moneda == moneda,
        GovernmentOfficialExchangeRate.fecha_efectiva == fecha,
        GovernmentOfficialExchangeRate.estado == estado,
    )
    return db.execute(stmt).scalar_one_or_none() is not None


def listar(
    db: Session,
    ctx: CompanyContext,
    moneda: str | None = None,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
) -> dict[str, Any]:
    stmt = select(GovernmentOfficialExchangeRate).where(
        GovernmentOfficialExchangeRate.company_id == ctx.company_id
    )
    if moneda:
        stmt = stmt.where(GovernmentOfficialExchangeRate.moneda == moneda)
    if estado:
        stmt = stmt.where(GovernmentOfficialExchangeRate.estado == estado)
    if desde:
        stmt = stmt.where(GovernmentOfficialExchangeRate.fecha_efectiva >= desde)
    if hasta:
        stmt = stmt.where(GovernmentOfficialExchangeRate.fecha_efectiva <= hasta)
    stmt = stmt.order_by(
        GovernmentOfficialExchangeRate.fecha_efectiva.desc(),
        GovernmentOfficialExchangeRate.moneda,
        GovernmentOfficialExchangeRate.version.desc(),
    )
    tasas = db.execute(stmt).scalars().all()
    ids: set[str] = set()
    for tasa in tasas:
        if tasa.capturada_por:
            ids.add(tasa.capturada_por)
        if tasa.aprobada_por:
            ids.add(tasa.aprobada_por)
        if tasa.anulada_por:
            ids.add(tasa.anulada_por)
    nombres = _usuarios_por_ids(db, ids, ctx.tenant_id)
    return {
        "items": [_salida(tasa, nombres) for tasa in tasas],
        "monedas": list(MONEDAS_TASA),
        "estados": list(ESTADOS_TASA),
    }


def detalle(db: Session, ctx: CompanyContext, tasa_id: str) -> dict[str, Any]:
    tasa = _tasa(db, ctx, tasa_id)
    stmt = select(GovernmentOfficialExchangeRate).where(
        GovernmentOfficialExchangeRate.company_id == ctx.company_id,
        GovernmentOfficialExchangeRate.moneda == tasa.moneda,
        GovernmentOfficialExchangeRate.fecha_efectiva == tasa.fecha_efectiva,
    ).order_by(GovernmentOfficialExchangeRate.version)
    historial = db.execute(stmt).scalars().all()
    ids: set[str] = set()
    for item in historial:
        if item.capturada_por:
            ids.add(item.capturada_por)
        if item.aprobada_por:
            ids.add(item.aprobada_por)
        if item.anulada_por:
            ids.add(item.anulada_por)
    nombres = _usuarios_por_ids(db, ids, ctx.tenant_id)
    salida = _salida(tasa, nombres)
    salida["historia"] = [_salida(item, nombres) for item in historial]
    return salida


def crear(
    db: Session,
    ctx: CompanyContext,
    user: User,
    datos: dict[str, Any],
) -> dict[str, Any]:
    moneda = datos["moneda"]
    fecha = datos["fecha_efectiva"]
    if _hay(db, ctx, moneda, fecha, "BORRADOR"):
        raise ConflictError(
            "GOV_OFFICIAL_RATE_DRAFT_EXISTS",
            "Ya hay una tasa en borrador para esa moneda y fecha",
        )
    if _hay(db, ctx, moneda, fecha, "APROBADA"):
        raise ConflictError(
            "GOV_OFFICIAL_RATE_ALREADY_APPROVED",
            "Ya hay una tasa aprobada para esa moneda y fecha: corríjala con una nueva versión",
        )
    ahora = instante_actual()
    tasa = GovernmentOfficialExchangeRate(
        company_id=ctx.company_id,
        moneda=moneda,
        moneda_cotizacion="VES",
        fecha_efectiva=fecha,
        valor=Decimal(str(datos["valor"])),
        fuente="BCV",
        fuente_referencia=datos["fuente_referencia"],
        publicada_en=datos.get("publicada_en"),
        estado="BORRADOR",
        version=1,
        capturada_por=str(user.id),
        capturada_en=ahora,
        created_by=ctx.user_id,
    )
    db.add(tasa)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_OFFICIAL_RATE_CONFLICT",
            "Otra tasa de la misma moneda y fecha se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _auditar(
        db,
        ctx,
        tasa,
        "GOV_OFFICIAL_RATE_CREATED",
        {
            "fecha_efectiva": tasa.fecha_efectiva.isoformat(),
            "fuente_referencia": tasa.fuente_referencia,
            "moneda": tasa.moneda,
            "valor": str(tasa.valor),
            "version": tasa.version,
        },
    )
    return detalle(db, ctx, str(tasa.id))


def corregir(
    db: Session,
    ctx: CompanyContext,
    user: User,
    tasa_id: str,
    datos: dict[str, Any],
) -> dict[str, Any]:
    anterior = _tasa(db, ctx, tasa_id, bloquear=True)
    if anterior.estado != "APROBADA":
        raise ConflictError(
            "GOV_OFFICIAL_RATE_NOT_APPROVED",
            "Solo se corrige una tasa aprobada",
        )
    if _hay(db, ctx, anterior.moneda, anterior.fecha_efectiva, "BORRADOR"):
        raise ConflictError(
            "GOV_OFFICIAL_RATE_DRAFT_EXISTS",
            "Ya hay una tasa en borrador para esa moneda y fecha",
        )
    if datos.get("publicada_en") and datos["publicada_en"] > anterior.fecha_efectiva:
        raise KontrolError(
            code="GOV_OFFICIAL_RATE_INVALID",
            message="La fecha de publicación no puede ser posterior a la fecha efectiva",
            field_errors={"publicada_en": ["La fecha de publicación no puede ser posterior a la fecha efectiva"]},
            status_code=422,
        )
    ahora = instante_actual()
    tasa = GovernmentOfficialExchangeRate(
        company_id=ctx.company_id,
        moneda=anterior.moneda,
        moneda_cotizacion="VES",
        fecha_efectiva=anterior.fecha_efectiva,
        valor=Decimal(str(datos["valor"])),
        fuente="BCV",
        fuente_referencia=datos["fuente_referencia"],
        publicada_en=datos.get("publicada_en"),
        estado="BORRADOR",
        version=anterior.version + 1,
        sustituye_id=anterior.id,
        motivo_correccion=datos["motivo"],
        capturada_por=str(user.id),
        capturada_en=ahora,
        created_by=ctx.user_id,
    )
    db.add(tasa)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_OFFICIAL_RATE_CONFLICT",
            "Otra tasa de la misma moneda y fecha se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    _auditar(
        db,
        ctx,
        tasa,
        "GOV_OFFICIAL_RATE_CREATED",
        {
            "fecha_efectiva": tasa.fecha_efectiva.isoformat(),
            "fuente_referencia": tasa.fuente_referencia,
            "moneda": tasa.moneda,
            "valor": str(tasa.valor),
            "version": tasa.version,
        },
    )
    return detalle(db, ctx, str(tasa.id))


def _evidencia(
    db: Session,
    ctx: CompanyContext,
    tasa_id: str,
) -> tuple[str, str] | None:
    stmt = (
        select(Document, DocumentLink)
        .join(DocumentLink, DocumentLink.document_id == Document.id)
        .where(
            DocumentLink.resource_type == ENTIDAD,
            DocumentLink.resource_id == tasa_id,
            DocumentLink.company_id == ctx.company_id,
            Document.company_id == ctx.company_id,
            Document.status == "ACTIVE",
        )
        .order_by(DocumentLink.created_at.desc())
    )
    filas = db.execute(stmt).all()
    vistos: set[str] = set()
    for documento, _link in filas:
        if str(documento.id) in vistos:
            continue
        vistos.add(str(documento.id))
        version = db.get(DocumentVersion, documento.current_version_id) if documento.current_version_id else None
        if version is not None and version.sha256:
            return str(documento.id), version.sha256
    return None


def aprobar(
    db: Session,
    ctx: CompanyContext,
    user: User,
    tasa_id: str,
) -> dict[str, Any]:
    tasa = _tasa(db, ctx, tasa_id, bloquear=True)
    if tasa.estado != "BORRADOR":
        raise ConflictError(
            "GOV_OFFICIAL_RATE_NOT_DRAFT",
            "La tasa ya no está en borrador",
        )
    if tasa.capturada_por in usuarios_equivalentes(db, ctx, str(user.id)):
        raise ConflictError(
            "GOV_OFFICIAL_RATE_MAKER_CHECKER",
            "Quien captura una tasa no puede aprobarla: debe aprobarla otro usuario",
            details={"regla": "Quien captura no aprueba"},
        )
    evidencia = _evidencia(db, ctx, tasa_id)
    if evidencia is None:
        raise KontrolError(
            code="GOV_OFFICIAL_RATE_EVIDENCE_REQUIRED",
            message="Adjunte la evidencia oficial del BCV (documento) antes de aprobar la tasa",
            status_code=422,
        )
    evidencia_id, evidencia_sha = evidencia
    ahora = instante_actual()
    if tasa.sustituye_id:
        anterior = _tasa(db, ctx, str(tasa.sustituye_id), bloquear=True)
        if anterior.estado != "APROBADA":
            raise ConflictError(
                "GOV_OFFICIAL_RATE_CONFLICT",
                "La tasa que se corrige ya no está aprobada",
            )
        anterior.estado = "SUSTITUIDA"
        anterior.sustituida_en = ahora
        db.flush()
    else:
        if _hay(db, ctx, tasa.moneda, tasa.fecha_efectiva, "APROBADA"):
            raise ConflictError(
                "GOV_OFFICIAL_RATE_ALREADY_APPROVED",
                "Ya hay una tasa aprobada para esa moneda y fecha: corríjala con una nueva versión",
            )
    tasa.estado = "APROBADA"
    tasa.aprobada_por = str(user.id)
    tasa.aprobada_en = ahora
    tasa.evidencia_documento_id = evidencia_id
    tasa.evidencia_sha256 = evidencia_sha
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError(
            "GOV_OFFICIAL_RATE_CONFLICT",
            "Otra tasa de la misma moneda y fecha se registró al mismo tiempo; vuelva a intentarlo",
        ) from None
    if tasa.sustituye_id:
        anterior = _tasa(db, ctx, str(tasa.sustituye_id), bloquear=True)
        _auditar(
            db,
            ctx,
            anterior,
            "GOV_OFFICIAL_RATE_SUPERSEDED",
            {
                "fecha_efectiva": anterior.fecha_efectiva.isoformat(),
                "moneda": anterior.moneda,
                "sustituida_por": f"versión {tasa.version}",
                "valor": str(anterior.valor),
                "version": anterior.version,
            },
        )
    _auditar(
        db,
        ctx,
        tasa,
        "GOV_OFFICIAL_RATE_APPROVED",
        {
            "evidencia_sha256": tasa.evidencia_sha256,
            "fecha_efectiva": tasa.fecha_efectiva.isoformat(),
            "moneda": tasa.moneda,
            "valor": str(tasa.valor),
            "version": tasa.version,
        },
    )
    return detalle(db, ctx, str(tasa.id))


def anular(
    db: Session,
    ctx: CompanyContext,
    user: User,
    tasa_id: str,
    datos: dict[str, Any],
) -> dict[str, Any]:
    tasa = _tasa(db, ctx, tasa_id, bloquear=True)
    if tasa.estado not in ("BORRADOR", "APROBADA"):
        raise ConflictError(
            "GOV_OFFICIAL_RATE_NOT_ACTIVE",
            "La tasa ya está anulada o sustituida",
        )
    ahora = instante_actual()
    tasa.estado = "ANULADA"
    tasa.anulada_por = str(user.id)
    tasa.anulada_en = ahora
    tasa.motivo_anulacion = datos["motivo"].strip()
    db.flush()
    _auditar(
        db,
        ctx,
        tasa,
        "GOV_OFFICIAL_RATE_ANNULLED",
        {
            "fecha_efectiva": tasa.fecha_efectiva.isoformat(),
            "moneda": tasa.moneda,
            "motivo": tasa.motivo_anulacion,
            "valor": str(tasa.valor),
            "version": tasa.version,
        },
    )
    return detalle(db, ctx, str(tasa.id))


def tasa_aplicable(
    db: Session,
    ctx: CompanyContext,
    moneda: str,
    fecha: date,
    bloquear: bool = False,
) -> GovernmentOfficialExchangeRate | None:
    stmt = (
        select(GovernmentOfficialExchangeRate)
        .where(
            GovernmentOfficialExchangeRate.company_id == ctx.company_id,
            GovernmentOfficialExchangeRate.moneda == moneda,
            GovernmentOfficialExchangeRate.estado == "APROBADA",
            GovernmentOfficialExchangeRate.fecha_efectiva <= fecha,
        )
        .order_by(GovernmentOfficialExchangeRate.fecha_efectiva.desc())
        .limit(1)
    )
    if bloquear:
        stmt = stmt.with_for_update(read=True)
    resultado = db.execute(stmt).scalar_one_or_none()
    if resultado is None and bloquear:
        # Con READ COMMITTED, una corrección aprobada de forma concurrente puede
        # sustituir la fila bloqueada mientras esta sentencia esperaba; al reevaluar
        # el WHERE la fila antigua se descarta y la nueva aún no está en la instantánea.
        # Una segunda sentencia toma una instantánea nueva y ve la tasa ya aprobada.
        resultado = db.execute(stmt).scalar_one_or_none()
    return resultado


def instantanea_tasa(t: GovernmentOfficialExchangeRate) -> dict[str, Any]:
    return {
        "tasa_id": str(t.id),
        "moneda": t.moneda,
        "moneda_cotizacion": t.moneda_cotizacion,
        "fecha_efectiva": t.fecha_efectiva.isoformat(),
        "valor": str(t.valor),
        "fuente": t.fuente,
        "fuente_referencia": t.fuente_referencia,
        "version": t.version,
        "evidencia_sha256": t.evidencia_sha256,
    }


def verificar_limite(
    db: Session,
    ctx: CompanyContext,
    moneda_operacion: str,
    total: Decimal,
    limite_monto: Decimal,
    limite_moneda: str,
    fecha: date,
    *,
    bloquear: bool,
    exigir: bool,
) -> dict[str, Any]:
    op = canonical_currency(moneda_operacion)
    lim = canonical_currency(limite_moneda)
    base: dict[str, Any] = {
        "requiere_conversion": op != lim,
        "moneda_operacion": op,
        "moneda_limite": lim,
        "fecha": fecha.isoformat(),
        "tasas": [],
        "total": str(total),
        "limite": str(limite_monto),
        "total_ves": None,
        "limite_ves": None,
        "dentro_del_limite": False,
        "resultado": "",
        "monedas_sin_tasa": [],
    }
    if op == lim:
        base["requiere_conversion"] = False
        base["dentro_del_limite"] = total <= limite_monto
        base["resultado"] = "DENTRO_DEL_LIMITE" if base["dentro_del_limite"] else "EXCEDE_LIMITE"
        return base

    base["requiere_conversion"] = True
    faltantes: list[str] = []
    tasas_dict: dict[str, GovernmentOfficialExchangeRate] = {}
    for m in (op, lim):
        if m == "VES":
            continue
        t = tasa_aplicable(db, ctx, m, fecha, bloquear)
        if t is None:
            faltantes.append(m)
        else:
            tasas_dict[m] = t

    if faltantes:
        mensaje = (
            f"No hay tasa oficial BCV aprobada aplicable al {fecha:%d/%m/%Y} para {', '.join(faltantes)}: "
            f"el límite está en {lim} y la operación en {op}. Registre y apruebe la tasa en Tesorería → Tasas oficiales."
        )
        if exigir:
            raise KontrolError(
                code="GOV_OFFICIAL_RATE_REQUIRED",
                message=mensaje,
                details={
                    "moneda_operacion": op,
                    "moneda_limite": lim,
                    "fecha": fecha.isoformat(),
                    "monedas_sin_tasa": faltantes,
                },
                field_errors={"autoridad_cargo_id": [mensaje]},
                status_code=422,
            )
        base["resultado"] = "SIN_TASA"
        base["dentro_del_limite"] = False
        base["monedas_sin_tasa"] = faltantes
        return base

    def r(m: str) -> Decimal:
        if m == "VES":
            return Decimal("1")
        return tasas_dict[m].valor

    total_ves = total * r(op)
    limite_ves = limite_monto * r(lim)
    tasas_ordenadas = [tasas_dict[m] for m in (op, lim) if m != "VES"]
    base["tasas"] = [instantanea_tasa(t) for t in tasas_ordenadas]
    base["total_ves"] = str(total_ves)
    base["limite_ves"] = str(limite_ves)
    base["dentro_del_limite"] = total_ves <= limite_ves
    base["resultado"] = "DENTRO_DEL_LIMITE" if base["dentro_del_limite"] else "EXCEDE_LIMITE"
    return base
