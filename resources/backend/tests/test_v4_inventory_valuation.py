"""V4 · integridad del ledger y de la valoración del inventario (P3 Enterprise).

Cada prueba responde a la pregunta de V4: ¿puede una unidad entrar, transferirse,
ajustarse, revertirse y salir sin perder cantidad, valor, trazabilidad ni
autorización? Corre sobre PostgreSQL real con el arnés `mundo`; la concurrencia
solo vale ahí (`FOR UPDATE` no existe en SQLite).

Defectos que reproduce (rebaseline Enterprise, `ENTERPRISE_CURRENT_DEFECTS.md`):
D-INV-TRANSFER-COST, D-INV-TRANSFER-RECEIPT, D-INV-REVERSE-STATE, D-INV-RECOMPUTE,
D-INV-ADJ-NO-APPLY, D-INV-COUNT-STUCK y la sobretransferencia concurrente.
"""

from __future__ import annotations

import os
import threading
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import ConflictError
from app.modules.inventory import service as inv
from app.modules.inventory.models import (
    CostingProfile,
    CostLayer,
    InventoryAdjustment,
    InventoryBalance,
    InventoryMovement,
    StockCount,
    Transfer,
    TransferLine,
)
from app.modules.master_data.models import CatalogItem
from tests.conftest_multicompany import PASSWORD

pytest_plugins = ("tests.conftest_multicompany",)

pytestmark = pytest.mark.skipif(not os.environ.get("KONTROL_TEST_DB_URL"),
                                reason="V4 se certifica sobre PostgreSQL real")

D = Decimal


# --------------------------------------------------------------------------- #
# Construcción del mundo
# --------------------------------------------------------------------------- #
def _producto(db, company_id: str, metodo: str | None = None) -> str:
    marca = uuid4().hex[:8]
    item = CatalogItem(company_id=company_id, code=f"V4-{marca}", name=f"Artículo V4 {marca}",
                       item_type="PRODUCT", status="ACTIVE")
    db.add(item)
    db.flush()
    if metodo:
        db.add(CostingProfile(company_id=company_id, product_id=str(item.id), code=f"CP-{marca}",
                              method=metodo, status="ACTIVE"))
        db.flush()
    return str(item.id)


def _almacen(db, company_id: str) -> str:
    from app.modules.organization.models import Warehouse

    marca = uuid4().hex[:6]
    wh = Warehouse(company_id=company_id, code=f"WV4-{marca}", name=f"Almacén V4 {marca}", status="ACTIVE")
    db.add(wh)
    db.flush()
    return str(wh.id)


def _entrada(db, company_id, warehouse_id, product_id, qty, costo, ref=None, state=None):
    tipo = inv._get_movement_type_by_code(db, company_id, "ENTRADA_RECEPCION")
    return inv.record_movement(db, company_id=company_id, warehouse_id=warehouse_id, product_id=product_id,
                               movement_type_id=str(tipo.id), quantity=qty, unit_cost=costo,
                               document_ref=ref or f"REC-{uuid4().hex[:6]}", actor="qa", state=state)


def _valor(db, company_id, product_id, warehouse_id=None) -> D:
    return D(str(inv.valuation(db, company_id=company_id, product_id=product_id, warehouse_id=warehouse_id)))


def _fisico(db, company_id, product_id, warehouse_id, state="DISPONIBLE") -> D:
    filas = db.execute(select(InventoryBalance).where(
        InventoryBalance.company_id == company_id, InventoryBalance.product_id == product_id,
        InventoryBalance.warehouse_id == warehouse_id, InventoryBalance.state == state)).scalars().all()
    return sum((D(str(f.qty_on_hand)) for f in filas), D(0))


def _transferencia(db, company_id, origen, destino, product_id, qty) -> Transfer:
    t = Transfer(company_id=company_id, code=f"TR-{uuid4().hex[:6]}", origin_warehouse_id=origen,
                 destination_warehouse_id=destino, status="APPROVED", created_by="qa")
    db.add(t)
    db.flush()
    db.add(TransferLine(transfer_id=str(t.id), product_id=product_id, quantity_sent=qty))
    db.flush()
    return t


