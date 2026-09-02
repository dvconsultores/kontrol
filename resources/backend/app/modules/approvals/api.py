"""API del motor de aprobaciones (Spec 045, F4).

Convenciones heredadas: errores uniformes, permisos deny-by-default,
`allowed_actions` calculado en backend (Constitución P6).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.core.errors import NotFoundError
from app.modules.approvals import service as approvals_service
from app.modules.approvals.models import (
    ApprovalDelegation,
    ApprovalPolicy,
    ApprovalRequest,
    ApprovalRule,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/approvals", tags=["aprobaciones"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class PolicyCreate(BaseModel):
    #: Se conserva por compatibilidad; la empresa la decide el contexto.
    company_id: str | None = None
    process_type: str = Field(min_length=1, max_length=64)
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    base_currency: str = "VED"
    requires_segregation: bool = False
    allow_self_approval: bool = True
    distinct_actors_across_levels: bool = False


class PolicyUpdate(BaseModel):
    name: str | None = None
    base_currency: str | None = None
    requires_segregation: bool | None = None
    allow_self_approval: bool | None = None
    distinct_actors_across_levels: bool | None = None


class RuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    conditions: list[dict[str, Any]]
    condition_fields: list[str] | None = None
    sequence: int | None = None
    is_exception: bool = False
    risk_class: str | None = None


class LevelCreate(BaseModel):
    level_order: int = Field(ge=1)
    resolver_type: str
    resolver_ref: str
    quorum_type: str = "ANY"
    quorum_n: int | None = None
    can_delegate: bool = True
    sla_hours: int | None = None


class EvaluateIn(BaseModel):
    #: Se conserva por compatibilidad; la empresa la decide el contexto.
    company_id: str | None = None
    process_type: str
    context: dict[str, Any]
    #: Simula una política concreta, incluida una en borrador (FR-045-008).
    policy_id: str | None = None


class RequestIn(BaseModel):
    #: Se conserva por compatibilidad; la empresa la decide el contexto.
    company_id: str | None = None
    process_type: str
    document_type: str
    document_id: str
    context: dict[str, Any]


class DecisionIn(BaseModel):
    reason: str | None = None
    observations: str | None = None


class DelegationCreate(BaseModel):
    #: Se conserva por compatibilidad; la empresa la decide el contexto.
    company_id: str | None = None
    grantor_id: str
    grantee_id: str
    scope_process_type: str | None = None
    scope_branch_id: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    reason: str | None = None
    is_temporary_substitution: bool = False


def _policy_out(db: Session, policy: ApprovalPolicy) -> dict[str, Any]:
    rules = []
    for rule in approvals_service._policy_rules(db, str(policy.id)):
        rules.append({
            "id": str(rule.id), "name": rule.name, "sequence": rule.sequence,
            "conditions": rule.conditions, "condition_fields": rule.condition_fields,
            "is_exception": rule.is_exception, "risk_class": rule.risk_class,
            "levels": [
                {"id": str(lv.id), "level_order": lv.level_order, "resolver_type": lv.resolver_type,
                 "resolver_ref": lv.resolver_ref, "quorum_type": lv.quorum_type,
                 "quorum_n": lv.quorum_n, "can_delegate": lv.can_delegate, "sla_hours": lv.sla_hours}
                for lv in approvals_service._rule_levels(db, str(rule.id))
            ],
        })
    return {
        "id": str(policy.id), "company_id": policy.company_id, "process_type": policy.process_type,
        "code": policy.code, "name": policy.name, "version": policy.version, "status": policy.status,
        "valid_from": policy.valid_from, "valid_to": policy.valid_to,
        "requires_segregation": policy.requires_segregation,
        "allow_self_approval": policy.allow_self_approval,
        "distinct_actors_across_levels": policy.distinct_actors_across_levels,
        "base_currency": policy.base_currency, "rules": rules,
        "allowed_actions": (["edit", "activate", "add_rule"] if policy.status == "DRAFT"
                            else ["close"] if policy.status == "ACTIVE" else []),
    }


def _empresa(ctx: CompanyContext, declarada: str | None) -> str:
    """La empresa del contexto validado; el cuerpo, como mucho, la confirma.

    Antes estas rutas tomaban `company_id` de la petición, así que el cliente
    elegía en qué empresa escribir: operando en A se podía crear una política
    que quedaba guardada en B, y desde otro tenant se podía escribir dentro de
    este. Se conserva el campo por compatibilidad, pero contradecir el contexto
    ahora es un error, no una preferencia.
    """
    if declarada is not None and declarada != ctx.company_id:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    return ctx.company_id


def _get_policy(db: Session, ctx: CompanyContext, policy_id: str) -> ApprovalPolicy:
    policy = db.get(ApprovalPolicy, policy_id)
    if policy is None or policy.company_id != ctx.company_id:
        # Una política de otra empresa se responde como inexistente: confirmar
        # que existe ya sería enumerar la configuración ajena.
        raise NotFoundError(code="APPROVAL_POLICY_NOT_FOUND", message="Política no encontrada.")
    return policy


# --------------------------------------------------------------------------- #
# Políticas
# --------------------------------------------------------------------------- #
@router.get("/process-types")
def process_types(db: Session = Depends(get_db), user: User = Depends(require_permission("aprobaciones", "view"))):
    """Catálogo de tipos de proceso: se deriva de los datos, no de una lista fija (FR-045-006)."""
    rows = db.execute(select(ApprovalPolicy.process_type).distinct()).all()
    return {"items": sorted({r[0] for r in rows})}


@router.get("/policies")
def list_policies(process_type: str | None = None,
                  status: str | None = None, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("aprobaciones", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    # Antes, sin `company_id` en la petición, esto devolvía las políticas de
    # todas las empresas de todos los tenants.
    q = select(ApprovalPolicy).where(ApprovalPolicy.company_id == ctx.company_id)
    if process_type:
        q = q.where(ApprovalPolicy.process_type == process_type)
    if status:
        q = q.where(ApprovalPolicy.status == status)
    rows = db.execute(q.order_by(ApprovalPolicy.process_type, ApprovalPolicy.version.desc())).scalars().all()
    return {"items": [_policy_out(db, p) for p in rows]}


@router.post("/policies", status_code=201)
def create_policy(body: PolicyCreate, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("aprobaciones", "configure")),
                  _: None = Depends(require_write_allowed),
                  ctx: CompanyContext = Depends(get_company_context)):
    policy = approvals_service.create_policy(
        db, company_id=_empresa(ctx, body.company_id), process_type=body.process_type, code=body.code,
        name=body.name, base_currency=body.base_currency,
        requires_segregation=body.requires_segregation,
        allow_self_approval=body.allow_self_approval,
        distinct_actors_across_levels=body.distinct_actors_across_levels, actor=str(user.id))
    db.commit()
    db.refresh(policy)
    return _policy_out(db, policy)


@router.get("/policies/{policy_id}")
def get_policy(policy_id: str, db: Session = Depends(get_db),
               user: User = Depends(require_permission("aprobaciones", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    return _policy_out(db, _get_policy(db, ctx, policy_id))


@router.patch("/policies/{policy_id}")
def update_policy(policy_id: str, body: PolicyUpdate, db: Session = Depends(get_db),
                  user: User = Depends(require_permission("aprobaciones", "configure")),
                  _: None = Depends(require_write_allowed),
                  ctx: CompanyContext = Depends(get_company_context)):
    policy = _get_policy(db, ctx, policy_id)
    approvals_service.update_policy(db, policy=policy, actor=str(user.id),
                                    **body.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(policy)
    return _policy_out(db, policy)


@router.post("/policies/{policy_id}/activate")
def activate_policy(policy_id: str, db: Session = Depends(get_db),
                    user: User = Depends(require_permission("aprobaciones", "configure")),
                    _: None = Depends(require_write_allowed),
                  ctx: CompanyContext = Depends(get_company_context)):
    policy = approvals_service.activate_policy(db, policy=_get_policy(db, ctx, policy_id), actor=str(user.id))
    db.commit()
    db.refresh(policy)
    return _policy_out(db, policy)


@router.post("/policies/{policy_id}/close")
def close_policy(policy_id: str, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("aprobaciones", "configure")),
                 _: None = Depends(require_write_allowed),
                  ctx: CompanyContext = Depends(get_company_context)):
    policy = approvals_service.close_policy(db, policy=_get_policy(db, ctx, policy_id), actor=str(user.id))
    db.commit()
    db.refresh(policy)
    return _policy_out(db, policy)


@router.post("/policies/{policy_id}/rules", status_code=201)
def add_rule(policy_id: str, body: RuleCreate, db: Session = Depends(get_db),
             user: User = Depends(require_permission("aprobaciones", "configure")),
             _: None = Depends(require_write_allowed),
                  ctx: CompanyContext = Depends(get_company_context)):
    policy = _get_policy(db, ctx, policy_id)
    rule = approvals_service.add_rule(
        db, policy=policy, name=body.name, conditions=body.conditions,
        condition_fields=body.condition_fields, sequence=body.sequence,
        is_exception=body.is_exception, risk_class=body.risk_class, actor=str(user.id))
    db.commit()
    return {"id": str(rule.id), "name": rule.name, "condition_fields": rule.condition_fields}


@router.post("/policies/{policy_id}/rules/{rule_id}/levels", status_code=201)
def add_level(policy_id: str, rule_id: str, body: LevelCreate, db: Session = Depends(get_db),
              user: User = Depends(require_permission("aprobaciones", "configure")),
              _: None = Depends(require_write_allowed),
                  ctx: CompanyContext = Depends(get_company_context)):
    _get_policy(db, ctx, policy_id)
    rule = db.get(ApprovalRule, rule_id)
    if rule is None:
        raise NotFoundError(code="APPROVAL_RULE_NOT_FOUND", message="Regla no encontrada.")
    level = approvals_service.add_level(
        db, rule=rule, level_order=body.level_order, resolver_type=body.resolver_type,
        resolver_ref=body.resolver_ref, quorum_type=body.quorum_type, quorum_n=body.quorum_n,
        can_delegate=body.can_delegate, sla_hours=body.sla_hours, actor=str(user.id))
    db.commit()
    return {"id": str(level.id), "level_order": level.level_order}


# --------------------------------------------------------------------------- #
# Evaluación y solicitud
# --------------------------------------------------------------------------- #
@router.post("/evaluate")
def evaluate(body: EvaluateIn, db: Session = Depends(get_db),
             user: User = Depends(require_permission("aprobaciones", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """No crea nada: informa qué niveles aplicarían (FR-045-008)."""
    return approvals_service.evaluate(db, company_id=_empresa(ctx, body.company_id),
                                      process_type=body.process_type, context=body.context,
                                      policy_id=body.policy_id)


@router.post("/requests", status_code=201)
def create_request(body: RequestIn, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("aprobaciones", "create")),
                   _: None = Depends(require_write_allowed),
                   idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
                  ctx: CompanyContext = Depends(get_company_context)):
    result = approvals_service.require(
        db, company_id=_empresa(ctx, body.company_id), process_type=body.process_type,
        document_type=body.document_type, document_id=body.document_id,
        context=body.context, actor=str(user.id))
    db.commit()
    req = result.get("request")
    return {
        "requires_approval": result["requires_approval"],
        "idempotent_hit": result.get("idempotent_hit", False),
        "reason": result.get("reason"),
        "request_id": str(req.id) if req else None,
        "status": req.status if req else None,
    }


@router.get("/requests")
def list_requests(status: str | None = None, process_type: str | None = None,
                  db: Session = Depends(get_db),
                  user: User = Depends(require_permission("aprobaciones", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    q = select(ApprovalRequest).where(ApprovalRequest.company_id == ctx.company_id)
    if status:
        q = q.where(ApprovalRequest.status == status)
    if process_type:
        q = q.where(ApprovalRequest.process_type == process_type)
    rows = db.execute(q.order_by(ApprovalRequest.created_at.desc())).scalars().all()
    return {"items": [
        {"id": str(r.id), "process_type": r.process_type, "document_type": r.document_type,
         "document_id": r.document_id, "status": r.status, "policy_version": r.policy_version,
         "amount_base": float(r.amount_base) if r.amount_base is not None else None,
         "requested_by": r.requested_by, "requested_at": r.requested_at}
        for r in rows]}


@router.get("/requests/by-document")
def by_document(document_type: str, document_id: str,
                db: Session = Depends(get_db),
                user: User = Depends(require_permission("aprobaciones", "view")),
                ctx: CompanyContext = Depends(get_company_context)):
    company_id = ctx.company_id
    return approvals_service.status(db, company_id=company_id, document_type=document_type,
                                    document_id=document_id, actor_id=str(user.id))


@router.get("/requests/{request_id}")
def get_request(request_id: str, db: Session = Depends(get_db),
                user: User = Depends(require_permission("aprobaciones", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    req = db.get(ApprovalRequest, request_id)
    if req is not None and req.company_id != ctx.company_id:
        req = None
    if req is None:
        raise NotFoundError(code="APPROVAL_REQUEST_NOT_FOUND", message="Solicitud no encontrada.")
    data = approvals_service.status(db, company_id=req.company_id, document_type=req.document_type,
                                    document_id=req.document_id, actor_id=str(user.id))
    found = next((r for r in data["requests"] if r["id"] == str(req.id)), None)
    return found or data


@router.post("/requests/{request_id}/cancel")
def cancel_request(request_id: str, body: DecisionIn, db: Session = Depends(get_db),
                   user: User = Depends(require_permission("aprobaciones", "create")),
                   _: None = Depends(require_write_allowed),
                   ctx: CompanyContext = Depends(get_company_context)):
    req = approvals_service.cancel(db, company_id=ctx.company_id, request_id=request_id,
                                   actor_id=str(user.id), reason=body.reason)
    db.commit()
    return {"id": str(req.id), "status": req.status}


# --------------------------------------------------------------------------- #
# Bandeja y resolución
# --------------------------------------------------------------------------- #
@router.get("/inbox")
def get_inbox(process_type: str | None = None, only_overdue: bool = False,
              limit: int = 50, offset: int = 0, db: Session = Depends(get_db),
              user: User = Depends(require_permission("aprobaciones", "approve")),
                  ctx: CompanyContext = Depends(get_company_context)):
    return approvals_service.inbox(db, company_id=ctx.company_id, actor_id=str(user.id),
                                   process_type=process_type, only_overdue=only_overdue,
                                   limit=limit, offset=offset)


def _decide(db: Session, step_id: str, user: User, decision: str, body: DecisionIn,
            if_match: str | None) -> dict[str, Any]:
    expected = int(if_match) if if_match and if_match.isdigit() else None
    result = approvals_service.decide(db, step_id=step_id, actor_id=str(user.id), decision=decision,
                                      reason=body.reason, observations=body.observations,
                                      expected_version=expected)
    db.commit()
    req = result["request"]
    return {"request_id": str(req.id), "status": req.status,
            "step_status": result["step"].status,
            "quorum_pending": result.get("quorum_pending", False),
            "next_level": result.get("next_level")}


@router.post("/steps/{step_id}/approve")
def approve_step(step_id: str, body: DecisionIn, db: Session = Depends(get_db),
                 user: User = Depends(require_permission("aprobaciones", "approve")),
                 _: None = Depends(require_write_allowed),
                 if_match: str | None = Header(default=None, alias="If-Match")):
    return _decide(db, step_id, user, "APPROVE", body, if_match)


@router.post("/steps/{step_id}/reject")
def reject_step(step_id: str, body: DecisionIn, db: Session = Depends(get_db),
                user: User = Depends(require_permission("aprobaciones", "approve")),
                _: None = Depends(require_write_allowed),
                if_match: str | None = Header(default=None, alias="If-Match")):
    return _decide(db, step_id, user, "REJECT", body, if_match)


@router.post("/steps/{step_id}/return")
def return_step(step_id: str, body: DecisionIn, db: Session = Depends(get_db),
                user: User = Depends(require_permission("aprobaciones", "approve")),
                _: None = Depends(require_write_allowed),
                if_match: str | None = Header(default=None, alias="If-Match")):
    return _decide(db, step_id, user, "RETURN", body, if_match)


# --------------------------------------------------------------------------- #
# Delegaciones
# --------------------------------------------------------------------------- #
@router.get("/delegations")
def list_delegations(db: Session = Depends(get_db),
                     user: User = Depends(require_permission("aprobaciones", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    rows = db.execute(
        select(ApprovalDelegation).where(ApprovalDelegation.company_id == ctx.company_id)
        .order_by(ApprovalDelegation.created_at.desc())
    ).scalars().all()
    return {"items": [
        {"id": str(d.id), "grantor_id": d.grantor_id, "grantee_id": d.grantee_id,
         "scope_process_type": d.scope_process_type, "valid_from": d.valid_from,
         "valid_to": d.valid_to, "reason": d.reason,
         "is_temporary_substitution": d.is_temporary_substitution,
         "revoked_at": d.revoked_at,
         "status": "REVOKED" if d.revoked_at else "ACTIVE"}
        for d in rows]}


@router.post("/delegations", status_code=201)
def create_delegation(body: DelegationCreate, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("aprobaciones", "delegate")),
                      _: None = Depends(require_write_allowed),
                  ctx: CompanyContext = Depends(get_company_context)):
    d = approvals_service.create_delegation(
        db, company_id=_empresa(ctx, body.company_id), grantor_id=body.grantor_id, grantee_id=body.grantee_id,
        scope_process_type=body.scope_process_type, scope_branch_id=body.scope_branch_id,
        valid_from=body.valid_from, valid_to=body.valid_to, reason=body.reason,
        is_temporary_substitution=body.is_temporary_substitution, actor=str(user.id))
    db.commit()
    return {"id": str(d.id), "status": "ACTIVE"}


@router.post("/delegations/{delegation_id}/revoke")
def revoke_delegation(delegation_id: str, db: Session = Depends(get_db),
                      user: User = Depends(require_permission("aprobaciones", "delegate")),
                      _: None = Depends(require_write_allowed),
                  ctx: CompanyContext = Depends(get_company_context)):
    d = db.get(ApprovalDelegation, delegation_id)
    if d is not None and d.company_id != ctx.company_id:
        d = None
    if d is None:
        raise NotFoundError(code="APPROVAL_DELEGATION_NOT_FOUND", message="Delegación no encontrada.")
    approvals_service.revoke_delegation(db, delegation=d, actor=str(user.id))
    db.commit()
    return {"id": str(d.id), "status": "REVOKED"}
