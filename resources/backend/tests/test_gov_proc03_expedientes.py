from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.shared.clock import hoy_de_negocio
from tests.org04_ayudantes import acto_eficaz, crear_funcionario
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_ctl01_reglas import cerrar_regla, regla_vigente
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc02_actos import _doc_con_version
from tests.test_gov_doc08_paquete import _doc_real
from tests.test_gov_proc02_comisiones import _activar, _completa

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)

E = "/gobierno/contrataciones/expedientes"


def _base(mundo, ocupacion, funcionario_id):
    return {
        "fecha_inicio": (hoy_de_negocio() - timedelta(days=30)).isoformat(),
        "objeto": "Objeto de prueba",
        "partes": None,
        "tipo_contratacion": "BIENES",
        "modalidad_declarada": None,
        "modalidad_fundamento": None,
        "modalidad_fuente": None,
        "unidad_id": ocupacion["unidad_raiz"],
        "responsable_id": funcionario_id,
    }


def _crear(mundo, ocupacion, usuario="ua", empresa=None, funcionario_id=None):
    empresa = empresa or mundo.company_a
    if funcionario_id is None:
        funcionario_id = crear_funcionario(mundo, usuario=usuario, empresa=empresa)["id"]
    cuerpo = {"numero": f"EX-{uuid4().hex[:8]}", **_base(mundo, ocupacion, funcionario_id)}
    r = _post(mundo, E, usuario, empresa, cuerpo)
    assert r.status_code == 201, r.text
    return r.json()


def _patch(mundo, expediente, usuario="ua", empresa=None, **extra):
    empresa = empresa or mundo.company_a
    cuerpo = {
        "numero": expediente["numero"],
        "fecha_inicio": expediente["fecha_inicio"],
        "objeto": expediente["objeto"],
        "partes": expediente["partes"],
        "tipo_contratacion": expediente["tipo_contratacion"],
        "modalidad_declarada": expediente["modalidad_declarada"],
        "modalidad_fundamento": expediente["modalidad_fundamento"],
        "modalidad_fuente": expediente["modalidad_fuente"],
        "unidad_id": expediente["unidad_id"],
        "motivo": "Actualización",
    }
    cuerpo.update(extra)
    return mundo.client.patch(
        f"/api/v1{E}/{expediente['id']}",
        headers={**mundo.como(usuario, empresa), "If-Match": str(expediente["version"])},
        json=cuerpo,
    )


