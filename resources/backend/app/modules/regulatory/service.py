"""Servicios de regulación y traslados (008).

Maestros regulatorios, permisos con ciclo de vida, guías SICA/SIGESAI/SACS
(registro y validación), evaluación regulatoria por línea de despacho con
bloqueo de salida, y contingencias con regla oficial versionada.

Integración: 008 consume los despachos de 005 (`Shipment`) vía contrato v1;
no fabrica permisos externos (DOC-01 §10).
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.approvals import integration as approvals_integration
from app.modules.regulatory.models import (
    OfficialDocument,
    OfficialRegistration,
    PermitInstance,
    PermitType,
    RegulatoryApprovalRequest,
    RegulatoryAuthority,
    RegulatoryContingency,
    RegulatoryEvaluation,
    RegulatoryProfile,
    TransportDriver,
    TransportVehicle,
)
from app.shared import audit as audit_service


def _audit(db: Session, *, action: str, entity_type: str, entity_id: str,
           company_id: str, actor: str | None = None, **kw: Any) -> None:
    """Registra un evento de auditoría de negocio (KAUD-001 → FR-009-022)."""
    audit_service.record_audit(
        db, action=action, entity_type=entity_type, entity_id=entity_id,
        company_id=company_id, user_id=actor, source="API", **kw,
    )

PERMIT_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"REGISTERED", "CANCELLED"},
    "REGISTERED": {"VERIFIED", "REJECTED"},
    "VERIFIED": {"APPROVED_FOR_USE", "REJECTED"},
    "APPROVED_FOR_USE": {"USED", "EXPIRED"},
    "USED": set(),
    "EXPIRED": set(),
    "REJECTED": set(),
    "CANCELLED": set(),
}

APPROVAL_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"APPROVED", "REJECTED"},
    "APPROVED": set(),
    "REJECTED": set(),
}


def _company(company_id: str | None, *, obj: str) -> str:
    if not company_id:
        raise KontrolError(code="COMPANY_REQUIRED", message="Se requiere la empresa para esta operación", status_code=422)
    return company_id


def _assert_transition(current: str, target: str, transitions: dict[str, set[str]], what: str) -> None:
    if target not in transitions.get(current, set()):
        raise ConflictError(code="INVALID_STATE_TRANSITION", message=f"No se permite pasar {what} de {current} a {target}.")


def _require_authority(db: Session, company_id: str, authority_id: str) -> RegulatoryAuthority:
    a = db.get(RegulatoryAuthority, authority_id)
    if not a or a.company_id != company_id:
        raise NotFoundError(code="AUTHORITY_NOT_FOUND", message="Autoridad regulatoria no encontrada")
    return a


def _doc_hash(*parts: object) -> str:
    return hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Maestros regulatorios
# --------------------------------------------------------------------------- #
def create_authority(db: Session, *, company_id: str, code: str, name: str, validation_method: str | None = None,
                     actor: str | None = None) -> RegulatoryAuthority:
    company_id = _company(company_id, obj="autoridad")
    a = RegulatoryAuthority(company_id=company_id, code=code, name=name, validation_method=validation_method,
                            status="ACTIVE", created_by=actor)
    db.add(a)
    db.flush()
    return a


def create_permit_type(db: Session, *, company_id: str, authority_id: str, code: str, name: str,
                       scope: str | None = None, validation_method: str | None = None,
                       actor: str | None = None) -> PermitType:
    company_id = _company(company_id, obj="tipo de permiso")
    _require_authority(db, company_id, authority_id)
    t = PermitType(company_id=company_id, authority_id=authority_id, code=code, name=name, scope=scope,
                   validation_method=validation_method, status="ACTIVE", created_by=actor)
    db.add(t)
    db.flush()
    return t


def create_official_registration(db: Session, *, company_id: str, authority_id: str, scope: str, ref_number: str,
                                 issued_at: date | None = None, expires_at: date | None = None,
                                 file_ref: str | None = None, actor: str | None = None) -> OfficialRegistration:
    company_id = _company(company_id, obj="registro oficial")
    _require_authority(db, company_id, authority_id)
    r = OfficialRegistration(company_id=company_id, authority_id=authority_id, scope=scope, ref_number=ref_number,
                             issued_at=issued_at, expires_at=expires_at, file_ref=file_ref, status="ACTIVE",
                             created_by=actor)
    db.add(r)
    db.flush()
    return r


def create_profile(db: Session, *, company_id: str, operation: str = "DESPACHO", rubric_id: str | None = None,
                   product_id: str | None = None, origin: str | None = None, destination: str | None = None,
                   required_documents: list[str] | None = None, validity: dict | None = None,
                   version: str = "1.0", actor: str | None = None) -> RegulatoryProfile:
    company_id = _company(company_id, obj="perfil regulatorio")
    p = RegulatoryProfile(company_id=company_id, rubric_id=rubric_id, product_id=product_id, operation=operation,
                          origin=origin, destination=destination,
                          required_documents=json.dumps(required_documents or []),
                          validity=json.dumps(validity or {}), version=version, status="ACTIVE", created_by=actor)
    db.add(p)
    db.flush()
    return p


def create_vehicle(db: Session, *, company_id: str, plate: str, vehicle_type: str | None = None,
                   capacity: float | None = None, owner_party_id: str | None = None,
                   documents: dict | None = None, actor: str | None = None) -> TransportVehicle:
    company_id = _company(company_id, obj="vehículo")
    v = TransportVehicle(company_id=company_id, plate=plate, vehicle_type=vehicle_type, capacity=capacity,
                         owner_party_id=owner_party_id, documents=json.dumps(documents or {}), status="ACTIVE",
                         created_by=actor)
    db.add(v)
    db.flush()
    return v


def create_driver(db: Session, *, company_id: str, party_id: str, license: str | None = None,
                  documents: dict | None = None, actor: str | None = None) -> TransportDriver:
    company_id = _company(company_id, obj="conductor")
    d = TransportDriver(company_id=company_id, party_id=party_id, license=license,
                        documents=json.dumps(documents or {}), status="ACTIVE", created_by=actor)
    db.add(d)
    db.flush()
    return d


# --------------------------------------------------------------------------- #
# Permisos y guías
# --------------------------------------------------------------------------- #
def create_permit(db: Session, *, company_id: str, permit_type_id: str, number: str, issued_at: date | None = None,
                  expires_at: date | None = None, origin: str | None = None, destination: str | None = None,
                  products: list[str] | None = None, lots: list[str] | None = None, quantity: float | None = None,
                  vehicle_id: str | None = None, file_ref: str | None = None,
                  actor: str | None = None) -> PermitInstance:
    company_id = _company(company_id, obj="permiso")
    pt = db.get(PermitType, permit_type_id)
    if not pt or pt.company_id != company_id:
        raise NotFoundError(code="PERMIT_TYPE_NOT_FOUND", message="Tipo de permiso no encontrado")
    p = PermitInstance(company_id=company_id, permit_type_id=permit_type_id, number=number, issued_at=issued_at,
                       expires_at=expires_at, origin=origin, destination=destination,
                       products=json.dumps(products or []), lots=json.dumps(lots or []), quantity=quantity,
                       vehicle_id=vehicle_id, file_ref=file_ref, status="DRAFT", created_by=actor)
    p.hash = _doc_hash(company_id, number, issued_at)
    db.add(p)
    db.flush()
    return p


def transition_permit(db: Session, *, company_id: str, permit_id: str, target: str,
                      actor: str | None = None) -> PermitInstance:
    permit = db.get(PermitInstance, permit_id)
    if not permit or permit.company_id != company_id:
        raise NotFoundError(code="PERMIT_NOT_FOUND", message="Permiso no encontrado")
    _assert_transition(permit.status, target, PERMIT_TRANSITIONS, "el permiso")
    permit.status = target
    permit.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="PERMIT_TRANSITIONED", entity_type="PermitInstance", entity_id=str(permit.id),
           company_id=company_id, actor=actor, after={"target": permit.status})
    return permit


def register_official_document(db: Session, *, company_id: str, kind: str, number: str,
                               authority_id: str | None = None, organism: str | None = None,
                               issued_at: date | None = None, expires_at: date | None = None,
                               file_ref: str | None = None, verification: str | None = None,
                               actor: str | None = None) -> OfficialDocument:
    """Registra una guía/documento oficial (SICA, SIGESAI, SACS). No fabrica permisos externos."""
    company_id = _company(company_id, obj="documento oficial")
    if kind not in ("SICA", "SIGESAI", "SACS", "GUIA_FISCAL", "OTRO"):
        raise KontrolError(code="INVALID_DOCUMENT_KIND", message="Tipo de documento oficial inválido", status_code=422)
    if authority_id:
        _require_authority(db, company_id, authority_id)
    doc = OfficialDocument(company_id=company_id, kind=kind, authority_id=authority_id, number=number,
                           organism=organism, issued_at=issued_at, expires_at=expires_at, file_ref=file_ref,
                           verification=verification, status="VALID", created_by=actor)
    doc.hash = _doc_hash(company_id, kind, number, organism)
    db.add(doc)
    db.flush()
    return doc


# --------------------------------------------------------------------------- #
# Evaluación y bloqueo del despacho (consume 005)
# --------------------------------------------------------------------------- #
def _applicable_profiles(db: Session, company_id: str, operation: str, product_id: str) -> list[RegulatoryProfile]:
    return list(db.execute(select(RegulatoryProfile).where(
        RegulatoryProfile.company_id == company_id, RegulatoryProfile.operation == operation,
        RegulatoryProfile.status == "ACTIVE",
        (RegulatoryProfile.product_id.is_(None)) | (RegulatoryProfile.product_id == product_id),
    ).order_by(RegulatoryProfile.version.desc())).scalars().all())


def _required_kinds(profiles: list[RegulatoryProfile]) -> list[str]:
    kinds: list[str] = []
    for p in profiles:
        try:
            required = json.loads(p.required_documents or "[]")
        except json.JSONDecodeError:
            required = []
        for k in required:
            if k not in kinds:
                kinds.append(k)
    return kinds


def evaluate_shipment(db: Session, *, company_id: str, shipment_id: str, actor: str | None = None) -> dict:
    """Evalúa cada línea del despacho de 005 y consolida requisitos del movimiento (FR-008-020/022)."""
    from app.modules.sales.models import Shipment, ShipmentLine

    company_id = _company(company_id, obj="evaluación regulatoria")
    shipment = db.get(Shipment, shipment_id)
    if not shipment or shipment.company_id != company_id:
        raise NotFoundError(code="SHIPMENT_NOT_FOUND", message="Despacho no encontrado")
    lines = db.execute(select(ShipmentLine).where(ShipmentLine.shipment_id == shipment_id)).scalars().all()

    created: list[RegulatoryEvaluation] = []
    for line in lines:
        profiles = _applicable_profiles(db, company_id, "DESPACHO", line.product_id)
        required = _required_kinds(profiles)
        blockers: list[dict] = []
        today = date.today()
        for kind in required:
            doc = db.execute(select(OfficialDocument).where(
                OfficialDocument.company_id == company_id, OfficialDocument.kind == kind,
                OfficialDocument.status == "VALID").order_by(OfficialDocument.created_at.desc())).scalars().first()
            if not doc:
                blockers.append({"kind": kind, "reason": "MISSING"})
            elif doc.expires_at and doc.expires_at < today:
                blockers.append({"kind": kind, "reason": "EXPIRED"})
        status = "BLOCKED" if blockers else "CLEARED"
        evaluation = RegulatoryEvaluation(company_id=company_id, shipment_id=shipment_id,
                                          shipment_line_ref=str(line.id), profile_version_id=profiles[0].id if profiles else None,
                                          required=json.dumps(required),
                                          # `quantity` es `Decimal` desde la Spec 011: se serializa como
                                          # texto para no perder precisión al pasar por `float`.
                                          results=json.dumps({"line": str(line.id),
                                                              "product_id": line.product_id,
                                                              "quantity": str(line.quantity)}),
                                          blockers=json.dumps(blockers), status=status, created_by=actor)
        db.add(evaluation)
        created.append(evaluation)
    db.flush()
    blocked = [e for e in created if e.status == "BLOCKED"]
    return {"shipment_id": shipment_id, "evaluated": len(created), "blocked": len(blocked), "status": "BLOCKED" if blocked else "CLEARED"}


def override_evaluation(db: Session, *, company_id: str, evaluation_id: str, reason: str,
                        actor: str | None = None) -> RegulatoryEvaluation:
    """Anula un bloqueo regulatorio (auditado) — FR-008-021."""
    evaluation = db.get(RegulatoryEvaluation, evaluation_id)
    if not evaluation or evaluation.company_id != company_id:
        raise NotFoundError(code="EVALUATION_NOT_FOUND", message="Evaluación regulatoria no encontrada")
    if evaluation.status != "BLOCKED":
        raise ConflictError(code="EVALUATION_NOT_BLOCKED", message="La evaluación no está bloqueada.")
    evaluation.status = "OVERRIDDEN"
    evaluation.override = json.dumps({"allowed_by": actor, "reason": reason, "at": datetime.now(UTC).isoformat()})
    evaluation.updated_at = datetime.now(UTC)
    db.flush()
    return evaluation


# --------------------------------------------------------------------------- #
# Contingencias y aprobaciones
# --------------------------------------------------------------------------- #
def create_contingency(db: Session, *, company_id: str, rule_ref: str, reason: str,
                       actor: str | None = None) -> RegulatoryContingency:
    """Habilita una contingencia solo con regla oficial versionada (FR-008-030)."""
    company_id = _company(company_id, obj="contingencia")
    if not rule_ref:
        raise KontrolError(code="RULE_REQUIRED", message="Se requiere una regla oficial versionada", status_code=422)
    c = RegulatoryContingency(company_id=company_id, rule_ref=rule_ref, reason=reason, allowed_by=actor,
                              started_at=datetime.now(UTC), status="ACTIVE", created_by=actor)
    db.add(c)
    db.flush()
    return c


def end_contingency(db: Session, *, company_id: str, contingency_id: str) -> RegulatoryContingency:
    c = db.get(RegulatoryContingency, contingency_id)
    if not c or c.company_id != company_id:
        raise NotFoundError(code="CONTINGENCY_NOT_FOUND", message="Contingencia no encontrada")
    c.status = "ENDED"
    c.ended_at = datetime.now(UTC)
    c.updated_at = datetime.now(UTC)
    db.flush()
    return c


def create_approval_request(db: Session, *, company_id: str, object_ref: str, rule_ref: str | None = None,
                            risk: str | None = None, amount: float | None = None, deadline: date | None = None,
                            actor: str | None = None) -> RegulatoryApprovalRequest:
    company_id = _company(company_id, obj="solicitud de aprobación")
    req = RegulatoryApprovalRequest(company_id=company_id, object_ref=object_ref, rule_ref=rule_ref, requester_id=actor,
                          approvers="[]", risk=risk, amount=amount, deadline=deadline, status="PENDING",
                          created_by=actor)
    db.add(req)
    db.flush()
    # Delegación en el motor transversal (Spec 045, FR-045-073/075). Sin política
    # activa no exige nada y el comportamiento es el anterior (AC-20).
    approvals_integration.require_for_document(
        db, company_id=company_id,
        process_type=approvals_integration.PROCESS_REGULATORY_APPROVAL,
        document_type="RegulatoryApprovalRequest", document_id=str(req.id),
        context={"amount": float(amount) if amount is not None else None,
                 "currency": "VED", "risk_class": risk, "rule_ref": rule_ref,
                 "object_ref": object_ref},
        actor=actor)
    return req


def transition_approval_request(db: Session, *, company_id: str, request_id: str, target: str,
                                actor: str | None = None) -> RegulatoryApprovalRequest:
    req = db.get(RegulatoryApprovalRequest, request_id)
    if not req or req.company_id != company_id:
        raise NotFoundError(code="APPROVAL_REQUEST_NOT_FOUND", message="Solicitud de aprobación no encontrada")
    _assert_transition(req.status, target, APPROVAL_TRANSITIONS, "la solicitud")
    if target == "APPROVED":
        approvals_integration.ensure_approved(
            db, company_id=company_id, document_type="RegulatoryApprovalRequest",
            document_id=str(req.id), what="la solicitud de aprobación")
    req.status = target
    req.decision = target
    req.updated_at = datetime.now(UTC)
    db.flush()
    _audit(db, action="APPROVAL_REQUEST_DECIDED", entity_type="RegulatoryApprovalRequest", entity_id=str(req.id),
           company_id=company_id, actor=actor, after={"target": req.status})
    return req
