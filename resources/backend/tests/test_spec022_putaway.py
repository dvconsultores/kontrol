"""Spec 022 · put-away y ubicación (post `D0-14`).

Lo que estas pruebas defienden es la frase que bloqueó la Spec durante un ciclo
entero: **ubicar la mercancía no puede volverla invendible**. El compromiso de
reserva es del almacén y no de la ubicación (`R-D0-14-1`), así que mover
existencia de una ubicación a otra no puede tocar ni el reservado ni el
disponible del almacén.

Multiempresa sobre PostgreSQL real, con el arnés `mundo`.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.modules.inventory import service as inv
from app.modules.inventory.models import InventoryBalance
from app.modules.organization.models import WarehouseLocation

pytest_plugins = ("tests.conftest_multicompany",)


def _producto(db, company_id: str, marca: str) -> str:
    from app.modules.master_data.models import CatalogItem

    item = CatalogItem(company_id=company_id, code=f"PA-{marca}", name=f"Artículo {marca}",
                       item_type="PRODUCT", status="ACTIVE")
    db.add(item)
    db.flush()
    return str(item.id)


def _ubicacion(db, company_id: str, warehouse_id: str, code: str, *, status="ACTIVE",
               capacity_units=None, capacity_uom=None) -> str:
    loc = WarehouseLocation(company_id=company_id, warehouse_id=warehouse_id, code=code,
                            name=f"Ubicación {code}", sequence=1, status=status,
                            capacity_units=capacity_units, capacity_uom=capacity_uom)
    db.add(loc)
    db.flush()
    return str(loc.id)


def _entrada(db, *, company_id, warehouse_id, product_id, qty, state=None, presentation_id=None):
    tipo = inv._get_movement_type_by_code(db, company_id, "ENTRADA_RECEPCION")
    return inv.record_movement(
        db, company_id=company_id, warehouse_id=warehouse_id, product_id=product_id,
        movement_type_id=str(tipo.id), quantity=qty, state=state,
        presentation_id=presentation_id, actor="qa")


def _saldos(db, company_id, product_id) -> dict[tuple[str | None, str], Decimal]:
    filas = db.execute(select(InventoryBalance).where(
        InventoryBalance.company_id == company_id,
        InventoryBalance.product_id == product_id)).scalars().all()
    return {(f.location_id, f.state): Decimal(str(f.qty_on_hand)) for f in filas}


def _disponible(db, company_id, warehouse_id, product_id) -> Decimal:
    ancla = inv.lock_balance(db, company_id=company_id, warehouse_id=warehouse_id,
                             product_id=product_id)
    return inv.available_under_lock(db, ancla)


# ------------------------------------------------- el caso canónico de D0-14
def test_ubicar_no_toca_el_reservado_ni_el_disponible_del_almacen(mundo):
    """`R-D0-14-2`: el caso que bloqueó la Spec, convertido en regresión."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L1-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=100)
        inv.reserve(db, company_id=mundo.company_a, source_document="OV-1", product_id=prod,
                    warehouse_id=mundo.warehouse_a, quantity=30, actor="qa")
        db.flush()

        antes = _disponible(db, mundo.company_a, mundo.warehouse_a, prod)
        reservas_antes = len(inv.list_reservations(db, company_id=mundo.company_a)) \
            if hasattr(inv, "list_reservations") else None
        assert antes == Decimal("70")

        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=100, actor="qa")
        db.commit()

        saldos = _saldos(db, mundo.company_a, prod)
        assert saldos[(None, "DISPONIBLE")] == Decimal("0"), "quedó existencia sin ubicar"
        assert saldos[(l1, "DISPONIBLE")] == Decimal("100")
        assert sum(saldos.values()) == Decimal("100"), "la colocación creó o destruyó existencia"

        despues = _disponible(db, mundo.company_a, mundo.warehouse_a, prod)
        assert despues == Decimal("70"), "ubicar la mercancía cambió el disponible del almacén"
        if reservas_antes is not None:
            assert len(inv.list_reservations(db, company_id=mundo.company_a)) == reservas_antes
    finally:
        db.close()


