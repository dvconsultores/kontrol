from datetime import timedelta
from uuid import uuid4

from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio
from tests.org06_ayudantes import (
    D,
    accion,
    accion_vinculo,
    activa,
    acto_eficaz,
    consultar,
    crear_funcionario,
    crear_vinculo,
    cuenta,
    cuerpo,
    cuerpo_vinculo,
    nuevo_cargo,
    post_vinculo,
    titular_activo,
    vinculo_activo,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def test_D01_crear_y_activar_vinculo(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d01cuenta")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D01 Funcionario")
    datos = cuerpo_vinculo(user_id, funcionario["id"])
    creado = crear_vinculo(mundo, datos)
    assert creado["status"] == "BORRADOR"
    assert creado["situacion"] == "BORRADOR"
    assert creado["cuenta"]["usuario"] == "d01cuenta"
    assert creado["funcionario"]["documento"] != funcionario.get("documento_completo", "")
    activado = accion_vinculo(mundo, creado, "activar")
    assert activado.status_code == 200
    activado = activado.json()
    assert activado["status"] == "ACTIVO"
    assert activado["situacion"] == "VIGENTE"
    assert activado["version"] > creado["version"]
    assert len(activado["historia"]) >= 2
    assert activado["historia"][-1]["tipo"] == "ACTIVADO"


def test_D02_consultar_vinculo_detalle(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d02cuenta")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D02 Funcionario")
    creado = crear_vinculo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    activado = accion_vinculo(mundo, creado, "activar").json()
    response = consultar(mundo, f"/vinculos/{activado['id']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["contexto"]["vinculo"]["codigo"] == activado["codigo"]
    assert payload["contexto"]["funcionario"]["id"] == funcionario["id"]


def test_D03_historico_vinculo(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d03cuenta")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D03 Funcionario")
    datos = cuerpo_vinculo(user_id, funcionario["id"], desde=D(1, 10).isoformat(), hasta=None)
    creado = crear_vinculo(mundo, datos)
    activado = accion_vinculo(mundo, creado, "activar").json()
    cerrado = accion_vinculo(
        mundo,
        activado,
        "cerrar",
        cuerpo_accion={"fecha": D(2, 1).isoformat(), "motivo": "Cambio de cuenta institucional."},
    ).json()
    vigente = consultar(mundo, f"/vinculos/{cerrado['id']}", params={"fecha": D(1, 20).isoformat()}).json()
    assert vigente["situacion"] == "VIGENTE"
    cerrada = consultar(mundo, f"/vinculos/{cerrado['id']}", params={"fecha": D(3, 1).isoformat()}).json()
    assert cerrada["situacion"] == "CERRADA"
    assert cerrada["id"] == cerrado["id"]


def test_D04_cerrar_vinculo(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d04cuenta")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D04 Funcionario")
    activado = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    response = accion_vinculo(
        mundo,
        activado,
        "cerrar",
        cuerpo_accion={"fecha": D(2, 1).isoformat(), "motivo": "Cambio de cuenta institucional."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "CERRADO"
    assert payload["fin_efectivo"] == D(2, 1).isoformat()


def test_D05_nuevo_vinculo_posterior_sin_solape(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d05cuenta1")
    user_id2 = cuenta(mundo, "d05cuenta2")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D05 Funcionario")
    activado = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"], desde=D(1, 10).isoformat()))
    accion_vinculo(
        mundo,
        activado,
        "cerrar",
        cuerpo_accion={"fecha": D(2, 1).isoformat(), "motivo": "Cambio de cuenta institucional."},
    )
    segundo = vinculo_activo(mundo, cuerpo_vinculo(user_id2, funcionario["id"], desde=D(2, 2).isoformat()))
    assert segundo["situacion"] == "VIGENTE"
    tercera_cuenta = cuenta(mundo, "d05cuentatres")
    tercero = crear_vinculo(mundo, cuerpo_vinculo(tercera_cuenta, funcionario["id"], desde=D(2, 1).isoformat()))
    response = accion_vinculo(mundo, tercero, "activar")
    assert response.status_code == 409
    assert response.json()["code"] == "GOV_IDENTITY_OVERLAP"


def test_D06_no_acceso_otro_ente(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d06cuenta")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D06 Funcionario")
    activado = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    response = consultar(mundo, f"/vinculos/{activado['id']}", usuario="ub", empresa=mundo.company_b)
    assert response.status_code == 404
    assert response.json()["code"] == "GOV_IDENTITY_LINK_NOT_FOUND"


def test_D07_usuario_inexistente(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D07 Funcionario")
    response = post_vinculo(mundo, cuerpo_vinculo(str(uuid4()), funcionario["id"]))
    assert response.status_code == 404
    assert response.json()["code"] == "GOV_IDENTITY_USER_NOT_FOUND"


def test_D08_funcionario_inexistente(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d08cuenta")
    response = post_vinculo(mundo, cuerpo_vinculo(user_id, str(uuid4())))
    assert response.status_code == 404
    assert response.json()["code"] == "GOV_OFFICIAL_NOT_FOUND"


def test_D09_funcionario_otro_ente(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d09cuenta")
    funcionario_b = crear_funcionario(mundo, usuario="ub", empresa=mundo.company_b, nombre="D09 Funcionario B")
    response = post_vinculo(mundo, cuerpo_vinculo(user_id, funcionario_b["id"]))
    assert response.status_code == 404
    assert response.json()["code"] == "GOV_OFFICIAL_NOT_FOUND"


def test_D10_vigencia_futura_contexto_sin_vinculo(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d10cuenta")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D10 Funcionario")
    desde = hoy_de_negocio() + timedelta(days=30)
    activado = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"], desde=desde.isoformat()))
    response = consultar(mundo, f"/vinculos/{activado['id']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["situacion"] == "FUTURA"
    assert payload["contexto"]["vinculo"] is None
    assert payload["contexto"]["motivo_sin_autoridad"] == "SIN_VINCULO"


def test_D11_vigencia_expirada(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d11cuenta")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D11 Funcionario")
    activado = vinculo_activo(
        mundo, cuerpo_vinculo(user_id, funcionario["id"], desde=D(1, 10).isoformat(), hasta=D(1, 20).isoformat())
    )
    response = consultar(mundo, f"/vinculos/{activado['id']}")
    assert response.status_code == 200
    assert response.json()["situacion"] == "VENCIDA"


def test_D12_cuenta_deshabilitada(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d12cuenta")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D12 Funcionario")
    creado = crear_vinculo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    with mundo.factory() as session:
        user = session.get(User, user_id)
        user.status = "INACTIVE"
        session.commit()
    response = accion_vinculo(mundo, creado, "activar")
    assert response.status_code == 422
    assert response.json()["code"] == "GOV_IDENTITY_USER_INACTIVE"

    user_id2 = cuenta(mundo, "d12cuenta2")
    funcionario2 = crear_funcionario(mundo, usuario="ua", nombre="D12 Funcionario 2")
    activado = vinculo_activo(mundo, cuerpo_vinculo(user_id2, funcionario2["id"]))
    with mundo.factory() as session:
        user = session.get(User, user_id2)
        user.status = "INACTIVE"
        session.commit()
    response = consultar(mundo, f"/vinculos/{activado['id']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["contexto"]["tiene_autoridad"] is False
    assert payload["contexto"]["motivo_sin_autoridad"] == "CUENTA_INACTIVA"
    assert payload["id"] == activado["id"]
    assert len(payload["historia"]) >= 2


def test_D13_funcionario_sin_ocupacion(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d13cuenta")
    funcionario = crear_funcionario(mundo, usuario="ua", nombre="D13 Funcionario")
    activado = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    response = consultar(mundo, f"/vinculos/{activado['id']}")
    assert response.status_code == 200
    payload = response.json()
    assert payload["contexto"]["ocupaciones"] == []
    assert payload["contexto"]["tiene_autoridad"] is False
    assert payload["contexto"]["motivo_sin_autoridad"] == "SIN_OCUPACION"


def test_D14_ocupacion_finalizada(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d14cuenta")
    asignacion, cargo = titular_activo(mundo, ocupacion)
    funcionario = asignacion["funcionario"]
    activado = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    consultar(mundo, f"/vinculos/{activado['id']}").json()
    accion(
        mundo,
        asignacion,
        "finalizar",
        cuerpo={"fecha": D(3, 1).isoformat(), "motivo": "Fin de la designación de prueba."},
        usuario="uab",
    )
    response = consultar(mundo, f"/vinculos/{activado['id']}", params={"fecha": D(3, 2).isoformat()})
    assert response.status_code == 200
    payload = response.json()
    assert payload["contexto"]["ocupaciones"] == []
    assert payload["contexto"]["motivo_sin_autoridad"] == "SIN_OCUPACION"
    response = consultar(mundo, f"/vinculos/{activado['id']}", params={"fecha": D(2, 15).isoformat()})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["contexto"]["ocupaciones"]) == 1


def test_D15_nueva_ocupacion_actualiza_contexto(mundo, gobierno, ocupacion):
    user_id = cuenta(mundo, "d15cuenta")
    asignacion, cargo_anterior = titular_activo(mundo, ocupacion)
    funcionario = asignacion["funcionario"]
    activado = vinculo_activo(mundo, cuerpo_vinculo(user_id, funcionario["id"]))
    accion(
        mundo,
        asignacion,
        "finalizar",
        cuerpo={"fecha": D(3, 1).isoformat(), "motivo": "Fin de la designación de prueba."},
        usuario="uab",
    )
    nuevo_cargo_id = nuevo_cargo(mundo, ocupacion, unidad="unidad_hija")
    acto = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    datos_nueva = cuerpo(funcionario, nuevo_cargo_id, acto, figura="TITULAR", desde=D(3, 2).isoformat())
    activa(mundo, datos_nueva, usuario="ua", activador="uab")
    response = consultar(mundo, f"/vinculos/{activado['id']}", params={"fecha": D(3, 10).isoformat()})
    assert response.status_code == 200
    payload = response.json()
    assert payload["contexto"]["ocupaciones"][0]["cargo_id"] == nuevo_cargo_id
    assert any(unidad["id"] == ocupacion["unidad_hija"] for unidad in payload["contexto"]["unidades"])
    response = consultar(mundo, f"/vinculos/{activado['id']}", params={"fecha": D(2, 15).isoformat()})
    assert response.status_code == 200
    payload = response.json()
    assert payload["contexto"]["ocupaciones"][0]["cargo_id"] == cargo_anterior
