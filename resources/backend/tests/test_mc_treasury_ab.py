"""Tesorería con dos empresas del mismo tenant (ARCH-MC-001, N5).

Tesorería va primero porque es donde una confusión de empresa se convierte en
dinero mal aplicado: un pago de A cancelando una deuda de B no es un listado
sucio, es un asiento falso en dos contabilidades a la vez.

Cada bloque cubre la matriz completa: crear en ambas, listar, leer y modificar
cruzado, relacionar cruzado, comprobar la propiedad **en PostgreSQL**, y el
evento y la auditoría. Ninguna de esas filas sustituye a otra.
"""

from __future__ import annotations

from sqlalchemy import text

pytest_plugins = ("tests.conftest_multicompany",)


def _banco(mundo, usuario, empresa, code):
    return mundo.crear("/treasury/banks", usuario, empresa,
                       {"code": code, "name": f"Banco {code}"})


def _cuenta(mundo, usuario, empresa, banco, code):
    return mundo.crear("/treasury/accounts", usuario, empresa, {
        "bank_id": banco, "code": code, "name": f"Cuenta {code}",
        "currency": "VED", "account_number": f"0102{code}"})


# --------------------------------------------------------------- cuentas
def test_cuentas_de_a_y_b_guardan_su_propia_empresa(mundo):
    ca = _cuenta(mundo, "ua", mundo.company_a, _banco(mundo, "ua", mundo.company_a, "BA"), "CTA-A")
    cb = _cuenta(mundo, "ub", mundo.company_b, _banco(mundo, "ub", mundo.company_b, "BB"), "CTA-B")

    assert mundo.dueño("financial_accounts", ca) == mundo.company_a
    assert mundo.dueño("financial_accounts", cb) == mundo.company_b
    # El fallo que esta remediación corrige tenía esta forma exacta.
    assert mundo.dueño("financial_accounts", ca) != mundo.t1


def test_cada_empresa_lista_solo_sus_cuentas(mundo):
    _cuenta(mundo, "ua", mundo.company_a, _banco(mundo, "ua", mundo.company_a, "BLA"), "L-A")
    _cuenta(mundo, "ub", mundo.company_b, _banco(mundo, "ub", mundo.company_b, "BLB"), "L-B")

    de_a = {c["id"] for c in mundo.get("/treasury/accounts", "ua", mundo.company_a).json()["items"]}
    de_b = {c["id"] for c in mundo.get("/treasury/accounts", "ub", mundo.company_b).json()["items"]}
    assert de_a and de_b
    assert not (de_a & de_b), "una cuenta aparece en las dos empresas"


def test_una_cuenta_de_b_no_sirve_para_operar_en_a(mundo):
    """Detalle y modificación cruzados, por la vía en que existen.

    Tesorería no expone `GET /accounts/{id}` ni `PATCH`: la forma de leer o
    tocar una cuenta ajena es usarla como relación. Se prueba por ahí, que es
    donde el daño ocurriría.
    """
    cb = _cuenta(mundo, "ub", mundo.company_b, _banco(mundo, "ub", mundo.company_b, "BX"), "X-B")

    r = mundo.post("/treasury/bank-transactions", "ua", mundo.company_a, {
        "account_id": cb, "direction": "IN", "amount": "100.00", "currency": "VED"})
    assert r.status_code == 404, f"A movió dinero en una cuenta de B: {r.text}"
    assert r.json()["code"] == "ACCOUNT_NOT_FOUND"


def test_movimiento_bancario_hereda_la_empresa_de_su_cuenta(mundo):
    ca = _cuenta(mundo, "ua", mundo.company_a, _banco(mundo, "ua", mundo.company_a, "BM"), "M-A")
    tx = mundo.crear("/treasury/bank-transactions", "ua", mundo.company_a, {
        "account_id": ca, "direction": "IN", "amount": "250.00", "currency": "VED"})

    assert mundo.dueño("bank_transactions", tx) == mundo.company_a
    db = mundo.factory()
    try:
        cuenta = db.execute(text(
            "SELECT account_id FROM bank_transactions WHERE id = :i"), {"i": tx}).scalar_one()
    finally:
        db.close()
    assert cuenta == ca


