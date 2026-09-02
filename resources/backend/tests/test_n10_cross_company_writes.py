"""Escrituras hijas que nunca comprobaron la empresa (ARCH-MC-001, N10).

N5 buscó el defecto donde la petición **declara** la empresa. N10 lo buscó donde
no la declara: rutas que reciben el identificador del padre por la URL, no piden
`CompanyContext` y llaman al servicio con ese identificador tal cual.

El permiso no salva estas rutas. `compras:create` dice que el usuario puede
crear líneas de compra; no dice en qué empresa. Sin contexto no hay nada que
comparar, y el servicio guarda la línea bajo el padre que le den.

Cada prueba hace lo mismo: crea el padre en A, entra como un usuario que solo
tiene B, y escribe contra el padre de A. Si responde 200, la empresa no existe
como frontera.
"""

from __future__ import annotations

pytest_plugins = ("tests.conftest_multicompany",)

BLOQUEO = (403, 404)


def _tercero(mundo, usuario, empresa, code, rol):
    return mundo.crear("/maestros/terceros", usuario, empresa,
                       {"code": code, "name": f"Tercero {code}", "roles": [rol]})


def _producto(mundo, usuario, empresa, code):
    return mundo.crear("/maestros/catalogos/items", usuario, empresa,
                       {"code": code, "name": f"Producto {code}", "item_type": "PRODUCT"})


# --------------------------------------------------------------------- ventas
def test_una_linea_de_cotizacion_de_ventas_no_entra_en_la_cotizacion_de_otra(mundo):
    cli = _tercero(mundo, "ua", mundo.company_a, "N10-CLI-1", "CLIENTE")
    cot = mundo.crear("/sales/quotes", "ua", mundo.company_a,
                      {"code": "N10-COT-V1", "customer_id": cli, "currency": "VED"})
    prod = _producto(mundo, "ub", mundo.company_b, "N10-PB-1")
    r = mundo.post(f"/sales/quotes/{cot}/lines", "ub", mundo.company_b,
                   {"product_id": prod, "quantity": 1, "unit_price": 10.0})
    assert r.status_code in BLOQUEO, (
        f"B añadió una línea a la cotización de venta de A: {r.status_code} {r.text}")


def test_una_linea_de_devolucion_de_ventas_no_entra_en_la_devolucion_de_otra(mundo):
    dev = mundo.crear("/sales/returns", "ua", mundo.company_a,
                      {"code": "N10-DEV-V1", "reason": "Producto defectuoso"})
    prod = _producto(mundo, "ub", mundo.company_b, "N10-PB-2")
    r = mundo.post(f"/sales/returns/{dev}/lines", "ub", mundo.company_b,
                   {"product_id": prod, "quantity": 1})
    assert r.status_code in BLOQUEO, (
        f"B añadió una línea a la devolución de venta de A: {r.status_code} {r.text}")


# -------------------------------------------------------------------- compras
def test_una_linea_de_cotizacion_de_compras_no_entra_en_la_cotizacion_de_otra(mundo):
    prov = _tercero(mundo, "ua", mundo.company_a, "N10-PRV-1", "PROVEEDOR")
    cot = mundo.crear("/purchasing/quotes", "ua", mundo.company_a,
                      {"code": "N10-COT-C1", "supplier_id": prov, "currency": "VED"})
    prod = _producto(mundo, "ub", mundo.company_b, "N10-PB-3")
    r = mundo.post(f"/purchasing/quotes/{cot}/lines", "ub", mundo.company_b,
                   {"product_id": prod, "quantity": 1, "unit_price": 10.0})
    assert r.status_code in BLOQUEO, (
        f"B añadió una línea a la cotización de compra de A: {r.status_code} {r.text}")


