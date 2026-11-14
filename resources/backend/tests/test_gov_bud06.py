"""BUD-06 · Disponibilidad presupuestaria y certificación (GOV-BUD-009/010)."""

from __future__ import annotations

import re
import threading
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from tests.org04_ayudantes import ANIO, nuevo_cargo
from tests.org06_guarda import cuenta_con_permisos, exigir_identidad
from tests.test_gov_bud01_ejercicio import ONLY_PG, P, _aprobar, _completo
from tests.test_gov_ctl06_hallazgos import _post

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

_ESTADO: dict[str, dict] = {}


def _preparar(mundo, ocupacion) -> dict:
    if "s" in _ESTADO:
        return _ESTADO["s"]
    if "error" in _ESTADO:
        pytest.fail(_ESTADO["error"])

    try:
        detalle = _completo(mundo, ANIO)
    except AssertionError as exc:
        _ESTADO["error"] = str(exc)
        raise

    # Partidas EGRESO adicionales 402, 403, 404
    for codigo, denominacion in [
        ("402", "Materiales"),
        ("403", "Servicios"),
        ("404", "Equipamiento"),
    ]:
        respuesta = _post(
            mundo,
            f"{P}/{detalle['id']}/clasificador/partidas",
            "ua",
            mundo.company_a,
            {
                "tipo": "EGRESO",
                "codigo": codigo,
                "denominacion": denominacion,
                "nivel": 1,
                "codigo_padre": None,
                "vigente_desde": None,
                "vigente_hasta": None,
            },
            version=detalle["version"],
        )
        assert respuesta.status_code == 201
        detalle["version"] = respuesta.json()["version"]

    # Fuente F01
    respuesta = _post(
        mundo,
        f"{P}/{detalle['id']}/fuentes",
        "ua",
        mundo.company_a,
        {
            "codigo": "F01",
            "denominacion": "Ingresos propios",
            "procedencia": "Ordenanza municipal de ingresos",
        },
        version=detalle["version"],
    )
    assert respuesta.status_code == 201
    detalle["version"] = respuesta.json()["version"]

    # Obtener ids de partidas iniciales
    partidas_resp = mundo.get(f"{P}/{detalle['id']}/clasificador/partidas", "ua", mundo.company_a)
    assert partidas_resp.status_code == 200
    partidas_ids = {}
    for p in partidas_resp.json()["items"]:
        partidas_ids[p["codigo"]] = p["id"]
    partida_301 = partidas_ids["301"]
    partida_401_01 = partidas_ids["401.01"]
    fuentes_resp = mundo.get(f"{P}/{detalle['id']}/fuentes", "ua", mundo.company_a)
    assert fuentes_resp.status_code == 200
    fuente_id = next(f["id"] for f in fuentes_resp.json()["items"] if f["codigo"] == "F01")

    # Ingreso 301
    respuesta = _post(
        mundo,
        f"{P}/{detalle['id']}/presupuesto-aprobado/ingresos",
        "ua",
        mundo.company_a,
        {"partida_id": partida_301, "monto": "10000.00"},
        version=detalle["version"],
    )
    assert respuesta.status_code == 201
    detalle["version"] = respuesta.json()["version"]

    # Obtener categoria 01.02
    detalle_get = mundo.get(f"{P}/{detalle['id']}", "ua", mundo.company_a)
    assert detalle_get.status_code == 200
    categorias = detalle_get.json()["categorias"]
    categoria_01_02 = next(c["id"] for c in categorias if c["codigo_completo"] == "01.02")

    # Créditos 01.02 para las partidas hoja
    creditos: dict[str, str] = {}
    for codigo in ["401.01", "402", "403", "404"]:
        partida_id = partida_401_01 if codigo == "401.01" else partidas_ids[codigo]
        respuesta = _post(
            mundo,
            f"{P}/{detalle['id']}/presupuesto-aprobado/creditos",
            "ua",
            mundo.company_a,
            {
                "categoria_id": categoria_01_02,
                "partida_id": partida_id,
                "fuente_id": fuente_id,
                "monto": "1000.00",
            },
            version=detalle["version"],
        )
        assert respuesta.status_code == 201
        detalle["version"] = respuesta.json()["version"]
        for credito in respuesta.json()["creditos"]:
            if credito["partida"]["codigo"] == codigo:
                creditos[codigo] = credito["id"]
                break

    # Releer detalle y aprobar
    detalle_releido = mundo.get(f"{P}/{detalle['id']}", "ua", mundo.company_a)
    assert detalle_releido.status_code == 200
    _aprobar(mundo, detalle_releido.json())

    cargo_id = nuevo_cargo(mundo, ocupacion)

    _ESTADO["s"] = {
        "year_id": detalle["id"],
        "creditos": creditos,
        "cargo_id": cargo_id,
    }
    return _ESTADO["s"]


