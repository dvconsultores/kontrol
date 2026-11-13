"""BUD-01 / BUD-02 · Ejercicio presupuestario del gobierno (presupuesto anual).

Se ejecuta sobre PostgreSQL: disparadores de inmutabilidad, auditoría y concurrencia optimista son parte de la
compuerta. Ver `KONTROL_TEST_DB_URL`.
"""

import io
import os
from datetime import date

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentBudgetYearHistory
from app.shared.clock import hoy_de_negocio
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_ctl06_hallazgos import _post
from tests.test_gov_doc08_paquete import _doc_real

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

P = "/gobierno/presupuesto/ejercicios"
HOY = hoy_de_negocio()
ONLY_PG = pytest.mark.skipif(
    "postgresql" not in os.environ.get("KONTROL_TEST_DB_URL", ""),
    reason="BUD-01 y BUD-02 se verifican sobre PostgreSQL",
)

CABECERA_CSV = (
    "tipo,codigo,denominacion,nivel,codigo_padre,vigente_desde,vigente_hasta\n"
)


def _put(mundo, ruta, usuario, empresa, cuerpo, version):
    headers = mundo.como(usuario, empresa)
    headers["If-Match"] = str(version)
    return mundo.client.put(f"/api/v1{ruta}", headers=headers, json=cuerpo)


def _patch(mundo, ruta, usuario, empresa, cuerpo, version):
    headers = mundo.como(usuario, empresa)
    headers["If-Match"] = str(version)
    return mundo.client.patch(f"/api/v1{ruta}", headers=headers, json=cuerpo)


def _delete(mundo, ruta, usuario, empresa, version):
    headers = mundo.como(usuario, empresa)
    headers["If-Match"] = str(version)
    return mundo.client.delete(f"/api/v1{ruta}", headers=headers)


def _documento(mundo, ejercicio_id, empresa=None) -> str:
    empresa = empresa or mundo.company_a
    doc = _doc_real(mundo, empresa, None, b"ordenanza", "ordenanza")
    r = mundo.post(
        f"/documentos/{doc}/vinculos",
        "ua",
        empresa,
        {"resource_type": "GovernmentBudgetYear", "resource_id": ejercicio_id},
    )
    assert r.status_code == 200, r.text
    return doc


def _crear(mundo, anio, empresa=None) -> dict:
    empresa = empresa or mundo.company_a
    r = _post(mundo, P, "ua", empresa, {"anio": anio})
    assert r.status_code == 201, r.text
    return r.json()


def _completo(mundo, anio) -> dict:
    detalle = _crear(mundo, anio)
    v = detalle["version"]
    r = _put(
        mundo,
        f"{P}/{detalle['id']}/niveles",
        "ua",
        mundo.company_a,
        {"niveles": [{"nombre": "Sector"}, {"nombre": "Programa"}]},
        v,
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    v = detalle["version"]
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ua",
        mundo.company_a,
        {"nivel_orden": 1, "parent_id": None, "codigo": "01", "denominacion": "Sector salud"},
        version=v,
    )
    assert r.status_code == 201, r.text
    detalle = r.json()
    v = detalle["version"]
    categoria1 = detalle["categorias"][0]["id"]
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ua",
        mundo.company_a,
        {
            "nivel_orden": 2,
            "parent_id": categoria1,
            "codigo": "02",
            "denominacion": "Atención primaria",
        },
        version=v,
    )
    assert r.status_code == 201, r.text
    detalle = r.json()
    v = detalle["version"]
    doc = _documento(mundo, detalle["id"])
    r = _put(
        mundo,
        f"{P}/{detalle['id']}/clasificador",
        "ua",
        mundo.company_a,
        {
            "edicion": f"Clasificador del ente {anio}",
            "fecha_edicion": date(anio, 1, 1).isoformat(),
            "procedencia": "Copia entregada por la Dirección de Presupuesto",
            "documento_id": doc,
        },
        v,
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    v = detalle["version"]
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/clasificador/partidas",
        "ua",
        mundo.company_a,
        {
            "tipo": "RECURSO",
            "codigo": "301",
            "denominacion": "Ingresos propios",
            "nivel": 1,
            "codigo_padre": None,
            "vigente_desde": date(anio, 1, 1).isoformat(),
            "vigente_hasta": date(anio, 12, 31).isoformat(),
        },
        version=v,
    )
    assert r.status_code == 201, r.text
    detalle = r.json()
    v = detalle["version"]
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/clasificador/partidas",
        "ua",
        mundo.company_a,
        {
            "tipo": "EGRESO",
            "codigo": "401",
            "denominacion": "Gasto corriente",
            "nivel": 1,
            "codigo_padre": None,
            "vigente_desde": date(anio, 1, 1).isoformat(),
            "vigente_hasta": date(anio, 12, 31).isoformat(),
        },
        version=v,
    )
    assert r.status_code == 201, r.text
    detalle = r.json()
    v = detalle["version"]
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/clasificador/partidas",
        "ua",
        mundo.company_a,
        {
            "tipo": "EGRESO",
            "codigo": "401.01",
            "denominacion": "Servicios personales",
            "nivel": 2,
            "codigo_padre": "401",
            "vigente_desde": date(anio, 1, 1).isoformat(),
            "vigente_hasta": date(anio, 12, 31).isoformat(),
        },
        version=v,
    )
    assert r.status_code == 201, r.text
    return r.json()


