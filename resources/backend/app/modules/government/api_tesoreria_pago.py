"""API HTTP del pago de una orden de pago (TRE-04)."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government.schemas_tesoreria_pago import (
    AnularPagoIn,
    AprobarPagoIn,
    EnviarPagoIn,
    PagoCreate,
    PagoUpdate,
    RechazarPagoIn,
    RegistrarPagoIn,
)
from app.modules.government.service_tesoreria_pago import (
    actualizar_pago,
    controles_pago,
    crear_pago,
    descartar_borrador,
    enviar_pago,
    listar_pagos,
    obtener_pago,
    opciones_pago,
    reporte_csv_pagos,
)
from app.modules.government.service_tesoreria_pago_transiciones import (
    anular_pago,
    aprobar_pago,
    rechazar_pago,
    registrar_pago,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/tesoreria", tags=["gobierno"])


def _version(if_match: str | None) -> int | None:
    if if_match is None:
        return None
    try:
        return int(if_match.strip('"'))
    except ValueError:
        return None


@router.get("/pagos")
def get_pagos(
    estado: str | None = None,
    order_id: str | None = None,
    beneficiario: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    account_id: str | None = None,
    method_id: str | None = None,
    moneda: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return listar_pagos(
        db,
        ctx,
        estado,
        order_id,
        beneficiario,
        desde,
        hasta,
        account_id,
        method_id,
        moneda,
        q,
    )


@router.get("/pagos/reporte.csv")
def get_pagos_reporte(
    estado: str | None = None,
    order_id: str | None = None,
    beneficiario: str | None = None,
    desde: date | None = None,
    hasta: date | None = None,
    account_id: str | None = None,
    method_id: str | None = None,
    moneda: str | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> Response:
    salida = reporte_csv_pagos(
        db,
        ctx,
        estado,
        order_id,
        beneficiario,
        desde,
        hasta,
        account_id,
        method_id,
        moneda,
        q,
    )
    contenido = "﻿" + salida
    return Response(
        content=contenido,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="pagos.csv"'},
    )


@router.get("/pagos/opciones")
def get_pagos_opciones(
    order_id: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return opciones_pago(db, ctx, order_id)


@router.post("/pagos", status_code=status.HTTP_201_CREATED)
def post_pagos(
    cuerpo: PagoCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = crear_pago(db, ctx, cuerpo.model_dump(mode="python"))
    db.commit()
    return resultado


@router.get("/pagos/{payment_id}")
def get_pago(
    payment_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return obtener_pago(db, ctx, payment_id)


@router.put("/pagos/{payment_id}")
def put_pago(
    payment_id: str,
    cuerpo: PagoUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = actualizar_pago(db, ctx, payment_id, cuerpo.model_dump(mode="python", exclude_unset=True), version)
    db.commit()
    return resultado


@router.get("/pagos/{payment_id}/controles")
def get_pago_controles(
    payment_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return controles_pago(db, ctx, payment_id)


@router.post("/pagos/{payment_id}/enviar")
def post_pago_enviar(
    payment_id: str,
    cuerpo: EnviarPagoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = enviar_pago(db, ctx, payment_id, cuerpo.model_dump(mode="python"), version)
    db.commit()
    return resultado


@router.post("/pagos/{payment_id}/aprobar")
def post_pago_aprobar(
    payment_id: str,
    cuerpo: AprobarPagoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "authorize")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = aprobar_pago(db, ctx, payment_id, cuerpo.model_dump(mode="python"), version)
    db.commit()
    return resultado


@router.post("/pagos/{payment_id}/rechazar")
def post_pago_rechazar(
    payment_id: str,
    cuerpo: RechazarPagoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "authorize")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = rechazar_pago(db, ctx, payment_id, cuerpo.model_dump(mode="python"), version)
    db.commit()
    return resultado


@router.post("/pagos/{payment_id}/registrar")
def post_pago_registrar(
    payment_id: str,
    cuerpo: RegistrarPagoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "execute")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = registrar_pago(db, ctx, payment_id, cuerpo.model_dump(mode="python"), version)
    db.commit()
    return resultado


@router.post("/pagos/{payment_id}/descartar")
def post_pago_descartar(
    payment_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = descartar_borrador(db, ctx, payment_id, version)
    db.commit()
    return resultado


@router.post("/pagos/{payment_id}/anular")
def post_pago_anular(
    payment_id: str,
    cuerpo: AnularPagoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_pagos", "cancel")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = anular_pago(db, ctx, payment_id, cuerpo.model_dump(mode="python"), version)
    db.commit()
    return resultado
