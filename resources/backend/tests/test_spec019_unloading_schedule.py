"""Spec 019 · programar la descarga y recepción.

Una recepción abierta (DRAFT o CONFIRMED) admite fijar, cambiar o limpiar la
fecha prevista de descarga. La acción queda auditada con
`RECEIPT_UNLOADING_SCHEDULED` y se respeta el aislamiento multicompañía.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

from tests.test_spec021_confirmation import _producto, _recepcion_aceptada, _sql

pytest_plugins = ("tests.conftest_multicompany",)


def _recepcion_borrador(mundo, usuario, empresa, almacen, marca):
    """Crea una recepción DRAFT con una línea y la devuelve."""


    prov = mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": f"PROV-{marca}", "name": "Proveedor", "person_type": "JURIDICA",
                        "roles": ["PROVEEDOR"], "status": "ACTIVE"})
    prod = _producto(mundo, usuario, empresa, f"P-{marca}")
    orden = mundo.crear("/purchasing/orders", usuario, empresa,
                        {"code": f"OC-{marca}", "supplier_id": prov, "currency": "VED"})
    linea = mundo.crear(f"/purchasing/orders/{orden}/lines", usuario, empresa,
                        {"product_id": prod, "quantity_ordered": 10, "unit_price": 1})
    for destino in ("SUBMITTED", "APPROVED"):
        assert mundo.post(f"/purchasing/orders/{orden}/transition", usuario, empresa,
                          {"target": destino}).status_code == 200
    rec = mundo.crear("/purchasing/receipts", usuario, empresa,
                      {"code": f"RC-{marca}", "order_id": orden, "warehouse_id": almacen})
    mundo.crear(f"/purchasing/receipts/{rec}/lines", usuario, empresa,
                {"order_line_id": linea, "product_id": prod, "quantity_received": 10,
                 "quantity_accepted": 10, "quantity_rejected": 0})
    return rec


def _instant(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def test_programar_descarga_y_consultar(mundo):
    rec = _recepcion_borrador(mundo, "ua", mundo.company_a, mundo.warehouse_a, "SD01")
    esperado = datetime(2026, 11, 20, 18, 30, tzinfo=UTC)
    cuerpo = {"unloading_scheduled_at": "2026-11-20T14:30:00-04:00"}
    r = mundo.post(f"/purchasing/receipts/{rec}/unloading-schedule", "ua", mundo.company_a, cuerpo)
    assert r.status_code == 200, r.text
    assert _instant(r.json()["unloading_scheduled_at"]) == esperado

    r = mundo.get(f"/purchasing/receipts/{rec}", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert _instant(r.json()["unloading_scheduled_at"]) == esperado


def test_reprogramar_descarga_audita_antes_y_despues(mundo):
    rec = _recepcion_borrador(mundo, "ua", mundo.company_a, mundo.warehouse_a, "SD02")
    primera = "2026-11-20T14:30:00-04:00"
    segunda = "2026-11-21T09:00:00-04:00"
    for valor in (primera, segunda):
        r = mundo.post(f"/purchasing/receipts/{rec}/unloading-schedule", "ua", mundo.company_a,
                       {"unloading_scheduled_at": valor})
        assert r.status_code == 200, r.text

    filas = _sql(mundo, "SELECT before, after FROM audit_events "
                        "WHERE action = 'RECEIPT_UNLOADING_SCHEDULED' AND entity_id = :e "
                        "ORDER BY event_time DESC", e=rec)
    assert len(filas) == 2
    before, after = filas[0]
    if isinstance(before, str):
        before = json.loads(before)
    if isinstance(after, str):
        after = json.loads(after)
    assert _instant(before["unloading_scheduled_at"]) == datetime(2026, 11, 20, 18, 30, tzinfo=UTC)
    assert _instant(after["unloading_scheduled_at"]) == datetime(2026, 11, 21, 13, 0, tzinfo=UTC)


def test_limpiar_descarga_con_null(mundo):
    rec = _recepcion_borrador(mundo, "ua", mundo.company_a, mundo.warehouse_a, "SD03")
    r = mundo.post(f"/purchasing/receipts/{rec}/unloading-schedule", "ua", mundo.company_a,
                   {"unloading_scheduled_at": "2026-11-20T14:30:00-04:00"})
    assert r.status_code == 200, r.text
    r = mundo.post(f"/purchasing/receipts/{rec}/unloading-schedule", "ua", mundo.company_a,
                   {"unloading_scheduled_at": None})
    assert r.status_code == 200, r.text
    assert r.json()["unloading_scheduled_at"] is None


def test_datetime_naive_rechazado(mundo):
    rec = _recepcion_borrador(mundo, "ua", mundo.company_a, mundo.warehouse_a, "SD04")
    r = mundo.post(f"/purchasing/receipts/{rec}/unloading-schedule", "ua", mundo.company_a,
                   {"unloading_scheduled_at": "2026-11-20T14:30:00"})
    assert r.status_code == 422, r.text


def test_recepcion_aceptada_no_admite_programar(mundo):
    rec = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "SD05")["receipt"]
    r = mundo.post(f"/purchasing/receipts/{rec}/unloading-schedule", "ua", mundo.company_a,
                   {"unloading_scheduled_at": "2026-11-20T14:30:00-04:00"})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "RECEIPT_NOT_OPEN"

    consulta = _sql(mundo, "SELECT unloading_scheduled_at FROM goods_receipts WHERE id = :e", e=rec)
    assert consulta[0][0] is None


def test_aislamiento_multicompania(mundo):
    rec = _recepcion_borrador(mundo, "ua", mundo.company_a, mundo.warehouse_a, "SD06")
    r = mundo.post(f"/purchasing/receipts/{rec}/unloading-schedule", "ub", mundo.company_b,
                   {"unloading_scheduled_at": "2026-11-20T14:30:00-04:00"})
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "RECEIPT_NOT_FOUND"
