"""BUD-08 · Compromisos presupuestarios (GOV-BUD-012)."""

from __future__ import annotations

import re
import threading
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentPosition,
    GovernmentPositionCompetency,
    GovernmentPositionVersion,
)
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.setup.api import CATALOGO_DE_PERMISOS
from tests.org04_ayudantes import ANIO, D, _codigo, nuevo_cargo
from tests.org06_guarda import cuenta_con_permisos, exigir_identidad
from tests.test_gov_bud01_ejercicio import ONLY_PG, P, _aprobar, _completo, _documento
from tests.test_gov_ctl06_hallazgos import _post

pytest_plugins = ("tests.conftest_multicompany", "tests.test_gov_ctl06_hallazgos", "tests.org04_ayudantes")

_ESTADO: dict[str, dict] = {}


def _cargo_comprometer(mundo, ocupacion, tipo_limite: str, monto: str | None, moneda: str | None) -> str:
    """Crea un cargo con competencia COMPROMETER × PRESUPUESTO con límite dado."""
    structure_id = ocupacion["estructura"]
    unit_id = ocupacion["unidad_raiz"]
    with mundo.factory() as db:
        cargo = GovernmentPosition(
            company_id=mundo.company_a,
            structure_id=structure_id,
            unit_id=unit_id,
            code=_codigo("C"),
            name=f"Cargo de prueba {_codigo('N')}",
            status="VIGENTE",
            valid_from=D(1, 1),
            valid_to=None,
            activated_at=datetime.now(UTC),
            version=1,
        )
        db.add(cargo)
        db.flush()

        comp = GovernmentPositionCompetency(
            position_id=cargo.id,
            company_id=mundo.company_a,
            action="COMPROMETER",
            subject="PRESUPUESTO",
            limit_type=tipo_limite,
            limit_amount=monto,
            limit_currency=moneda,
            basis="Fundamento de prueba",
        )
        db.add(comp)

        version = GovernmentPositionVersion(
            position_id=cargo.id,
            structure_id=structure_id,
            company_id=mundo.company_a,
            version=1,
            status="VIGENTE",
            snapshot={
                "competencias": [
                    {
                        "accion": "COMPROMETER",
                        "materia": "PRESUPUESTO",
                        "tipo_limite": tipo_limite,
                        "monto": monto,
                        "moneda": moneda,
                    }
                ]
            },
            reason=None,
            actor_id=None,
        )
        db.add(version)
        db.commit()
        return str(cargo.id)


