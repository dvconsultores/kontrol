"""Spec 047 · notificaciones y alertas contra PostgreSQL y el motor real de la 045."""

from __future__ import annotations

import threading
from datetime import timedelta

import pytest
from sqlalchemy import event

from app.modules.notifications import delivery, messages, service
from app.modules.scheduler.service import tick
from tests.concurrency import carrera
from tests.spec047_support import (
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
    solo,
    uid,
    usuario_limitado,
    valor,
)

pytest_plugins = ("tests.conftest_multicompany",)


@pytest.fixture(autouse=True)
def _limpio(mundo):
    limpiar(mundo)
    yield


def _notificaciones(mundo, source_id: str) -> list[tuple]:
    return filas(mundo.factory, "SELECT id, company_id, actor_type, actor_user_id, category, route_key "
                                "FROM notifications WHERE source_id = :s ORDER BY created_at", s=source_id)


def _destinatarios(mundo, notification_id: str) -> set[str]:
    return {r[0] for r in filas(mundo.factory, "SELECT user_id FROM notification_recipients "
                                               "WHERE notification_id = :n", n=notification_id)}


def _contadores(mundo, usuario: str, empresa: str) -> dict:
    r = mundo.get("/notifications/counts", usuario, empresa)
    assert r.status_code == 200, r.text
    return r.json()


# ------------------------------------------------------------------ flujo A
def test_flujo_a_una_aprobacion_real_notifica_una_vez_a_cada_elegible(mundo):
    regla(mundo.factory, mundo.company_a)
    rid, paso = aprobacion(mundo)
    tick(mundo.factory)

    notas = _notificaciones(mundo, rid)
    assert len(notas) == 1
    nid, empresa, actor_type, actor_user, categoria, ruta = notas[0]
    assert (empresa, actor_type, actor_user, categoria, ruta) == (
        mundo.company_a, "SYSTEM", None, "approval.step_opened", "approval_inbox")
    assert _destinatarios(mundo, nid) == elegibles(mundo.factory, paso) != set()

    item = next(i for i in mundo.get("/notifications?state=unread&page_size=100", "ua",
                                     mundo.company_a).json()["items"] if i["id"] == nid)
    assert item["message"]["key"] == "approval.step_opened.notification"
    assert item["message"]["text"].startswith("Hay una aprobación de P047")
    assert item["link"] == {"source_type": "ApprovalRequest", "source_id": rid,
                            "source_item_id": paso, "route_key": "approval_inbox"}


