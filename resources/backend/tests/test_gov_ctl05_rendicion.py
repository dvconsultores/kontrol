import io
import os
from datetime import date, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text

from app.modules.audit.models import AuditEvent
from app.modules.documents.storage import get_storage
from app.modules.government.models import GovernmentRenditionFile, GovernmentRenditionPiece
from app.modules.identity_access.mfa_policy import SENSITIVE, STANDARD, classify
from app.shared.clock import hoy_de_negocio
from tests.org04_ayudantes import crear_funcionario, titular_activo
from tests.org06_guarda import cuenta_con_permisos

pytestmark = pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Requiere PostgreSQL",
)
pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _evento_de_funcionario(mundo, usuario, empresa) -> str:
    funcionario = crear_funcionario(mundo, usuario=usuario, empresa=empresa)
    with mundo.factory() as db:
        evento_id = db.scalars(
            select(AuditEvent.id)
            .where(AuditEvent.company_id == empresa, AuditEvent.entity_id == funcionario["id"])
            .order_by(AuditEvent.event_time.desc())
        ).first()
    return str(evento_id)


def _crear_expediente(mundo, gobierno, ocupacion, denominacion="Cuenta CTL05"):
    asignacion, _ = titular_activo(mundo, ocupacion)
    hoy = hoy_de_negocio()
    cuerpo = {
        "denominacion": denominacion,
        "periodo_desde": date(hoy.year, 1, 1).isoformat(),
        "periodo_hasta": hoy.isoformat(),
        "fecha_corte": hoy.isoformat(),
        "ejercicio": hoy.year,
        "assignment_id": asignacion["id"],
    }
    respuesta = mundo.post("/gobierno/rendicion/expedientes", "ua", mundo.company_a, cuerpo)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _incorporar_eventos(mundo, expediente, n=2):
    ids = []
    for _ in range(n):
        id_evento = _evento_de_funcionario(mundo, "ua", mundo.company_a)
        ids.append(id_evento)
    for id_evento in ids:
        r = mundo.post(
            f"/gobierno/rendicion/expedientes/{expediente['id']}/piezas",
            "ua",
            mundo.company_a,
            {"evento_id": id_evento},
        )
        assert r.status_code == 201, r.text
    return ids