def _preparar(mundo, ocupacion) -> dict:
    if "s" in _ESTADO:
        return _ESTADO["s"]
    if "error" in _ESTADO:
        pytest.fail(_ESTADO["error"])

    # ORG-03 admite límites en VES, USD o EUR; el ente de prueba opera en VES
    # para poder comparar el límite sin conversión.
    with mundo.factory() as db:
        db.execute(text("UPDATE companies SET functional_currency = 'VES' WHERE id = :c"), {"c": mundo.company_a})
        db.commit()

    try:
        detalle = _completo(mundo, ANIO)
    except AssertionError as exc:
        _ESTADO["error"] = str(exc)
        raise

    for codigo, denominacion in [
        ("402", "Materiales"),
        ("403", "Servicios"),
        ("404", "Equipamiento"),
        ("405", "Suministros"),
        ("406", "Transporte"),
        ("407", "Mantenimiento"),
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

    detalle_get = mundo.get(f"{P}/{detalle['id']}", "ua", mundo.company_a)
    assert detalle_get.status_code == 200
    categorias = detalle_get.json()["categorias"]
    categoria_01_02 = next(c["id"] for c in categorias if c["codigo_completo"] == "01.02")

    creditos: dict[str, str] = {}
    for codigo in ["401.01", "402", "403", "404", "405", "406", "407"]:
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

    detalle_releido = mundo.get(f"{P}/{detalle['id']}", "ua", mundo.company_a)
    assert detalle_releido.status_code == 200
    _aprobar(mundo, detalle_releido.json())

    moneda = detalle_releido.json().get("moneda_funcional") or detalle_get.json().get("moneda_funcional")
    otra = "USD" if moneda != "USD" else "EUR"
    firmante = nuevo_cargo(mundo, ocupacion)
    sin_limite = _cargo_comprometer(mundo, ocupacion, "SIN_LIMITE", None, None)
    con_limite = _cargo_comprometer(mundo, ocupacion, "MONTO", "500.00", moneda)
    otra_moneda = _cargo_comprometer(mundo, ocupacion, "MONTO", "500.00", otra)
    soporte = _documento(mundo, detalle["id"])
    cuenta_con_permisos(mundo, "compr_b08", [("gobierno_presupuesto", "view"), ("gobierno_presupuesto", "commit")])
    cuenta_con_permisos(mundo, "solo_ver_b08", [("gobierno_presupuesto", "view")])

    _ESTADO["s"] = {
        "year_id": detalle["id"],
        "creditos": creditos,
        "partidas": partidas_ids,
        "firmante": firmante,
        "sin_limite": sin_limite,
        "con_limite": con_limite,
        "otra_moneda": otra_moneda,
        "soporte": soporte,
        "moneda": moneda,
    }
    return _ESTADO["s"]


def _cdp(mundo, s, codigo_partida, monto, referencia="EXP-PRES-2026-001") -> dict:
    r = _post(
        mundo,
        f"{P}/{s['year_id']}/certificaciones",
        "ua",
        mundo.company_a,
        {
            "credito_id": s["creditos"][codigo_partida],
            "monto": monto,
            "concepto": "Adquisición de material médico",
            "expediente_referencia": referencia,
            "firmante_cargo_id": s["firmante"],
        },
    )
    assert r.status_code == 201
    return r.json()


def _comprometer(mundo, s, lineas, cargo=None, usuario="compr_b08", soporte=None, concepto="Orden de compra de material médico"):
    return _post(
        mundo,
        f"{P}/{s['year_id']}/compromisos",
        usuario,
        mundo.company_a,
        {
            "concepto": concepto,
            "autoridad_cargo_id": cargo or s["sin_limite"],
            "soporte_documento_id": soporte or s["soporte"],
            "lineas": lineas,
        },
    )


def _disponible(mundo, s, codigo_partida) -> Decimal:
    r = mundo.get(
        f"{P}/{s['year_id']}/disponibilidad?partida_id={s['partidas'][codigo_partida]}",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200
    for item in r.json()["items"]:
        if item["credito_id"] == s["creditos"][codigo_partida]:
            return Decimal(item["disponible"])
    pytest.fail(f"Crédito {codigo_partida} no está en la disponibilidad")


def _cert(mundo, s, cid) -> dict:
    r = mundo.get(f"{P}/{s['year_id']}/certificaciones/{cid}", "ua", mundo.company_a)
    assert r.status_code == 200
    return r.json()


@ONLY_PG
def test_vectores_a_b_c(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "401.01", "300.00")
    assert _disponible(mundo, s, "401.01") == Decimal("700.00")

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "200.00"}])
    assert r.status_code == 201
    body = r.json()
    assert re.fullmatch(rf"CP-{ANIO}-\d{{4}}", body["codigo"])
    assert Decimal(body["total"]) == Decimal("200.00")
    assert _disponible(mundo, s, "401.01") == Decimal("700.00")
    cert = _cert(mundo, s, cdp["id"])
    assert Decimal(cert["consumido"]) == Decimal("200.00")
    assert Decimal(cert["remanente"]) == Decimal("100.00")
    assert cert["situacion"] == "PARCIALMENTE_CONSUMIDA"

    disp = mundo.get(f"{P}/{s['year_id']}/disponibilidad?partida_id={s['partidas']['401.01']}", "ua", mundo.company_a)
    assert disp.status_code == 200
    for item in disp.json()["items"]:
        if item["credito_id"] == s["creditos"]["401.01"]:
            assert Decimal(item["certificado"]) == Decimal("300.00")
            assert Decimal(item["comprometido"]) == Decimal("200.00")
            break

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "100.01"}])
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_CERTIFICATE_INSUFFICIENT_REMAINING"
    assert r.json()["details"]["remanente"] == "100.00"

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "100.00"}])
    assert r.status_code == 201
    cert = _cert(mundo, s, cdp["id"])
    assert Decimal(cert["remanente"]) == Decimal("0.00")
    assert cert["situacion"] == "AGOTADA"
    assert _disponible(mundo, s, "401.01") == Decimal("700.00")

    r = mundo.get(f"{P}/{s['year_id']}/compromisos/opciones", "compr_b08", mundo.company_a)
    assert r.status_code == 200
    ids = [c["certificado_id"] for c in r.json()["certificados"]]
    assert cdp["id"] not in ids