def _certificar(mundo, year_id, credito_id, cargo_id, monto="300.00", concepto="Adquisición de material médico"):
    return _post(
        mundo,
        f"{P}/{year_id}/certificaciones",
        "ua",
        mundo.company_a,
        {
            "credito_id": credito_id,
            "monto": monto,
            "concepto": concepto,
            "expediente_referencia": "EXP-PRES-2026-001",
            "firmante_cargo_id": cargo_id,
        },
    )


@ONLY_PG
def test_vectores_a_b_c(mundo, gobierno, ocupacion):
    estado = _preparar(mundo, ocupacion)
    year_id = estado["year_id"]
    credito_id = estado["creditos"]["401.01"]

    # A
    r1 = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "300.00")
    assert r1.status_code == 201
    datos = r1.json()
    assert re.fullmatch(rf"CDP-{ANIO}-\d{{4}}", datos["codigo"])
    assert Decimal(datos["saldo_antes"]) == Decimal("1000.00")
    assert Decimal(datos["saldo_despues"]) == Decimal("700.00")

    # B
    r2 = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "700.00")
    assert r2.status_code == 201
    assert Decimal(r2.json()["saldo_antes"]) == Decimal("700.00")
    assert Decimal(r2.json()["saldo_despues"]) == Decimal("0.00")

    # C
    r3 = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "0.01")
    assert r3.status_code == 422
    assert r3.json()["code"] == "GOV_BUDGET_INSUFFICIENT_AVAILABILITY"
    assert r3.json()["details"]["disponible"] == "0.00"

    disp = mundo.get(f"{P}/{year_id}/disponibilidad?partida_id={partida_401_01_id(mundo, year_id)}", "ua", mundo.company_a)
    assert disp.status_code == 200
    for item in disp.json()["items"]:
        if item["credito_id"] == credito_id:
            assert Decimal(item["disponible"]) == Decimal("0.00")
            assert Decimal(item["certificado"]) == Decimal("1000.00")
            break

    certs = mundo.get(f"{P}/{year_id}/certificaciones", "ua", mundo.company_a)
    assert certs.status_code == 200
    items_del_credito = [i for i in certs.json()["items"] if i["credito_id"] == credito_id]
    assert len(items_del_credito) == 2


def partida_401_01_id(mundo, year_id):
    r = mundo.get(f"{P}/{year_id}/clasificador/partidas", "ua", mundo.company_a)
    assert r.status_code == 200
    return next(p["id"] for p in r.json()["items"] if p["codigo"] == "401.01")


@ONLY_PG
def test_vector_d_concurrencia(mundo, gobierno, ocupacion):
    estado = _preparar(mundo, ocupacion)
    year_id = estado["year_id"]
    credito_id = estado["creditos"]["402"]
    barrera = threading.Barrier(2, timeout=30)
    resultados: list[int] = []
    cuerpos: list[dict] = []

    cuerpo = {
        "credito_id": credito_id,
        "monto": "700.00",
        "concepto": "Adquisición de material médico",
        "expediente_referencia": "EXP-PRES-2026-001",
        "firmante_cargo_id": estado["cargo_id"],
    }

    cabeceras = mundo.como("ua", mundo.company_a)

    def emitir():
        barrera.wait()
        r = mundo.client.post(
            f"/api/v1{P}/{year_id}/certificaciones",
            headers=cabeceras,
            json=cuerpo,
        )
        resultados.append(r.status_code)
        cuerpos.append(r.json())

    hilos = [threading.Thread(target=emitir) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=35)

    assert sorted(resultados) == [201, 422]
    idx_422 = resultados.index(422)
    assert cuerpos[idx_422]["code"] == "GOV_BUDGET_INSUFFICIENT_AVAILABILITY"

    disp = mundo.get(f"{P}/{year_id}/disponibilidad?partida_id={partida_402_id(mundo, year_id)}", "ua", mundo.company_a)
    assert disp.status_code == 200
    for item in disp.json()["items"]:
        if item["credito_id"] == credito_id:
            assert Decimal(item["disponible"]) == Decimal("300.00")
            break


