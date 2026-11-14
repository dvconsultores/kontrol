from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.documents.models import Document, DocumentVersion
from app.modules.documents.service import documento_sellado
from app.modules.government.models import (
    MONEDAS_LIMITE,
    GovernmentProcurementFile,
    GovernmentProcurementOffer,
    GovernmentProcurementOfferAmount,
    GovernmentProcurementOfferDocument,
    GovernmentProcurementOpening,
    GovernmentProcurementOpeningOffer,
)
from app.modules.government.schemas_ofertas import MontoEntrada
from app.modules.government.service_auditoria import _usuarios_por_ids
from app.modules.government.service_expedientes import _abierto, _auditar, _evento, _para_escribir
from app.shared.clock import hoy_de_negocio, instante_actual

_ETIQUETAS_SOPORTE = {
    "DOCUMENTO_OFERTA": "Documento de la oferta",
    "ACTA_APERTURA": "Acta de apertura",
}
_ETIQUETAS_ESTADO = {
    "DECLARADO": "Declarado",
    "NO_DECLARADO": "No declarado",
    "SELLADO": "Sellada: el monto se registra después de la apertura",
    "NO_APLICA": "No aplica: el sobre de calificación no lleva precio",
}


def _referencia(numero: int) -> str:
    return f"R-{numero:04d}"


def _texto(valor: Decimal) -> str:
    return f"{Decimal(valor):.2f}"


def _inv(campo: str, mensaje: str) -> KontrolError:
    return KontrolError(
        code="GOV_OFFER_AMOUNT_INVALID",
        message="Datos del monto inválidos",
        field_errors={campo: [mensaje]},
        status_code=422,
    )


def _abierta(db: Session, ctx: CompanyContext, offer: GovernmentProcurementOffer) -> GovernmentProcurementOpening | None:
    fila = db.scalar(
        select(GovernmentProcurementOpeningOffer).where(
            GovernmentProcurementOpeningOffer.offer_id == offer.id,
            GovernmentProcurementOpeningOffer.company_id == ctx.company_id,
        )
    )
    if fila is None:
        return None
    return db.get(GovernmentProcurementOpening, fila.opening_id)


def _versiones(db: Session, ctx: CompanyContext, offer: GovernmentProcurementOffer) -> list[GovernmentProcurementOfferAmount]:
    return list(
        db.scalars(
            select(GovernmentProcurementOfferAmount)
            .where(
                GovernmentProcurementOfferAmount.company_id == ctx.company_id,
                GovernmentProcurementOfferAmount.offer_id == offer.id,
            )
            .order_by(GovernmentProcurementOfferAmount.version.desc())
        ).all()
    )


def _bloqueo(offer: GovernmentProcurementOffer, expediente: GovernmentProcurementFile, opening: GovernmentProcurementOpening | None) -> str | None:
    if offer.tipo_sobre == "CALIFICACION":
        return "No aplica: el sobre de calificación no lleva precio"
    if offer.confidencial and opening is None:
        return "El monto de una oferta sellada se registra después de la apertura"
    if expediente.status != "ABIERTO":
        return "El expediente no está en curso"
    if expediente.evaluacion_concluida_en is not None:
        return "La evaluación está concluida: el monto ya no se registra ni se corrige"
    return None


def _estado(offer: GovernmentProcurementOffer, opening: GovernmentProcurementOpening | None, vigente: GovernmentProcurementOfferAmount | None) -> str:
    if offer.tipo_sobre == "CALIFICACION":
        return "NO_APLICA"
    if vigente is not None:
        return "DECLARADO"
    if offer.confidencial and opening is None:
        return "SELLADO"
    return "NO_DECLARADO"


