from app.modules.organization.models import WarehouseLocation
from tests.test_spec021_confirmation import _recepcion_aceptada, _saldos, _sql

pytest_plugins = ("tests.conftest_multicompany",)


def _ubicacion(mundo, code, *, warehouse_id=None, status="ACTIVE"):
    db = mundo.factory()
    try:
        loc = WarehouseLocation(
            company_id=mundo.company_a,
            warehouse_id=warehouse_id or mundo.warehouse_a,
            code=code,
            name=f"Zona {code}",
            sequence=1,
            status=status,
        )
        db.add(loc)
        db.commit()
        return str(loc.id)
    finally:
        db.close()


def test_t1_set_temporary_zone_visible_in_detail_and_list(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TZ1", cantidad=100)
    zt1 = _ubicacion(mundo, "ZT1")
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt1},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["temporary_location"]["label"] == "ZT1 - Zona ZT1"
    assert data["can_set_temporary_location"] is True

    lista = mundo.get("/purchasing/receipts", "ua", mundo.company_a)
    assert lista.status_code == 200, lista.text
    item = next(x for x in lista.json()["items"] if x["id"] == m["receipt"])
    assert item["temporary_location_label"] == "ZT1 - Zona ZT1"

    detalle = mundo.get(f"/purchasing/receipts/{m['receipt']}", "ua", mundo.company_a)
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["temporary_location"]["label"] == "ZT1 - Zona ZT1"


def test_t2_change_temporary_zone_audits_each_change(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TZ2", cantidad=100)
    zt2a = _ubicacion(mundo, "ZT2a")
    zt2b = _ubicacion(mundo, "ZT2b")
    r1 = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt2a},
    )
    assert r1.status_code == 200, r1.text
    r2 = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt2b},
    )
    assert r2.status_code == 200, r2.text
    rows = _sql(
        mundo,
        "SELECT action FROM audit_events WHERE entity_id = :e AND action = 'RECEIPT_TEMPORARY_LOCATION_SET'",
        e=m["receipt"],
    )
    assert len(rows) == 2

    r3 = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt2b},
    )
    assert r3.status_code == 200, r3.text
    rows = _sql(
        mundo,
        "SELECT action FROM audit_events WHERE entity_id = :e AND action = 'RECEIPT_TEMPORARY_LOCATION_SET'",
        e=m["receipt"],
    )
    assert len(rows) == 2


def test_t3_temporary_zone_has_no_inventory_effect(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TZ3", cantidad=100)
    zt3a = _ubicacion(mundo, "ZT3a")
    zt3b = _ubicacion(mundo, "ZT3b")
    saldos_antes = _saldos(mundo, mundo.company_a, m["product"])
    movimientos_antes = _sql(
        mundo, "SELECT count(*) FROM inventory_movements WHERE product_id = :p", p=m["product"]
    )
    r1 = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt3a},
    )
    assert r1.status_code == 200, r1.text
    r2 = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt3b},
    )
    assert r2.status_code == 200, r2.text
    saldos_despues = _saldos(mundo, mundo.company_a, m["product"])
    movimientos_despues = _sql(
        mundo, "SELECT count(*) FROM inventory_movements WHERE product_id = :p", p=m["product"]
    )
    assert saldos_despues == saldos_antes
    assert movimientos_despues == movimientos_antes


def test_t4_confirmation_closes_temporary_zone_but_keeps_history(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TZ4", cantidad=100)
    zt4 = _ubicacion(mundo, "ZT4")
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt4},
    )
    assert r.status_code == 200, r.text

    mundo.post(
        f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
        "uab",
        mundo.company_a,
        {"counted_base_quantity": "100"},
    )
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
        "ua",
        mundo.company_a,
        {
            "decisions": [
                {"receipt_line_id": m["line"], "target_state": "DISPONIBLE", "base_quantity": "100"}
            ]
        },
    )
    assert r.status_code == 200, r.text

    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt4},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "RECEIPT_TEMPORARY_LOCATION_CLOSED"

    detalle = mundo.get(f"/purchasing/receipts/{m['receipt']}", "ua", mundo.company_a)
    assert detalle.status_code == 200, detalle.text
    data = detalle.json()
    assert data["temporary_location"]["label"] == "ZT4 - Zona ZT4"
    assert data["can_set_temporary_location"] is False


def test_t5_invalid_locations(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TZ5", cantidad=100)
    otro = mundo.post(
        "/organization/warehouses",
        "ua",
        mundo.company_a,
        {
            "company_id": mundo.company_a,
            "code": "WTZ5",
            "name": "Otro",
            "warehouse_type": "PHYSICAL",
            "status": "ACTIVE",
        },
    )
    assert otro.status_code == 200, otro.text
    otro_id = otro.json()["id"]
    zt5_otro = _ubicacion(mundo, "ZT5-O", warehouse_id=otro_id)
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt5_otro},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "LOCATION_OTHER_WAREHOUSE"

    zt5_inactiva = _ubicacion(mundo, "ZT5-I", status="INACTIVE")
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt5_inactiva},
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "LOCATION_NOT_ELIGIBLE"

    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "LOCATION_NOT_FOUND"


def test_t6_company_isolation(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TZ6", cantidad=100)
    zt6 = _ubicacion(mundo, "ZT6")
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ub",
        mundo.company_b,
        {"temporary_location_id": zt6},
    )
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "RECEIPT_NOT_FOUND"


def test_t7_options_endpoint_filters(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TZ7", cantidad=100)
    _ubicacion(mundo, "ZT7-A")
    _ubicacion(mundo, "ZT7-I", status="INACTIVE")
    otro = mundo.post(
        "/organization/warehouses",
        "ua",
        mundo.company_a,
        {
            "company_id": mundo.company_a,
            "code": "WTZ7",
            "name": "Otro",
            "warehouse_type": "PHYSICAL",
            "status": "ACTIVE",
        },
    )
    assert otro.status_code == 200, otro.text
    _ubicacion(mundo, "ZT7-O", warehouse_id=otro.json()["id"])

    r = mundo.get(f"/purchasing/receipts/{m['receipt']}/temporary-zone/options", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    labels = {x["label"] for x in items}
    assert "ZT7-A - Zona ZT7-A" in labels
    assert "ZT7-I - Zona ZT7-I" not in labels
    assert "ZT7-O - Zona ZT7-O" not in labels


def test_t8_putaway_does_not_clear_temporary_zone(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "TZ8", cantidad=100)
    zt8 = _ubicacion(mundo, "ZT8")
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/temporary-zone",
        "ua",
        mundo.company_a,
        {"temporary_location_id": zt8},
    )
    assert r.status_code == 200, r.text

    destino = _ubicacion(mundo, "ZT8-D")
    mundo.post(
        f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
        "uab",
        mundo.company_a,
        {"counted_base_quantity": "100"},
    )
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
        "ua",
        mundo.company_a,
        {
            "decisions": [
                {"receipt_line_id": m["line"], "target_state": "DISPONIBLE", "base_quantity": "100"}
            ]
        },
    )
    assert r.status_code == 200, r.text

    r = mundo.post(
        "/inventory/putaway/desde-recepcion",
        "ua",
        mundo.company_a,
        {
            "receipt_id": m["receipt"],
            "product_id": m["product"],
            "target_location_id": destino,
            "quantity": "40",
        },
    )
    assert r.status_code == 200, r.text

    detalle = mundo.get(f"/purchasing/receipts/{m['receipt']}", "ua", mundo.company_a)
    assert detalle.status_code == 200, detalle.text
    assert detalle.json()["temporary_location"]["label"] == "ZT8 - Zona ZT8"