@ONLY_PG
def test_vector_d_concurrencia(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "402", "1000.00")
    barrera = threading.Barrier(2, timeout=30)
    resultados: list[int] = []
    cuerpos: list[dict] = []

    cuerpo = {
        "concepto": "Orden de compra de material médico",
        "autoridad_cargo_id": s["sin_limite"],
        "soporte_documento_id": s["soporte"],
        "lineas": [{"certificado_id": cdp["id"], "monto": "700.00"}],
    }
    cabeceras = mundo.como("compr_b08", mundo.company_a)

    def emitir():
        barrera.wait()
        r = mundo.client.post(
            f"/api/v1{P}/{s['year_id']}/compromisos",
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
    assert cuerpos[idx_422]["code"] == "GOV_BUDGET_CERTIFICATE_INSUFFICIENT_REMAINING"
    cert = _cert(mundo, s, cdp["id"])
    assert Decimal(cert["consumido"]) == Decimal("700.00")


@ONLY_PG
def test_vector_e_f_anulacion(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "403", "300.00")
    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "200.00"}])
    assert r.status_code == 201
    cid = r.json()["id"]

    r = _post(mundo, f"{P}/{s['year_id']}/certificaciones/{cdp['id']}/anular", "ua", mundo.company_a, {"motivo": "Error en el expediente de origen"})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_CERTIFICATE_IN_USE"

    r = _post(mundo, f"{P}/{s['year_id']}/compromisos/{cid}/anular", "compr_b08", mundo.company_a, {"motivo": "Error en la orden de compra"})
    assert r.status_code == 200
    assert r.json()["estado"] == "ANULADO"
    cert = _cert(mundo, s, cdp["id"])
    assert Decimal(cert["remanente"]) == Decimal("300.00")
    assert cert["situacion"] == "DISPONIBLE"
    assert _disponible(mundo, s, "403") == Decimal("700.00")

    r = _post(mundo, f"{P}/{s['year_id']}/compromisos/{cid}/anular", "compr_b08", mundo.company_a, {"motivo": "Error en la orden de compra"})
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_COMMITMENT_NOT_ACTIVE"

    r2 = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}])
    assert r2.status_code == 201
    cid2 = r2.json()["id"]
    r = _post(mundo, f"{P}/{s['year_id']}/compromisos/{cid2}/anular", "compr_b08", mundo.company_a, {"motivo": "corto"})
    assert r.status_code == 422

    r = _post(mundo, f"{P}/{s['year_id']}/compromisos/{cid2}/anular", "compr_b08", mundo.company_a, {"motivo": "Motivo suficientemente largo"})
    assert r.status_code == 200

    r = _post(mundo, f"{P}/{s['year_id']}/certificaciones/{cdp['id']}/anular", "ua", mundo.company_a, {"motivo": "Ya sin uso"})
    assert r.status_code == 200
    assert _disponible(mundo, s, "403") == Decimal("1000.00")


@ONLY_PG
def test_vectores_g_h_i_limite(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "404", "1000.00")

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "400.00"}], cargo=s["con_limite"])
    assert r.status_code == 201

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "500.01"}], cargo=s["con_limite"])
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_COMMITMENT_AUTHORITY_AMOUNT_EXCEEDED"

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}], cargo=s["otra_moneda"])
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_COMMITMENT_AUTHORITY_CURRENCY_MISMATCH"

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}], cargo=s["firmante"])
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_COMMITMENT_AUTHORITY_INVALID"