def _salida_monto(db: Session, ctx: CompanyContext, fila: GovernmentProcurementOfferAmount) -> dict[str, Any]:
    diferencia = fila.total_con_tributos - (fila.monto_sin_iva + fila.tributos)
    doc = db.get(Document, fila.soporte_document_id)
    ver = db.get(DocumentVersion, fila.soporte_version_id)
    return {
        "version": fila.version,
        "moneda": fila.moneda,
        "monto_sin_iva": _texto(fila.monto_sin_iva),
        "tributos": _texto(fila.tributos),
        "total_con_tributos": _texto(fila.total_con_tributos),
        "suma_coincide": diferencia == 0,
        "diferencia": _texto(diferencia),
        "soporte_tipo": fila.soporte_tipo,
        "soporte_etiqueta": _ETIQUETAS_SOPORTE[fila.soporte_tipo],
        "soporte_titulo": doc.title if doc else None,
        "soporte_version": ver.version_number if ver else 0,
        "soporte_huella": fila.soporte_sha256,
        "motivo": fila.motivo,
        "registrada_por": _usuarios_por_ids(db, [fila.registrada_por], ctx.tenant_id).get(fila.registrada_por),
        "registrada_en": fila.registrada_en,
    }


def _soportes(db: Session, ctx: CompanyContext, offer: GovernmentProcurementOffer, opening: GovernmentProcurementOpening | None) -> list[dict[str, Any]]:
    resultado: list[dict[str, Any]] = []
    filas = db.scalars(
        select(GovernmentProcurementOfferDocument)
        .where(
            GovernmentProcurementOfferDocument.company_id == ctx.company_id,
            GovernmentProcurementOfferDocument.offer_id == offer.id,
        )
        .order_by(GovernmentProcurementOfferDocument.created_at)
    ).all()
    for row in filas:
        if documento_sellado(db, row.document_id):
            continue
        doc = db.get(Document, row.document_id)
        resultado.append(
            {
                "tipo": "DOCUMENTO_OFERTA",
                "etiqueta": _ETIQUETAS_SOPORTE["DOCUMENTO_OFERTA"],
                "documento_id": row.document_id,
                "titulo": doc.title if doc else None,
                "version": row.version_numero,
                "_version_id": row.document_version_id,
                "_sha256": row.sha256,
            }
        )
    if opening is not None:
        doc = db.get(Document, opening.acta_document_id)
        ver = db.get(DocumentVersion, opening.acta_version_id)
        resultado.append(
            {
                "tipo": "ACTA_APERTURA",
                "etiqueta": _ETIQUETAS_SOPORTE["ACTA_APERTURA"],
                "documento_id": opening.acta_document_id,
                "titulo": doc.title if doc else None,
                "version": ver.version_number if ver else 0,
                "_version_id": opening.acta_version_id,
                "_sha256": opening.acta_sha256,
            }
        )
    return resultado


def resumen_monto(db: Session, ctx: CompanyContext, offer: GovernmentProcurementOffer, *, abierta: bool) -> dict[str, Any]:
    expediente = db.get(GovernmentProcurementFile, offer.file_id)
    if expediente is None:
        raise NotFoundError(code="GOV_PROCUREMENT_FILE_NOT_FOUND", message="Expediente no encontrado")
    opening = _abierta(db, ctx, offer)
    versiones = _versiones(db, ctx, offer)
    vigente = versiones[0] if versiones else None
    estado = _estado(offer, opening, vigente)
    return {
        "monto_estado": estado,
        "monto_estado_etiqueta": _ETIQUETAS_ESTADO[estado],
        "monto": _salida_monto(db, ctx, vigente) if vigente else None,
        "monto_bloqueo": _bloqueo(offer, expediente, opening),
    }


def detalle_monto(db: Session, ctx: CompanyContext, offer: GovernmentProcurementOffer, *, abierta: bool) -> dict[str, Any]:
    versiones = _versiones(db, ctx, offer)
    opening = _abierta(db, ctx, offer)
    soportes = []
    for soporte in _soportes(db, ctx, offer, opening):
        publico = {k: v for k, v in soporte.items() if not k.startswith("_")}
        soportes.append(publico)
    return {
        "montos_historial": [_salida_monto(db, ctx, f) for f in versiones],
        "soportes_monto": soportes,
    }


