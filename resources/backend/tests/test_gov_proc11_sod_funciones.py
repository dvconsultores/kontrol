"""PROC-11 · Funciones incompatibles del procedimiento de contratación (GOV-PROC-017).

Se ejecuta sobre PostgreSQL: el aislamiento por ente, el bloqueo y el índice de no solapamiento son parte de la
compuerta. Ver `KONTROL_TEST_DB_URL`.
"""

import csv
import io
import os
from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentSoDRoleRuleHistory
from app.shared.clock import hoy_de_negocio
from tests.org06_guarda import cuenta_con_permisos
from tests.proc08_ayudantes import evaluacion_concluida
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_proc03_expedientes import E
from tests.test_gov_proc06_ofertas import _recibir

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

S = "/gobierno/sod/funciones"
HOY = hoy_de_negocio()
ONLY_PG = pytest.mark.skipif(
    "postgresql" not in os.environ.get("KONTROL_TEST_DB_URL", ""),
    reason="PROC-11 se verifica sobre PostgreSQL",
)


@pytest.fixture(autouse=True)
def _cerrar_reglas_al_terminar(mundo):
    """Cada prueba deja su matriz cerrada: la base de prueba se comparte por módulo y el par vigente es único."""
    yield
    from datetime import UTC, datetime

    from sqlalchemy import update

    from app.modules.government.models import GovernmentSoDRoleRule

    with mundo.factory() as session:
        session.execute(
            update(GovernmentSoDRoleRule)
            .where(GovernmentSoDRoleRule.estado != "CERRADA")
            .values(
                estado="CERRADA",
                cerrada_por="00000000-0000-0000-0000-000000000000",
                cerrada_en=datetime.now(UTC),
                motivo_cierre="Limpieza de la prueba",
            )
        )
        session.commit()


def cuerpo_regla(**cambios) -> dict:
    cuerpo = {
        "nombre": "Receptor no evalúa",
        "descripcion": "Quien recibe las ofertas no puede evaluarlas: perdería la confidencialidad del sobre.",
        "rol_a": "RECEPTOR",
        "rol_b": "EVALUADOR",
        "fundamento": "N20 y N23: segregación de funciones y prevención del conflicto de interés.",
        "vigente_desde": HOY.isoformat(),
    }
    cuerpo.update(cambios)
    return cuerpo


def crear_regla(mundo, usuario="ua", empresa=None, **cambios) -> dict:
    empresa = empresa or mundo.company_a
    r = _post(mundo, f"{S}/reglas", usuario, empresa, cuerpo_regla(**cambios))
    assert r.status_code == 201, r.text
    return r.json()


def activar_regla(mundo, regla: dict, usuario="ua", empresa=None, **cambios) -> dict:
    empresa = empresa or mundo.company_a
    r = _post(mundo, f"{S}/reglas/{regla['id']}/activar", usuario, empresa, cambios or None,
              version=regla["version"])
    assert r.status_code == 200, r.text
    return r.json()


