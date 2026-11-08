from sqlalchemy import select

from app.modules.identity_access.models import User
from app.shared.audit import record_audit
from tests.org06_ayudantes import crear_funcionario, cuerpo_vinculo, titular_activo, vinculo_activo
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")
B = "/api/v1/gobierno/bitacora"


def _auditor(mundo, nombre):
    cuenta_con_permisos(mundo, nombre, [("gobierno_auditoria", "view")])
    return mundo.como(nombre, mundo.company_a)


def _actor_vinculado(mundo, ocupacion, nombre):
    asig, cargo = titular_activo(mundo, ocupacion)
    oficial = asig["funcionario"]["id"]
    user_id = cuenta_con_permisos(
        mundo, nombre, [("gobierno_ocupacion", "view"), ("gobierno_ocupacion", "manage")]
    )
    vinculo_activo(mundo, cuerpo_vinculo(user_id, oficial))
    crear_funcionario(mundo, usuario=nombre)
    return oficial, cargo


def test_f_consulta_evento_con_contexto(mundo, gobierno, ocupacion):
    oficial, cargo = _actor_vinculado(mundo, ocupacion, "ctl02_f")
    h = _auditor(mundo, "ctl02_f_aud")
    r = mundo.client.get(B, headers=h, params={"funcionario_id": oficial, "accion": "GOV_OFFICIAL_CREATED"})
    assert r.status_code == 200
    data = r.json()
    assert data["items"]
    item = data["items"][0]
    assert item["usuario"] == "ctl02_f"
    assert item["resultado"] == "EXITO"
    assert item["estado_contexto"] == "CON_IDENTIDAD"
    assert item["funcionario"]
    assert item["cargos"]
    assert item["unidades"]

    d = mundo.client.get(f"{B}/{item['id']}", headers=h).json()
    assert d["ip"]
    assert d["sesion_id"]
    assert d["request_id"]
    assert d["contexto"]["funcionario"]["id"] == oficial
    assert d["contexto"]["ocupaciones"][0]["cargo_id"] == cargo

    unidad = d["contexto"]["ocupaciones"][0]["unidad_id"]
    r = mundo.client.get(B, headers=h, params={"unidad_id": unidad})
    assert r.status_code == 200
    ids = [evento["id"] for evento in r.json()["items"]]
    assert item["id"] in ids

    r = mundo.client.get(B, headers=h, params={"request_id": d["request_id"]})
    assert r.status_code == 200
    ids = [evento["id"] for evento in r.json()["items"]]
    assert item["id"] in ids


def test_g_otro_ente_no_ve_el_evento(mundo, gobierno, ocupacion):
    oficial, _ = _actor_vinculado(mundo, ocupacion, "ctl02_g")
    h_a = _auditor(mundo, "ctl02_g_aud")
    r = mundo.client.get(B, headers=h_a, params={"funcionario_id": oficial, "accion": "GOV_OFFICIAL_CREATED"})
    assert r.status_code == 200
    item = r.json()["items"][0]

    _crear_usuario_con_permisos(
        mundo, "ctl02_g_b", [("gobierno_auditoria", "view")], mundo.company_b
    )
    h_b = mundo.como("ctl02_g_b", mundo.company_b)
    r = mundo.client.get(f"{B}/{item['id']}", headers=h_b)
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_BITACORA_EVENT_NOT_FOUND"

    r = mundo.client.get(B, headers=h_b, params={"funcionario_id": oficial})
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_h_autenticacion_solo_de_cuentas_vinculadas(mundo, gobierno, ocupacion):
    oficial, _ = _actor_vinculado(mundo, ocupacion, "ctl02_h")
    ajena = cuenta_con_permisos(mundo, "ctl02_h_ajena", [("gobierno_auditoria", "view")])
    with mundo.factory() as db:
        user = db.execute(select(User).where(User.username == "ctl02_h")).scalar_one()
        for user_id in (str(user.id), ajena):
            record_audit(
                db,
                action="LOGIN_SUCCESS",
                entity_type="User",
                entity_id=user_id,
                tenant_id=str(user.tenant_id),
                user_id=user_id,
                ip="10.0.0.1",
            )
        db.commit()

    h = _auditor(mundo, "ctl02_h_aud")
    r = mundo.client.get(B, headers=h, params={"accion": "LOGIN_SUCCESS", "usuario": "ctl02_h"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    item = data["items"][0]
    assert item["estado_contexto"] == "NO_APLICA"
    assert item["funcionario"] is None
    assert item["proceso"] == "AUTENTICACION"
    assert item["resultado"] == "EXITO"

    r = mundo.client.get(B, headers=h, params={"accion": "LOGIN_SUCCESS", "usuario": "ctl02_h_ajena"})
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_i_sin_capacidad_403(mundo, gobierno, ocupacion):
    cuenta_con_permisos(mundo, "ctl02_i", [("gobierno_ocupacion", "view")])
    h = mundo.como("ctl02_i", mundo.company_a)
    r = mundo.client.get(B, headers=h)
    assert r.status_code == 403


def test_j_lista_con_evento_sin_vinculo(mundo, gobierno, ocupacion):
    cuenta_con_permisos(mundo, "ctl02_j", [("gobierno_ocupacion", "view"), ("gobierno_ocupacion", "manage")])
    crear_funcionario(mundo, usuario="ctl02_j")
    h = _auditor(mundo, "ctl02_j_aud")
    r = mundo.client.get(B, headers=h, params={"usuario": "ctl02_j", "accion": "GOV_OFFICIAL_CREATED"})
    assert r.status_code == 200, r.text
    item = r.json()["items"][0]
    assert item["estado_contexto"] == "SIN_VINCULO"
    assert item["funcionario"] is None
    assert item["cargos"] == []
    d = mundo.client.get(f"{B}/{item['id']}", headers=h)
    assert d.status_code == 200, d.text
    assert d.json()["contexto"]["funcionario"] is None
