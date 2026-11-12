from decimal import Decimal

from app.modules.organization.models import WarehouseLocation
from tests.test_spec021_confirmation import _recepcion_aceptada, _sql

pytest_plugins = ("tests.conftest_multicompany",)


def _ubicacion(mundo, code):
    db = mundo.factory()
    try:
        loc = WarehouseLocation(
            company_id=mundo.company_a,
            warehouse_id=mundo.warehouse_a,
            code=code,
            name=f"Ubicación {code}",
            sequence=1,
            status="ACTIVE",
        )
        db.add(loc)
        db.commit()
        return str(loc.id)
    finally:
        db.close()


def _preparar_recepcion(mundo, marca, cantidad="100"):
    return _recepcion_aceptada(
        mundo, "ua", mundo.company_a, mundo.warehouse_a, marca, cantidad=int(cantidad)
    )


def _contar_y_confirmar(mundo, m, cantidad="100"):
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
        "uab",
        mundo.company_a,
        {"counted_base_quantity": cantidad},
    )
    assert r.status_code == 200, r.text
    r = mundo.post(
        f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
        "ua",
        mundo.company_a,
        {
            "decisions": [
                {
                    "receipt_line_id": m["line"],
                    "target_state": "DISPONIBLE",
                    "base_quantity": cantidad,
                }
            ]
        },
    )
    assert r.status_code == 200, r.text


def test_t1_pending_lista_recepciones(mundo):
    m = _preparar_recepcion(mundo, "PTW1")
    _contar_y_confirmar(mundo, m)

    r = mundo.get(
        "/inventory/putaway/recepciones"
        f"?warehouse_id={mundo.warehouse_a}&product_id={m['product']}",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200, r.text
    data = r.json()["items"]
    assert len(data) == 1
    assert Decimal(data[0]["pending_base"]) == Decimal("100")


def test_t2_putaway_desde_recepcion_parcial(mundo):
    m = _preparar_recepcion(mundo, "PTW2")
    _contar_y_confirmar(mundo, m)
    loc_id = _ubicacion(mundo, "PTW2-A")

    r = mundo.post(
        "/inventory/putaway/desde-recepcion",
        "ua",
        mundo.company_a,
        {
            "receipt_id": m["receipt"],
            "product_id": m["product"],
            "target_location_id": loc_id,
            "quantity": "60",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()

    links = _sql(
        mundo,
        "SELECT movement_id, base_quantity FROM receipt_putaways WHERE receipt_id = :r",
        r=m["receipt"],
    )
    assert len(links) == 1
    assert str(links[0][0]) == body["movement_id"]
    assert Decimal(links[0][1]) == Decimal("60")

    balances = _sql(
        mundo,
        "SELECT location_id, qty_on_hand FROM inventory_balances "
        "WHERE company_id = :c AND product_id = :p AND state = 'DISPONIBLE'",
        c=mundo.company_a,
        p=m["product"],
    )
    by_location = {str(row[0]) if row[0] is not None else None: Decimal(row[1]) for row in balances}
    assert by_location.get(loc_id) == Decimal("60")
    assert by_location.get(None) == Decimal("40")

    r = mundo.get(
        "/inventory/putaway/recepciones"
        f"?warehouse_id={mundo.warehouse_a}&product_id={m['product']}",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200, r.text
    assert Decimal(r.json()["items"][0]["pending_base"]) == Decimal("40")


def test_t3_excede_pendiente_409(mundo):
    m = _preparar_recepcion(mundo, "PTW3")
    _contar_y_confirmar(mundo, m)
    loc_id = _ubicacion(mundo, "PTW3-A")

    r = mundo.post(
        "/inventory/putaway/desde-recepcion",
        "ua",
        mundo.company_a,
        {
            "receipt_id": m["receipt"],
            "product_id": m["product"],
            "target_location_id": loc_id,
            "quantity": "60",
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
            "target_location_id": loc_id,
            "quantity": "50",
        },
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "PUTAWAY_EXCEEDS_RECEIPT_PENDING"

    links = _sql(
        mundo,
        "SELECT movement_id, base_quantity FROM receipt_putaways WHERE receipt_id = :r",
        r=m["receipt"],
    )
    assert len(links) == 1


def test_t4_empresa_b_no_puede_putaway_empresa_a(mundo):
    m = _preparar_recepcion(mundo, "PTW4")
    _contar_y_confirmar(mundo, m)
    loc_id = _ubicacion(mundo, "PTW4-A")

    r = mundo.post(
        "/inventory/putaway/desde-recepcion",
        "ub",
        mundo.company_b,
        {
            "receipt_id": m["receipt"],
            "product_id": m["product"],
            "target_location_id": loc_id,
            "quantity": "60",
        },
    )
    assert r.status_code == 404, r.text


def test_t5_putaway_generico_no_genera_vinculo(mundo):
    m = _preparar_recepcion(mundo, "PTW5")
    _contar_y_confirmar(mundo, m)
    loc_id = _ubicacion(mundo, "PTW5-A")

    r = mundo.post(
        "/inventory/putaway",
        "ua",
        mundo.company_a,
        {
            "warehouse_id": mundo.warehouse_a,
            "product_id": m["product"],
            "target_location_id": loc_id,
            "quantity": "10",
            "state": "DISPONIBLE",
        },
    )
    assert r.status_code == 200, r.text

    links = _sql(
        mundo,
        "SELECT movement_id, base_quantity FROM receipt_putaways WHERE receipt_id = :r",
        r=m["receipt"],
    )
    assert len(links) == 0

    r = mundo.get(
        "/inventory/putaway/recepciones"
        f"?warehouse_id={mundo.warehouse_a}&product_id={m['product']}",
        "ua",
        mundo.company_a,
    )
    assert r.status_code == 200, r.text
    assert Decimal(r.json()["items"][0]["pending_base"]) == Decimal("100")


def test_t6_evento_auditoria(mundo):
    m = _preparar_recepcion(mundo, "PTW6")
    _contar_y_confirmar(mundo, m)
    loc_id = _ubicacion(mundo, "PTW6-A")

    r = mundo.post(
        "/inventory/putaway/desde-recepcion",
        "ua",
        mundo.company_a,
        {
            "receipt_id": m["receipt"],
            "product_id": m["product"],
            "target_location_id": loc_id,
            "quantity": "60",
        },
    )
    assert r.status_code == 200, r.text

    rows = _sql(
        mundo,
        "SELECT action FROM audit_events WHERE entity_id = :e AND action = 'RECEIPT_PUTAWAY_ATTRIBUTED'",
        e=m["receipt"],
    )
    assert len(rows) == 1