@ONLY_PG
def test_catalogo_publica_pagador_no_disponible(mundo, gobierno):
    r = mundo.get(S, "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    funciones = {f["codigo"]: f for f in r.json()["funciones"]}
    assert set(funciones) == {"SOLICITANTE", "RECEPTOR", "EVALUADOR", "ADJUDICADOR", "PAGADOR"}
    assert funciones["PAGADOR"]["disponible"] is False
    assert "GOV-TRE-004" in funciones["PAGADOR"]["requisito_habilitante"]
    assert all(funciones[codigo]["disponible"] for codigo in ("SOLICITANTE", "RECEPTOR", "EVALUADOR", "ADJUDICADOR"))


@ONLY_PG
def test_regla_vida_completa(mundo, gobierno):
    regla = crear_regla(mundo)
    assert regla["estado"] == "BORRADOR"
    assert regla["codigo"] == "RF-0001"
    assert regla["en_vigor"] is False

    activa = activar_regla(mundo, regla)
    assert activa["estado"] == "VIGENTE"
    assert activa["en_vigor"] is True
    assert activa["version"] == regla["version"] + 1

    listado = mundo.get(f"{S}/reglas?estado=VIGENTE", "ua", mundo.company_a)
    assert listado.status_code == 200, listado.text
    assert [item["codigo"] for item in listado.json()["items"]] == ["RF-0001"]

    r = _post(mundo, f"{S}/reglas/{activa['id']}/cerrar", "ua", mundo.company_a,
              {"motivo": "La matriz institucional cambió de criterio."}, version=activa["version"])
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "CERRADA"
    assert r.json()["en_vigor"] is False

    with mundo.factory() as session:
        tipos = session.execute(
            select(GovernmentSoDRoleRuleHistory.tipo).where(
                GovernmentSoDRoleRuleHistory.rule_id == activa["id"]
            ).order_by(GovernmentSoDRoleRuleHistory.created_at)
        ).scalars().all()
        assert tipos == ["CREADA", "ACTIVADA", "CERRADA"]
        acciones = session.execute(
            select(AuditEvent.action).where(
                AuditEvent.entity_type == "GovernmentSoDRoleRule",
                AuditEvent.entity_id == activa["id"],
            )
        ).scalars().all()
    assert {"GOV_SOD_ROLE_RULE_CREATED", "GOV_SOD_ROLE_RULE_ACTIVATED", "GOV_SOD_ROLE_RULE_CLOSED"} <= set(acciones)


@ONLY_PG
def test_regla_sin_fecha_arranca_hoy(mundo, gobierno):
    cuerpo = cuerpo_regla()
    cuerpo.pop("vigente_desde")
    r = _post(mundo, f"{S}/reglas", "ua", mundo.company_a, cuerpo)
    assert r.status_code == 201, r.text
    assert r.json()["vigente_desde"] == HOY.isoformat()


@ONLY_PG
def test_regla_invalida_422(mundo, gobierno):
    r = _post(mundo, f"{S}/reglas", "ua", mundo.company_a,
              cuerpo_regla(rol_b="RECEPTOR"))
    assert r.status_code == 422, r.text

    r = _post(mundo, f"{S}/reglas", "ua", mundo.company_a,
              cuerpo_regla(rol_a="RECEPTOR", rol_b="PAGADOR"))
    assert r.status_code == 422, r.text
    assert "GOV-TRE-004" in r.text or "no está disponible" in r.text


@ONLY_PG
def test_par_vigente_no_se_solapa(mundo, gobierno):
    activar_regla(mundo, crear_regla(mundo))
    segunda = crear_regla(mundo, nombre="Otra redacción", descripcion="Otra redacción del mismo par declarado.")
    r = _post(mundo, f"{S}/reglas/{segunda['id']}/activar", "ua", mundo.company_a, None, version=segunda["version"])
    assert r.status_code == 409, r.text
    assert "GOV_SOD_ROLE_RULE_OVERLAP" in r.text


@ONLY_PG
def test_bloqueo_al_asumir_funcion_incompatible(mundo, gobierno, ocupacion):
    """SC-002: quien recibió una oferta no puede abrir y evaluar la misma oferta."""
    from datetime import UTC, datetime

    from tests.test_gov_doc08_paquete import _doc_real
    from tests.test_gov_proc07_evaluacion import _preparar

    exp, comision = _preparar(mundo, ocupacion)
    doc = _doc_real(mundo, mundo.company_a, None, b"oferta sellada", "oferta")
    mundo.post(f"/documentos/{doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    oferta = _recibir(mundo, exp, "ua", mundo.company_a, [doc])
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/ofertas/concluir", "ua", mundo.company_a, {"motivo": None},
              version=exp["version"])
    assert r.status_code == 200, r.text
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()

    activar_regla(mundo, crear_regla(mundo))

    acta_doc = _doc_real(mundo, mundo.company_a, None, b"acta de apertura", "acta")
    mundo.post(f"/documentos/{acta_doc}/vinculos", "ua", mundo.company_a, {
        "resource_type": "GovernmentProcurementFile",
        "resource_id": exp["id"],
    })
    exp = mundo.get(f"{E}/{exp['id']}", "ua", mundo.company_a).json()
    r = _post(mundo, f"{E}/{exp['id']}/evaluacion/aperturas", "ua", mundo.company_a, {
        "abierta_en": datetime.now(UTC).isoformat(),
        "oferta_ids": [oferta["id"]],
        "miembro_ids": [m["id"] for m in comision["miembros"]],
        "acta_documento_id": acta_doc,
        "observaciones": "Apertura",
    }, version=exp["version"])
    assert r.status_code == 409, r.text
    assert "GOV_SOD_ROLE_CONFLICT" in r.text
    assert "Receptor de ofertas" in r.text

    with mundo.factory() as session:
        eventos = session.execute(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_SOD_ROLE_CONFLICT_BLOCKED",
                AuditEvent.entity_id == exp["id"],
            )
        ).scalars().all()
    assert eventos, "el intento bloqueado debe quedar auditado"