def _aprobar(mundo, detalle) -> dict:
    anio = detalle["anio"]
    fecha = HOY if HOY.year <= anio else date(anio, 12, 31)
    doc = _documento(mundo, detalle["id"])
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/aprobar",
        "ua",
        mundo.company_a,
        {
            "referencia": "Gaceta Municipal Extraordinaria N.º 9999",
            "fecha": fecha.isoformat(),
            "documento_id": doc,
        },
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    return r.json()


@ONLY_PG
def test_vida_aprobada(mundo, gobierno):
    detalle = _completo(mundo, 2061)
    aprobado = _aprobar(mundo, detalle)
    assert aprobado["estado"] == "APROBADO"
    assert aprobado["congelado"] is True
    assert aprobado["precompromiso_activo"] is False
    assert len(aprobado["moneda_funcional"]) == 3
    fundamentos = aprobado["fundamentos"]
    assert len(fundamentos) == 1
    assert fundamentos[0]["tipo"] == "ORDENANZA"
    assert len(fundamentos[0]["huella"]) == 64
    assert len(fundamentos[0]["documento_sha256"]) == 64
    tipos_historia = [h["tipo"] for h in aprobado["historia"]]
    assert "CREADO" in tipos_historia
    assert "NIVELES_CONFIGURADOS" in tipos_historia
    assert "CATEGORIA_CREADA" in tipos_historia
    assert "CLASIFICADOR_REGISTRADO" in tipos_historia
    assert "PARTIDA_CREADA" in tipos_historia
    assert "APROBADO" in tipos_historia
    with mundo.factory() as session:
        acciones = set(
            session.execute(
                select(AuditEvent.action).where(
                    AuditEvent.entity_type == "GovernmentBudgetYear",
                    AuditEvent.entity_id == aprobado["id"],
                )
            ).scalars()
        )
    assert "GOV_BUDGET_YEAR_CREATED" in acciones
    assert "GOV_BUDGET_LEVELS_CONFIGURED" in acciones
    assert "GOV_BUDGET_CATEGORY_CREATED" in acciones
    assert "GOV_BUDGET_CLASSIFIER_REGISTERED" in acciones
    assert "GOV_BUDGET_CLASSIFIER_ITEM_CREATED" in acciones
    assert "GOV_BUDGET_YEAR_APPROVED" in acciones


@ONLY_PG
def test_duplicado(mundo, gobierno):
    _crear(mundo, 2072)
    r = _post(mundo, P, "ua", mundo.company_a, {"anio": 2072})
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_EXISTS" in r.text


