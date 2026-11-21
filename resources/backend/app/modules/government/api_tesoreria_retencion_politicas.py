"""API de políticas y configuración de retención (TRE-05, T004)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_tesoreria_retencion_politicas
from app.modules.government.api import _version
from app.modules.government.schemas_tesoreria_retencion import (
    ActivarPoliticaRetencionIn,
    CatalogoRetencionCreate,
    CatalogoRetencionUpdate,
    CerrarPoliticaRetencionIn,
    ConfiguracionRetencionIn,
    PoliticaRetencionCreate,
    PoliticaRetencionUpdate,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/tesoreria/retenciones", tags=["gobierno"])


@router.get("/configuracion")
def get_retenciones_configuracion(
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_tesoreria_retencion_politicas.configuracion_actual(db, ctx)


@router.put("/configuracion")
def put_retenciones_configuracion(
    cuerpo: ConfiguracionRetencionIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_retencion_politicas.actualizar_configuracion(
        db, ctx, cuerpo.model_dump(mode="python"), version
    )
    db.commit()
    return resultado


@router.get("/catalogo")
def get_retenciones_catalogo(
    tipo: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return service_tesoreria_retencion_politicas.listar_catalogo(db, ctx, tipo)


@router.post("/catalogo", status_code=status.HTTP_201_CREATED)
def post_retenciones_catalogo(
    cuerpo: CatalogoRetencionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_tesoreria_retencion_politicas.crear_elemento_catalogo(
        db, ctx, cuerpo.model_dump(mode="python")
    )
    db.commit()
    return resultado


@router.put("/catalogo/{item_id}")
def put_retenciones_catalogo(
    item_id: str,
    cuerpo: CatalogoRetencionUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_retencion_politicas.actualizar_elemento_catalogo(
        db, ctx, item_id, cuerpo.model_dump(mode="python", exclude_unset=True), version
    )
    db.commit()
    return resultado


@router.get("/politicas")
def get_retenciones_politicas(
    estado: str | None = None,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return service_tesoreria_retencion_politicas.listar_politicas(db, ctx, estado)


@router.post("/politicas", status_code=status.HTTP_201_CREATED)
def post_retenciones_politicas(
    cuerpo: PoliticaRetencionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_tesoreria_retencion_politicas.crear_politica(
        db, ctx, cuerpo.model_dump(mode="python")
    )
    db.commit()
    return resultado


@router.get("/politicas/{policy_id}")
def get_retenciones_politica(
    policy_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_tesoreria_retencion_politicas.obtener_politica(db, ctx, policy_id)


@router.put("/politicas/{policy_id}")
def put_retenciones_politica(
    policy_id: str,
    cuerpo: PoliticaRetencionUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_retencion_politicas.actualizar_politica(
        db, ctx, policy_id, cuerpo.model_dump(mode="python", exclude_unset=True), version
    )
    db.commit()
    return resultado


@router.post("/politicas/{policy_id}/activar")
def post_retenciones_politica_activar(
    policy_id: str,
    cuerpo: ActivarPoliticaRetencionIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_retencion_politicas.activar_politica(
        db, ctx, policy_id, cuerpo.model_dump(mode="python"), version
    )
    db.commit()
    return resultado


@router.post("/politicas/{policy_id}/cerrar")
def post_retenciones_politica_cerrar(
    policy_id: str,
    cuerpo: CerrarPoliticaRetencionIn,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "policy")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_tesoreria_retencion_politicas.cerrar_politica(
        db, ctx, policy_id, cuerpo.model_dump(mode="python"), version
    )
    db.commit()
    return resultado


@router.post("/politicas/{policy_id}/nueva-version", status_code=status.HTTP_201_CREATED)
def post_retenciones_politica_nueva_version(
    policy_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_tesoreria_retencion_politicas.nueva_version_politica(db, ctx, policy_id)
    db.commit()
    return resultado


@router.get("/politicas/{policy_id}/historia")
def get_retenciones_politica_historia(
    policy_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_retenciones", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> list[dict[str, Any]]:
    return service_tesoreria_retencion_politicas.historia_politica(db, ctx, policy_id)
