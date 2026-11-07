from tests.ctl10_ayudantes import (
    MOTIVO,
    C,
    activar,
    anadir_control,
    crear_politica,
    politicas_limpias,  # noqa: F401
    retirar,
)
from tests.test_gov_ctl06_hallazgos import _crear_usuario_con_permisos, _post
from tests.test_gov_tre01_cuentas import eventos
from tests.tre02_ayudantes import cerrar_regla, regla_sod_vigente

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos")


def test_rt01_retirar_vigente_con_motivo(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", "ALTO")
    politica = activar(mundo, politica).json()
    r = retirar(mundo, politica)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["estado"] == "RETIRADA"
    assert cuerpo["retirada_por"] is not None
    assert cuerpo["retirada_en"] is not None
    assert cuerpo["motivo_retiro"] == MOTIVO
    assert cuerpo["efectiva_hoy"] is False
    assert any(h["evento"] == "RETIRADA" for h in cuerpo["historia"])
    lista = eventos(mundo, "GOV_CLOSURE_POLICY_RETIRED", politica["id"])
    assert len(lista) == 1
    assert lista[0].entity_id == politica["id"]


def test_rt02_retirar_borrador(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    r = retirar(mundo, politica)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "RETIRADA"


def test_rt03_motivo_9_y_501_caracteres_422(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    for motivo in ("123456789", f"{MOTIVO}{'x' * 501}"):
        r = retirar(mundo, politica, motivo=motivo)
        assert r.status_code == 422, r.text


def test_rt04_retirada_no_vuelve(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    r = retirar(mundo, politica)
    assert r.status_code == 200, r.text
    retirada = r.json()
    r = retirar(mundo, retirada)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID_STATE"
    r = activar(mundo, retirada)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_INVALID_STATE"


def test_rt05_sin_if_match_428_version_vieja_409_stale(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    r = _post(
        mundo,
        f"{C}/politicas/{politica['id']}/retirar",
        "ua",
        mundo.company_a,
        {"motivo": MOTIVO},
    )
    assert r.status_code == 428, r.text
    r = retirar(mundo, politica, version=politica["version"] - 1)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CLOSURE_POLICY_STALE"


def test_rt06_usuario_solo_manage_403(mundo, gobierno):
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    _crear_usuario_con_permisos(
        mundo,
        "rt_solo_manage",
        [("gobierno_cierre", "view"), ("gobierno_cierre", "manage")],
        mundo.company_a,
    )
    r = retirar(mundo, politica, usuario="rt_solo_manage")
    assert r.status_code == 403, r.text


def test_rt07_tras_retirar_puede_activarse_otra_politica(mundo, gobierno):
    primera = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    r = retirar(mundo, primera)
    assert r.status_code == 200, r.text
    segunda = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    segunda = anadir_control(mundo, segunda, "HALLAZGOS_ABIERTOS", "ALTO")
    r = activar(mundo, segunda)
    assert r.status_code == 200, r.text


def test_rt08_guarda_sod_en_retirar(mundo, gobierno):
    regla = regla_sod_vigente(mundo, "CTL10_ACTIVAR", "CTL10_RETIRAR", "CTL10_ACTIVAR_RETIRAR", proceso="CTL-10")
    politica = crear_politica(mundo, "ORG02_CERRAR_ESTRUCTURA")
    politica = anadir_control(mundo, politica, "HALLAZGOS_ABIERTOS", "ALTO")
    politica = activar(mundo, politica).json()
    r = retirar(mundo, politica)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_SOD_CONFLICT"
    r = mundo.client.get(
        f"/api/v1{C}/politicas/{politica['id']}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "VIGENTE"
    cerrar_regla(mundo, regla)
