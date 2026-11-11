from datetime import timedelta
from uuid import uuid4

import pytest

from app.shared.clock import hoy_de_negocio
from tests.org06_guarda import cuenta_con_permisos
from tests.proc08_ayudantes import (
    acto_decision,
    cargo_contrataciones,
    evaluacion_concluida,
    recomendar,
)
from tests.test_gov_ctl01_reglas import cerrar_regla, eventos, regla_vigente
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc08_paquete import _doc_real
from tests.test_gov_proc03_expedientes import E

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

G = "/gobierno/contrataciones"
HOY = hoy_de_negocio()


def _exp(mundo, exp):
    return mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()


def _doc(mundo, exp, nombre):
    doc = _doc_real(mundo, mundo.company_a, None, f"garantia {nombre}".encode(), nombre)
    r = mundo.post(
        f"/documentos/{doc}/vinculos",
        "ua",
        mundo.company_a,
        {"resource_type": "GovernmentProcurementFile", "resource_id": exp["id"]},
    )
    assert r.status_code == 200, r.text
    return doc, _exp(mundo, exp)


def _estado(mundo, exp):
    return mundo.get(f"{G}/expedientes/{exp['id']}/garantias", "ua", mundo.company_a)


def _post_g(mundo, exp, sufijo, cuerpo, version=None, usuario="ua", empresa=None):
    return _post(
        mundo,
        f"{G}/expedientes/{exp['id']}/garantias{sufijo}",
        usuario,
        empresa or mundo.company_a,
        cuerpo,
        version=_estado(mundo, exp).json()["version"] if version is None else version,
    )


def _emisor(mundo, nombre, rif, usuario="ua", empresa=None):
    r = _post(
        mundo,
        f"{G}/garantias/emisores",
        usuario,
        empresa or mundo.company_a,
        {"tipo": "ASEGURADORA", "nombre": nombre, "rif": rif},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _adjudicado(mundo, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[
            {"posicion": 1, "offer_id": ofertas[0]["id"]},
            {"posicion": 2, "offer_id": ofertas[1]["id"]},
        ],
    )
    exp = _exp(mundo, exp)
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)
    r = _post(
        mundo,
        f"{E}/{exp['id']}/decision/decisiones",
        "ua",
        mundo.company_a,
        {
            "resultado": "ADJUDICADA",
            "recomendacion_id": estado["recomendacion_vigente"]["id"],
            "acto_id": acto["id"],
            "oferta_id": ofertas[0]["id"],
            "motivacion": "Adjudicación de prueba",
        },
        version=exp["version"],
    )
    assert r.status_code == 201, r.text
    return _exp(mundo, exp), ofertas, acto


def _gar(estado, ref):
    return next(g for g in estado["garantias"] if g["referencia"] == ref)