def _linea(db, t: Transfer) -> TransferLine:
    return db.execute(select(TransferLine).where(TransferLine.transfer_id == t.id)).scalars().one()


@pytest.fixture()
def db(mundo):
    s = mundo.factory()
    try:
        yield s
    finally:
        s.rollback()
        s.close()


# --------------------------------------------------------------------------- #
# Transferencia: cantidad y valor (D-INV-TRANSFER-COST)
# --------------------------------------------------------------------------- #
def test_transferencia_parcial_conserva_cantidad_y_valor(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    total_antes = _valor(db, c, p)
    t = _transferencia(db, c, a, b, p, 4)
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    inv.confirm_transfer_receipt(db, transfer=t, actor="qa")
    db.flush()
    assert _fisico(db, c, p, a) == D(6)
    assert _fisico(db, c, p, b) == D(4)
    assert _valor(db, c, p, a) == D("60")
    assert _valor(db, c, p, b) == D("40"), "el destino recibe la cantidad pero no el valor"
    assert _valor(db, c, p) == total_antes == D("100")


def test_transferencia_fifo_conserva_la_composicion_de_capas(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c, "FIFO")
    _entrada(db, c, a, p, 5, 10)
    _entrada(db, c, a, p, 5, 20)
    t = _transferencia(db, c, a, b, p, 7)
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    inv.confirm_transfer_receipt(db, transfer=t, actor="qa")
    db.flush()
    capas_b = db.execute(select(CostLayer).where(CostLayer.company_id == c, CostLayer.product_id == p,
                                                 CostLayer.warehouse_id == b, CostLayer.quantity_remaining > 0)
                         .order_by(CostLayer.created_at)).scalars().all()
    assert [(D(str(x.quantity_remaining)), D(str(x.unit_cost))) for x in capas_b] == [(D(5), D("10.00")), (D(2), D("20.00"))]
    assert _valor(db, c, p, a) == D("60")
    assert _valor(db, c, p, b) == D("90")
    assert _valor(db, c, p) == D("150")


def test_transferencia_conserva_el_landed_cost(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 1, 100)
    capa = db.execute(select(CostLayer).where(CostLayer.product_id == p, CostLayer.warehouse_id == a)).scalars().one()
    capa.landed_cost = D("20.00")   # lo que escribe la aplicación del landed cost (Spec 018)
    db.flush()
    assert _valor(db, c, p, a) == D("120")
    t = _transferencia(db, c, a, b, p, 1)
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    inv.confirm_transfer_receipt(db, transfer=t, actor="qa")
    db.flush()
    assert _valor(db, c, p, b) == D("120"), "el destino vuelve al costo base y pierde el landed cost"
    assert _valor(db, c, p) == D("120")


# --------------------------------------------------------------------------- #
# Recepción de transferencia (D-INV-TRANSFER-RECEIPT) — por la API
# --------------------------------------------------------------------------- #
def test_recepcion_parcial_por_la_api_y_luego_completa(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    t = _transferencia(db, c, a, b, p, 4)
    db.commit()
    linea = str(_linea(db, t).id)
    r = mundo.post(f"/inventory/transfers/{t.id}/transition", "admin", c, {"target": "IN_TRANSIT"})
    assert r.status_code == 200, r.text
    r = mundo.post(f"/inventory/transfers/{t.id}/transition", "admin", c,
                   {"target": "PARTIALLY_RECEIVED", "received": {linea: 3}})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "PARTIALLY_RECEIVED", "la API ignora lo recibido y da todo por recibido"
    r = mundo.post(f"/inventory/transfers/{t.id}/transition", "admin", c,
                   {"target": "RECEIVED", "received": {linea: 1}})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "RECEIVED"
    db.expire_all()
    assert _fisico(db, c, p, b) + _fisico(db, c, p, b, "CUARENTENA") == D(4), \
        "una segunda recepción vuelve a ingresar lo enviado completo"
    assert _valor(db, c, p) == D("100")


# --------------------------------------------------------------------------- #
# Reversión (D-INV-REVERSE-STATE)
# --------------------------------------------------------------------------- #
def test_revertir_una_entrada_retira_exactamente_su_capa(db, mundo):
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c, "FIFO")
    _entrada(db, c, a, p, 5, 10)
    segunda = _entrada(db, c, a, p, 5, 20)
    inv.reverse_movement(db, movement=segunda, actor="qa")
    db.flush()
    assert _fisico(db, c, p, a) == D(5)
    assert _valor(db, c, p) == D("50"), "el reverso consume la capa más antigua en vez de la suya"


def test_revertir_una_salida_restaura_cantidad_y_valor(db, mundo):
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c, "FIFO")
    _entrada(db, c, a, p, 5, 10)
    _entrada(db, c, a, p, 5, 20)
    tipo = inv._get_movement_type_by_code(db, c, "AJUSTE_NEGATIVO")
    salida = inv.record_movement(db, company_id=c, warehouse_id=a, product_id=p,
                                 movement_type_id=str(tipo.id), quantity=-7, document_ref="X", actor="qa")
    assert _valor(db, c, p) == D("60")
    inv.reverse_movement(db, movement=salida, actor="qa")
    db.flush()
    assert _fisico(db, c, p, a) == D(10)
    assert _valor(db, c, p) == D("150")


