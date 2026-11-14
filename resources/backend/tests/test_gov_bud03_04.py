"""BUD-03 / BUD-04 · Plan operativo y fuentes de financiamiento (reintento 1)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentBudgetYearFoundation, GovernmentEntity, GovernmentStructure, GovernmentUnit
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud01_ejercicio import (
    ONLY_PG,
    P,
    _aprobar,
    _completo,
    _crear,
    _delete,
    _documento,
    _patch,
    _put,
)
from tests.test_gov_ctl06_hallazgos import _post

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


def _estructura_vigente(mundo, anio, empresa=None) -> dict[str, str]:
    empresa = empresa or mundo.company_a
    with mundo.factory() as session:
        entity = session.query(GovernmentEntity).filter_by(company_id=empresa).first()
        if entity is None:
            entity = GovernmentEntity(
                company_id=empresa,
                denominacion="Ente de prueba",
                status="BORRADOR",
                version=1,
            )
            session.add(entity)
            session.flush()

        estructura = (
            session.query(GovernmentStructure)
            .filter_by(company_id=empresa, exercise=anio, status="VIGENTE")
            .first()
        )
        if estructura is None:
            estructura = GovernmentStructure(
                company_id=empresa,
                entity_id=entity.id,
                exercise=anio,
                status="VIGENTE",
                published_at=datetime.now(UTC),
                version=1,
            )
            session.add(estructura)
            session.flush()

        unidades = {
            "DESP": ("Despacho", "ORGANO"),
            "ADM": ("Administración", "UNIDAD_ADMINISTRATIVA"),
        }
        ids: dict[str, str] = {}
        for code, (name, unit_type) in unidades.items():
            unit = (
                session.query(GovernmentUnit)
                .filter_by(structure_id=estructura.id, company_id=empresa, code=code)
                .first()
            )
            if unit is None:
                unit = GovernmentUnit(
                    structure_id=estructura.id,
                    company_id=empresa,
                    code=code,
                    name=name,
                    unit_type=unit_type,
                    status="ACTIVA",
                    valid_from=date(anio, 1, 1),
                    version=1,
                )
                session.add(unit)
                session.flush()
            ids[code] = unit.id
        session.commit()
    return ids


@ONLY_PG
def test_plan_y_objetivos(mundo, gobierno):
    detalle = _completo(mundo, 2081)
    ejercicio_id = detalle["id"]
    version = detalle["version"]
    _estructura_vigente(mundo, 2081)

    documento_id = _documento(mundo, ejercicio_id)
    r = _put(
        mundo,
        f"{P}/{ejercicio_id}/plan",
        "ua",
        mundo.company_a,
        {"denominacion": "Plan 2081", "documento_id": documento_id},
        version,
    )
    assert r.status_code == 200, r.text
    plan = r.json()
    version = plan["version"]
    assert plan["plan"]["denominacion"] == "Plan 2081"
    assert len(plan["plan"]["documento_sha256"]) == 64

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos",
        "ua",
        mundo.company_a,
        {"codigo": "O1", "descripcion": "Objetivo uno"},
        version,
    )
    assert r.status_code == 201, r.text
    version = r.json()["version"]
    o1 = next(o for o in r.json()["objetivos"] if o["codigo"] == "O1")

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos",
        "ua",
        mundo.company_a,
        {"codigo": "O2", "descripcion": "Objetivo dos"},
        version,
    )
    assert r.status_code == 201, r.text
    version = r.json()["version"]
    o2 = next(o for o in r.json()["objetivos"] if o["codigo"] == "O2")

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos",
        "ua",
        mundo.company_a,
        {"codigo": "O1", "descripcion": "Repetido"},
        version,
    )
    assert r.status_code == 422, r.text

    r = _patch(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos/{o2['id']}",
        "ua",
        mundo.company_a,
        {"descripcion": "Objetivo dos modificado"},
        version,
    )
    assert r.status_code == 200, r.text
    version = r.json()["version"]

    categorias = detalle["categorias"]
    c01 = next(c["id"] for c in categorias if c["codigo_completo"] == "01")
    unidades = _estructura_vigente(mundo, 2081)
    r = _put(
        mundo,
        f"{P}/{ejercicio_id}/categorias/{c01}/vinculo",
        "ua",
        mundo.company_a,
        {"unidad_id": unidades["DESP"], "objetivo_id": o1["id"]},
        version,
    )
    assert r.status_code == 200, r.text
    version = r.json()["version"]
    vinculo = next(v for v in r.json()["vinculos"] if v["categoria_id"] == c01)
    assert vinculo["unidad"]["codigo"] == "DESP"
    assert vinculo["objetivo"]["codigo"] == "O1"

    r = _delete(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos/{o1['id']}",
        "ua",
        mundo.company_a,
        version,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_BUDGET_OBJECTIVE_IN_USE"

    r = _delete(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos/{o2['id']}",
        "ua",
        mundo.company_a,
        version,
    )
    assert r.status_code == 200, r.text

    r = mundo.get(f"{P}/{ejercicio_id}", "ua", mundo.company_a)
    historia = [h["tipo"] for h in r.json()["historia"]]
    assert "PLAN_REGISTRADO" in historia
    assert "OBJETIVO_CREADO" in historia
    assert "CATEGORIA_VINCULADA" in historia

    with mundo.factory() as session:
        acciones = list(
            session.execute(
                select(AuditEvent.action).where(
                    AuditEvent.entity_type == "GovernmentBudgetYear",
                    AuditEvent.entity_id == ejercicio_id,
                )
            ).scalars()
        )
    assert "GOV_BUDGET_CATEGORY_LINKED" in acciones


@ONLY_PG
def test_unidad_ajena(mundo, gobierno):
    detalle = _completo(mundo, 2082)
    ejercicio_id = detalle["id"]
    version = detalle["version"]
    _estructura_vigente(mundo, 2083)

    r = mundo.get(f"{P}/{ejercicio_id}/plan", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    plan = r.json()
    assert plan["unidades_disponibles"] == []
    assert plan["estructura_organizativa"] is None

    categorias = detalle["categorias"]
    c01 = next(c["id"] for c in categorias if c["codigo_completo"] == "01")
    unidades_2083 = _estructura_vigente(mundo, 2083)
    r = _put(
        mundo,
        f"{P}/{ejercicio_id}/categorias/{c01}/vinculo",
        "ua",
        mundo.company_a,
        {"unidad_id": unidades_2083["DESP"], "objetivo_id": None},
        version,
    )
    assert r.status_code == 422, r.text

    unidades_b = _estructura_vigente(mundo, 2082, mundo.company_b)
    r = _put(
        mundo,
        f"{P}/{ejercicio_id}/categorias/{c01}/vinculo",
        "ua",
        mundo.company_a,
        {"unidad_id": unidades_b["DESP"], "objetivo_id": None},
        version,
    )
    assert r.status_code == 422, r.text


@ONLY_PG
def test_metas(mundo, gobierno):
    detalle = _completo(mundo, 2084)
    ejercicio_id = detalle["id"]
    version = detalle["version"]
    categorias = detalle["categorias"]
    c0102 = next(c["id"] for c in categorias if c["codigo_completo"] == "01.02")

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/metas",
        "ua",
        mundo.company_a,
        {
            "categoria_id": c0102,
            "descripcion": "Meta inicial",
            "unidad_medida": "Kilogramo",
            "cantidad": "1200.5",
            "indicador": "Cobertura",
            "formula": "kg / habitante",
        },
        version,
    )
    assert r.status_code == 201, r.text
    version = r.json()["version"]
    meta = r.json()["metas"][0]
    assert Decimal(meta["cantidad"]) == Decimal("1200.5")
    meta_id = meta["id"]

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/metas",
        "ua",
        mundo.company_a,
        {
            "categoria_id": c0102,
            "descripcion": "Cero",
            "unidad_medida": "Kilogramo",
            "cantidad": "0",
            "indicador": "Cobertura",
            "formula": "kg / habitante",
        },
        version,
    )
    assert r.status_code == 422, r.text

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/metas",
        "ua",
        mundo.company_a,
        {
            "categoria_id": c0102,
            "descripcion": "Demasiados decimales",
            "unidad_medida": "Kilogramo",
            "cantidad": "1.12345",
            "indicador": "Cobertura",
            "formula": "kg / habitante",
        },
        version,
    )
    assert r.status_code == 422, r.text

    detalle_otro = _completo(mundo, 2085)
    categoria_otro = next(c["id"] for c in detalle_otro["categorias"] if c["codigo_completo"] == "01.02")
    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/metas",
        "ua",
        mundo.company_a,
        {
            "categoria_id": categoria_otro,
            "descripcion": "Categoría ajena",
            "unidad_medida": "Kilogramo",
            "cantidad": "5",
            "indicador": "Cobertura",
            "formula": "kg / habitante",
        },
        version,
    )
    assert r.status_code == 422, r.text

    r = _patch(
        mundo,
        f"{P}/{ejercicio_id}/plan/metas/{meta_id}",
        "ua",
        mundo.company_a,
        {
            "descripcion": "Consultas atendidas",
            "unidad_medida": "consulta",
            "cantidad": "1200.5",
            "indicador": "Cobertura actualizada",
            "formula": None,
        },
        version,
    )
    assert r.status_code == 200, r.text
    version = r.json()["version"]

    r = _delete(
        mundo,
        f"{P}/{ejercicio_id}/plan/metas/{meta_id}",
        "ua",
        mundo.company_a,
        version,
    )
    assert r.status_code == 200, r.text

    with mundo.factory() as session:
        acciones = list(
            session.execute(
                select(AuditEvent.action).where(
                    AuditEvent.entity_type == "GovernmentBudgetYear",
                    AuditEvent.entity_id == ejercicio_id,
                )
            ).scalars()
        )
    assert "GOV_BUDGET_GOAL_CREATED" in acciones
    assert "GOV_BUDGET_GOAL_UPDATED" in acciones
    assert "GOV_BUDGET_GOAL_DELETED" in acciones


@ONLY_PG
def test_fuentes(mundo, gobierno):
    detalle = _completo(mundo, 2086)
    ejercicio_id = detalle["id"]
    version = detalle["version"]
    documento_id = _documento(mundo, ejercicio_id)

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F01",
            "denominacion": "Fuente uno",
            "procedencia": "Ordenanza municipal de ingresos",
            "documento_id": documento_id,
            "vigente_desde": "2086-01-01",
            "vigente_hasta": "2086-12-31",
        },
        version,
    )
    assert r.status_code == 201, r.text
    version = r.json()["version"]
    fuente = r.json()["items"][0]
    assert len(fuente["documento_sha256"]) == 64
    fuente_id = fuente["id"]

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F01",
            "denominacion": "Repetida",
            "procedencia": "Ordenanza municipal de ingresos",
            "documento_id": documento_id,
        },
        version,
    )
    assert r.status_code == 422, r.text

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F02",
            "denominacion": "Fuera de año",
            "procedencia": "Ordenanza municipal de ingresos",
            "documento_id": documento_id,
            "vigente_hasta": "2087-06-30",
        },
        version,
    )
    assert r.status_code == 422, r.text

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F02",
            "denominacion": "Fecha por defecto",
            "procedencia": "Ordenanza municipal de ingresos",
            "documento_id": documento_id,
        },
        version,
    )
    assert r.status_code == 201, r.text
    version = r.json()["version"]
    f02 = next(i for i in r.json()["items"] if i["codigo"] == "F02")
    assert f02["vigente_desde"] == "2086-01-01"

    r = _patch(
        mundo,
        f"{P}/{ejercicio_id}/fuentes/{fuente_id}",
        "ua",
        mundo.company_a,
        {
            "denominacion": "Fuente uno renombrada",
            "procedencia": "Ordenanza municipal de ingresos",
        },
        version,
    )
    assert r.status_code == 200, r.text
    version = r.json()["version"]

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes/{fuente_id}/restricciones",
        "ua",
        mundo.company_a,
        {"descripcion": "Solo egresos", "fundamento": "Art. 1", "partidas": ["401"]},
        version,
    )
    assert r.status_code == 201, r.text
    version = r.json()["version"]
    restriccion = r.json()["items"][0]["restricciones"][0]
    assert restriccion["partidas"] == ["401"]
    restriccion_id = restriccion["id"]

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes/{fuente_id}/restricciones",
        "ua",
        mundo.company_a,
        {"descripcion": "Recurso", "fundamento": "Art. 2", "partidas": ["301"]},
        version,
    )
    assert r.status_code == 422, r.text

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes/{fuente_id}/restricciones",
        "ua",
        mundo.company_a,
        {"descripcion": "Inexistente", "fundamento": "Art. 3", "partidas": ["999"]},
        version,
    )
    assert r.status_code == 422, r.text

    r = _delete(
        mundo,
        f"{P}/{ejercicio_id}/fuentes/{fuente_id}/restricciones/{restriccion_id}",
        "ua",
        mundo.company_a,
        version,
    )
    assert r.status_code == 200, r.text
    version = r.json()["version"]

    r = _delete(
        mundo,
        f"{P}/{ejercicio_id}/fuentes/{fuente_id}",
        "ua",
        mundo.company_a,
        version,
    )
    assert r.status_code == 200, r.text

    with mundo.factory() as session:
        acciones = list(
            session.execute(
                select(AuditEvent.action).where(
                    AuditEvent.entity_type == "GovernmentBudgetYear",
                    AuditEvent.entity_id == ejercicio_id,
                )
            ).scalars()
        )
    assert "GOV_BUDGET_FUNDING_SOURCE_CREATED" in acciones
    assert "GOV_BUDGET_FUNDING_RESTRICTION_ADDED" in acciones


@ONLY_PG
def test_restriccion_sin_clasificador(mundo, gobierno):
    detalle = _crear(mundo, 2087)
    ejercicio_id = detalle["id"]
    version = detalle["version"]

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F01",
            "denominacion": "Fuente",
            "procedencia": "Ordenanza municipal de ingresos",
        },
        version,
    )
    assert r.status_code == 201, r.text
    version = r.json()["version"]
    fuente_id = r.json()["items"][0]["id"]

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes/{fuente_id}/restricciones",
        "ua",
        mundo.company_a,
        {"descripcion": "Con partida", "fundamento": "Art. 1", "partidas": ["401"]},
        version,
    )
    assert r.status_code == 409, r.text

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes/{fuente_id}/restricciones",
        "ua",
        mundo.company_a,
        {"descripcion": "Sin partida", "fundamento": "Art. 2"},
        version,
    )
    assert r.status_code == 201, r.text


@ONLY_PG
def test_congelado_y_fotografia(mundo, gobierno):
    detalle = _completo(mundo, 2088)
    ejercicio_id = detalle["id"]
    version = detalle["version"]
    _estructura_vigente(mundo, 2088)

    documento_id = _documento(mundo, ejercicio_id)
    version = _put(
        mundo,
        f"{P}/{ejercicio_id}/plan",
        "ua",
        mundo.company_a,
        {"denominacion": "Plan 2088", "documento_id": documento_id},
        version,
    ).json()["version"]

    version = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos",
        "ua",
        mundo.company_a,
        {"codigo": "O1", "descripcion": "Objetivo"},
        version,
    ).json()["version"]

    objetivo = mundo.get(f"{P}/{ejercicio_id}/plan", "ua", mundo.company_a).json()["objetivos"][0]
    categorias = detalle["categorias"]
    c01 = next(c["id"] for c in categorias if c["codigo_completo"] == "01")
    unidades = _estructura_vigente(mundo, 2088)
    version = _put(
        mundo,
        f"{P}/{ejercicio_id}/categorias/{c01}/vinculo",
        "ua",
        mundo.company_a,
        {"unidad_id": unidades["DESP"], "objetivo_id": objetivo["id"]},
        version,
    ).json()["version"]

    c0102 = next(c["id"] for c in categorias if c["codigo_completo"] == "01.02")
    version = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/metas",
        "ua",
        mundo.company_a,
        {
            "categoria_id": c0102,
            "descripcion": "Meta",
            "unidad_medida": "Kilogramo",
            "cantidad": "10",
            "indicador": "Cobertura",
            "formula": "kg / habitante",
        },
        version,
    ).json()["version"]

    version = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F01",
            "denominacion": "Fuente",
            "procedencia": "Ordenanza municipal de ingresos",
        },
        version,
    ).json()["version"]

    fuente_id = mundo.get(f"{P}/{ejercicio_id}/fuentes", "ua", mundo.company_a).json()["items"][0]["id"]
    version = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes/{fuente_id}/restricciones",
        "ua",
        mundo.company_a,
        {"descripcion": "Restricción", "fundamento": "Art. 1"},
        version,
    ).json()["version"]

    detalle_aprobado = _aprobar(mundo, {**detalle, "version": version})
    version = detalle_aprobado["version"]

    with mundo.factory() as session:
        foundation = (
            session.query(GovernmentBudgetYearFoundation)
            .filter_by(company_id=mundo.company_a, year_id=ejercicio_id)
            .one()
        )
        assert "plan" in foundation.fotografia
        assert "fuentes" in foundation.fotografia
        assert any(o["codigo"] == "O1" for o in foundation.fotografia["plan"]["objetivos"])
        assert any(f["codigo"] == "F01" for f in foundation.fotografia["fuentes"])

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos",
        "ua",
        mundo.company_a,
        {"codigo": "O2", "descripcion": "Frozen"},
        version,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_BUDGET_YEAR_FROZEN"

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/metas",
        "ua",
        mundo.company_a,
        {
            "categoria_id": c0102,
            "descripcion": "Meta frozen",
            "unidad_medida": "Kilogramo",
            "cantidad": "1",
            "indicador": "Cobertura",
            "formula": "kg / habitante",
        },
        version,
    )
    assert r.status_code == 409, r.text

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F02",
            "denominacion": "Frozen",
            "procedencia": "Ordenanza municipal de ingresos",
        },
        version,
    )
    assert r.status_code == 409, r.text

    r = _put(
        mundo,
        f"{P}/{ejercicio_id}/categorias/{c01}/vinculo",
        "ua",
        mundo.company_a,
        {"unidad_id": unidades["ADM"], "objetivo_id": None},
        version,
    )
    assert r.status_code == 409, r.text

    with pytest.raises(DBAPIError):
        with mundo.factory() as session:
            session.execute(
                text(
                    "UPDATE gov_budget_funding_sources SET denominacion = 'hack' WHERE company_id = :company_id "
                    "AND year_id = :y"
                ),
                {"company_id": mundo.company_a, "y": ejercicio_id},
            )
            session.commit()


@ONLY_PG
def test_aislamiento_y_permisos(mundo, gobierno):
    detalle = _completo(mundo, 2089)
    ejercicio_id = detalle["id"]

    r = mundo.get(f"{P}/{ejercicio_id}/plan", "ub", mundo.company_b)
    assert r.status_code == 404, r.text
    r = mundo.get(f"{P}/{ejercicio_id}/fuentes", "ub", mundo.company_b)
    assert r.status_code == 404, r.text

    cuenta_con_permisos(mundo, "solo_ver_b34", [("gobierno_presupuesto", "view")])
    r = mundo.get(f"{P}/{ejercicio_id}/plan", "solo_ver_b34", mundo.company_a)
    assert r.status_code == 200, r.text
    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/fuentes",
        "solo_ver_b34",
        mundo.company_a,
        {
            "codigo": "F01",
            "denominacion": "Sin permiso",
            "procedencia": "Ordenanza municipal de ingresos",
        },
        detalle["version"],
    )
    assert r.status_code == 403, r.text

    cuenta_con_permisos(mundo, "sin_permisos_b34", [])
    r = mundo.get(f"{P}/{ejercicio_id}/plan", "sin_permisos_b34", mundo.company_a)
    assert r.status_code == 403, r.text


@ONLY_PG
def test_version_obsoleta(mundo, gobierno):
    detalle = _crear(mundo, 2090)
    ejercicio_id = detalle["id"]
    version = detalle["version"]

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos",
        "ua",
        mundo.company_a,
        {"codigo": "O1", "descripcion": "Primero"},
        version,
    )
    assert r.status_code == 201, r.text

    r = _post(
        mundo,
        f"{P}/{ejercicio_id}/plan/objetivos",
        "ua",
        mundo.company_a,
        {"codigo": "O2", "descripcion": "Segundo"},
        version,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_BUDGET_YEAR_STALE"
