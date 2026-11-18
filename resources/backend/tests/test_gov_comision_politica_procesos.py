# ruff: noqa: E402, F811, F401, I001
import json
from datetime import UTC, datetime
from uuid import uuid4

import tests.test_gov_proc02_comisiones as p02
from app.shared.clock import hoy_de_negocio
from tests.org04_ayudantes import D, crear_funcionario
from tests.proc08_ayudantes import (
    _recibir_oferta,
    evaluacion_concluida,
    post_recomendacion_cruda,
    recomendar,
)
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc08_paquete import _doc_real
from tests.test_gov_proc03_expedientes import E, _crear, _patch
from tests.test_gov_proc07_evaluacion import (
    _abrir_ofertas,
    _crear_criterios_contrato,
    _crear_matriz,
    _preparar,
)

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

C = "/gobierno/contrataciones/comisiones"


def _politica(mundo, decision_tipo="SIMPLE_MAJORITY", quorum_tipo="SIMPLE_MAJORITY",
              decision_calificada=None, documentos=None):
    cuerpo = {
        "codigo": f"P{uuid4().hex[:8]}",
        "nombre": f"Política {uuid4().hex[:6]}",
        "base_normativa": "LCP_ART14",
        "fundamento": "Fundamento de la política de prueba",
        "vigente_desde": D(1, 1).isoformat(),
        "exige_impar": True,
        "suplente_por_principal": True,
        "exige_secretario": True,
        "exige_suplente_secretario": True,
        "quorum": {"tipo": quorum_tipo},
        "decision": decision_calificada or {"tipo": decision_tipo, "base": "MIEMBROS_CON_VOTO"},
        "documentos": documentos or [],
    }
    r = _post(mundo, "/gobierno/contrataciones/politicas-comision", "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    pol = r.json()
    r = _post(mundo, f"/gobierno/contrataciones/politicas-comision/{pol['id']}/activar",
              "uab", mundo.company_a, {}, version=pol["version"])
    assert r.status_code == 200, r.text
    return r.json()


def _parchear_politica(monkeypatch, politica_id):
    original = p02._comision
    monkeypatch.setattr(p02, "_comision", lambda m, o, **c: original(m, o, politica_id=politica_id, **c))


def _sin_comision(mundo, exp):
    r = _post(mundo, f"{E}/{exp['id']}/comision", "ua", mundo.company_a,
              {"comision_id": None,
               "no_aplica_motivo": "Contratación por consulta de precios sin comisión",
               "motivo": None},
              version=exp["version"])
    assert r.status_code == 200, r.text
    return mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()


def _responsable_id(mundo, exp):
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    return exp["responsables"][0]["id"]


def _crear_oferta(mundo, exp, nombre):
    doc = _doc_real(mundo, mundo.company_a, None, f"oferta {nombre}".encode(), f"d{nombre}")
    r = mundo.post(f"/documentos/{doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    return _recibir_oferta(mundo, exp, "ua", mundo.company_a, f"Oferente {nombre}", doc)


def _bloquear(mundo, exp, estado):
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/matriz/bloquear", "ua", mundo.company_a,
              {}, version=estado["matriz"]["version"])
    assert r.status_code == 200, r.text
    return mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()


def _post_apertura_cruda(mundo, exp, cuerpo):
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a,
              cuerpo, version=exp["version"])
    return r


def _apertura_body(mundo, exp, ofertas, miembro_ids=(), responsable_ids=()):
    acta_doc = _doc_real(mundo, mundo.company_a, None, b"acta apertura", "acta")
    r = mundo.post(f"/documentos/{acta_doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cuerpo = {
        "abierta_en": datetime.now(UTC).isoformat(),
        "oferta_ids": [o["id"] for o in ofertas],
        "miembro_ids": list(miembro_ids),
        "responsable_ids": list(responsable_ids),
        "acta_documento_id": acta_doc,
        "observaciones": "Apertura",
    }
    return cuerpo, exp