def declarar_monto(db: Session, ctx: CompanyContext, expediente_id: str, oferta_id: str, entrada: MontoEntrada, version: int | None) -> None:
    expediente = _para_escribir(db, ctx, expediente_id, version)
    offer = db.scalar(
        select(GovernmentProcurementOffer).where(
            GovernmentProcurementOffer.id == oferta_id,
            GovernmentProcurementOffer.company_id == ctx.company_id,
            GovernmentProcurementOffer.file_id == expediente.id,
        )
    )
    if offer is None:
        raise NotFoundError(code="GOV_PROCUREMENT_OFFER_NOT_FOUND", message="Oferta no encontrada")
    _abierto(expediente)
    if offer.tipo_sobre == "CALIFICACION":
        raise KontrolError(code="GOV_OFFER_AMOUNT_NOT_APPLICABLE", message="El sobre de calificación no lleva precio", status_code=422)
    opening = _abierta(db, ctx, offer)
    if offer.confidencial and opening is None:
        raise ConflictError("GOV_OFFER_AMOUNT_SEALED", "El monto de una oferta sellada se registra después de la apertura")
    if expediente.evaluacion_concluida_en is not None:
        raise ConflictError("GOV_OFFER_AMOUNT_CLOSED", "La evaluación está concluida: el monto ya no se registra ni se corrige")
    if entrada.moneda not in MONEDAS_LIMITE:
        raise _inv("moneda", "Moneda inválida")
    soportes = _soportes(db, ctx, offer, opening)
    soporte = next(
        (s for s in soportes if s["tipo"] == entrada.soporte_tipo and s["documento_id"] == entrada.soporte_documento_id),
        None,
    )
    if soporte is None:
        raise _inv("soporte_documento_id", "El soporte debe ser un documento de esta oferta o el acta de su apertura")
    versiones = _versiones(db, ctx, offer)
    vigente = versiones[0] if versiones else None
    if vigente is None:
        if entrada.version_anterior is not None:
            raise ConflictError("GOV_OFFER_AMOUNT_STALE", "El monto cambió; recargue la oferta")
        motivo = None
        numero = 1
        reemplaza = None
    else:
        if entrada.version_anterior != vigente.version:
            raise ConflictError("GOV_OFFER_AMOUNT_STALE", "El monto cambió; recargue la oferta")
        motivo = (entrada.motivo or "").strip()
        if len(motivo) < 10:
            raise _inv("motivo", "Explique la corrección (mínimo 10 caracteres)")
        numero = vigente.version + 1
        reemplaza = vigente.id
    fila = GovernmentProcurementOfferAmount(
        company_id=ctx.company_id,
        offer_id=offer.id,
        version=numero,
        moneda=entrada.moneda,
        monto_sin_iva=entrada.monto_sin_iva,
        tributos=entrada.tributos,
        total_con_tributos=entrada.total_con_tributos,
        soporte_tipo=soporte["tipo"],
        soporte_document_id=soporte["documento_id"],
        soporte_version_id=soporte["_version_id"],
        soporte_sha256=soporte["_sha256"],
        motivo=motivo,
        reemplaza_id=reemplaza,
        registrada_por=ctx.user_id,
        registrada_en=instante_actual(),
        created_by=ctx.user_id,
    )
    db.add(fila)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("GOV_OFFER_AMOUNT_STALE", "El monto cambió; recargue la oferta") from None
    expediente.version += 1
    db.flush()
    accion = "declarado" if numero == 1 else "corregido"
    _evento(db, ctx, expediente, "OFERTA", hoy_de_negocio(), f"Monto {accion} {_referencia(offer.numero)}", detalle=f"Versión {numero} · {entrada.moneda}")
    _auditar(
        db,
        ctx,
        "GOV_PROCUREMENT_OFFER_AMOUNT_DECLARED" if numero == 1 else "GOV_PROCUREMENT_OFFER_AMOUNT_CORRECTED",
        expediente_id=str(expediente.id),
        after={"referencia": _referencia(offer.numero), "numero": numero, "moneda": entrada.moneda, "version": expediente.version},
        motivo=motivo,
    )
