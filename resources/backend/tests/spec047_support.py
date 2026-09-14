"""Apoyo de las pruebas de la Spec 047. Pytest no lo recoge: no contiene pruebas.

Los hechos de aprobación salen del **motor real de la 045** por su API. Solo se
construyen a mano los efectos que la propia 047 publica.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import UTC, datetime

from sqlalchemy import text

from app.core.company_context import company_context_for
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Permission, Role, RolePermission, User, UserRole, UserScope
from app.modules.notifications import service
from app.modules.notifications.models import NotificationRule
from app.modules.scheduler import registry
from app.modules.scheduler.service import tick

PASSWORD = "Kontrol2026Segura!"


def marca() -> str:
    return uuid.uuid4().hex[:8].upper()


def ahora() -> datetime:
    return datetime.now(UTC)


# -- lectura directa de PostgreSQL -------------------------------------------
def valor(factory, sql: str, **p):
    with factory() as db:
        return db.execute(text(sql), p).scalar()


def filas(factory, sql: str, **p) -> list[tuple]:
    with factory() as db:
        return [tuple(r) for r in db.execute(text(sql), p).all()]


def ejecutar(factory, sql: str, **p) -> None:
    with factory() as db:
        db.execute(text(sql), p)
        db.commit()


def uid(factory, username: str) -> str:
    return valor(factory, "SELECT id FROM users WHERE username = :u", u=username)


def rol_admin(factory) -> str:
    return valor(factory, "SELECT id FROM roles WHERE code = 'ADMIN' AND company_id IS NULL")


def codigo(r) -> str | None:
    cuerpo = r.json()
    return cuerpo.get("code") if isinstance(cuerpo, dict) else None


# -- estado limpio entre pruebas del mismo módulo ------------------------------
def limpiar(mundo) -> None:
    """Consume los hechos pendientes y apaga las reglas de pruebas anteriores."""
    tick(mundo.factory)
    ejecutar(mundo.factory, "UPDATE notification_rules SET active = false")


def regla(factory, company_id: str, *, event_type: str = "approval.step_opened",
          effect: str = "NOTIFICATION", **extra) -> str:
    with factory() as db:
        r = NotificationRule(
            company_id=company_id, code=extra.pop("code", f"R{marca()}"), source="APPROVAL",
            event_type=event_type, effect=effect, severity=extra.pop("severity", "INFO"),
            mandatory=extra.pop("mandatory", False), auto_close=extra.pop("auto_close", False),
            active=True, **extra)
        db.add(r)
        db.commit()
        return str(r.id)


# -- el motor real de la 045 ---------------------------------------------------
def politica(mundo, empresa: str, usuario: str, process_type: str) -> None:
    r = mundo.post("/approvals/policies", usuario, empresa, {
        "process_type": process_type, "code": f"P{marca()}", "name": "Política 047",
        "requires_segregation": False})
    assert r.status_code in (200, 201), r.text
    pid = r.json()["id"]
    rr = mundo.post(f"/approvals/policies/{pid}/rules", usuario, empresa, {
        "name": "Siempre", "conditions": [{"field": "amount_base", "operator": "gt", "value": 0}],
        "condition_fields": ["amount_base", "amount", "currency"]})
    assert rr.status_code == 201, rr.text
    rl = mundo.post(f"/approvals/policies/{pid}/rules/{rr.json()['id']}/levels", usuario, empresa, {
        "level_order": 1, "resolver_type": "ROLE", "resolver_ref": "ADMIN", "quorum_type": "ANY"})
    assert rl.status_code == 201, rl.text
    act = mundo.post(f"/approvals/policies/{pid}/activate", usuario, empresa, {})
    assert act.status_code == 200, act.text


def solicitud(mundo, empresa: str, usuario: str, process_type: str) -> tuple[str, str]:
    r = mundo.post("/approvals/requests", usuario, empresa, {
        "process_type": process_type, "document_type": "Doc", "document_id": marca(),
        "context": {"amount": 5000, "currency": "VED"}})
    assert r.status_code == 201, r.text
    assert r.json()["requires_approval"] is True, r.text
    rid = r.json()["request_id"]
    paso = valor(mundo.factory, "SELECT id FROM approval_steps WHERE request_id = :r AND status = 'IN_REVIEW'",
                 r=rid)
    assert paso, "la 045 no abrió el paso"
    return rid, paso


def aprobacion(mundo, empresa: str = None, usuario: str = "ua") -> tuple[str, str]:
    empresa = empresa or mundo.company_a
    pt = f"P047{marca()}"
    politica(mundo, empresa, usuario, pt)
    return solicitud(mundo, empresa, usuario, pt)


def elegibles(factory, step_id: str) -> set[str]:
    v = valor(factory, "SELECT eligible_actors FROM approval_steps WHERE id = :s", s=step_id)
    return {str(x) for x in (v or [])}


# -- planificador ----------------------------------------------------------------
def solo(*codigos: str):
    return tuple(m for m in registry.manejadores() if m.code in codigos)


def con_vencimiento_045_habilitado():
    return tuple(replace(m, enabled=True) if m.code == "approval_step_expiration" else m
                 for m in registry.manejadores())


# -- efectos publicados por la propia 047 --------------------------------------------
def efecto(company_id: str, **kw) -> service.Efecto:
    base = dict(company_id=company_id, category=f"test.{marca()}", severity="INFO",
                message_key="approval.step_opened.notification",
                message_params={"process_type": "PRUEBA", "document_type": "Doc", "level_order": 1},
                source_type="ApprovalRequest", source_id=str(uuid.uuid4()), route_key="approval_inbox",
                dedupe_key=f"test:{uuid.uuid4()}")
    base.update(kw)
    return service.Efecto(**base)


def publicar(factory, crear, e: service.Efecto) -> str:
    with factory() as db:
        fila, _ = crear(db, e)
        db.commit()
        return str(fila.id)


def contexto(db, username: str, company_id: str):
    user = db.query(User).filter(User.username == username).one()
    return user, company_context_for(db, user, company_id)


def usuario_limitado(mundo, empresas: list[str], sin: set[str]) -> tuple[str, str]:
    """Usuario de T1 con todos los permisos existentes menos `sin`."""
    username = f"lim{marca().lower()}"
    with mundo.factory() as db:
        u = identity_service.create_user(db, tenant_id=mundo.t1, username=username,
                                         email=f"{username}@demo.test", password=PASSWORD,
                                         created_by=None)
        rol = Role(code=f"LIM{marca()}", name="Limitado 047", protected=False, status="ACTIVE")
        db.add(rol)
        db.flush()
        for p in db.query(Permission).all():
            if f"{p.resource}:{p.action}" not in sin:
                db.add(RolePermission(role_id=str(rol.id), permission_id=str(p.id)))
        db.add(UserRole(user_id=str(u.id), role_id=str(rol.id), company_id=None))
        for c in empresas:
            db.add(UserScope(user_id=str(u.id), company_id=c))
        db.commit()
        return username, str(u.id)