@ONLY_PG
def test_vector_j_multilinea(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp_a = _cdp(mundo, s, "405", "600.00")
    cdp_b = _cdp(mundo, s, "406", "500.00")
    assert _disponible(mundo, s, "405") == Decimal("400.00")
    assert _disponible(mundo, s, "406") == Decimal("500.00")

    r = _comprometer(mundo, s, [
        {"certificado_id": cdp_a["id"], "monto": "400.00"},
        {"certificado_id": cdp_b["id"], "monto": "300.00"},
    ])
    assert r.status_code == 201
    body = r.json()
    assert Decimal(body["total"]) == Decimal("700.00")
    assert len(body["lineas"]) == 2
    assert body["lineas"][0]["linea"] == 1
    assert body["lineas"][1]["linea"] == 2
    assert Decimal(_cert(mundo, s, cdp_a["id"])["remanente"]) == Decimal("200.00")
    assert Decimal(_cert(mundo, s, cdp_b["id"])["remanente"]) == Decimal("200.00")
    assert _disponible(mundo, s, "405") == Decimal("400.00")
    assert _disponible(mundo, s, "406") == Decimal("500.00")

    r = _comprometer(mundo, s, [
        {"certificado_id": cdp_a["id"], "monto": "10.00"},
        {"certificado_id": cdp_a["id"], "monto": "10.00"},
    ])
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_INVALID"

    cdp_c = _cdp(mundo, s, "405", "50.00", referencia="EXP-OTRO-2026-009")
    r = _comprometer(mundo, s, [
        {"certificado_id": cdp_a["id"], "monto": "10.00"},
        {"certificado_id": cdp_c["id"], "monto": "10.00"},
    ])
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_COMMITMENT_EXPEDIENTE_MISMATCH"


@ONLY_PG
def test_sod_quien_certifica_no_compromete(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "407", "300.00")

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}], usuario="ua")
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_SOD_CONFLICT"
    assert cdp["codigo"] in r.json()["details"]["certificados"]

    with mundo.factory() as session:
        eventos = session.execute(
            select(AuditEvent).where(
                AuditEvent.entity_type == "GovernmentBudgetYear",
                AuditEvent.entity_id == s["year_id"],
                AuditEvent.action == "GOV_BUDGET_COMMITMENT_SOD_BLOCKED",
            )
        ).scalars().all()
        assert len(eventos) > 0

    cert = _cert(mundo, s, cdp["id"])
    assert Decimal(cert["consumido"]) == Decimal("0.00")


@ONLY_PG
def test_validaciones(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "407", "50.00")

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "0"}])
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.123"}])
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    r = _comprometer(mundo, s, [])
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    cuerpo = {
        "concepto": "Orden de compra de material médico",
        "autoridad_cargo_id": s["sin_limite"],
        "soporte_documento_id": s["soporte"],
        "lineas": [{"certificado_id": cdp["id"], "monto": "10.00"}],
        "total": "10.00",
    }
    r = _post(mundo, f"{P}/{s['year_id']}/compromisos", "compr_b08", mundo.company_a, cuerpo)
    assert r.status_code == 422
    assert r.json()["code"] == "VALIDATION_ERROR"

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}], soporte="00000000-0000-0000-0000-000000000000")
    assert r.status_code == 422
    assert r.json()["code"] == "GOV_BUDGET_INVALID_DOCUMENT"

    r = _comprometer(mundo, s, [{"certificado_id": "00000000-0000-0000-0000-000000000000", "monto": "10.00"}])
    assert r.status_code == 404
    assert r.json()["code"] == "GOV_BUDGET_CERTIFICATE_NOT_FOUND"

    r = mundo.get(f"{P}/{s['year_id']}/compromisos/opciones", "solo_ver_b08", mundo.company_a)
    assert r.status_code == 200

    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}], usuario="solo_ver_b08")
    assert r.status_code == 403


@ONLY_PG
def test_autoridad_funcional(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "407", "50.00")
    exigir_identidad(mundo, exige=True)
    try:
        r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "1.00"}])
        assert r.status_code == 403
        assert r.json()["code"] in {"GOV_IDENTITY_LINK_REQUIRED", "GOV_FUNCTIONAL_AUTHORITY_REQUIRED"}
    finally:
        exigir_identidad(mundo, exige=False)


@ONLY_PG
def test_aislamiento(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "407", "20.00")
    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}])
    assert r.status_code == 201
    cid = r.json()["id"]

    r = mundo.get(f"{P}/{s['year_id']}/compromisos", "ub", mundo.company_b)
    assert r.status_code == 404
    r = mundo.get(f"{P}/{s['year_id']}/compromisos/opciones", "ub", mundo.company_b)
    assert r.status_code == 404
    r = _post(mundo, f"{P}/{s['year_id']}/compromisos", "ub", mundo.company_b, {
        "concepto": "Orden de compra de material médico",
        "autoridad_cargo_id": s["sin_limite"],
        "soporte_documento_id": s["soporte"],
        "lineas": [{"certificado_id": cdp["id"], "monto": "10.00"}],
    })
    assert r.status_code == 404
    r = mundo.get(f"{P}/{s['year_id']}/compromisos/{cid}/documento", "ub", mundo.company_b)
    assert r.status_code == 404


