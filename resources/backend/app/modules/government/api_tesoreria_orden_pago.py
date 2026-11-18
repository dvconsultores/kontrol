"""API HTTP de la orden de pago (TRE-03)."""

from __future__ import annotations

import io
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government.schemas_tesoreria_orden_pago import AnularOrdenIn, OrdenCreate, OrdenUpdate
from app.modules.government.service_tesoreria_orden_pago import (
    actualizar_orden,
    anular_orden,
    crear_orden,
    emitir_orden,
    listar_ordenes,
    obtener_controles,
    obtener_orden,
    opciones,
    reporte_csv,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/tesoreria", tags=["Gobierno · Tesorería"])


def _version(if_match: str | None) -> int | None:
    if if_match is None:
        return None
    try:
        return int(if_match.strip('"'))
    except ValueError:
        return None


@router.get("/ejercicios/{year_id}/ordenes-pago")
def get_ejercicios_ordenes_pago(
    year_id: str,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    beneficiario: str | None = None,
    moneda: str | None = None,
    cause_id: str | None = None,
    commitment_id: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return listar_ordenes(db, ctx, year_id, estado, desde, hasta, beneficiario, moneda, cause_id, commitment_id, q)


@router.get("/ejercicios/{year_id}/ordenes-pago/reporte.csv")
def get_ejercicios_ordenes_pago_reporte(
    year_id: str,
    estado: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    beneficiario: str | None = None,
    moneda: str | None = None,
    cause_id: str | None = None,
    commitment_id: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> StreamingResponse:
    from app.modules.government.service_tesoreria_orden_pago import _ejercicio_de_empresa

    year = _ejercicio_de_empresa(db, ctx, year_id)
    salida = reporte_csv(db, ctx, year_id, estado, desde, hasta, beneficiario, moneda, cause_id, commitment_id, q)
    contenido = "﻿" + salida
    return StreamingResponse(
        io.StringIO(contenido),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="ordenes-pago-{year.anio}.csv"'},
    )


@router.get("/ejercicios/{year_id}/ordenes-pago/opciones")
def get_ejercicios_ordenes_pago_opciones(
    year_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return opciones(db, ctx, year_id)


@router.post("/ejercicios/{year_id}/ordenes-pago", status_code=status.HTTP_201_CREATED)
def post_ejercicios_ordenes_pago(
    year_id: str,
    cuerpo: OrdenCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = crear_orden(db, ctx, year_id, cuerpo.model_dump())
    db.commit()
    return resultado


@router.get("/ordenes-pago/{order_id}")
def get_orden_pago(
    order_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return obtener_orden(db, ctx, order_id)


@router.get("/ordenes-pago/{order_id}/controles")
def get_orden_pago_controles(
    order_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return obtener_controles(db, ctx, order_id)


@router.put("/ordenes-pago/{order_id}")
def put_orden_pago(
    order_id: str,
    cuerpo: OrdenUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = actualizar_orden(db, ctx, order_id, cuerpo.model_dump(exclude_unset=True), version)
    db.commit()
    return resultado


@router.post("/ordenes-pago/{order_id}/emitir")
def post_orden_pago_emitir(
    order_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "issue")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = emitir_orden(db, ctx, order_id, version)
    db.commit()
    return resultado


@router.post("/ordenes-pago/{order_id}/anular")
def post_orden_pago_anular(
    order_id: str,
    cuerpo: AnularOrdenIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "cancel")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = anular_orden(db, ctx, order_id, cuerpo.model_dump(), version)
    db.commit()
    return resultado