def test_rn01_alta_y_validaciones(mundo, gobierno, ocupacion):
    asignacion, _ = titular_activo(mundo, ocupacion)
    hoy = hoy_de_negocio()
    periodo_desde = date(hoy.year, 1, 1)
    cuerpo = {
        "denominacion": "CTL05 RN01",
        "periodo_desde": periodo_desde.isoformat(),
        "periodo_hasta": hoy.isoformat(),
        "fecha_corte": hoy.isoformat(),
        "ejercicio": hoy.year,
        "assignment_id": asignacion["id"],
    }
    r = mundo.post("/gobierno/rendicion/expedientes", "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    ficha = r.json()
    assert ficha["codigo"].startswith(f"CTA-{hoy.year}-")
    assert ficha["numero_version"] == 1
    assert ficha["estado"] == "EN_FORMACION"
    assert ficha["responsable"]["funcionario"]
    assert ficha["responsable"]["cargo"]
    cuerpo_invalido = dict(cuerpo)
    cuerpo_invalido["fecha_corte"] = (hoy + timedelta(days=1)).isoformat()
    r2 = mundo.post("/gobierno/rendicion/expedientes", "ua", mundo.company_a, cuerpo_invalido)
    assert r2.status_code == 422
    assert r2.json()["code"] == "GOV_RENDITION_INVALID_PERIOD"
    cuerpo_sin_asig = dict(cuerpo)
    cuerpo_sin_asig["assignment_id"] = "00000000-0000-0000-0000-000000000000"
    r3 = mundo.post("/gobierno/rendicion/expedientes", "ua", mundo.company_a, cuerpo_sin_asig)
    assert r3.status_code == 422
    assert r3.json()["code"] == "GOV_RENDITION_RESPONSIBLE_INVALID"


def test_rn02_candidatas_paginadas_y_aisladas(mundo, gobierno, ocupacion):
    for _ in range(3):
        crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)
    crear_funcionario(mundo, usuario="ub", empresa=mundo.company_b)
    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN02")
    r = mundo.get(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/candidatas?por_pagina=2&pagina=1",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200, r.text
    datos = r.json()
    assert len(datos["items"]) == 2
    assert datos["total"] >= 3
    with mundo.factory() as sesion:
        for item in datos["items"]:
            evento = sesion.scalar(select(AuditEvent).where(AuditEvent.id == item["evento_id"]))
            assert evento is not None
            assert evento.company_id == mundo.company_a
    r2 = mundo.get(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/candidatas?por_pagina=51",
        "ua",
        mundo.company_a,
    )
    assert r2.status_code == 422
    assert r2.json()["code"] == "GOV_RENDITION_INVALID_PAGE"


def test_rn03_incorporar_duplicado_ajeno_inexistente(mundo, gobierno, ocupacion):
    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN03")
    id_evento = _evento_de_funcionario(mundo, "ua", mundo.company_a)
    r = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/piezas",
        "ua",
        mundo.company_a,
        {"evento_id": id_evento},
    )
    assert r.status_code == 201, r.text
    pieza = r.json()
    assert pieza["proceso"] == "ORG-04"
    assert pieza["referencia"]
    assert len(pieza["huella"]) == 64
    r2 = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/piezas",
        "ua",
        mundo.company_a,
        {"evento_id": id_evento},
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "GOV_RENDITION_PIECE_DUPLICATE"
    id_evento_b = _evento_de_funcionario(mundo, "ub", mundo.company_b)
    r3 = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/piezas",
        "ua",
        mundo.company_a,
        {"evento_id": id_evento_b},
    )
    assert r3.status_code == 404
    assert r3.json()["code"] == "GOV_RENDITION_EVENT_NOT_FOUND"
    r4 = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/piezas",
        "ua",
        mundo.company_a,
        {"evento_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r4.status_code == 404
    assert r4.json()["code"] == "GOV_RENDITION_EVENT_NOT_FOUND"


def test_rn04_formar_reporte_pdf_csv(mundo, gobierno, ocupacion):
    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN04")
    r0 = mundo.get(f"/gobierno/rendicion/expedientes/{expediente['id']}/reporte", "ua", mundo.company_a)
    assert r0.status_code == 200
    assert r0.json()["provisional"] is True
    vacio = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN04 VACIO")
    r_vacio = mundo.post(f"/gobierno/rendicion/expedientes/{vacio['id']}/formar", "ua", mundo.company_a, {})
    assert r_vacio.status_code == 422
    assert r_vacio.json()["code"] == "GOV_RENDITION_EMPTY"
    _incorporar_eventos(mundo, expediente, 2)
    r = mundo.post(f"/gobierno/rendicion/expedientes/{expediente['id']}/formar", "ua", mundo.company_a, {})
    assert r.status_code == 200, r.text
    ficha = r.json()
    assert ficha["estado"] == "FORMADA"
    assert [p["ordinal"] for p in ficha["piezas"]] == [1, 2]
    assert len(ficha["snapshot_sha256"]) == 64
    r_pdf = mundo.client.get(
        f"/api/v1/gobierno/rendicion/expedientes/{expediente['id']}/reporte.pdf",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r_pdf.status_code == 200
    assert r_pdf.content.startswith(b"%PDF")
    import hashlib

    assert hashlib.sha256(r_pdf.content).hexdigest() == ficha["informe"]["sha256"]
    r_csv = mundo.client.get(
        f"/api/v1/gobierno/rendicion/expedientes/{expediente['id']}/indice.csv",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r_csv.status_code == 200
    lineas = r_csv.content.decode("utf-8").strip().splitlines()
    assert len(lineas) == 3
    r_reporte = mundo.get(f"/gobierno/rendicion/expedientes/{expediente['id']}/reporte", "ua", mundo.company_a)
    reporte = r_reporte.json()
    fila_piezas = next(fila for fila in reporte["resumen"] if fila["concepto"] == "Piezas incluidas")
    assert fila_piezas["resultado"] == 2
    for fila in reporte["resumen"]:
        assert set(fila.keys()) == {"concepto", "fuente", "filtro", "periodo", "conjunto", "regla", "resultado"}


def test_rn05_snapshot_no_cambia(mundo, gobierno, ocupacion):
    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN05")
    _incorporar_eventos(mundo, expediente, 1)
    mundo.post(f"/gobierno/rendicion/expedientes/{expediente['id']}/formar", "ua", mundo.company_a, {})
    antes = mundo.get(f"/gobierno/rendicion/expedientes/{expediente['id']}/reporte", "ua", mundo.company_a).json()
    crear_funcionario(mundo, usuario="ua", empresa=mundo.company_a)
    despues = mundo.get(f"/gobierno/rendicion/expedientes/{expediente['id']}/reporte", "ua", mundo.company_a).json()
    assert antes == despues
    id_evento = _evento_de_funcionario(mundo, "ua", mundo.company_a)
    r = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/piezas",
        "ua",
        mundo.company_a,
        {"evento_id": id_evento},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_RENDITION_STATE"
    pieza_id = antes["piezas"][0]["id"]
    r2 = mundo.client.request(
        "DELETE",
        f"/api/v1/gobierno/rendicion/expedientes/{expediente['id']}/piezas/{pieza_id}",
        headers=mundo.como("ua", mundo.company_a),
    )
    assert r2.status_code == 409
    r3 = mundo.client.put(
        f"/api/v1/gobierno/rendicion/expedientes/{expediente['id']}",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(expediente["version"])},
        json={
            "denominacion": "Cambio",
            "periodo_desde": date(hoy_de_negocio().year, 1, 1).isoformat(),
            "periodo_hasta": hoy_de_negocio().isoformat(),
            "fecha_corte": hoy_de_negocio().isoformat(),
            "assignment_id": expediente["responsable"]["asignacion_codigo"],
        },
    )
    assert r3.status_code == 409
    assert r3.json()["code"] == "GOV_RENDITION_STATE"


def test_rn06_disparadores_postgresql(mundo, gobierno, ocupacion):
    from sqlalchemy.exc import DBAPIError

    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN06")
    _incorporar_eventos(mundo, expediente, 1)
    mundo.post(f"/gobierno/rendicion/expedientes/{expediente['id']}/formar", "ua", mundo.company_a, {})
    with mundo.factory() as sesion:
        pieza_id = sesion.scalar(select(GovernmentRenditionPiece.id).where(GovernmentRenditionPiece.file_id == expediente["id"]))
        with pytest.raises(DBAPIError):
            sesion.execute(
                text("UPDATE gov_rendition_pieces SET referencia = 'x' WHERE id = :id"),
                {"id": pieza_id},
            )
            sesion.commit()
        sesion.rollback()
        file_id = sesion.scalar(select(GovernmentRenditionFile.id).where(GovernmentRenditionFile.id == expediente["id"]))
        with pytest.raises(DBAPIError):
            sesion.execute(
                text("UPDATE gov_rendition_files SET snapshot = '{}'::json WHERE id = :id"),
                {"id": file_id},
            )
            sesion.commit()
        sesion.rollback()
        sesion.execute(
            text("UPDATE gov_rendition_files SET estado = 'FORMADA' WHERE id = :id"),
            {"id": file_id},
        )
        sesion.rollback()


def test_rn07_integridad(mundo, gobierno, ocupacion):
    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN07")
    _incorporar_eventos(mundo, expediente, 1)
    mundo.post(f"/gobierno/rendicion/expedientes/{expediente['id']}/formar", "ua", mundo.company_a, {})
    r = mundo.get(f"/gobierno/rendicion/expedientes/{expediente['id']}/integridad", "ua", mundo.company_a)
    assert r.status_code == 200
    datos = r.json()
    assert datos["estado"] == "VALIDO"
    assert datos["snapshot_ok"] is True
    assert datos["informe_ok"] is True
    with mundo.factory() as sesion:
        f = sesion.scalar(select(GovernmentRenditionFile).where(GovernmentRenditionFile.id == expediente["id"]))
        key = f.informe_storage_key
    get_storage().put(key, io.BytesIO(b"alterado"))
    r2 = mundo.get(f"/gobierno/rendicion/expedientes/{expediente['id']}/integridad", "ua", mundo.company_a)
    datos2 = r2.json()
    assert datos2["estado"] == "INCOMPLETO"
    assert datos2["informe_ok"] is False


def test_rn08_rendicion_calificacion_makerchecker(mundo, gobierno, ocupacion):
    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN08")
    _incorporar_eventos(mundo, expediente, 1)
    mundo.post(f"/gobierno/rendicion/expedientes/{expediente['id']}/formar", "ua", mundo.company_a, {})
    r = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/participacion",
        "ua",
        mundo.company_a,
        {"fecha": hoy_de_negocio().isoformat(), "oficio": "Oficio 123"},
    )
    assert r.status_code == 200, r.text
    ficha = r.json()
    assert ficha["estado"] == "PARTICIPADA"
    assert ficha["participacion"]["vence"]
    assert ficha["participacion"]["en_plazo"] is True
    r2 = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/calificacion",
        "ua",
        mundo.company_a,
        {
            "resultado": "CONFORME",
            "organo": "Órgano de control",
            "informe_numero": "INF-1",
            "informe_fecha": hoy_de_negocio().isoformat(),
        },
    )
    assert r2.status_code == 403
    assert r2.json()["code"] == "GOV_RENDITION_SAME_ACTOR"
    nombre_calificador = f"calificador_{uuid4().hex[:8]}"
    cuenta_con_permisos(
        mundo,
        nombre_calificador,
        [("gobierno_rendicion", "view"), ("gobierno_rendicion", "qualify")],
    )
    r3 = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/calificacion",
        nombre_calificador,
        mundo.company_a,
        {
            "resultado": "CONFORME",
            "organo": "Órgano de control",
            "informe_numero": "INF-2",
            "informe_fecha": hoy_de_negocio().isoformat(),
        },
    )
    assert r3.status_code == 200, r3.text
    r4 = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/fenecimiento",
        nombre_calificador,
        mundo.company_a,
        {"auto_numero": "AUTO-1", "auto_fecha": hoy_de_negocio().isoformat()},
    )
    assert r4.status_code == 200
    assert r4.json()["estado"] == "FENECIDA"