def test_revertir_respeta_el_estado_del_movimiento(db, mundo):
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    cuarentena = _entrada(db, c, a, p, 3, 10, state="CUARENTENA")
    inv.reverse_movement(db, movement=cuarentena, actor="qa")
    db.flush()
    assert _fisico(db, c, p, a, "CUARENTENA") == D(0)
    assert _fisico(db, c, p, a, "DISPONIBLE") == D(10), "el reverso descuenta DISPONIBLE en lugar de CUARENTENA"


def test_doble_reversion_bloqueada(db, mundo):
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    m = _entrada(db, c, a, p, 2, 10)
    inv.reverse_movement(db, movement=m, actor="qa")
    with pytest.raises(ConflictError) as e:
        inv.reverse_movement(db, movement=m, actor="qa")
    assert e.value.code == "ALREADY_REVERSED"
    tipo = inv._get_movement_type_by_code(db, c, "AJUSTE_NEGATIVO")
    _entrada(db, c, a, p, 5, 10)
    salida = inv.record_movement(db, company_id=c, warehouse_id=a, product_id=p, movement_type_id=str(tipo.id),
                                 quantity=-2, document_ref="Z", actor="qa")
    inv.reverse_movement(db, movement=salida, actor="qa")
    valor = _valor(db, c, p)
    with pytest.raises(ConflictError) as e:
        inv.reverse_movement(db, movement=salida, actor="qa")
    assert e.value.code == "ALREADY_REVERSED"
    assert _valor(db, c, p) == valor, "una segunda reversión no puede devolver valor otra vez"


def test_revertir_transferencia_restaura_ambos_almacenes(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c, "FIFO")
    _entrada(db, c, a, p, 5, 10)
    _entrada(db, c, a, p, 5, 20)
    t = _transferencia(db, c, a, b, p, 7)
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    inv.confirm_transfer_receipt(db, transfer=t, actor="qa")
    inv.reverse_transfer(db, transfer=t, actor="qa", reason="error de destino")
    db.flush()
    assert t.status == "REVERSED"
    assert (_fisico(db, c, p, a), _fisico(db, c, p, b)) == (D(10), D(0))
    assert (_valor(db, c, p, a), _valor(db, c, p, b)) == (D("150"), D("0"))
    with pytest.raises(ConflictError):
        inv.reverse_transfer(db, transfer=t, actor="qa", reason="otra vez")


