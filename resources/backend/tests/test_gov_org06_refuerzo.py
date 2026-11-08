from tests.org06_ayudantes import (
    D,
    I,
    accion,
    accion_vinculo,
    acto_eficaz,
    crear_funcionario,
    crear_vinculo,
    cuenta,
    cuerpo_vinculo,
    post_vinculo,
    titular_activo,
    vinculo_activo,
)
from tests.org06_guarda import contexto_de

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def test_r1_escritura_desde_otro_ente(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_r1")
    oficial = crear_funcionario(mundo)
    vinculo = crear_vinculo(mundo, cuerpo_vinculo(user_id, oficial["id"]))

    respuesta = accion_vinculo(
        mundo, vinculo, "activar", usuario="ub", empresa=mundo.company_b
    )

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "GOV_IDENTITY_LINK_NOT_FOUND"

    detalle = mundo.client.get(
        f"/api/v1{I}/vinculos/{vinculo['id']}",
        headers=mundo.como("ua", mundo.company_a),
    ).json()
    assert detalle["status"] == "BORRADOR"


def test_r2_cuenta_sin_acceso_al_ente(mundo, gobierno, ocupacion):
    user_b = cuenta(mundo, "org06_r2", empresa=mundo.company_b)
    oficial = crear_funcionario(mundo)

    respuesta = post_vinculo(mundo, cuerpo_vinculo(user_b, oficial["id"]))

    assert respuesta.status_code == 404
    assert respuesta.json()["code"] == "GOV_IDENTITY_USER_NOT_FOUND"


def test_r3_quien_registra_no_activa(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "org06_r3")
    oficial = crear_funcionario(mundo)
    vinculo = crear_vinculo(mundo, cuerpo_vinculo(user_id, oficial["id"]))

    respuesta = accion_vinculo(mundo, vinculo, "activar", usuario="ua")

    assert respuesta.status_code == 403
    assert respuesta.json()["code"] == "GOV_IDENTITY_SELF_ACTIVATION"


def test_r4_ocupacion_revocada_fuera_del_contexto_actual(mundo, gobierno, ocupacion):
    detalle, _cargo = titular_activo(mundo, ocupacion)
    user_id = cuenta(mundo, "org06_r4")
    vinculo = vinculo_activo(
        mundo, cuerpo_vinculo(user_id, detalle["funcionario"]["id"])
    )

    respuesta_revocacion = accion(
        mundo,
        detalle,
        "revocar",
        cuerpo={
            "acto_id": acto_eficaz(mundo, ocupacion["cargo_emisor"]),
            "fecha": D(3, 1).isoformat(),
            "motivo": "Revocación de prueba",
        },
    )
    assert respuesta_revocacion.status_code == 200

    contexto_actual = contexto_de(mundo, vinculo)
    assert contexto_actual["ocupaciones"] == []
    assert contexto_actual["motivo_sin_autoridad"] == "SIN_OCUPACION"

    contexto_pasado = contexto_de(mundo, vinculo, fecha=D(2, 15))
    assert len(contexto_pasado["ocupaciones"]) == 1
    assert contexto_pasado["ocupaciones"][0]["ejerce"] is True


def test_r5_la_politica_de_identidad_enlaza_a_una_pantalla_real():
    from pathlib import Path

    backend = Path(__file__).resolve().parents[1]
    resources = Path(__file__).resolve().parents[2]

    fuente_servicio = (backend / "app" / "modules" / "government" / "service_auditoria.py").read_text(encoding="utf-8")
    assert "/gobierno/identidad/politica" not in fuente_servicio
    assert 'ruta="/gobierno/identidad/categorias"' in fuente_servicio

    fuente_router = (resources / "frontend" / "src" / "app" / "router.tsx").read_text(encoding="utf-8")
    assert 'path: "gobierno/identidad/categorias"' in fuente_router
