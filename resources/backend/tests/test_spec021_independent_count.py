"""Spec 021 · control de conteo independiente (R-D0-10-9).

La persona que registró o aceptó una recepción no puede contar sus líneas
mientras la empresa mantenga el control activo (valor por defecto).
"""

from __future__ import annotations

import json
from decimal import Decimal

from tests.test_spec021_confirmation import _recepcion_aceptada, _saldos, _sql

pytest_plugins = ("tests.conftest_multicompany",)


def _cargar_json(valor):
    return json.loads(valor) if isinstance(valor, str) else valor


def test_receptor_no_puede_contar(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "T1-IND")
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
                   "ua", mundo.company_a, {"counted_base_quantity": "100"})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "INDEPENDENT_COUNT_REQUIRED"
    filas = _sql(mundo,
                 "SELECT counted_base_quantity FROM goods_receipt_lines WHERE id = :l",
                 l=m["line"])
    assert filas[0][0] is None


def test_conteo_del_ab_y_confirmacion_del_ua(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "T2-IND")
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
                   "uab", mundo.company_a, {"counted_base_quantity": "100"})
    assert r.status_code == 200, r.text
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
                   "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                   "base_quantity": "100"}]})
    assert r.status_code == 200, r.text
    assert r.json()["confirmation_status"] == "CONFIRMADA"
    assert _saldos(mundo, mundo.company_a, m["product"]) == {
        "RECIBIDO": Decimal("0"), "DISPONIBLE": Decimal("100")}

    filas = _sql(mundo,
                 "SELECT counted_by FROM goods_receipt_lines WHERE id = :l",
                 l=m["line"])
    assert filas[0][0] is not None
    counted_by_id = str(filas[0][0])

    filas = _sql(mundo,
                 "SELECT confirmed_by FROM goods_receipts WHERE id = :r",
                 r=m["receipt"])
    assert filas[0][0] is not None
    confirmed_by_id = str(filas[0][0])

    usuarios = _sql(mundo, "SELECT id, username FROM users WHERE username IN ('uab', 'ua')")
    por_username = {f[1]: str(f[0]) for f in usuarios}
    assert counted_by_id == por_username["uab"]
    assert confirmed_by_id == por_username["ua"]


def test_sin_conteo_no_se_confirma(mundo):
    m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "T3-IND")
    r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
                   "ua", mundo.company_a,
                   {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                   "base_quantity": "100"}]})
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "COUNT_REQUIRED_BEFORE_CONFIRMATION"
    assert _saldos(mundo, mundo.company_a, m["product"]) == {"RECIBIDO": Decimal("100")}
    filas = _sql(mundo,
                 "SELECT confirmation_status FROM goods_receipts WHERE id = :r",
                 r=m["receipt"])
    assert filas[0][0] == "PENDIENTE"
    confirmaciones = _sql(mundo,
                          "SELECT COUNT(*) FROM receipt_confirmations WHERE receipt_id = :r",
                          r=m["receipt"])
    assert confirmaciones[0][0] == 0


def test_politica_por_defecto_y_auditoria(mundo):
    r = mundo.get("/purchasing/settings/receipt-count", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    assert r.json() == {"receipt_count_same_user_allowed": False,
                        "independent_count_required": True}

    try:
        r = mundo.put_json("/purchasing/settings/receipt-count", "ua", mundo.company_a,
                           {"receipt_count_same_user_allowed": True})
        assert r.status_code == 200, r.text
        assert r.json() == {"receipt_count_same_user_allowed": True,
                            "independent_count_required": False}

        m = _recepcion_aceptada(mundo, "ua", mundo.company_a, mundo.warehouse_a, "T4-DISABLED")
        r = mundo.post(f"/purchasing/receipts/{m['receipt']}/lines/{m['line']}/conteo",
                       "ua", mundo.company_a, {"counted_base_quantity": "100"})
        assert r.status_code == 200, r.text
        r = mundo.post(f"/purchasing/receipts/{m['receipt']}/confirmacion-inventario",
                       "ua", mundo.company_a,
                       {"decisions": [{"receipt_line_id": m["line"], "target_state": "DISPONIBLE",
                                       "base_quantity": "100"}]})
        assert r.status_code == 200, r.text

        filas = _sql(mundo,
                     "SELECT before, after FROM audit_events "
                     "WHERE action = 'COMPANY_RECEIPT_COUNT_POLICY_CHANGED' "
                     "AND company_id = :c ORDER BY event_time DESC",
                     c=mundo.company_a)
        assert filas, "no se auditó el cambio de política"
        before = _cargar_json(filas[0][0])
        after = _cargar_json(filas[0][1])
        assert before == {"receipt_count_same_user_allowed": False}
        assert after == {"receipt_count_same_user_allowed": True}
    finally:
        r = mundo.put_json("/purchasing/settings/receipt-count", "ua", mundo.company_a,
                           {"receipt_count_same_user_allowed": False})
        assert r.status_code == 200, r.text
        assert r.json() == {"receipt_count_same_user_allowed": False,
                            "independent_count_required": True}

    r = mundo.get("/purchasing/settings/receipt-count", "ub", mundo.company_b)
    assert r.status_code == 200, r.text
    assert r.json() == {"receipt_count_same_user_allowed": False,
                        "independent_count_required": True}
