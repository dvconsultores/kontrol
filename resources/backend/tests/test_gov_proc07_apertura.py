from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.documents.models import DocumentSeal
from tests.org04_ayudantes import crear_funcionario
from tests.org06_guarda import cuenta_con_permisos, exigir_identidad
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc08_paquete import _doc_real
from tests.test_gov_proc02_comisiones import _activar, _completa
from tests.test_gov_proc03_expedientes import E, _crear, _patch

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _preparar(mundo, ocupacion):
    """Crea expediente, declara concurso abierto, comision vigente y vincula comision."""
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
    """Crea matriz vinculando documento pliego y retorna estado."""
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


def _crear_aspectos_base(mundo, exp, estado):
    """Crea criterios TECNICO, ECONOMICO y LEGAL para cumplir contrato."""
    matriz_version = estado["matriz"]["version"]
    ids = []
    for aspecto, orden, nombre, escala, puntaje_maximo, ponderacion in [
        ("TECNICO", 1, "Criterio Tecnico", "PUNTAJE", "40.00", "0.4000"),
        ("ECONOMICO", 2, "Criterio Economico", "PUNTAJE", "30.00", "0.3000"),
        ("LEGAL", 3, "Criterio Legal", "CUMPLE", None, "0.3000"),
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


def test_apertura_completa(mundo, gobierno, ocupacion):
    """Matriz, criterios, bloqueo, recibir ofertas, apertura, aportes, resultados y concluir."""
    exp, comision = _preparar(mundo, ocupacion)

    estado = _crear_matriz(mundo, exp)
    estado, matriz_version, criterios = _crear_aspectos_base(mundo, exp, estado)
    criterio_id, criterio_cumple_id, criterio_legal_id = criterios

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/bloquear", "ua", mundo.company_a,
              {}, version=matriz_version)
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["matriz"]["estado"] == "BLOQUEADA"
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    doc_oferta1 = _doc_real(mundo, mundo.company_a, None, b"oferta1", "oferta1")
    r = mundo.post(f"/documentos/{doc_oferta1}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta1 = _recibir_oferta(mundo, exp, "ua", mundo.company_a, "Proveedor Uno", doc_oferta1)

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    doc_oferta2 = _doc_real(mundo, mundo.company_a, None, b"oferta2", "oferta2")
    r = mundo.post(f"/documentos/{doc_oferta2}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta2 = _recibir_oferta(mundo, exp, "ua", mundo.company_a, "Proveedor Dos", doc_oferta2)

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    assert len(estado["ofertas"]) == 2

    r = _post(mundo, f"{E}/{exp['id']}/ofertas/concluir", "ua", mundo.company_a,
              {"motivo": None}, version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = mundo.get(f"/documentos/{doc_oferta1}/descargar", "ua", mundo.company_a)
    assert r.status_code == 404, r.text

    acta_doc = _doc_real(mundo, mundo.company_a, None, b"acta apertura", "acta")
    r = mundo.post(f"/documentos/{acta_doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text

    miembro_ids = [m["id"] for m in comision["miembros"]]
    exigir_identidad(mundo)
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta1["id"], oferta2["id"]],
               "miembro_ids": miembro_ids,
               "acta_documento_id": acta_doc,
               "observaciones": "Apertura publica"},
              version=exp["version"])
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "GOV_EVAL_IDENTITY_REQUIRED"
    exigir_identidad(mundo, False)
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta1["id"], oferta2["id"]],
               "miembro_ids": miembro_ids,
               "acta_documento_id": acta_doc,
               "observaciones": "Apertura publica"},
              version=exp["version"])
    assert r.status_code == 201, r.text
    estado = r.json()
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = mundo.get(f"/documentos/{doc_oferta1}/descargar", "ua", mundo.company_a)
    assert r.status_code == 200, r.text

    for oferta in estado["ofertas"]:
        assert oferta["situacion"] == "ABIERTA"

    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    assert estado["siguiente_accion"] == "Registre los resultados de la Comisión"
    assert estado["progreso"] == {
        "ofertas_abiertas": 2,
        "criterios": 3,
        "resultados_requeridos": 6,
        "resultados_registrados": 0,
    }

    with mundo.factory() as s:
        sellos = s.query(DocumentSeal).all()
        assert len(sellos) >= 2