def test_los_movimientos_no_se_mezclan_entre_empresas(mundo):
    ca = _cuenta(mundo, "ua", mundo.company_a, _banco(mundo, "ua", mundo.company_a, "BM2"), "M2-A")
    cb = _cuenta(mundo, "ub", mundo.company_b, _banco(mundo, "ub", mundo.company_b, "BM2"), "M2-B")
    mundo.crear("/treasury/bank-transactions", "ua", mundo.company_a,
                {"account_id": ca, "direction": "IN", "amount": "10.00", "currency": "VED"})
    mundo.crear("/treasury/bank-transactions", "ub", mundo.company_b,
                {"account_id": cb, "direction": "IN", "amount": "20.00", "currency": "VED"})

    de_a = {t["id"] for t in mundo.get("/treasury/bank-transactions", "ua", mundo.company_a).json()["items"]}
    de_b = {t["id"] for t in mundo.get("/treasury/bank-transactions", "ub", mundo.company_b).json()["items"]}
    assert de_a and de_b and not (de_a & de_b)


# --------------------------------------------------------------- conciliación
def test_no_se_concilia_una_cuenta_ajena(mundo):
    cb = _cuenta(mundo, "ub", mundo.company_b, _banco(mundo, "ub", mundo.company_b, "BC"), "C-B")
    r = mundo.post("/treasury/reconciliations", "ua", mundo.company_a,
                   {"account_id": cb, "statement_ref": "EXT-CRUZADO"})
    assert r.status_code == 404, f"A concilió una cuenta de B: {r.text}"


def test_la_conciliacion_ajena_no_se_lee_ni_se_toca(mundo):
    cb = _cuenta(mundo, "ub", mundo.company_b, _banco(mundo, "ub", mundo.company_b, "BC2"), "C2-B")
    rec_b = mundo.crear("/treasury/reconciliations", "ub", mundo.company_b,
                        {"account_id": cb, "statement_ref": "EXT-B"})
    assert mundo.dueño("reconciliations", rec_b) == mundo.company_b

    assert mundo.get(f"/treasury/reconciliations/{rec_b}", "ua", mundo.company_a).status_code == 404
    # El payload es válido y de A: si respondiera 422 no probaría nada, porque
    # la petición no habría llegado siquiera a la comprobación de empresa.
    ca = _cuenta(mundo, "ua", mundo.company_a, _banco(mundo, "ua", mundo.company_a, "BC3"), "C3-A")
    tx_a = mundo.crear("/treasury/bank-transactions", "ua", mundo.company_a,
                       {"account_id": ca, "direction": "IN", "amount": "5.00", "currency": "VED"})

    r = mundo.post(f"/treasury/reconciliations/{rec_b}/lines", "ua", mundo.company_a,
                   {"bank_transaction_id": tx_a})
    assert r.status_code == 404, f"A añadió una línea a la conciliación de B: {r.text}"
    r = mundo.post(f"/treasury/reconciliations/{rec_b}/transition", "ua", mundo.company_a,
                   {"target": "IN_PROGRESS"})
    assert r.status_code == 404, f"A movió el estado de la conciliación de B: {r.text}"


# --------------------------------------------------------------- caja
def test_la_sesion_de_caja_de_b_no_se_opera_desde_a(mundo):
    caja_b = mundo.crear("/treasury/cashboxes", "ub", mundo.company_b,
                         {"code": "CAJA-B", "name": "Caja B", "currency": "VED"})
    ses_b = mundo.crear("/treasury/cash-sessions", "ub", mundo.company_b,
                        {"cashbox_id": caja_b, "opened_amount": 0})
    assert mundo.dueño("cash_sessions", ses_b) == mundo.company_b

    assert mundo.get(f"/treasury/cash-sessions/{ses_b}", "ua", mundo.company_a).status_code == 404
    # Payloads válidos a propósito: un 422 significaría que la petición murió
    # en la validación de forma, sin llegar a preguntarse de quién es la caja.
    for ruta, cuerpo in (("movements", {"movement_type": "IN", "amount": 5}),
                         ("arqueo", {"counted_amount": "5.00"}),
                         ("pre-close", {}),
                         ("close", {"difference_approved": False}),
                         ("reject", {})):
        r = mundo.post(f"/treasury/cash-sessions/{ses_b}/{ruta}", "ua", mundo.company_a, cuerpo)
        assert r.status_code == 404, f"A operó '{ruta}' sobre la sesión de B: {r.status_code}"


