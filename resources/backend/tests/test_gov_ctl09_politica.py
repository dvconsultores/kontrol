# ruff: noqa: E402, F811, F401, I001
"""CTL-09-DELIVERY-ACT-POLICY: política de actas, regla aplicada y defecto P0 (A17 solo donde se declara)."""

import os
import uuid

import pytest
from sqlalchemy import select, text

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Requiere PostgreSQL",
)
pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

from app.modules.government.models import GovernmentEntity, GovernmentHandoverAct, GovernmentPosition
from tests.org04_ayudantes import D, activa, crear_funcionario, nuevo_cargo, titular_activo
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_org04_politica_procesos import _suplencia

P = "/gobierno/actas-entrega/politicas"
A = "/gobierno/actas-entrega"
A17 = {"A17_1", "A17_2", "A17_3", "A17_4", "A17_5"}


# --- Ayudantes ---------------------------------------------------------------------------------------------------


def _ente(mundo, **campos):
    with mundo.factory() as db:
        ente = db.execute(select(GovernmentEntity).where(GovernmentEntity.company_id == mundo.company_a)).scalar_one()
        anterior = {k: getattr(ente, k) for k in campos}
        for k, v in campos.items():
            setattr(ente, k, v)
        db.commit()
    return anterior


def _cerrar_vigentes(mundo):
    resp = mundo.client.get(f"/api/v1{P}", headers=mundo.como("ua", mundo.company_a), params={"estado": "VIGENTE"})
    assert resp.status_code == 200, resp.text
    for item in resp.json()["items"]:
        resp = mundo.client.post(
            f"/api/v1{P}/{item['id']}/cerrar",
            headers={**mundo.como("uab", mundo.company_a), "If-Match": str(item["version"])},
            json={"motivo": "Cierre de prueba del ciclo"},
        )
        assert resp.status_code == 200, resp.text


def _activar(mundo, detalle):
    resp = mundo.client.post(
        f"/api/v1{P}/{detalle['id']}/activar",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(detalle["version"])},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _politica(mundo, activar=True, **cambios):
    cuerpo = {
        "codigo": f"PAE-{uuid.uuid4().hex[:6].upper()}",
        "nombre": "Política de actas de prueba",
        "fundamento": "Resolución interna de prueba sobre actas de entrega",
        "vigente_desde": D(1, 1).isoformat(),
    }
    cuerpo.update(cambios)
    resp = _post(mundo, P, "ua", mundo.company_a, cuerpo)
    assert resp.status_code == 201, resp.text
    detalle = resp.json()
    return _activar(mundo, detalle) if activar else detalle


def _suplencia_maxima(mundo, ocupacion):
    """Suplencia activa de la máxima autoridad (ámbito ENTE desde siempre), vigente del 1 al 20 de febrero."""
    return activa(mundo, _suplencia(mundo, ocupacion, autorizacion_especial="Autorización del Concejo Municipal de prueba"))


def _cuerpo_acta(mundo, asignacion, *, corte=None, **cambios):
    receptor = crear_funcionario(mundo)
    cuerpo = {
        "assignment_id": asignacion["id"],
        "receptor_official_id": receptor["id"],
        "receptor_assignment_id": None,
        "modalidad": "ENTREGA",
        "testigos": [],
        "auditor_official_id": None,
        "motivo": "Motivo de prueba para el acta de entrega",
        "fundamento": "Fundamento de prueba para el acta de entrega",
        "lugar": "Sede del ente",
        "fecha_corte": (corte or D(2, 10)).isoformat(),
    }
    cuerpo.update(cambios)
    return cuerpo


def _acta(mundo, asignacion, **cambios):
    resp = mundo.post(f"{A}/actas", "ua", mundo.company_a, _cuerpo_acta(mundo, asignacion, **cambios))
    assert resp.status_code == 201, resp.text
    return resp.json()


def _codigos(acta):
    return {a["codigo"] for a in acta["anexos"]}