def test_el_planificador_audita_como_sistema_y_la_lectura_como_persona(mundo):
    nid = publicar(mundo.factory, service.crear_notificacion,
                   efecto(mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua")})))
    assert mundo.post(f"/notifications/{nid}/read", "ua", mundo.company_a, {}).status_code == 200
    rastro = filas(mundo.factory, "SELECT action, user_id, source FROM audit_events WHERE entity_id = :n "
                                  "ORDER BY event_time", n=nid)
    assert rastro == [("NOTIFICATION_CREATED", None, "SCHEDULER"),
                      ("NOTIFICATION_READ", uid(mundo.factory, "ua"), "API")]


# --------------------------------------------------------------- idempotencia
def test_el_mismo_hecho_no_duplica_ni_repetido_ni_tras_perder_el_recibo(mundo):
    regla(mundo.factory, mundo.company_a)
    rid, _ = aprobacion(mundo)
    tick(mundo.factory)
    tick(mundo.factory)
    assert len(_notificaciones(mundo, rid)) == 1

    # Caída después del commit del dominio y antes de que el consumo quedara escrito.
    ejecutar(mundo.factory, "DELETE FROM notification_event_receipts WHERE source_event_id IN "
                            "(SELECT id FROM approval_events WHERE request_id = :r)", r=rid)
    tick(mundo.factory)
    assert len(_notificaciones(mundo, rid)) == 1
    assert valor(mundo.factory, "SELECT count(*) FROM notification_event_receipts WHERE source_event_id IN "
                                "(SELECT id FROM approval_events WHERE request_id = :r)", r=rid) >= 1


def test_dos_publicaciones_forzadas_del_mismo_hecho_no_duplican_ni_revientan(mundo):
    e = efecto(mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua")}))
    primero, segundo = carrera(mundo.factory, lambda s: service.crear_notificacion(s, e),
                               lambda s: service.crear_notificacion(s, e))
    assert not isinstance(segundo, Exception), f"la carrera escapó como excepción: {segundo!r}"
    assert segundo[1] is False and str(segundo[0].id) == str(primero[0].id)
    assert valor(mundo.factory, "SELECT count(*) FROM notifications WHERE dedupe_key = :k",
                 k=e.dedupe_key) == 1


def test_diez_reintentos_simultaneos_producen_una_sola_notificacion(mundo):
    e = efecto(mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua")}))
    barrera, errores = threading.Barrier(10), []

    def intentar():
        with mundo.factory() as db:
            try:
                barrera.wait(10)
                service.crear_notificacion(db, e)
                db.commit()
            except Exception as error:  # noqa: BLE001 - se cuenta, no se oculta
                errores.append(error)

    hilos = [threading.Thread(target=intentar) for _ in range(10)]
    [h.start() for h in hilos]
    [h.join(30) for h in hilos]
    assert errores == []
    assert valor(mundo.factory, "SELECT count(*) FROM notifications WHERE dedupe_key = :k", k=e.dedupe_key) == 1
    assert valor(mundo.factory, "SELECT count(*) FROM notification_recipients r JOIN notifications n "
                                "ON n.id = r.notification_id WHERE n.dedupe_key = :k", k=e.dedupe_key) == 1


# ------------------------------------------------------- estado por destinatario
def test_flujo_g_cada_destinatario_tiene_su_propio_estado_de_lectura(mundo):
    nid = publicar(mundo.factory, service.crear_notificacion, efecto(
        mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua"), uid(mundo.factory, "uab")})))
    leida = mundo.post(f"/notifications/{nid}/read", "ua", mundo.company_a, {})
    assert leida.status_code == 200 and leida.json()["read_at"] is not None
    assert mundo.get(f"/notifications/{nid}", "uab", mundo.company_a).json()["read_at"] is None
    assert valor(mundo.factory, "SELECT count(*) FROM notification_recipients WHERE notification_id = :n "
                                "AND read_at IS NULL", n=nid) == 1


def test_leer_dos_veces_no_cambia_la_fecha_ni_audita_dos_veces(mundo):
    nid = publicar(mundo.factory, service.crear_notificacion,
                   efecto(mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua")})))
    a = mundo.post(f"/notifications/{nid}/read", "ua", mundo.company_a, {}).json()["read_at"]
    b = mundo.post(f"/notifications/{nid}/read", "ua", mundo.company_a, {}).json()["read_at"]
    assert a == b
    assert valor(mundo.factory, "SELECT count(*) FROM audit_events WHERE entity_id = :n "
                                "AND action = 'NOTIFICATION_READ'", n=nid) == 1


def test_archivar_no_borra_y_sale_de_las_activas(mundo):
    cat = f"arch.{marca()}"
    nid = publicar(mundo.factory, service.crear_notificacion, efecto(
        mundo.company_a, category=cat, destinatarios=frozenset({uid(mundo.factory, "ua")})))
    assert mundo.post(f"/notifications/{nid}/archive", "ua", mundo.company_a, {}).json()["archived_at"]
    activas = mundo.get(f"/notifications?state=active&category={cat}", "ua", mundo.company_a).json()
    archivadas = mundo.get(f"/notifications?state=archived&category={cat}", "ua", mundo.company_a).json()
    assert activas["total"] == 0 and [i["id"] for i in archivadas["items"]] == [nid]
    assert valor(mundo.factory, "SELECT count(*) FROM notifications WHERE id = :n", n=nid) == 1


def test_una_notificacion_critica_no_caduca_sola(mundo):
    nid = publicar(mundo.factory, service.crear_notificacion, efecto(
        mundo.company_a, severity="CRITICAL", mandatory=True,
        destinatarios=frozenset({uid(mundo.factory, "ua")})))
    tick(mundo.factory)
    item = mundo.get(f"/notifications/{nid}", "ua", mundo.company_a).json()
    assert (item["severity"], item["mandatory"], item["archived_at"]) == ("CRITICAL", True, None)


# ------------------------------------------------------------ aislamiento
def test_flujo_l_la_notificacion_de_a_no_existe_en_el_contexto_de_b(mundo):
    antes_b = _contadores(mundo, "uab", mundo.company_b)
    antes_a = _contadores(mundo, "uab", mundo.company_a)
    nid = publicar(mundo.factory, service.crear_notificacion,
                   efecto(mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "uab")})))

    en_b = mundo.get("/notifications?state=all&page_size=100", "uab", mundo.company_b).json()
    assert nid not in {i["id"] for i in en_b["items"]}
    r = mundo.get(f"/notifications/{nid}", "uab", mundo.company_b)
    assert r.status_code == 404 and codigo(r) == "NOTIFICATION_NOT_FOUND"
    assert mundo.post(f"/notifications/{nid}/read", "uab", mundo.company_b, {}).status_code == 404
    assert _contadores(mundo, "uab", mundo.company_b) == antes_b
    assert _contadores(mundo, "uab", mundo.company_a)["unread_notifications"] == antes_a["unread_notifications"] + 1


def test_un_id_ajeno_responde_igual_que_uno_inexistente(mundo):
    nid = publicar(mundo.factory, service.crear_notificacion,
                   efecto(mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua")})))
    ajeno = mundo.get(f"/notifications/{nid}", "ub", mundo.company_b)
    inexistente = mundo.get("/notifications/00000000-0000-0000-0000-000000000000", "ub", mundo.company_b)
    assert ajeno.status_code == inexistente.status_code == 404
    assert (ajeno.json()["code"], ajeno.json()["message"], ajeno.json()["details"]) == \
        (inexistente.json()["code"], inexistente.json()["message"], inexistente.json()["details"])
    assert "PRUEBA" not in ajeno.text
    assert ajeno.json()["message"] == messages.texto("error.notification_not_found")


def test_un_usuario_de_otro_tenant_nunca_llega_a_destinatario(mundo):
    nid = publicar(mundo.factory, service.crear_notificacion, efecto(
        mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua"), uid(mundo.factory, "uc")})))
    assert _destinatarios(mundo, nid) == {uid(mundo.factory, "ua")}
    r = mundo.get(f"/notifications/{nid}", "uc", mundo.company_c, tenant="T2")
    assert r.status_code == 404


# ------------------------------------------------------------ enlace y permiso
def test_flujo_j_sin_permiso_del_origen_el_item_no_existe_para_el_usuario(mundo):
    limitado, id_limitado = usuario_limitado(mundo, [mundo.company_a], sin={"aprobaciones:view"})
    antes = _contadores(mundo, limitado, mundo.company_a)
    nid = publicar(mundo.factory, service.crear_notificacion, efecto(
        mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua"), id_limitado})))

    assert id_limitado in _destinatarios(mundo, nid)     # instantánea fijada al crear
    lista = mundo.get("/notifications?state=all&page_size=100", limitado, mundo.company_a).json()
    assert nid not in {i["id"] for i in lista["items"]}
    r = mundo.get(f"/notifications/{nid}", limitado, mundo.company_a)
    assert r.status_code == 404 and "PRUEBA" not in r.text
    assert _contadores(mundo, limitado, mundo.company_a) == antes

    permitido = mundo.get(f"/notifications/{nid}", "ua", mundo.company_a).json()
    assert permitido["link"]["route_key"] == "approval_inbox"


# ------------------------------------------------------------ preferencias
def test_una_preferencia_opcional_apagada_evita_el_destinatario(mundo):
    cat = f"pref.{marca()}"
    r = mundo.put_json("/notifications/preferences", "ua", mundo.company_a,
                       {"category": cat, "channel": "INTERNAL", "enabled": False})
    assert r.status_code == 200, r.text
    ua, uab = uid(mundo.factory, "ua"), uid(mundo.factory, "uab")
    opcional = publicar(mundo.factory, service.crear_notificacion,
                        efecto(mundo.company_a, category=cat, destinatarios=frozenset({ua, uab})))
    obligatoria = publicar(mundo.factory, service.crear_notificacion, efecto(
        mundo.company_a, category=cat, mandatory=True, destinatarios=frozenset({ua, uab})))
    assert _destinatarios(mundo, opcional) == {uab}
    assert _destinatarios(mundo, obligatoria) == {ua, uab}


def test_una_notificacion_obligatoria_no_se_desactiva(mundo):
    regla(mundo.factory, mundo.company_a, event_type="approval.step_expired", mandatory=True)
    r = mundo.put_json("/notifications/preferences", "ua", mundo.company_a,
                       {"category": "approval.step_expired", "channel": "INTERNAL", "enabled": False})
    assert r.status_code == 409 and codigo(r) == "NOTIFICATION_MANDATORY"


def test_sin_proveedor_el_canal_externo_no_esta_disponible(mundo):
    r = mundo.put_json("/notifications/preferences", "ua", mundo.company_a,
                       {"category": "x", "channel": "EMAIL", "enabled": True})
    assert r.status_code == 422 and codigo(r) == "CHANNEL_UNAVAILABLE"


# ------------------------------------------------------------ entrega externa
class _Proveedor:
    def __init__(self, falla: bool, max_intentos: int = 2):
        self.falla, self.max_intentos = falla, max_intentos
        self.espera_entre_intentos = timedelta(minutes=5)
        self.envios: list[str] = []

    def enviar(self, envio):
        self.envios.append(envio.delivery_id)
        if self.falla:
            raise ConnectionError("simulado")


def _con_correo(mundo, monkeypatch, proveedor, categoria):
    monkeypatch.setitem(delivery.PROVEEDORES, "EMAIL", proveedor)
    r = mundo.put_json("/notifications/preferences", "ua", mundo.company_a,
                       {"category": categoria, "channel": "EMAIL", "enabled": True})
    assert r.status_code == 200, r.text
    return publicar(mundo.factory, service.crear_notificacion, efecto(
        mundo.company_a, category=categoria, destinatarios=frozenset({uid(mundo.factory, "ua")})))


def test_flujo_k_el_fallo_del_canal_externo_no_toca_la_notificacion_interna(mundo, monkeypatch):
    proveedor = _Proveedor(falla=True)
    nid = _con_correo(mundo, monkeypatch, proveedor, f"mail.{marca()}")
    t0 = valor(mundo.factory, "SELECT now()")

    tick(mundo.factory, now=t0, manejadores=solo("notification_delivery"))
    estado = filas(mundo.factory, "SELECT d.status, d.attempts FROM notification_deliveries d JOIN "
                                  "notification_recipients r ON r.id = d.recipient_id WHERE r.notification_id = :n",
                   n=nid)
    assert estado == [("RETRYING", 1)]
    tick(mundo.factory, now=t0 + timedelta(minutes=10), manejadores=solo("notification_delivery"))
    estado = filas(mundo.factory, "SELECT d.status, d.attempts, d.last_error_code FROM notification_deliveries d "
                                  "JOIN notification_recipients r ON r.id = d.recipient_id "
                                  "WHERE r.notification_id = :n", n=nid)
    assert estado == [("FAILED", 2, "ConnectionError")]
    assert valor(mundo.factory, "SELECT count(*) FROM notification_recipients WHERE notification_id = :n",
                 n=nid) == 1
    assert mundo.get(f"/notifications/{nid}", "ua", mundo.company_a).status_code == 200


def test_una_entrega_enviada_no_se_reenvia_en_el_siguiente_tick(mundo, monkeypatch):
    proveedor = _Proveedor(falla=False)
    _con_correo(mundo, monkeypatch, proveedor, f"mail.{marca()}")
    tick(mundo.factory, manejadores=solo("notification_delivery"))
    tick(mundo.factory, manejadores=solo("notification_delivery"))
    assert len(proveedor.envios) == 1


# ------------------------------------------------------------ alertas
def test_flujo_e_la_alerta_se_ve_con_permiso_y_no_crea_tarea(mundo):
    regla(mundo.factory, mundo.company_a, effect="ALERT", severity="WARNING")
    rid, _ = aprobacion(mundo)
    tick(mundo.factory)
    alertas = mundo.get("/alerts?status=ACTIVE&page_size=100", "ua", mundo.company_a).json()
    assert [a["severity"] for a in alertas["items"] if a["link"]["source_id"] == rid] == ["WARNING"]
    assert valor(mundo.factory, "SELECT count(*) FROM tasks WHERE source_id = :r", r=rid) == 0

    limitado, _ = usuario_limitado(mundo, [mundo.company_a], sin={"alertas:view"})
    assert mundo.get("/alerts", limitado, mundo.company_a).status_code == 403
    assert _contadores(mundo, limitado, mundo.company_a)["active_alerts"] == 0


# ------------------------------------------------------------ historia
def test_flujo_f_cambiar_la_redaccion_no_toca_la_fila(mundo, monkeypatch):
    clave = "approval.step_opened.notification"
    nid = publicar(mundo.factory, service.crear_notificacion,
                   efecto(mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua")})))
    antes = filas(mundo.factory, "SELECT message_key, message_params::text FROM notifications WHERE id = :n", n=nid)
    monkeypatch.setitem(messages.CATALOGOS["es"], clave,
                        messages._p("Aprobación {process_type} pendiente, nivel {level_order}."))
    item = mundo.get(f"/notifications/{nid}", "ua", mundo.company_a).json()
    assert item["message"]["text"] == "Aprobación PRUEBA pendiente, nivel 1."
    assert filas(mundo.factory, "SELECT message_key, message_params::text FROM notifications WHERE id = :n",
                 n=nid) == antes


def test_una_clave_retirada_del_catalogo_se_lee_como_error_controlado(mundo, monkeypatch):
    nid = publicar(mundo.factory, service.crear_notificacion,
                   efecto(mundo.company_a, destinatarios=frozenset({uid(mundo.factory, "ua")})))
    monkeypatch.delitem(messages.CATALOGOS["es"], "approval.step_opened.notification")
    r = mundo.get(f"/notifications/{nid}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert (r.json()["message"]["text"], r.json()["message"]["render_error"]) == (None, "MESSAGE_KEY_UNKNOWN")


# ------------------------------------------------------------ volumen
def test_flujo_m_mas_de_cien_notificaciones_se_recorren_por_paginas(mundo):
    cat = f"vol.{marca()}"
    ua = uid(mundo.factory, "ua")
    with mundo.factory() as db:
        for _ in range(105):
            service.crear_notificacion(db, efecto(mundo.company_a, category=cat, destinatarios=frozenset({ua})))
        db.commit()
    paginas = [mundo.get(f"/notifications?category={cat}&page={p}&page_size=50", "ua", mundo.company_a).json()
               for p in (1, 2, 3)]
    assert [len(p["items"]) for p in paginas] == [50, 50, 5]
    assert {p["total"] for p in paginas} == {105}
    assert len({i["id"] for p in paginas for i in p["items"]}) == 105
    assert mundo.get(f"/notifications?category={cat}&page=3&page_size=101", "ua",
                     mundo.company_a).status_code == 422


def test_la_lista_no_hace_una_consulta_por_fila(mundo):
    cat = f"n1.{marca()}"
    ua = uid(mundo.factory, "ua")
    with mundo.factory() as db:
        for _ in range(30):
            service.crear_notificacion(db, efecto(mundo.company_a, category=cat, destinatarios=frozenset({ua})))
        db.commit()
    motor = mundo.factory.kw["bind"]

    def consultas(page_size: int) -> int:
        n = [0]

        def contar(*_a, **_k):
            n[0] += 1

        with mundo.factory() as db:
            user, ctx = contexto(db, "ua", mundo.company_a)
            service.contadores(db, ctx=ctx, user=user)      # calienta las relaciones del usuario
            event.listen(motor, "before_cursor_execute", contar)
            try:
                service.listar_notificaciones(db, ctx=ctx, user=user, state="all", category=cat, severity=None,
                                              source_type=None, created_from=None, created_to=None,
                                              page=1, page_size=page_size)
            finally:
                event.remove(motor, "before_cursor_execute", contar)
        return n[0]

    assert consultas(5) == consultas(30) <= 4


# ------------------------------------------------------------ reglas y contadores
def test_las_reglas_se_validan_y_exigen_su_permiso(mundo):
    base = {"code": f"R{marca()}", "source": "APPROVAL", "event_type": "approval.step_opened",
            "effect": "NOTIFICATION"}
    assert mundo.post("/notifications/rules", "ua", mundo.company_a, base).status_code == 201
    repetida = mundo.post("/notifications/rules", "ua", mundo.company_a, base)
    assert repetida.status_code == 409 and codigo(repetida) == "NOTIFICATION_RULE_CODE_TAKEN"
    evento = mundo.post("/notifications/rules", "ua", mundo.company_a,
                        {**base, "code": f"R{marca()}", "event_type": "approval.requested"})
    assert evento.status_code == 422 and evento.json()["details"]["reason"] == "EVENT_NOT_SUPPORTED"
    tiempos = mundo.post("/notifications/rules", "ua", mundo.company_a,
                         {**base, "code": f"R{marca()}", "reminder_offset_minutes": 30})
    assert tiempos.status_code == 422 and tiempos.json()["details"]["reason"] == "TIMING_ONLY_FOR_TASKS"
    limitado, _ = usuario_limitado(mundo, [mundo.company_a], sin={"notificaciones:configure"})
    assert mundo.post("/notifications/rules", limitado, mundo.company_a,
                      {**base, "code": f"R{marca()}"}).status_code == 403


def test_flujo_k_la_049_puede_leer_los_cuatro_contadores(mundo):
    datos = _contadores(mundo, "ua", mundo.company_a)
    assert set(datos) == {"unread_notifications", "open_tasks", "overdue_tasks", "active_alerts"}
    assert all(isinstance(v, int) and v >= 0 for v in datos.values())
