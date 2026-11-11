"""Spec 047 · planificador de plataforma (ADR-D0-015) contra PostgreSQL."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime, timedelta

import pytest

from app.modules.notifications import service
from app.modules.scheduler.service import Manejador, Resultado, tick
from tests.spec047_support import (
    aprobacion,
    con_vencimiento_045_habilitado,
    efecto,
    ejecutar,
    filas,
    limpiar,
    publicar,
    regla,
    rol_admin,
    solo,
    uid,
    valor,
)

pytest_plugins = ("tests.conftest_multicompany",)

#: Reloj lógico lejos del real: los ticks de limpieza, con la hora real, no tocan
#: estas tareas.
T0 = datetime(2030, 1, 15, 12, 0, tzinfo=UTC)


@pytest.fixture(autouse=True)
def _limpio(mundo):
    limpiar(mundo)
    yield


def _tarea_programada(mundo, empresa: str, due_at: datetime, candidatos: set[str], **extra) -> str:
    rule_id = regla(mundo.factory, empresa, effect="TASK", **extra)
    return publicar(mundo.factory, service.crear_tarea, efecto(
        empresa, rule_id=rule_id, due_at=due_at, destinatarios=frozenset(candidatos),
        message_key="approval.step_opened.task", category="approval.step_opened"))


def _efectos(mundo, tid: str, clase: str) -> list[tuple]:
    return filas(mundo.factory, "SELECT id, company_id, dedupe_key, mandatory, actor_type, actor_user_id "
                                "FROM notifications WHERE dedupe_key LIKE :k ORDER BY dedupe_key",
                 k=f"task:{tid}:{clase}:%")


def _eventos(mundo, tid: str, tipo: str) -> int:
    return valor(mundo.factory, "SELECT count(*) FROM task_events WHERE task_id = :t AND event_type = :e",
                 t=tid, e=tipo)


# ------------------------------------------------------------------ flujo A
def test_flujo_a_un_recordatorio_se_emite_una_sola_vez_aunque_el_tick_se_repita(mundo):
    ua = uid(mundo.factory, "ua")
    tid = _tarea_programada(mundo, mundo.company_a, T0 + timedelta(minutes=30), {ua}, reminder_offset_minutes=60)
    salidas = [tick(mundo.factory, now=momento, manejadores=solo("task_reminders")).exit_code
               for momento in (T0, T0, T0 + timedelta(hours=5))]
    assert salidas == [0, 0, 0]
    efectos = _efectos(mundo, tid, "reminder")
    assert len(efectos) == 1 and _eventos(mundo, tid, "REMINDED") == 1
    assert {f[0] for f in filas(mundo.factory, "SELECT user_id FROM notification_recipients "
                                               "WHERE notification_id = :n", n=efectos[0][0])} == {ua}


def test_antes_de_su_ventana_no_se_recuerda(mundo):
    tid = _tarea_programada(mundo, mundo.company_a, T0 + timedelta(hours=3), {uid(mundo.factory, "ua")},
                            reminder_offset_minutes=60)
    tick(mundo.factory, now=T0, manejadores=solo("task_reminders"))
    assert _efectos(mundo, tid, "reminder") == []


# ------------------------------------------------------------------ flujo C
def test_flujo_c_tras_48_horas_sin_ticks_solo_se_emite_la_ventana_vigente(mundo):
    tid = _tarea_programada(mundo, mundo.company_a, T0 - timedelta(hours=48), {uid(mundo.factory, "ua")},
                            reminder_offset_minutes=0, reminder_repeat_minutes=60)
    tick(mundo.factory, now=T0, manejadores=solo("task_reminders"))
    efectos = _efectos(mundo, tid, "reminder")
    assert len(efectos) == 1 and efectos[0][2].endswith(":48")
    tick(mundo.factory, now=T0 + timedelta(minutes=30), manejadores=solo("task_reminders"))
    assert len(_efectos(mundo, tid, "reminder")) == 1
    tick(mundo.factory, now=T0 + timedelta(minutes=61), manejadores=solo("task_reminders"))
    assert [f[2].rsplit(":", 1)[1] for f in _efectos(mundo, tid, "reminder")] == ["48", "49"]


# ------------------------------------------------------------------ escaladas
def test_la_escalada_llega_una_vez_a_quien_tiene_el_rol_en_esa_empresa(mundo):
    tid = _tarea_programada(mundo, mundo.company_a, T0 - timedelta(hours=2), {uid(mundo.factory, "ua")},
                            escalation_after_minutes=30, escalation_role_id=rol_admin(mundo.factory))
    tick(mundo.factory, now=T0, manejadores=solo("task_escalations"))
    tick(mundo.factory, now=T0 + timedelta(hours=1), manejadores=solo("task_escalations"))
    efectos = _efectos(mundo, tid, "escalation")
    assert len(efectos) == 1 and efectos[0][3] is True and _eventos(mundo, tid, "ESCALATED") == 1
    destino = {f[0] for f in filas(mundo.factory, "SELECT user_id FROM notification_recipients "
                                                  "WHERE notification_id = :n", n=efectos[0][0])}
    assert {uid(mundo.factory, u) for u in ("admin", "ua", "uab")} <= destino
    assert not destino & {uid(mundo.factory, u) for u in ("ub", "uc", "adminc")}


def test_cada_efecto_se_crea_en_la_empresa_de_su_tarea(mundo):
    uab = uid(mundo.factory, "uab")
    de_a = _tarea_programada(mundo, mundo.company_a, T0 - timedelta(hours=1), {uab}, reminder_offset_minutes=0)
    de_b = _tarea_programada(mundo, mundo.company_b, T0 - timedelta(hours=1), {uab}, reminder_offset_minutes=0)
    tick(mundo.factory, now=T0, manejadores=solo("task_reminders"))
    for tid, empresa in ((de_a, mundo.company_a), (de_b, mundo.company_b)):
        assert [f[1] for f in _efectos(mundo, tid, "reminder")] == [empresa]
        assert filas(mundo.factory, "SELECT company_id FROM task_events WHERE task_id = :t "
                                    "AND event_type = 'REMINDED'", t=tid) == [(empresa,)]
    en_a = {i["id"] for i in mundo.get("/notifications?state=all&page_size=100", "uab",
                                       mundo.company_a).json()["items"]}
    assert _efectos(mundo, de_a, "reminder")[0][0] in en_a
    assert _efectos(mundo, de_b, "reminder")[0][0] not in en_a


# ------------------------------------------------------------------ flujo B
def test_flujo_b_un_tick_solapado_se_registra_y_no_ejecuta_nada(mundo):
    tid = _tarea_programada(mundo, mundo.company_a, T0 - timedelta(hours=1), {uid(mundo.factory, "ua")},
                            reminder_offset_minutes=0)
    dentro, soltar, salida = threading.Event(), threading.Event(), {}

    def lento(_contexto):
        dentro.set()
        assert soltar.wait(30)
        return Resultado()

    primero = (Manejador("lento_de_prueba", "047", True, "EFFECT_ONCE", lento), *solo("task_reminders"))
    hilo = threading.Thread(target=lambda: salida.update(r=tick(mundo.factory, now=T0, manejadores=primero)))
    hilo.start()
    try:
        assert dentro.wait(30), "el primer tick nunca llegó a su manejador"
        segundo = tick(mundo.factory, now=T0, manejadores=solo("task_reminders"))
    finally:
        soltar.set()
        hilo.join(60)
    assert (segundo.status, segundo.exit_code, segundo.handlers) == ("SKIPPED_OVERLAP", 0, [])
    assert salida["r"].status == "COMPLETED"
    assert filas(mundo.factory, "SELECT r.status, r.finished_at IS NOT NULL, count(h.id) FROM scheduler_runs r "
                                "LEFT JOIN scheduler_handler_runs h ON h.run_id = r.id "
                                "WHERE r.correlation_id = :c GROUP BY r.status, r.finished_at",
                 c=segundo.correlation_id) == [("SKIPPED_OVERLAP", True, 0)]
    assert len(_efectos(mundo, tid, "reminder")) == 1 and _eventos(mundo, tid, "REMINDED") == 1


def test_dos_ticks_reales_a_la_vez_no_duplican_el_consumo(mundo):
    regla(mundo.factory, mundo.company_a)
    rid, _ = aprobacion(mundo)
    barrera, resultados = threading.Barrier(2), []

    def correr():
        barrera.wait(10)
        resultados.append(tick(mundo.factory, manejadores=solo("approval_event_intake")))

    hilos = [threading.Thread(target=correr) for _ in range(2)]
    [h.start() for h in hilos]
    [h.join(60) for h in hilos]
    assert len(resultados) == 2 and {r.exit_code for r in resultados} == {0}
    assert sorted(r.status for r in resultados) in (["COMPLETED", "COMPLETED"], ["COMPLETED", "SKIPPED_OVERLAP"])
    assert valor(mundo.factory, "SELECT count(*) FROM notifications WHERE source_id = :r", r=rid) == 1


# ------------------------------------------------------------------ registro y salida
def test_el_tick_deja_registro_de_cada_manejador_y_el_de_la_045_deshabilitado(mundo):
    r = tick(mundo.factory)
    assert filas(mundo.factory, "SELECT status, finished_at IS NOT NULL FROM scheduler_runs "
                                "WHERE correlation_id = :c", c=r.correlation_id) == [("COMPLETED", True)]
    manejadores = {f[0]: (f[1], f[2], f[3]) for f in filas(
        mundo.factory, "SELECT h.handler_code, h.owner_spec, h.status, h.catch_up FROM scheduler_handler_runs h "
                       "JOIN scheduler_runs r ON r.id = h.run_id WHERE r.correlation_id = :c", c=r.correlation_id)}
    assert manejadores == {
        "approval_step_expiration": ("045", "DISABLED", "OWNER_IDEMPOTENT"),
        "approval_event_intake": ("047", "COMPLETED", "DRAIN"),
        "task_reminders": ("047", "COMPLETED", "LATEST_WINDOW"),
        "task_escalations": ("047", "COMPLETED", "EFFECT_ONCE"),
        "notification_delivery": ("047", "COMPLETED", "DUE_RETRY"),
        "installation_backup": ("001", "COMPLETED", "LATEST_WINDOW"),
        "backup_retention": ("001", "COMPLETED", "OWNER_IDEMPOTENT"),
        "backup_rpo_evaluation": ("001", "COMPLETED", "OWNER_IDEMPOTENT"),
        "planning_replenishment_detection": ("015", "COMPLETED", "OWNER_IDEMPOTENT"),
    }


def test_un_manejador_que_falla_no_detiene_a_los_demas_y_el_tick_sale_con_dos(mundo):
    llamados = []

    def roto(_contexto):
        raise RuntimeError("simulado")

    def sano(_contexto):
        llamados.append(1)
        return Resultado(seen=1, processed=1)

    r = tick(mundo.factory, manejadores=(Manejador("roto_de_prueba", "047", True, "EFFECT_ONCE", roto),
                                         Manejador("sano_de_prueba", "047", True, "EFFECT_ONCE", sano)))
    assert (r.status, r.exit_code, llamados) == ("COMPLETED_WITH_ERRORS", 2, [1])
    assert dict((f[0], (f[1], f[2])) for f in filas(
        mundo.factory, "SELECT h.handler_code, h.status, h.error_code FROM scheduler_handler_runs h JOIN "
                       "scheduler_runs r ON r.id = h.run_id WHERE r.correlation_id = :c", c=r.correlation_id)) == {
        "roto_de_prueba": ("FAILED", "RuntimeError"), "sano_de_prueba": ("COMPLETED", None)}


def test_la_orden_devuelve_su_estado_y_su_codigo_de_salida(mundo, capsys, monkeypatch):
    from app.modules.scheduler import __main__ as orden
    from app.modules.scheduler import service as planificador

    codigo = orden.main(["tick"])
    salida = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert (codigo, salida["exit_code"], salida["status"]) == (0, 0, "COMPLETED")

    def sin_base(*_a, **_k):
        raise OSError("sin base")

    monkeypatch.setattr(planificador, "tick", sin_base)
    assert orden.main(["tick"]) == 1
    assert json.loads(capsys.readouterr().out.strip().splitlines()[-1]) == {"status": "FAILED", "error_code": "OSError"}


def test_un_reloj_sin_zona_se_rechaza(mundo):
    with pytest.raises(ValueError):
        tick(mundo.factory, now=datetime(2030, 1, 15, 12, 0), manejadores=())


def test_los_efectos_del_planificador_son_del_sistema_sin_usuario_ficticio(mundo):
    tid = _tarea_programada(mundo, mundo.company_a, T0 - timedelta(hours=1), {uid(mundo.factory, "ua")},
                            reminder_offset_minutes=0)
    tick(mundo.factory, now=T0, manejadores=solo("task_reminders"))
    (nid, _, _, _, actor_type, actor_user), = _efectos(mundo, tid, "reminder")
    assert (actor_type, actor_user) == ("SYSTEM", None)
    assert filas(mundo.factory, "SELECT user_id, source FROM audit_events WHERE entity_id = :n", n=nid) == \
        [(None, "SCHEDULER")]


# ------------------------------------------------------------------ correlación y lotes
def test_el_efecto_guarda_el_hecho_de_origen_y_el_tick_que_lo_produjo(mundo):
    regla(mundo.factory, mundo.company_a)
    rid, _ = aprobacion(mundo)
    r = tick(mundo.factory, manejadores=solo("approval_event_intake"))
    evento = valor(mundo.factory, "SELECT id FROM approval_events WHERE request_id = :r "
                                  "AND event_type = 'approval.step_opened'", r=rid)
    assert filas(mundo.factory, "SELECT source_event_id, correlation_id FROM notifications WHERE source_id = :r",
                 r=rid) == [(evento, r.correlation_id)]
    assert filas(mundo.factory, "SELECT outcome, run_correlation_id FROM notification_event_receipts "
                                "WHERE source_event_id = :e", e=evento) == [("APPLIED", r.correlation_id)]


def test_un_hecho_masivo_se_consume_por_lotes_sin_duplicar(mundo, monkeypatch):
    from app.modules.notifications import handlers

    regla(mundo.factory, mundo.company_a)
    solicitudes = [aprobacion(mundo)[0] for _ in range(3)]
    pendientes = valor(mundo.factory, "SELECT count(*) FROM approval_events e WHERE NOT EXISTS "
                                      "(SELECT 1 FROM notification_event_receipts r WHERE r.source_event_id = e.id)")
    assert pendientes > 2
    monkeypatch.setattr(handlers, "LOTE_POR_TICK", 2)
    vistos = []
    for _ in range(pendientes):
        resultado = tick(mundo.factory, manejadores=solo("approval_event_intake"))
        vistos.append(resultado.handlers[0]["seen"])
        if resultado.handlers[0]["seen"] == 0:
            break
    assert max(vistos) == 2 and sum(vistos) == pendientes
    for rid in solicitudes:
        assert valor(mundo.factory, "SELECT count(*) FROM notifications WHERE source_id = :r", r=rid) == 1


# ------------------------------------------------------------------ flujo D
def test_flujo_d_el_vencimiento_de_la_045_solo_corre_si_su_duena_lo_habilita(mundo):
    regla(mundo.factory, mundo.company_a, event_type="approval.step_expired")
    rid, paso = aprobacion(mundo)
    ejecutar(mundo.factory, "UPDATE approval_steps SET due_at = now() - interval '1 hour' WHERE id = :p", p=paso)

    tick(mundo.factory)
    assert valor(mundo.factory, "SELECT status FROM approval_steps WHERE id = :p", p=paso) == "IN_REVIEW"

    for _ in range(2):
        tick(mundo.factory, manejadores=con_vencimiento_045_habilitado())
    assert valor(mundo.factory, "SELECT status FROM approval_steps WHERE id = :p", p=paso) == "EXPIRED"
    assert valor(mundo.factory, "SELECT count(*) FROM approval_events WHERE request_id = :r "
                                "AND event_type = 'approval.step_expired'", r=rid) == 1
    assert valor(mundo.factory, "SELECT count(*) FROM notifications WHERE source_id = :r "
                                "AND category = 'approval.step_expired'", r=rid) == 1