def _cron(mundo, expediente_id, empresa=None, clases=None):
    cabeceras = mundo.como("ua", empresa or mundo.company_a)
    params = {"clases": clases} if clases else None
    r = mundo.client.get(f"/api/v1{E}/{expediente_id}/cronologia", headers=cabeceras, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def _actuacion(**extra):
    cuerpo = {
        "clase": "ACTUACION",
        "fecha": hoy_de_negocio().isoformat(),
        "titulo": "Actuación",
        "detalle": None,
        "resultado": None,
        "funcionario_id": None,
        "acto_id": None,
        "folio_id": None,
        "hito_id": None,
        "rectifica_id": None,
        "motivo": None,
    }
    cuerpo.update(extra)
    return cuerpo


def test_flujo_del_expediente(mundo, gobierno, ocupacion):
    funcionario = crear_funcionario(mundo, usuario="ua")
    detalle = _crear(mundo, ocupacion, funcionario_id=funcionario["id"])
    assert detalle["status"] == "ABIERTO"
    assert detalle["version"] == 1
    assert detalle["responsable"] == funcionario["nombre"]
    assert detalle["responsables"][0]["funcionario_id"] == funcionario["id"]
    codes = {p["codigo"] for p in detalle["pendientes"]}
    assert "MODALIDAD" in codes and "PARTES" in codes
    assert detalle["siguiente_accion"] is not None

    r = _patch(
        mundo,
        detalle,
        partes="Ayuntamiento y contratista",
        modalidad_declarada="CONCURSO_ABIERTO",
        modalidad_fundamento="Ley 9/2017",
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["modalidad_etiqueta"] == "Concurso abierto"
    assert "MODALIDAD" not in {p["codigo"] for p in detalle["pendientes"]}

    r = _post(
        mundo,
        f"{E}/{detalle['id']}/responsables",
        "ua",
        mundo.company_a,
        {"funcionario_id": funcionario["id"], "rol": "CUSTODIA", "desde": None},
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    custodias = [x for x in detalle["responsables"] if x["rol"] == "CUSTODIA"]
    assert custodias
    custodia_id = custodias[-1]["id"]
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/responsables/{custodia_id}/terminar",
        "ua",
        mundo.company_a,
        {"fecha": hoy_de_negocio().isoformat(), "motivo": "Fin de custodia"},
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()

    comision = _completa(mundo, ocupacion)
    r = _activar(mundo, comision, usuario="uab")
    assert r.status_code == 200, r.text
    comision = r.json()
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/comision",
        "ua",
        mundo.company_a,
        {"comision_id": comision["id"], "no_aplica_motivo": None, "motivo": None},
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert detalle["comision_detalle"]["codigo"] == comision["codigo"]

    expediente_id = detalle["id"]
    documento = _doc_real(mundo, mundo.company_a, None, b"%PDF-1.4 prueba", "solicitud.pdf")
    r = _post(
        mundo,
        f"{E}/{expediente_id}/folios",
        "ua",
        mundo.company_a,
        {
            "clase": "SOLICITUD",
            "documento_id": documento,
            "acto_id": None,
            "hito_id": None,
            "reservado": False,
            "motivo_reserva": None,
        },
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    folio1 = [f for f in detalle["folios"] if f["clase"] == "SOLICITUD"][0]
    assert folio1["numero"] == 1
    assert folio1["version_numero"] == 1
    assert folio1["incorporado_por"]

    acto_id = acto_eficaz(mundo, ocupacion["cargo_emisor"])
    r = _post(
        mundo,
        f"{E}/{expediente_id}/folios",
        "ua",
        mundo.company_a,
        {
            "clase": "ACTOS_MOTIVADOS",
            "documento_id": None,
            "acto_id": acto_id,
            "hito_id": None,
            "reservado": False,
            "motivo_reserva": None,
        },
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    folio2 = [f for f in detalle["folios"] if f["clase"] == "ACTOS_MOTIVADOS"][0]
    assert folio2["numero"] == 2
    assert folio2["acto_id"] == acto_id

    fecha_hito = (hoy_de_negocio() + timedelta(days=15)).isoformat()
    r = _post(
        mundo,
        f"{E}/{expediente_id}/hitos",
        "ua",
        mundo.company_a,
        {"nombre": "Hito de prueba", "fuente": None, "fecha_prevista": fecha_hito, "funcionario_id": None},
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    hito_id = detalle["hitos"][-1]["id"]

    r = _post(
        mundo,
        f"{E}/{expediente_id}/actuaciones",
        "ua",
        mundo.company_a,
        _actuacion(
            titulo="Actuación inicial",
            detalle="Detalle de la actuación",
            funcionario_id=funcionario["id"],
            folio_id=folio1["id"],
            hito_id=hito_id,
        ),
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()

    r = _post(
        mundo,
        f"{E}/{expediente_id}/actuaciones",
        "ua",
        mundo.company_a,
        _actuacion(
            clase="DECISION",
            titulo="Decisión",
            resultado="ADJUDICADO",
            funcionario_id=funcionario["id"],
            acto_id=acto_id,
        ),
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()

    r = _post(
        mundo,
        f"{E}/{expediente_id}/hitos/{hito_id}/actualizar",
        "ua",
        mundo.company_a,
        {
            "fecha_prevista": fecha_hito,
            "fecha_real": hoy_de_negocio().isoformat(),
            "no_aplica": False,
            "fuente": None,
            "funcionario_id": None,
            "motivo": "Cumplido",
        },
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    hito = [h for h in detalle["hitos"] if h["id"] == hito_id][0]
    assert hito["estado"] == "CUMPLIDO"

    cronologia = _cron(mundo, expediente_id)
    eventos = cronologia["items"]
    claves = [(e["fecha"], e["secuencia"]) for e in eventos]
    assert claves == sorted(claves)
    clases = {e["clase"] for e in eventos}
    for esperada in [
        "APERTURA",
        "DATOS",
        "RESPONSABLE",
        "COMISION",
        "DOCUMENTO",
        "ACTO",
        "HITO",
        "ACTUACION",
        "DECISION",
    ]:
        assert esperada in clases, clases
    decision = [e for e in eventos if e["clase"] == "DECISION"][0]
    assert decision["resultado"] == "ADJUDICADO"
    assert decision["acto_etiqueta"]
    apertura = [e for e in eventos if e["clase"] == "APERTURA"][0]
    assert apertura["estado_expediente"] == "ABIERTO"
    assert eventos[0]["actor"]

    solo_actos = _cron(mundo, expediente_id, clases="ACTUACION,DECISION")
    assert {e["clase"] for e in solo_actos["items"]} <= {"ACTUACION", "DECISION"}

    cabeceras = mundo.como("ua", mundo.company_a)
    r = mundo.client.get(f"/api/v1{E}", headers=cabeceras, params={"q": detalle["numero"]})
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1
    r = mundo.client.get(
        f"/api/v1{E}", headers=cabeceras, params={"unidad_id": ocupacion["unidad_raiz"], "modalidad": "CONCURSO_ABIERTO"}
    )
    assert r.status_code == 200, r.text
    assert any(item["id"] == expediente_id for item in r.json()["items"])

    r = _post(
        mundo,
        f"{E}/{expediente_id}/cerrar",
        "ua",
        mundo.company_a,
        {"fecha": hoy_de_negocio().isoformat(), "motivo": "Cierre"},
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    cerrado = r.json()
    assert cerrado["status"] == "CERRADO"
    assert cerrado["pendientes"] == []
    assert cerrado["siguiente_accion"] is None

    r = _post(
        mundo,
        f"{E}/{expediente_id}/actuaciones",
        "ua",
        mundo.company_a,
        _actuacion(titulo="Tras cierre", funcionario_id=funcionario["id"]),
        version=cerrado["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_NOT_OPEN"

    apertura = [e for e in _cron(mundo, expediente_id)["items"] if e["clase"] == "APERTURA"][0]
    assert apertura["estado_expediente"] == "ABIERTO"


def test_otro_ente_404(mundo, gobierno, ocupacion):
    detalle = _crear(mundo, ocupacion)
    cabeceras = mundo.como("ub", mundo.company_b)
    r = mundo.client.get(f"/api/v1{E}/{detalle['id']}", headers=cabeceras)
    assert r.status_code == 404, r.text
    funcionario_b = crear_funcionario(mundo, usuario="ub", empresa=mundo.company_b)
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/actuaciones",
        "ub",
        mundo.company_b,
        _actuacion(titulo="Cruzada", funcionario_id=funcionario_b["id"]),
        version=1,
    )
    assert r.status_code == 404, r.text


def test_referencias_de_otro_ente_rechazadas(mundo, gobierno, ocupacion):
    detalle = _crear(mundo, ocupacion)
    funcionario_b = crear_funcionario(mundo, usuario="ub", empresa=mundo.company_b)
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/actuaciones",
        "ua",
        mundo.company_a,
        _actuacion(titulo="Con funcionario ajeno", funcionario_id=funcionario_b["id"]),
        version=detalle["version"],
    )
    assert r.status_code == 422, r.text

    ocupacion_b = dict(ocupacion)
    ocupacion_b["unidad_raiz"] = ocupacion["unidad_b"]
    expediente_b = _crear(mundo, ocupacion_b, usuario="ub", empresa=mundo.company_b, funcionario_id=funcionario_b["id"])
    documento_b = _doc_con_version(
        mundo, mundo.company_b, resource_id=expediente_b["id"], resource_type="GovernmentProcurementFile"
    )
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/folios",
        "ua",
        mundo.company_a,
        {
            "clase": "SOLICITUD",
            "documento_id": documento_b,
            "acto_id": None,
            "hito_id": None,
            "reservado": False,
            "motivo_reserva": None,
        },
        version=detalle["version"],
    )
    assert r.status_code == 422, r.text

    acto_b = acto_eficaz(mundo, ocupacion["cargo_b"], empresa=mundo.company_b)
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/folios",
        "ua",
        mundo.company_a,
        {
            "clase": "ACTOS_MOTIVADOS",
            "documento_id": None,
            "acto_id": acto_b,
            "hito_id": None,
            "reservado": False,
            "motivo_reserva": None,
        },
        version=detalle["version"],
    )
    assert r.status_code == 422, r.text

    cuerpo = {
        "numero": f"EX-{uuid4().hex[:8]}",
        **_base(mundo, ocupacion, crear_funcionario(mundo, usuario="ua")["id"]),
        "unidad_id": ocupacion["unidad_b"],
    }
    r = _post(mundo, E, "ua", mundo.company_a, cuerpo)
    assert r.status_code == 422, r.text

    r = _post(
        mundo,
        f"{E}/{detalle['id']}/comision",
        "ua",
        mundo.company_a,
        {"comision_id": "00000000-0000-0000-0000-000000000000", "no_aplica_motivo": None, "motivo": None},
        version=detalle["version"],
    )
    assert r.status_code == 422, r.text


def test_sin_permiso_denegado(mundo, gobierno, ocupacion):
    detalle = _crear(mundo, ocupacion)
    cuenta_con_permisos(mundo, "lector_exp", [("gobierno_expedientes", "view")])
    cabeceras = mundo.como("lector_exp", mundo.company_a)
    r = mundo.client.get(f"/api/v1{E}/{detalle['id']}", headers=cabeceras)
    assert r.status_code == 200, r.text
    funcionario = crear_funcionario(mundo, usuario="ua")
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/actuaciones",
        "lector_exp",
        mundo.company_a,
        _actuacion(titulo="Sin permiso", funcionario_id=funcionario["id"]),
        version=detalle["version"],
    )
    assert r.status_code == 403, r.text


def test_version_vieja_409(mundo, gobierno, ocupacion):
    detalle = _crear(mundo, ocupacion)
    r = _patch(mundo, detalle, objeto="Objeto modificado")
    assert r.status_code == 200, r.text
    r = _patch(mundo, detalle)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_STALE"


def test_cronologia_no_se_reescribe(mundo, gobierno, ocupacion):
    detalle = _crear(mundo, ocupacion)
    funcionario = crear_funcionario(mundo, usuario="ua")
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/actuaciones",
        "ua",
        mundo.company_a,
        _actuacion(titulo="Original", detalle="Detalle original", funcionario_id=funcionario["id"]),
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    original = [e for e in _cron(mundo, detalle["id"])["items"] if e["titulo"] == "Original"][0]

    r = _post(
        mundo,
        f"{E}/{detalle['id']}/actuaciones",
        "ua",
        mundo.company_a,
        _actuacion(
            titulo="Rectificación",
            funcionario_id=funcionario["id"],
            rectifica_id=original["acto_id"] or original["id"],
            motivo="Corrección de error material",
        ),
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()

    eventos = _cron(mundo, detalle["id"])["items"]
    orig_ev = [e for e in eventos if e.get("titulo") == "Original"][0]
    assert orig_ev["detalle"] == "Detalle original"
    assert orig_ev["rectificada_por_secuencia"] is not None
    rect_ev = [e for e in eventos if e.get("rectifica_secuencia") is not None][0]
    assert rect_ev["rectifica_secuencia"] == orig_ev["secuencia"]

    r = _post(
        mundo,
        f"{E}/{detalle['id']}/actuaciones",
        "ua",
        mundo.company_a,
        _actuacion(
            titulo="Segunda rectificación",
            funcionario_id=funcionario["id"],
            rectifica_id=original["acto_id"] or original["id"],
            motivo="Otra corrección",
        ),
        version=detalle["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_YA_RECTIFICADA"

    r = _post(mundo, f"{E}/{detalle['id']}/actuaciones", "ua", mundo.company_a, _actuacion(titulo="Otra", funcionario_id=funcionario["id"]), version=detalle["version"])
    assert r.status_code == 200, r.text
    detalle = r.json()
    nueva = [e for e in _cron(mundo, detalle["id"])["items"] if e["titulo"] == "Otra"][0]


    r = _post(
        mundo,
        f"{E}/{detalle['id']}/actuaciones",
        "ua",
        mundo.company_a,
        _actuacion(
            titulo="Sin motivo",
            funcionario_id=funcionario["id"],
            rectifica_id=nueva["id"],
            motivo=None,
        ),
        version=detalle["version"],
    )
    assert r.status_code == 422, r.text

    with mundo.factory() as db:
        if db.get_bind().dialect.name == "postgresql":
            with mundo.factory() as db:
                with pytest.raises(DBAPIError):
                    db.execute(text("UPDATE gov_procurement_file_events SET titulo = 'x'"))
                    db.commit()
                db.rollback()


def test_sod_cierre(mundo, gobierno, ocupacion):
    regla = regla_vigente(mundo, proceso="PROC-03", accion_a="PROC03_REGISTRAR", accion_b="PROC03_CERRAR")
    try:
        detalle = _crear(mundo, ocupacion, usuario="ua")
        r = _post(
            mundo,
            f"{E}/{detalle['id']}/cerrar",
            "ua",
            mundo.company_a,
            {"fecha": hoy_de_negocio().isoformat(), "motivo": "Cierre"},
            version=detalle["version"],
        )
        assert r.status_code == 409, r.text
        assert r.json()["code"] == "GOV_SOD_CONFLICT"
        cabeceras = mundo.como("ua", mundo.company_a)
        r = mundo.client.get(f"/api/v1{E}/{detalle['id']}", headers=cabeceras)
        vigente = r.json()
        r = _post(
            mundo,
            f"{E}/{detalle['id']}/cerrar",
            "uab",
            mundo.company_a,
            {"fecha": hoy_de_negocio().isoformat(), "motivo": "Cierre"},
            version=vigente["version"],
        )
        assert r.status_code == 200, r.text
    finally:
        cerrar_regla(mundo, regla)


def test_descartar_solo_sin_contenido(mundo, gobierno, ocupacion):
    detalle = _crear(mundo, ocupacion)
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/descartar",
        "ua",
        mundo.company_a,
        {"motivo": "Descartado sin contenido"},
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "DESCARTADO"

    detalle2 = _crear(mundo, ocupacion)
    documento = _doc_real(mundo, mundo.company_a, None, b"%PDF-1.4 prueba", "solicitud.pdf")
    r = _post(
        mundo,
        f"{E}/{detalle2['id']}/folios",
        "ua",
        mundo.company_a,
        {
            "clase": "SOLICITUD",
            "documento_id": documento,
            "acto_id": None,
            "hito_id": None,
            "reservado": False,
            "motivo_reserva": None,
        },
        version=detalle2["version"],
    )
    assert r.status_code == 200, r.text
    detalle2 = r.json()
    r = _post(
        mundo,
        f"{E}/{detalle2['id']}/descartar",
        "ua",
        mundo.company_a,
        {"motivo": "Con contenido"},
        version=detalle2["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_PROCUREMENT_FILE_CON_CONTENIDO"


def test_hito_exige_motivo(mundo, gobierno, ocupacion):
    detalle = _crear(mundo, ocupacion)
    fecha_hito = (hoy_de_negocio() + timedelta(days=10)).isoformat()
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/hitos",
        "ua",
        mundo.company_a,
        {"nombre": "Hito", "fuente": None, "fecha_prevista": fecha_hito, "funcionario_id": None},
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    hito_id = detalle["hitos"][-1]["id"]

    nueva = (hoy_de_negocio() + timedelta(days=20)).isoformat()
    r = _post(
        mundo,
        f"{E}/{detalle['id']}/hitos/{hito_id}/actualizar",
        "ua",
        mundo.company_a,
        {"fecha_prevista": nueva, "fecha_real": None, "no_aplica": False, "fuente": None, "funcionario_id": None, "motivo": None},
        version=detalle["version"],
    )
    assert r.status_code == 422, r.text

    r = _post(
        mundo,
        f"{E}/{detalle['id']}/hitos/{hito_id}/actualizar",
        "ua",
        mundo.company_a,
        {
            "fecha_prevista": nueva,
            "fecha_real": None,
            "no_aplica": False,
            "fuente": None,
            "funcionario_id": None,
            "motivo": "Reprogramación justificada",
        },
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    titulos = [e.get("titulo") or "" for e in _cron(mundo, detalle["id"])["items"]]
    assert any("Hito reprogramado" in t for t in titulos), titulos