def _resolver_pendientes(mundo, acta):
    for codigo in acta["anexos_pendientes"]:
        resp = mundo.put_json(
            f"{A}/actas/{acta['id']}/anexos/{codigo}",
            "ua",
            mundo.company_a,
            {"constancia": "Constancia art. 19: la información no existe en el ente"},
        )
        assert resp.status_code == 200, resp.text
        acta = resp.json()
    return acta


def _suscribir(mundo, acta, fecha=None):
    return mundo.post(
        f"{A}/actas/{acta['id']}/suscribir",
        "ua",
        mundo.company_a,
        {"fecha_suscripcion": (fecha or D(2, 10)).isoformat()},
    )


def _cargo(mundo, cargo_id):
    with mundo.factory() as db:
        return db.execute(select(GovernmentPosition).where(GovernmentPosition.id == cargo_id)).scalar_one()


# --- Defecto P0 ----------------------------------------------------------------------------------------------------


def test_p0_instituto_municipal_no_recibe_a17(mundo, gobierno, ocupacion):
    """Antes: todo ente MUNICIPAL con ámbito ENTE recibía A17. Ahora solo si la política lo declara."""
    _cerrar_vigentes(mundo)
    anterior = _ente(mundo, nivel_territorial="MUNICIPAL", forma_organizativa="INSTITUTO_PUBLICO")
    try:
        acta = _acta(mundo, _suplencia_maxima(mundo, ocupacion))
    finally:
        _ente(mundo, **anterior)
    assert acta["ambito"] == "ENTE"
    assert not (_codigos(acta) & A17), _codigos(acta)
    assert {"A11_1", "A11_2", "A11_3", "A11_4", "A11_5", "A11_6"} <= _codigos(acta)
    assert acta["regla"]["origen"] == "LEGAL"
    assert any("art. 17" in aviso for aviso in acta["regla"]["avisos"])
    assert not any(s["codigo"] == "N34_ART17" for s in acta["regla"]["supuestos"])