# --------------------------------------------------------------------------- #
# Ajustes y conteos (D-INV-ADJ-NO-APPLY, D-INV-COUNT-STUCK)
# --------------------------------------------------------------------------- #
def test_ajuste_aprobado_ofrece_aplicar_y_mueve_el_ledger(db, mundo):
    assert inv.adjustment_allowed_actions("APPROVED").get("apply") is True
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    adj = InventoryAdjustment(company_id=c, warehouse_id=a, product_id=p, quantity=D(2), reason="hallazgo",
                              status="APPROVED", currency="VED", created_by="qa")
    db.add(adj)
    db.flush()
    inv.apply_adjustment(db, adjustment=adj, actor="qa")
    db.flush()
    assert _fisico(db, c, p, a) == D(12)
    assert _valor(db, c, p) == D("120"), "el ajuste positivo sin costo deja la cantidad sin valor"


def test_ajuste_negativo_consume_valor(db, mundo):
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    adj = InventoryAdjustment(company_id=c, warehouse_id=a, product_id=p, quantity=D(-3), reason="merma",
                              status="APPROVED", currency="VED", created_by="qa")
    db.add(adj)
    db.flush()
    inv.apply_adjustment(db, adjustment=adj, actor="qa")
    db.flush()
    assert _fisico(db, c, p, a) == D(7)
    assert _valor(db, c, p) == D("70")


def test_conteo_recorre_su_ciclo_y_valora_la_diferencia(db, mundo):
    acciones = inv.count_allowed_actions("FROZEN")
    assert acciones.get("start") is True and acciones.get("submit") is False, \
        "en FROZEN la pantalla ofrece enviar, pero la máquina exige pasar a COUNTING"
    assert inv.count_allowed_actions("COUNTING").get("submit") is True
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    conteo = StockCount(company_id=c, code=f"CT-{uuid4().hex[:6]}", warehouse_id=a, status="SUBMITTED",
                        created_by="qa")
    db.add(conteo)
    db.flush()
    inv.record_count_line(db, count_id=str(conteo.id), product_id=p, expected_qty=10, counted_qty=12)
    inv.approve_count(db, count=conteo, actor="qa")
    db.flush()
    assert _fisico(db, c, p, a) == D(12)
    assert _valor(db, c, p) == D("120"), "la diferencia positiva del conteo entra sin valor"


# --------------------------------------------------------------------------- #
# Recálculo de saldos (D-INV-RECOMPUTE)
# --------------------------------------------------------------------------- #
def _usuario_limitado(mundo, acciones: list[str]) -> str:
    from app.modules.identity_access import service as identity_service
    from app.modules.identity_access.models import Permission, Role, RolePermission, UserRole, UserScope

    s = mundo.factory()
    try:
        nombre = f"inv-{uuid4().hex[:6]}"
        user = identity_service.create_user(s, tenant_id=mundo.t1, username=nombre,
                                            email=f"{nombre}@demo.test", password=PASSWORD, created_by=None)
        rol = Role(code=f"R-{nombre}", name=nombre, tenant_id=mundo.t1, protected=False, status="ACTIVE")
        s.add(rol)
        s.flush()
        for accion in acciones:
            perm = s.execute(select(Permission).where(Permission.resource == "inventario",
                                                      Permission.action == accion)).scalars().first()
            assert perm is not None, accion
            s.add(RolePermission(role_id=str(rol.id), permission_id=str(perm.id)))
        s.add(UserRole(user_id=str(user.id), role_id=str(rol.id), company_id=None))
        s.add(UserScope(user_id=str(user.id), company_id=mundo.company_a))
        s.commit()
        return nombre
    finally:
        s.close()


def test_recalcular_saldos_exige_permiso_explicito(mundo):
    sin_permiso = _usuario_limitado(mundo, ["view", "create", "approve", "transition"])
    r = mundo.post("/inventory/balances/recompute", sin_permiso, mundo.company_a, {})
    assert r.status_code == 403, f"recalcular saldos solo exige estar autenticado: {r.status_code}"


