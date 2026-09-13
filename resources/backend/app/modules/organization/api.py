"""API de organización: companies, branches y establishments.

Los almacenes y su estructura física los sirve `warehouse_api.py` (Spec 008),
que es la autoridad única sobre la jerarquía (P22).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.organization.models import (
    Branch,
    Company,
    Establishment,
)

router = APIRouter(prefix="/organization", tags=["organization"])


class CompanyCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    legal_name: str = Field(min_length=1, max_length=255)
    trade_name: str | None = None
    rif: str = Field(min_length=5, max_length=20)
    legal_type: str = "JURIDICA"
    activity: str | None = None
    fiscal_address: str | None = None
    functional_currency: str = "VED"


class BranchCreate(BaseModel):
    #: Se conserva por compatibilidad; la empresa la decide el contexto.
    company_id: str | None = None
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    address: str | None = None
    manager: str | None = None


class EstablishmentCreate(BaseModel):
    branch_id: str
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    fiscal_address: str | None = None


@router.get("/companies")
def list_companies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Las empresas en las que este usuario puede operar.

    Es la autoridad del selector de empresa: lo que salga de aquí es lo que la
    interfaz ofrecerá. Devolver todas las del tenant no concedía acceso —cada
    petición se seguía rechazando— pero ofrecía empresas ajenas y convertía el
    selector en una fuente de errores inexplicables.

    Se resuelve con `accessible_company_ids`, la misma autoridad que valida cada
    petición, para que la lista y el permiso no puedan divergir.
    """
    from app.core.company_context import accessible_company_ids

    alcanzables = set(accessible_company_ids(db, user))
    companies = [
        c for c in db.execute(
            select(Company).where(Company.tenant_id == user.tenant_id)
            .order_by(Company.created_at)).scalars().all()
        if str(c.id) in alcanzables
    ]
    return [
        {
            "id": str(c.id),
            "code": c.code,
            "legal_name": c.legal_name,
            "trade_name": c.trade_name,
            "rif": c.rif,
            "status": c.status,
            # La moneda funcional deja de ser un dato interno con la Spec 013:
            # es el ancla contra la que cotiza casi todo par, y la interfaz no
            # tenía forma de saberla.
            "functional_currency": c.functional_currency,
            "allowed_actions": {"view": True, "edit": True, "activate": True, "deactivate": True, "delete": False},
        }
        for c in companies
    ]


@router.post("/companies", dependencies=[Depends(require_write_allowed)])
def create_company(
    body: CompanyCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("organization", "create")),
):
    company = Company(
        tenant_id=actor.tenant_id,
        code=body.code,
        legal_name=body.legal_name,
        trade_name=body.trade_name,
        rif=body.rif,
        legal_type=body.legal_type,
        activity=body.activity,
        fiscal_address=body.fiscal_address,
        functional_currency=body.functional_currency,
        status="ACTIVE",
        created_by=str(actor.id),
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return {"id": str(company.id), "code": company.code, "legal_name": company.legal_name}


@router.get("/branches")
def list_branches(db: Session = Depends(get_db), user: User = Depends(get_current_user),
                  ctx: CompanyContext = Depends(get_company_context)):
    # Antes listaba las sucursales de todas las empresas del tenant, y el
    # filtro por empresa era una preferencia del cliente en vez de un límite.
    query = select(Branch).where(Branch.company_id == ctx.company_id)
    return [{"id": str(b.id), "company_id": b.company_id, "code": b.code, "name": b.name, "status": b.status} for b in db.execute(query.order_by(Branch.created_at)).scalars().all()]


@router.post("/branches", dependencies=[Depends(require_write_allowed)])
def create_branch(body: BranchCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("organization", "create")),
                  ctx: CompanyContext = Depends(get_company_context)):
    # La sucursal nace en la empresa en la que se está operando; el cuerpo puede
    # confirmarlo pero no elegir otra.
    if body.company_id is not None and body.company_id != ctx.company_id:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    branch = Branch(
        company_id=ctx.company_id,
        code=body.code,
        name=body.name,
        address=body.address,
        manager=body.manager,
        status="ACTIVE",
        created_by=str(actor.id),
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    return {"id": str(branch.id), "code": branch.code, "name": branch.name}


@router.get("/establishments")
def list_establishments(branch_id: str | None = None, db: Session = Depends(get_db),
                        user: User = Depends(get_current_user),
                        ctx: CompanyContext = Depends(get_company_context)):
    """Establecimientos de la empresa activa.

    Filtraba por `Company.tenant_id == user.tenant_id`: un usuario de A veía los
    establecimientos de B por el hecho de compartir tenant. El establecimiento
    es de empresa —`Establishment.__scope_authority__` dice `branch_id →
    branches`—, así que el tenant nunca fue el filtro correcto.
    """
    query = select(Establishment).join(Branch, Establishment.branch_id == Branch.id)\
        .where(Branch.company_id == ctx.company_id)
    if branch_id:
        query = query.where(Establishment.branch_id == branch_id)
    return [{"id": str(e.id), "branch_id": e.branch_id, "code": e.code, "name": e.name, "issuance_enabled": e.issuance_enabled, "status": e.status} for e in db.execute(query.order_by(Establishment.created_at)).scalars().all()]


@router.post("/establishments", dependencies=[Depends(require_write_allowed)])
def create_establishment(body: EstablishmentCreate, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("organization", "create")),
                         ctx: CompanyContext = Depends(get_company_context)):
    """El establecimiento nace en una sucursal **de la empresa activa**.

    Comprobaba `branch_in_tenant`: bastaba con que la sucursal fuera de alguna
    empresa del tenant. Un usuario de A podía abrir un establecimiento en una
    sucursal de B, y el establecimiento es donde se emiten documentos fiscales.
    """
    sucursal = db.get(Branch, body.branch_id)
    if sucursal is None or sucursal.company_id != ctx.company_id:
        raise NotFoundError(code="BRANCH_NOT_FOUND", message="Sucursal no encontrada")
    est = Establishment(
        branch_id=body.branch_id,
        code=body.code,
        name=body.name,
        fiscal_address=body.fiscal_address,
        issuance_enabled=False,
        status="ACTIVE",
        created_by=str(actor.id),
    )
    db.add(est)
    db.commit()
    db.refresh(est)
    return {"id": str(est.id), "code": est.code, "name": est.name}