@ONLY_PG
def test_conflicto_previo_visible_por_periodo(mundo, gobierno, ocupacion):
    """SC-003: un conflicto producido antes de declarar la regla aparece con su evidencia."""
    exp, _comision, _ofertas = evaluacion_concluida(mundo, ocupacion)
    activar_regla(mundo, crear_regla(mundo))

    r = mundo.get(f"{S}/conflictos", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    propios = [item for item in cuerpo["items"] if item["expediente_id"] == exp["id"]]
    assert propios, cuerpo
    conflicto = propios[0]
    assert conflicto["regla_codigo"].startswith("RF-")
    assert {conflicto["rol_a"], conflicto["rol_b"]} == {"RECEPTOR", "EVALUADOR"}
    assert len(conflicto["evidencia"]) == 2
    assert {item["rol"] for item in conflicto["evidencia"]} == {"RECEPTOR", "EVALUADOR"}
    assert conflicto["actor_nombre"]


@ONLY_PG
def test_periodo_invalido_422(mundo, gobierno):
    r = mundo.get(f"{S}/conflictos?desde=2026-12-31&hasta=2026-01-01", "ua", mundo.company_a)
    assert r.status_code == 422, r.text
    assert "INVALID_DATE_RANGE" in r.text


@ONLY_PG
def test_exportacion_csv_deja_evento(mundo, gobierno, ocupacion):
    exp, _comision, _ofertas = evaluacion_concluida(mundo, ocupacion)
    activar_regla(mundo, crear_regla(mundo))
    desde = (HOY - timedelta(days=1)).isoformat()
    hasta = (HOY + timedelta(days=1)).isoformat()
    r = mundo.get(f"{S}/conflictos.csv?desde={desde}&hasta={hasta}", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers["content-type"]
    assert "funciones-incompatibles-" in r.headers["content-disposition"]
    filas = list(csv.reader(io.StringIO(r.content.decode("utf-8"))))
    assert filas[0][0] == "Expediente"
    assert any(fila[0] == exp["numero"] for fila in filas[1:])

    with mundo.factory() as session:
        evento = session.execute(
            select(AuditEvent).where(AuditEvent.action == "GOV_SOD_ROLE_CONFLICTS_EXPORTED")
        ).scalars().first()
    assert evento is not None
    assert evento.after["filas"] >= 1


@ONLY_PG
def test_otro_ente_no_ve_ni_consulta(mundo, gobierno):
    regla = crear_regla(mundo)
    r = mundo.get(f"{S}/reglas/{regla['id']}", "ub", mundo.company_b)
    assert r.status_code == 404, r.text
    listado = mundo.get(f"{S}/reglas", "ub", mundo.company_b)
    assert listado.status_code == 200
    assert listado.json()["items"] == []


@ONLY_PG
def test_sin_capacidad_403(mundo, gobierno):
    cuenta_con_permisos(mundo, "sin_so_d", [])
    assert mundo.get(S, "sin_so_d", mundo.company_a).status_code == 403
    assert mundo.get(f"{S}/conflictos", "sin_so_d", mundo.company_a).status_code == 403
    assert _post(mundo, f"{S}/reglas", "sin_so_d", mundo.company_a, cuerpo_regla()).status_code == 403


@ONLY_PG
def test_historia_inmutable(mundo, gobierno):
    regla = activar_regla(mundo, crear_regla(mundo))
    with mundo.factory() as session:
        from app.modules.government.models import GovernmentSoDRoleRuleHistory as H

        fila = session.execute(select(H).where(H.rule_id == regla["id"])).scalars().first()
        session.delete(fila)
        with pytest.raises(DBAPIError):
            session.flush()
