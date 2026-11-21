"""API HTTP de liquidaciones y comprobantes de retención (TRE05-T006)."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.core.errors import ConflictError
from app.modules.government.api import _version
from app.modules.government.schemas_tesoreria_retencion_liquidacion import (
    AjustarLineaIn,
    AnularComprobanteIn,
    AnularLiquidacionIn,
    AprobarLiquidacionIn,
    CalcularRetencionIn,
)
from app.modules.government.service_tesoreria_retencion import (
    ajustar_linea,
    anular,
    aprobar,
    calcular,
    estado_de,
    historia,
    liquidacion_del_pago,
    listar,
    obtener,
    opciones,
    reporte_csv,
)
from app.modules.government.service_tesoreria_retencion_comprobantes import (
    anular_comprobante,
    historia_comprobante,
    listar_comprobantes,
    obtener_comprobante,
    pdf_comprobante,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/tesoreria/retenciones", tags=["gobierno"])


@router.get("/opciones")
def get_opciones(
    payment_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return opciones(db, ctx, payment_id)


@router.get("/pagos/{payment_id}/liquidacion")
def get_liquidacion_del_pago(
    payment_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return liquidacion_del_pago(db, ctx, payment_id)


@router.post("/pagos/{payment_id}/liquidacion", status_code=status.HTTP_201_CREATED)
def post_calcular(
    payment_id: str,
    cuerpo: CalcularRetencionIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "calculate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = calcular(db, ctx, payment_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.get("/liquidaciones.csv")
def get_liquidaciones_reporte(
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> Response:
    salida = reporte_csv(db, ctx, estado, desde, hasta)
    contenido = "﻿" + salida
    return Response(
        content=contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="liquidaciones-retencion.csv"'},
    )


@router.get("/liquidaciones")
def get_liquidaciones(
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    payment_id: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return listar(db, ctx, estado, desde, hasta, payment_id)


@router.get("/liquidaciones/{settlement_id}")
def get_liquidacion(
    settlement_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return obtener(db, ctx, settlement_id)


@router.get("/liquidaciones/{settlement_id}/historia")
def get_liquidacion_historia(
    settlement_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return historia(db, ctx, settlement_id)


@router.put("/liquidaciones/{settlement_id}/lineas/{linea_id}")
def put_ajustar_linea(
    settlement_id: str,
    linea_id: str,
    cuerpo: AjustarLineaIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "calculate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = ajustar_linea(
        db, ctx, settlement_id, linea_id, cuerpo.model_dump(), version
    )
    db.commit()
    return resultado


@router.post("/liquidaciones/{settlement_id}/aprobar")
def post_aprobar(
    settlement_id: str,
    cuerpo: AprobarLiquidacionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "approve")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = aprobar(db, ctx, settlement_id, cuerpo.model_dump(), version)
    db.commit()
    return resultado


@router.post("/liquidaciones/{settlement_id}/descartar")
def post_descartar(
    settlement_id: str,
    cuerpo: AnularLiquidacionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "calculate")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    if estado_de(db, ctx, settlement_id) != "CALCULADA":
        raise ConflictError(
            "GOV_WITHHOLDING_NOT_CALCULATED",
            "La liquidación no está en estado CALCULADA.",
        )
    version = _version(if_match)
    resultado = anular(db, ctx, settlement_id, cuerpo.model_dump(), version)
    db.commit()
    return resultado


@router.post("/liquidaciones/{settlement_id}/anular")
def post_anular(
    settlement_id: str,
    cuerpo: AnularLiquidacionIn,
    if_match: str | None = Header(default=None, alias="If-Match"),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "cancel")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = anular(db, ctx, settlement_id, cuerpo.model_dump(), version)
    db.commit()
    return resultado


@router.get("/comprobantes")
def get_comprobantes(
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    payment_id: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return listar_comprobantes(db, ctx, estado, desde, hasta, payment_id)


@router.get("/comprobantes/{receipt_id}")
def get_comprobante(
    receipt_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return obtener_comprobante(db, ctx, receipt_id)


@router.get("/comprobantes/{receipt_id}/historia")
def get_comprobante_historia(
    receipt_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return historia_comprobante(db, ctx, receipt_id)


@router.get("/comprobantes/{receipt_id}/pdf")
def get_comprobante_pdf(
    receipt_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> Response:
    contenido, nombre = pdf_comprobante(db, ctx, receipt_id)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.post("/comprobantes/{receipt_id}/anular")
def post_anular_comprobante(
    receipt_id: str,
    cuerpo: AnularComprobanteIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "cancel")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = anular_comprobante(db, ctx, receipt_id, cuerpo.model_dump())
    db.commit()
    return resultado