def test_negativos(mundo, gobierno, ocupacion):
    """Errores de permisos, versiones, matriz sin bloqueo, apertura sin ofertas, aportes con datos invalidos."""
    exp, comision = _preparar(mundo, ocupacion)

    r = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    estado = r.json()
    assert estado["matriz"] is None

    doc_pliego = _doc_real(mundo, mundo.company_a, None, b"pliego", "pliego")
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz", "ua", mundo.company_a,
              {"pliego_documento_id": doc_pliego}, version=exp["version"])
    assert r.status_code == 422, r.text

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
    estado, matriz_version, criterios = _crear_aspectos_base(mundo, exp, estado)
    criterio_id = criterios[0]

    cuenta = f"sin_permisos_proc07_{uuid4().hex[:8]}"
    cuenta_con_permisos(mundo, cuenta, [("gobierno_expedientes", "view")])
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/criterios", cuenta, mundo.company_a,
              {"aspecto": "TECNICO", "orden": 4, "nombre": "Otro", "escala": "PUNTAJE",
               "puntaje_maximo": "5.00", "ponderacion": "0.1000"},
              version=matriz_version)
    assert r.status_code == 403, r.text

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/bloquear", "ua", mundo.company_a,
              {}, version=matriz_version)
    assert r.status_code == 200, r.text
    estado = r.json()
    matriz_version = estado["matriz"]["version"]
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/criterios", "ua", mundo.company_a,
              {"aspecto": "TECNICO", "orden": 5, "nombre": "Tarde", "escala": "PUNTAJE",
               "puntaje_maximo": "5.00", "ponderacion": "0.1000"},
              version=matriz_version)
    assert r.status_code == 409, r.text

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [],
               "miembro_ids": [m["id"] for m in comision["miembros"]],
               "acta_documento_id": "0" * 36,
               "observaciones": None},
              version=exp["version"])
    assert r.status_code == 422, r.text

    doc_oferta = _doc_real(mundo, mundo.company_a, None, b"oferta negativos", "oferta_neg")
    r = mundo.post(f"/documentos/{doc_oferta}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta = _recibir_oferta(mundo, exp, "ua", mundo.company_a, "Proveedor Negativo", doc_oferta)

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    acta_doc = _doc_real(mundo, mundo.company_a, None, b"acta", "acta")
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta["id"]],
               "miembro_ids": [m["id"] for m in comision["miembros"]],
               "acta_documento_id": acta_doc,
               "observaciones": None},
              version=exp["version"])
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_OPENING_RECEPTION_OPEN"

    r = _post(mundo, f"{E}/{exp['id']}/ofertas/concluir", "ua", mundo.company_a,
              {"motivo": None}, version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta["id"]],
               "miembro_ids": [m["id"] for m in comision["miembros"]],
               "acta_documento_id": acta_doc,
               "observaciones": None},
              version=exp["version"] - 1)
    assert r.status_code == 409, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta["id"]],
               "miembro_ids": [m["id"] for m in comision["miembros"]],
               "acta_documento_id": acta_doc,
               "observaciones": None},
              version=exp["version"])
    assert r.status_code == 422, r.text
    assert "acta_documento_id" in r.json()["field_errors"]

    r = mundo.post(f"/documentos/{acta_doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta["id"]],
               "miembro_ids": [m["id"] for m in comision["miembros"]],
               "acta_documento_id": acta_doc,
               "observaciones": None},
              version=exp["version"])
    assert r.status_code == 201, r.text
    estado = r.json()

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta["id"]],
               "miembro_ids": [m["id"] for m in comision["miembros"]],
               "acta_documento_id": acta_doc,
               "observaciones": None},
              version=exp["version"])
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_OFFER_ALREADY_OPENED"

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta["id"], "criterio_id": criterio_id,
               "miembro_id": comision["miembros"][0]["id"],
               "matriz_version": estado["matriz"]["version"] + 1, "puntaje": "0.00",
               "observacion": None, "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 409, r.text

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/concluir", "ua", mundo.company_a,
              {}, version=exp["version"] - 1)
    assert r.status_code == 409, r.text


def test_eliminar_criterio(mundo, gobierno, ocupacion):
    """Eliminar criterio reordena y funciona."""
    exp, comision = _preparar(mundo, ocupacion)
    estado = _crear_matriz(mundo, exp)
    estado, matriz_version, criterios = _crear_aspectos_base(mundo, exp, estado)
    criterio_id = criterios[0]

    r = mundo.client.delete(f"/api/v1{E}/{exp['id']}/evaluacion/matriz/criterios/{criterio_id}",
                            headers={**mundo.como("ua", mundo.company_a), "If-Match": str(matriz_version)})
    assert r.status_code == 200, r.text
    estado = r.json()
    assert len(estado["matriz"]["criterios"]) == 2
    ordenes = [c["orden"] for c in estado["matriz"]["criterios"]]
    assert 0 not in ordenes
    assert len(ordenes) == len(set(ordenes))


