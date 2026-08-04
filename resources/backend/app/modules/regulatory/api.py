"""API de regulación y traslados (008).

Endpoints REST `/regulatory/*` con las convenciones heredadas: errores
uniformes, transiciones explícitas, `allowed_actions` en backend.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.identity_access.models import User
from app.modules.regulatory import service as regulatory_service
from app.modules.regulatory.models import (
    ApprovalRequest,
    OfficialDocument,
    OfficialRegistration,
    PermitInstance,
    PermitType,
    RegulatoryAuthority,
    RegulatoryContingency,
    RegulatoryEvaluation,
    RegulatoryProfile,
    TransportDriver,
    TransportVehicle,
)

router = APIRouter(prefix="/regulatory", tags=["regulatorio"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class AuthorityCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    validation_method: str | None = None


class PermitTypeCreate(BaseModel):
    authority_id: str
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    scope: str | None = None
    validation_method: str | None = None


class RegistrationCreate(BaseModel):
    authority_id: str
    scope: str = Field(pattern="^(COMPANY|PARTY|SITE|VEHICLE|PERSON)$")
    ref_number: str = Field(min_length=1, max_length=120)
    issued_at: date | None = None
    expires_at: date | None = None
    file_ref: str | None = None


class ProfileCreate(BaseModel):
    operation: str = "DESPACHO"
    rubric_id: str | None = None
    product_id: str | None = None
    origin: str | None = None
    destination: str | None = None
    required_documents: list[str] | None = None
    version: str = "1.0"


class VehicleCreate(BaseModel):
    plate: str = Field(min_length=1, max_length=32)
    vehicle_type: str | None = None
    capacity: float | None = None
    owner_party_id: str | None = None
    documents: dict | None = None


class DriverCreate(BaseModel):
    party_id: str
    license: str | None = None
    documents: dict | None = None


class PermitCreate(BaseModel):
    permit_type_id: str
    number: str = Field(min_length=1, max_length=120)
    issued_at: date | None = None
    expires_at: date | None = None
    origin: str | None = None
    destination: str | None = None
    products: list[str] | None = None
    lots: list[str] | None = None
    quantity: float | None = None
    vehicle_id: str | None = None
    file_ref: str | None = None


class OfficialDocumentCreate(BaseModel):
    kind: str = Field(pattern="^(SICA|SIGESAI|SACS|GUIA_FISCAL|OTRO)$")
    number: str = Field(min_length=1, max_length=120)
    authority_id: str | None = None
    organism: str | None = None
    issued_at: date | None = None
    expires_at: date | None = None
    file_ref: str | None = None
    verification: str | None = None


class EvaluationCreate(BaseModel):
    shipment_id: str


class OverrideBody(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


class ContingencyCreate(BaseModel):
    rule_ref: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=3, max_length=255)


class ApprovalCreate(BaseModel):
    object_ref: str = Field(min_length=1, max_length=200)
    rule_ref: str | None = None
    risk: str | None = None
    amount: float | None = None
    deadline: date | None = None


class TransitionBody(BaseModel):
    target: str


# --------------------------------------------------------------------------- #
# Maestros regulatorios
# --------------------------------------------------------------------------- #
@router.get("/authorities")
def list_authorities(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(RegulatoryAuthority).where(RegulatoryAuthority.company_id == user.tenant_id)
                       .order_by(RegulatoryAuthority.name)).scalars().all()
    return {"items": [{"id": a.id, "code": a.code, "name": a.name, "validation_method": a.validation_method,
                       "status": a.status} for a in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/authorities", dependencies=[Depends(require_write_allowed)])
def create_authority(body: AuthorityCreate, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("regulatorio", "create"))):
    a = regulatory_service.create_authority(db, company_id=actor.tenant_id, code=body.code, name=body.name,
                                            validation_method=body.validation_method, actor=str(actor.id))
    db.commit()
    db.refresh(a)
    return {"id": a.id, "code": a.code, "name": a.name, "status": a.status}


@router.get("/permit-types")
def list_permit_types(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(PermitType).where(PermitType.company_id == user.tenant_id)
                       .order_by(PermitType.name)).scalars().all()
    return {"items": [{"id": t.id, "authority_id": t.authority_id, "code": t.code, "name": t.name,
                       "scope": t.scope, "status": t.status} for t in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/permit-types", dependencies=[Depends(require_write_allowed)])
def create_permit_type(body: PermitTypeCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("regulatorio", "create"))):
    t = regulatory_service.create_permit_type(db, company_id=actor.tenant_id, authority_id=body.authority_id,
                                              code=body.code, name=body.name, scope=body.scope,
                                              validation_method=body.validation_method, actor=str(actor.id))
    db.commit()
    db.refresh(t)
    return {"id": t.id, "code": t.code, "name": t.name, "status": t.status}


@router.get("/official-registrations")
def list_registrations(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(OfficialRegistration).where(OfficialRegistration.company_id == user.tenant_id)
                       .order_by(OfficialRegistration.created_at.desc())).scalars().all()
    return {"items": [{"id": r.id, "authority_id": r.authority_id, "scope": r.scope, "ref_number": r.ref_number,
                       "expires_at": r.expires_at.isoformat() if r.expires_at else None, "status": r.status} for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/official-registrations", dependencies=[Depends(require_write_allowed)])
def create_registration(body: RegistrationCreate, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("regulatorio", "create"))):
    r = regulatory_service.create_official_registration(db, company_id=actor.tenant_id, authority_id=body.authority_id,
                                                        scope=body.scope, ref_number=body.ref_number,
                                                        issued_at=body.issued_at, expires_at=body.expires_at,
                                                        file_ref=body.file_ref, actor=str(actor.id))
    db.commit()
    db.refresh(r)
    return {"id": r.id, "scope": r.scope, "ref_number": r.ref_number, "status": r.status}


@router.get("/profiles")
def list_profiles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(RegulatoryProfile).where(RegulatoryProfile.company_id == user.tenant_id)
                       .order_by(RegulatoryProfile.operation)).scalars().all()
    return {"items": [{"id": p.id, "operation": p.operation, "product_id": p.product_id, "rubric_id": p.rubric_id,
                       "required_documents": p.required_documents, "version": p.version, "status": p.status} for p in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/profiles", dependencies=[Depends(require_write_allowed)])
def create_profile(body: ProfileCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("regulatorio", "create"))):
    p = regulatory_service.create_profile(db, company_id=actor.tenant_id, operation=body.operation,
                                          rubric_id=body.rubric_id, product_id=body.product_id,
                                          origin=body.origin, destination=body.destination,
                                          required_documents=body.required_documents, version=body.version,
                                          actor=str(actor.id))
    db.commit()
    db.refresh(p)
    return {"id": p.id, "operation": p.operation, "required_documents": p.required_documents, "status": p.status}


@router.get("/vehicles")
def list_vehicles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(TransportVehicle).where(TransportVehicle.company_id == user.tenant_id)
                       .order_by(TransportVehicle.plate)).scalars().all()
    return {"items": [{"id": v.id, "plate": v.plate, "vehicle_type": v.vehicle_type, "capacity": v.capacity,
                       "owner_party_id": v.owner_party_id, "status": v.status} for v in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/vehicles", dependencies=[Depends(require_write_allowed)])
def create_vehicle(body: VehicleCreate, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("regulatorio", "create"))):
    v = regulatory_service.create_vehicle(db, company_id=actor.tenant_id, plate=body.plate, vehicle_type=body.vehicle_type,
                                          capacity=body.capacity, owner_party_id=body.owner_party_id,
                                          documents=body.documents, actor=str(actor.id))
    db.commit()
    db.refresh(v)
    return {"id": v.id, "plate": v.plate, "status": v.status}


@router.get("/drivers")
def list_drivers(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(TransportDriver).where(TransportDriver.company_id == user.tenant_id)
                       .order_by(TransportDriver.created_at.desc())).scalars().all()
    return {"items": [{"id": d.id, "party_id": d.party_id, "license": d.license, "status": d.status} for d in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/drivers", dependencies=[Depends(require_write_allowed)])
def create_driver(body: DriverCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("regulatorio", "create"))):
    d = regulatory_service.create_driver(db, company_id=actor.tenant_id, party_id=body.party_id, license=body.license,
                                         documents=body.documents, actor=str(actor.id))
    db.commit()
    db.refresh(d)
    return {"id": d.id, "party_id": d.party_id, "status": d.status}


# --------------------------------------------------------------------------- #
# Permisos y guías
# --------------------------------------------------------------------------- #
@router.get("/permits")
def list_permits(status: str | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    query = select(PermitInstance).where(PermitInstance.company_id == user.tenant_id)
    if status:
        query = query.where(PermitInstance.status == status)
    items = db.execute(query.order_by(PermitInstance.created_at.desc())).scalars().all()
    return {"items": [{"id": p.id, "permit_type_id": p.permit_type_id, "number": p.number,
                       "expires_at": p.expires_at.isoformat() if p.expires_at else None,
                       "hash": p.hash, "verification": p.verification, "status": p.status} for p in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/permits", dependencies=[Depends(require_write_allowed)])
def create_permit(body: PermitCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("regulatorio", "create"))):
    p = regulatory_service.create_permit(db, company_id=actor.tenant_id, permit_type_id=body.permit_type_id,
                                         number=body.number, issued_at=body.issued_at, expires_at=body.expires_at,
                                         origin=body.origin, destination=body.destination, products=body.products,
                                         lots=body.lots, quantity=body.quantity, vehicle_id=body.vehicle_id,
                                         file_ref=body.file_ref, actor=str(actor.id))
    db.commit()
    db.refresh(p)
    return {"id": p.id, "number": p.number, "status": p.status, "hash": p.hash}


@router.post("/permits/{permit_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_permit(permit_id: str, body: TransitionBody, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("regulatorio", "approve"))):
    p = _owned(db, PermitInstance, permit_id, actor.tenant_id, "PERMIT_NOT_FOUND", "Permiso no encontrado")
    regulatory_service.transition_permit(db, company_id=actor.tenant_id, permit_id=str(p.id), target=body.target,
                                         actor=str(actor.id))
    db.commit()
    db.refresh(p)
    return {"id": p.id, "number": p.number, "status": p.status}


@router.get("/official-documents")
def list_official_documents(kind: str | None = None, db: Session = Depends(get_db),
                            user: User = Depends(get_current_user)):
    query = select(OfficialDocument).where(OfficialDocument.company_id == user.tenant_id)
    if kind:
        query = query.where(OfficialDocument.kind == kind)
    items = db.execute(query.order_by(OfficialDocument.created_at.desc())).scalars().all()
    return {"items": [{"id": d.id, "kind": d.kind, "number": d.number, "organism": d.organism,
                       "expires_at": d.expires_at.isoformat() if d.expires_at else None,
                       "hash": d.hash, "verification": d.verification, "status": d.status} for d in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/official-documents", dependencies=[Depends(require_write_allowed)])
def register_official_document(body: OfficialDocumentCreate, db: Session = Depends(get_db),
                               actor: User = Depends(require_permission("regulatorio", "create"))):
    doc = regulatory_service.register_official_document(db, company_id=actor.tenant_id, kind=body.kind,
                                                        number=body.number, authority_id=body.authority_id,
                                                        organism=body.organism, issued_at=body.issued_at,
                                                        expires_at=body.expires_at, file_ref=body.file_ref,
                                                        verification=body.verification, actor=str(actor.id))
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "kind": doc.kind, "number": doc.number, "hash": doc.hash, "status": doc.status}


# --------------------------------------------------------------------------- #
# Evaluación y bloqueo del despacho
# --------------------------------------------------------------------------- #
@router.post("/evaluations", dependencies=[Depends(require_write_allowed)])
def evaluate_shipment(body: EvaluationCreate, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("regulatorio", "approve"))):
    result = regulatory_service.evaluate_shipment(db, company_id=actor.tenant_id, shipment_id=body.shipment_id,
                                                  actor=str(actor.id))
    db.commit()
    return result


@router.get("/evaluations")
def list_evaluations(shipment_id: str | None = None, db: Session = Depends(get_db),
                     user: User = Depends(get_current_user)):
    query = select(RegulatoryEvaluation).where(RegulatoryEvaluation.company_id == user.tenant_id)
    if shipment_id:
        query = query.where(RegulatoryEvaluation.shipment_id == shipment_id)
    items = db.execute(query.order_by(RegulatoryEvaluation.created_at.desc())).scalars().all()
    return {"items": [{"id": e.id, "shipment_id": e.shipment_id, "shipment_line_ref": e.shipment_line_ref,
                       "required": e.required, "blockers": e.blockers, "override": e.override, "status": e.status}
                      for e in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/evaluations/{evaluation_id}/override", dependencies=[Depends(require_write_allowed)])
def override_evaluation(evaluation_id: str, body: OverrideBody, db: Session = Depends(get_db),
                        actor: User = Depends(require_permission("regulatorio", "approve"))):
    e = _owned(db, RegulatoryEvaluation, evaluation_id, actor.tenant_id, "EVALUATION_NOT_FOUND", "Evaluación no encontrada")
    regulatory_service.override_evaluation(db, company_id=actor.tenant_id, evaluation_id=str(e.id),
                                           reason=body.reason, actor=str(actor.id))
    db.commit()
    db.refresh(e)
    return {"id": e.id, "status": e.status, "override": e.override}


# --------------------------------------------------------------------------- #
# Contingencias y aprobaciones
# --------------------------------------------------------------------------- #
@router.get("/contingencies")
def list_contingencies(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(RegulatoryContingency).where(RegulatoryContingency.company_id == user.tenant_id)
                       .order_by(RegulatoryContingency.created_at.desc())).scalars().all()
    return {"items": [{"id": c.id, "rule_ref": c.rule_ref, "reason": c.reason, "allowed_by": c.allowed_by,
                       "status": c.status} for c in items], "total": len(items), "page": 1, "page_size": len(items) or 1}


@router.post("/contingencies", dependencies=[Depends(require_write_allowed)])
def create_contingency(body: ContingencyCreate, db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("regulatorio", "create"))):
    c = regulatory_service.create_contingency(db, company_id=actor.tenant_id, rule_ref=body.rule_ref,
                                              reason=body.reason, actor=str(actor.id))
    db.commit()
    db.refresh(c)
    return {"id": c.id, "rule_ref": c.rule_ref, "status": c.status}


@router.post("/contingencies/{contingency_id}/end", dependencies=[Depends(require_write_allowed)])
def end_contingency(contingency_id: str, db: Session = Depends(get_db),
                    actor: User = Depends(require_permission("regulatorio", "approve"))):
    c = _owned(db, RegulatoryContingency, contingency_id, actor.tenant_id, "CONTINGENCY_NOT_FOUND", "Contingencia no encontrada")
    regulatory_service.end_contingency(db, company_id=actor.tenant_id, contingency_id=str(c.id))
    db.commit()
    db.refresh(c)
    return {"id": c.id, "status": c.status}


@router.post("/approval-requests", dependencies=[Depends(require_write_allowed)])
def create_approval_request(body: ApprovalCreate, db: Session = Depends(get_db),
                            actor: User = Depends(require_permission("regulatorio", "create"))):
    req = regulatory_service.create_approval_request(db, company_id=actor.tenant_id, object_ref=body.object_ref,
                                                     rule_ref=body.rule_ref, risk=body.risk, amount=body.amount,
                                                     deadline=body.deadline, actor=str(actor.id))
    db.commit()
    db.refresh(req)
    return {"id": req.id, "object_ref": req.object_ref, "status": req.status}


@router.post("/approval-requests/{request_id}/transition", dependencies=[Depends(require_write_allowed)])
def transition_approval_request(request_id: str, body: TransitionBody, db: Session = Depends(get_db),
                                actor: User = Depends(require_permission("regulatorio", "approve"))):
    req = _owned(db, ApprovalRequest, request_id, actor.tenant_id, "APPROVAL_REQUEST_NOT_FOUND", "Solicitud no encontrada")
    regulatory_service.transition_approval_request(db, company_id=actor.tenant_id, request_id=str(req.id),
                                                   target=body.target, actor=str(actor.id))
    db.commit()
    db.refresh(req)
    return {"id": req.id, "object_ref": req.object_ref, "status": req.status, "decision": req.decision}


@router.get("/approval-requests")
def list_approval_requests(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    items = db.execute(select(ApprovalRequest).where(ApprovalRequest.company_id == user.tenant_id)
                       .order_by(ApprovalRequest.created_at.desc())).scalars().all()
    return {"items": [{"id": r.id, "object_ref": r.object_ref, "rule_ref": r.rule_ref, "risk": r.risk,
                       "amount": r.amount, "status": r.status, "decision": r.decision} for r in items],
            "total": len(items), "page": 1, "page_size": len(items) or 1}


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _owned(db: Session, model, obj_id: str, tenant: str, code: str, message: str):
    obj = db.get(model, obj_id)
    if not obj or getattr(obj, "company_id", tenant) != tenant:
        raise NotFoundError(code=code, message=message)
    return obj