def partida_402_id(mundo, year_id):
    r = mundo.get(f"{P}/{year_id}/clasificador/partidas", "ua", mundo.company_a)
    assert r.status_code == 200
    return next(p["id"] for p in r.json()["items"] if p["codigo"] == "402")


@ONLY_PG
def test_vector_e_anulacion(mundo, gobierno, ocupacion):
    estado = _preparar(mundo, ocupacion)
    year_id = estado["year_id"]
    credito_id = estado["creditos"]["403"]

    r = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "300.00")
    assert r.status_code == 201
    cid = r.json()["id"]

    disp = mundo.get(f"{P}/{year_id}/disponibilidad?partida_id={partida_403_id(mundo, year_id)}", "ua", mundo.company_a)
    assert disp.status_code == 200
    for item in disp.json()["items"]:
        if item["credito_id"] == credito_id:
            assert Decimal(item["disponible"]) == Decimal("700.00")
            break

    anul = _post(mundo, f"{P}/{year_id}/certificaciones/{cid}/anular", "ua", mundo.company_a,
                 {"motivo": "Error en el expediente de origen"})
    assert anul.status_code == 200
    assert anul.json()["estado"] == "ANULADA"
    assert anul.json()["motivo_anulacion"] == "Error en el expediente de origen"

    disp = mundo.get(f"{P}/{year_id}/disponibilidad?partida_id={partida_403_id(mundo, year_id)}", "ua", mundo.company_a)
    assert disp.status_code == 200
    for item in disp.json()["items"]:
        if item["credito_id"] == credito_id:
            assert Decimal(item["disponible"]) == Decimal("1000.00")
            break

    anul2 = _post(mundo, f"{P}/{year_id}/certificaciones/{cid}/anular", "ua", mundo.company_a,
                  {"motivo": "Error en el expediente de origen"})
    assert anul2.status_code == 409
    assert anul2.json()["code"] == "GOV_BUDGET_CERTIFICATE_NOT_ACTIVE"

    # Otra certificación de 100.00 para anulación concurrente
    r_otra = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "100.00")
    assert r_otra.status_code == 201
    cid_otra = r_otra.json()["id"]

    barrera = threading.Barrier(2, timeout=30)
    resultados_concurrentes: list[int] = []

    cabeceras = mundo.como("ua", mundo.company_a)

    def anular_concurrente():
        barrera.wait()
        r = mundo.client.post(
            f"/api/v1{P}/{year_id}/certificaciones/{cid_otra}/anular",
            headers=cabeceras,
            json={"motivo": "Error en el expediente de origen"},
        )
        resultados_concurrentes.append(r.status_code)

    hilos = [threading.Thread(target=anular_concurrente) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join(timeout=35)

    assert sorted(resultados_concurrentes) == [200, 409]

    # Motivo corto
    r_corta = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "50.00")
    assert r_corta.status_code == 201
    cid_corta = r_corta.json()["id"]
    anul_corta = _post(mundo, f"{P}/{year_id}/certificaciones/{cid_corta}/anular", "ua", mundo.company_a,
                       {"motivo": "corto"})
    assert anul_corta.status_code == 422


def partida_403_id(mundo, year_id):
    r = mundo.get(f"{P}/{year_id}/clasificador/partidas", "ua", mundo.company_a)
    assert r.status_code == 200
    return next(p["id"] for p in r.json()["items"] if p["codigo"] == "403")