def test_el_reservado_sigue_en_el_ancla_y_no_viaja_a_la_ubicacion(mundo):
    """`R-D0-14-1`: la ubicación no es dimensión de la reserva."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"L2-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=100)
        inv.reserve(db, company_id=mundo.company_a, source_document="OV-2", product_id=prod,
                    warehouse_id=mundo.warehouse_a, quantity=30, actor="qa")
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=100, actor="qa")
        db.commit()

        filas = db.execute(select(InventoryBalance).where(
            InventoryBalance.product_id == prod)).scalars().all()
        reservado = {(f.location_id, Decimal(str(f.qty_reserved))) for f in filas}
        assert (None, Decimal("30")) in reservado, "el compromiso salió del ancla"
        assert (l1, Decimal("0")) in reservado, "el compromiso viajó a la ubicación"
    finally:
        db.close()


# ------------------------------------------------------- disponible agregado
def test_el_disponible_suma_todas_las_ubicaciones(mundo):
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"A-{uuid4().hex[:6]}")
        l2 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"B-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=100)
        inv.reserve(db, company_id=mundo.company_a, source_document="OV-3", product_id=prod,
                    warehouse_id=mundo.warehouse_a, quantity=30, actor="qa")
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=40, actor="qa")
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l2, quantity=60, actor="qa")
        db.commit()
        assert _disponible(db, mundo.company_a, mundo.warehouse_a, prod) == Decimal("70")
    finally:
        db.close()


def test_lo_no_vendible_no_entra_en_el_disponible_aunque_este_ubicado(mundo):
    """`D0-10` sigue vigente: cien en cuarentena no son cien disponibles."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"C-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=100)
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=100, state="RECIBIDO")
        inv.reserve(db, company_id=mundo.company_a, source_document="OV-4", product_id=prod,
                    warehouse_id=mundo.warehouse_a, quantity=30, actor="qa")
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=100, actor="qa")
        db.commit()
        assert _disponible(db, mundo.company_a, mundo.warehouse_a, prod) == Decimal("70")
    finally:
        db.close()


# ---------------------------------------------------------------- el traslado
def test_el_movimiento_guarda_de_que_ubicacion_sale_y_a_cual_entra(mundo):
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"D-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=10)
        m = inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, target_location_id=l1, quantity=10, actor="qa")
        db.commit()
        assert m.source_location_id is None
        assert m.target_location_id == l1
        assert m.source_state == m.target_state == "DISPONIBLE", "el put-away cambió el estado"
    finally:
        db.close()


def test_no_se_puede_ubicar_mas_de_lo_que_hay_sin_ubicar(mundo):
    from app.core.errors import ConflictError

    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"E-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=10)
        db.flush()
        with pytest.raises(ConflictError) as info:
            inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, target_location_id=l1, quantity=11, actor="qa")
        assert info.value.code == "INSUFFICIENT_LOCATION_QUANTITY"
        db.rollback()
    finally:
        db.close()