@ONLY_PG
def test_documento_auditoria_historia(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "407", "100.00")
    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "50.00"}])
    assert r.status_code == 201
    cid = r.json()["id"]
    assert len(r.json()["huella"]) == 64
    assert len(r.json()["documento_sha256"]) == 64
    assert len(r.json()["soporte_sha256"]) == 64

    doc = mundo.get(f"{P}/{s['year_id']}/compromisos/{cid}/documento", "compr_b08", mundo.company_a)
    assert doc.status_code == 200
    assert doc.headers["content-type"] == "application/pdf"
    assert doc.content.startswith(b"%PDF")

    r = _post(mundo, f"{P}/{s['year_id']}/compromisos/{cid}/anular", "compr_b08", mundo.company_a, {"motivo": "Error en la orden"})
    assert r.status_code == 200

    with mundo.factory() as session:
        eventos = session.execute(
            select(AuditEvent).where(
                AuditEvent.entity_type == "GovernmentBudgetYear",
                AuditEvent.entity_id == s["year_id"],
            )
        ).scalars().all()
        acciones = [e.action for e in eventos]
        assert "GOV_BUDGET_COMMITMENT_ISSUED" in acciones
        assert "GOV_BUDGET_COMMITMENT_ANNULLED" in acciones

    detalle = mundo.get(f"{P}/{s['year_id']}", "ua", mundo.company_a)
    assert detalle.status_code == 200
    tipos = [h["tipo"] for h in detalle.json()["historia"]]
    assert "COMPROMISO_REGISTRADO" in tipos
    assert "COMPROMISO_ANULADO" in tipos

    r = mundo.get(f"{P}/{s['year_id']}/compromisos/{cid}", "compr_b08", mundo.company_a)
    assert r.status_code == 200
    assert r.json()["estado"] == "ANULADO"


@ONLY_PG
def test_inmutable_en_base(mundo, gobierno, ocupacion):
    s = _preparar(mundo, ocupacion)
    cdp = _cdp(mundo, s, "407", "100.00")
    r = _comprometer(mundo, s, [{"certificado_id": cdp["id"], "monto": "10.00"}])
    assert r.status_code == 201

    with mundo.factory() as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text("UPDATE gov_budget_commitment_lines SET monto = 1 WHERE year_id = :y"),
                {"y": s["year_id"]},
            )
            session.commit()

    with mundo.factory() as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text("DELETE FROM gov_budget_commitment_lines WHERE year_id = :y"),
                {"y": s["year_id"]},
            )
            session.commit()

    with mundo.factory() as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text("UPDATE gov_budget_commitments SET concepto = 'Cambio no permitido' WHERE year_id = :y"),
                {"y": s["year_id"]},
            )
            session.commit()

    with mundo.factory() as session:
        with pytest.raises(DBAPIError):
            session.execute(
                text("DELETE FROM gov_budget_commitments WHERE year_id = :y"),
                {"y": s["year_id"]},
            )
            session.commit()


@ONLY_PG
def test_mfa_y_catalogo(mundo, gobierno, ocupacion):
    assert "commit" in CATALOGO_DE_PERMISOS["gobierno_presupuesto"]
    assert classify(["gobierno_presupuesto:commit"]) == SENSITIVE


@ONLY_PG
def test_ejercicio_no_aprobado(mundo, gobierno, ocupacion):
    detalle = _completo(mundo, ANIO - 1)
    r = _post(
        mundo,
        f"{P}/{detalle['id']}/compromisos",
        "compr_b08",
        mundo.company_a,
        {
            "concepto": "Orden de compra de material médico",
            "autoridad_cargo_id": "00000000-0000-0000-0000-000000000000",
            "soporte_documento_id": "00000000-0000-0000-0000-000000000000",
            "lineas": [{"certificado_id": "00000000-0000-0000-0000-000000000000", "monto": "10.00"}],
        },
    )
    assert r.status_code == 409
    assert r.json()["code"] == "GOV_BUDGET_YEAR_INVALID_STATE"