def test_a17_se_exige_cuando_la_politica_lo_declara_para_la_entidad(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    _politica(mundo, vinculos=[{"supuesto": "N34_ART17", "alcance": "ENTE", "unit_id": None}])
    acta = _acta(mundo, _suplencia_maxima(mundo, ocupacion))
    assert A17 <= _codigos(acta)
    a17 = [a for a in acta["anexos"] if a["codigo"].startswith("A17_")]
    assert all(a["obligatorio"] and a["supuesto"] == "N34_ART17" and "art. 17" in a["fuente"] for a in a17)
    assert acta["regla"]["avisos"] == []

    resp = _suscribir(mundo, acta)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_HANDOVER_ANNEXES_PENDING"
    assert "A17_1" in resp.json()["details"]["anexos"]

    acta = _resolver_pendientes(mundo, acta)
    assert acta["anexos_pendientes"] == []
    resp = _suscribir(mundo, acta)
    assert resp.status_code == 200, resp.text
    _cerrar_vigentes(mundo)


def test_a17_en_la_unidad_de_hacienda_y_no_en_otra_unidad(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    asig_hacienda, cargo_hacienda = titular_activo(mundo, ocupacion, nuevo_cargo(mundo, ocupacion, unidad="unidad_raiz"))
    unidad_hacienda = _cargo(mundo, cargo_hacienda).unit_id
    _politica(mundo, vinculos=[{"supuesto": "N34_ART17", "alcance": "UNIDAD", "unit_id": unidad_hacienda}])

    acta = _acta(mundo, asig_hacienda)
    assert acta["ambito"] == "UNIDAD"
    assert A17 <= _codigos(acta)

    otra, cargo_otro = titular_activo(mundo, ocupacion, nuevo_cargo(mundo, ocupacion, unidad="unidad_hija"))
    assert _cargo(mundo, cargo_otro).unit_id != unidad_hacienda
    assert not (_codigos(_acta(mundo, otra)) & A17)
    _cerrar_vigentes(mundo)


def test_cargo_de_maxima_autoridad_declarado_hace_acta_de_la_entidad(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    asig, cargo_id = titular_activo(mundo, ocupacion)
    codigo = _cargo(mundo, cargo_id).code
    _politica(
        mundo,
        cargo_maxima_autoridad_codigo=codigo,
        vinculos=[{"supuesto": "N34_ART17", "alcance": "ENTE", "unit_id": None}],
    )
    acta = _acta(mundo, asig)
    assert acta["ambito"] == "ENTE"
    assert codigo in acta["regla"]["ambito_motivo"]
    assert A17 <= _codigos(acta)
    _cerrar_vigentes(mundo)


# --- Piso legal, versiones y aislamiento de la política ------------------------------------------------------------


def test_piso_legal_no_se_rebaja(mundo, gobierno, ocupacion):
    base = {
        "codigo": f"PAE-{uuid.uuid4().hex[:6].upper()}",
        "nombre": "Política inválida",
        "vigente_desde": D(1, 1).isoformat(),
    }
    casos = [
        ({"vinculos": [{"supuesto": "N34_ART16", "alcance": "ENTE", "unit_id": None}]}, "vinculos.0.supuesto"),
        ({"vinculos": [{"supuesto": "N34_ART11", "alcance": "ENTE", "unit_id": None}]}, "vinculos.0.supuesto"),
        ({"plazos": [{"hito": "REMISION_UAI", "valor": 6, "unidad": "DIAS_CONTINUOS"}]}, "plazos.0.valor"),
        ({"requisitos": [{"codigo": "A17_9", "titulo": "Anexo inventado", "evidencia": "DOCUMENTO"}]}, "requisitos.0.codigo"),
        ({"numeracion_patron": "AE-{ANIO}"}, "numeracion_patron"),
    ]
    for cambios, campo in casos:
        resp = _post(mundo, P, "ua", mundo.company_a, {**base, **cambios})
        assert resp.status_code == 422, (cambios, resp.text)
        assert resp.json()["code"] == "GOV_HANDOVER_POLICY_INVALID"
        assert campo in resp.json()["field_errors"], (campo, resp.json())

    opciones = mundo.get(f"{P}/opciones", "ua", mundo.company_a).json()
    declarable = {s["codigo"]: s["declarable"] for s in opciones["supuestos"]}
    assert declarable["N34_ART17"] is True
    assert declarable["N34_ART16"] is False
    assert declarable["N34_ART15"] is False


def test_activar_sustituye_y_nueva_version_copia(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    sin_fundamento = _politica(mundo, activar=False, fundamento=None)
    resp = mundo.client.post(
        f"/api/v1{P}/{sin_fundamento['id']}/activar",
        headers={**mundo.como("uab", mundo.company_a), "If-Match": str(sin_fundamento["version"])},
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["details"]["motivos"]

    v1 = _politica(mundo, requisitos=[{"codigo": "P1", "titulo": "Declaración jurada", "evidencia": "DECLARACION"}])
    resp = _post(mundo, f"{P}/{v1['id']}/nueva-version", "ua", mundo.company_a, {}, version=v1["version"])
    assert resp.status_code == 201, resp.text
    v2 = resp.json()
    assert v2["numero_version"] == 2 and v2["estado"] == "BORRADOR"
    assert [r["codigo"] for r in v2["requisitos"]] == ["P1"]

    v2 = _activar(mundo, v2)
    anterior = mundo.get(f"{P}/{v1['id']}", "ua", mundo.company_a).json()
    assert anterior["estado"] == "CERRADA"
    assert "Sustituida" in anterior["motivo_cierre"]
    assert [h["evento"] for h in anterior["historia"]][-1] == "SUSTITUIDA"
    assert [h["evento"] for h in v2["historia"]] == ["NUEVA_VERSION", "ACTIVADA"]
    _cerrar_vigentes(mundo)


def test_politica_aislamiento_entre_empresas(mundo, gobierno, ocupacion):
    detalle = _politica(mundo, activar=False)
    assert mundo.get(f"{P}/{detalle['id']}", "ub", mundo.company_b).status_code == 404
    resp = mundo.client.put(
        f"/api/v1{P}/{detalle['id']}",
        headers={**mundo.como("ub", mundo.company_b), "If-Match": str(detalle["version"])},
        json={"codigo": detalle["codigo"], "nombre": "Intento ajeno", "vigente_desde": D(1, 1).isoformat()},
    )
    assert resp.status_code == 404, resp.text
    listado = mundo.get(P, "ub", mundo.company_b).json()
    assert all(item["id"] != detalle["id"] for item in listado["items"])


# --- Congelación, legado, testigos, plazos y numeración ------------------------------------------------------------


def test_version_congelada_en_el_acta(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    v1 = _politica(mundo, requisitos=[{"codigo": "P1", "titulo": "Declaración jurada", "evidencia": "DECLARACION"}])
    acta_a = _acta(mundo, _suplencia_maxima(mundo, ocupacion))
    assert acta_a["regla"]["regla_version"] == f"{v1['codigo']} v1"
    acta_a = _resolver_pendientes(mundo, acta_a)
    assert _suscribir(mundo, acta_a).status_code == 200

    resp = _post(mundo, f"{P}/{v1['id']}/nueva-version", "ua", mundo.company_a, {}, version=v1["version"])
    v2 = resp.json()
    entrada = {
        "codigo": v2["codigo"],
        "nombre": v2["nombre"],
        "fundamento": v2["fundamento"],
        "vigente_desde": v2["vigente_desde"],
        "requisitos": [
            {"codigo": "P1", "titulo": "Declaración jurada", "evidencia": "DECLARACION"},
            {"codigo": "P2", "titulo": "Certificación de inventario", "evidencia": "CERTIFICACION"},
        ],
    }
    resp = mundo.client.put(
        f"/api/v1{P}/{v2['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(v2["version"])},
        json=entrada,
    )
    assert resp.status_code == 200, resp.text
    _activar(mundo, resp.json())

    ficha_a = mundo.get(f"{A}/actas/{acta_a['id']}", "ua", mundo.company_a).json()
    assert ficha_a["regla_congelada"] is True
    assert ficha_a["regla"]["regla_version"] == f"{v1['codigo']} v1"
    assert "P2" not in _codigos(ficha_a)

    acta_b = _acta(mundo, _suplencia_maxima(mundo, ocupacion))
    assert acta_b["regla"]["regla_version"] == f"{v1['codigo']} v2"
    assert {"P1", "P2"} <= _codigos(acta_b)
    _cerrar_vigentes(mundo)


def test_legado_se_lee_con_su_regla_historica(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    acta = _acta(mundo, _suplencia_maxima(mundo, ocupacion))
    with mundo.factory() as db:
        db.execute(
            text("UPDATE gov_handover_acts SET regla = NULL, policy_id = NULL, policy_version = NULL WHERE id = :id"),
            {"id": acta["id"]},
        )
        db.commit()
    ficha = mundo.get(f"{A}/actas/{acta['id']}", "ua", mundo.company_a).json()
    assert ficha["regla"]["origen"] == "HISTORICA"
    assert {a["codigo"] for a in ficha["regla"]["anexos"]} == _codigos(acta)


def test_testigos_exigidos_por_la_politica_en_la_entrega(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    _politica(mundo, testigos_en_entrega=1)
    asig = _suplencia_maxima(mundo, ocupacion)
    resp = mundo.post(f"{A}/actas", "ua", mundo.company_a, _cuerpo_acta(mundo, asig))
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_HANDOVER_WITNESSES_REQUIRED"
    acta = _acta(mundo, asig, testigos=[{"nombre": "Testigo Uno", "documento": "V-1234567"}])
    assert acta["regla"]["testigos"]["entrega"]["minimo"] == 1
    _cerrar_vigentes(mundo)


def test_numeracion_y_plazo_interno(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    _politica(
        mundo,
        numeracion_patron="ACT-{ANIO}-{NUMERO:3}",
        plazos=[
            {"hito": "REMISION_UAI", "valor": 2, "unidad": "DIAS_CONTINUOS"},
            {"hito": "ELABORACION", "valor": 1, "unidad": "DIAS_CONTINUOS"},
        ],
    )
    vista = mundo.get(f"{P}/numeracion/vista-previa?patron=ACT-{{ANIO}}-{{NUMERO:3}}&anio=2030", "ua", mundo.company_a).json()
    assert vista["ejemplos"][0] == "ACT-2030-001"

    acta = _acta(mundo, _suplencia_maxima(mundo, ocupacion))
    assert acta["codigo"].startswith(f"ACT-{D(2, 10).year}-")
    acta = _resolver_pendientes(mundo, acta)
    assert _suscribir(mundo, acta, fecha=D(2, 12)).status_code == 200
    resp = mundo.post(f"{A}/actas/{acta['id']}/remision", "ua", mundo.company_a, {"fecha": D(2, 13).isoformat()})
    assert resp.status_code == 200, resp.text
    ficha = mundo.get(f"{A}/actas/{acta['id']}", "ua", mundo.company_a).json()
    estados = {(p["hito"], p["origen"]): p["estado"] for p in ficha["plazos"]}
    assert estados[("REMISION_UAI", "POLITICA")] == "CUMPLIDO"
    assert estados[("ELABORACION", "POLITICA")] == "CUMPLIDO_FUERA_DE_PLAZO"
    assert estados[("REMISION_UAI", "LEGAL")] == "REGISTRADO"
    assert estados[("OBSERVACIONES", "LEGAL")] == "SIN_CALENDARIO_HABIL"
    _cerrar_vigentes(mundo)


def test_declaracion_resuelve_solo_anexos_de_texto(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    _politica(mundo, requisitos=[{"codigo": "P1", "titulo": "Declaración jurada", "evidencia": "DECLARACION"}])
    acta = _acta(mundo, _suplencia_maxima(mundo, ocupacion))
    assert "P1" in acta["anexos_pendientes"]
    resp = mundo.put_json(f"{A}/actas/{acta['id']}/anexos/P1", "ua", mundo.company_a, {"declaracion": "Declaro bajo fe de juramento"})
    assert resp.status_code == 200, resp.text
    assert "P1" not in resp.json()["anexos_pendientes"]
    resp = mundo.put_json(f"{A}/actas/{acta['id']}/anexos/A11_3", "ua", mundo.company_a, {"declaracion": "Texto que no corresponde"})
    assert resp.status_code == 422, resp.text
    _cerrar_vigentes(mundo)


# --- Responsabilidad (ORG-04) y aislamiento de la regla --------------------------------------------------------------


def test_responsabilidad_con_la_autoridad_de_org04(mundo, gobierno, ocupacion):
    _cerrar_vigentes(mundo)
    asig = _suplencia_maxima(mundo, ocupacion)
    resp = mundo.post(f"{A}/actas", "ua", mundo.company_a, _cuerpo_acta(mundo, asig, corte=D(2, 25)))
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_HANDOVER_ASSIGNMENT_INVALID"

    acta = _acta(mundo, asig)
    responsabilidad = acta["responsabilidad"]
    assert responsabilidad["saliente"]["assignment_id"] == asig["id"]
    assert responsabilidad["saliente"]["situacion_al_corte"] == "VIGENTE"
    assert responsabilidad["receptor"]["relacion"] == "DESIGNADO"
    assert responsabilidad["fecha_efectiva"] == D(2, 10).isoformat()


def test_regla_aislada_por_empresa(mundo, gobierno, ocupacion):
    asig = _suplencia_maxima(mundo, ocupacion)
    resp = mundo.get(f"{A}/regla?assignment_id={asig['id']}&fecha_corte={D(2, 10).isoformat()}", "ub", mundo.company_b)
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "GOV_HANDOVER_ASSIGNMENT_INVALID"
    resp = mundo.get(f"{A}/regla?assignment_id={asig['id']}&fecha_corte={D(2, 10).isoformat()}", "ua", mundo.company_a)
    assert resp.status_code == 200, resp.text
    assert resp.json()["ambito"] == "ENTE"