def test_no_se_abre_sesion_sobre_una_caja_ajena(mundo):
    caja_b = mundo.crear("/treasury/cashboxes", "ub", mundo.company_b,
                         {"code": "CAJA-B2", "name": "Caja B2", "currency": "VED"})
    r = mundo.post("/treasury/cash-sessions", "ua", mundo.company_a,
                   {"cashbox_id": caja_b, "opened_amount": 0})
    assert r.status_code == 404, f"A abrió caja en una caja de B: {r.text}"


# --------------------------------------------------------------- transferencias
def test_no_hay_transferencia_entre_empresas(mundo):
    """§62: sin proceso intercompany explícito, esto se bloquea.

    No se implementa la capacidad: se impide la operación. Mover dinero entre
    dos personas jurídicas distintas es un hecho contable con documentación
    propia, no un asiento interno.
    """
    ca = _cuenta(mundo, "ua", mundo.company_a, _banco(mundo, "ua", mundo.company_a, "BT"), "T-A")
    cb = _cuenta(mundo, "ub", mundo.company_b, _banco(mundo, "ub", mundo.company_b, "BT"), "T-B")

    r = mundo.post("/treasury/transfers", "ua", mundo.company_a, {
        "amount": 500, "currency": "VED", "from_account_id": ca, "to_account_id": cb})
    assert r.status_code == 404, f"se transfirió dinero de A a B: {r.text}"

    db = mundo.factory()
    try:
        assert db.execute(text(
            "SELECT count(*) FROM treasury_transfers WHERE to_account_id = :c"),
            {"c": cb}).scalar_one() == 0, "quedó una transferencia hacia B"
    finally:
        db.close()


# --------------------------------------------------------------- otro tenant
def test_el_otro_tenant_no_alcanza_nada(mundo):
    ca = _cuenta(mundo, "ua", mundo.company_a, _banco(mundo, "ua", mundo.company_a, "BZ"), "Z-A")
    r = mundo.post("/treasury/bank-transactions", "uc", mundo.company_c,
                   {"account_id": ca, "direction": "IN", "amount": "1.00", "currency": "VED"},
                   tenant="T2")
    assert r.status_code == 404
    # Y tampoco puede simplemente declarar la empresa de A.
    assert mundo.get("/treasury/accounts", "uc", mundo.company_a, tenant="T2").status_code == 404


# --------------------------------------------------------------- rastro
def test_la_auditoria_registra_la_empresa_real(mundo):
    """Sobre una acción que este dominio audita de verdad.

    Tesorería audita el arqueo, el cierre de caja y la transición de
    conciliación; no la creación de catálogos. No se inventa auditoría donde el
    contrato no la pide: se comprueba que la que existe lleva la empresa
    correcta, que es lo que ARCH-MC-001 puede exigir.
    """
    caja = mundo.crear("/treasury/cashboxes", "ua", mundo.company_a,
                       {"code": "CAJA-AUD", "name": "Caja auditada", "currency": "VED"})
    ses = mundo.crear("/treasury/cash-sessions", "ua", mundo.company_a,
                      {"cashbox_id": caja, "opened_amount": 0})
    r = mundo.post(f"/treasury/cash-sessions/{ses}/arqueo", "ua", mundo.company_a,
                   {"counted_amount": "0.00"})
    assert r.status_code == 200, r.text

    db = mundo.factory()
    try:
        fila = db.execute(text(
            "SELECT tenant_id, company_id, user_id FROM audit_events "
            "WHERE entity_id = :i AND action = 'CASH_SESSION_ARCHED' "
            "ORDER BY event_time DESC LIMIT 1"), {"i": ses}).first()
    finally:
        db.close()
    assert fila is not None, "el arqueo no dejó rastro de auditoría"
    assert fila.company_id == mundo.company_a, "la auditoría anotó otra empresa"
    assert fila.company_id != mundo.t1, "la auditoría guardó el tenant como empresa"
    assert fila.user_id is not None, "la auditoría no sabe quién arqueó"


def test_ninguna_auditoria_de_tesoreria_apunta_a_una_empresa_inexistente(mundo):
    """El otro fallo: que la base no sepa de quién es la fila.

    No basta con que A no vea lo de B. Si `company_id` guardara el tenant, o una
    empresa que no existe, el filtro sería correcto sobre un dato indistinguible.
    """
    db = mundo.factory()
    try:
        huerfanas = db.execute(text(
            "SELECT count(*) FROM audit_events a WHERE a.company_id IS NOT NULL "
            "AND NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = a.company_id)"
        )).scalar_one()
    finally:
        db.close()
    assert huerfanas == 0, f"{huerfanas} auditorías apuntan a una empresa que no existe"
