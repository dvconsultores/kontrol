"""TRE-05 · Retenciones (TRE-05, parte B: casos 16–30) — pruebas backend."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.government.models import (
    GovernmentWithholdingReceipt,
    GovernmentWithholdingSettlement,
)
from app.modules.government.service_sod import CATALOGO_SOD
from app.modules.identity_access.mfa_policy import SENSITIVE, classify
from app.modules.identity_access.models import User
from app.shared.clock import hoy_de_negocio
from tests.org06_guarda import cuenta_con_permisos
from tests.test_gov_bud01_ejercicio import ONLY_PG
from tests.test_gov_tre03_orden_pago import _get_op, _post_op, _put_op
from tests.tre05_ayudantes import (
    R,
    aislar_caches,
    aprobar_liq,
    calcular,
    cargo_aprobador,
    concepto,
    cuentas_t05,
    pago_actual,
    pago_listo,
    politica_ret,
    registrar_pago,
    regla,
)

pytest_plugins = (
    "tests.conftest_multicompany",
    "tests.test_gov_ctl06_hallazgos",
    "tests.org04_ayudantes",
)


@pytest.fixture(scope="module", autouse=True)
def _aislar_caches_t05():
    aislar_caches()
    yield
    aislar_caches()


def test_t05_16_bruto_neto_tope_sustraendo(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    s = datos["s"]
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, orden=1, tasa="10", sustraendo="1.00", tope="3.00")],
    )
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    assert liq.status_code == 201, liq.text
    data = liq.json()

    bruto = Decimal(data["bruto"])
    total = Decimal(data["total_retenido"])
    neto = Decimal(data["neto"])
    assert bruto == total + neto
    assert total == Decimal("3.00")
    assert neto == Decimal("97.00")

    # GET del pago incluye retenciones
    pg = pago_actual(mundo, pago["id"])
    ret = pg["retenciones"]
    assert Decimal(ret["bruto"]) == Decimal("100.00")
    assert Decimal(ret["total_retenido"]) == Decimal("3.00")
    assert Decimal(ret["neto"]) == Decimal("97.00")

    # Dos reglas que suman 110% → EXCEEDS_GROSS, sobre OTRO pago
    datos2 = pago_listo(mundo, ocupacion, monto="100.00")
    c2 = concepto(mundo)
    pol2 = politica_ret(
        mundo,
        s["moneda"],
        [
            regla(c, orden=1, tasa="60"),
            regla(c2, orden=2, tasa="50"),
        ],
    )
    r2 = calcular(mundo, datos2["pago"], pol2, [c["codigo"], c2["codigo"]])
    assert r2.status_code == 422, r2.text
    assert r2.json()["code"] == "GOV_WITHHOLDING_EXCEEDS_GROSS"


def test_t05_17_decimal_redondeo_down(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    s = datos["s"]
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, orden=1, tasa="7.9")],
        redondeo_decimales=0,
        redondeo_modo="DOWN",
    )
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    assert liq.status_code == 201, liq.text
    data = liq.json()

    assert Decimal(data["total_retenido"]) == Decimal("7")
    assert data["total_retenido"] in ("7.00", "7")
    line = data["lineas"][0]
    assert Decimal(line["monto_calculado"]) == Decimal("7")
    # str de montos
    assert isinstance(data["total_retenido"], str)


def test_t05_18_moneda_mismatch(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(mundo, "USD", [regla(c)])
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    assert liq.status_code == 422, liq.text
    assert liq.json()["code"] == "GOV_WITHHOLDING_CURRENCY_MISMATCH"


def test_t05_19_fecha_referencia_negocio(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    s = datos["s"]
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(mundo, s["moneda"], [regla(c)])
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    assert liq.status_code == 201, liq.text
    data = liq.json()

    assert data["fecha_referencia"] == hoy_de_negocio().isoformat()
    pg = pago_actual(mundo, pago["id"])
    assert pg["fecha_pago"] == hoy_de_negocio().isoformat()


def test_t05_20_ajuste_prohibido(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    s = datos["s"]
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, tasa="5")],
        permite_ajuste=False,
    )
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    assert liq.status_code == 201, liq.text
    data = liq.json()
    line = data["lineas"][0]

    r = _put_op(
        mundo,
        f"{R}/liquidaciones/{data['id']}/lineas/{line['id']}",
        "rt_mk",
        {"monto_aprobado": "3.00", "motivo": "Ajuste manual de monto"},
        version=data["version"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_ADJUSTMENT_FORBIDDEN"


def test_t05_21_ajuste_permitido_y_auditoria(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    s = datos["s"]
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, tasa="5")],
        permite_ajuste=True,
    )
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    assert liq.status_code == 201, liq.text
    data = liq.json()
    line = data["lineas"][0]

    # Ajuste válido
    r = _put_op(
        mundo,
        f"{R}/liquidaciones/{data['id']}/lineas/{line['id']}",
        "rt_mk",
        {"monto_aprobado": "3.00", "motivo": "Ajuste manual de monto"},
        version=data["version"],
    )
    assert r.status_code == 200, r.text
    adj = r.json()

    assert Decimal(adj["lineas"][0]["monto_calculado"]) == Decimal("5.00")
    assert Decimal(adj["lineas"][0]["monto_aprobado"]) == Decimal("3.00")
    assert adj["lineas"][0]["motivo_ajuste"] == "Ajuste manual de monto"
    assert adj["lineas"][0]["ajustado_por"] is not None
    assert Decimal(adj["total_retenido"]) == Decimal("3.00")

    # Auditoría ADJUSTED
    with mundo.factory() as db:
        ev = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_WITHHOLDING_ADJUSTED",
                AuditEvent.entity_id == data["id"],
            )
        ).all()
        assert len(ev) == 1

    # Motivo corto → 422 ADJUSTMENT_INVALID
    r2 = _put_op(
        mundo,
        f"{R}/liquidaciones/{data['id']}/lineas/{line['id']}",
        "rt_mk",
        {"monto_aprobado": "2.00", "motivo": "corto"},
        version=adj["version"],
    )
    assert r2.status_code == 422, r2.text
    assert r2.json()["code"] == "GOV_WITHHOLDING_ADJUSTMENT_INVALID"

    # Monto > base → 422 ADJUSTMENT_INVALID
    r3 = _put_op(
        mundo,
        f"{R}/liquidaciones/{data['id']}/lineas/{line['id']}",
        "rt_mk",
        {"monto_aprobado": "200.00", "motivo": "Monto excede la base"},
        version=adj["version"],
    )
    assert r3.status_code == 422, r3.text
    assert r3.json()["code"] == "GOV_WITHHOLDING_ADJUSTMENT_INVALID"


def test_t05_22_aprobacion_y_autoridad(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    s = datos["s"]
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(mundo, s["moneda"], [regla(c, tasa="5")])
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    assert liq.status_code == 201, liq.text
    data = liq.json()

    # Cargo sin APROBAR → 422 AUTHORITY_INVALID
    cargo_malo = cargo_aprobador(mundo, ocupacion, accion="PAGAR", materia="TESORERIA")
    r = _post_op(
        mundo,
        f"{R}/liquidaciones/{data['id']}/aprobar",
        "rt_ck",
        {"cargo_id": cargo_malo},
        version=data["version"],
    )
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_AUTHORITY_INVALID"

    # Cargo correcto → APROBADA con huella
    cargo_ok = cargo_aprobador(mundo, ocupacion, accion="APROBAR", materia="TESORERIA")
    r2 = _post_op(
        mundo,
        f"{R}/liquidaciones/{data['id']}/aprobar",
        "rt_ck",
        {"cargo_id": cargo_ok},
        version=data["version"],
    )
    assert r2.status_code == 200, r2.text
    aprob = r2.json()
    assert aprob["estado"] == "APROBADA"
    assert aprob["huella"] is not None

    # Auditoría APPROVED
    with mundo.factory() as db:
        ev = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_WITHHOLDING_APPROVED",
                AuditEvent.entity_id == data["id"],
            )
        ).all()
        assert len(ev) == 1


def test_t05_23_mfa_clasificacion(mundo, gobierno, ocupacion):
    assert classify({"gobierno_retenciones:policy"}) == SENSITIVE
    assert classify({"gobierno_retenciones:approve"}) == SENSITIVE
    assert classify({"gobierno_retenciones:cancel"}) == SENSITIVE
    assert classify({"gobierno_retenciones:view"}) != SENSITIVE
    assert classify({"gobierno_retenciones:manage"}) != SENSITIVE
    assert classify({"gobierno_retenciones:calculate"}) != SENSITIVE


def test_t05_24_ctl01_y_maker_checker(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    s = datos["s"]
    pago = datos["pago"]

    # CTL-01
    assert "TRE-05" in CATALOGO_SOD
    assert "TRE05_CALCULAR" in CATALOGO_SOD["TRE-05"]["acciones"]
    assert "TRE05_APROBAR" in CATALOGO_SOD["TRE-05"]["acciones"]

    # Usuario con calculate+approve (rt_mix)
    with mundo.factory() as db:
        if db.scalar(select(User).where(User.username == "rt_mix")) is None:
            cuenta_con_permisos(
                mundo,
                "rt_mix",
                [
                    ("gobierno_retenciones", "view"),
                    ("gobierno_retenciones", "calculate"),
                    ("gobierno_retenciones", "approve"),
                    ("gobierno_pagos", "view"),
                ],
            )

    c = concepto(mundo)
    pol = politica_ret(mundo, s["moneda"], [regla(c, tasa="5")])

    # rt_mix calcula
    liq = calcular(mundo, pago, pol, [c["codigo"]], usuario="rt_mix")
    assert liq.status_code == 201, liq.text
    data = liq.json()

    # rt_mix intenta aprobar → 409 MAKER_CHECKER
    cargo_ok = cargo_aprobador(mundo, ocupacion, accion="APROBAR", materia="TESORERIA")
    r = _post_op(
        mundo,
        f"{R}/liquidaciones/{data['id']}/aprobar",
        "rt_mix",
        {"cargo_id": cargo_ok},
        version=data["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_MAKER_CHECKER"


def test_t05_25_comprobante_exigido_y_aplicacion(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00", autorizado=True)
    s = datos["s"]
    pago = datos["pago"]

    c1 = concepto(mundo)
    c2 = concepto(mundo)
    pol = politica_ret(
        mundo,
        s["moneda"],
        [
            regla(c1, orden=1, tasa="5", exige_comprobante=True),
            regla(c2, orden=2, tasa="3", exige_comprobante=False),
        ],
    )
    liq = calcular(mundo, pago, pol, [c1["codigo"], c2["codigo"]])
    assert liq.status_code == 201, liq.text
    data = liq.json()

    # CALCULADA → registrar 409 PENDING_APPROVAL
    r = registrar_pago(mundo, pago["id"], "REF-CALC")
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_PENDING_APPROVAL"

    # Aprobar y registrar → APLICADA + comprobante
    cargo = cargo_aprobador(mundo, ocupacion, accion="APROBAR", materia="TESORERIA")
    aprobar_liq(mundo, data, cargo)

    r2 = registrar_pago(mundo, pago["id"], "REF-APROB")
    assert r2.status_code in (200, 201), r2.text

    # Liquidación APLICADA
    pg = pago_actual(mundo, pago["id"])
    ret = pg["retenciones"]
    assert ret["definitivo"] is True

    # Un comprobante para c1
    r3 = mundo.client.get(f"/api/v1{R}/comprobantes", headers=mundo.como("rt_mk"))
    assert r3.status_code == 200, r3.text
    comps = r3.json()
    comps_c1 = [cp for cp in comps if cp.get("concepto_codigo") == c1["codigo"]]
    comps_c2 = [cp for cp in comps if cp.get("concepto_codigo") == c2["codigo"]]
    assert len(comps_c1) == 1
    assert len(comps_c2) == 0

    # Auditoría APPLIED y RECEIPT_ISSUED
    with mundo.factory() as db:
        ev_applied = db.scalars(
            select(AuditEvent).where(AuditEvent.action == "GOV_WITHHOLDING_APPLIED")
        ).all()
        assert len(ev_applied) >= 1
        ev_receipt = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "GOV_WITHHOLDING_RECEIPT_ISSUED"
            )
        ).all()
        assert len(ev_receipt) == 1


def test_t05_26_numeracion_patron(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00", autorizado=True)
    s = datos["s"]

    # Configurar patrón de numeración
    r = _get_op(mundo, f"{R}/configuracion", "rt_mk")
    assert r.status_code == 200, r.text
    cfg = r.json()
    patron = "R{SERIE}-{ANIO}-{NUMERO:4}"
    r2 = _put_op(
        mundo,
        f"{R}/configuracion",
        "rt_mk",
        {"patron": patron},
        version=cfg["version"],
    )
    assert r2.status_code == 200, r2.text
    cfg2 = r2.json()

    # Concepto con serie
    c = concepto(mundo, serie="ISX")

    # Primer pago aplicado
    pol = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, orden=1, tasa="5", exige_comprobante=True)],
    )
    liq1 = calcular(mundo, datos["pago"], pol, [c["codigo"]])
    data1 = liq1.json()
    cargo = cargo_aprobador(mundo, ocupacion, accion="APROBAR", materia="TESORERIA")
    aprobar_liq(mundo, data1, cargo)
    registrar_pago(mundo, datos["pago"]["id"], "REF-NUM-1")

    # Segundo pago aplicado
    datos2 = pago_listo(mundo, ocupacion, monto="100.00", autorizado=True)
    liq2 = calcular(mundo, datos2["pago"], pol, [c["codigo"]])
    data2 = liq2.json()
    aprobar_liq(mundo, data2, cargo)
    registrar_pago(mundo, datos2["pago"]["id"], "REF-NUM-2")

    # Obtener comprobantes
    r3 = mundo.client.get(f"/api/v1{R}/comprobantes", headers=mundo.como("rt_mk"))
    assert r3.status_code == 200, r3.text
    comps = r3.json()
    anio = hoy_de_negocio().year
    codigos = sorted(
        [cp["codigo"] for cp in comps if cp["codigo"].startswith(f"RISX-{anio}-")]
    )
    assert len(codigos) == 2
    n1 = int(codigos[0].split("-")[-1])
    n2 = int(codigos[1].split("-")[-1])
    assert n2 == n1 + 1

    # Patrón sin {NUMERO:n} → 422 PATTERN_INVALID
    r4 = _put_op(
        mundo,
        f"{R}/configuracion",
        "rt_mk",
        {"patron": "R{SERIE}-{ANIO}"},
        version=cfg2["version"],
    )
    assert r4.status_code == 422, r4.text
    assert r4.json()["code"] == "GOV_WITHHOLDING_PATTERN_INVALID"


def test_t05_27_instantanea_comprobante_pdf_inmutable(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00", autorizado=True)
    s = datos["s"]
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, orden=1, tasa="5", exige_comprobante=True)],
    )
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    data = liq.json()
    cargo = cargo_aprobador(mundo, ocupacion, accion="APROBAR", materia="TESORERIA")
    aprobar_liq(mundo, data, cargo)
    registrar_pago(mundo, pago["id"], "REF-SNAP")

    # Obtener comprobante
    r = mundo.client.get(f"/api/v1{R}/comprobantes", headers=mundo.como("rt_mk"))
    comps = r.json()
    comp = [cp for cp in comps if cp.get("concepto_codigo") == c["codigo"]][0]

    r2 = mundo.client.get(
        f"/api/v1{R}/comprobantes/{comp['id']}", headers=mundo.como("rt_mk")
    )
    assert r2.status_code == 200, r2.text
    snap = r2.json()["snapshot"]

    assert snap["beneficiario"]["declarado"] is True
    assert snap["pago"]["codigo"] == pago["codigo"]
    assert len(snap["lineas"]) == 1
    assert Decimal(snap["total"]) == Decimal("5.00")
    assert snap["politica"]["fuente_descripcion"] == "Acto del ente de prueba"

    # PDF
    r3 = mundo.client.get(
        f"/api/v1{R}/comprobantes/{comp['id']}/pdf", headers=mundo.como("rt_mk")
    )
    assert r3.status_code == 200, r3.text
    assert r3.headers["content-type"] == "application/pdf"
    assert r3.content.startswith(b"%PDF")

    # Crear nueva versión de la política → snapshot y huella no cambian
    nueva = _post_op(
        mundo,
        f"{R}/politicas/{pol['id']}/nueva-version",
        "rt_mk",
        {},
        version=pol["version"],
    )
    assert nueva.status_code == 201, nueva.text
    nv = nueva.json()
    cuerpo_v2 = {
        "codigo": pol["codigo"],
        "nombre": pol["nombre"],
        "moneda": s["moneda"],
        "aprobador_competencia_accion": "APROBAR",
        "aprobador_competencia_materia": "TESORERIA",
        "vigente_desde": hoy_de_negocio().isoformat(),
        "reglas": [regla(c, orden=1, tasa="7", exige_comprobante=True)],
        "fuente_descripcion": pol.get("fuente_descripcion", "Acto del ente de prueba"),
    }
    r5 = _put_op(
        mundo,
        f"{R}/politicas/{nv['id']}",
        "rt_mk",
        cuerpo_v2,
        version=nv["version"],
    )
    assert r5.status_code == 200, r5.text
    nv_act = r5.json()
    act = _post_op(
        mundo,
        f"{R}/politicas/{nv['id']}/activar",
        "rt_mk",
        {"fundamento": "Fundamento suficiente para activar version nueva"},
        version=nv_act["version"],
    )
    assert act.status_code == 200, act.text

    r4 = mundo.client.get(
        f"/api/v1{R}/comprobantes/{comp['id']}", headers=mundo.como("rt_mk")
    )
    snap2 = r4.json()["snapshot"]
    assert snap2 == snap
    assert r4.json()["huella"] == r2.json()["huella"]


def test_t05_28_version_congelada(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00")
    s = datos["s"]
    pagov1 = datos["pago"]

    hoy = hoy_de_negocio()
    vigencia_v1 = hoy - timedelta(days=1)
    vigencia_v2 = hoy

    # v1 con vigente_desde explícito
    c = concepto(mundo)
    pol_v1 = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, orden=1, tasa="5")],
        vigente_desde=vigencia_v1.isoformat(),
    )

    liq_a = calcular(mundo, pagov1, pol_v1, [c["codigo"]])
    assert liq_a.status_code == 201, liq_a.text
    data_a = liq_a.json()
    assert data_a["policy_numero_version"] == 1
    assert Decimal(data_a["total_retenido"]) == Decimal("5.00")

    # v2 activada con 7%
    nueva = _post_op(
        mundo,
        f"{R}/politicas/{pol_v1['id']}/nueva-version",
        "rt_mk",
        {},
        version=pol_v1["version"],
    )
    assert nueva.status_code == 201, nueva.text
    nv = nueva.json()
    cuerpo_v2 = {
        "codigo": pol_v1["codigo"],
        "nombre": pol_v1["nombre"],
        "moneda": s["moneda"],
        "aprobador_competencia_accion": "APROBAR",
        "aprobador_competencia_materia": "TESORERIA",
        "vigente_desde": vigencia_v2.isoformat(),
        "reglas": [regla(c, orden=1, tasa="7")],
        "fuente_descripcion": pol_v1.get("fuente_descripcion", "Acto del ente de prueba"),
    }
    r_put = _put_op(
        mundo,
        f"{R}/politicas/{nv['id']}",
        "rt_mk",
        cuerpo_v2,
        version=nv["version"],
    )
    assert r_put.status_code == 200, r_put.text
    pol_v2 = r_put.json()
    r_act = _post_op(
        mundo,
        f"{R}/politicas/{nv['id']}/activar",
        "rt_mk",
        {"fundamento": "Fundamento suficiente para activar version nueva"},
        version=pol_v2["version"],
    )
    assert r_act.status_code == 200, r_act.text

    datos2 = pago_listo(mundo, ocupacion, monto="100.00")
    pago_b = datos2["pago"]
    liq_b = calcular(mundo, pago_b, pol_v2, [c["codigo"]])
    assert liq_b.status_code == 201, liq_b.text
    data_b = liq_b.json()
    assert data_b["policy_numero_version"] == 2
    assert Decimal(data_b["total_retenido"]) == Decimal("7.00")

    # A sigue en versión 1 con 5%
    r = _get_op(mundo, f"{R}/liquidaciones/{data_a['id']}", "rt_mk")
    assert r.status_code == 200, r.text
    assert r.json()["policy_numero_version"] == 1
    assert Decimal(r.json()["total_retenido"]) == Decimal("5.00")


def test_t05_29_frontera_anulacion_descarre_rechazo(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00", autorizado=True)
    s = datos["s"]
    pago = datos["pago"]

    # Liquidación APLICADA → anular 409 APPLIED_IMMUTABLE
    c = concepto(mundo)
    pol = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, orden=1, tasa="5", exige_comprobante=True)],
    )
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    data = liq.json()
    cargo = cargo_aprobador(mundo, ocupacion, accion="APROBAR", materia="TESORERIA")
    aprobar_liq(mundo, data, cargo)
    registrar_pago(mundo, pago["id"], "REF-ANUL")

    data = _get_op(mundo, f"{R}/liquidaciones/{data['id']}", "rt_mk").json()
    r = _post_op(
        mundo,
        f"{R}/liquidaciones/{data['id']}/anular",
        "rt_ck",
        {"motivo": "Anulación de prueba"},
        version=data["version"],
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "GOV_WITHHOLDING_APPLIED_IMMUTABLE"

    # Anular comprobante con sustituir → nuevo EMITIDO, original ANULADO
    r2 = mundo.client.get(f"/api/v1{R}/comprobantes", headers=mundo.como("rt_mk"))
    comp = [cp for cp in r2.json() if cp.get("concepto_codigo") == c["codigo"]][0]

    r3 = _post_op(
        mundo,
        f"{R}/comprobantes/{comp['id']}/anular",
        "rt_ck",
        {
            "motivo": "Corrección de beneficiario",
            "sustituir": True,
            "beneficiario": {
                "nombre": "Proveedor Corregido S.A.",
            },
        },
    )
    assert r3.status_code == 200, r3.text
    anulado = r3.json()
    assert anulado["estado"] == "ANULADO"
    assert anulado["sustituido_por_id"] is not None

    # Nuevo comprobante EMITIDO
    r4 = mundo.client.get(
        f"/api/v1{R}/comprobantes/{anulado['sustituido_por_id']}",
        headers=mundo.como("rt_mk"),
    )
    assert r4.status_code == 200, r4.text
    nuevo = r4.json()
    assert nuevo["estado"] == "EMITIDO"
    assert nuevo["sustituye_a_id"] == comp["id"]
    assert nuevo["snapshot"]["beneficiario"]["nombre"] == "Proveedor Corregido S.A."
    assert Decimal(nuevo["monto"]) == Decimal(comp["monto"])

    # Anular de nuevo → 409 RECEIPT_ALREADY_CANCELLED
    r5 = _post_op(
        mundo,
        f"{R}/comprobantes/{comp['id']}/anular",
        "rt_ck",
        {"motivo": "Anular otra vez", "sustituir": False},
    )
    assert r5.status_code == 409, r5.text
    assert r5.json()["code"] == "GOV_WITHHOLDING_RECEIPT_ALREADY_CANCELLED"

    # Descartar una CALCULADA → ANULADA
    datos2 = pago_listo(mundo, ocupacion, monto="100.00")
    c2 = concepto(mundo)
    pol2 = politica_ret(mundo, s["moneda"], [regla(c2, orden=1, tasa="5")])
    liq2 = calcular(mundo, datos2["pago"], pol2, [c2["codigo"]])
    data2 = liq2.json()
    r6 = _post_op(
        mundo,
        f"{R}/liquidaciones/{data2['id']}/descartar",
        "rt_mk",
        {"motivo": "Descartar cálculo de prueba"},
        version=data2["version"],
    )
    assert r6.status_code == 200, r6.text
    assert r6.json()["estado"] == "ANULADA"

    # Rechazar pago PENDIENTE_AUTORIZACION con liquidación CALCULADA → liquidación ANULADA
    datos3 = pago_listo(mundo, ocupacion, monto="100.00")
    c3 = concepto(mundo)
    pol3 = politica_ret(mundo, s["moneda"], [regla(c3, orden=1, tasa="5")])
    liq3 = calcular(mundo, datos3["pago"], pol3, [c3["codigo"]])
    data3 = liq3.json()

    from tests.test_gov_tre04_pago import _enviar, _rechazar

    _enviar(mundo, datos3["pago"])
    pago3_pend = pago_actual(mundo, datos3["pago"]["id"])
    cargo_rech = cargo_aprobador(mundo, ocupacion, accion="PAGAR", materia="TESORERIA")
    _rechazar(mundo, pago3_pend, cargo_rech)

    r7 = _get_op(mundo, f"{R}/liquidaciones/{data3['id']}", "rt_mk")
    assert r7.status_code == 200, r7.text
    assert r7.json()["estado"] == "ANULADA"


@ONLY_PG
def test_t05_29b_guardas_bd(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00", autorizado=True)
    s = datos["s"]
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, orden=1, tasa="5", exige_comprobante=True)],
    )
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    data = liq.json()
    cargo = cargo_aprobador(mundo, ocupacion, accion="APROBAR", materia="TESORERIA")
    aprobar_liq(mundo, data, cargo)
    registrar_pago(mundo, pago["id"], "REF-GUARDAS")

    r = mundo.client.get(f"/api/v1{R}/comprobantes", headers=mundo.como("rt_mk"))
    comp = [cp for cp in r.json() if cp.get("concepto_codigo") == c["codigo"]][0]

    with mundo.factory() as db:
        rec = db.get(GovernmentWithholdingReceipt, comp["id"])
        assert rec is not None

        # DELETE de un comprobante → DBAPIError
        db.delete(rec)
        with pytest.raises(DBAPIError):
            db.commit()
        db.rollback()

        # UPDATE del bruto de una liquidación APLICADA → DBAPIError
        liq_db = db.get(GovernmentWithholdingSettlement, data["id"])
        assert liq_db is not None
        liq_db.bruto = Decimal("999.99")
        with pytest.raises(DBAPIError):
            db.commit()


def test_t05_30_integracion_tre04(mundo, gobierno, ocupacion):
    cuentas_t05(mundo)
    datos = pago_listo(mundo, ocupacion, monto="100.00", autorizado=True)
    s = datos["s"]
    pago = datos["pago"]

    c = concepto(mundo)
    pol = politica_ret(
        mundo,
        s["moneda"],
        [regla(c, orden=1, tasa="5", exige_comprobante=True)],
    )
    liq = calcular(mundo, pago, pol, [c["codigo"]])
    data = liq.json()
    cargo = cargo_aprobador(mundo, ocupacion, accion="APROBAR", materia="TESORERIA")
    aprobar_liq(mundo, data, cargo)
    registrar_pago(mundo, pago["id"], "REF-INT")

    # GET del pago: monto intacto y retenciones con neto y definitivo
    pg = pago_actual(mundo, pago["id"])
    assert Decimal(pg["monto"]) == Decimal("100.00")
    ret = pg["retenciones"]
    assert Decimal(ret["neto"]) == Decimal("95.00")
    assert ret["definitivo"] is True

    # GET /liquidaciones.csv
    r = mundo.client.get(f"/api/v1{R}/liquidaciones.csv", headers=mundo.como("rt_mk"))
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "text/csv; charset=utf-8"
    csv_text = r.text
    assert (
        "liquidacion,pago,politica,version,estado,fecha,moneda,bruto,"
        "total_retenido,neto,beneficiario,identificacion_fiscal,comprobantes"
        in csv_text
    )
    assert pago["codigo"] in csv_text
