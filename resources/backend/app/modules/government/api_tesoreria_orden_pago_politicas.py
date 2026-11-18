"""API de políticas y configuración de la orden de pago (TRE-03, parte 1)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_tesoreria_orden_pago_politicas
from app.modules.government.api import _version
from app.modules.government.schemas_tesoreria_orden_pago import (
    ActivarPoliticaIn,
    CerrarPoliticaIn,
    ConfiguracionOrdenPagoIn,
    PoliticaOrdenPagoCreate,
    PoliticaOrdenPagoUpdate,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/tesoreria", tags=["gobierno"])


@router.get("/ordenes-pago/configuracion")
def get_ordenes_pago_configuracion(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_tesoreria_orden_pago_politicas.configuracion_actual(db, ctx)


@router.put("/ordenes-pago/configuracion")
def put_ordenes_pago_configuracion(
    cuerpo: ConfiguracionOrdenPagoIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_orden_pago_politicas.actualizar_configuracion(
        db, ctx, cuerpo.model_dump(), version
    )
    db.commit()
    return resultado


@router.get("/politicas-orden-pago")
def get_politicas_orden_pago(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return service_tesoreria_orden_pago_politicas.listar_politicas(db, ctx)


@router.get("/politicas-orden-pago/{policy_id}")
def get_politica_orden_pago(
    policy_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_tesoreria_orden_pago_politicas.obtener_politica(db, ctx, policy_id)


@router.post("/politicas-orden-pago", status_code=status.HTTP_201_CREATED)
def post_politica_orden_pago(
    cuerpo: PoliticaOrdenPagoCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_tesoreria_orden_pago_politicas.crear_politica(
        db, ctx, cuerpo.model_dump()
    )
    db.commit()
    return resultado


@router.put("/politicas-orden-pago/{policy_id}")
def put_politica_orden_pago(
    policy_id: str,
    cuerpo: PoliticaOrdenPagoUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_orden_pago_politicas.actualizar_politica(
        db, ctx, policy_id, cuerpo.model_dump(exclude_unset=True), version
    )
    db.commit()
    return resultado


@router.post("/politicas-orden-pago/{policy_id}/activar")
def post_politica_orden_pago_activar(
    policy_id: str,
    cuerpo: ActivarPoliticaIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_orden_pago_politicas.activar_politica(
        db, ctx, policy_id, cuerpo.model_dump(), version
    )
    db.commit()
    return resultado


@router.post("/politicas-orden-pago/{policy_id}/cerrar")
def post_politica_orden_pago_cerrar(
    policy_id: str,
    cuerpo: CerrarPoliticaIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_ordenes_pago", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_orden_pago_politicas.cerrar_politica(
        db, ctx, policy_id, cuerpo.model_dump(), version
    )
    db.commit()
    return resultado