# ------------------------------------------------------------- la reconstrucción
def test_reconstruir_da_lo_mismo_que_el_camino_incremental(mundo):
    """La invariante que la Spec 023 abrió y esta extiende a la ubicación."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"F-{uuid4().hex[:6]}")
        l2 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"G-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=100)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=70, actor="qa")
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l2, quantity=30, actor="qa")
        db.commit()

        incremental = _saldos(db, mundo.company_a, prod)
        assert incremental[(l1, "DISPONIBLE")] == Decimal("70")
        assert incremental[(l2, "DISPONIBLE")] == Decimal("30")

        inv.recompute_balances(db, company_id=mundo.company_a)
        db.commit()
        assert _saldos(db, mundo.company_a, prod) == incremental, "la reconstrucción derivó"
    finally:
        db.close()


def test_la_caja_por_doce_llega_ubicada_como_veinticuatro(mundo):
    """Extremo a extremo: recibir en cajas, ubicar en base."""
    unidad = mundo.crear("/maestros/unidades", "ua", mundo.company_a,
                         {"code": "UND-022", "name": "Unidad", "symbol": "u", "decimals": 0})
    prod = mundo.crear("/maestros/catalogos/items", "ua", mundo.company_a,
                       {"code": "P022-CAJA", "name": "Producto caja", "item_type": "PRODUCT",
                        "status": "ACTIVE", "base_unit_id": unidad})
    from datetime import UTC, datetime, timedelta
    caja = mundo.crear(f"/maestros/productos/{prod}/presentaciones", "ua", mundo.company_a,
                       {"code": "CAJA12-022", "name": "Caja de 12", "factor_to_base": "12",
                        "valid_from": (datetime.now(UTC) - timedelta(days=1)).isoformat()})
    db = mundo.factory()
    try:
        l1 = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"H-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=2, presentation_id=caja)
        db.flush()
        assert _saldos(db, mundo.company_a, prod)[(None, "DISPONIBLE")] == Decimal("24")

        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=l1, quantity=24, actor="qa")
        db.commit()
        assert _saldos(db, mundo.company_a, prod)[(l1, "DISPONIBLE")] == Decimal("24")

        inv.recompute_balances(db, company_id=mundo.company_a)
        db.commit()
        assert _saldos(db, mundo.company_a, prod)[(l1, "DISPONIBLE")] == Decimal("24")
    finally:
        db.close()


# ------------------------------------------------------------- las fronteras
def test_no_se_ubica_en_el_almacen_de_al_lado(mundo):
    """`R-D0-14-9`: trasladar entre almacenes es de la Spec 025, no de esta.

    El segundo almacén es **de la misma empresa**: la clave foránea compuesta de
    la Spec 008 ya impide que una ubicación cruce de empresa, así que probarlo
    con el almacén de otra empresa mediría otra cosa.
    """
    from app.core.errors import ConflictError
    from app.modules.organization.models import Warehouse

    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        segundo = Warehouse(company_id=mundo.company_a, code=f"W2-{uuid4().hex[:6]}",
                            name="Segundo almacén", warehouse_type="PHYSICAL", status="ACTIVE")
        db.add(segundo)
        db.flush()
        otra = _ubicacion(db, mundo.company_a, str(segundo.id), f"I-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=10)
        db.flush()
        with pytest.raises(ConflictError) as info:
            inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, target_location_id=otra, quantity=5, actor="qa")
        assert info.value.code == "LOCATION_OTHER_WAREHOUSE"
        db.rollback()
    finally:
        db.close()


def test_una_ubicacion_inactiva_no_admite_mercancia(mundo):
    from app.core.errors import ConflictError

    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        muerta = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"J-{uuid4().hex[:6]}",
                            status="INACTIVE")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=10)
        db.flush()
        with pytest.raises(ConflictError) as info:
            inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, target_location_id=muerta, quantity=5, actor="qa")
        assert info.value.code == "LOCATION_NOT_ELIGIBLE"
        db.rollback()
    finally:
        db.close()


def test_la_ubicacion_de_otra_empresa_no_existe_para_esta(mundo):
    from app.core.errors import NotFoundError

    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        ajena = _ubicacion(db, mundo.company_b, mundo.warehouse_b, f"K-{uuid4().hex[:6]}")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=10)
        db.flush()
        with pytest.raises(NotFoundError):
            inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                        product_id=prod, target_location_id=ajena, quantity=5, actor="qa")
        db.rollback()
    finally:
        db.close()


# -------------------------------------------------------------- la capacidad
def test_la_capacidad_no_bloquea(mundo):
    """`R-D0-14-6`: es informativa. Su unidad es texto libre y no puede rechazar."""
    db = mundo.factory()
    try:
        prod = _producto(db, mundo.company_a, uuid4().hex[:8])
        pequena = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"M-{uuid4().hex[:6]}",
                             capacity_units=5, capacity_uom="CAJAS")
        _entrada(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                 product_id=prod, qty=100)
        inv.putaway(db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a,
                    product_id=prod, target_location_id=pequena, quantity=100, actor="qa")
        db.commit()
        assert _saldos(db, mundo.company_a, prod)[(pequena, "DISPONIBLE")] == Decimal("100")
    finally:
        db.close()


def test_las_candidatas_son_las_activas_del_almacen_y_sin_orden_de_preferencia(mundo):
    """`R-D0-14-10`: sin recomendación. Se listan, no se puntúan."""
    db = mundo.factory()
    try:
        viva = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"N-{uuid4().hex[:6]}")
        muerta = _ubicacion(db, mundo.company_a, mundo.warehouse_a, f"O-{uuid4().hex[:6]}",
                            status="INACTIVE")
        otra_empresa = _ubicacion(db, mundo.company_b, mundo.warehouse_b, f"P-{uuid4().hex[:6]}")
        db.flush()
        ids = {str(x.id) for x in inv.putaway_candidates(
            db, company_id=mundo.company_a, warehouse_id=mundo.warehouse_a)}
        assert viva in ids
        assert muerta not in ids
        assert otra_empresa not in ids
    finally:
        db.close()