def test_recalcular_saldos_audita_y_respeta_lo_ya_extraido(db, mundo):
    from app.modules.audit.models import AuditEvent

    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    res = inv.reserve(db, company_id=c, source_document="PED", product_id=p, warehouse_id=a, quantity=4,
                      actor="qa")
    res.picked_base_quantity = D(1)
    ancla = inv.lock_balance(db, company_id=c, warehouse_id=a, product_id=p)
    ancla.qty_reserved = D(3)
    db.commit()
    r = mundo.post(f"/inventory/balances/recompute?warehouse_id={a}", "admin", c, {})
    assert r.status_code == 200, r.text
    db.expire_all()
    ancla = db.execute(select(InventoryBalance).where(
        InventoryBalance.warehouse_id == a, InventoryBalance.product_id == p,
        InventoryBalance.state == "DISPONIBLE", InventoryBalance.location_id.is_(None))).scalars().one()
    assert D(str(ancla.qty_reserved)) == D(3), "la reconstrucción vuelve a reservar lo ya extraído"
    assert db.execute(select(AuditEvent).where(AuditEvent.action == "INVENTORY_BALANCES_RECOMPUTED",
                                               AuditEvent.company_id == c)).first() is not None


# --------------------------------------------------------------------------- #
# Aislamiento
# --------------------------------------------------------------------------- #
def test_transferencia_no_cruza_empresas(db, mundo):
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    db.commit()
    r = mundo.post("/inventory/transfers", "admin", c, {
        "code": f"X-{uuid4().hex[:5]}", "origin_warehouse_id": a, "destination_warehouse_id": mundo.warehouse_b,
        "lines": [{"product_id": p, "quantity_sent": 1}]})
    assert r.status_code == 404, r.text


def test_transferencia_no_permite_mismo_origen_y_destino(db, mundo):
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    db.commit()
    r = mundo.post("/inventory/transfers", "admin", c, {
        "code": f"X-{uuid4().hex[:5]}", "origin_warehouse_id": a, "destination_warehouse_id": a,
        "lines": [{"product_id": p, "quantity_sent": 1}]})
    assert r.status_code == 422, r.text


def test_otra_empresa_no_ve_ni_mueve_la_transferencia(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 5, 10)
    t = _transferencia(db, c, a, b, p, 2)
    db.commit()
    r = mundo.post(f"/inventory/transfers/{t.id}/transition", "ub", mundo.company_b, {"target": "IN_TRANSIT"})
    assert r.status_code == 404, r.text
    r = mundo.post(f"/inventory/transfers/{t.id}/transition", "uc", mundo.company_c,
                   {"target": "IN_TRANSIT"}, tenant="T2")
    assert r.status_code == 404, r.text


# --------------------------------------------------------------------------- #
# Concurrencia real (PostgreSQL)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("con_costo", [True, False])
def test_dos_transferencias_no_sacan_mas_de_lo_que_hay(mundo, con_costo):
    s = mundo.factory()
    try:
        c = mundo.company_a
        a, b = _almacen(s, c), _almacen(s, c)
        p = _producto(s, c)
        _entrada(s, c, a, p, 10, 10 if con_costo else None)
        t1 = _transferencia(s, c, a, b, p, 7)
        t2 = _transferencia(s, c, a, b, p, 7)
        s.commit()
        ids = [str(t1.id), str(t2.id)]
    finally:
        s.close()

    exitos: list[str] = []
    fallos: list[str] = []
    barrera = threading.Barrier(2)

    def _enviar(tid: str) -> None:
        s2 = mundo.factory()
        try:
            t = s2.get(Transfer, tid)
            barrera.wait()
            inv.confirm_transfer_ship(s2, transfer=t, actor="qa")
            s2.commit()
            exitos.append(tid)
        except ConflictError as e:
            s2.rollback()
            fallos.append(e.code)
        finally:
            s2.close()

    hilos = [threading.Thread(target=_enviar, args=(i,)) for i in ids]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    s = mundo.factory()
    try:
        assert len(exitos) == 1, f"dos salidas de 7 sobre 10: {exitos} {fallos}"
        assert fallos == ["INSUFFICIENT_STOCK"]
        assert _fisico(s, c, p, a) == D(3)
    finally:
        s.close()