@ONLY_PG
def test_estructura_invalida(mundo, gobierno):
    detalle = _crear(mundo, 2062)
    v = detalle["version"]
    r = _put(
        mundo,
        f"{P}/{detalle['id']}/niveles",
        "ua",
        mundo.company_a,
        {"niveles": [{"nombre": "Sector"}, {"nombre": "Programa"}]},
        v,
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    v = detalle["version"]
    next(n["orden"] for n in detalle["niveles"] if n["nombre"] == "Programa")
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ua",
        mundo.company_a,
        {"nivel_orden": 2, "parent_id": None, "codigo": "10", "denominacion": "Sin padre"},
        version=v,
    )
    assert r.status_code == 422, r.text
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ua",
        mundo.company_a,
        {
            "nivel_orden": 1,
            "parent_id": None,
            "codigo": "01",
            "denominacion": "Sector salud",
        },
        version=v,
    )
    assert r.status_code == 201, r.text
    detalle = r.json()
    v = detalle["version"]
    cat1 = detalle["categorias"][0]["id"]
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ua",
        mundo.company_a,
        {"nivel_orden": 2, "parent_id": cat1, "codigo": "a b", "denominacion": "Código con espacio"},
        version=v,
    )
    assert r.status_code == 422, r.text
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ua",
        mundo.company_a,
        {
            "nivel_orden": 2,
            "parent_id": cat1,
            "codigo": "02",
            "denominacion": "Atención primaria",
        },
        version=v,
    )
    assert r.status_code == 201, r.text
    detalle = r.json()
    v = detalle["version"]
    cat2 = detalle["categorias"][1]["id"]
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ua",
        mundo.company_a,
        {"nivel_orden": 2, "parent_id": cat2, "codigo": "03", "denominacion": "Padre de nivel 2"},
        version=v,
    )
    assert r.status_code == 422, r.text
    otro = _crear(mundo, 2080)
    v_otro = otro["version"]
    r = _put(
        mundo,
        f"{P}/{otro['id']}/niveles",
        "ua",
        mundo.company_a,
        {"niveles": [{"nombre": "Sector"}]},
        v_otro,
    )
    assert r.status_code == 200, r.text
    otro = r.json()
    v_otro = otro["version"]
    r = _post(
        mundo,
        f"{P}/{otro['id']}/categorias",
        "ua",
        mundo.company_a,
        {"nivel_orden": 1, "parent_id": None, "codigo": "01", "denominacion": "Otro ejercicio"},
        version=v_otro,
    )
    assert r.status_code == 201, r.text
    otro = r.json()
    cat_otro = otro["categorias"][0]["id"]
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ua",
        mundo.company_a,
        {"nivel_orden": 2, "parent_id": cat_otro, "codigo": "04", "denominacion": "Padre ajeno"},
        version=v,
    )
    assert r.status_code in (404, 422), r.text
    r = _delete(mundo, f"{P}/{detalle['id']}/categorias/{cat1}", "ua", mundo.company_a, v)
    assert r.status_code == 409
    assert "GOV_BUDGET_CATEGORY_HAS_CHILDREN" in r.text
    r = _put(
        mundo,
        f"{P}/{detalle['id']}/niveles",
        "ua",
        mundo.company_a,
        {"niveles": [{"nombre": "Sector"}]},
        v,
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_LEVELS_IN_USE" in r.text
    r = _patch(
        mundo,
        f"{P}/{detalle['id']}/categorias/{cat2}",
        "ua",
        mundo.company_a,
        {"denominacion": "Atención hospitalaria"},
        v,
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert any(
        h["tipo"] == "CATEGORIA_MODIFICADA" for h in detalle["historia"]
    )


@ONLY_PG
def test_clasificador_e_importacion(mundo, gobierno):
    detalle = _completo(mundo, 2063)
    doc = _documento(mundo, detalle["id"])
    v = detalle["version"]
    r = _put(
        mundo,
        f"{P}/{detalle['id']}/clasificador",
        "ua",
        mundo.company_a,
        {
            "edicion": f"Clasificador del ente {2063}",
            "fecha_edicion": date(2063, 1, 1).isoformat(),
            "procedencia": "Procedencia sustituida",
            "documento_id": doc,
        },
        v,
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    assert any(h["tipo"] == "PROCEDENCIA_MODIFICADA" for h in detalle["historia"])
    with mundo.factory() as session:
        acciones = set(
            session.execute(
                select(AuditEvent.action).where(
                    AuditEvent.entity_type == "GovernmentBudgetYear",
                    AuditEvent.entity_id == detalle["id"],
                )
            ).scalars()
        )
    assert "GOV_BUDGET_CLASSIFIER_PROVENANCE_UPDATED" in acciones
    v = detalle["version"]
    csv_valido = (
        CABECERA_CSV
        + f"EGRESO,402,Transferencias,1,,{2063}-01-01,{2063}-12-31\n"
        + f"EGRESO,402.01,Transferencias internas,2,402,{2063}-01-01,{2063}-12-31\n"
        + f"RECURSO,302,Recursos de capital,1,,{2063}-01-01,{2063}-12-31\n"
    )
    r = mundo.client.post(
        f"/api/v1{P}/{detalle['id']}/clasificador/importar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(v)},
        files={"archivo": ("clasificador.csv", io.BytesIO(csv_valido.encode("utf-8")), "text/csv")},
    )
    assert r.status_code == 200, r.text
    detalle = r.json()
    v = detalle["version"]
    r = mundo.get(f"{P}/{detalle['id']}/clasificador/partidas?tipo=EGRESO", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    partida_402_01 = next(i for i in items if i["codigo"] == "402.01")
    assert partida_402_01["codigo_padre"] == "402"
    csv_invalido = (
        CABECERA_CSV
        + f"EGRESO,403,Nivel 2 sin padre,2,,{2063}-01-01,{2063}-12-31\n"
    )
    r = mundo.client.post(
        f"/api/v1{P}/{detalle['id']}/clasificador/importar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(v)},
        files={"archivo": ("mal.csv", io.BytesIO(csv_invalido.encode("utf-8")), "text/csv")},
    )
    assert r.status_code == 422, r.text
    assert "Fila" in r.text
    r = mundo.get(f"{P}/{detalle['id']}/clasificador/partidas?tipo=EGRESO", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert not any(i["codigo"] == "403" for i in r.json()["items"])
    csv_cabecera_mala = "tipo,codigo,denominacion,nivel,codigo_padre,vigente_desde\nEGRESO,404,Nueva,1,,2020-01-01\n"
    r = mundo.client.post(
        f"/api/v1{P}/{detalle['id']}/clasificador/importar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(v)},
        files={"archivo": ("cabecera.csv", io.BytesIO(csv_cabecera_mala.encode("utf-8")), "text/csv")},
    )
    assert r.status_code == 422, r.text
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/clasificador/partidas",
        "ua",
        mundo.company_a,
        {
            "tipo": "EGRESO",
            "codigo": "405",
            "denominacion": "Nivel 2 con padre de RECURSO",
            "nivel": 2,
            "codigo_padre": "301",
            "vigente_desde": date(2063, 1, 1).isoformat(),
            "vigente_hasta": date(2063, 12, 31).isoformat(),
        },
        version=v,
    )
    assert r.status_code == 422, r.text
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/clasificador/partidas",
        "ua",
        mundo.company_a,
        {
            "tipo": "EGRESO",
            "codigo": "406",
            "denominacion": "Vigencia fuera del año",
            "nivel": 1,
            "codigo_padre": None,
            "vigente_desde": date(2063, 1, 1).isoformat(),
            "vigente_hasta": date(2064, 12, 31).isoformat(),
        },
        version=v,
    )
    assert r.status_code == 422, r.text


@ONLY_PG
def test_incompleto(mundo, gobierno):
    detalle = _crear(mundo, 2064)
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/aprobar",
        "ua",
        mundo.company_a,
        {
            "referencia": "Gaceta sin datos",
            "fecha": HOY.isoformat(),
            "documento_id": _documento(mundo, detalle["id"]),
        },
        version=detalle["version"],
    )
    assert r.status_code == 422
    assert "GOV_BUDGET_YEAR_INCOMPLETE" in r.text
    detalle = mundo.get(f"{P}/{detalle['id']}", "ua", mundo.company_a).json()
    assert detalle["faltantes"]


@ONLY_PG
def test_documento_invalido(mundo, gobierno):
    detalle = _completo(mundo, 2066)
    doc_sin_vincular = _doc_real(mundo, mundo.company_a, None, b"ordenanza", "ordenanza")
    anio = detalle["anio"]
    fecha = HOY if HOY.year <= anio else date(anio, 12, 31)
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/aprobar",
        "ua",
        mundo.company_a,
        {
            "referencia": "Gaceta Municipal Extraordinaria N.º 9999",
            "fecha": fecha.isoformat(),
            "documento_id": doc_sin_vincular,
        },
        version=detalle["version"],
    )
    assert r.status_code == 422
    assert "GOV_BUDGET_INVALID_DOCUMENT" in r.text


@ONLY_PG
def test_congelado_y_trigger(mundo, gobierno):
    detalle = _completo(mundo, 2065)
    aprobado = _aprobar(mundo, detalle)
    v = aprobado["version"]
    r = _post(
        mundo,
        f"{P}/{aprobado['id']}/categorias",
        "ua",
        mundo.company_a,
        {"nivel_orden": 1, "parent_id": None, "codigo": "99", "denominacion": "Nueva"},
        version=v,
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_FROZEN" in r.text
    r = _put(
        mundo,
        f"{P}/{aprobado['id']}/niveles",
        "ua",
        mundo.company_a,
        {"niveles": [{"nombre": "Sector"}]},
        v,
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_FROZEN" in r.text
    doc = _documento(mundo, aprobado["id"])
    r = _put(
        mundo,
        f"{P}/{aprobado['id']}/clasificador",
        "ua",
        mundo.company_a,
        {
            "edicion": "Otra edición",
            "fecha_edicion": date(2065, 1, 1).isoformat(),
            "procedencia": "Otra procedencia",
            "documento_id": doc,
        },
        v,
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_FROZEN" in r.text
    r = _post(
        mundo,
        f"{P}/{aprobado['id']}/clasificador/partidas",
        "ua",
        mundo.company_a,
        {
            "tipo": "EGRESO",
            "codigo": "407",
            "denominacion": "Nueva partida",
            "nivel": 1,
            "codigo_padre": None,
            "vigente_desde": date(2065, 1, 1).isoformat(),
            "vigente_hasta": date(2065, 12, 31).isoformat(),
        },
        version=v,
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_FROZEN" in r.text
    partidas = mundo.get(
        f"{P}/{aprobado['id']}/clasificador/partidas?tipo=EGRESO", "ua", mundo.company_a
    ).json()["items"]
    partida_id = partidas[0]["id"]
    r = _delete(
        mundo,
        f"{P}/{aprobado['id']}/clasificador/partidas/{partida_id}",
        "ua",
        mundo.company_a,
        v,
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_FROZEN" in r.text
    csv_extra = CABECERA_CSV + f"EGRESO,408,Importada,1,,{2065}-01-01,{2065}-12-31\n"
    r = mundo.client.post(
        f"/api/v1{P}/{aprobado['id']}/clasificador/importar",
        headers={**mundo.como("ua", mundo.company_a), "If-Match": str(v)},
        files={"archivo": ("import.csv", io.BytesIO(csv_extra.encode("utf-8")), "text/csv")},
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_FROZEN" in r.text
    with mundo.factory() as session:
        with pytest.raises(DBAPIError) as excinfo:
            session.execute(
                text(
                    "UPDATE gov_budget_categories SET denominacion='x' WHERE year_id=:y"
                ),
                {"y": aprobado["id"]},
            )
            session.commit()
        assert "GOV_BUDGET_YEAR_FROZEN" in str(excinfo.value)
        session.rollback()
        with pytest.raises(DBAPIError) as excinfo:
            session.execute(
                text(
                    "INSERT INTO gov_budget_program_levels "
                    "(id, year_id, company_id, orden, nombre, created_at, updated_at) "
                    "VALUES (gen_random_uuid()::text, :y, :c, 99, 'Falso', now(), now())"
                ),
                {"y": aprobado["id"], "c": mundo.company_a},
            )
            session.commit()
        assert "GOV_BUDGET_YEAR_FROZEN" in str(excinfo.value)
        session.rollback()


@ONLY_PG
def test_reconduccion_prematura(mundo, gobierno):
    anio = HOY.year + 2
    detalle = _completo(mundo, anio)
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/reconducir",
        "ua",
        mundo.company_a,
        {
            "referencia": "Gaceta de reconducción",
            "fecha": date(HOY.year - 1, 12, 16).isoformat(),
            "documento_id": _documento(mundo, detalle["id"]),
        },
        version=detalle["version"],
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_RECONDUCTION_PREMATURE" in r.text


@ONLY_PG
def test_reconduccion(mundo, gobierno):
    anio = HOY.year
    detalle = _completo(mundo, anio)
    doc = _documento(mundo, detalle["id"])
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/reconducir",
        "ua",
        mundo.company_a,
        {
            "referencia": "Gaceta de reconducción",
            "fecha": date(HOY.year - 1, 12, 16).isoformat(),
            "documento_id": doc,
        },
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    reconducido = r.json()
    assert reconducido["estado"] == "RECONDUCIDO"
    assert reconducido["reconduccion_definitiva"] == (HOY > date(HOY.year, 3, 31))
    assert any(f["tipo"] == "RECONDUCCION" for f in reconducido["fundamentos"])
    aprobar_de_nuevo = _post(
        mundo,
        f"{P}/{detalle['id']}/aprobar",
        "ua",
        mundo.company_a,
        {
            "referencia": "Otra gaceta",
            "fecha": HOY.isoformat(),
            "documento_id": _documento(mundo, detalle["id"]),
        },
        version=reconducido["version"],
    )
    assert aprobar_de_nuevo.status_code == 409
    assert "GOV_BUDGET_YEAR_INVALID_STATE" in aprobar_de_nuevo.text
    otro = _completo(mundo, HOY.year - 3)
    r = _post(
        mundo,
        f"{P}/{otro['id']}/reconducir",
        "ua",
        mundo.company_a,
        {
            "referencia": "Fecha demasiado pronto",
            "fecha": date(HOY.year - 4, 12, 15).isoformat(),
            "documento_id": _documento(mundo, otro["id"]),
        },
        version=otro["version"],
    )
    assert r.status_code == 422, r.text


@ONLY_PG
def test_cierre(mundo, gobierno):
    prem = _completo(mundo, 2067)
    prem_aprobado = _aprobar(mundo, prem)
    r = _post(
        mundo,
        f"{P}/{prem_aprobado['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": "Cierre prematuro"},
        version=prem_aprobado["version"],
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_NOT_ENDED" in r.text
    anio = HOY.year - 1
    detalle = _completo(mundo, anio)
    aprobado = _aprobar(mundo, detalle)
    r = _post(
        mundo,
        f"{P}/{aprobado['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": "Cierre del ejercicio"},
        version=aprobado["version"],
    )
    assert r.status_code == 200, r.text
    cerrado = r.json()
    assert cerrado["estado"] == "CERRADO"
    assert cerrado["cerrado_en"] is not None
    assert cerrado["motivo_cierre"] == "Cierre del ejercicio"
    with mundo.factory() as session:
        acciones = set(
            session.execute(
                select(AuditEvent.action).where(
                    AuditEvent.entity_type == "GovernmentBudgetYear",
                    AuditEvent.entity_id == cerrado["id"],
                )
            ).scalars()
        )
    assert "GOV_BUDGET_YEAR_CLOSED" in acciones
    r = _post(
        mundo,
        f"{P}/{cerrado['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": "De nuevo"},
        version=cerrado["version"],
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_INVALID_STATE" in r.text
    borrador = _crear(mundo, 2074)
    r = _post(
        mundo,
        f"{P}/{borrador['id']}/cerrar",
        "ua",
        mundo.company_a,
        {"motivo": "Cerrar borrador"},
        version=borrador["version"],
    )
    assert r.status_code == 409
    assert "GOV_BUDGET_YEAR_INVALID_STATE" in r.text


@ONLY_PG
def test_precompromiso(mundo, gobierno):
    detalle = _crear(mundo, 2068)
    assert detalle["precompromiso_activo"] is False
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/precompromiso",
        "ua",
        mundo.company_a,
        {
            "activo": True,
            "vigente_desde": date(2068, 3, 1).isoformat(),
            "motivo": "Manual interno aprobado",
        },
        version=detalle["version"],
    )
    assert r.status_code == 200, r.text
    activo = r.json()
    assert activo["precompromiso_activo"] is True
    assert activo["precompromiso_desde"] == "2068-03-01"
    assert any(h["tipo"] == "PRECOMPROMISO_CAMBIADO" for h in activo["historia"])
    with mundo.factory() as session:
        acciones = set(
            session.execute(
                select(AuditEvent.action).where(
                    AuditEvent.entity_type == "GovernmentBudgetYear",
                    AuditEvent.entity_id == activo["id"],
                )
            ).scalars()
        )
    assert "GOV_BUDGET_PRECOMMITMENT_POLICY_CHANGED" in acciones
    r = _post(
        mundo,
        f"{P}/{activo['id']}/precompromiso",
        "ua",
        mundo.company_a,
        {
            "activo": True,
            "vigente_desde": date(2068, 3, 1).isoformat(),
            "motivo": "Manual interno aprobado",
        },
        version=activo["version"],
    )
    assert r.status_code == 422, r.text
    r = _post(
        mundo,
        f"{P}/{activo['id']}/precompromiso",
        "ua",
        mundo.company_a,
        {
            "activo": False,
            "vigente_desde": date(2069, 3, 1).isoformat(),
            "motivo": "Fuera del año",
        },
        version=activo["version"],
    )
    assert r.status_code == 422, r.text
    cuenta_con_permisos(
        mundo,
        "solo_presu_gestion",
        [("gobierno_presupuesto", "view"), ("gobierno_presupuesto", "manage")],
    )
    r = _post(
        mundo,
        f"{P}/{activo['id']}/precompromiso",
        "solo_presu_gestion",
        mundo.company_a,
        {
            "activo": False,
            "vigente_desde": date(2068, 1, 1).isoformat(),
            "motivo": "Sin capacidad específica",
        },
        version=activo["version"],
    )
    assert r.status_code == 403, r.text


@ONLY_PG
def test_aislamiento(mundo, gobierno):
    detalle = _crear(mundo, 2069)
    r = mundo.get(f"{P}/{detalle['id']}", "ub", mundo.company_b)
    assert r.status_code == 404, r.text
    listado_b = mundo.get(P, "ub", mundo.company_b).json()["items"]
    assert detalle["id"] not in [i["id"] for i in listado_b]
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ub",
        mundo.company_b,
        {"nivel_orden": 1, "parent_id": None, "codigo": "01", "denominacion": "Ajeno"},
        version=detalle["version"],
    )
    assert r.status_code == 404, r.text


@ONLY_PG
def test_sin_capacidad(mundo, gobierno):
    cuenta_con_permisos(mundo, "sin_presu", [])
    assert mundo.get(P, "sin_presu", mundo.company_a).status_code == 403
    assert _post(mundo, P, "sin_presu", mundo.company_a, {"anio": 2080}).status_code == 403
    cuenta_con_permisos(mundo, "solo_ver_presu", [("gobierno_presupuesto", "view")])
    assert mundo.get(P, "solo_ver_presu", mundo.company_a).status_code == 200
    assert _post(mundo, P, "solo_ver_presu", mundo.company_a, {"anio": 2080}).status_code == 403


@ONLY_PG
def test_concurrencia_doble_aprobacion(mundo, gobierno):
    detalle = _completo(mundo, 2070)
    doc = _documento(mundo, detalle["id"])
    anio = detalle["anio"]
    fecha = HOY if HOY.year <= anio else date(anio, 12, 31)
    cuerpo = {
        "referencia": "Gaceta Concurrente",
        "fecha": fecha.isoformat(),
        "documento_id": doc,
    }
    primera = _post(
        mundo,
        f"{P}/{detalle['id']}/aprobar",
        "ua",
        mundo.company_a,
        cuerpo,
        version=detalle["version"],
    )
    assert primera.status_code == 200, primera.text
    segunda = _post(
        mundo,
        f"{P}/{detalle['id']}/aprobar",
        "ua",
        mundo.company_a,
        cuerpo,
        version=detalle["version"],
    )
    assert segunda.status_code == 409, segunda.text
    assert "GOV_BUDGET_YEAR_STALE" in segunda.text or "GOV_BUDGET_YEAR_INVALID_STATE" in segunda.text
    vieja = _post(
        mundo,
        f"{P}/{detalle['id']}/categorias",
        "ua",
        mundo.company_a,
        {"nivel_orden": 1, "parent_id": None, "codigo": "99", "denominacion": "Vieja"},
        version=detalle["version"],
    )
    assert vieja.status_code == 409, vieja.text


@ONLY_PG
def test_historia_inmutable(mundo, gobierno):
    detalle = _crear(mundo, 2071)
    with mundo.factory() as session:
        fila = session.execute(
            select(GovernmentBudgetYearHistory).where(
                GovernmentBudgetYearHistory.year_id == detalle["id"]
            )
        ).scalars().first()
        session.delete(fila)
        with pytest.raises(DBAPIError):
            session.flush()
        session.rollback()
    completo = _completo(mundo, 2073)
    aprobado = _aprobar(mundo, completo)
    with mundo.factory() as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "UPDATE gov_budget_year_foundations SET referencia='x' WHERE year_id=:y"
                ),
                {"y": aprobado["id"]},
            )
            session.commit()
        session.rollback()
