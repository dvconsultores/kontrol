"""API del contrato u orden derivada de la adjudicación (CNT-01)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_module, require_permission, require_write_allowed
from app.modules.government import service_contratos
from app.modules.government.api import _version
from app.modules.government.schemas_contratos import (
    CoberturaUpdate,
    ContratoCreate,
    ContratoUpdate,
    FormalizacionCreate,
    GarantiasUpdate,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/gobierno/contratos", tags=["gobierno"])


@router.get("")
def get_contratos(
    estado: str | None = Query(default=None),
    tipo: str | None = Query(default=None),
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_contratos.listar(db, ctx, estado, tipo)


@router.post("", status_code=status.HTTP_201_CREATED)
def post_contrato(
    cuerpo: ContratoCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
) -> dict[str, Any]:
    resultado = service_contratos.crear(db, ctx, user, cuerpo.model_dump())
    db.commit()
    return resultado


@router.get("/{contrato_id}")
def get_contrato(
    contrato_id: str,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "view")),
    _modulo: None = Depends(require_module("gobierno")),
) -> dict[str, Any]:
    return service_contratos.ficha(db, ctx, contrato_id)


@router.patch("/{contrato_id}")
def patch_contrato(
    contrato_id: str,
    cuerpo: ContratoUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_contratos.actualizar(db, ctx, user, contrato_id, version, cuerpo.model_dump(exclude_unset=True))
    db.commit()
    return resultado


@router.put("/{contrato_id}/cobertura")
def put_cobertura(
    contrato_id: str,
    cuerpo: CoberturaUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_contratos.actualizar_cobertura(
        db, ctx, user, contrato_id, version, [a.model_dump() for a in cuerpo.asignaciones]
    )
    db.commit()
    return resultado


@router.put("/{contrato_id}/garantias")
def put_garantias(
    contrato_id: str,
    cuerpo: GarantiasUpdate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "manage")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_contratos.actualizar_garantias(db, ctx, user, contrato_id, version, cuerpo.instrumento_ids)
    db.commit()
    return resultado


@router.post("/{contrato_id}/formalizar")
def post_formalizar(
    contrato_id: str,
    cuerpo: FormalizacionCreate,
    db: Session = Depends(get_db),
    ctx: CompanyContext = Depends(get_company_context),
    user: User = Depends(require_permission("gobierno_contratos", "formalize")),
    _modulo: None = Depends(require_module("gobierno")),
    _: None = Depends(require_write_allowed),
    if_match: str | None = Header(default=None, alias="If-Match"),
) -> dict[str, Any]:
    version = _version(if_match)
    resultado = service_contratos.formalizar(db, ctx, user, contrato_id, version, cuerpo.model_dump())
    db.commit()
    return resultado