def test_una_linea_de_devolucion_de_compras_no_entra_en_la_devolucion_de_otra(mundo):
    dev = mundo.crear("/purchasing/returns", "ua", mundo.company_a,
                      {"code": "N10-DEV-C1", "reason": "Mercancía no conforme"})
    prod = _producto(mundo, "ub", mundo.company_b, "N10-PB-4")
    r = mundo.post(f"/purchasing/returns/{dev}/lines", "ub", mundo.company_b,
                   {"product_id": prod, "quantity": 1})
    assert r.status_code in BLOQUEO, (
        f"B añadió una línea a la devolución de compra de A: {r.status_code} {r.text}")


def test_una_linea_de_recepcion_no_entra_en_la_recepcion_de_otra(mundo):
    prov = _tercero(mundo, "ua", mundo.company_a, "N10-PRV-2", "PROVEEDOR")
    prod_a = _producto(mundo, "ua", mundo.company_a, "N10-PA-5")
    orden = mundo.crear("/purchasing/orders", "ua", mundo.company_a,
                        {"code": "N10-OC-1", "supplier_id": prov, "currency": "VED"})
    linea = mundo.post(f"/purchasing/orders/{orden}/lines", "ua", mundo.company_a,
                       {"product_id": prod_a, "quantity_ordered": 5, "unit_price": 10.0})
    assert linea.status_code == 200, linea.text
    linea_id = linea.json()["id"]
    for destino in ("SUBMITTED", "APPROVED"):
        r = mundo.post(f"/purchasing/orders/{orden}/transition", "ua", mundo.company_a,
                       {"target": destino})
        assert r.status_code == 200, f"{destino}: {r.text}"
    rec = mundo.crear("/purchasing/receipts", "ua", mundo.company_a,
                      {"code": "N10-REC-1", "order_id": orden,
                       "warehouse_id": mundo.warehouse_a})
    prod_b = _producto(mundo, "ub", mundo.company_b, "N10-PB-5")
    r = mundo.post(f"/purchasing/receipts/{rec}/lines", "ub", mundo.company_b,
                   {"order_line_id": linea_id, "product_id": prod_b,
                    "quantity_received": 1, "quantity_accepted": 1, "quantity_rejected": 0})
    assert r.status_code in BLOQUEO, (
        f"B añadió una línea a la recepción de A: {r.status_code} {r.text}")


# ------------------------------------------------------------------ tesorería
def _banco(mundo, usuario, empresa, code):
    return mundo.crear("/treasury/banks", usuario, empresa,
                       {"code": code, "name": f"Banco {code}"})


def _cuenta(mundo, usuario, empresa, banco, code):
    return mundo.crear("/treasury/accounts", usuario, empresa, {
        "bank_id": banco, "code": code, "name": f"Cuenta {code}",
        "currency": "VED", "account_number": f"0102{code}"})


def test_una_linea_de_conciliacion_no_se_resuelve_desde_otra_empresa(mundo):
    """La conciliación de A ya estaba protegida; su **línea** no lo estaba.

    `resolve_line` recibe el id de la línea, comprueba el estado de la
    conciliación y el tipo de resolución, y no mira de quién es.
    """
    ca = _cuenta(mundo, "ua", mundo.company_a,
                 _banco(mundo, "ua", mundo.company_a, "N10-BA"), "N10-CA")
    tx = mundo.crear("/treasury/bank-transactions", "ua", mundo.company_a,
                     {"account_id": ca, "direction": "IN", "amount": 5, "currency": "VED"})
    rec = mundo.crear("/treasury/reconciliations", "ua", mundo.company_a,
                      {"account_id": ca, "statement_ref": "N10-EXT-A"})
    r = mundo.post(f"/treasury/reconciliations/{rec}/lines", "ua", mundo.company_a,
                   {"bank_transaction_id": tx})
    assert r.status_code == 200, r.text
    linea = r.json()["id"]
    # Sin este paso la conciliación está en DRAFT y quien rechaza es el estado,
    # no la empresa: la prueba pasaría sin comprobar nada de lo que dice.
    r = mundo.post(f"/treasury/reconciliations/{rec}/transition", "ua", mundo.company_a,
                   {"target": "IN_PROGRESS"})
    assert r.status_code == 200, r.text
    r = mundo.post(f"/treasury/reconciliation-lines/{linea}/resolve", "ub", mundo.company_b,
                   {"resolution_type": "MATCHED"})
    assert r.status_code in BLOQUEO, (
        f"B resolvió una línea de conciliación de A: {r.status_code} {r.text}")