@ONLY_PG
def test_vector_f_aislamiento(mundo, gobierno, ocupacion):
    estado = _preparar(mundo, ocupacion)
    year_id = estado["year_id"]

    # Disponibilidad desde company_b
    r = mundo.get(f"{P}/{year_id}/disponibilidad", "ub", mundo.company_b)
    assert r.status_code == 404

    # POST certificación desde company_b
    r = _post(
        mundo,
        f"{P}/{year_id}/certificaciones",
        "ub",
        mundo.company_b,
        {
            "credito_id": estado["creditos"]["401.01"],
            "monto": "1.00",
            "concepto": "Adquisición de material médico",
            "expediente_referencia": "EXP-PRES-2026-001",
            "firmante_cargo_id": estado["cargo_id"],
        },
    )
    assert r.status_code == 404

    # Crear certificación en A para probar documento
    r_cert = _certificar(mundo, year_id, estado["creditos"]["404"], estado["cargo_id"], "1.00")
    assert r_cert.status_code == 201
    cid = r_cert.json()["id"]

    # GET documento desde company_b
    r = mundo.get(f"{P}/{year_id}/certificaciones/{cid}/documento", "ub", mundo.company_b)
    assert r.status_code == 404


@ONLY_PG
def test_validaciones(mundo, gobierno, ocupacion):
    estado = _preparar(mundo, ocupacion)
    year_id = estado["year_id"]
    credito_id = estado["creditos"]["404"]

    # Monto 0
    r = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "0")
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    # Monto 10.123
    r = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "10.123")
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    # Concepto corto
    r = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "30.00", concepto="corto")
    assert r.status_code == 422

    # Sin expediente_referencia ni expediente_id
    r = _post(
        mundo,
        f"{P}/{year_id}/certificaciones",
        "ua",
        mundo.company_a,
        {
            "credito_id": credito_id,
            "monto": "30.00",
            "concepto": "Adquisición de material médico",
            "firmante_cargo_id": estado["cargo_id"],
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_INVALID"

    # credito_id inexistente
    r = _post(
        mundo,
        f"{P}/{year_id}/certificaciones",
        "ua",
        mundo.company_a,
        {
            "credito_id": "00000000-0000-0000-0000-000000000000",
            "monto": "30.00",
            "concepto": "Adquisición de material médico",
            "expediente_referencia": "EXP-PRES-2026-001",
            "firmante_cargo_id": estado["cargo_id"],
        },
    )
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_BUDGET_CREDIT_NOT_FOUND"

    # Firmante con cargo de company_b
    cargo_b = nuevo_cargo(mundo, ocupacion, empresa=mundo.company_b)
    r = _post(
        mundo,
        f"{P}/{year_id}/certificaciones",
        "ua",
        mundo.company_a,
        {
            "credito_id": credito_id,
            "monto": "30.00",
            "concepto": "Adquisición de material médico",
            "expediente_referencia": "EXP-PRES-2026-001",
            "firmante_cargo_id": cargo_b,
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_CERTIFICATE_SIGNER_INVALID"

    # Firmante con cargo en BORRADOR
    cargo_borrador = nuevo_cargo(mundo, ocupacion, status="BORRADOR")
    r = _post(
        mundo,
        f"{P}/{year_id}/certificaciones",
        "ua",
        mundo.company_a,
        {
            "credito_id": credito_id,
            "monto": "30.00",
            "concepto": "Adquisición de material médico",
            "expediente_referencia": "EXP-PRES-2026-001",
            "firmante_cargo_id": cargo_borrador,
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_CERTIFICATE_SIGNER_INVALID"

    # Usuario con solo view
    cuenta_con_permisos(mundo, "solo_ver_b06", [("gobierno_presupuesto", "view")])
    disp = mundo.get(f"{P}/{year_id}/disponibilidad", "solo_ver_b06", mundo.company_a)
    assert disp.status_code == 200

    r = _post(
        mundo,
        f"{P}/{year_id}/certificaciones",
        "solo_ver_b06",
        mundo.company_a,
        {
            "credito_id": credito_id,
            "monto": "30.00",
            "concepto": "Adquisición de material médico",
            "expediente_referencia": "EXP-PRES-2026-001",
            "firmante_cargo_id": estado["cargo_id"],
        },
    )
    assert r.status_code == 403


@ONLY_PG
def test_autoridad_funcional(mundo, gobierno, ocupacion):
    estado = _preparar(mundo, ocupacion)
    year_id = estado["year_id"]
    exigir_identidad(mundo, exige=True)
    try:
        r = _certificar(mundo, year_id, estado["creditos"]["404"], estado["cargo_id"], "1.00")
        assert r.status_code == 403
        assert r.json()["code"] in {"GOV_IDENTITY_LINK_REQUIRED", "GOV_FUNCTIONAL_AUTHORITY_REQUIRED"}
    finally:
        exigir_identidad(mundo, exige=False)


@ONLY_PG
def test_documento_auditoria_historia(mundo, gobierno, ocupacion):
    estado = _preparar(mundo, ocupacion)
    year_id = estado["year_id"]
    credito_id = estado["creditos"]["404"]

    r = _certificar(mundo, year_id, credito_id, estado["cargo_id"], "50.00")
    assert r.status_code == 201
    cid = r.json()["id"]
    assert len(r.json()["huella"]) == 64
    assert len(r.json()["documento_sha256"]) == 64

    doc = mundo.get(f"{P}/{year_id}/certificaciones/{cid}/documento", "ua", mundo.company_a)
    assert doc.status_code == 200
    assert doc.headers["content-type"] == "application/pdf"
    assert doc.content.startswith(b"%PDF")

    anul = _post(mundo, f"{P}/{year_id}/certificaciones/{cid}/anular", "ua", mundo.company_a,
                 {"motivo": "Error en el expediente de origen"})
    assert anul.status_code == 200

    # Auditoría
    with mundo.factory() as session:
        eventos = session.execute(
            select(AuditEvent).where(
                AuditEvent.entity_type == "GovernmentBudgetYear",
                AuditEvent.entity_id == year_id,
            )
        ).scalars().all()
        acciones = [e.action for e in eventos]
        assert "GOV_BUDGET_CERTIFICATE_ISSUED" in acciones
        assert "GOV_BUDGET_CERTIFICATE_ANNULLED" in acciones

    # Historia del ejercicio
    detalle = mundo.get(f"{P}/{year_id}", "ua", mundo.company_a)
    assert detalle.status_code == 200
    tipos = [h["tipo"] for h in detalle.json()["historia"]]
    assert "CERTIFICACION_EMITIDA" in tipos
    assert "CERTIFICACION_ANULADA" in tipos


@ONLY_PG
def test_inmutable_en_base(mundo, gobierno, ocupacion):
    estado = _preparar(mundo, ocupacion)
    year_id = estado["year_id"]

    with mundo.factory() as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text("UPDATE gov_budget_certificates SET monto = 1 WHERE year_id = :y"),
                {"y": year_id},
            )
            session.commit()

    with mundo.factory() as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text("DELETE FROM gov_budget_certificates WHERE year_id = :y"),
                {"y": year_id},
            )
            session.commit()


@ONLY_PG
def test_mfa_y_catalogo(mundo, gobierno, ocupacion):
    assert "certify" in CATALOGO_DE_PERMISOS["gobierno_presupuesto"]
    assert classify(["gobierno_presupuesto:certify"]) == SENSITIVE


@ONLY_PG
def test_ejercicio_no_aprobado(mundo, gobierno, ocupacion):
    detalle_anterior = _completo(mundo, ANIO - 1)
    r = _post(
        mundo,
        f"{P}/{detalle_anterior['id']}/certificaciones",
        "ua",
        mundo.company_a,
        {
            "credito_id": "00000000-0000-0000-0000-000000000000",
            "monto": "1.00",
            "concepto": "Adquisición de material médico",
            "expediente_referencia": "EXP-PRES-2026-001",
            "firmante_cargo_id": nuevo_cargo(mundo, ocupacion),
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_YEAR_INVALID_STATE"
