"""API de las modificaciones contractuales (CNT-02)."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_contratos_modificaciones
from app.modules.government.api import _version
from app.modules.government.schemas_contratos import (
    CoberturaUpdate,
    FormalizacionCreate,
)
from app.modules.government.schemas_contratos_modificaciones import (
    ModificacionCreate,
    ModificacionUpdate,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contratos", tags=["gobierno"])


@router.get("/{contrato_id}/modificaciones")
def get_historia(
    contrato_id: str,
    fecha: date | None = Query(default=None),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_contratos_modificaciones.historia(db, ctx, contrato_id, fecha)


@router.post(
    "/{contrato_id}/modificaciones",
    status_code=status.HTTP_201_CREATED,
)
def post_modificacion(
    contrato_id: str,
    cuerpo: ModificacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos_modificaciones.crear(
        db, ctx, user, contrato_id, cuerpo.model_dump()
    )
    db.commit()
    return resultado


@router.get("/{contrato_id}/modificaciones/{modificacion_id}")
def get_modificacion(
    contrato_id: str,
    modificacion_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    _user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    resultado = service_contratos_modificaciones.ficha(
        db, ctx, contrato_id, modificacion_id
    )
    db.commit()
    return resultado


@router.patch("/{contrato_id}/modificaciones/{modificacion_id}")
def patch_modificacion(
    contrato_id: str,
    modificacion_id: str,
    cuerpo: ModificacionUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_contratos_modificaciones.actualizar(
        db,
        ctx,
        user,
        contrato_id,
        modificacion_id,
        version,
        cuerpo.model_dump(exclude_unset=True),
    )
    db.commit()
    return resultado


@router.put("/{contrato_id}/modificaciones/{modificacion_id}/cobertura")
def put_cobertura(
    contrato_id: str,
    modificacion_id: str,
    cuerpo: CoberturaUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    asignaciones = [a.model_dump() for a in cuerpo.asignaciones]
    resultado = service_contratos_modificaciones.actualizar_cobertura(
        db, ctx, user, contrato_id, modificacion_id, version, asignaciones
    )
    db.commit()
    return resultado


@router.delete(
    "/{contrato_id}/modificaciones/{modificacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_modificacion(
    contrato_id: str,
    modificacion_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> Response:
    version = _version(if_match)
    service_contratos_modificaciones.descartar(
        db, ctx, user, contrato_id, modificacion_id, version
    )
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{contrato_id}/modificaciones/{modificacion_id}/formalizar")
def post_formalizar(
    contrato_id: str,
    modificacion_id: str,
    cuerpo: FormalizacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "formalize")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_contratos_modificaciones.formalizar(
        db, ctx, user, contrato_id, modificacion_id, version, cuerpo.model_dump()
    )
    db.commit()
    return resultado