def test_negativos_apertura_quorum_autoridad_evaluador(mundo, gobierno, ocupacion):
    """Quorum insuficiente, autoridad de evaluacion y aportes con miembros invalidos."""
    exp, comision = _preparar(mundo, ocupacion)

    estado = _crear_matriz(mundo, exp)
    estado, matriz_version, criterios = _crear_aspectos_base(mundo, exp, estado)
    criterio_id, criterio_cumple_id, criterio_legal_id = criterios

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/bloquear", "ua", mundo.company_a,
              {}, version=matriz_version)
    assert r.status_code == 200, r.text
    estado = r.json()
    matriz_version = estado["matriz"]["version"]
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    doc_oferta = _doc_real(mundo, mundo.company_a, None, b"oferta quorum", "oferta_quorum")
    r = mundo.post(f"/documentos/{doc_oferta}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta = _recibir_oferta(mundo, exp, "ua", mundo.company_a, "Proveedor Quorum", doc_oferta)

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/ofertas/concluir", "ua", mundo.company_a,
              {"motivo": None}, version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    acta_doc = _doc_real(mundo, mundo.company_a, None, b"acta quorum", "acta_quorum")
    r = mundo.post(f"/documentos/{acta_doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    cuenta = f"sin_permiso_apertura_{uuid4().hex[:8]}"
    cuenta_con_permisos(mundo, cuenta, [("gobierno_expedientes", "view"), ("gobierno_evaluacion", "view")])
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", cuenta, mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta["id"]],
               "miembro_ids": [m["id"] for m in comision["miembros"]],
               "acta_documento_id": acta_doc,
               "observaciones": None},
              version=exp["version"])
    assert r.status_code == 403, r.text

    miembro_principal = next(m for m in comision["miembros"] if m["funcion"] == "MIEMBRO" and m["condicion"] == "PRINCIPAL")
    secretarios = [m["id"] for m in comision["miembros"] if m["funcion"] == "SECRETARIO"]
    asistentes_insuficientes = [miembro_principal["id"]] + secretarios
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta["id"]],
               "miembro_ids": asistentes_insuficientes,
               "acta_documento_id": acta_doc,
               "observaciones": None},
              version=exp["version"])
    assert r.status_code == 422, r.text
    assert "asistentes" in r.json()["field_errors"]

    miembro_ids = [m["id"] for m in comision["miembros"]]
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": datetime.now(UTC).isoformat(),
               "oferta_ids": [oferta["id"]],
               "miembro_ids": miembro_ids,
               "acta_documento_id": acta_doc,
               "observaciones": None},
              version=exp["version"])
    assert r.status_code == 201, r.text
    estado = r.json()
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    secretario_id = next(m for m in comision["miembros"] if m["funcion"] == "SECRETARIO")["id"]

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta["id"], "criterio_id": criterio_id, "miembro_id": "0" * 36,
               "matriz_version": estado["matriz"]["version"], "puntaje": "10.00",
               "observacion": None, "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "GOV_EVAL_NOT_MEMBER"

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aportes", "ua", mundo.company_a,
              {"oferta_id": oferta["id"], "criterio_id": criterio_id, "miembro_id": secretario_id,
               "matriz_version": estado["matriz"]["version"], "puntaje": "10.00",
               "observacion": None, "evidencia_documento_id": None},
              version=exp["version"])
    assert r.status_code == 422, r.text
    assert "miembro_id" in r.json()["field_errors"]

    r = mundo.get(f"{E}/{exp['id']}/evaluacion", "ub", mundo.company_b)
    assert r.status_code == 404, r.text


def test_apertura_mismo_minuto_que_recepcion(mundo, gobierno, ocupacion):
    """Apertura en el mismo minuto que la recepcion concluida es valida."""
    exp, comision = _preparar(mundo, ocupacion)

    estado = _crear_matriz(mundo, exp)
    estado, matriz_version, criterios = _crear_aspectos_base(mundo, exp, estado)

    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/bloquear", "ua", mundo.company_a,
              {}, version=matriz_version)
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    doc_oferta1 = _doc_real(mundo, mundo.company_a, None, b"oferta1", "oferta1")
    r = mundo.post(f"/documentos/{doc_oferta1}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta1 = _recibir_oferta(mundo, exp, "ua", mundo.company_a, "Proveedor Uno", doc_oferta1)

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
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

    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    recepcion_concluida_en = datetime.fromisoformat(estado["recepcion_concluida_en"])
    if recepcion_concluida_en.tzinfo is None:
        recepcion_concluida_en = recepcion_concluida_en.replace(tzinfo=UTC)
    inicio = recepcion_concluida_en.replace(second=0, microsecond=0)

    miembro_ids = [m["id"] for m in comision["miembros"]]
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": (inicio - timedelta(seconds=1)).isoformat(),
               "oferta_ids": [oferta1["id"]],
               "miembro_ids": miembro_ids,
               "acta_documento_id": acta_doc,
               "observaciones": "Apertura publica"},
              version=exp["version"])
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_INVALID"
    assert "abierta_en" in r.json()["field_errors"]

    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              {"abierta_en": inicio.isoformat(),
               "oferta_ids": [oferta1["id"]],
               "miembro_ids": miembro_ids,
               "acta_documento_id": acta_doc,
               "observaciones": "Apertura publica"},
              version=exp["version"])
    assert r.status_code == 201, r.text
    estado = r.json()
    assert estado["ofertas"][0]["situacion"] == "ABIERTA"
