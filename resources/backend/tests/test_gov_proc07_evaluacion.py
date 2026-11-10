import json
from datetime import UTC, datetime
from uuid import uuid4

from app.modules.documents.models import DocumentSeal
from tests.org04_ayudantes import crear_funcionario
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc08_paquete import _doc_real
from tests.test_gov_proc02_comisiones import _activar, _completa
from tests.test_gov_proc03_expedientes import E, _crear, _patch

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _preparar(mundo, ocupacion):
    exp = _crear(mundo, ocupacion)
    exp = _patch(mundo, exp, modalidad_declarada="CONCURSO_ABIERTO", modalidad_fundamento="LCP art. 78", modalidad_fuente="LCP").json()
    comision = _completa(mundo, ocupacion)
    r = _activar(mundo, comision, usuario="uab")
    assert r.status_code == 200, r.text
    comision_vigente = r.json()
    r = _post(mundo, f"{E}/{exp['id']}/comision", "ua", mundo.company_a,
              {"comision_id": comision_vigente["id"], "no_aplica_motivo": None, "motivo": None},
              version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    return exp, comision_vigente


def _crear_matriz(mundo, exp):
    doc_id = _doc_real(mundo, mundo.company_a, None, b"pliego", "pliego")
    r = mundo.post(f"/documentos/{doc_id}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
        "role": "pliego",
    })
    assert r.status_code == 200, r.text
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz", "ua", mundo.company_a,
              {"pliego_documento_id": doc_id}, version=exp["version"])
    assert r.status_code == 201, r.text
    return r.json()


def _crear_criterios_contrato(mundo, exp, estado):
    """Crea al menos un criterio TECNICO, ECONOMICO y LEGAL."""
    matriz_version = estado["matriz"]["version"]
    ids = []
    for aspecto, orden, nombre, escala, puntaje_maximo, ponderacion in [
        ("TECNICO", 1, "Precio", "PUNTAJE", "50.00", "0.5000"),
        ("ECONOMICO", 2, "Capacidad", "PUNTAJE", "50.00", "0.5000"),
        ("LEGAL", 3, "Cumplimiento", "CUMPLE", None, None),
    ]:
        body = {"aspecto": aspecto, "orden": orden, "nombre": nombre, "escala": escala}
        if puntaje_maximo is not None:
            body["puntaje_maximo"] = puntaje_maximo
        body["ponderacion"] = ponderacion
        r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/criterios", "ua", mundo.company_a,
                  body, version=matriz_version)
        assert r.status_code == 201, r.text
        estado = r.json()
        matriz_version = estado["matriz"]["version"]
        ids.append(next(c["id"] for c in estado["matriz"]["criterios"] if c["nombre"] == nombre))
    return estado, matriz_version, ids


def _recibir_oferta(mundo, exp, usuario, empresa, oferente_nombre, doc_id=None):
    funcionario = crear_funcionario(mundo, usuario=usuario, empresa=empresa)
    doc_ids = [doc_id] if doc_id else []
    body = {
        "oferente_nombre": oferente_nombre,
        "oferente_documento": f"abc-{uuid4().hex[:6]}",
        "representante": "Representante",
        "tipo_sobre": "UNICO",
        "canal": "MEDIO_ELECTRONICO",
        "recibida_en": datetime.now(UTC).isoformat(),
        "funcionario_id": funcionario["id"],
        "confidencial": True,
        "documento_ids": doc_ids,
    }
    r = _post(mundo, f"{E}/{exp['id']}/ofertas", usuario, empresa, body, version=exp["version"])
    assert r.status_code == 201, r.text
    return r.json()


def _abrir_ofertas(mundo, exp, comision, ofertas):
    r = _post(mundo, f"{E}/{exp['id']}/ofertas/concluir", "ua", mundo.company_a,
              {"motivo": None}, version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    acta_doc = _doc_real(mundo, mundo.company_a, None, b"acta apertura", "acta")
    r = mundo.post(f"/documentos/{acta_doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    miembro_ids = [m["id"] for m in comision["miembros"]]
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [o["id"] for o in ofertas],
               "miembro_ids": miembro_ids,
               "acta_documento_id": acta_doc,
               "observaciones": "Apertura"},
              version=exp["version"])
    assert r.status_code == 201, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    return r.json(), exp