def _inhibir(mundo, exp, comision, miembro_id, usuaria="uab"):
    r = _post(mundo, f"{C}/{comision['id']}/inhibiciones", "ua", mundo.company_a, {
        "miembro_id": miembro_id,
        "asunto": "Conflicto de intereses",
        "causal": "INTERES",
        "descripcion": "Tiene interés directo en el resultado",
        "fecha": D(1, 11).isoformat(),
        "soporte": None,
        "expediente_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    inh = r.json()["inhibiciones"][-1]
    r = _post(mundo, f"{C}/{comision['id']}/inhibiciones/{inh['id']}/resolver",
              usuaria, mundo.company_a,
              {"decision": "ACEPTADA", "motivo": "Se acepta la inhibición declarada"},
              version=inh["version"])
    assert r.status_code == 200, r.text
    return inh


def _crear_tipo_documento(mundo):
    with mundo.factory() as db:
        from app.modules.documents.models import DocumentType

        tipo = DocumentType(
            company_id=mundo.company_a,
            code=f"TD{uuid4().hex[:8]}",
            name="Convocatoria",
        )
        db.add(tipo)
        db.commit()
        return tipo.id


def _vincular_documento(mundo, exp, tipo_id):
    with mundo.factory() as db:
        from app.modules.documents.models import Document, DocumentLink

        doc = Document(
            company_id=mundo.company_a,
            document_type_id=tipo_id,
            title=f"Doc {uuid4().hex[:6]}",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()
        link = DocumentLink(
            document_id=doc.id,
            company_id=mundo.company_a,
            resource_type="GovernmentProcurementFile",
            resource_id=exp["id"],
        )
        db.add(link)
        db.commit()


def test_apertura_sin_comision_y_sin_motivo_se_rechaza(mundo, gobierno, ocupacion):
    exp = _crear(mundo, ocupacion)
    exp = _patch(mundo, exp, modalidad_declarada="CONCURSO_ABIERTO",
                 modalidad_fundamento="LCP art. 78", modalidad_fuente="LCP").json()

    estado = _crear_matriz(mundo, exp)
    _crear_criterios_contrato(mundo, exp, estado)
    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    exp = _bloquear(mundo, exp, estado)

    doc = _doc_real(mundo, mundo.company_a, None, b"oferta a", "da")
    r = mundo.post(f"/documentos/{doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    funcionario = crear_funcionario(mundo, usuario="ua")
    cuerpo = {
        "oferente_nombre": "Oferente a",
        "oferente_documento": f"J-{uuid4().int % 100000000:08d}-1",
        "representante": "Representante",
        "tipo_sobre": "UNICO",
        "canal": "MEDIO_ELECTRONICO",
        "recibida_en": datetime.now(UTC).isoformat(),
        "funcionario_id": funcionario["id"],
        "confidencial": True,
        "documento_ids": [doc],
    }
    r = _post(mundo, f"{E}/{exp['id']}/ofertas", "ua", mundo.company_a, cuerpo, version=exp["version"])
    assert r.status_code == 422, r.text
    assert "comision" in r.json()["field_errors"]


def test_ciclo_sin_comision_por_responsables(mundo, gobierno, ocupacion, monkeypatch):
    exp = _crear(mundo, ocupacion)
    exp = _patch(mundo, exp, modalidad_declarada="CONCURSO_ABIERTO",
                 modalidad_fundamento="LCP art. 78", modalidad_fuente="LCP").json()
    exp = _sin_comision(mundo, exp)

    estado = _crear_matriz(mundo, exp)
    estado, _version, _criterios = _crear_criterios_contrato(mundo, exp, estado)
    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    exp = _bloquear(mundo, exp, estado)

    oferta1 = _crear_oferta(mundo, exp, "1")
    oferta2 = _crear_oferta(mundo, exp, "2")
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/ofertas/concluir", "ua", mundo.company_a,
              {"motivo": None}, version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    ofertas = [oferta1, oferta2]
    exp_actual = exp

    # Apertura sin responsables → 422
    cuerpo, exp_actual = _apertura_body(mundo, exp_actual, ofertas, responsable_ids=())
    r = _post_apertura_cruda(mundo, exp_actual, cuerpo)
    assert r.status_code == 422, r.text
    assert "responsables" in r.json()["field_errors"]

    # Apertura con responsables → 201
    responsable_id = _responsable_id(mundo, exp_actual)
    cuerpo, exp_actual = _apertura_body(mundo, exp_actual, ofertas, responsable_ids=[responsable_id])
    r = _post_apertura_cruda(mundo, exp_actual, cuerpo)
    assert r.status_code == 201, r.text
    estado = r.json()
    apertura = estado["aperturas"][-1]
    assert apertura["modo"] == "UNIDAD_CONTRATANTE"
    assert len(apertura["responsables"]) == 1

    criterios = estado["matriz"]["criterios"]
    for oferta in ofertas:
        for criterio in criterios:
            exp_actual = mundo.get(f"{E}/{exp_actual['id']}", "ua", mundo.company_a).json()
            estado_ev = mundo.get(f"{E}/{exp_actual['id']}/evaluacion", "ua", mundo.company_a).json()
            version = estado_ev["matriz"]["version"]
            body = {
                "oferta_id": oferta["id"],
                "criterio_id": criterio["id"],
                "responsable_id": responsable_id,
                "matriz_version": version,
                "observacion": "Unidad",
                "evidencia_documento_id": None,
            }
            if criterio["escala"] == "PUNTAJE":
                body["puntaje"] = "40.00"
            else:
                body["cumple"] = True
            r = _post(mundo, f"{E}/{exp_actual['id']}/evaluacion/resultados", "ua", mundo.company_a,
                      body, version=exp_actual["version"])
            assert r.status_code == 201, r.text

    exp_actual = mundo.get(f"{E}/{exp_actual['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp_actual['id']}/evaluacion/concluir", "ua", mundo.company_a,
              {}, version=exp_actual["version"])
    assert r.status_code == 200, r.text
    exp_actual = mundo.get(f"{E}/{exp_actual['id']}", "ua", mundo.company_a).json()

    cuerpo = {
        "resultado_recomendado": "ADJUDICAR",
        "motivacion": "Motivación",
        "examen_legal": "Examen legal",
        "examen_financiero": "Examen financiero",
        "examen_tecnico": "Examen técnico",
        "resultado_matriz": "Resultado matriz",
        "medidas_promocion": "Medidas",
        "responsable_ids": [responsable_id],
        "opciones": [{"posicion": 1, "offer_id": oferta1["id"]}],
        "rechazos": [],
        "causal_desierta": None,
    }
    r = _post(mundo, f"{E}/{exp_actual['id']}/decision/recomendaciones", "ua", mundo.company_a,
              cuerpo, version=exp_actual["version"])
    assert r.status_code == 201, r.text
    estado = r.json()
    assert estado["recomendacion_vigente"]["modo"] == "UNIDAD_CONTRATANTE"
    assert len(estado["recomendacion_vigente"]["responsables"]) == 1


def test_quorum_por_unanimidad(mundo, gobierno, ocupacion, monkeypatch):
    pol = _politica(mundo, quorum_tipo="UNANIMITY")
    _parchear_politica(monkeypatch, pol["id"])

    exp, comision = _preparar(mundo, ocupacion)
    estado = _crear_matriz(mundo, exp)
    estado, _version, _criterios = _crear_criterios_contrato(mundo, exp, estado)
    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    exp = _bloquear(mundo, exp, estado)

    oferta = _crear_oferta(mundo, exp, "a")
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/ofertas/concluir", "ua", mundo.company_a,
              {"motivo": None}, version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    principales = [m["id"] for m in comision["miembros"] if m["condicion"] == "PRINCIPAL"]

    # Solo 2 de los 3 principales → sin quórum
    cuerpo, exp_actual = _apertura_body(mundo, exp, [oferta], miembro_ids=principales[:2])
    r = _post_apertura_cruda(mundo, exp_actual, cuerpo)
    assert r.status_code == 422, r.text
    assert "Sin quórum" in r.json()["field_errors"]["asistentes"][0]

    # Con los 3 principales → OK
    exp_actual = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cuerpo, exp_actual = _apertura_body(mundo, exp_actual, [oferta], miembro_ids=principales)
    r = _post_apertura_cruda(mundo, exp_actual, cuerpo)
    assert r.status_code == 201, r.text


def test_inhibido_no_asiste_y_actua_su_suplente(mundo, gobierno, ocupacion):
    exp, comision = _preparar(mundo, ocupacion)
    estado = _crear_matriz(mundo, exp)
    estado, _version, _criterios = _crear_criterios_contrato(mundo, exp, estado)
    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    exp = _bloquear(mundo, exp, estado)

    oferta = _crear_oferta(mundo, exp, "a")
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/ofertas/concluir", "ua", mundo.company_a,
              {"motivo": None}, version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    principales = [m for m in comision["miembros"] if m["funcion"] == "MIEMBRO" and m["condicion"] == "PRINCIPAL"]
    inhibido = principales[0]
    suplente = next(m for m in comision["miembros"] if m["suplente_de_id"] == inhibido["id"])

    _inhibir(mundo, exp, comision, inhibido["id"])

    # Con inhibido → rechaza
    cuerpo, exp_actual = _apertura_body(mundo, exp, [oferta], miembro_ids=[inhibido["id"]])
    r = _post_apertura_cruda(mundo, exp_actual, cuerpo)
    assert r.status_code == 422, r.text
    assert "inhibición aceptada" in r.json()["field_errors"]["asistentes"][0]

    # Con suplente y otros principales → OK
    exp_actual = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    asistentes = [m["id"] for m in principales[1:]] + [suplente["id"]]
    cuerpo, exp_actual = _apertura_body(mundo, exp_actual, [oferta], miembro_ids=asistentes)
    r = _post_apertura_cruda(mundo, exp_actual, cuerpo)
    assert r.status_code == 201, r.text
    estado = r.json()
    miembro_inhibido = next(m for m in estado["miembros"] if m["id"] == inhibido["id"])
    assert miembro_inhibido["inhibido"] is True


def test_documento_de_apertura_obligatorio(mundo, gobierno, ocupacion, monkeypatch):
    tipo_id = _crear_tipo_documento(mundo)
    pol = _politica(mundo, documentos=[{
        "document_type_id": tipo_id,
        "etapa": "APERTURA",
        "obligatorio": True,
    }])
    _parchear_politica(monkeypatch, pol["id"])

    exp, comision = _preparar(mundo, ocupacion)
    estado = _crear_matriz(mundo, exp)
    estado, _version, _criterios = _crear_criterios_contrato(mundo, exp, estado)
    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    exp = _bloquear(mundo, exp, estado)

    oferta = _crear_oferta(mundo, exp, "a")
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/ofertas/concluir", "ua", mundo.company_a,
              {"motivo": None}, version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    principales = [m["id"] for m in comision["miembros"] if m["condicion"] == "PRINCIPAL"]

    # Sin documento → 422
    cuerpo, exp_actual = _apertura_body(mundo, exp, [oferta], miembro_ids=principales)
    r = _post_apertura_cruda(mundo, exp_actual, cuerpo)
    assert r.status_code == 422, r.text
    assert "documentos" in r.json()["field_errors"]

    # Vincular documento → 201
    _vincular_documento(mundo, exp_actual, tipo_id)
    exp_actual = mundo.get(f"{E}/{exp_actual['id']}", "ua", mundo.company_a).json()
    cuerpo, exp_actual = _apertura_body(mundo, exp_actual, [oferta], miembro_ids=principales)
    r = _post_apertura_cruda(mundo, exp_actual, cuerpo)
    assert r.status_code == 201, r.text


def test_mayoria_calificada_en_la_recomendacion(mundo, gobierno, ocupacion, monkeypatch):
    pol = _politica(mundo, decision_calificada={
        "tipo": "QUALIFIED_MAJORITY",
        "numerador": 2,
        "denominador": 3,
        "base": "MIEMBROS_CON_VOTO",
    })
    _parchear_politica(monkeypatch, pol["id"])

    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    principales = [m["id"] for m in comision["miembros"] if m["funcion"] == "MIEMBRO" and m["condicion"] == "PRINCIPAL"]

    # 1 firmante con decision 2/3 → no alcanza mayoría
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cuerpo = {
        "resultado_recomendado": "ADJUDICAR",
        "motivacion": "Motivación",
        "examen_legal": "Examen legal",
        "examen_financiero": "Examen financiero",
        "examen_tecnico": "Examen técnico",
        "resultado_matriz": "Resultado matriz",
        "medidas_promocion": "Medidas",
        "firmante_ids": [principales[0]],
        "asistente_ids": principales,
        "opciones": [{"posicion": 1, "offer_id": ofertas[0]["id"]}],
        "rechazos": [],
        "causal_desierta": None,
    }
    r = post_recomendacion_cruda(mundo, exp, cuerpo)
    assert r.status_code == 422, r.text
    assert "GOV_RECOMMENDATION_MAJORITY" in str(r.json())

    # 2 firmantes → mayoría calificada alcanzada
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cuerpo = {
        "resultado_recomendado": "ADJUDICAR",
        "motivacion": "Motivación",
        "examen_legal": "Examen legal",
        "examen_financiero": "Examen financiero",
        "examen_tecnico": "Examen técnico",
        "resultado_matriz": "Resultado matriz",
        "medidas_promocion": "Medidas",
        "firmante_ids": principales[:2],
        "asistente_ids": principales,
        "opciones": [{"posicion": 1, "offer_id": ofertas[0]["id"]}],
        "rechazos": [],
        "causal_desierta": None,
    }
    r = post_recomendacion_cruda(mundo, exp, cuerpo)
    assert r.status_code == 201, r.text
    estado = r.json()
    regla = estado["recomendacion_vigente"]["regla"]
    assert regla["votos_a_favor"] == 2
    assert regla["requerido"] == 2


def test_firmante_inhibido_se_rechaza(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    principales = [m["id"] for m in comision["miembros"] if m["funcion"] == "MIEMBRO" and m["condicion"] == "PRINCIPAL"]
    inhibido = principales[0]
    _inhibir(mundo, exp, comision, inhibido)

    r = recomendar(
        mundo, exp, comision, ofertas,
        firmante_ids=[m["id"] for m in comision["miembros"]],
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
        esperado=422,
    )
    assert "inhibición aceptada" in r.json()["field_errors"]["firmantes"][0]


def test_suplente_con_su_principal_no_cuenta_voto(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)

    r = recomendar(
        mundo, exp, comision, ofertas,
        firmante_ids=[m["id"] for m in comision["miembros"]],
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}],
    )
    estado = r
    firmantes = estado["recomendacion_vigente"]["firmantes"]
    for f in firmantes:
        if f["funcion"] == "MIEMBRO" and f["condicion"] == "PRINCIPAL":
            assert f["cuenta_voto"] is True
        elif f["funcion"] == "MIEMBRO" and f["condicion"] == "SUPLENTE":
            assert f["cuenta_voto"] is False
        elif f["funcion"] == "SECRETARIO":
            assert f["cuenta_voto"] is False


def test_responsable_no_evalua_con_comision(mundo, gobierno, ocupacion):
    exp, comision = _preparar(mundo, ocupacion)
    estado = _crear_matriz(mundo, exp)
    estado, _version, criterios = _crear_criterios_contrato(mundo, exp, estado)
    estado = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    exp = _bloquear(mundo, exp, estado)

    oferta = _crear_oferta(mundo, exp, "a")
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    estado_apertura, exp = _abrir_ofertas(mundo, exp, comision, [oferta])

    responsable_id = _responsable_id(mundo, exp)
    criterio = estado_apertura["matriz"]["criterios"][0]
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    estado_ev = mundo.get(f"{E}/{exp['id']}/evaluacion", "ua", mundo.company_a).json()
    version = estado_ev["matriz"]["version"]
    body = {
        "oferta_id": oferta["id"],
        "criterio_id": criterio["id"],
        "responsable_id": responsable_id,
        "matriz_version": version,
        "observacion": "Responsable",
        "evidencia_documento_id": None,
    }
    if criterio["escala"] == "PUNTAJE":
        body["puntaje"] = "40.00"
    else:
        body["cumple"] = True
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/resultados", "ua", mundo.company_a,
              body, version=exp["version"])
    assert r.status_code == 422, r.text
    assert "responsable_id" in r.json()["field_errors"]