# --------------------------------------------------------------------------- #
# Auditoría
# --------------------------------------------------------------------------- #
def test_la_salida_de_transferencia_deja_rastro_de_costo(db, mundo):
    from app.modules.audit.models import AuditEvent

    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    t = _transferencia(db, c, a, b, p, 4)
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    inv.confirm_transfer_receipt(db, transfer=t, actor="qa")
    db.flush()
    eventos = {e.action for e in db.execute(select(AuditEvent).where(
        AuditEvent.entity_id == str(t.id))).scalars().all()}
    assert {"INVENTORY_TRANSFER_SHIPPED", "INVENTORY_TRANSFER_RECEIVED"} <= eventos
    salida = db.execute(select(InventoryMovement).where(
        InventoryMovement.document_ref == f"TRANSFER:{t.id}", InventoryMovement.quantity < 0)).scalars().one()
    assert D(str(salida.unit_cost)) == D("10")


# --------------------------------------------------------------------------- #
# Bordes de la reversión y del tránsito
# --------------------------------------------------------------------------- #
def test_no_se_revierte_una_entrada_ya_consumida(db, mundo):
    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    entrada = _entrada(db, c, a, p, 5, 10)
    tipo = inv._get_movement_type_by_code(db, c, "AJUSTE_NEGATIVO")
    inv.record_movement(db, company_id=c, warehouse_id=a, product_id=p, movement_type_id=str(tipo.id),
                        quantity=-2, document_ref="X", actor="qa")
    with pytest.raises(ConflictError) as e:
        inv.reverse_movement(db, movement=entrada, actor="qa")
    assert e.value.code == "REVERSAL_COST_LAYER_CONSUMED"


