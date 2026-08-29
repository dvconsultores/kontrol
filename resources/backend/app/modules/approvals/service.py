"""Motor transversal de aprobaciones (Spec 045, fases F2 y F3).

Regla de acoplamiento (`plan.md` §1): este módulo **no importa ningún módulo de
dominio**. Recibe un `context` plano construido por el consumidor, de modo que
un `process_type` nuevo no obliga a tocar el motor (FR-045-006) y el motor puede
probarse sin ningún dominio.

Fachada de consumo (`plan.md` §2):
    evaluate(...)  -> qué niveles aplicarían, sin efectos secundarios
    require(...)   -> crea la solicitud (idempotente) o indica que no requiere
    status(...)    -> estado, pasos, decisiones y allowed_actions
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.modules.approvals.models import (
    ApprovalDecision,
    ApprovalDelegation,
    ApprovalEvent,
    ApprovalLevel,
    ApprovalPolicy,
    ApprovalRequest,
    ApprovalRule,
    ApprovalStep,
)
from app.shared import audit as audit_service

# --------------------------------------------------------------------------- #
# Máquinas de estado (`state-machines.md`)
# --------------------------------------------------------------------------- #
REQUEST_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"PENDING", "CANCELLED"},
    "PENDING": {"IN_REVIEW", "CANCELLED", "OBSOLETE"},
    "IN_REVIEW": {"IN_REVIEW", "APPROVED", "REJECTED", "RETURNED", "CANCELLED", "OBSOLETE"},
    "APPROVED": set(),
    "REJECTED": set(),
    "RETURNED": set(),
    "CANCELLED": set(),
    "OBSOLETE": set(),
}
TERMINAL_REQUEST_STATES = {"APPROVED", "REJECTED", "RETURNED", "CANCELLED", "OBSOLETE"}
OPEN_REQUEST_STATES = {"PENDING", "IN_REVIEW"}

STEP_TRANSITIONS: dict[str, set[str]] = {
    "PENDING": {"IN_REVIEW", "SKIPPED"},
    "IN_REVIEW": {"APPROVED", "REJECTED", "RETURNED", "EXPIRED"},
    "APPROVED": set(),
    "REJECTED": set(),
    "RETURNED": set(),
    "EXPIRED": {"IN_REVIEW"},  # el vencimiento marca, no resuelve (CL-045-06)
    "SKIPPED": set(),
}


def _audit(db: Session, *, action: str, entity_type: str, entity_id: str,
           company_id: str, actor: str | None = None, **kw: Any) -> None:
    """Auditoría de negocio del motor (FR-045-064, ADR-012)."""
    audit_service.record_audit(
        db, action=action, entity_type=entity_type, entity_id=entity_id,
        company_id=company_id, user_id=actor, source="API", **kw,
    )


def _emit(db: Session, *, company_id: str, event_type: str, request_id: str | None = None,
          step_id: str | None = None, payload: dict[str, Any] | None = None) -> ApprovalEvent:
    """Emite un evento de dominio (FR-045-066). El motor no notifica: emite."""
    ev = ApprovalEvent(company_id=company_id, request_id=request_id, step_id=step_id,
                       event_type=event_type, payload=payload or {}, occurred_at=datetime.now(UTC))
    db.add(ev)
    db.flush()
    return ev


# --------------------------------------------------------------------------- #
# ConditionEvaluator (FR-045-010/013/015)
# --------------------------------------------------------------------------- #
_OPERATORS = {
    "eq", "ne", "gt", "gte", "lt", "lte", "in", "not_in", "is_true", "is_false", "is_null", "not_null",
}


class ConditionUnevaluable(Exception):
    """El contexto no trae un dato requerido por la condición (FR-045-015)."""

    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(field)


def _coerce(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _eval_predicate(pred: dict[str, Any], context: dict[str, Any]) -> bool:
    field = str(pred.get("field") or "")
    operator = pred.get("operator")
    expected = pred.get("value")
    if operator not in _OPERATORS:
        raise ConflictError(code="APPROVAL_CONDITION_INVALID_OPERATOR",
                            message=f"Operador no soportado: {operator}")
    if operator in {"is_null", "not_null"}:
        present = context.get(field) is not None
        return (not present) if operator == "is_null" else present
    if field not in context or context.get(field) is None:
        raise ConditionUnevaluable(str(field))
    actual = _coerce(context[field])
    expected = _coerce(expected)
    if operator == "eq":
        return actual == expected
    if operator == "ne":
        return actual != expected
    if operator == "in":
        return actual in (expected or [])
    if operator == "not_in":
        return actual not in (expected or [])
    if operator == "is_true":
        return bool(actual) is True
    if operator == "is_false":
        return bool(actual) is False
    # Comparaciones numéricas
    try:
        a, e = float(actual), float(expected)
    except (TypeError, ValueError):
        raise ConditionUnevaluable(str(field)) from None
    return {"gt": a > e, "gte": a >= e, "lt": a < e, "lte": a <= e}[operator]


def evaluate_rule(rule: ApprovalRule, context: dict[str, Any]) -> bool:
    """Todos los predicados con AND. El OR se expresa con varias reglas."""
    for pred in rule.conditions or []:
        if not _eval_predicate(pred, context):
            return False
    return True


# --------------------------------------------------------------------------- #
# Moneda base (FR-045-011) — tasa snapshot del documento, no la del día
# --------------------------------------------------------------------------- #
def compute_amount_base(context: dict[str, Any], base_currency: str) -> float | None:
    amount = context.get("amount")
    if amount is None:
        return None
    currency = context.get("currency") or base_currency
    if currency == base_currency:
        return float(amount)
    rate = context.get("rate_snapshot")
    if rate is None:
        raise ConditionUnevaluable("rate_snapshot")
    return float(amount) * float(rate)


# --------------------------------------------------------------------------- #
# PolicyResolver (FR-045-001)
# --------------------------------------------------------------------------- #
def get_active_policy(db: Session, *, company_id: str, process_type: str) -> ApprovalPolicy | None:
    return db.execute(
        select(ApprovalPolicy).where(
            ApprovalPolicy.company_id == company_id,
            ApprovalPolicy.process_type == process_type,
            ApprovalPolicy.status == "ACTIVE",
        ).order_by(ApprovalPolicy.version.desc())
    ).scalars().first()


def _policy_rules(db: Session, policy_id: str) -> list[ApprovalRule]:
    return list(db.execute(
        select(ApprovalRule).where(ApprovalRule.policy_id == policy_id).order_by(ApprovalRule.sequence)
    ).scalars().all())


def _rule_levels(db: Session, rule_id: str) -> list[ApprovalLevel]:
    return list(db.execute(
        select(ApprovalLevel).where(ApprovalLevel.rule_id == rule_id).order_by(ApprovalLevel.level_order)
    ).scalars().all())


# --------------------------------------------------------------------------- #
# FingerprintService (FR-045-050) — huella sobre los campos de condición
# --------------------------------------------------------------------------- #
def compute_fingerprint(context: dict[str, Any], fields: list[str]) -> str:
    subset = {f: _coerce(context.get(f)) for f in sorted(set(fields))}
    canonical = json.dumps(subset, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# ActorResolver (FR-045-014/040/042)
# --------------------------------------------------------------------------- #
def active_delegations(db: Session, *, company_id: str, process_type: str,
                       now: datetime | None = None) -> list[ApprovalDelegation]:
    now = now or datetime.now(UTC)
    rows = db.execute(
        select(ApprovalDelegation).where(
            ApprovalDelegation.company_id == company_id,
            ApprovalDelegation.revoked_at.is_(None),
        )
    ).scalars().all()
    out: list[ApprovalDelegation] = []
    for d in rows:
        if d.scope_process_type and d.scope_process_type != process_type:
            continue
        if d.valid_from and _as_utc(d.valid_from) > now:
            continue
        if d.valid_to and _as_utc(d.valid_to) < now:
            continue
        out.append(d)
    return out


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def resolve_actors(db: Session, *, company_id: str, level: dict[str, Any],
                   policy: ApprovalPolicy, requested_by: str | None,
                   used_actors: set[str]) -> list[str]:
    """Actores elegibles para un nivel, congelados al abrir el paso.

    Aplica segregación (el creador no resuelve) y distinción entre niveles.
    La delegación NO amplía la elegibilidad aquí: se resuelve en la decisión,
    para que el delegado herede siempre las restricciones del delegante
    (`ADR-D0-002` R-D0-02-8, FR-045-043).
    """
    from app.modules.identity_access.models import Role, User, UserRole

    resolver_type = level.get("resolver_type")
    ref = level.get("resolver_ref")
    actors: list[str] = []
    if resolver_type == "USER":
        actors = [ref] if ref else []
    elif resolver_type == "ROLE":
        role = db.execute(select(Role).where(Role.code == ref)).scalars().first()
        if role:
            rows = db.execute(select(UserRole.user_id).where(UserRole.role_id == role.id)).all()
            actors = [r[0] for r in rows]
    elif resolver_type == "SCOPE_OWNER":
        scope_rows = db.execute(select(User.id).where(User.status == "ACTIVE")).all()
        actors = [str(r[0]) for r in scope_rows]

    if policy.requires_segregation and requested_by:
        actors = [a for a in actors if str(a) != str(requested_by)]
    if not policy.allow_self_approval and requested_by:
        actors = [a for a in actors if str(a) != str(requested_by)]
    if policy.distinct_actors_across_levels and used_actors:
        actors = [a for a in actors if str(a) not in used_actors]
    return [str(a) for a in dict.fromkeys(actors)]


# --------------------------------------------------------------------------- #
# Fachada: evaluate (FR-045-008/010)
# --------------------------------------------------------------------------- #
def evaluate(db: Session, *, company_id: str, process_type: str,
             context: dict[str, Any]) -> dict[str, Any]:
    """Determina si la operación requiere aprobación. Sin efectos secundarios."""
    policy = get_active_policy(db, company_id=company_id, process_type=process_type)
    if not policy:
        return {"requires_approval": False, "reason": "NO_ACTIVE_POLICY"}

    ctx = dict(context)
    try:
        amount_base = compute_amount_base(ctx, policy.base_currency)
    except ConditionUnevaluable as exc:
        raise KontrolError(code="APPROVAL_CONDITION_UNEVALUABLE",
                           message=f"No se puede evaluar la política: falta '{exc.field}'",
                           status_code=422) from None
    if amount_base is not None:
        ctx["amount_base"] = amount_base

    matched: list[ApprovalRule] = []
    fingerprint_fields: set[str] = set()
    try:
        for rule in _policy_rules(db, str(policy.id)):
            fingerprint_fields.update(rule.condition_fields or [])
            if evaluate_rule(rule, ctx):
                matched.append(rule)
    except ConditionUnevaluable as exc:
        raise KontrolError(code="APPROVAL_CONDITION_UNEVALUABLE",
                           message=f"No se puede evaluar la política: falta '{exc.field}'",
                           status_code=422) from None

    if not matched:
        return {"requires_approval": False, "reason": "NO_RULE_MATCHED",
                "policy_id": str(policy.id), "policy_version": policy.version}

    # Acumular niveles sin duplicar, conservando el orden (FR-045-013)
    levels_by_order: dict[int, dict[str, Any]] = {}
    for rule in matched:
        for lv in _rule_levels(db, str(rule.id)):
            levels_by_order.setdefault(lv.level_order, {
                "level_order": lv.level_order,
                "resolver_type": lv.resolver_type,
                "resolver_ref": lv.resolver_ref,
                "quorum_type": lv.quorum_type,
                "quorum_n": lv.quorum_n,
                "can_delegate": lv.can_delegate,
                "sla_hours": lv.sla_hours,
            })
    levels = [levels_by_order[k] for k in sorted(levels_by_order)]
    return {
        "requires_approval": True,
        "policy_id": str(policy.id),
        "policy_version": policy.version,
        "amount_base": amount_base,
        "base_currency": policy.base_currency,
        "levels": levels,
        "fingerprint_fields": sorted(fingerprint_fields),
        "matched_rules": [str(r.id) for r in matched],
    }


# --------------------------------------------------------------------------- #
# F3 · Ciclo de la solicitud
# --------------------------------------------------------------------------- #
def _assert_request_transition(current: str, target: str) -> None:
    if target not in REQUEST_TRANSITIONS.get(current, set()):
        raise ConflictError(
            code="APPROVAL_INVALID_TRANSITION",
            message=f"Transición no permitida de {current} a {target}.",
        )


def _open_step(db: Session, request: ApprovalRequest, policy: ApprovalPolicy,
               level: dict[str, Any], used_actors: set[str]) -> ApprovalStep:
    """Abre un paso y CONGELA sus actores elegibles (FR-045-014)."""
    actors = resolve_actors(db, company_id=request.company_id, level=level, policy=policy,
                            requested_by=request.requested_by, used_actors=used_actors)
    now = datetime.now(UTC)
    sla = level.get("sla_hours")
    step = ApprovalStep(
        request_id=str(request.id),
        level_order=int(level["level_order"]),
        quorum_type=level.get("quorum_type") or "ANY",
        quorum_n=level.get("quorum_n"),
        eligible_actors=actors,
        status="IN_REVIEW",
        opened_at=now,
        due_at=now + timedelta(hours=int(sla)) if sla else None,
        version=1,
    )
    db.add(step)
    db.flush()
    request.current_level = step.level_order
    _emit(db, company_id=request.company_id, event_type="approval.step_opened",
          request_id=str(request.id), step_id=str(step.id),
          payload={"level_order": step.level_order, "eligible": len(actors)})
    return step


def require(db: Session, *, company_id: str, process_type: str, document_type: str,
            document_id: str, context: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
    """Punto de entrada de los dominios (FR-045-020). Idempotente (FR-045-053).

    El dominio NO decide si hay aprobación: pregunta. Esa inversión es lo que
    impide que reaparezca una quinta implementación (Constitución P22).
    """
    result = evaluate(db, company_id=company_id, process_type=process_type, context=context)
    if not result.get("requires_approval"):
        return {"requires_approval": False, "request": None, "reason": result.get("reason")}

    policy = db.get(ApprovalPolicy, result["policy_id"])
    if policy is None:  # pragma: no cover - defensivo
        raise NotFoundError(code="APPROVAL_POLICY_NOT_FOUND", message="Política no encontrada.")

    ctx = dict(context)
    if result.get("amount_base") is not None:
        ctx["amount_base"] = result["amount_base"]
    fingerprint = compute_fingerprint(ctx, result["fingerprint_fields"])

    # Idempotencia: misma solicitud viva para el mismo documento y huella
    existing = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.company_id == company_id,
            ApprovalRequest.document_type == document_type,
            ApprovalRequest.document_id == document_id,
            ApprovalRequest.fingerprint == fingerprint,
            ApprovalRequest.status.in_(tuple(OPEN_REQUEST_STATES)),
        )
    ).scalars().first()
    if existing:
        return {"requires_approval": True, "request": existing, "idempotent_hit": True}

    # Una huella nueva deja obsoletas las solicitudes vivas del mismo documento
    _obsolete_open_requests(db, company_id=company_id, document_type=document_type,
                            document_id=document_id, keep_fingerprint=fingerprint)

    request = ApprovalRequest(
        company_id=company_id,
        process_type=process_type,
        document_type=document_type,
        document_id=document_id,
        policy_id=str(policy.id),
        policy_version=str(policy.version),
        policy_snapshot={
            "policy_id": str(policy.id), "version": policy.version,
            "requires_segregation": policy.requires_segregation,
            "allow_self_approval": policy.allow_self_approval,
            "distinct_actors_across_levels": policy.distinct_actors_across_levels,
            "base_currency": policy.base_currency,
            "levels": result["levels"],
            "matched_rules": result["matched_rules"],
        },
        fingerprint=fingerprint,
        fingerprint_fields=result["fingerprint_fields"],
        amount_base=result.get("amount_base"),
        base_currency=policy.base_currency,
        rate_snapshot=context.get("rate_snapshot"),
        requested_by=actor,
        requested_at=datetime.now(UTC),
        status="PENDING",
        idempotency_key=f"{document_type}:{document_id}:{fingerprint}",
    )
    db.add(request)
    db.flush()

    _assert_request_transition(request.status, "IN_REVIEW")
    request.status = "IN_REVIEW"
    _open_step(db, request, policy, result["levels"][0], used_actors=set())

    _emit(db, company_id=company_id, event_type="approval.requested", request_id=str(request.id),
          payload={"process_type": process_type, "levels": len(result["levels"])})
    _audit(db, action="APPROVAL_REQUESTED", entity_type="ApprovalRequest", entity_id=str(request.id),
           company_id=company_id, actor=actor,
           after={"document": f"{document_type}:{document_id}", "policy_version": policy.version,
                  "levels": len(result["levels"])})
    return {"requires_approval": True, "request": request, "idempotent_hit": False}


def _obsolete_open_requests(db: Session, *, company_id: str, document_type: str,
                            document_id: str, keep_fingerprint: str | None = None) -> int:
    """Marca OBSOLETE las solicitudes vivas cuya huella ya no corresponde (FR-045-051)."""
    rows = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.company_id == company_id,
            ApprovalRequest.document_type == document_type,
            ApprovalRequest.document_id == document_id,
            ApprovalRequest.status.in_(tuple(OPEN_REQUEST_STATES)),
        )
    ).scalars().all()
    count = 0
    for req in rows:
        if keep_fingerprint and req.fingerprint == keep_fingerprint:
            continue
        _assert_request_transition(req.status, "OBSOLETE")
        req.status = "OBSOLETE"
        req.resolved_at = datetime.now(UTC)
        req.resolution_reason = "El documento cambió después de solicitar la aprobación."
        for step in _steps(db, str(req.id)):
            if step.status in {"PENDING", "IN_REVIEW"}:
                step.status = "SKIPPED"
                step.closed_at = datetime.now(UTC)
        _emit(db, company_id=company_id, event_type="approval.obsolete", request_id=str(req.id))
        _audit(db, action="APPROVAL_OBSOLETE", entity_type="ApprovalRequest", entity_id=str(req.id),
               company_id=company_id, before={"status": "IN_REVIEW"}, after={"status": "OBSOLETE"})
        count += 1
    db.flush()
    return count


def document_changed(db: Session, *, company_id: str, document_type: str, document_id: str,
                     context: dict[str, Any]) -> int:
    """Notificación del dominio: el documento cambió (FR-045-051).

    Recalcula la huella y marca obsoletas las solicitudes que ya no
    corresponden. No aprueba nada en silencio (regla 7 del encargo).
    """
    open_reqs = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.company_id == company_id,
            ApprovalRequest.document_type == document_type,
            ApprovalRequest.document_id == document_id,
            ApprovalRequest.status.in_(tuple(OPEN_REQUEST_STATES)),
        )
    ).scalars().all()
    changed = 0
    for req in open_reqs:
        ctx = dict(context)
        policy = db.get(ApprovalPolicy, req.policy_id) if req.policy_id else None
        if policy is not None:
            try:
                base = compute_amount_base(ctx, policy.base_currency)
            except ConditionUnevaluable:
                base = None
            if base is not None:
                ctx["amount_base"] = base
        new_fp = compute_fingerprint(ctx, list(req.fingerprint_fields or []))
        if new_fp != req.fingerprint:
            _obsolete_open_requests(db, company_id=company_id, document_type=document_type,
                                    document_id=document_id, keep_fingerprint=None)
            changed += 1
            break
    return changed


def _steps(db: Session, request_id: str) -> list[ApprovalStep]:
    return list(db.execute(
        select(ApprovalStep).where(ApprovalStep.request_id == request_id).order_by(ApprovalStep.level_order)
    ).scalars().all())


def _decisions(db: Session, step_id: str) -> list[ApprovalDecision]:
    return list(db.execute(
        select(ApprovalDecision).where(ApprovalDecision.step_id == step_id)
    ).scalars().all())


# --------------------------------------------------------------------------- #
# Resolución de pasos (FR-045-022..028, 040..046, 054..055)
# --------------------------------------------------------------------------- #
def _resolve_delegation(db: Session, *, company_id: str, process_type: str,
                        actor_id: str, eligible: list[str]) -> ApprovalDelegation | None:
    """Delegación vigente que habilita a `actor_id` a actuar por un elegible.

    La delegación NO amplía lo que la segregación prohíbe: sólo puede actuar por
    alguien que YA figura como elegible (FR-045-043).
    """
    for d in active_delegations(db, company_id=company_id, process_type=process_type):
        if str(d.grantee_id) == str(actor_id) and str(d.grantor_id) in eligible:
            return d
    return None


def _assert_can_decide(db: Session, *, request: ApprovalRequest, step: ApprovalStep,
                       actor_id: str) -> ApprovalDelegation | None:
    """Autoridad de decisión. El backend decide; ocultar un botón no es control (P6)."""
    if step.status != "IN_REVIEW":
        raise ConflictError(code="APPROVAL_STEP_NOT_OPEN",
                            message="El paso no está abierto para decisión.")
    if request.status == "OBSOLETE":
        raise ConflictError(code="APPROVAL_REQUEST_OBSOLETE",
                            message="El documento cambió después de solicitar la aprobación.")
    if request.status not in OPEN_REQUEST_STATES:
        raise ConflictError(code="APPROVAL_REQUEST_NOT_OPEN",
                            message="La solicitud ya está resuelta.")

    snapshot = request.policy_snapshot or {}
    eligible = [str(a) for a in (step.eligible_actors or [])]

    # Segregación y autoaprobación se comprueban contra el snapshot congelado
    if str(actor_id) == str(request.requested_by or ""):
        if snapshot.get("requires_segregation"):
            raise PermissionDeniedError(
                code="APPROVAL_SEGREGATION_VIOLATION",
                message="Quien crea el documento no puede aprobarlo (segregación de funciones).",
                status_code=403)
        if snapshot.get("allow_self_approval") is False:
            raise PermissionDeniedError(
                code="APPROVAL_SELF_APPROVAL_DENIED",
                message="La política no permite la autoaprobación.",
                status_code=403)

    delegation: ApprovalDelegation | None = None
    if str(actor_id) not in eligible:
        delegation = _resolve_delegation(db, company_id=request.company_id,
                                         process_type=request.process_type,
                                         actor_id=str(actor_id), eligible=eligible)
        if delegation is None:
            raise PermissionDeniedError(
                code="APPROVAL_NOT_ELIGIBLE",
                message="No figura entre los aprobadores de este nivel.",
                status_code=403)
        # El delegado hereda las restricciones del delegante (FR-045-043)
        if str(delegation.grantor_id) == str(request.requested_by or "") and snapshot.get("requires_segregation"):
            raise PermissionDeniedError(
                code="APPROVAL_SEGREGATION_VIOLATION",
                message="La delegación no habilita lo que la segregación prohíbe.",
                status_code=403)

    already = db.execute(
        select(ApprovalDecision).where(
            ApprovalDecision.step_id == str(step.id),
            ApprovalDecision.actor_id == str(actor_id),
        )
    ).scalars().first()
    if already:
        raise ConflictError(code="APPROVAL_DUPLICATE_DECISION",
                            message="Ya registró una decisión sobre este paso.")
    return delegation


def _lock_step(db: Session, step_id: str) -> ApprovalStep:
    """Bloquea la fila del paso dentro de la transacción (ADR-013, FR-045-054).

    En PostgreSQL usa `SELECT … FOR UPDATE`; en SQLite el dialecto lo ignora y
    la protección efectiva queda en el control de versión y en la restricción
    única `(step_id, actor_id)`. Por eso la prueba de concurrencia es criterio
    de salida sobre PostgreSQL (Constitución P21).
    """
    stmt = select(ApprovalStep).where(ApprovalStep.id == step_id)
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        stmt = stmt.with_for_update()
    step = db.execute(stmt).scalars().first()
    if step is None:
        raise NotFoundError(code="APPROVAL_STEP_NOT_FOUND", message="Paso no encontrado.")
    return step


def _used_actors(db: Session, request_id: str) -> set[str]:
    used: set[str] = set()
    for step in _steps(db, request_id):
        for dec in _decisions(db, str(step.id)):
            used.add(str(dec.actor_id))
    return used


def _quorum_reached(step: ApprovalStep, approvals: int) -> bool:
    if step.quorum_type == "ANY":
        return approvals >= 1
    if step.quorum_type == "ALL":
        return approvals >= max(1, len(step.eligible_actors or []))
    if step.quorum_type == "N_OF_M":
        return approvals >= max(1, int(step.quorum_n or 1))
    return approvals >= 1


def decide(db: Session, *, step_id: str, actor_id: str, decision: str,
           reason: str | None = None, observations: str | None = None,
           expected_version: int | None = None) -> dict[str, Any]:
    """Registra una decisión y avanza la solicitud. Transaccional (FR-045-055)."""
    decision = decision.upper()
    if decision not in {"APPROVE", "REJECT", "RETURN"}:
        raise ConflictError(code="APPROVAL_INVALID_DECISION", message="Decisión no soportada.")
    if decision in {"REJECT", "RETURN"} and not (reason or "").strip():
        raise KontrolError(code="APPROVAL_REASON_REQUIRED",
                           message="Debe indicar el motivo.", status_code=422)

    step = _lock_step(db, step_id)
    if expected_version is not None and int(expected_version) != int(step.version):
        raise ConflictError(code="APPROVAL_STEP_VERSION_CONFLICT",
                            message="Otro aprobador resolvió este paso. Recargue para ver el estado actual.")
    request = db.get(ApprovalRequest, step.request_id)
    if request is None:  # pragma: no cover - defensivo
        raise NotFoundError(code="APPROVAL_REQUEST_NOT_FOUND", message="Solicitud no encontrada.")

    delegation = _assert_can_decide(db, request=request, step=step, actor_id=actor_id)

    now = datetime.now(UTC)
    dec = ApprovalDecision(
        step_id=str(step.id), actor_id=str(actor_id),
        on_behalf_of_id=str(delegation.grantor_id) if delegation else None,
        delegation_id=str(delegation.id) if delegation else None,
        decision=decision, reason=reason, observations=observations, decided_at=now,
    )
    db.add(dec)
    step.version = int(step.version) + 1
    db.flush()

    _emit(db, company_id=request.company_id, event_type="approval.decided",
          request_id=str(request.id), step_id=str(step.id),
          payload={"decision": decision, "by_delegation": bool(delegation)})
    _audit(db, action=f"APPROVAL_{decision}", entity_type="ApprovalStep", entity_id=str(step.id),
           company_id=request.company_id, actor=str(actor_id), reason=reason,
           before={"step_status": step.status},
           after={"decision": decision, "level_order": step.level_order,
                  "on_behalf_of": str(delegation.grantor_id) if delegation else None})

    # Una decisión negativa cierra el paso y la solicitud, cualquiera sea el cuórum
    if decision in {"REJECT", "RETURN"}:
        target_step = "REJECTED" if decision == "REJECT" else "RETURNED"
        step.status = target_step
        step.closed_at = now
        for other in _steps(db, str(request.id)):
            if other.status in {"PENDING", "IN_REVIEW"} and str(other.id) != str(step.id):
                other.status = "SKIPPED"
                other.closed_at = now
        target_req = "REJECTED" if decision == "REJECT" else "RETURNED"
        _assert_request_transition(request.status, target_req)
        request.status = target_req
        request.resolved_at = now
        request.resolution_reason = reason
        request.current_level = None
        db.flush()
        _emit(db, company_id=request.company_id, event_type="approval.resolved",
              request_id=str(request.id), payload={"status": target_req})
        return {"request": request, "step": step, "status": request.status}

    approvals = len([d for d in _decisions(db, str(step.id)) if d.decision == "APPROVE"])
    if not _quorum_reached(step, approvals):
        return {"request": request, "step": step, "status": request.status, "quorum_pending": True}

    step.status = "APPROVED"
    step.closed_at = now
    db.flush()

    snapshot = request.policy_snapshot or {}
    levels = snapshot.get("levels") or []
    next_level = next((lv for lv in levels if int(lv["level_order"]) > int(step.level_order)), None)
    if next_level is None:
        _assert_request_transition(request.status, "APPROVED")
        request.status = "APPROVED"
        request.resolved_at = now
        request.current_level = None
        db.flush()
        _emit(db, company_id=request.company_id, event_type="approval.resolved",
              request_id=str(request.id), payload={"status": "APPROVED"})
        return {"request": request, "step": step, "status": "APPROVED"}

    policy = db.get(ApprovalPolicy, request.policy_id)
    if policy is not None:
        _open_step(db, request, policy, next_level, used_actors=_used_actors(db, str(request.id)))
    db.flush()
    return {"request": request, "step": step, "status": request.status, "next_level": next_level["level_order"]}


def cancel(db: Session, *, request_id: str, actor_id: str, reason: str | None = None) -> ApprovalRequest:
    """Cancela una solicitud viva (FR-045-025)."""
    request = db.get(ApprovalRequest, request_id)
    if request is None:
        raise NotFoundError(code="APPROVAL_REQUEST_NOT_FOUND", message="Solicitud no encontrada.")
    _assert_request_transition(request.status, "CANCELLED")
    now = datetime.now(UTC)
    for step in _steps(db, str(request.id)):
        if step.status in {"PENDING", "IN_REVIEW"}:
            step.status = "SKIPPED"
            step.closed_at = now
    request.status = "CANCELLED"
    request.resolved_at = now
    request.resolution_reason = reason
    request.current_level = None
    db.flush()
    _emit(db, company_id=request.company_id, event_type="approval.resolved",
          request_id=str(request.id), payload={"status": "CANCELLED"})
    _audit(db, action="APPROVAL_CANCELLED", entity_type="ApprovalRequest", entity_id=str(request.id),
           company_id=request.company_id, actor=str(actor_id), reason=reason,
           after={"status": "CANCELLED"})
    return request


def mark_expired(db: Session, *, company_id: str | None = None, now: datetime | None = None) -> int:
    """Marca pasos vencidos. NO resuelve: el silencio nunca decide (CL-045-06)."""
    now = now or datetime.now(UTC)
    q = select(ApprovalStep).where(ApprovalStep.status == "IN_REVIEW", ApprovalStep.due_at.is_not(None))
    count = 0
    for step in db.execute(q).scalars().all():
        if step.due_at is None or _as_utc(step.due_at) > now:
            continue
        request = db.get(ApprovalRequest, step.request_id)
        if request is None or (company_id and request.company_id != company_id):
            continue
        step.status = "EXPIRED"
        db.flush()
        _emit(db, company_id=request.company_id, event_type="approval.step_expired",
              request_id=str(request.id), step_id=str(step.id))
        count += 1
    return count


# --------------------------------------------------------------------------- #
# Consulta y allowed_actions (FR-045-060..062)
# --------------------------------------------------------------------------- #
def allowed_actions_for(db: Session, *, request: ApprovalRequest, step: ApprovalStep | None,
                        actor_id: str) -> list[str]:
    """Acciones permitidas, calculadas en backend (FR-045-062, P6)."""
    if step is None or request.status not in OPEN_REQUEST_STATES:
        return []
    try:
        _assert_can_decide(db, request=request, step=step, actor_id=actor_id)
    except (PermissionDeniedError, ConflictError):
        return []
    return ["approve", "reject", "return"]


def status(db: Session, *, company_id: str, document_type: str, document_id: str,
           actor_id: str | None = None) -> dict[str, Any]:
    """Estado de aprobación de un documento, con su historial completo."""
    requests = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.company_id == company_id,
            ApprovalRequest.document_type == document_type,
            ApprovalRequest.document_id == document_id,
        ).order_by(ApprovalRequest.created_at)
    ).scalars().all()
    out = []
    for req in requests:
        steps = []
        for st in _steps(db, str(req.id)):
            steps.append({
                "id": str(st.id), "level_order": st.level_order, "status": st.status,
                "quorum_type": st.quorum_type, "quorum_n": st.quorum_n,
                "eligible_actors": st.eligible_actors, "due_at": st.due_at, "version": st.version,
                "decisions": [
                    {"actor_id": d.actor_id, "decision": d.decision, "reason": d.reason,
                     "observations": d.observations, "decided_at": d.decided_at,
                     "on_behalf_of_id": d.on_behalf_of_id}
                    for d in _decisions(db, str(st.id))
                ],
            })
        current = next((s for s in _steps(db, str(req.id)) if s.status == "IN_REVIEW"), None)
        out.append({
            "id": str(req.id), "status": req.status, "process_type": req.process_type,
            "policy_id": req.policy_id, "policy_version": req.policy_version,
            "amount_base": float(req.amount_base) if req.amount_base is not None else None,
            "base_currency": req.base_currency, "requested_by": req.requested_by,
            "requested_at": req.requested_at, "resolved_at": req.resolved_at,
            "resolution_reason": req.resolution_reason,
            "previous_request_id": req.previous_request_id,
            "fingerprint_fields": req.fingerprint_fields,
            "steps": steps,
            "allowed_actions": allowed_actions_for(db, request=req, step=current,
                                                   actor_id=actor_id) if actor_id else [],
        })
    latest = out[-1] if out else None
    return {
        "document": f"{document_type}:{document_id}",
        "requests": out,
        "current": latest,
        "is_approved": bool(latest and latest["status"] == "APPROVED"),
        "blocks_advance": bool(latest and latest["status"] in OPEN_REQUEST_STATES),
    }


def is_approved(db: Session, *, company_id: str, document_type: str, document_id: str) -> bool:
    """¿El documento tiene aprobación vigente? Usado por los dominios (FR-045-029)."""
    latest = db.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.company_id == company_id,
            ApprovalRequest.document_type == document_type,
            ApprovalRequest.document_id == document_id,
        ).order_by(ApprovalRequest.created_at.desc())
    ).scalars().first()
    return bool(latest and latest.status == "APPROVED")


def inbox(db: Session, *, company_id: str, actor_id: str, process_type: str | None = None,
          only_overdue: bool = False, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    """Bandeja «Mis aprobaciones», transversal a todos los dominios (FR-045-060)."""
    steps = db.execute(
        select(ApprovalStep).where(ApprovalStep.status == "IN_REVIEW").order_by(ApprovalStep.opened_at)
    ).scalars().all()
    now = datetime.now(UTC)
    items: list[dict[str, Any]] = []
    for st in steps:
        req = db.get(ApprovalRequest, st.request_id)
        if req is None or req.company_id != company_id or req.status not in OPEN_REQUEST_STATES:
            continue
        if process_type and req.process_type != process_type:
            continue
        eligible = [str(a) for a in (st.eligible_actors or [])]
        if str(actor_id) not in eligible and not _resolve_delegation(
                db, company_id=company_id, process_type=req.process_type,
                actor_id=str(actor_id), eligible=eligible):
            continue
        overdue = bool(st.due_at and _as_utc(st.due_at) < now)
        if only_overdue and not overdue:
            continue
        items.append({
            "step_id": str(st.id), "request_id": str(req.id), "process_type": req.process_type,
            "document_type": req.document_type, "document_id": req.document_id,
            "level_order": st.level_order, "quorum_type": st.quorum_type,
            "amount_base": float(req.amount_base) if req.amount_base is not None else None,
            "base_currency": req.base_currency, "requested_by": req.requested_by,
            "requested_at": req.requested_at, "due_at": st.due_at, "overdue": overdue,
            "step_version": st.version,
            "allowed_actions": allowed_actions_for(db, request=req, step=st, actor_id=str(actor_id)),
        })
    return {"total": len(items), "items": items[offset:offset + limit]}


# --------------------------------------------------------------------------- #
# Configuración de políticas (FR-045-001..007)
# --------------------------------------------------------------------------- #
def create_policy(db: Session, *, company_id: str, process_type: str, code: str, name: str,
                  base_currency: str = "VED", requires_segregation: bool = False,
                  allow_self_approval: bool = True, distinct_actors_across_levels: bool = False,
                  actor: str | None = None) -> ApprovalPolicy:
    """Crea una política en DRAFT. La versión se autoincrementa por proceso."""
    last = db.execute(
        select(ApprovalPolicy).where(
            ApprovalPolicy.company_id == company_id,
            ApprovalPolicy.process_type == process_type,
        ).order_by(ApprovalPolicy.version.desc())
    ).scalars().first()
    policy = ApprovalPolicy(
        company_id=company_id, process_type=process_type, code=code, name=name,
        version=(int(last.version) + 1) if last else 1, status="DRAFT",
        base_currency=base_currency, requires_segregation=requires_segregation,
        allow_self_approval=allow_self_approval,
        distinct_actors_across_levels=distinct_actors_across_levels, created_by=actor,
    )
    db.add(policy)
    db.flush()
    _audit(db, action="APPROVAL_POLICY_CREATED", entity_type="ApprovalPolicy", entity_id=str(policy.id),
           company_id=company_id, actor=actor,
           after={"process_type": process_type, "version": policy.version})
    return policy


def update_policy(db: Session, *, policy: ApprovalPolicy, actor: str | None = None,
                  **fields: Any) -> ApprovalPolicy:
    """Edita una política. Sólo en DRAFT: lo activo es inmutable (R-D0-02-3)."""
    if policy.status != "DRAFT":
        raise ConflictError(code="APPROVAL_POLICY_NOT_EDITABLE",
                            message="Sólo se edita una política en borrador. Cree una versión nueva.")
    before = {k: getattr(policy, k) for k in fields if hasattr(policy, k)}
    for key, value in fields.items():
        if value is not None and hasattr(policy, key):
            setattr(policy, key, value)
    db.flush()
    _audit(db, action="APPROVAL_POLICY_UPDATED", entity_type="ApprovalPolicy", entity_id=str(policy.id),
           company_id=policy.company_id, actor=actor, before=before, after=fields)
    return policy


def activate_policy(db: Session, *, policy: ApprovalPolicy, actor: str | None = None) -> ApprovalPolicy:
    """Activa y cierra la versión anterior. No puede haber dos activas (FR-045-004)."""
    if policy.status != "DRAFT":
        raise ConflictError(code="APPROVAL_POLICY_NOT_DRAFT",
                            message="Sólo se activa una política en borrador.")
    if not _policy_rules(db, str(policy.id)):
        raise ConflictError(code="APPROVAL_POLICY_WITHOUT_RULES",
                            message="La política no tiene reglas: no se puede activar.")
    now = datetime.now(UTC)
    current = get_active_policy(db, company_id=policy.company_id, process_type=policy.process_type)
    if current and str(current.id) != str(policy.id):
        current.status = "CLOSED"
        current.valid_to = now
        db.flush()
    policy.status = "ACTIVE"
    policy.valid_from = now
    db.flush()
    _audit(db, action="APPROVAL_POLICY_ACTIVATED", entity_type="ApprovalPolicy", entity_id=str(policy.id),
           company_id=policy.company_id, actor=actor,
           before={"previous_version": current.version if current else None},
           after={"version": policy.version, "status": "ACTIVE"})
    return policy


def close_policy(db: Session, *, policy: ApprovalPolicy, actor: str | None = None) -> ApprovalPolicy:
    """Cierra la vigencia. Las políticas no se eliminan (FR-045-005)."""
    policy.status = "CLOSED"
    policy.valid_to = datetime.now(UTC)
    db.flush()
    _audit(db, action="APPROVAL_POLICY_CLOSED", entity_type="ApprovalPolicy", entity_id=str(policy.id),
           company_id=policy.company_id, actor=actor, after={"status": "CLOSED"})
    return policy


def add_rule(db: Session, *, policy: ApprovalPolicy, name: str, conditions: list[dict[str, Any]],
             condition_fields: list[str] | None = None, sequence: int | None = None,
             is_exception: bool = False, risk_class: str | None = None,
             actor: str | None = None) -> ApprovalRule:
    if policy.status != "DRAFT":
        raise ConflictError(code="APPROVAL_POLICY_NOT_EDITABLE",
                            message="Sólo se editan reglas de una política en borrador.")
    for pred in conditions:
        if pred.get("operator") not in _OPERATORS:
            raise ConflictError(code="APPROVAL_CONDITION_INVALID_OPERATOR",
                                message=f"Operador no soportado: {pred.get('operator')}")
    fields = condition_fields or [p["field"] for p in conditions if p.get("field")]
    rule = ApprovalRule(
        policy_id=str(policy.id), name=name, conditions=conditions,
        condition_fields=sorted(set(fields)),
        sequence=sequence or (len(_policy_rules(db, str(policy.id))) + 1),
        is_exception=is_exception, risk_class=risk_class,
    )
    db.add(rule)
    db.flush()
    _audit(db, action="APPROVAL_RULE_ADDED", entity_type="ApprovalRule", entity_id=str(rule.id),
           company_id=policy.company_id, actor=actor, after={"name": name, "fields": rule.condition_fields})
    return rule


def add_level(db: Session, *, rule: ApprovalRule, level_order: int, resolver_type: str,
              resolver_ref: str, quorum_type: str = "ANY", quorum_n: int | None = None,
              can_delegate: bool = True, sla_hours: int | None = None,
              actor: str | None = None) -> ApprovalLevel:
    if resolver_type not in {"ROLE", "USER", "SCOPE_OWNER"}:
        raise ConflictError(code="APPROVAL_RESOLVER_INVALID",
                            message="Tipo de resolutor no soportado.")
    if quorum_type not in {"ANY", "ALL", "N_OF_M"}:
        raise ConflictError(code="APPROVAL_QUORUM_INVALID", message="Cuórum no soportado.")
    if quorum_type == "N_OF_M" and not quorum_n:
        raise KontrolError(code="APPROVAL_QUORUM_N_REQUIRED",
                           message="El cuórum N de M requiere indicar N.", status_code=422)
    level = ApprovalLevel(
        rule_id=str(rule.id), level_order=level_order, resolver_type=resolver_type,
        resolver_ref=resolver_ref, quorum_type=quorum_type, quorum_n=quorum_n,
        can_delegate=can_delegate, sla_hours=sla_hours,
    )
    db.add(level)
    db.flush()
    return level


# --------------------------------------------------------------------------- #
# Delegaciones (FR-045-042..046)
# --------------------------------------------------------------------------- #
def create_delegation(db: Session, *, company_id: str, grantor_id: str, grantee_id: str,
                      valid_from: datetime | None = None, valid_to: datetime | None = None,
                      scope_process_type: str | None = None, scope_branch_id: str | None = None,
                      reason: str | None = None, is_temporary_substitution: bool = False,
                      actor: str | None = None) -> ApprovalDelegation:
    if str(grantor_id) == str(grantee_id):
        raise KontrolError(code="APPROVAL_DELEGATION_SELF",
                           message="No es posible delegar en uno mismo.", status_code=422)
    delegation = ApprovalDelegation(
        company_id=company_id, grantor_id=str(grantor_id), grantee_id=str(grantee_id),
        scope_process_type=scope_process_type, scope_branch_id=scope_branch_id,
        valid_from=valid_from or datetime.now(UTC), valid_to=valid_to, reason=reason,
        is_temporary_substitution=is_temporary_substitution, created_by=actor,
    )
    db.add(delegation)
    db.flush()
    _audit(db, action="APPROVAL_DELEGATION_CREATED", entity_type="ApprovalDelegation",
           entity_id=str(delegation.id), company_id=company_id, actor=actor,
           after={"grantor": str(grantor_id), "grantee": str(grantee_id),
                  "scope": scope_process_type, "valid_to": str(valid_to) if valid_to else None})
    return delegation


def revoke_delegation(db: Session, *, delegation: ApprovalDelegation,
                      actor: str | None = None) -> ApprovalDelegation:
    """Revoca. Las decisiones ya tomadas siguen siendo válidas (FR-045-046, P5)."""
    if delegation.revoked_at is not None:
        return delegation
    delegation.revoked_at = datetime.now(UTC)
    delegation.revoked_by = actor
    db.flush()
    _audit(db, action="APPROVAL_DELEGATION_REVOKED", entity_type="ApprovalDelegation",
           entity_id=str(delegation.id), company_id=delegation.company_id, actor=actor,
           after={"revoked": True})
    return delegation
