from datetime import timedelta
from uuid import uuid4

from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_cnt01_contratos import C, _cargo_firmante
from tests.test_gov_cnt02_modificaciones import (
    FIN,
    _delete_m,
    _formalizar_m,
    _nueva,
    _patch_m,
)
from tests.test_gov_cnt04_supervisor import (
    S,
    _acto_designante,
    _designar,
    _formalizado,
    _supervisor,
)
from tests.test_gov_cnt07_terminacion import _escenario, _formalizar, _listo
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc10_garantias import HOY, _doc

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)


def _prorroga(mundo, ocupacion, exp, cid, nueva_fin, vigente_desde=HOY, formalizar=True):
    """Crea una modificación PRORROGA y opcionalmente la formaliza."""
    r = _nueva(mundo, cid, "PRORROGA")
    assert r.status_code == 201, r.text
    doc_id, _ = _doc(mundo, exp, f"doc-pr-{uuid4().hex[:6]}")
    cuerpo = {
        "fecha_instrumento": HOY.isoformat(),
        "vigente_desde": vigente_desde.isoformat(),
        "motivo": "Solicitud justificada del contratista",
        "referencia_instrumento": "INSTR-PR",
        "documento_id": doc_id,
        "nueva_fecha_fin": nueva_fin.isoformat(),
    }
    r = _patch_m(mundo, cid, r.json()["id"], cuerpo, r.json()["version"])
    assert r.status_code == 200, r.text
    b = r.json()
    if formalizar:
        r = _formalizar_m(mundo, cid, b["id"], _cargo_firmante(mundo, ocupacion, "SIN_LIMITE"), b["version"])
        assert r.status_code == 200, r.text
        b = r.json()
    return b


def _supervision(mundo, cid):
    """Obtiene el bloque contrato del endpoint de supervisión."""
    r = mundo.get(f"{C}/{cid}{S}", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    return r.json()["contrato"]


@ONLY_PG
def test_plazo_original_admite_hasta_el_fin_y_rechaza_despues(mundo, gobierno, ocupacion):
    """Sin prórroga, la designación admite el fin original y rechaza después."""
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=1))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_DATE_INVALID", r.text

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN)
    assert r.status_code == 201, r.text

    sup = _supervision(mundo, cid)
    assert sup["fecha_fin_original"] == sup["fecha_fin_vigente"] == FIN.isoformat(), sup
    assert sup["fuente_plazo"] == "CNT01_ORIGINAL", sup
    assert sup["modificacion_plazo"] is None, sup


@ONLY_PG
def test_prorroga_formalizada_admite_despues_del_fin_original(mundo, gobierno, ocupacion):
    """Una prórroga formalizada amplía el plazo efectivo de supervisión."""
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    _prorroga(mundo, ocupacion, f["exp"], cid, FIN + timedelta(days=60))

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=61))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_DATE_INVALID", r.text

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=10))
    assert r.status_code == 201, r.text

    sup = _supervision(mundo, cid)
    assert sup["fecha_fin_original"] == FIN.isoformat(), sup
    assert sup["fecha_fin_vigente"] == (FIN + timedelta(days=60)).isoformat(), sup
    assert sup["fuente_plazo"] == "CNT02_MODIFICACION", sup
    assert sup["modificacion_plazo"], sup


@ONLY_PG
def test_prorroga_en_borrador_no_amplia_el_plazo(mundo, gobierno, ocupacion):
    """Un borrador de prórroga no modifica el plazo efectivo."""
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    _prorroga(mundo, ocupacion, f["exp"], cid, FIN + timedelta(days=60), formalizar=False)

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=10))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_DATE_INVALID", r.text

    sup = _supervision(mundo, cid)
    assert sup["fecha_fin_vigente"] == FIN.isoformat(), sup
    assert sup["fuente_plazo"] == "CNT01_ORIGINAL", sup


@ONLY_PG
def test_prorroga_descartada_no_amplia_el_plazo(mundo, gobierno, ocupacion):
    """Una prórroga descartada no amplía el plazo efectivo."""
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    b = _prorroga(mundo, ocupacion, f["exp"], cid, FIN + timedelta(days=60), formalizar=False)
    r = _delete_m(mundo, cid, b["id"], b["version"])
    assert r.status_code in (200, 204), r.text

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=10))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_DATE_INVALID", r.text


