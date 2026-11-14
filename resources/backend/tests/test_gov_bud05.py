"""BUD-05 · Presupuesto aprobado: ingresos, créditos, existencias del Tesoro y cuadre LOPPM 240."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import GovernmentBudgetYearFoundation
from app.shared.clock import hoy_de_negocio
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud01_ejercicio import ONLY_PG, P, _aprobar, _completo, _delete, _documento, _patch, _put
from tests.test_gov_ctl06_hallazgos import _post

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")


@ONLY_PG
def test_ingresos(mundo, gobierno):
    anio = 2091
    detalle = _completo(mundo, anio)
    id_ejercicio, v = detalle["id"], detalle["version"]
    a = f"{P}/{id_ejercicio}/presupuesto-aprobado"

    # Necesitamos el id de la partida RECURSO 301 (hoja).
    r = mundo.get(f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a)
    assert r.status_code == 200
    partida_301 = next(p for p in r.json()["items"] if p["codigo"] == "301")
    egreso_401_01 = next(p for p in r.json()["items"] if p["codigo"] == "401.01")

    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "1000000.00"}, version=v)
    assert r.status_code == 201
    v = r.json()["version"]
    assert Decimal(r.json()["totales"]["ingresos"]) == Decimal("1000000.00")

    # Duplicado.
    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "200000.00"}, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_INCOME_DUPLICATE"

    # Partida de egreso inválida.
    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": egreso_401_01["id"], "monto": "10.00"}, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_INVALID"

    # Montos inválidos.
    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "0"}, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "10.123"}, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    r = mundo.get(a, "ua", mundo.company_a)
    assert r.status_code == 200
    ingreso_id = r.json()["ingresos"][0]["id"]
    v = r.json()["version"]

    # PATCH válido.
    r = _patch(mundo, f"{a}/ingresos/{ingreso_id}", "ua", mundo.company_a, {"monto": "900000.50"}, version=v)
    assert r.status_code == 200
    v = r.json()["version"]
    assert Decimal(r.json()["totales"]["ingresos"]) == Decimal("900000.50")

    # DELETE.
    r = _delete(mundo, f"{a}/ingresos/{ingreso_id}", "ua", mundo.company_a, version=v)
    assert r.status_code == 200
    assert r.json()["ingresos"] == []
    assert Decimal(r.json()["totales"]["ingresos"]) == Decimal("0.00")


@ONLY_PG
def test_creditos(mundo, gobierno):
    anio = 2092
    detalle = _completo(mundo, anio)
    id_ejercicio, v = detalle["id"], detalle["version"]
    a = f"{P}/{id_ejercicio}/presupuesto-aprobado"

    # Crear fuente F01.
    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes", "ua", mundo.company_a, {"codigo": "F01", "denominacion": "Ingresos propios", "procedencia": "Ordenanza municipal de ingresos"}, v)
    assert r.status_code == 201
    v = r.json()["version"]
    fuente_id = next(f for f in r.json()["items"] if f["codigo"] == "F01")["id"]

    # Partidas y categorías.
    r = mundo.get(f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a)
    partida_401_01 = next(p for p in r.json()["items"] if p["codigo"] == "401.01")
    partida_401 = next(p for p in r.json()["items"] if p["codigo"] == "401")
    partida_301 = next(p for p in r.json()["items"] if p["codigo"] == "301")

    categoria_01_02 = next(c for c in detalle["categorias"] if c["codigo_completo"] == "01.02")
    categoria_01 = next(c for c in detalle["categorias"] if c["codigo_completo"] == "01")

    # Crédito válido.
    cuerpo = {
        "categoria_id": categoria_01_02["id"],
        "partida_id": partida_401_01["id"],
        "fuente_id": fuente_id,
        "monto": "600000.00",
    }
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, cuerpo, version=v)
    assert r.status_code == 201
    v = r.json()["version"]
    assert r.json()["creditos"][0]["categoria"]["codigo_completo"] == "01.02"
    assert r.json()["creditos"][0]["partida"]["codigo"] == "401.01"
    assert r.json()["creditos"][0]["fuente"]["codigo"] == "F01"

    # Duplicado.
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, cuerpo, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_CREDIT_DUPLICATE"

    # Categoría padre.
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {**cuerpo, "categoria_id": categoria_01["id"]}, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_INVALID"

    # Partida padre.
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {**cuerpo, "partida_id": partida_401["id"]}, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_INVALID"

    # Partida recurso.
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {**cuerpo, "partida_id": partida_301["id"]}, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_INVALID"

    # Monto negativo.
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {**cuerpo, "monto": "-5"}, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    # PATCH.
    r = mundo.get(a, "ua", mundo.company_a)
    credito_id = r.json()["creditos"][0]["id"]
    v = r.json()["version"]
    r = _patch(mundo, f"{a}/creditos/{credito_id}", "ua", mundo.company_a, {"monto": "650000.00"}, version=v)
    assert r.status_code == 200
    assert Decimal(r.json()["creditos"][0]["monto"]) == Decimal("650000.00")

    # Opciones.
    r = mundo.get(a, "ua", mundo.company_a)
    categorias = [c["codigo_completo"] for c in r.json()["opciones"]["categorias"]]
    partidas_egreso = [p["codigo"] for p in r.json()["opciones"]["partidas_egreso"]]
    assert "01.02" in categorias
    assert "01" not in categorias
    assert "401.01" in partidas_egreso
    assert "401" not in partidas_egreso


@ONLY_PG
def test_restricciones(mundo, gobierno):
    anio = 2093
    detalle = _completo(mundo, anio)
    id_ejercicio, v = detalle["id"], detalle["version"]
    a = f"{P}/{id_ejercicio}/presupuesto-aprobado"

    # Partidas.
    r = mundo.get(f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a)
    partida_401_01 = next(p for p in r.json()["items"] if p["codigo"] == "401.01")
    categoria_01_02 = next(c for c in detalle["categorias"] if c["codigo_completo"] == "01.02")

    # Crear partida EGRESO 402.
    r = _post(mundo, f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a, {
        "tipo": "EGRESO", "codigo": "402", "denominacion": "Materiales", "nivel": 1,
        "codigo_padre": None, "vigente_desde": date(anio, 1, 1).isoformat(), "vigente_hasta": date(anio, 12, 31).isoformat(),
    }, version=v)
    assert r.status_code == 201
    v = r.json()["version"]
    partidas_respuesta = mundo.get(f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a).json()["items"]
    partida_402 = next(p for p in partidas_respuesta if p["codigo"] == "402")

    # Fuente F01 con restricción ["401"].
    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes", "ua", mundo.company_a, {"codigo": "F01", "denominacion": "Ingresos propios", "procedencia": "Ordenanza municipal de ingresos"}, v)
    assert r.status_code == 201
    v = r.json()["version"]
    fuente_f01 = next(f for f in r.json()["items"] if f["codigo"] == "F01")

    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes/{fuente_f01['id']}/restricciones", "ua", mundo.company_a, {
        "descripcion": "Afectación legal", "fundamento": "LOPPM art. 246", "partidas": ["401"],
    }, version=v)
    assert r.status_code == 201
    v = r.json()["version"]
    restriccion_f01 = next(f for f in r.json()["items"] if f["codigo"] == "F01")
    rid_401 = next(rid for rid in restriccion_f01.get("restricciones", []) if "401" in rid.get("partidas", []))["id"]

    # Crédito con 402 restringido.
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {
        "categoria_id": categoria_01_02["id"], "partida_id": partida_402["id"], "fuente_id": fuente_f01["id"], "monto": "100.00",
    }, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_CREDIT_SOURCE_RESTRICTED"

    # Crédito con 401.01 pasa (401 cubre a hija).
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {
        "categoria_id": categoria_01_02["id"], "partida_id": partida_401_01["id"], "fuente_id": fuente_f01["id"], "monto": "100.00",
    }, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    # Opciones.fuentes.
    r = mundo.get(a, "ua", mundo.company_a)
    f01_opciones = next(f for f in r.json()["opciones"]["fuentes"] if f["codigo"] == "F01")
    assert f01_opciones["partidas_permitidas"] == ["401"]

    # Añadir restricción ["402"] amplía la unión.
    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes/{fuente_f01['id']}/restricciones", "ua", mundo.company_a, {
        "descripcion": "Ampliación", "fundamento": "LOPPM art. 247", "partidas": ["402"],
    }, version=v)
    assert r.status_code == 201
    v = r.json()["version"]
    restriccion_f01 = next(f for f in r.json()["items"] if f["codigo"] == "F01")

    # Quitar restricción ["401"] dejaría fuera el crédito 401.01.
    r = _delete(mundo, f"{P}/{id_ejercicio}/fuentes/{fuente_f01['id']}/restricciones/{rid_401}", "ua", mundo.company_a, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_FUNDING_RESTRICTION_CONFLICT"

    # Fuente F02 sin restricciones admite 402.
    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes", "ua", mundo.company_a, {"codigo": "F02", "denominacion": "Otra", "procedencia": "Ordenanza municipal de ingresos"}, version=v)
    assert r.status_code == 201
    v = r.json()["version"]
    fuente_f02 = next(f for f in r.json()["items"] if f["codigo"] == "F02")
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {
        "categoria_id": categoria_01_02["id"], "partida_id": partida_402["id"], "fuente_id": fuente_f02["id"], "monto": "100.00",
    }, version=v)
    assert r.status_code == 201


@ONLY_PG
def test_cuadre_y_aprobacion(mundo, gobierno):
    anio = hoy_de_negocio().year + 1
    detalle = _completo(mundo, anio)
    id_ejercicio, v = detalle["id"], detalle["version"]
    a = f"{P}/{id_ejercicio}/presupuesto-aprobado"

    # Ingreso 301.
    r = mundo.get(f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a)
    partida_301 = next(p for p in r.json()["items"] if p["codigo"] == "301")
    partida_401_01 = next(p for p in r.json()["items"] if p["codigo"] == "401.01")
    categoria_01_02 = next(c for c in detalle["categorias"] if c["codigo_completo"] == "01.02")

    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "1000000.00"}, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    # Fuente F01.
    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes", "ua", mundo.company_a, {"codigo": "F01", "denominacion": "Ingresos propios", "procedencia": "Ordenanza municipal de ingresos"}, v)
    assert r.status_code == 201
    v = r.json()["version"]
    fuente_id = next(f for f in r.json()["items"] if f["codigo"] == "F01")["id"]

    # Crédito mayor que ingreso.
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {
        "categoria_id": categoria_01_02["id"], "partida_id": partida_401_01["id"], "fuente_id": fuente_id, "monto": "1200000.00",
    }, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    r = mundo.get(a, "ua", mundo.company_a)
    assert r.json()["totales"]["cuadra"] is False
    v = r.json()["version"]

    # Aprobar desbalanceado.
    fecha_aprobacion = hoy_de_negocio() if hoy_de_negocio().year <= anio else date(anio, 12, 31)
    r = _post(mundo, f"{P}/{id_ejercicio}/aprobar", "ua", mundo.company_a, {
        "referencia": "Gaceta Municipal N.º 1", "fecha": fecha_aprobacion.isoformat(), "documento_id": _documento(mundo, id_ejercicio),
    }, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_UNBALANCED"
    assert Decimal(r.json()["details"]["exceso"]) == Decimal("200000.00")

    # Existencias del Tesoro.
    r = _put(mundo, f"{a}/existencias-tesoro", "ua", mundo.company_a, {
        "monto": "400000.00", "fecha_corte": hoy_de_negocio().isoformat(), "documento_id": _documento(mundo, id_ejercicio),
    }, version=v)
    assert r.status_code == 200
    v = r.json()["version"]
    assert Decimal(r.json()["totales"]["holgura_tesoro"]) == Decimal("200000.00")
    assert Decimal(r.json()["totales"]["disponible"]) == Decimal("1200000.00")
    assert r.json()["totales"]["cuadra"] is True

    # Aprobar.
    detalle["version"] = v
    _aprobar(mundo, detalle)

    # Fotografía en la fundación.
    with mundo.factory() as session:
        fundacion = session.execute(select(GovernmentBudgetYearFoundation).where(GovernmentBudgetYearFoundation.year_id == id_ejercicio)).scalar_one()
        fotografia = fundacion.fotografia["presupuesto_aprobado"]
        assert len(fotografia["creditos"]) == 1
        assert fotografia["creditos"][0]["monto"] == "1200000.00"
        assert "ingresos" in fotografia
        assert "existencias_tesoro" in fotografia
        assert "totales" in fotografia


@ONLY_PG
def test_existencias_invalidas(mundo, gobierno):
    anio = hoy_de_negocio().year
    detalle = _completo(mundo, anio)
    id_ejercicio, v = detalle["id"], detalle["version"]
    a = f"{P}/{id_ejercicio}/presupuesto-aprobado"

    futura = hoy_de_negocio() + timedelta(days=400)
    r = _put(mundo, f"{a}/existencias-tesoro", "ua", mundo.company_a, {
        "monto": "1.00", "fecha_corte": futura.isoformat(), "documento_id": _documento(mundo, id_ejercicio),
    }, version=v)
    assert r.status_code == 422

    # Documento inexistente.
    r = _put(mundo, f"{a}/existencias-tesoro", "ua", mundo.company_a, {
        "monto": "1.00", "fecha_corte": hoy_de_negocio().isoformat(), "documento_id": "00000000-0000-0000-0000-000000000000",
    }, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_INVALID_DOCUMENT"

    # DELETE sin existencias.
    r = _delete(mundo, f"{a}/existencias-tesoro", "ua", mundo.company_a, version=v)
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_BUDGET_TREASURY_HOLDINGS_NOT_FOUND"

    # PUT válido.
    r = _put(mundo, f"{a}/existencias-tesoro", "ua", mundo.company_a, {
        "monto": "1.00", "fecha_corte": date(anio - 1, 12, 31).isoformat(), "documento_id": _documento(mundo, id_ejercicio),
    }, version=v)
    assert r.status_code == 200
    v = r.json()["version"]

    # DELETE válido.
    r = _delete(mundo, f"{a}/existencias-tesoro", "ua", mundo.company_a, version=v)
    assert r.status_code == 200
    assert r.json()["existencias_tesoro"] is None


@ONLY_PG
def test_congelado(mundo, gobierno):
    anio = 2096
    detalle = _completo(mundo, anio)
    id_ejercicio, v = detalle["id"], detalle["version"]
    a = f"{P}/{id_ejercicio}/presupuesto-aprobado"

    # Configurar y aprobar.
    r = mundo.get(f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a)
    partida_301 = next(p for p in r.json()["items"] if p["codigo"] == "301")
    partida_401_01 = next(p for p in r.json()["items"] if p["codigo"] == "401.01")
    categoria_01_02 = next(c for c in detalle["categorias"] if c["codigo_completo"] == "01.02")

    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "1000000.00"}, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes", "ua", mundo.company_a, {"codigo": "F01", "denominacion": "Ingresos propios", "procedencia": "Ordenanza municipal de ingresos"}, v)
    assert r.status_code == 201
    v = r.json()["version"]
    fuente_id = next(f for f in r.json()["items"] if f["codigo"] == "F01")["id"]

    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {
        "categoria_id": categoria_01_02["id"], "partida_id": partida_401_01["id"], "fuente_id": fuente_id, "monto": "1000000.00",
    }, version=v)
    assert r.status_code == 201
    credito_id = r.json()["creditos"][0]["id"]
    v = r.json()["version"]

    detalle["version"] = v
    _aprobar(mundo, detalle)

    r = mundo.get(a, "ua", mundo.company_a)
    assert r.json()["congelado"] is True
    v = r.json()["version"]

    # Mutaciones rechazadas por congelado.
    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "1.00"}, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_YEAR_FROZEN"

    r = _patch(mundo, f"{a}/creditos/{credito_id}", "ua", mundo.company_a, {"monto": "2.00"}, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_YEAR_FROZEN"

    r = _delete(mundo, f"{a}/creditos/{credito_id}", "ua", mundo.company_a, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_YEAR_FROZEN"

    r = _put(mundo, f"{a}/existencias-tesoro", "ua", mundo.company_a, {
        "monto": "1.00", "fecha_corte": date(anio - 1, 12, 31).isoformat(), "documento_id": _documento(mundo, id_ejercicio),
    }, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_YEAR_FROZEN"

    # Trigger.
    with pytest.raises(DBAPIError):
        with mundo.factory() as session:
            session.execute(text("UPDATE gov_budget_credits SET monto = 1 WHERE year_id = :y"), {"y": id_ejercicio})
            session.commit()


@ONLY_PG
def test_en_uso(mundo, gobierno):
    anio = 2097
    detalle = _completo(mundo, anio)
    id_ejercicio, v = detalle["id"], detalle["version"]
    a = f"{P}/{id_ejercicio}/presupuesto-aprobado"

    r = mundo.get(f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a)
    partida_301 = next(p for p in r.json()["items"] if p["codigo"] == "301")
    partida_401_01 = next(p for p in r.json()["items"] if p["codigo"] == "401.01")
    categoria_01_02 = next(c for c in detalle["categorias"] if c["codigo_completo"] == "01.02")

    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "100.00"}, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes", "ua", mundo.company_a, {"codigo": "F01", "denominacion": "Ingresos propios", "procedencia": "Ordenanza municipal de ingresos"}, v)
    assert r.status_code == 201
    v = r.json()["version"]
    fuente = next(f for f in r.json()["items"] if f["codigo"] == "F01")

    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {
        "categoria_id": categoria_01_02["id"], "partida_id": partida_401_01["id"], "fuente_id": fuente["id"], "monto": "100.00",
    }, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    # Borrar fuente en uso.
    r = _delete(mundo, f"{P}/{id_ejercicio}/fuentes/{fuente['id']}", "ua", mundo.company_a, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_FUNDING_SOURCE_IN_USE"

    # Borrar partida de egreso en uso.
    r = _delete(mundo, f"{P}/{id_ejercicio}/clasificador/partidas/{partida_401_01['id']}", "ua", mundo.company_a, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_ITEM_IN_USE"

    # Borrar partida de ingreso en uso.
    r = _delete(mundo, f"{P}/{id_ejercicio}/clasificador/partidas/{partida_301['id']}", "ua", mundo.company_a, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_ITEM_IN_USE"

    # Borrar categoría en uso.
    r = _delete(mundo, f"{P}/{id_ejercicio}/categorias/{categoria_01_02['id']}", "ua", mundo.company_a, version=v)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_CATEGORY_IN_USE"


@ONLY_PG
def test_no_imputable_al_fijar(mundo, gobierno):
    anio = 2098
    detalle = _completo(mundo, anio)
    id_ejercicio, v = detalle["id"], detalle["version"]
    a = f"{P}/{id_ejercicio}/presupuesto-aprobado"

    r = mundo.get(f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a)
    partida_301 = next(p for p in r.json()["items"] if p["codigo"] == "301")
    partida_401_01 = next(p for p in r.json()["items"] if p["codigo"] == "401.01")
    categoria_01_02 = next(c for c in detalle["categorias"] if c["codigo_completo"] == "01.02")

    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "1000000.00"}, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes", "ua", mundo.company_a, {"codigo": "F01", "denominacion": "Ingresos propios", "procedencia": "Ordenanza municipal de ingresos"}, v)
    assert r.status_code == 201
    v = r.json()["version"]
    fuente_id = next(f for f in r.json()["items"] if f["codigo"] == "F01")["id"]

    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {
        "categoria_id": categoria_01_02["id"], "partida_id": partida_401_01["id"], "fuente_id": fuente_id, "monto": "1000000.00",
    }, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    # Intentar crear categoría hija de 01.02.
    r = _post(mundo, f"{P}/{id_ejercicio}/categorias", "ua", mundo.company_a, {
        "nivel_orden": 2, "parent_id": categoria_01_02["id"], "codigo": "03", "denominacion": "Sub",
    }, version=v)
    if r.status_code == 201:
        v = r.json()["version"]
    else:
        assert r.status_code == 422
        # Alternativa: partida EGRESO "401.01.01" de nivel 3, hija de "401.01".
        r = _post(mundo, f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a, {
            "tipo": "EGRESO", "codigo": "401.01.01", "denominacion": "Subpartida", "nivel": 3,
            "codigo_padre": "401.01", "vigente_desde": date(anio, 1, 1).isoformat(), "vigente_hasta": date(anio, 12, 31).isoformat(),
        }, version=v)
        assert r.status_code == 201
        v = r.json()["version"]

    detalle["version"] = v
    fecha_aprobacion = hoy_de_negocio() if hoy_de_negocio().year <= anio else date(anio, 12, 31)
    r = _post(mundo, f"{P}/{id_ejercicio}/aprobar", "ua", mundo.company_a, {
        "referencia": "Gaceta Municipal N.º 1", "fecha": fecha_aprobacion.isoformat(), "documento_id": _documento(mundo, id_ejercicio),
    }, version=v)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_NOT_IMPUTABLE"


@ONLY_PG
def test_auditoria_historia_aislamiento_permisos(mundo, gobierno):
    anio = 2099
    detalle = _completo(mundo, anio)
    id_ejercicio, v = detalle["id"], detalle["version"]
    a = f"{P}/{id_ejercicio}/presupuesto-aprobado"

    r = mundo.get(f"{P}/{id_ejercicio}/clasificador/partidas", "ua", mundo.company_a)
    partida_301 = next(p for p in r.json()["items"] if p["codigo"] == "301")
    partida_401_01 = next(p for p in r.json()["items"] if p["codigo"] == "401.01")
    categoria_01_02 = next(c for c in detalle["categorias"] if c["codigo_completo"] == "01.02")

    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "100.00"}, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    r = _post(mundo, f"{P}/{id_ejercicio}/fuentes", "ua", mundo.company_a, {"codigo": "F01", "denominacion": "Ingresos propios", "procedencia": "Ordenanza municipal de ingresos"}, v)
    assert r.status_code == 201
    v = r.json()["version"]
    fuente_id = next(f for f in r.json()["items"] if f["codigo"] == "F01")["id"]

    v_anterior = v
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {
        "categoria_id": categoria_01_02["id"], "partida_id": partida_401_01["id"], "fuente_id": fuente_id, "monto": "100.00",
    }, version=v)
    assert r.status_code == 201
    v = r.json()["version"]

    # Historia del detalle.
    r = mundo.get(f"{P}/{id_ejercicio}", "ua", mundo.company_a)
    tipos = [h["tipo"] for h in r.json()["historia"]]
    assert "INGRESO_REGISTRADO" in tipos
    assert "CREDITO_REGISTRADO" in tipos

    # AuditEvent.
    with mundo.factory() as session:
        acciones = list(session.execute(
            select(AuditEvent.action).where(AuditEvent.entity_type == "GovernmentBudgetYear", AuditEvent.entity_id == id_ejercicio)
        ).scalars())
    assert "GOV_BUDGET_INCOME_ESTIMATE_CREATED" in acciones
    assert "GOV_BUDGET_CREDIT_CREATED" in acciones

    # Aislamiento multiempresa.
    r = mundo.get(a, "ub", mundo.company_b)
    assert r.status_code == 404

    r = _post(mundo, f"{a}/creditos", "ub", mundo.company_b, {
        "categoria_id": categoria_01_02["id"], "partida_id": partida_401_01["id"], "fuente_id": fuente_id, "monto": "1.00",
    }, version=v)
    assert r.status_code == 404

    # Permisos: GET view, POST rechazado.
    cuenta_con_permisos(mundo, "usuario_nuevo", [("gobierno_presupuesto", "view")])
    r = mundo.get(a, "usuario_nuevo", mundo.company_a)
    assert r.status_code == 200

    r = _post(mundo, f"{a}/ingresos", "usuario_nuevo", mundo.company_a, {"partida_id": partida_301["id"], "monto": "1.00"}, version=v)
    assert r.status_code == 403

    # If-Match obsoleto.
    version_obsoleta = v_anterior
    r = _post(mundo, f"{a}/ingresos", "ua", mundo.company_a, {"partida_id": partida_301["id"], "monto": "1.00"}, version=version_obsoleta)
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_YEAR_STALE"

    # Categoría de otro ejercicio.
    otro = _completo(mundo, 2083)
    categoria_otro = next(c for c in otro["categorias"] if c["codigo_completo"] == "01.02")
    r = mundo.get(a, "ua", mundo.company_a)
    v_actual = r.json()["version"]
    r = _post(mundo, f"{a}/creditos", "ua", mundo.company_a, {
        "categoria_id": categoria_otro["id"], "partida_id": partida_401_01["id"], "fuente_id": fuente_id, "monto": "1.00",
    }, version=v_actual)
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_INVALID"