def test_rn09_nueva_version(mundo, gobierno, ocupacion):
    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN09")
    _incorporar_eventos(mundo, expediente, 1)
    mundo.post(f"/gobierno/rendicion/expedientes/{expediente['id']}/formar", "ua", mundo.company_a, {})
    r_corto = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/nueva-version",
        "ua",
        mundo.company_a,
        {"motivo": "corto"},
    )
    assert r_corto.status_code == 422
    assert r_corto.json()["code"] == "GOV_RENDITION_REASON_REQUIRED"
    r = mundo.post(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/nueva-version",
        "ua",
        mundo.company_a,
        {"motivo": "Motivo suficientemente largo para la nueva versión."},
    )
    assert r.status_code == 201, r.text
    ficha_v2 = r.json()
    assert ficha_v2["numero_version"] == 2
    assert ficha_v2["estado"] == "EN_FORMACION"
    ficha_formada = mundo.get(
        f"/gobierno/rendicion/expedientes/{expediente['id']}", "ua", mundo.company_a
    ).json()
    ficha_v2_leida = mundo.get(
        f"/gobierno/rendicion/expedientes/{ficha_v2['id']}", "ua", mundo.company_a
    ).json()
    assert len(ficha_v2_leida["piezas"]) == len(ficha_formada["piezas"])
    assert [p["ordinal"] for p in ficha_v2_leida["piezas"]] == list(range(1, len(ficha_v2_leida["piezas"]) + 1))
    with mundo.factory() as db:
        assert all(o is None for o in db.scalars(select(GovernmentRenditionPiece.ordinal)
        .where(GovernmentRenditionPiece.file_id == ficha_v2_leida["id"])))
    ficha_v1 = mundo.get(f"/gobierno/rendicion/expedientes/{expediente['id']}", "ua", mundo.company_a).json()
    assert ficha_v1["estado"] == "SUSTITUIDA"
    reporte_v1 = mundo.get(f"/gobierno/rendicion/expedientes/{expediente['id']}/reporte", "ua", mundo.company_a).json()
    assert reporte_v1["snapshot_sha256"] == ficha_formada["snapshot_sha256"]
    historial = mundo.get(
        f"/gobierno/rendicion/expedientes/{ficha_v2['id']}/historial", "ua", mundo.company_a
    ).json()
    acciones = [item["accion"] for item in historial["items"]]
    assert "GOV_RENDITION_FILE_CREATED" in acciones
    assert "GOV_RENDITION_FILE_FORMED" in acciones


