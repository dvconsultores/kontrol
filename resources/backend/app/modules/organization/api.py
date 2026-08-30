"""API de organización: companies, branches y establishments.

Los almacenes y su estructura física los sirve `warehouse_api.py` (Spec 008),
que es la autoridad única sobre la jerarquía (P22).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.organization.models import (
    Branch,
    Company,
    Establishment,
)
from app.modules.organization.service import branch_in_tenant, company_in_tenant

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
    company_id: str
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
    companies = db.execute(select(Company).where(Company.tenant_id == user.tenant_id)
                           .order_by(Company.created_at)).scalars().all()
    return [
        {
            "id": str(c.id),
            "code": c.code,
            "legal_name": c.legal_name,
            "trade_name": c.trade_name,
            "rif": c.rif,
            "status": c.status,
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
def list_branches(company_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Branch).join(Company, Branch.company_id == Company.id)\
        .where(Company.tenant_id == user.tenant_id)
    if company_id:
        query = query.where(Branch.company_id == company_id)
    return [{"id": str(b.id), "company_id": b.company_id, "code": b.code, "name": b.name, "status": b.status} for b in db.execute(query.order_by(Branch.created_at)).scalars().all()]


@router.post("/branches", dependencies=[Depends(require_write_allowed)])
def create_branch(body: BranchCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("organization", "create"))):
    if not company_in_tenant(db, actor.tenant_id, body.company_id):
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    branch = Branch(
        company_id=body.company_id,
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
def list_establishments(branch_id: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(Establishment).join(Branch, Establishment.branch_id == Branch.id)\
        .join(Company, Branch.company_id == Company.id).where(Company.tenant_id == user.tenant_id)
    if branch_id:
        query = query.where(Establishment.branch_id == branch_id)
    return [{"id": str(e.id), "branch_id": e.branch_id, "code": e.code, "name": e.name, "issuance_enabled": e.issuance_enabled, "status": e.status} for e in db.execute(query.order_by(Establishment.created_at)).scalars().all()]


@router.post("/establishments", dependencies=[Depends(require_write_allowed)])
def create_establishment(body: EstablishmentCreate, db: Session = Depends(get_db), actor: User = Depends(require_permission("organization", "create"))):
    if not branch_in_tenant(db, actor.tenant_id, body.branch_id):
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