def test_no_se_revierte_una_transferencia_cuya_mercancia_ya_salio_del_destino(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    t = _transferencia(db, c, a, b, p, 4)
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    inv.confirm_transfer_receipt(db, transfer=t, actor="qa")
    tipo = inv._get_movement_type_by_code(db, c, "AJUSTE_NEGATIVO")
    inv.record_movement(db, company_id=c, warehouse_id=b, product_id=p, movement_type_id=str(tipo.id),
                        quantity=-1, document_ref="Y", actor="qa")
    with pytest.raises(ConflictError):
        inv.reverse_transfer(db, transfer=t, actor="qa", reason="error")
    assert t.status == "RECEIVED"


def test_el_valor_en_transito_es_visible_y_vuelve_al_recibir(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    t = _transferencia(db, c, a, b, p, 4)
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    resumen = inv.transfer_cost_summary(db, t)
    assert (D(resumen["value_sent"]), D(resumen["value_in_transit"])) == (D("40.00"), D("40.00"))
    assert _valor(db, c, p) + D(resumen["value_in_transit"]) == D("100")
    inv.confirm_transfer_receipt(db, transfer=t, received={str(_linea(db, t).id): 1}, actor="qa")
    resumen = inv.transfer_cost_summary(db, t)
    assert D(resumen["value_in_transit"]) == D("30.00")
    assert _valor(db, c, p) + D(resumen["value_in_transit"]) == D("100")


def test_sin_existencia_suficiente_la_transferencia_no_sale(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 3, 10)
    t = _transferencia(db, c, a, b, p, 4)
    with pytest.raises(ConflictError) as e:
        inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    assert e.value.code == "INSUFFICIENT_STOCK"


def test_un_movimiento_de_transferencia_no_se_revierte_suelto(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    t = _transferencia(db, c, a, b, p, 4)
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    salida = db.execute(select(InventoryMovement).where(
        InventoryMovement.idempotency_key == f"TRANSFER-OUT:{_linea(db, t).id}:1")).scalars().one()
    with pytest.raises(ConflictError) as e:
        inv.reverse_movement(db, movement=salida, actor="qa")
    assert e.value.code == "REVERSAL_USE_DOCUMENT"


def test_aplicar_un_ajuste_deja_rastro(db, mundo):
    from app.modules.audit.models import AuditEvent

    c = mundo.company_a
    a = _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    adj = InventoryAdjustment(company_id=c, warehouse_id=a, product_id=p, quantity=D(-1), reason="rotura",
                              status="APPROVED", currency="VED", created_by="qa")
    db.add(adj)
    db.flush()
    inv.apply_adjustment(db, adjustment=adj, actor="qa")
    db.flush()
    evento = db.execute(select(AuditEvent).where(AuditEvent.action == "INVENTORY_ADJUSTMENT_APPLIED",
                                                 AuditEvent.entity_id == str(adj.id))).scalars().first()
    assert evento is not None


def test_la_transferencia_revertida_no_vuelve_a_ofrecer_revertir(db, mundo):
    assert inv.transfer_allowed_actions("REVERSED")["reverse"] is False
    assert inv.transfer_allowed_actions("RECEIVED")["reverse"] is True


def test_revertir_transferencia_por_la_api_exige_motivo(db, mundo):
    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    t = _transferencia(db, c, a, b, p, 4)
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    inv.confirm_transfer_receipt(db, transfer=t, actor="qa")
    db.commit()
    r = mundo.post(f"/inventory/transfers/{t.id}/reverse", "admin", c, {"reason": ""})
    assert r.status_code == 422, r.text
    r = mundo.post(f"/inventory/transfers/{t.id}/reverse", "admin", c, {"reason": "destino equivocado"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "REVERSED"
    r = mundo.post(f"/inventory/transfers/{t.id}/reverse", "admin", c, {"reason": "otra vez"})
    assert r.status_code == 409, r.text


def test_se_transfiere_mercancia_ya_ubicada_y_la_reversion_la_devuelve_a_su_ubicacion(db, mundo):
    from app.modules.organization.models import WarehouseLocation

    c = mundo.company_a
    a, b = _almacen(db, c), _almacen(db, c)
    p = _producto(db, c)
    _entrada(db, c, a, p, 10, 10)
    ubic = WarehouseLocation(company_id=c, warehouse_id=a, code=f"U-{uuid4().hex[:5]}", name="Pasillo 1",
                             sequence=1, status="ACTIVE")
    db.add(ubic)
    db.flush()
    inv.putaway(db, company_id=c, warehouse_id=a, product_id=p, target_location_id=str(ubic.id), quantity=8,
                actor="qa")
    t = _transferencia(db, c, a, b, p, 9)   # 2 sin ubicar + 7 de la ubicación
    inv.confirm_transfer_ship(db, transfer=t, actor="qa")
    inv.confirm_transfer_receipt(db, transfer=t, actor="qa")
    db.flush()
    assert (_fisico(db, c, p, a), _fisico(db, c, p, b)) == (D(1), D(9))
    assert (_valor(db, c, p, a), _valor(db, c, p, b)) == (D("10"), D("90"))
    inv.reverse_transfer(db, transfer=t, actor="qa", reason="no correspondía")
    db.flush()
    fila = db.execute(select(InventoryBalance).where(
        InventoryBalance.warehouse_id == a, InventoryBalance.product_id == p,
        InventoryBalance.location_id == str(ubic.id), InventoryBalance.state == "DISPONIBLE")).scalars().one()
    assert D(str(fila.qty_on_hand)) == D(8), "la reversión no devuelve la mercancía a su ubicación de origen"
    assert (_fisico(db, c, p, a), _valor(db, c, p)) == (D(10), D("100"))
