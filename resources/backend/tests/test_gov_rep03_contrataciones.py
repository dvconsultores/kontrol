import os
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentProcurementFile, GovernmentProcurementFileMilestone
from app.shared.clock import hoy_de_negocio
from tests.n9_resource_seeds import sembrar
from tests.org06_guarda import cuenta_con_permisos
from tests.proc08_ayudantes import acto_decision, cargo_contrataciones, evaluacion_concluida, recomendar
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc03_expedientes import E

pytestmark = pytest.mark.skipif(not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"), reason="Requiere PostgreSQL")
pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")
R = "/gobierno/contrataciones/reporte"


def _sembrar_despues(mundo, company_id: str) -> tuple[str, GovernmentProcurementFile]:
    with mundo.factory() as db:
        fid = sembrar(db, "GovernmentProcurementFile", company_id, uuid4().hex)
        db.commit()
        expediente = db.get(GovernmentProcurementFile, fid)
        assert expediente is not None
        return fid, expediente


def _sembrar_hito(mundo, company_id: str, file_id: str, nombre: str, fecha_prevista, estado: str, fecha_real=None) -> None:
    with mundo.factory() as db:
        db.add(
            GovernmentProcurementFileMilestone(
                company_id=company_id,
                file_id=file_id,
                nombre=nombre,
                fecha_prevista=fecha_prevista,
                fecha_real=fecha_real,
                estado=estado,
            )
        )
        db.commit()


def _pedir(mundo, usuario: str, empresa: str, ruta: str = R):
    return mundo.get(ruta, usuario, empresa)


def test_rc01_estructura_y_periodo_por_defecto(mundo, gobierno, ocupacion):
    r = _pedir(mundo, "ua", mundo.company_a)
    assert r.status_code == 200
    data = r.json()

    assert set(data.keys()) >= {
        "periodo",
        "generado_en",
        "totales",
        "por_modalidad",
        "por_estado",
        "por_tipo",
        "por_unidad",
        "resultados",
        "proveedores",
        "tiempos",
        "desviaciones",
        "monto",
    }
    assert data["periodo"]["desde"] == f"{hoy_de_negocio().year}-01-01"
    assert data["periodo"]["hasta"] == hoy_de_negocio().isoformat()
    assert data["monto"]["disponible"] is False
    assert data["monto"]["motivo"] == "No declarado: ninguna oferta adjudicada del periodo tiene monto declarado."
    assert data["monto"]["por_moneda"] == []
    assert data["monto"]["adjudicaciones_con_monto"] == 0
    assert [m["codigo"] for m in data["por_modalidad"]] == ["CONCURSO_ABIERTO", "CONCURSO_CERRADO", "CONSULTA_PRECIOS", "CONTRATACION_DIRECTA", None]
    assert [e["codigo"] for e in data["por_estado"]] == ["ABIERTO", "CERRADO", "DESCARTADO"]
    assert [t["codigo"] for t in data["por_tipo"]] == ["BIENES", "SERVICIOS", "OBRAS"]
    assert [res["codigo"] for res in data["resultados"]] == ["ADJUDICADA", "DESIERTA", "TERMINADA", "NULIDAD", "SIN_DECISION"]


def test_rc02_expediente_sembrado_y_periodo_antiguo(mundo, gobierno, ocupacion):
    fid, _ = _sembrar_despues(mundo, mundo.company_a)
    unidad_id_local = None
    with mundo.factory() as db:
        exp = db.get(GovernmentProcurementFile, fid)
        assert exp is not None
        exp.fecha_inicio = hoy_de_negocio()
        unidad_id_local = str(exp.unidad_id) if exp.unidad_id is not None else None
        db.commit()

    r = _pedir(mundo, "ua", mundo.company_a)
    assert r.status_code == 200
    data = r.json()
    assert data["totales"]["expedientes"] >= 1
    assert any(u["unidad_id"] == unidad_id_local and u["total"] >= 1 for u in data["por_unidad"])

    fecha_antigua = hoy_de_negocio() - timedelta(days=400)
    r = mundo.get(f"{R}?desde={fecha_antigua.isoformat()}&hasta={fecha_antigua.isoformat()}", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["totales"]["expedientes"] == 0


def test_rc03_flujo_real_de_adjudicacion(mundo, gobierno, ocupacion):
    exp, comision, ofertas = evaluacion_concluida(mundo, ocupacion)
    estado = recomendar(
        mundo,
        exp,
        comision,
        ofertas,
        opciones=[{"posicion": 1, "offer_id": ofertas[0]["id"]}, {"posicion": 2, "offer_id": ofertas[1]["id"]}],
    )
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    cargo_id = cargo_contrataciones(mundo, ocupacion)
    acto = acto_decision(mundo, cargo_id)
    r = _post(mundo, f"{E}/{exp['id']}/decision/decisiones", "ua", mundo.company_a,
              {"resultado": "ADJUDICADA", "recomendacion_id": estado["recomendacion_vigente"]["id"], "acto_id": acto["id"],
               "oferta_id": ofertas[0]["id"], "motivacion": "Adjudicación de prueba"}, version=exp["version"])
    assert r.status_code == 201, r.text

    respuesta = _pedir(mundo, "ua", mundo.company_a)
    assert respuesta.status_code == 200
    data = respuesta.json()
    proveedor = next(p for p in data["proveedores"] if p["documento"] == ofertas[0]["oferente_documento"])
    assert proveedor["adjudicaciones"] >= 1
    assert proveedor["ofertas"] >= 1
    assert next(item for item in data["resultados"] if item["codigo"] == "ADJUDICADA")["total"] >= 1
    assert data["tiempos"]["global"]["inicio_recepcion"] is not None


def test_rc04_hitos_con_desviacion(mundo, gobierno, ocupacion):
    fid, _ = _sembrar_despues(mundo, mundo.company_a)
    with mundo.factory() as db:
        exp = db.get(GovernmentProcurementFile, fid)
        assert exp is not None
        exp.fecha_inicio = hoy_de_negocio()
        db.commit()

    _sembrar_hito(mundo, mundo.company_a, fid, "Vencido", hoy_de_negocio() - timedelta(days=5), "PREVISTO")
    _sembrar_hito(mundo, mundo.company_a, fid, "Atrasado", hoy_de_negocio() - timedelta(days=2), "CUMPLIDO", hoy_de_negocio())
    _sembrar_hito(mundo, mundo.company_a, fid, "A tiempo", hoy_de_negocio() - timedelta(days=1), "CUMPLIDO", hoy_de_negocio() - timedelta(days=1))

    r = _pedir(mundo, "ua", mundo.company_a)
    assert r.status_code == 200
    desviaciones = r.json()["desviaciones"]
    assert desviaciones["vencidos"] >= 1
    assert desviaciones["con_atraso"] >= 1
    assert desviaciones["a_tiempo"] >= 1
    vencido = next(h for h in desviaciones["hitos"] if h["estado"] == "VENCIDO")
    assert vencido["dias"] == 5
    atrasado = next(h for h in desviaciones["hitos"] if h["estado"] == "CON_ATRASO")
    assert atrasado["dias"] == 2


def test_rc05_permisos(mundo, gobierno, ocupacion):
    cuenta_con_permisos(mundo, "sin_permiso_gobierno", [("gobierno_cargos", "view")])
    r = mundo.get(R, "sin_permiso_gobierno", mundo.company_a)
    assert r.status_code == 403


def test_rc06_aislamiento(mundo, gobierno, ocupacion):
    fid, _ = _sembrar_despues(mundo, mundo.company_a)
    with mundo.factory() as db:
        exp = db.get(GovernmentProcurementFile, fid)
        assert exp is not None
        exp.fecha_inicio = hoy_de_negocio()
        db.commit()

    r = _pedir(mundo, "ub", mundo.company_b)
    assert r.status_code == 200
    data = r.json()
    assert data["totales"]["expedientes"] == 0
    assert data["proveedores"] == []


def test_rc07_csv_y_auditoria(mundo, gobierno, ocupacion):
    fid, _ = _sembrar_despues(mundo, mundo.company_a)
    with mundo.factory() as db:
        exp = db.get(GovernmentProcurementFile, fid)
        assert exp is not None
        exp.fecha_inicio = hoy_de_negocio()
        db.commit()

    r = mundo.get(f"{R}.csv", "ua", mundo.company_a)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    texto = r.text
    assert "Hitos con desviación" in texto
    assert "Monto" in texto

    with mundo.factory() as db:
        evento = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_PROCUREMENT_REPORT_EXPORTED",
                AuditEvent.company_id == mundo.company_a,
            )
        ).first()
        assert evento is not None
        assert evento.after["filas"] >= 1
        assert "desde" in evento.after["filtros"]
        assert "hasta" in evento.after["filtros"]


def test_rc08_desde_posterior_a_hasta(mundo, gobierno, ocupacion):
    r = mundo.get(f"{R}?desde=2024-12-31&hasta=2024-01-01", "ua", mundo.company_a)
    assert r.status_code == 422
    data = r.json()
    assert data["code"] == "INVALID_DATE_RANGE"