def test_rn10_aislamiento_y_permisos(mundo, gobierno, ocupacion):
    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN10")
    r = mundo.get(f"/gobierno/rendicion/expedientes/{expediente['id']}", "ub", mundo.company_b)
    assert r.status_code == 404
    listado = mundo.get("/gobierno/rendicion/expedientes", "ub", mundo.company_b).json()
    assert expediente["id"] not in [item["id"] for item in listado["items"]]
    from app.modules.setup.api import CATALOGO_DE_PERMISOS

    assert "gobierno_rendicion" in CATALOGO_DE_PERMISOS
    assert set(CATALOGO_DE_PERMISOS["gobierno_rendicion"]) == {"view", "form", "qualify"}
    assert classify(["gobierno_rendicion:form"]) == SENSITIVE
    assert classify(["gobierno_rendicion:qualify"]) == SENSITIVE
    assert classify(["gobierno_rendicion:view"]) == STANDARD


def test_rn11_auditoria_bitacora(mundo, gobierno, ocupacion):
    expediente = _crear_expediente(mundo, gobierno, ocupacion, "CTL05 RN11")
    _incorporar_eventos(mundo, expediente, 1)
    mundo.post(f"/gobierno/rendicion/expedientes/{expediente['id']}/formar", "ua", mundo.company_a, {})
    with mundo.factory() as sesion:
        eventos = sesion.scalars(
            select(AuditEvent)
            .where(AuditEvent.entity_id == expediente["id"], AuditEvent.company_id == mundo.company_a)
            .order_by(AuditEvent.event_time)
        ).all()
        acciones = [e.action for e in eventos]
        assert "GOV_RENDITION_FILE_CREATED" in acciones
        assert "GOV_RENDITION_FILE_PIECE_ADDED" in acciones
        assert "GOV_RENDITION_FILE_FORMED" in acciones
    historial = mundo.get(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/historial", "ua", mundo.company_a
    ).json()
    acciones_hist = [item["accion"] for item in historial["items"]]
    assert "GOV_RENDITION_FILE_CREATED" in acciones_hist
    assert "GOV_RENDITION_FILE_PIECE_ADDED" in acciones_hist
    assert "GOV_RENDITION_FILE_FORMED" in acciones_hist
    candidatas = mundo.get(
        f"/gobierno/rendicion/expedientes/{expediente['id']}/candidatas", "ua", mundo.company_a
    ).json()
    assert all(item.get("proceso") != "GovernmentRenditionFile" for item in candidatas["items"])