@ONLY_PG
def test_varias_prorrogas_usan_la_version_vigente(mundo, gobierno, ocupacion):
    """Varias prórrogas formalizadas: rige la última versión vigente."""
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    _prorroga(mundo, ocupacion, f["exp"], cid, FIN + timedelta(days=30))
    codigo_p1 = _supervision(mundo, cid)["modificacion_plazo"]

    _prorroga(mundo, ocupacion, f["exp"], cid, FIN + timedelta(days=90))

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=91))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_DATE_INVALID", r.text

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=60))
    assert r.status_code == 201, r.text

    sup = _supervision(mundo, cid)
    assert sup["fecha_fin_vigente"] == (FIN + timedelta(days=90)).isoformat(), sup
    assert sup["modificacion_plazo"] != codigo_p1, sup


@ONLY_PG
def test_corte_historico_usa_el_plazo_de_la_fecha_desde(mundo, gobierno, ocupacion):
    """El corte histórico usa la prórroga vigente en la fecha desde."""
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    _prorroga(mundo, ocupacion, f["exp"], cid, FIN + timedelta(days=30))
    codigo_p1 = _supervision(mundo, cid)["modificacion_plazo"]

    _prorroga(mundo, ocupacion, f["exp"], cid, FIN + timedelta(days=90), vigente_desde=FIN + timedelta(days=50))

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=40))
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_CONTRACT_SUPERVISOR_DATE_INVALID", r.text

    r = _designar(mundo, cid, _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=60))
    assert r.status_code == 201, r.text

    sup = _supervision(mundo, cid)
    assert sup["fecha_fin_vigente"] == (FIN + timedelta(days=30)).isoformat(), sup
    assert sup["modificacion_plazo"] == codigo_p1, sup


@ONLY_PG
def test_terminacion_eficaz_bloquea_aunque_haya_prorroga(mundo, gobierno, ocupacion):
    """La terminación eficaz bloquea la designación pese a existir prórroga."""
    esc = _escenario(mundo, ocupacion)
    _prorroga(mundo, ocupacion, esc["exp"], esc["cid"], FIN + timedelta(days=60))
    b = _listo(mundo, esc)
    r = _formalizar(mundo, esc["cid"], b["version"])
    assert r.status_code == 200, r.text

    r = _designar(mundo, esc["cid"], _supervisor(mundo, ocupacion), _acto_designante(mundo, ocupacion), FIN + timedelta(days=10))
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_CONTRACT_TERMINATED", r.text


@ONLY_PG
def test_otra_empresa_recibe_404(mundo, gobierno, ocupacion):
    """Otra empresa no puede leer ni designar supervisión del contrato."""
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    _prorroga(mundo, ocupacion, f["exp"], cid, FIN + timedelta(days=60))

    r = mundo.get(f"{C}/{cid}{S}", "ua", mundo.company_b)
    assert r.status_code == 404, r.text

    sup = _supervisor(mundo, ocupacion)
    cuerpo = {
        "funcionario_id": sup["funcionario_id"],
        "asignacion_id": sup["asignacion_id"],
        "acto_id": _acto_designante(mundo, ocupacion),
        "desde": (FIN + timedelta(days=10)).isoformat(),
        "motivo": None,
        "sustituye_id": None,
    }
    r = _post(mundo, f"{C}/{cid}{S}/designaciones", "ua", mundo.company_b, cuerpo)
    assert r.status_code == 404, r.text


@ONLY_PG
def test_cnt04_y_cnt08_coinciden_en_el_fin_vigente(mundo, gobierno, ocupacion):
    """CNT-04 y CNT-08 exponen el mismo fin vigente tras una prórroga."""
    f = _formalizado(mundo, ocupacion)
    cid = f["contrato"]["id"]
    _prorroga(mundo, ocupacion, f["exp"], cid, FIN + timedelta(days=60))

    fin_supervision = _supervision(mundo, cid)["fecha_fin_vigente"]
    r_exp = mundo.get(f"{C}/{cid}/expediente", "ua", mundo.company_a)
    assert r_exp.status_code == 200, r_exp.text
    fin_expediente = r_exp.json()["resumen"]["fecha_fin_vigente"]

    assert fin_supervision == fin_expediente == (FIN + timedelta(days=60)).isoformat()
