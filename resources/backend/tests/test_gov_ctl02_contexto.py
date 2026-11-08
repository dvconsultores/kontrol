from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.shared.clock import hoy_de_negocio
from tests.org06_ayudantes import (
    accion_vinculo,
    crear_funcionario,
    cuenta,
    cuerpo_vinculo,
    nuevo_cargo,
    titular_activo,
    vinculo_activo,
)
from tests.org06_guarda import (
    acto_borrador,
    cuenta_con_permisos,
    emisor_vinculado,
    emitir,
    exigir_identidad,
)

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)


def _eventos(mundo, accion, user_id):
    with mundo.factory() as db:
        return list(
            db.scalars(
                select(AuditEvent)
                .where(AuditEvent.action == accion, AuditEvent.user_id == user_id)
                .order_by(AuditEvent.event_time)
            ).all()
        )


def test_a_mutacion_guarda_el_contexto_institucional(mundo, gobierno, ocupacion):
    asig, cargo = titular_activo(mundo, ocupacion)
    oficial = asig["funcionario"]["id"]
    nombre = "ctl02_a"
    user_id = cuenta_con_permisos(
        mundo,
        nombre,
        [("gobierno_ocupacion", "view"), ("gobierno_ocupacion", "manage")],
    )
    vinculo_activo(mundo, cuerpo_vinculo(user_id, oficial))
    crear_funcionario(mundo, usuario=nombre)

    e = _eventos(mundo, "GOV_OFFICIAL_CREATED", user_id)[-1]
    assert e.user_id == user_id
    assert e.session_id is not None
    assert e.ip is not None
    assert e.request_id is not None

    c = e.institutional_context
    assert c["estado"] == "CON_IDENTIDAD"
    assert c["funcionario"]["id"] == oficial
    assert "documento" not in c["funcionario"]
    assert c["ente"]["id"]
    assert c["ocupaciones"][0]["cargo_id"] == cargo
    assert c["ocupaciones"][0]["unidad_id"]
    assert c["fecha"] == hoy_de_negocio().isoformat()
    assert c["tiene_autoridad"] is True


def test_b_rechazo_conserva_evento_y_contexto(mundo, gobierno, ocupacion):
    cargo = nuevo_cargo(mundo, ocupacion)
    oficial = crear_funcionario(mundo)["id"]
    nombre = "ctl02_b"
    user_id = emisor_vinculado(mundo, nombre, oficial)
    exigir_identidad(mundo)
    acto = acto_borrador(mundo, cargo)
    r = emitir(mundo, acto, nombre)
    exigir_identidad(mundo, False)

    assert r.status_code == 403

    e = _eventos(mundo, "GOV_IDENTITY_GUARD_BLOCKED", user_id)[-1]
    c = e.institutional_context
    assert c["funcionario"]["id"] == oficial
    assert c["ocupaciones"] == []
    assert c["tiene_autoridad"] is False
    assert e.ip is not None

    emitidos = _eventos(mundo, "GOV_ACT_ISSUED", user_id)
    assert emitidos == []


def test_c_sin_identidad_no_se_fabrica(mundo, gobierno, ocupacion):
    nombre = "ctl02_c"
    user_id = cuenta_con_permisos(
        mundo,
        nombre,
        [("gobierno_ocupacion", "view"), ("gobierno_ocupacion", "manage")],
    )
    crear_funcionario(mundo, usuario=nombre)

    c = _eventos(mundo, "GOV_OFFICIAL_CREATED", user_id)[-1].institutional_context
    assert c["estado"] == "SIN_VINCULO"
    assert c["funcionario"] is None
    assert c["vinculo"] is None
    assert c["ocupaciones"] == []
    assert c["tiene_autoridad"] is False


def test_d_la_instantanea_no_cambia_con_el_tiempo(mundo, gobierno, ocupacion):
    asig, _ = titular_activo(mundo, ocupacion)
    oficial = asig["funcionario"]["id"]
    nombre = "ctl02_d"
    user_id = cuenta_con_permisos(
        mundo,
        nombre,
        [("gobierno_ocupacion", "view"), ("gobierno_ocupacion", "manage")],
    )
    vinculo = vinculo_activo(mundo, cuerpo_vinculo(user_id, oficial))
    crear_funcionario(mundo, usuario=nombre)

    evento_creado = _eventos(mundo, "GOV_OFFICIAL_CREATED", user_id)[-1]
    antes = evento_creado.institutional_context

    r = accion_vinculo(
        mundo,
        vinculo,
        "cerrar",
        {"fecha": hoy_de_negocio().isoformat(), "motivo": "Cierre de prueba del vínculo."},
    )
    assert r.status_code == 200, r.text

    with mundo.factory() as db:
        despues = db.get(AuditEvent, evento_creado.id).institutional_context

    assert despues == antes
    assert despues["estado"] == "CON_IDENTIDAD"


def test_e_otros_modulos_sin_contexto(mundo, gobierno, ocupacion):
    cuenta(mundo, "ctl02_e")

    with mundo.factory() as db:
        eventos = list(
            db.scalars(
                select(AuditEvent).where(
                    AuditEvent.action.not_like("GOV\\_%", escape="\\")
                )
            ).all()
        )

    assert len(eventos) > 0
    assert all(evento.institutional_context is None for evento in eventos)
