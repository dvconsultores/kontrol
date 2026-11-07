from tests.ctl10_ayudantes import C, anadir_control, crear_politica, politica_vigente, retirar
from tests.test_gov_tre01_cuentas import eventos
from tests.tre02_ayudantes import delete_con_version, patch_con_version

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_ed01_patch_nombre_y_fundamento(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    r = patch_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}",
        {"nombre": "Nuevo nombre", "fundamento": "Fundamento actualizado de la política de cierre."},
        politica["version"],
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["nombre"] == "Nuevo nombre"
    assert cuerpo["fundamento"] == "Fundamento actualizado de la política de cierre."
    assert cuerpo["version"] == politica["version"] + 1
    assert any(h["evento"] == "ACTUALIZADA" for h in cuerpo["historia"])
    lista = eventos(mundo, "GOV_CLOSURE_POLICY_UPDATED", politica["id"])
    assert len(lista) == 1
    assert lista[0].entity_id == politica["id"]


def test_ed02_sin_cabecera_428_version_vieja_409_stale(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    r = mundo.client.patch(
        f"/api/v1{C}/politicas/{politica['id']}",
        headers=mundo.como("ua", mundo.company_a),
        json={"nombre": "Sin cabecera"},
    )
    assert r.status_code == 428, r.text
    r = patch_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}",
        {"nombre": "Versión vieja"},
        politica["version"] - 1,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_STALE"


def test_ed03_delete_control(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", "ALTO")
    control_id = politica["controles"][0]["id"]
    r = delete_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}/controles/{control_id}",
        politica["version"],
    )
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert all(c["id"] != control_id for c in cuerpo["controles"])
    assert any(h["evento"] == "CONTROL_RETIRADO" for h in cuerpo["historia"])
    lista = eventos(mundo, "GOV_CLOSURE_POLICY_CONTROL_REMOVED", politica["id"])
    assert len(lista) == 1
    assert lista[0].entity_id == politica["id"]


def test_ed04_vigente_y_retirada_no_se_editan(mundo, gobierno):
    politica = politica_vigente(mundo, "ORG02_CERRAR_ESTRUCTURA", "HALLAZGOS_ABIERTOS", "ALTO")
    r = patch_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}",
        {"nombre": "Vigente no se edita"},
        politica["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID_STATE"

    r = delete_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}/controles/{politica['controles'][0]['id']}",
        politica["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID_STATE"

    r = retirar(mundo, politica)
    assert r.status_code == 200, r.text
    retirada = r.json()
    r = patch_con_version(
        mundo,
        f"{C}/politicas/{retirada['id']}",
        {"nombre": "Retirada no se edita"},
        retirada["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID_STATE"


def test_ed05_campo_extra_estado_422(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    r = patch_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}",
        {"nombre": "Con extra", "estado": "VIGENTE"},
        politica["version"],
    )
    assert r.status_code == 422, r.text


def test_ed06_control_de_otra_politica_404(mundo, gobierno):
    primera = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    segunda = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    segunda = anadir_control(mundo, segunda, "HALLAZGOS_ABIERTOS", "ALTO")
    control_id = segunda["controles"][0]["id"]
    r = delete_con_version(
        mundo,
        f"{C}/politicas/{primera['id']}/controles/{control_id}",
        primera["version"],
    )
    assert r.status_code == 404, r.text


def test_ed07_vigencia_invertida_422(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    response = patch_con_version(
        mundo,
        f"{C}/politicas/{politica['id']}",
        {"vigente_desde": "2030-06-01", "vigente_hasta": "2030-01-01"},
        politica["version"],
    )
    assert response.status_code == 422
    assert response.json()["code"] == "GOV_CLOSURE_POLICY_INVALID"
