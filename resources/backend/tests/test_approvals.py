"""Pruebas del motor transversal de aprobaciones (Spec 045).

Cubre los criterios de aceptación AC-01..AC-24 de
`specs/045-motor-aprobaciones-segregacion/acceptance-criteria.md`.

Nota de alcance (Constitución P21): los casos que dependen de `SELECT … FOR
UPDATE` y de índices parciales sólo son concluyentes sobre PostgreSQL. Aquí se
verifica la lógica; la concurrencia real es criterio de salida sobre PG.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.errors import ConflictError, KontrolError, PermissionDeniedError
from app.modules.approvals import service as svc
from app.modules.approvals.models import ApprovalDecision, ApprovalRequest, ApprovalStep
from app.modules.identity_access.models import Role, User, UserRole

COMPANY = "company-1"
OTHER = "company-2"


@pytest.fixture()
def db_session(sesion_de_prueba):
    """Sesión de prueba con la cadena organizacional mínima creada.

    PostgreSQL SÍ exige las claves foráneas y SQLite no: sin empresa real, las
    inserciones de política fallaban en PostgreSQL. Crear la cadena
    installation → tenant → company es lo correcto en ambos motores
    (Constitución P21).
    """
    from app.modules.organization.models import Company, Installation, Tenant

    session = sesion_de_prueba
    inst = Installation(id="inst-1", installation_uuid="uuid-1", state="ACTIVE")
    session.add(inst)
    session.flush()
    for company_id, code in ((COMPANY, "C1"), (OTHER, "C2")):
        tenant = Tenant(id=f"ten-{code}", installation_id="inst-1", code=code,
                        name=f"Tenant {code}", plan="MULTI_COMPANY", status="ACTIVE")
        session.add(tenant)
        session.flush()
        session.add(Company(id=company_id, tenant_id=f"ten-{code}", code=code,
                            legal_name=f"Empresa {code}", rif=f"J-{code}", legal_type="CA",
                            functional_currency="VED", status="ACTIVE"))
    session.flush()
    return session


def _user(db, email: str) -> User:
    # El usuario pertenece al **tenant**, no a la empresa. Ponía `COMPANY` aquí,
    # que es exactamente la confusión que ARCH-MC-001 corrige, y solo pasaba
    # porque la columna no referenciaba nada.
    u = User(username=email.split("@")[0], email=email, password_hash="x",
             status="ACTIVE", tenant_id="ten-C1")
    db.add(u)
    db.flush()
    return u


def _role_with(db, code: str, users: list[User]) -> Role:
    role = Role(code=code, name=code, protected=False, status="ACTIVE")
    db.add(role)
    db.flush()
    # El rol de aprobadores trae la capacidad de aprobar: decidir la exige en la empresa (Spec 003).
    from sqlalchemy import select

    from app.modules.identity_access.models import Permission, RolePermission
    perm = db.execute(
        select(Permission).where(
            Permission.resource == "aprobaciones", Permission.action == "approve"
        )
    ).scalars().first()
    if perm is None:
        perm = Permission(resource="aprobaciones", action="approve", scope_type="COMPANY")
        db.add(perm)
        db.flush()
    db.add(RolePermission(role_id=str(role.id), permission_id=str(perm.id)))
    for u in users:
        db.add(UserRole(user_id=str(u.id), role_id=str(role.id)))
    db.flush()
    return role


def _policy(db, *, process_type="PURCHASE_ORDER", segregation=False, self_approval=True,
            distinct=False, levels=None, threshold=1000.0, base_currency="VED", activate=True):
    """Política de prueba. Los valores son de la PRUEBA, no del producto (P8)."""
    policy = svc.create_policy(db, company_id=COMPANY, process_type=process_type,
                               code="TEST", name="Política de prueba",
                               base_currency=base_currency, requires_segregation=segregation,
                               allow_self_approval=self_approval,
                               distinct_actors_across_levels=distinct, actor="setup")
    rule = svc.add_rule(db, policy=policy, name="Sobre umbral",
                        conditions=[{"field": "amount_base", "operator": "gt", "value": threshold}],
                        condition_fields=["amount_base", "amount", "currency"], actor="setup")
    for lv in (levels or [{"level_order": 1, "resolver_type": "ROLE", "resolver_ref": "APR1"}]):
        svc.add_level(db, rule=rule, **lv, actor="setup")
    if activate:
        svc.activate_policy(db, policy=policy, actor="setup")
    return policy


# --------------------------------------------------------------------------- #
# Configuración de políticas — AC-01, AC-02
# --------------------------------------------------------------------------- #
def test_policy_versioning_and_activation(db_session):
    p1 = _policy(db_session)
    assert p1.version == 1 and p1.status == "ACTIVE"
    p2 = _policy(db_session)
    db_session.refresh(p1)
    # AC-02: activar la nueva cierra la anterior; nunca dos activas
    assert p2.version == 2 and p2.status == "ACTIVE"
    assert p1.status == "CLOSED" and p1.valid_to is not None
    assert svc.get_active_policy(db_session, company_id=COMPANY,
                                 process_type="PURCHASE_ORDER").id == p2.id


def test_active_policy_is_not_editable(db_session):
    policy = _policy(db_session)
    with pytest.raises(ConflictError) as exc:
        svc.update_policy(db_session, policy=policy, name="otro")
    assert exc.value.code == "APPROVAL_POLICY_NOT_EDITABLE"


def test_policy_without_rules_cannot_activate(db_session):
    policy = svc.create_policy(db_session, company_id=COMPANY, process_type="X",
                               code="X", name="X", actor="setup")
    with pytest.raises(ConflictError) as exc:
        svc.activate_policy(db_session, policy=policy)
    assert exc.value.code == "APPROVAL_POLICY_WITHOUT_RULES"


def test_policies_are_closed_not_deleted(db_session):
    policy = _policy(db_session)
    svc.close_policy(db_session, policy=policy)
    assert db_session.get(type(policy), policy.id) is not None
    assert policy.status == "CLOSED"


# --------------------------------------------------------------------------- #
# Evaluación — AC-03, AC-04
# --------------------------------------------------------------------------- #
def test_amount_is_evaluated_in_base_currency(db_session):
    """AC-03: el umbral se mide sobre el equivalente en moneda base."""
    _policy(db_session, threshold=1000.0, base_currency="VED")
    # 100 USD a tasa 36,5 = 3.650 VED → supera el umbral
    over = svc.evaluate(db_session, company_id=COMPANY, process_type="PURCHASE_ORDER",
                        context={"amount": 100, "currency": "USD", "rate_snapshot": 36.5})
    assert over["requires_approval"] is True
    assert over["amount_base"] == pytest.approx(3650.0)
    # 100 VED nominales NO lo superan, pese al mismo importe nominal
    under = svc.evaluate(db_session, company_id=COMPANY, process_type="PURCHASE_ORDER",
                         context={"amount": 100, "currency": "VED"})
    assert under["requires_approval"] is False


def test_unevaluable_condition_never_passes_silently(db_session):
    """AC-04: falta un dato → error explícito, nunca «no requiere»."""
    policy = svc.create_policy(db_session, company_id=COMPANY, process_type="P",
                               code="C", name="N", actor="s")
    rule = svc.add_rule(db_session, policy=policy, name="por centro de costo",
                        conditions=[{"field": "cost_center_id", "operator": "eq", "value": "cc-1"}])
    svc.add_level(db_session, rule=rule, level_order=1, resolver_type="ROLE", resolver_ref="R")
    svc.activate_policy(db_session, policy=policy)
    with pytest.raises(KontrolError) as exc:
        svc.evaluate(db_session, company_id=COMPANY, process_type="P", context={"amount": 1})
    assert exc.value.code == "APPROVAL_CONDITION_UNEVALUABLE"
    assert exc.value.status_code == 422


def test_no_policy_means_no_approval_required(db_session):
    out = svc.evaluate(db_session, company_id=COMPANY, process_type="SIN_POLITICA", context={})
    assert out["requires_approval"] is False and out["reason"] == "NO_ACTIVE_POLICY"


def test_evaluate_has_no_side_effects(db_session):
    _policy(db_session)
    svc.evaluate(db_session, company_id=COMPANY, process_type="PURCHASE_ORDER",
                 context={"amount": 5000, "currency": "VED"})
    assert db_session.query(ApprovalRequest).count() == 0


# --------------------------------------------------------------------------- #
# Ciclo — AC-10 a AC-15
# --------------------------------------------------------------------------- #
def _request(db, *, actor="creator", amount=5000):
    return svc.require(db, company_id=COMPANY, process_type="PURCHASE_ORDER",
                       document_type="PurchaseOrder", document_id="doc-1",
                       context={"amount": amount, "currency": "VED"}, actor=actor)


def test_request_is_idempotent(db_session):
    """AC-10: dos solicitudes idénticas → una sola."""
    _policy(db_session)
    r1 = _request(db_session)
    r2 = _request(db_session)
    assert r2["idempotent_hit"] is True
    assert str(r1["request"].id) == str(r2["request"].id)
    assert db_session.query(ApprovalRequest).count() == 1


def test_approval_flow_single_level(db_session):
    approver = _user(db_session, "apr@x.com")
    _role_with(db_session, "APR1", [approver])
    _policy(db_session)
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    assert req.status == "IN_REVIEW" and step.status == "IN_REVIEW"
    out = svc.decide(db_session, step_id=str(step.id), actor_id=str(approver.id), decision="APPROVE")
    assert out["status"] == "APPROVED"
    assert svc.is_approved(db_session, company_id=COMPANY,
                           document_type="PurchaseOrder", document_id="doc-1") is True


def test_multilevel_sequential(db_session):
    """AC-11 secuencia: el nivel 2 no abre hasta resolverse el 1."""
    a1, a2 = _user(db_session, "a1@x.com"), _user(db_session, "a2@x.com")
    _role_with(db_session, "APR1", [a1])
    _role_with(db_session, "APR2", [a2])
    _policy(db_session, levels=[
        {"level_order": 1, "resolver_type": "ROLE", "resolver_ref": "APR1"},
        {"level_order": 2, "resolver_type": "ROLE", "resolver_ref": "APR2"},
    ])
    req = _request(db_session)["request"]
    steps = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).all()
    assert len(steps) == 1  # sólo el nivel 1 está abierto
    out = svc.decide(db_session, step_id=str(steps[0].id), actor_id=str(a1.id), decision="APPROVE")
    assert out["next_level"] == 2 and req.status == "IN_REVIEW"
    step2 = db_session.query(ApprovalStep).filter_by(request_id=str(req.id), level_order=2).one()
    svc.decide(db_session, step_id=str(step2.id), actor_id=str(a2.id), decision="APPROVE")
    assert req.status == "APPROVED"


def test_quorum_n_of_m(db_session):
    """AC-11: N de M no cierra hasta alcanzar N."""
    a1, a2, a3 = (_user(db_session, f"q{i}@x.com") for i in range(3))
    _role_with(db_session, "APR1", [a1, a2, a3])
    _policy(db_session, levels=[{"level_order": 1, "resolver_type": "ROLE", "resolver_ref": "APR1",
                                 "quorum_type": "N_OF_M", "quorum_n": 2}])
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    out = svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="APPROVE")
    assert out.get("quorum_pending") is True and req.status == "IN_REVIEW"
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a2.id), decision="APPROVE")
    assert req.status == "APPROVED"


def test_one_negative_closes_even_with_quorum_all(db_session):
    """AC-12: una sola negativa basta, cualquiera sea el cuórum."""
    a1, a2 = _user(db_session, "n1@x.com"), _user(db_session, "n2@x.com")
    _role_with(db_session, "APR1", [a1, a2])
    _policy(db_session, levels=[{"level_order": 1, "resolver_type": "ROLE", "resolver_ref": "APR1",
                                 "quorum_type": "ALL"}])
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id),
               decision="REJECT", reason="no procede")
    assert req.status == "REJECTED"


def test_reject_is_terminal(db_session):
    """AC-13: rechazo terminal; no admite más decisiones."""
    a1 = _user(db_session, "r@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="REJECT", reason="x")
    with pytest.raises(ConflictError) as exc:
        svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="APPROVE")
    assert exc.value.code in {"APPROVAL_STEP_NOT_OPEN", "APPROVAL_DUPLICATE_DECISION"}


def test_reason_required_on_negative(db_session):
    """AC-15."""
    a1 = _user(db_session, "m@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    for decision in ("REJECT", "RETURN"):
        with pytest.raises(KontrolError) as exc:
            svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id),
                       decision=decision, reason="   ")
        assert exc.value.code == "APPROVAL_REASON_REQUIRED"
        assert exc.value.status_code == 422


def test_return_keeps_history_and_chains(db_session):
    """AC-14: devolver conserva historial; reenviar encadena solicitud nueva."""
    a1 = _user(db_session, "d@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    req1 = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req1.id)).one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id),
               decision="RETURN", reason="falta centro de costo")
    assert req1.status == "RETURNED"
    assert db_session.query(ApprovalDecision).filter_by(step_id=str(step.id)).count() == 1
    # Reenvío con documento corregido → solicitud nueva
    req2 = svc.require(db_session, company_id=COMPANY, process_type="PURCHASE_ORDER",
                       document_type="PurchaseOrder", document_id="doc-1",
                       context={"amount": 6000, "currency": "VED"}, actor="creator")["request"]
    assert str(req2.id) != str(req1.id)
    hist = svc.status(db_session, company_id=COMPANY, document_type="PurchaseOrder", document_id="doc-1")
    assert len(hist["requests"]) == 2


def test_cancel(db_session):
    _policy(db_session)
    req = _request(db_session)["request"]
    svc.cancel(db_session, company_id=COMPANY, request_id=str(req.id),
               actor_id="creator", reason="ya no aplica")
    assert req.status == "CANCELLED"


# --------------------------------------------------------------------------- #
# Segregación y delegación — AC-05, AC-06, AC-18
# --------------------------------------------------------------------------- #
def test_segregation_excludes_creator(db_session):
    """AC-05: el creador no es elegible y recibe 403."""
    creator = _user(db_session, "creator@x.com")
    other = _user(db_session, "other@x.com")
    _role_with(db_session, "APR1", [creator, other])
    _policy(db_session, segregation=True)
    req = svc.require(db_session, company_id=COMPANY, process_type="PURCHASE_ORDER",
                      document_type="PurchaseOrder", document_id="doc-1",
                      context={"amount": 5000, "currency": "VED"}, actor=str(creator.id))["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    assert str(creator.id) not in step.eligible_actors
    assert str(other.id) in step.eligible_actors
    with pytest.raises(PermissionDeniedError) as exc:
        svc.decide(db_session, step_id=str(step.id), actor_id=str(creator.id), decision="APPROVE")
    assert exc.value.code == "APPROVAL_SEGREGATION_VIOLATION"
    assert svc.allowed_actions_for(db_session, request=req, step=step,
                                   actor_id=str(creator.id)) == []


def test_self_approval_denied_by_policy(db_session):
    creator = _user(db_session, "c2@x.com")
    _role_with(db_session, "APR1", [creator])
    _policy(db_session, self_approval=False)
    req = svc.require(db_session, company_id=COMPANY, process_type="PURCHASE_ORDER",
                      document_type="PurchaseOrder", document_id="doc-2",
                      context={"amount": 5000, "currency": "VED"}, actor=str(creator.id))["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    with pytest.raises(PermissionDeniedError) as exc:
        svc.decide(db_session, step_id=str(step.id), actor_id=str(creator.id), decision="APPROVE")
    assert exc.value.code in {"APPROVAL_SELF_APPROVAL_DENIED", "APPROVAL_NOT_ELIGIBLE"}


def test_delegation_allows_acting_for_eligible(db_session):
    approver, deputy = _user(db_session, "ap@x.com"), _user(db_session, "dep@x.com")
    _role_with(db_session, "APR1", [approver])
    # El suplente decide con aprobaciones:approve (lo exige la ruta y, desde Spec 003, el servicio); no es aprobador del nivel.
    _role_with(db_session, "DEP1", [deputy])
    _policy(db_session)
    svc.create_delegation(db_session, company_id=COMPANY, grantor_id=str(approver.id),
                          grantee_id=str(deputy.id), valid_to=datetime.now(UTC) + timedelta(days=5),
                          reason="ausencia", is_temporary_substitution=True, actor="admin")
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(deputy.id), decision="APPROVE")
    dec = db_session.query(ApprovalDecision).filter_by(step_id=str(step.id)).one()
    assert dec.on_behalf_of_id == str(approver.id) and dec.delegation_id is not None
    assert req.status == "APPROVED"


def test_delegation_cannot_bypass_segregation(db_session):
    """AC-06: la delegación no habilita lo que la segregación prohíbe."""
    creator = _user(db_session, "cr@x.com")
    approver = _user(db_session, "ap2@x.com")
    _role_with(db_session, "APR1", [approver])
    _policy(db_session, segregation=True)
    svc.create_delegation(db_session, company_id=COMPANY, grantor_id=str(approver.id),
                          grantee_id=str(creator.id), actor="admin")
    req = svc.require(db_session, company_id=COMPANY, process_type="PURCHASE_ORDER",
                      document_type="PurchaseOrder", document_id="doc-3",
                      context={"amount": 5000, "currency": "VED"}, actor=str(creator.id))["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    with pytest.raises(PermissionDeniedError) as exc:
        svc.decide(db_session, step_id=str(step.id), actor_id=str(creator.id), decision="APPROVE")
    assert exc.value.code == "APPROVAL_SEGREGATION_VIOLATION"


def test_revoked_delegation_does_not_invalidate_past_decisions(db_session):
    """AC-18: revocar afecta al futuro, no reescribe la historia."""
    approver, deputy = _user(db_session, "a3@x.com"), _user(db_session, "d3@x.com")
    _role_with(db_session, "APR1", [approver])
    # El suplente decide con aprobaciones:approve (lo exige la ruta y, desde Spec 003, el servicio); no es aprobador del nivel.
    _role_with(db_session, "DEP1", [deputy])
    _policy(db_session)
    dele = svc.create_delegation(db_session, company_id=COMPANY, grantor_id=str(approver.id),
                                 grantee_id=str(deputy.id), actor="admin")
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(deputy.id), decision="APPROVE")
    svc.revoke_delegation(db_session, delegation=dele, actor="admin")
    assert req.status == "APPROVED"
    dec = db_session.query(ApprovalDecision).filter_by(step_id=str(step.id)).one()
    assert dec.delegation_id == str(dele.id)


def test_cannot_delegate_to_self(db_session):
    u = _user(db_session, "s@x.com")
    with pytest.raises(KontrolError) as exc:
        svc.create_delegation(db_session, company_id=COMPANY, grantor_id=str(u.id),
                              grantee_id=str(u.id))
    assert exc.value.code == "APPROVAL_DELEGATION_SELF"


# --------------------------------------------------------------------------- #
# Obsolescencia — AC-07, AC-08
# --------------------------------------------------------------------------- #
def test_document_change_marks_request_obsolete(db_session):
    """AC-07: cambiar un campo de la huella invalida la solicitud."""
    a1 = _user(db_session, "o1@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    req = _request(db_session, amount=5000)["request"]
    svc.document_changed(db_session, company_id=COMPANY, document_type="PurchaseOrder",
                         document_id="doc-1", context={"amount": 9000, "currency": "VED"})
    assert req.status == "OBSOLETE"
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    with pytest.raises(ConflictError) as exc:
        svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="APPROVE")
    assert exc.value.code in {"APPROVAL_STEP_NOT_OPEN", "APPROVAL_REQUEST_OBSOLETE"}


def test_unrelated_change_does_not_invalidate(db_session):
    """AC-08: un cambio ajeno a la condición NO invalida."""
    _policy(db_session)
    req = _request(db_session, amount=5000)["request"]
    svc.document_changed(db_session, company_id=COMPANY, document_type="PurchaseOrder",
                         document_id="doc-1",
                         context={"amount": 5000, "currency": "VED", "notes": "otra observación"})
    assert req.status == "IN_REVIEW"


def test_fingerprint_is_scoped_to_condition_fields(db_session):
    fp1 = svc.compute_fingerprint({"amount": 10, "notes": "a"}, ["amount"])
    fp2 = svc.compute_fingerprint({"amount": 10, "notes": "b"}, ["amount"])
    fp3 = svc.compute_fingerprint({"amount": 11, "notes": "a"}, ["amount"])
    assert fp1 == fp2 and fp1 != fp3


# --------------------------------------------------------------------------- #
# Concurrencia (lógica) — AC-09
# --------------------------------------------------------------------------- #
def test_version_conflict_on_concurrent_decision(db_session):
    """AC-09 (lógica): la versión obsoleta del paso produce conflicto."""
    a1, a2 = _user(db_session, "c1@x.com"), _user(db_session, "c2b@x.com")
    _role_with(db_session, "APR1", [a1, a2])
    _policy(db_session, levels=[{"level_order": 1, "resolver_type": "ROLE", "resolver_ref": "APR1",
                                 "quorum_type": "N_OF_M", "quorum_n": 2}])
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    stale_version = step.version
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="APPROVE",
               expected_version=stale_version)
    with pytest.raises(ConflictError) as exc:
        svc.decide(db_session, step_id=str(step.id), actor_id=str(a2.id), decision="APPROVE",
                   expected_version=stale_version)
    assert exc.value.code == "APPROVAL_STEP_VERSION_CONFLICT"


def test_same_actor_cannot_decide_twice(db_session):
    """INV-06."""
    a1 = _user(db_session, "dup@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session, levels=[{"level_order": 1, "resolver_type": "ROLE", "resolver_ref": "APR1",
                                 "quorum_type": "N_OF_M", "quorum_n": 2}])
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="APPROVE")
    with pytest.raises(ConflictError) as exc:
        svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="APPROVE")
    assert exc.value.code == "APPROVAL_DUPLICATE_DECISION"


def test_not_eligible_is_denied(db_session):
    intruder = _user(db_session, "int@x.com")
    approver = _user(db_session, "ok@x.com")
    _role_with(db_session, "APR1", [approver])
    _policy(db_session)
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    with pytest.raises(PermissionDeniedError) as exc:
        svc.decide(db_session, step_id=str(step.id), actor_id=str(intruder.id), decision="APPROVE")
    assert exc.value.code == "APPROVAL_NOT_ELIGIBLE"


# --------------------------------------------------------------------------- #
# Vencimiento — AC-16
# --------------------------------------------------------------------------- #
def test_expiry_marks_but_does_not_resolve(db_session):
    """AC-16: el silencio nunca decide."""
    a1 = _user(db_session, "e@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session, levels=[{"level_order": 1, "resolver_type": "ROLE",
                                 "resolver_ref": "APR1", "sla_hours": 1}])
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    step.due_at = datetime.now(UTC) - timedelta(hours=2)
    db_session.flush()
    assert svc.mark_expired(db_session, company_id=COMPANY) == 1
    assert step.status == "EXPIRED"
    assert req.status == "IN_REVIEW"  # NO se resolvió por el paso del tiempo


# --------------------------------------------------------------------------- #
# Consulta y bandeja — AC-17, AC-19
# --------------------------------------------------------------------------- #
def test_blocks_advance_until_approved(db_session):
    """AC-17: el documento no avanza mientras la solicitud está viva."""
    a1 = _user(db_session, "b@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    req = _request(db_session)["request"]
    st = svc.status(db_session, company_id=COMPANY, document_type="PurchaseOrder", document_id="doc-1")
    assert st["blocks_advance"] is True and st["is_approved"] is False
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="APPROVE")
    st2 = svc.status(db_session, company_id=COMPANY, document_type="PurchaseOrder", document_id="doc-1")
    assert st2["blocks_advance"] is False and st2["is_approved"] is True


def test_inbox_is_transversal_across_domains(db_session):
    """AC-19: una sola bandeja para todos los dominios."""
    a1 = _user(db_session, "inbox@x.com")
    _role_with(db_session, "APR1", [a1])
    for process, doc in (("PURCHASE_ORDER", "po-1"), ("INVENTORY_ADJUSTMENT", "aj-1"),
                         ("SALES_CREDIT", "ov-1")):
        _policy(db_session, process_type=process)
        svc.require(db_session, company_id=COMPANY, process_type=process,
                    document_type=process, document_id=doc,
                    context={"amount": 5000, "currency": "VED"}, actor="creator")
    box = svc.inbox(db_session, company_id=COMPANY, actor_id=str(a1.id))
    assert box["total"] == 3
    assert {i["process_type"] for i in box["items"]} == {
        "PURCHASE_ORDER", "INVENTORY_ADJUSTMENT", "SALES_CREDIT"}
    assert all(i["allowed_actions"] == ["approve", "reject", "return"] for i in box["items"])


def test_inbox_isolated_by_company(db_session):
    a1 = _user(db_session, "iso@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    _request(db_session)
    assert svc.inbox(db_session, company_id=OTHER, actor_id=str(a1.id))["total"] == 0


def test_policy_snapshot_is_frozen(db_session):
    """INV-07 / AC-01: cambiar la política no altera la solicitud."""
    a1 = _user(db_session, "snap@x.com")
    _role_with(db_session, "APR1", [a1])
    p1 = _policy(db_session, threshold=1000.0)
    req = _request(db_session)["request"]
    snapshot_before = dict(req.policy_snapshot)
    _policy(db_session, threshold=99999.0)  # v2 con umbral distinto
    db_session.refresh(req)
    assert req.policy_snapshot == snapshot_before
    assert req.policy_version == str(p1.version)


def test_audit_is_recorded(db_session):
    """FR-045-064: el motor deja rastro en AuditEvent, sin rastro paralelo."""
    from app.modules.audit.models import AuditEvent
    a1 = _user(db_session, "aud@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="APPROVE")
    actions = {e.action for e in db_session.query(AuditEvent).all()}
    assert "APPROVAL_REQUESTED" in actions and "APPROVAL_APPROVE" in actions
    assert "APPROVAL_POLICY_ACTIVATED" in actions


def test_domain_events_are_emitted(db_session):
    """FR-045-066: el motor emite; no notifica (la Spec 047 los consumirá)."""
    from app.modules.approvals.models import ApprovalEvent
    a1 = _user(db_session, "ev@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    req = _request(db_session)["request"]
    step = db_session.query(ApprovalStep).filter_by(request_id=str(req.id)).one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id), decision="APPROVE")
    types = {e.event_type for e in db_session.query(ApprovalEvent).all()}
    assert {"approval.requested", "approval.step_opened",
            "approval.decided", "approval.resolved"} <= types


# --------------------------------------------------------------------------- #
# F6 · Migración de dominios — AC-20, AC-21
# --------------------------------------------------------------------------- #
def test_domains_behave_identically_without_policy(db_session):
    """AC-20: sin política activa, los dominios avanzan como antes de la Spec 045."""
    from app.modules.approvals import integration as integ
    # No hay política para PURCHASE_ORDER en esta empresa
    out = integ.require_for_document(
        db_session, company_id=COMPANY, process_type=integ.PROCESS_PURCHASE_ORDER,
        document_type="PurchaseOrder", document_id="po-x", context={"amount": 999999},
        actor="creator")
    assert out["requires_approval"] is False
    # Y `ensure_approved` no bloquea nada
    integ.ensure_approved(db_session, company_id=COMPANY, document_type="PurchaseOrder",
                          document_id="po-x")


def test_domain_blocked_while_approval_pending(db_session):
    """AC-17 vía integración: con política, el documento no avanza sin resolver."""
    from app.core.errors import ConflictError as CE
    from app.modules.approvals import integration as integ
    a1 = _user(db_session, "int1@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    integ.require_for_document(
        db_session, company_id=COMPANY, process_type="PURCHASE_ORDER",
        document_type="PurchaseOrder", document_id="po-y",
        context={"amount": 5000, "currency": "VED"}, actor="creator")
    with pytest.raises(CE) as exc:
        integ.ensure_approved(db_session, company_id=COMPANY, document_type="PurchaseOrder",
                              document_id="po-y", what="la orden")
    assert exc.value.code == "APPROVAL_PENDING"


def test_rejected_approval_blocks_advance(db_session):
    from app.core.errors import ConflictError as CE
    from app.modules.approvals import integration as integ
    a1 = _user(db_session, "int2@x.com")
    _role_with(db_session, "APR1", [a1])
    _policy(db_session)
    integ.require_for_document(
        db_session, company_id=COMPANY, process_type="PURCHASE_ORDER",
        document_type="PurchaseOrder", document_id="po-z",
        context={"amount": 5000, "currency": "VED"}, actor="creator")
    step = db_session.query(ApprovalStep).join(
        ApprovalRequest, ApprovalStep.request_id == ApprovalRequest.id
    ).filter(ApprovalRequest.document_id == "po-z").one()
    svc.decide(db_session, step_id=str(step.id), actor_id=str(a1.id),
               decision="REJECT", reason="fuera de presupuesto")
    with pytest.raises(CE) as exc:
        integ.ensure_approved(db_session, company_id=COMPANY, document_type="PurchaseOrder",
                              document_id="po-z", what="la orden")
    assert exc.value.code == "APPROVAL_NOT_GRANTED"


def test_no_domain_keeps_its_own_approval_logic():
    """AC-21 / Constitución P22: ningún módulo implementa aprobación propia."""
    import pathlib
    import re
    root = pathlib.Path(__file__).resolve().parents[1] / "app" / "modules"
    offenders: list[str] = []
    # Patrón: una transición a APPROVED que no consulte al motor.
    for module in ("purchasing", "sales", "inventory", "regulatory"):
        service = (root / module / "service.py").read_text(encoding="utf-8")
        approves = re.findall(r'target == "APPROVED"', service)
        if approves and "approvals_integration" not in service:
            offenders.append(module)
    # Ningún módulo de dominio puede tener su propio motor de política
    for module in ("purchasing", "sales", "inventory", "regulatory", "treasury", "fiscal"):
        service = (root / module / "service.py").read_text(encoding="utf-8")
        if "ApprovalPolicy" in service or "ApprovalLevel" in service:
            offenders.append(f"{module}:modelo-propio")
    assert offenders == [], f"Módulos con aprobación propia: {offenders}"