def test_mantenimiento_monto_fijo_renovacion_y_liberacion(mundo, gobierno, ocupacion):
    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    emisor = _emisor(mundo, "Aseguradora Uno", f"J-{uuid4().hex[:8]}")
    d1, exp = _doc(mundo, exp, "req1")
    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "MANT-FIJO-1",
            "monto_fijo": "1000.00",
            "moneda": "VES",
            "vigencia_minima_hasta": (HOY + timedelta(days=60)).isoformat(),
            "fundamento": "Pliego, cláusula 12",
            "documento_id": d1,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    assert estado["requisitos"][0]["referencia"] == "REQ-01"
    assert len(estado["requisitos"][0]["sujetos"]) == 3
    assert all(not s["cubierto"] for s in estado["requisitos"][0]["sujetos"])

    d2, exp = _doc(mundo, exp, "gar1")
    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": estado["requisitos"][0]["id"],
            "oferta_id": ofertas[1]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "FZ-0001",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d2,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    g1 = _gar(estado, "GAR-01")
    assert g1["estado"] == "REGISTRADA"
    assert g1["vigencia"] == "VIGENTE"
    assert g1["dias_restantes"] == 30
    assert g1["suficiencia"] == "INSUFICIENTE"
    criterios = {c["criterio"]: c for c in g1["criterios"]}
    assert criterios["Vigencia mínima"]["resultado"] == "NO_CUMPLE"
    assert criterios["Monto"]["resultado"] == "CUMPLE"
    assert estado["resumen"]["registradas"] == 1
    assert estado["resumen"]["insuficientes"] == 1
    assert estado["resumen"]["sin_garantia"] == 2

    d3, exp = _doc(mundo, exp, "ren1")
    r = _post_g(
        mundo,
        exp,
        f"/{g1['id']}/renovar",
        {
            "vigente_hasta": (HOY + timedelta(days=90)).isoformat(),
            "documento_id": d3,
            "motivo": "Prórroga de la oferta (LCP art. 71)",
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    g1 = _gar(estado, "GAR-01")
    g2 = _gar(estado, "GAR-02")
    assert g1["estado"] == "RENOVADA"
    assert g1["vigente_hasta"] == (HOY + timedelta(days=30)).isoformat()
    assert g1["sucesor"] == "GAR-02"
    assert g2["estado"] == "REGISTRADA"
    assert g2["antecesor"] == "GAR-01"
    assert g2["suficiencia"] == "SUFICIENTE"
    acciones = [h["accion"] for h in g2["historial"]]
    assert acciones == ["REGISTRO", "RENOVACION"]

    r = _post_g(
        mundo,
        exp,
        f"/{g2['id']}/liberar",
        {"acto_id": acto["id"], "motivo": "Oferente no adjudicado"},
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    g2 = _gar(estado, "GAR-02")
    assert g2["estado"] == "LIBERADA"
    assert g2["acciones"] == []
    ultimo = g2["historial"][-1]
    assert ultimo["accion"] == "LIBERACION"
    assert ultimo["precondicion"] == "VERIFICADA"
    assert ultimo["precondicion_detalle"].startswith("DEC-01")
    assert estado["resumen"]["liberadas"] == 1

    crono = mundo.get(f"{E}/{exp['id']}/cronologia", "ua", mundo.company_a).json()
    assert sum(1 for item in crono["items"] if item.get("clase") == "GARANTIA") >= 4
    for accion in (
        "GOV_GUARANTEE_REQUIREMENT_REGISTERED",
        "GOV_GUARANTEE_REGISTERED",
        "GOV_GUARANTEE_RENEWED",
        "GOV_GUARANTEE_RELEASED",
    ):
        assert eventos(mundo, accion, exp["id"]), accion


def test_fiel_cumplimiento_no_evaluable_sustitucion_y_ejecucion(mundo, gobierno, ocupacion):
    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    emisor1 = _emisor(mundo, "Aseguradora Dos", f"J-{uuid4().hex[:8]}")
    d1, exp = _doc(mundo, exp, "req2")
    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "FIEL-1",
            "porcentaje": "20",
            "fundamento": "Pliego, cláusula 20",
            "documento_id": d1,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    requisito = estado["requisitos"][0]

    d2, exp = _doc(mundo, exp, "gar2")
    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[1]["id"],
            "emisor_id": emisor1["id"],
            "referencia_emisor": "FC-0001",
            "monto": "5000.00",
            "moneda": "USD",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=365)).isoformat(),
            "documento_id": d2,
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["field_errors"]["oferta_id"]

    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor1["id"],
            "referencia_emisor": "FC-0001",
            "monto": "5000.00",
            "moneda": "USD",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=365)).isoformat(),
            "documento_id": d2,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    g1 = _gar(estado, "GAR-01")
    assert g1["suficiencia"] == "NO_EVALUABLE"
    criterios = {c["criterio"]: c for c in g1["criterios"]}
    assert criterios["Monto"]["resultado"] == "NO_EVALUABLE"
    assert criterios["Monto"]["detalle"].startswith("BASE_MONETARIA_NO_DISPONIBLE")
    assert estado["resumen"]["no_evaluables"] == 1
    assert "SUSTITUIR" in g1["acciones"]

    emisor2 = _emisor(mundo, "Aseguradora Tres", f"J-{uuid4().hex[:8]}")
    d3, exp = _doc(mundo, exp, "sus1")
    r = _post_g(
        mundo,
        exp,
        f"/{g1['id']}/sustituir",
        {
            "emisor_id": emisor2["id"],
            "referencia_emisor": "FC-0002",
            "monto": "6000.00",
            "moneda": "USD",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=365)).isoformat(),
            "documento_id": d3,
            "motivo": "Sustitución por insuficiencia",
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    g1 = _gar(estado, "GAR-01")
    g2 = _gar(estado, "GAR-02")
    assert g1["estado"] == "SUSTITUIDA"
    assert g2["estado"] == "REGISTRADA"

    r = _post_g(
        mundo,
        exp,
        f"/{g2['id']}/ejecutar",
        {"acto_id": acto["id"], "motivo": "Incumplimiento", "monto_ejecutado": "7000.00"},
    )
    assert r.status_code == 422, r.text
    assert r.json()["field_errors"]["monto_ejecutado"]

    r = _post_g(
        mundo,
        exp,
        f"/{g2['id']}/ejecutar",
        {"acto_id": acto["id"], "motivo": "Incumplimiento", "monto_ejecutado": "1500.00"},
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    g2 = _gar(estado, "GAR-02")
    assert g2["estado"] == "EJECUTADA"
    ultimo = g2["historial"][-1]
    assert ultimo["accion"] == "EJECUCION"
    assert ultimo["monto"] == "1500.00"
    assert ultimo["moneda"] == "USD"

    r = _post_g(
        mundo,
        exp,
        f"/{g2['id']}/ejecutar",
        {"acto_id": acto["id"], "motivo": "Otra", "monto_ejecutado": "100.00"},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_GUARANTEE_NOT_ACTIVE"

    r = _post_g(
        mundo,
        exp,
        f"/{g2['id']}/renovar",
        {"vigente_hasta": (HOY + timedelta(days=400)).isoformat(), "documento_id": d3, "motivo": "x"},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_GUARANTEE_NOT_ACTIVE"

    assert eventos(mundo, "GOV_GUARANTEE_SUBSTITUTED", exp["id"])
    assert eventos(mundo, "GOV_GUARANTEE_EXECUTED", exp["id"])


def test_negativas(mundo, gobierno, ocupacion):
    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    emisor = _emisor(mundo, "Aseguradora Cuatro", f"J-{uuid4().hex[:8]}")
    d1, exp = _doc(mundo, exp, "req3")
    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "MANT-FIJO-1",
            "monto_fijo": "1000.00",
            "moneda": "VES",
            "fundamento": "Pliego",
            "documento_id": d1,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    requisito = estado["requisitos"][0]

    r = mundo.get(f"{G}/expedientes/{exp['id']}/garantias", "ub", mundo.company_b)
    assert r.status_code == 404, r.text

    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-1",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d1,
        },
        usuario="ub",
        empresa=mundo.company_b,
    )
    assert r.status_code == 404, r.text

    nombre = f"sinpermiso-{uuid4().hex[:6]}"
    cuenta_con_permisos(
        mundo,
        nombre,
        [("gobierno_garantias", "view"), ("gobierno_expedientes", "view")],
    )
    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "MANT-FIJO-1",
            "monto_fijo": "1000.00",
            "moneda": "VES",
            "fundamento": "Pliego",
            "documento_id": d1,
        },
        usuario=nombre,
    )
    assert r.status_code == 403, r.text

    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {"regla_codigo": "NO-EXISTE", "fundamento": "x", "documento_id": d1},
    )
    assert r.status_code == 422, r.text
    assert r.json()["field_errors"]["regla_codigo"]

    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "MANT-PRESUPUESTO-1",
            "porcentaje": "3",
            "fundamento": "x",
            "documento_id": d1,
        },
    )
    assert r.status_code == 422, r.text
    assert "entre 1,50 % y 2,50 %" in r.json()["field_errors"]["porcentaje"][0]

    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "MANT-FIJO-1",
            "monto_fijo": "1000.00",
            "moneda": "USD",
            "fundamento": "x",
            "documento_id": d1,
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["field_errors"]["moneda"]

    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {"regla_codigo": "OTRA-FIJO-1", "fundamento": "x", "documento_id": d1, "monto_fijo": "100.00", "moneda": "VES"},
    )
    assert r.status_code == 422, r.text
    assert r.json()["field_errors"]["nombre"]

    emisor_otro = _emisor(mundo, "Aseguradora Otro", f"J-{uuid4().hex[:8]}", usuario="ub", empresa=mundo.company_b)
    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor_otro["id"],
            "referencia_emisor": "X-2",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d1,
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["field_errors"]["emisor_id"]

    doc_otro = _doc_real(mundo, mundo.company_b, None, b"otro", "otro")
    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-3",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": doc_otro,
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["field_errors"]["documento_id"]

    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-4",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY - timedelta(days=1)).isoformat(),
            "documento_id": d1,
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["field_errors"]["vigente_hasta"]

    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-5",
            "monto": "0",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d1,
        },
    )
    assert r.status_code == 422, r.text
    assert r.json()["field_errors"]["monto"]

    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-6",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d1,
        },
        version=1,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_STALE"

    d2, exp = _doc(mundo, exp, "gar3")
    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-7",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d2,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    g1 = _gar(estado, "GAR-01")

    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-8",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d2,
        },
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_GUARANTEE_ACTIVE_EXISTS"

    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[1]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-7",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d2,
        },
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_GUARANTEE_DUPLICATE"

    r = _post_g(
        mundo,
        exp,
        f"/{g1['id']}/sustituir",
        {
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-9",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d2,
            "motivo": "x",
        },
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_GUARANTEE_SUBSTITUTION_NOT_ALLOWED"

    r = _post(
        mundo,
        f"{G}/garantias/emisores",
        "ua",
        mundo.company_a,
        {"tipo": "ASEGURADORA", "nombre": "Repetida", "rif": emisor["rif"]},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_GUARANTEE_ISSUER_DUPLICATE"

    r = _post_g(
        mundo,
        exp,
        f"/{g1['id']}/liberar",
        {"acto_id": "no-existe", "motivo": "x"},
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_GUARANTEE_INVALID_ACT"

    r = _post_g(
        mundo,
        exp,
        f"/{g1['id']}/liberar",
        {"acto_id": acto["id"], "motivo": "Liberación"},
    )
    assert r.status_code == 201, r.text
    r = _post_g(
        mundo,
        exp,
        f"/{g1['id']}/liberar",
        {"acto_id": acto["id"], "motivo": "Otra"},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_GUARANTEE_NOT_ACTIVE"

    exp2, _, ofertas2 = evaluacion_concluida(mundo, ocupacion)
    d3, exp2 = _doc(mundo, exp2, "req4")
    r = _post_g(
        mundo,
        exp2,
        "/requisitos",
        {
            "regla_codigo": "FIEL-1",
            "porcentaje": "20",
            "fundamento": "Pliego",
            "documento_id": d3,
        },
    )
    assert r.status_code == 201, r.text
    estado2 = r.json()
    requisito2 = estado2["requisitos"][0]
    assert requisito2["pendiente_adjudicacion"] is True
    assert requisito2["sujetos"] == []

    r = _post_g(
        mundo,
        exp2,
        "",
        {
            "requisito_id": requisito2["id"],
            "oferta_id": ofertas2[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "X-10",
            "monto": "1000.00",
            "moneda": "USD",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d3,
        },
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_GUARANTEE_AWARD_REQUIRED"


def test_concurrencia_doble_ejecucion(mundo, gobierno, ocupacion):
    import os
    import threading

    if not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"):
        pytest.skip("Requiere postgresql para la carrera con bloqueo de fila")

    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    emisor = _emisor(mundo, "Aseguradora Cinco", f"J-{uuid4().hex[:8]}")
    d1, exp = _doc(mundo, exp, "req5")
    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "MANT-FIJO-1",
            "monto_fijo": "1000.00",
            "moneda": "VES",
            "fundamento": "Pliego",
            "documento_id": d1,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    requisito = estado["requisitos"][0]
    d2, exp = _doc(mundo, exp, "gar4")
    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "CC-1",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d2,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    g1 = _gar(estado, "GAR-01")
    version = estado["version"]
    cab = mundo.como("ua", mundo.company_a)

    resultados = []
    barrera = threading.Barrier(2, timeout=30)

    def ejecutar():
        barrera.wait()
        resp = mundo.client.post(
            f"/api/v1{G}/expedientes/{exp['id']}/garantias/{g1['id']}/ejecutar",
            headers={**cab, "If-Match": str(version)},
            json={"acto_id": acto["id"], "motivo": "Incumplimiento", "monto_ejecutado": "100.00"},
        )
        resultados.append(resp.status_code)
        if resp.status_code == 409:
            resultados.append(resp.json().get("code"))

    hilos = [threading.Thread(target=ejecutar) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    estados = [r for r in resultados if isinstance(r, int)]
    assert sorted(estados) == [201, 409]
    codigos = [r for r in resultados if isinstance(r, str)]
    assert codigos and codigos[0] in {"GOV_PROCUREMENT_FILE_STALE", "GOV_GUARANTEE_NOT_ACTIVE"}

    estado = _estado(mundo, exp).json()
    g1 = _gar(estado, "GAR-01")
    ejecuciones = [h for h in g1["historial"] if h["accion"] == "EJECUCION"]
    assert len(ejecuciones) == 1


def test_inmutable_postgresql(mundo, gobierno, ocupacion):
    from sqlalchemy.exc import DBAPIError

    from app.modules.government.models import (
        GovernmentGuaranteeEvent,
        GovernmentGuaranteeInstrument,
        GovernmentGuaranteeRequirement,
    )

    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    emisor = _emisor(mundo, "Aseguradora Seis", f"J-{uuid4().hex[:8]}")
    d1, exp = _doc(mundo, exp, "req6")
    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "MANT-FIJO-1",
            "monto_fijo": "1000.00",
            "moneda": "VES",
            "fundamento": "Pliego",
            "documento_id": d1,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    requisito = estado["requisitos"][0]
    d2, exp = _doc(mundo, exp, "gar5")
    r = _post_g(
        mundo,
        exp,
        "",
        {
            "requisito_id": requisito["id"],
            "oferta_id": ofertas[0]["id"],
            "emisor_id": emisor["id"],
            "referencia_emisor": "IN-1",
            "monto": "1000.00",
            "moneda": "VES",
            "fecha_emision": HOY.isoformat(),
            "vigente_desde": HOY.isoformat(),
            "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
            "documento_id": d2,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    g1 = _gar(estado, "GAR-01")

    d3, exp = _doc(mundo, exp, "ren2")
    r = _post_g(
        mundo,
        exp,
        f"/{g1['id']}/renovar",
        {
            "vigente_hasta": (HOY + timedelta(days=60)).isoformat(),
            "documento_id": d3,
            "motivo": "Prórroga",
        },
    )
    assert r.status_code == 201, r.text

    with mundo.factory() as db:
        if db.get_bind().dialect.name != "postgresql":
            pytest.skip("Requiere postgresql para validar el trigger de inmutabilidad")
        instrumento = db.get(GovernmentGuaranteeInstrument, g1["id"])
        instrumento.monto = 999999
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        evento = db.query(GovernmentGuaranteeEvent).filter_by(instrument_id=g1["id"]).first()
        evento.motivo = "ALTERADO"
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        requisito_db = db.get(GovernmentGuaranteeRequirement, requisito["id"])
        db.delete(requisito_db)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()


def test_sod_registrar_y_liberar(mundo, gobierno, ocupacion):
    exp, ofertas, acto = _adjudicado(mundo, ocupacion)
    emisor = _emisor(mundo, "Aseguradora Siete", f"J-{uuid4().hex[:8]}")
    d1, exp = _doc(mundo, exp, "req7")
    r = _post_g(
        mundo,
        exp,
        "/requisitos",
        {
            "regla_codigo": "MANT-FIJO-1",
            "monto_fijo": "1000.00",
            "moneda": "VES",
            "fundamento": "Pliego",
            "documento_id": d1,
        },
    )
    assert r.status_code == 201, r.text
    estado = r.json()
    requisito = estado["requisitos"][0]

    regla = regla_vigente(
        mundo,
        proceso="PROC-03",
        accion_a="PROC03_GARANTIA_REGISTRAR",
        accion_b="PROC03_GARANTIA_LIBERAR",
    )
    try:
        d2, exp = _doc(mundo, exp, "gar6")
        r = _post_g(
            mundo,
            exp,
            "",
            {
                "requisito_id": requisito["id"],
                "oferta_id": ofertas[0]["id"],
                "emisor_id": emisor["id"],
                "referencia_emisor": "SOD-1",
                "monto": "1000.00",
                "moneda": "VES",
                "fecha_emision": HOY.isoformat(),
                "vigente_desde": HOY.isoformat(),
                "vigente_hasta": (HOY + timedelta(days=30)).isoformat(),
                "documento_id": d2,
            },
        )
        assert r.status_code == 201, r.text
        estado = r.json()
        g1 = _gar(estado, "GAR-01")
        r = _post_g(
            mundo,
            exp,
            f"/{g1['id']}/liberar",
            {"acto_id": acto["id"], "motivo": "Liberación"},
        )
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "GOV_SOD_CONFLICT"
    finally:
        cerrar_regla(mundo, regla)
