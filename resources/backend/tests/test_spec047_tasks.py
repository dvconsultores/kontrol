"""Spec 047 · tareas: candidatos, asignación, historial, cierre y concurrencia."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.errors import ConflictError
from app.modules.notifications import service
from app.modules.scheduler.service import tick
from tests.concurrency import carrera
from tests.spec047_support import (
    ahora,
    aprobacion,
    codigo,
    contexto,
    efecto,
    ejecutar,
    elegibles,
    filas,
    limpiar,
    marca,
    publicar,
    regla,
    uid,
    usuario_limitado,
    valor,
)

pytest_plugins = ("tests.conftest_multicompany",)


@pytest.fixture(autouse=True)
def _limpio(mundo):
    limpiar(mundo)
    yield


def _tarea_de_aprobacion(mundo, **extra) -> tuple[str, str, str]:
    regla(mundo.factory, mundo.company_a, effect="TASK", **extra)
    rid, paso = aprobacion(mundo)
    tick(mundo.factory)
    tid = valor(mundo.factory, "SELECT id FROM tasks WHERE source_id = :r", r=rid)
    assert tid, "la regla no creó la tarea"
    return tid, rid, paso


def _eventos(mundo, tid: str, tipo: str | None = None) -> int:
    if tipo:
        return valor(mundo.factory, "SELECT count(*) FROM task_events WHERE task_id = :t AND event_type = :e",
                     t=tid, e=tipo)
    return valor(mundo.factory, "SELECT count(*) FROM task_events WHERE task_id = :t", t=tid)


def _reasignar(mundo, usuario, empresa, tid, destino, version):
    cabeceras = dict(mundo.como(usuario, empresa))
    if version is not None:
        cabeceras["If-Match"] = str(version)
    return mundo.client.post(f"/api/v1/tasks/{tid}/reassign", headers=cabeceras,
                             json={"assignee_user_id": destino, "reason": "cambio de turno"})


def test_la_tarea_nace_con_los_elegibles_que_fijo_la_045(mundo):
    tid, rid, paso = _tarea_de_aprobacion(mundo)
    candidatos = {f[0] for f in filas(mundo.factory, "SELECT user_id FROM task_candidates WHERE task_id = :t",
                                      t=tid)}
    assert candidatos == elegibles(mundo.factory, paso) != set()
    t = mundo.get(f"/tasks/{tid}", "ua", mundo.company_a).json()
    assert (t["status"], t["assignee_user_id"], t["link"]["route_key"]) == ("OPEN", None, "approval_inbox")
    assert t["message"]["text"].startswith("Atender la aprobación de P047")
    assert [h["event_type"] for h in t["history"]] == ["CREATED"]
    assert {"start", "complete"} <= set(t["allowed_actions"])


def test_flujo_h_asignar_reasignar_y_completar_conserva_todo_el_historial(mundo):
    tid, _, _ = _tarea_de_aprobacion(mundo)
    ua, uab = uid(mundo.factory, "ua"), uid(mundo.factory, "uab")
    iniciada = mundo.post(f"/tasks/{tid}/start", "ua", mundo.company_a, {})
    assert iniciada.status_code == 200, iniciada.text
    assert (iniciada.json()["status"], iniciada.json()["assignee_user_id"]) == ("IN_PROGRESS", ua)

    reasignada = _reasignar(mundo, "ua", mundo.company_a, tid, uab, iniciada.json()["version"])
    assert reasignada.status_code == 200, reasignada.text
    assert reasignada.json()["assignee_user_id"] == uab

    completada = mundo.post(f"/tasks/{tid}/complete", "uab", mundo.company_a, {})
    assert completada.status_code == 200, completada.text
    historia = completada.json()["history"]
    assert [h["event_type"] for h in historia] == ["CREATED", "ASSIGNED", "STARTED", "REASSIGNED", "COMPLETED"]
    assert (historia[3]["from_user_id"], historia[3]["to_user_id"], historia[3]["reason"]) == \
        (ua, uab, "cambio de turno")
    assert _eventos(mundo, tid) == 5
    acciones = {f[0] for f in filas(mundo.factory, "SELECT action FROM audit_events WHERE entity_id = :t", t=tid)}
    assert {"TASK_CREATED", "TASK_STARTED", "TASK_REASSIGNED", "TASK_COMPLETED"} <= acciones


def test_flujo_i_completar_la_tarea_no_aprueba_nada(mundo):
    tid, rid, paso = _tarea_de_aprobacion(mundo)
    assert mundo.post(f"/tasks/{tid}/complete", "ua", mundo.company_a, {}).status_code == 200
    assert valor(mundo.factory, "SELECT status FROM approval_steps WHERE id = :p", p=paso) == "IN_REVIEW"
    assert valor(mundo.factory, "SELECT status FROM approval_requests WHERE id = :r", r=rid) != "APPROVED"
    assert valor(mundo.factory, "SELECT count(*) FROM approval_decisions WHERE step_id = :p", p=paso) == 0


def test_completar_dos_veces_da_conflicto_y_un_solo_efecto(mundo):
    tid, _, _ = _tarea_de_aprobacion(mundo)
    assert mundo.post(f"/tasks/{tid}/complete", "ua", mundo.company_a, {}).status_code == 200
    otra = mundo.post(f"/tasks/{tid}/complete", "ua", mundo.company_a, {})
    assert otra.status_code == 409 and codigo(otra) == "TASK_ALREADY_CLOSED"
    assert _eventos(mundo, tid, "COMPLETED") == 1


def test_dos_completados_forzados_a_la_vez_dejan_un_solo_efecto(mundo):
    tid, _, _ = _tarea_de_aprobacion(mundo)

    def completar(s):
        user, ctx = contexto(s, "ua", mundo.company_a)
        return service.completar_tarea(s, ctx=ctx, user=user, task_id=tid)

    _, segundo = carrera(mundo.factory, completar, completar)
    assert isinstance(segundo, ConflictError) and segundo.code == "TASK_ALREADY_CLOSED", repr(segundo)
    assert _eventos(mundo, tid, "COMPLETED") == 1


def test_dos_reasignaciones_con_la_misma_version_una_gana_y_otra_choca(mundo):
    tid, _, _ = _tarea_de_aprobacion(mundo)
    version = valor(mundo.factory, "SELECT version FROM tasks WHERE id = :t", t=tid)
    uab, admin = uid(mundo.factory, "uab"), uid(mundo.factory, "admin")

    def hacia(destino):
        def reasignar(s):
            user, ctx = contexto(s, "ua", mundo.company_a)
            return service.reasignar_tarea(s, ctx=ctx, user=user, task_id=tid, assignee_user_id=destino,
                                           reason=None, expected_version=version)
        return reasignar

    _, segundo = carrera(mundo.factory, hacia(uab), hacia(admin))
    assert isinstance(segundo, ConflictError) and segundo.code == "TASK_VERSION_CONFLICT", repr(segundo)
    assert valor(mundo.factory, "SELECT assignee_user_id FROM tasks WHERE id = :t", t=tid) == uab
    assert _eventos(mundo, tid, "REASSIGNED") == 1


def test_reasignar_exige_version_y_un_destino_con_acceso_a_la_empresa(mundo):
    tid, _, _ = _tarea_de_aprobacion(mundo)
    v = valor(mundo.factory, "SELECT version FROM tasks WHERE id = :t", t=tid)
    sin = _reasignar(mundo, "ua", mundo.company_a, tid, uid(mundo.factory, "uab"), None)
    assert sin.status_code == 428 and codigo(sin) == "TASK_IF_MATCH_REQUIRED"
    for ajeno in ("uc", "ub"):
        r = _reasignar(mundo, "ua", mundo.company_a, tid, uid(mundo.factory, ajeno), v)
        assert r.status_code == 422 and codigo(r) == "TASK_ASSIGNEE_NOT_IN_COMPANY", ajeno
    vieja = _reasignar(mundo, "ua", mundo.company_a, tid, uid(mundo.factory, "uab"), v + 5)
    assert vieja.status_code == 409 and codigo(vieja) == "TASK_VERSION_CONFLICT"
    assert _eventos(mundo, tid, "REASSIGNED") == 0


def test_la_tarea_y_la_alerta_se_cierran_cuando_la_045_resuelve(mundo):
    regla(mundo.factory, mundo.company_a, effect="ALERT", auto_close=True)
    tid, rid, paso = _tarea_de_aprobacion(mundo, auto_close=True)
    r = mundo.post(f"/approvals/steps/{paso}/approve", "ua", mundo.company_a, {"reason": None})
    assert r.status_code == 200, r.text
    tick(mundo.factory)
    assert valor(mundo.factory, "SELECT status FROM tasks WHERE id = :t", t=tid) == "RESOLVED_BY_SOURCE"
    assert filas(mundo.factory, "SELECT actor_type, actor_user_id FROM task_events WHERE task_id = :t "
                                "AND event_type = 'RESOLVED_BY_SOURCE'", t=tid) == [("SYSTEM", None)]
    assert valor(mundo.factory, "SELECT status FROM alerts WHERE source_id = :r", r=rid) == "RESOLVED"


def test_sin_auto_close_la_tarea_sigue_abierta_aunque_la_045_resuelva(mundo):
    tid, _, paso = _tarea_de_aprobacion(mundo, auto_close=False)
    assert mundo.post(f"/approvals/steps/{paso}/approve", "ua", mundo.company_a, {"reason": None}).status_code == 200
    tick(mundo.factory)
    assert valor(mundo.factory, "SELECT status FROM tasks WHERE id = :t", t=tid) == "OPEN"


def test_la_tarea_de_a_no_se_ve_ni_se_completa_desde_b(mundo):
    tid, _, _ = _tarea_de_aprobacion(mundo)
    r = mundo.get(f"/tasks/{tid}", "uab", mundo.company_b)
    assert r.status_code == 404 and codigo(r) == "TASK_NOT_FOUND"
    assert mundo.post(f"/tasks/{tid}/complete", "uab", mundo.company_b, {}).status_code == 404
    en_b = mundo.get("/tasks?page_size=100", "uab", mundo.company_b).json()
    assert tid not in {t["id"] for t in en_b["items"]}
    assert valor(mundo.factory, "SELECT status FROM tasks WHERE id = :t", t=tid) == "OPEN"


def test_un_candidato_de_otro_tenant_se_descarta_al_crear(mundo):
    ua, uc = uid(mundo.factory, "ua"), uid(mundo.factory, "uc")
    tid = publicar(mundo.factory, service.crear_tarea, efecto(
        mundo.company_a, message_key="approval.step_opened.task", destinatarios=frozenset({ua, uc})))
    assert {f[0] for f in filas(mundo.factory, "SELECT user_id FROM task_candidates WHERE task_id = :t",
                                t=tid)} == {ua}


def test_la_tarea_vencida_se_cuenta_con_el_reloj_con_zona(mundo):
    ua = uid(mundo.factory, "ua")
    antes = mundo.get("/notifications/counts", "ua", mundo.company_a).json()
    origen = f"Venc{marca()}"
    vencida = publicar(mundo.factory, service.crear_tarea, efecto(
        mundo.company_a, source_type=origen, message_key="approval.step_opened.task",
        destinatarios=frozenset({ua}), due_at=ahora() - timedelta(hours=1)))
    publicar(mundo.factory, service.crear_tarea, efecto(
        mundo.company_a, source_type=origen, message_key="approval.step_opened.task",
        destinatarios=frozenset({ua}), due_at=ahora() + timedelta(days=2)))
    lista = mundo.get(f"/tasks?overdue=true&source_type={origen}", "ua", mundo.company_a).json()
    assert [t["id"] for t in lista["items"]] == [vencida] and lista["items"][0]["overdue"] is True
    despues = mundo.get("/notifications/counts", "ua", mundo.company_a).json()
    assert despues["overdue_tasks"] == antes["overdue_tasks"] + 1
    assert despues["open_tasks"] == antes["open_tasks"] + 2


def test_un_vencimiento_sin_zona_se_rechaza(mundo):
    with mundo.factory() as db, pytest.raises(ValueError):
        service.crear_tarea(db, efecto(mundo.company_a, message_key="approval.step_opened.task",
                                       due_at=datetime(2030, 1, 1, 12, 0)))


def test_repetir_el_hecho_no_duplica_la_tarea(mundo):
    tid, rid, _ = _tarea_de_aprobacion(mundo)
    ejecutar(mundo.factory, "DELETE FROM notification_event_receipts WHERE source_event_id IN "
                            "(SELECT id FROM approval_events WHERE request_id = :r)", r=rid)
    tick(mundo.factory)
    assert valor(mundo.factory, "SELECT count(*) FROM tasks WHERE source_id = :r", r=rid) == 1


def test_mas_de_cien_tareas_se_recorren_por_paginas(mundo):
    ua = uid(mundo.factory, "ua")
    origen = f"Vol{marca()}"
    with mundo.factory() as db:
        for _ in range(105):
            service.crear_tarea(db, efecto(mundo.company_a, source_type=origen,
                                           message_key="approval.step_opened.task", destinatarios=frozenset({ua})))
        db.commit()
    paginas = [mundo.get(f"/tasks?source_type={origen}&page={p}&page_size=50", "ua", mundo.company_a).json()
               for p in (1, 2, 3)]
    assert [len(p["items"]) for p in paginas] == [50, 50, 5]
    assert {p["total"] for p in paginas} == {105}
    assert len({t["id"] for p in paginas for t in p["items"]}) == 105


def test_sin_permiso_no_se_completa_y_sin_ver_todas_no_se_listan_todas(mundo):
    limitado, lid = usuario_limitado(mundo, [mundo.company_a], sin={"tareas:complete", "tareas:view"})
    tid = publicar(mundo.factory, service.crear_tarea, efecto(
        mundo.company_a, message_key="approval.step_opened.task", destinatarios=frozenset({lid})))
    r = mundo.post(f"/tasks/{tid}/complete", limitado, mundo.company_a, {})
    assert r.status_code == 403 and codigo(r) == "TASK_NOT_ACTIONABLE"
    assert mundo.get("/tasks?scope=all", limitado, mundo.company_a).status_code == 403
    propias = mundo.get("/tasks?page_size=100", limitado, mundo.company_a).json()
    assert tid in {t["id"] for t in propias["items"]}


def test_las_prioridades_son_de_la_empresa_y_se_validan(mundo):
    code = f"P{marca()}"
    creada = mundo.post("/tasks/priorities", "ua", mundo.company_a, {"code": code, "name": "Alta", "rank": 1})
    assert creada.status_code == 201, creada.text
    otra = mundo.post("/tasks/priorities", "ua", mundo.company_a, {"code": code, "name": "Alta", "rank": 1})
    assert otra.status_code == 409 and codigo(otra) == "TASK_PRIORITY_CODE_TAKEN"
    regla_mala = mundo.post("/notifications/rules", "ua", mundo.company_a, {
        "code": f"R{marca()}", "source": "APPROVAL", "event_type": "approval.step_opened",
        "effect": "TASK", "priority_code": "NO_EXISTE"})
    assert regla_mala.status_code == 422 and codigo(regla_mala) == "TASK_PRIORITY_NOT_FOUND"
    assert code not in {p["code"] for p in mundo.get("/tasks/priorities", "ub", mundo.company_b).json()}

    tid, _, _ = _tarea_de_aprobacion(mundo, priority_code=code)
    assert filas(mundo.factory, "SELECT priority_code, priority_rank FROM tasks WHERE id = :t", t=tid) == [(code, 1)]
    filtradas = mundo.get(f"/tasks?priority={code}&page_size=100", "ua", mundo.company_a).json()
    assert [t["id"] for t in filtradas["items"]] == [tid]