# ---------------------------------------------------------------- aprobaciones
def test_una_solicitud_de_aprobacion_no_se_cancela_desde_otra_empresa(mundo):
    """`cancel` comprobaba la transición de estado, no la empresa."""
    r = mundo.post("/approvals/policies", "ua", mundo.company_a,
                   {"process_type": "N10_CANCEL", "code": "N10P", "name": "Política N10"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    rr = mundo.post(f"/approvals/policies/{pid}/rules", "ua", mundo.company_a,
                    {"name": "Siempre", "conditions": [
                        {"field": "amount_base", "operator": "gt", "value": 10.0}],
                     "condition_fields": ["amount_base", "amount", "currency"]})
    assert rr.status_code == 201, rr.text
    rl = mundo.post(f"/approvals/policies/{pid}/rules/{rr.json()['id']}/levels",
                    "ua", mundo.company_a,
                    {"level_order": 1, "resolver_type": "ROLE",
                     "resolver_ref": "ADMIN", "quorum_type": "ANY"})
    assert rl.status_code == 201, rl.text
    assert mundo.post(f"/approvals/policies/{pid}/activate", "ua", mundo.company_a,
                      {}).status_code == 200

    r = mundo.post("/approvals/requests", "ua", mundo.company_a,
                   {"process_type": "N10_CANCEL", "document_type": "SalesOrder",
                    "document_id": "n10-doc-1",
                    "context": {"amount_base": 5000.0, "amount": 5000.0, "currency": "VED"}})
    assert r.status_code in (200, 201), r.text
    cuerpo = r.json()
    assert cuerpo.get("requires_approval"), f"la política no exigió aprobación: {cuerpo}"
    solicitud = cuerpo.get("request_id") or (cuerpo.get("request") or {}).get("id")
    assert solicitud, f"no se creó solicitud: {cuerpo}"

    r = mundo.post(f"/approvals/requests/{solicitud}/cancel", "ub", mundo.company_b,
                   {"reason": "Cancelada desde otra empresa"})
    assert r.status_code in BLOQUEO, (
        f"B canceló una solicitud de aprobación de A: {r.status_code} {r.text}")


# -------------------------------------------------------------------- unidades
def test_una_conversion_no_relaciona_dos_unidades_privadas_de_otra_empresa(mundo):
    """Había dos rutas para crear la misma conversión y solo una comprobaba algo.

    `/catalogos/unidades/{id}/conversiones` creaba la fila sin mirar si las
    unidades existían ni de quién eran. Una unidad de plataforma (`company_id`
    nulo) la ve todo el mundo; una de empresa, solo la suya.
    """
    u1 = mundo.crear("/maestros/catalogos/unidades", "ua", mundo.company_a,
                     {"code": "N10U1", "name": "Unidad N10 uno", "symbol": "n1",
                      "dimension": "MASA"})
    u2 = mundo.crear("/maestros/catalogos/unidades", "ua", mundo.company_a,
                     {"code": "N10U2", "name": "Unidad N10 dos", "symbol": "n2",
                      "dimension": "MASA"})
    r = mundo.post(f"/maestros/catalogos/unidades/{u1}/conversiones", "ub", mundo.company_b,
                   {"from_unit_id": u1, "to_unit_id": u2, "factor": 2.0})
    assert r.status_code in BLOQUEO, (
        f"B relacionó dos unidades privadas de A: {r.status_code} {r.text}")


# ------------------------------------------------- lo que ya estaba protegido
def test_un_paso_de_aprobacion_ajeno_no_se_decide_desde_otra_empresa(mundo):
    """Las tres rutas de decisión tampoco piden contexto, y **sí** están cerradas.

    No por la empresa sino por la elegibilidad: quien decide tiene que figurar
    entre los aprobadores del nivel, y esos se fijaron desde la política de A.
    Se comprueba con una ejecución, no leyendo el código: que una ruta parezca
    protegida y que lo esté son dos afirmaciones distintas.
    """
    r = mundo.post("/approvals/policies", "ua", mundo.company_a,
                   {"process_type": "N10_DECIDE", "code": "N10D", "name": "Política N10 D"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    rr = mundo.post(f"/approvals/policies/{pid}/rules", "ua", mundo.company_a,
                    {"name": "Siempre", "conditions": [
                        {"field": "amount_base", "operator": "gt", "value": 10.0}],
                     "condition_fields": ["amount_base", "amount", "currency"]})
    assert rr.status_code == 201, rr.text
    rl = mundo.post(f"/approvals/policies/{pid}/rules/{rr.json()['id']}/levels",
                    "ua", mundo.company_a,
                    {"level_order": 1, "resolver_type": "ROLE",
                     "resolver_ref": "ADMIN", "quorum_type": "ANY"})
    assert rl.status_code == 201, rl.text
    assert mundo.post(f"/approvals/policies/{pid}/activate", "ua", mundo.company_a,
                      {}).status_code == 200

    r = mundo.post("/approvals/requests", "ua", mundo.company_a,
                   {"process_type": "N10_DECIDE", "document_type": "SalesOrder",
                    "document_id": "n10-doc-2",
                    "context": {"amount_base": 5000.0, "amount": 5000.0, "currency": "VED"}})
    assert r.status_code in (200, 201), r.text
    cuerpo = r.json()
    assert cuerpo.get("requires_approval"), cuerpo
    solicitud = cuerpo.get("request_id") or (cuerpo.get("request") or {}).get("id")

    detalle = mundo.get(f"/approvals/requests/{solicitud}", "ua", mundo.company_a)
    assert detalle.status_code == 200, detalle.text
    pasos = detalle.json().get("steps") or []
    abiertos = [p for p in pasos if p.get("status") == "IN_REVIEW"]
    assert abiertos, f"la solicitud no dejó ningún paso abierto: {pasos}"

    r = mundo.post(f"/approvals/steps/{abiertos[0]['id']}/approve", "ub", mundo.company_b,
                   {"reason": "Aprobado desde otra empresa"})
    assert r.status_code in BLOQUEO, (
        f"B decidió un paso de aprobación de A: {r.status_code} {r.text}")


# ---------------------------------------------------------------- organización
def test_los_establecimientos_de_otra_empresa_no_se_listan(mundo):
    """Listaba por `Company.tenant_id == user.tenant_id`.

    Compartir tenant no es compartir empresa. El establecimiento es donde se
    emiten documentos fiscales: verlo es ver la estructura fiscal ajena.
    """
    est_b = mundo.crear("/organization/establishments", "ub", mundo.company_b,
                        {"branch_id": mundo.branch_b, "code": "N10-EST-B",
                         "name": "Establecimiento B"})
    r = mundo.get("/organization/establishments", "ua", mundo.company_a)
    assert r.status_code == 200, r.text
    ajenos = [e for e in r.json() if e["id"] == est_b]
    assert ajenos == [], f"A vio el establecimiento de B: {ajenos}"


def test_no_se_abre_un_establecimiento_en_la_sucursal_de_otra_empresa(mundo):
    """La escritura hermana comprobaba el tenant en vez de la empresa."""
    r = mundo.post("/organization/establishments", "ua", mundo.company_a,
                   {"branch_id": mundo.branch_b, "code": "N10-EST-CRUZADO",
                    "name": "Establecimiento cruzado"})
    assert r.status_code in BLOQUEO, (
        f"A abrió un establecimiento en una sucursal de B: {r.status_code} {r.text}")
