"""Spec 023 · capacidad de saldo multiestado (`ADR-D0-010` v2).

Lo que estas pruebas defienden, en una frase cada una: que el motor escriba el
estado que le piden y rechace el que no está declarado; que el saldo se pueda
reconstruir desde el ledger sin colapsar los estados **ni** perder la cantidad
base; y que la mercancía no vendible siga sin poder venderse ni reservarse.

Multiempresa sobre PostgreSQL real, con el arnés `mundo`: dos tenants, tres
empresas. Cada negativa falla por su motivo exacto y ninguna es tautológica.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.inventory import service as inv
from app.modules.inventory import states
from app.modules.inventory.models import InventoryBalance, InventoryMovement

pytest_plugins = ("tests.conftest_multicompany",)


def _tipo_entrada(db, company_id):
    return inv._get_movement_type_by_code(db, company_id, "ENTRADA_RECEPCION")


def _producto(db, company_id: str, marca: str) -> str:
    """Un artículo real de esa empresa. Lo que se prueba es el motor, no el CRUD."""
    from app.modules.master_data.models import CatalogItem

    item = CatalogItem(company_id=company_id, code=f"MS-{marca}", name=f"Artículo {marca}",
                       item_type="PRODUCT", status="ACTIVE")
    db.add(item)
    db.flush()
    return str(item.id)


def _entrada(db, *, company_id, warehouse_id, product_id, qty, state=None, presentation_id=None):
    return inv.record_movement(
        db, company_id=company_id, warehouse_id=warehouse_id, product_id=product_id,
        movement_type_id=str(_tipo_entrada(db, company_id).id), quantity=qty,
        state=state, presentation_id=presentation_id, actor="qa")


def _saldos(db, company_id, product_id) -> dict[str, Decimal]:
    filas = db.execute(select(InventoryBalance).where(
        InventoryBalance.company_id == company_id,
        InventoryBalance.product_id == product_id)).scalars().all()
    return {f.state: Decimal(str(f.qty_on_hand)) for f in filas}


# ------------------------------------------------------------------ catálogo
def test_el_catalogo_tiene_los_quince_estados_del_adr():
    """Quince, no siete: los siete son los de lote y serial de `FR-003-035`."""
    assert len(states.MERCHANDISE_STATES) == 15, states.MERCHANDISE_STATES
    for esperado in ("ESPERADO", "RECIBIDO", "PENDIENTE_CONFIRMACION", "CUARENTENA",
                     "BLOQUEADO", "DISPONIBLE", "RESERVADO", "PICKING", "PREPARADO",
                     "TRANSITO", "DESPACHADO", "DEVUELTO", "RECHAZADO", "DESECHO", "VENDIDO"):
        assert esperado in states.MERCHANDISE_STATES, esperado


def test_vencido_no_es_estado_de_mercancia():
    """Pertenece al vocabulario de lote y serial. Mezclarlos era el riesgo."""
    assert "VENCIDO" not in states.MERCHANDISE_STATES
    assert "VENCIDO" in inv.LOT_SERIAL_TRANSITIONS


def test_solo_disponible_es_vendible_y_reservable():
    """`R-D0-10-3` y `R-D0-03-5`, sin excepción por empresa."""
    vendibles = [e for e in states.MERCHANDISE_STATES if states.is_sellable(e)]
    reservables = [e for e in states.MERCHANDISE_STATES if states.is_reservable(e)]
    assert vendibles == ["DISPONIBLE"], vendibles
    assert reservables == ["DISPONIBLE"], reservables


# --------------------------------------------------------------- transiciones
def test_las_cuatro_transiciones_que_necesita_la_021_estan_declaradas():
    for origen, destino in (("RECIBIDO", "DISPONIBLE"), ("RECIBIDO", "RECHAZADO"),
                            ("CUARENTENA", "DISPONIBLE"), ("CUARENTENA", "RECHAZADO")):
        assert states.can_transition(origen, destino), f"{origen}→{destino}"


def test_ninguna_transicion_activa_sale_de_disponible():
    """El hallazgo que cerró `OQ-D010-02`: la cadena va hacia lo vendible."""
    salidas = [t for t in states.ACTIVE_TRANSITIONS if t.source == "DISPONIBLE"]
    assert salidas == [], salidas


def test_una_transicion_no_declarada_se_rechaza_por_nombre(mundo):
    from app.core.errors import ConflictError

    with pytest.raises(ConflictError) as info:
        states.assert_transition("DISPONIBLE", "CUARENTENA")
    assert info.value.code == "MERCHANDISE_TRANSITION_DENIED"
    assert info.value.details["source_state"] == "DISPONIBLE"


def test_un_estado_inventado_no_pasa_de_la_puerta():
    from app.core.errors import KontrolError

    with pytest.raises(KontrolError) as info:
        states.assert_valid_state("CALIDAD")
    assert info.value.code == "MERCHANDISE_STATE_UNKNOWN"
    assert info.value.status_code == 422


# ------------------------------------------------------------------- escritura
def test_el_motor_escribe_el_estado_que_le_piden(mundo):
    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=producto, qty=10, state="RECIBIDO")
        db.commit()
        assert _saldos(db, mundo.company_a, producto) == {"RECIBIDO": Decimal("10")}
    finally:
        db.close()


def test_sin_estado_explicito_el_saldo_nace_disponible(mundo):
    """Compatibilidad declarada: el ADR conserva el salto hasta que 021 lo cambie."""
    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=producto, qty=7)
        db.commit()
        assert _saldos(db, mundo.company_a, producto) == {"DISPONIBLE": Decimal("7")}
    finally:
        db.close()


def test_una_entrada_en_estado_no_declarado_no_deja_rastro(mundo):
    """Falla **antes** de escribir: ni movimiento ni saldo."""
    from app.core.errors import ConflictError

    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        with pytest.raises(ConflictError) as info:
            _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                     product_id=producto, qty=5, state="PICKING")
        assert info.value.code == "MERCHANDISE_TRANSITION_DENIED"
        db.rollback()
        assert _saldos(db, mundo.company_a, producto) == {}
        movimientos = db.execute(select(InventoryMovement).where(
            InventoryMovement.product_id == producto)).scalars().all()
        assert movimientos == []
    finally:
        db.close()


def test_el_movimiento_guarda_de_donde_sale_y_a_donde_entra(mundo):
    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        m = _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                     product_id=producto, qty=4, state="RECIBIDO")
        db.commit()
        assert m.source_state is None
        assert m.target_state == "RECIBIDO"
    finally:
        db.close()


# -------------------------------------------------------------- reclasificación
def test_la_reclasificacion_conserva_el_fisico(mundo):
    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=producto, qty=100, state="RECIBIDO")
        db.flush()
        antes = sum(_saldos(db, mundo.company_a, producto).values())

        inv.reclassify(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                       product_id=producto, source_state="RECIBIDO", target_state="DISPONIBLE",
                       quantity=90, actor="qa")
        db.commit()

        saldos = _saldos(db, mundo.company_a, producto)
        assert saldos == {"RECIBIDO": Decimal("10"), "DISPONIBLE": Decimal("90")}
        assert sum(saldos.values()) == antes == Decimal("100")
    finally:
        db.close()


def test_no_se_puede_reclasificar_mas_de_lo_que_hay_en_el_origen(mundo):
    from app.core.errors import ConflictError

    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=producto, qty=5, state="RECIBIDO")
        db.flush()
        with pytest.raises(ConflictError) as info:
            inv.reclassify(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                           product_id=producto, source_state="RECIBIDO",
                           target_state="DISPONIBLE", quantity=6, actor="qa")
        assert info.value.code == "INSUFFICIENT_STATE_QUANTITY"
        assert Decimal(info.value.details["available"]) == Decimal("5")
    finally:
        db.close()


def test_una_transicion_que_exige_motivo_lo_exige_de_verdad(mundo):
    from app.core.errors import KontrolError

    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=producto, qty=10, state="RECIBIDO")
        db.flush()
        with pytest.raises(KontrolError) as info:
            inv.reclassify(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                           product_id=producto, source_state="RECIBIDO",
                           target_state="RECHAZADO", quantity=3, actor="qa")
        assert info.value.code == "TRANSITION_REASON_REQUIRED"
        # Con motivo, la misma transición procede.
        inv.reclassify(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                       product_id=producto, source_state="RECIBIDO", target_state="RECHAZADO",
                       quantity=3, reason="No apto: embalaje roto", actor="qa")
        db.commit()
        assert _saldos(db, mundo.company_a, producto)["RECHAZADO"] == Decimal("3")
    finally:
        db.close()


def test_reclasificar_a_un_destino_no_declarado_no_mueve_nada(mundo):
    from app.core.errors import ConflictError

    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=producto, qty=20, state="RECIBIDO")
        db.flush()
        with pytest.raises(ConflictError):
            inv.reclassify(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                           product_id=producto, source_state="RECIBIDO",
                           target_state="DESECHO", quantity=5, reason="x", actor="qa")
        db.rollback()
        assert _saldos(db, mundo.company_a, producto) == {}
    finally:
        db.close()


# ------------------------------------------------------- paridad de reconstrucción
def test_reconstruir_da_exactamente_lo_mismo_que_el_camino_incremental(mundo):
    """La invariante del ciclo: `incremental == recompute`, estado por estado.

    Antes de esta Spec fallaba por dos motivos a la vez: la reconstrucción fijaba
    `DISPONIBLE` para todo —colapsando los estados— y acumulaba la cantidad
    **tecleada** en vez de la base, de modo que dos cajas de doce volvían a ser
    dos. La segunda es la misma caja ×12 que la Spec 019 corrigió en el
    incremental y que aquí seguía viva.
    """
    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=producto, qty=100, state="RECIBIDO")
        inv.reclassify(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                       product_id=producto, source_state="RECIBIDO", target_state="DISPONIBLE",
                       quantity=60, actor="qa")
        inv.reclassify(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                       product_id=producto, source_state="RECIBIDO", target_state="CUARENTENA",
                       quantity=25, reason="Inspección de calidad", actor="qa")
        db.commit()

        incremental = _saldos(db, mundo.company_a, producto)
        assert incremental == {"RECIBIDO": Decimal("15"), "DISPONIBLE": Decimal("60"),
                               "CUARENTENA": Decimal("25")}

        inv.recompute_balances(db, company_id=mundo.company_a)
        db.commit()

        assert _saldos(db, mundo.company_a, producto) == incremental
    finally:
        db.close()


def test_reconstruir_no_reintroduce_la_caja_por_doce(mundo):
    """Con presentación, reconstruir debe dar la base, no lo tecleado.

    El producto y la caja se crean por la API real, como en la Spec 019, porque
    el factor vive en una versión de presentación y falsificarlo por ORM probaría
    otra cosa.
    """
    from datetime import UTC, datetime, timedelta

    unidad = mundo.crear("/maestros/unidades", "ua", mundo.company_a,
                         {"code": "UND-023", "name": "Unidad", "symbol": "u", "decimals": 0})
    prod = mundo.crear("/maestros/catalogos/items", "ua", mundo.company_a,
                       {"code": "P023-CAJA", "name": "Producto caja", "item_type": "PRODUCT",
                        "status": "ACTIVE", "base_unit_id": unidad})
    caja = mundo.crear(f"/maestros/productos/{prod}/presentaciones", "ua", mundo.company_a,
                       {"code": "CAJA12-023", "name": "Caja de 12", "factor_to_base": "12",
                        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()})

    db = mundo.factory()
    try:
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=2, presentation_id=caja)
        db.commit()
        assert _saldos(db, mundo.company_a, prod)["DISPONIBLE"] == Decimal("24")

        inv.recompute_balances(db, company_id=mundo.company_a)
        db.commit()
        assert _saldos(db, mundo.company_a, prod)["DISPONIBLE"] == Decimal("24"), \
            "la reconstrucción volvió a contar cajas como unidades"
    finally:
        db.close()


# ------------------------------------------------------------------ vendibilidad
def test_lo_no_vendible_no_se_ofrece_ni_se_reserva(mundo):
    """Diez vendibles y cien en cuarentena no son ciento diez disponibles."""
    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_a, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=producto, qty=10)
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=producto, qty=100, state="RECIBIDO")
        db.commit()

        disponible = inv.get_available(db, company_id=mundo.company_a,
                                       warehouse_id=mundo.warehouse_a, product_id=producto)
        assert Decimal(str(disponible)) == Decimal("10")
        saldo = inv.lock_balance(db, company_id=mundo.company_a,
                                 warehouse_id=mundo.warehouse_a, product_id=producto)
        assert saldo.state == "DISPONIBLE"
        assert inv.available_under_lock(db, saldo) == Decimal("10")
    finally:
        db.close()


# ----------------------------------------------------------------- multiempresa
def test_una_empresa_no_reclasifica_el_saldo_de_otra(mundo):
    """El saldo de B no existe para A: el origen sale vacío y la cantidad falla."""
    from app.core.errors import ConflictError

    db = mundo.factory()
    try:
        producto = _producto(db, mundo.company_b, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_b, warehouse_id=mundo.warehouse_b,
                 product_id=producto, qty=50, state="RECIBIDO")
        db.commit()

        with pytest.raises(ConflictError) as info:
            inv.reclassify(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_b,
                           product_id=producto, source_state="RECIBIDO",
                           target_state="DISPONIBLE", quantity=10, actor="qa")
        assert info.value.code == "INSUFFICIENT_STATE_QUANTITY"
        assert Decimal(info.value.details["available"]) == Decimal("0")
        db.rollback()

        # Y el saldo de B queda intacto.
        assert _saldos(db, mundo.company_b, producto) == {"RECIBIDO": Decimal("50")}
    finally:
        db.close()


def test_el_saldo_de_cada_empresa_es_suyo_aunque_el_estado_coincida(mundo):
    db = mundo.factory()
    try:
        pa = _producto(db, mundo.company_a, uuid4().hex[:8])
        pb = _producto(db, mundo.company_b, uuid4().hex[:8])
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=pa, qty=3, state="RECIBIDO")
        _entrada(db, company_id=mundo.company_b, warehouse_id=mundo.warehouse_b,
                 product_id=pb, qty=8, state="RECIBIDO")
        db.commit()
        assert _saldos(db, mundo.company_a, pa) == {"RECIBIDO": Decimal("3")}
        assert _saldos(db, mundo.company_b, pb) == {"RECIBIDO": Decimal("8")}
    finally:
        db.close()