def test_evaluacion_completa_con_resultados(mundo, gobierno, ocupacion):
    """Flujo completo con aportes y resultados, verificar sellos y evaluacion final."""
    exp, comision = _preparar(mundo, ocupacion)

    estado = _crear_matriz(mundo, exp)
    estado, matriz_version, criterios = _crear_criterios_contrato(mundo, exp, estado)
    criterio_precio = criterios[0]
    criterio_calidad = criterios[1]
    criterio_legal = criterios[2]

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/bloquear", "ua", mundo.company_a,
              {}, version=matriz_version)
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["matriz"]["estado"] == "BLOQUEADA"
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    doc1 = _doc_real(mundo, mundo.company_a, None, b"oferta eval 1", "eval1")
    r = mundo.post(f"/documentos/{doc1}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta1 = _recibir_oferta(mundo, exp, "ua", mundo.company_a, "Eval Uno", doc1)

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    doc2 = _doc_real(mundo, mundo.company_a, None, b"oferta eval 2", "eval2")
    r = mundo.post(f"/documentos/{doc2}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta2 = _recibir_oferta(mundo, exp, "ua", mundo.company_a, "Eval Dos", doc2)

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    estado_apertura, exp = _abrir_ofertas(mundo, exp, comision, [oferta1, oferta2])
    matriz_version = estado_apertura["matriz"]["version"]
    miembros_principales = [
        m for m in comision["miembros"]
        if m["funcion"] == "MIEMBRO" and m["condicion"] == "PRINCIPAL"
    ]
    m1 = miembros_principales[0]["id"]
    m2 = miembros_principales[1]["id"]
    secretario = next(m for m in comision["miembros"] if m["funcion"] == "SECRETARIO")["id"]

    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    assert estado["siguiente_accion"] == "Registre los resultados de la Comisión"
    assert estado["progreso"] == {
        "ofertas_abiertas": 2,
        "criterios": 3,
        "resultados_requeridos": 6,
        "resultados_registrados": 0,
    }

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_precio, "miembro_id": m1,
               "matriz_version": matriz_version, "puntaje": "45.00", "observacion": "Buen precio",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_precio, "miembro_id": m2,
               "matriz_version": matriz_version, "puntaje": "40.00", "observacion": "Precio medio",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_precio, "miembro_id": m1,
               "matriz_version": matriz_version, "puntaje": "44.50", "observacion": "Precio revisado",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_legal, "miembro_id": m1,
               "matriz_version": matriz_version, "cumple": True, "observacion": "Cumple legal",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    elemento_precio = next(
        o for o in estado["resultados_por_oferta"]
        if o["oferta_id"] == oferta1["id"] and o["criterio_id"] == criterio_precio
    )
    assert len(elemento_precio["aportes"]) == 2
    aporte_m1 = next(a for a in elemento_precio["aportes"] if a["miembro_id"] == m1)
    aporte_m2 = next(a for a in elemento_precio["aportes"] if a["miembro_id"] == m2)
    assert aporte_m1["puntaje"] == "44.50"
    assert aporte_m1["reemplaza_a"] is not None
    assert len(aporte_m1["historial_reemplazos"]) == 1
    assert aporte_m1["historial_reemplazos"][0]["puntaje"] == "45.00"
    assert aporte_m2["puntaje"] == "40.00"
    assert aporte_m2["historial_reemplazos"] == []
    assert elemento_precio["resultado_comision"] is None

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_precio, "miembro_id": m1,
               "matriz_version": matriz_version, "puntaje": "60.00", "observacion": "Fuera de escala",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 422
    assert "puntaje" in r.json().get("field_errors", {})

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_calidad, "miembro_id": m1,
               "matriz_version": matriz_version, "cumple": True, "puntaje": "10.00",
               "observacion": "No corresponde",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 422
    assert "cumple" in r.json().get("field_errors", {})

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_legal, "miembro_id": m1,
               "matriz_version": matriz_version, "puntaje": "1.00", "observacion": "No corresponde",
               "evidencia_documento_id": None, "cumple": True},
              version=exp["version"])
    assert r.status_code == 422
    assert "puntaje" in r.json().get("field_errors", {})

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_precio, "miembro_id": secretario,
               "matriz_version": matriz_version, "puntaje": "40.00", "observacion": "Sin voto",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 422
    assert "miembro_id" in r.json().get("field_errors", {})

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/concluir", "ua", mundo.company_a,
              {"version": exp["version"]}, version=exp["version"])
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_EVAL_RESULTS_INCOMPLETE"

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/resultados", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_precio, "miembro_id": secretario,
               "matriz_version": matriz_version, "puntaje": "44.00", "observacion": "Comision precio",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/resultados", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_calidad, "miembro_id": secretario,
               "matriz_version": matriz_version, "puntaje": "38.00", "observacion": "Comision calidad",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/resultados", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_legal, "miembro_id": secretario,
               "matriz_version": matriz_version, "cumple": True, "observacion": "Comision legal",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/resultados", "ua", mundo.company_a,
              {"oferta_id": oferta2["id"], "criterio_id": criterio_precio, "miembro_id": secretario,
               "matriz_version": matriz_version, "puntaje": "41.00", "observacion": "Comision precio dos",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/resultados", "ua", mundo.company_a,
              {"oferta_id": oferta2["id"], "criterio_id": criterio_precio, "miembro_id": secretario,
               "matriz_version": matriz_version, "puntaje": "40.50", "observacion": "Comision precio dos revisado",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/resultados", "ua", mundo.company_a,
              {"oferta_id": oferta2["id"], "criterio_id": criterio_calidad, "miembro_id": secretario,
               "matriz_version": matriz_version, "puntaje": "35.00", "observacion": "Comision calidad dos",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/resultados", "ua", mundo.company_a,
              {"oferta_id": oferta2["id"], "criterio_id": criterio_legal, "miembro_id": secretario,
               "matriz_version": matriz_version, "cumple": False, "observacion": "Comision legal dos",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 201, r.text

    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    elemento_precio_dos = next(
        o for o in estado["resultados_por_oferta"]
        if o["oferta_id"] == oferta2["id"] and o["criterio_id"] == criterio_precio
    )
    assert elemento_precio_dos["resultado_comision"]["puntaje"] == "40.50"
    assert len(elemento_precio_dos["resultado_comision"]["historial_reemplazos"]) == 1
    assert elemento_precio_dos["resultado_comision"]["historial_reemplazos"][0]["puntaje"] == "41.00"

    elemento_precio_uno = next(
        o for o in estado["resultados_por_oferta"]
        if o["oferta_id"] == oferta1["id"] and o["criterio_id"] == criterio_precio
    )
    assert elemento_precio_uno["resultado_comision"]["puntaje"] == "44.00"
    aportes_precio_uno = {a["miembro_id"]: a for a in elemento_precio_uno["aportes"]}
    assert aportes_precio_uno[m1]["puntaje"] == "44.50"
    assert aportes_precio_uno[m2]["puntaje"] == "40.00"

    assert estado["progreso"]["resultados_registrados"] == 6
    assert estado["siguiente_accion"] == "Concluya la evaluación"

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/concluir", "ua", mundo.company_a,
              {"version": exp["version"]}, version=exp["version"] - 1)
    assert r.status_code == 409

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/concluir", "ua", mundo.company_a,
              {"version": exp["version"]}, version=exp["version"])
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["evaluacion_concluida_en"] is not None
    assert "PROC-08" in estado["siguiente_accion"]
    assert "evaluacion_por_oferta" not in estado

    estado_str = json.dumps(estado, ensure_ascii=False).upper()
    assert "ADJUDIC" not in estado_str

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta1["id"], "criterio_id": criterio_precio, "miembro_id": m1,
               "matriz_version": matriz_version, "puntaje": "45.00", "observacion": "Tarde",
               "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_EVALUATION_CONCLUDED"

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/concluir", "ua", mundo.company_a,
              {"version": exp["version"]}, version=exp["version"])
    assert r.status_code == 409

    with mundo.factory() as s:
        sellos = s.query(DocumentSeal).all()
        assert len(sellos) >= 2


def test_evaluacion_get_inicial_y_bloqueo(mundo, gobierno, ocupacion):
    """GET inicial sin matriz, error al bloquear sin criterios, y bloqueo exitoso."""
    exp, comision = _preparar(mundo, ocupacion)

    r = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["matriz"] is None
    assert estado["siguiente_accion"] is not None

    doc_pliego = _doc_real(mundo, mundo.company_a, None, b"pliego", "pliego")
    r = mundo.post(f"/documentos/{doc_pliego}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
        "role": "pliego",
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz", "ua", mundo.company_a,
              {"pliego_documento_id": doc_pliego}, version=exp["version"])
    assert r.status_code == 201, r.text
    estado = r.json()
    matriz_version = estado["matriz"]["version"]

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/bloquear", "ua", mundo.company_a,
              {}, version=matriz_version)
    assert r.status_code == 422, r.text

    estado, matriz_version, criterios = _crear_criterios_contrato(mundo, exp, estado)

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/bloquear", "ua", mundo.company_a,
              {}, version=matriz_version)
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["matriz"]["estado"] == "BLOQUEADA"
    assert estado["matriz"]["criterios"][0]["ponderacion"] == "0.5000"


def test_sin_permisos_otra_empresa(mundo, gobierno, ocupacion):
    """Otra empresa no ve evaluacion; sin permisos no crea matriz."""
    exp, comision = _preparar(mundo, ocupacion)

    r = mundo.get(f"{E}/{exp['id']}/evaluacion", "ub", mundo.company_b)
    assert r.status_code == 404, r.text

    cuenta = f"sin_permisos_proc07_eval_{uuid4().hex[:8]}"
    cuenta_con_permisos(mundo, cuenta, [("gobierno_expedientes", "view")])
    r = mundo.get(f"{E}/{exp['id']}/evaluacion", cuenta, mundo.company_a)
    assert r.status_code == 403, r.text

    doc_pliego = _doc_real(mundo, mundo.company_a, None, b"pliego", "pliego")
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz", cuenta, mundo.company_a,
              {"pliego_documento_id": doc_pliego}, version=exp["version"])
    assert r.status_code == 403, r.text
