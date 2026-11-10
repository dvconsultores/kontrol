# ruff: noqa: E402, F811, F401, I001
import os
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from test_importaciones_seguimiento import (
    _almacen,
    _operador,
    mundo,
)

from app.modules.inventory import models as inventory_models
from app.modules.inventory import service as inventory_service
from app.modules.master_data.models import CatalogItem
from app.modules.planning import models as planning_models
from app.modules.planning import service as planning_service
from app.modules.planning.engine import compute_plan
from app.shared.clock import hoy_de_negocio, inicio_del_dia_de_negocio

pytest_plugins = ["mfa_apoyo"]

API = "/api/v1"


def _producto(mundo):
    db = mundo.factory()
    try:
        product = CatalogItem(
            company_id=mundo.company_id,
            item_type="PRODUCT",
            code=f"PROD-{uuid.uuid4().hex[:8]}",
            name="Producto Prueba",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(product)
        db.flush()
        db.refresh(product)
        db.commit()
        return product.id
    finally:
        db.close()


def _dia(k):
    return inicio_del_dia_de_negocio(hoy_de_negocio() - timedelta(days=k)) + timedelta(hours=12)


def _entrada(mundo, warehouse_id, product_id, quantity, day):
    db = mundo.factory()
    try:
        inventory_service.record_movement(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            movement_type_id=inventory_service._get_movement_type_by_code(
                db, mundo.company_id, "ENTRADA_RECEPCION"
            ).id,
            quantity=quantity,
            unit_cost=1,
            occurred_at=_dia(day),
            actor=mundo.admin_id,
        )
        db.commit()
    finally:
        db.close()


def _despacho(mundo, warehouse_id, product_id, quantity, day):
    db = mundo.factory()
    try:
        for state_from, state_to in [
            ("DISPONIBLE", "PICKING"),
            ("PICKING", "PREPARADO"),
            ("PREPARADO", "DESPACHADO"),
        ]:
            inventory_service.reclassify(
                db,
                company_id=mundo.company_id,
                warehouse_id=warehouse_id,
                product_id=product_id,
                source_state=state_from,
                target_state=state_to,
                quantity=quantity,
                document_ref=f"SHIPMENT:{uuid.uuid4()}" if state_to == "DESPACHADO" else None,
                actor=mundo.admin_id,
                occurred_at=_dia(day),
            )
        db.commit()
    finally:
        db.close()


def _devolucion(mundo, warehouse_id, product_id, quantity, day):
    db = mundo.factory()
    try:
        inventory_service.reclassify(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            source_state="DESPACHADO",
            target_state="DEVUELTO",
            quantity=quantity,
            actor=mundo.admin_id,
            occurred_at=_dia(day),
        )
        db.commit()
    finally:
        db.close()


def _politica(mundo, warehouse_id, overrides=None):
    data = {
        "code": f"POL-{uuid.uuid4().hex[:8]}",
        "name": "Política motor",
        "warehouse_id": warehouse_id,
        "demand_source": "DISPATCHED_SALES",
        "lookback_days": 10,
        "horizon_days": 5,
        "lead_time_days": 3,
        "safety_mode": "DAYS",
        "safety_value": "2",
        "rotation_metric": "DEMAND_VELOCITY",
        "status": "ACTIVE",
    }
    if overrides:
        data.update(overrides)
    db = mundo.factory()
    try:
        planning_service.create_policy(
            db,
            company_id=mundo.company_id,
            data=data,
            actor_id=mundo.admin_id,
        )
        db.commit()
    finally:
        db.close()


def _desactivar_politicas(mundo, warehouse_id=None):
    db = mundo.factory()
    try:
        query = select(planning_models.PlanningPolicy).where(
            planning_models.PlanningPolicy.company_id == mundo.company_id,
        )
        if warehouse_id is not None:
            query = query.where(
                planning_models.PlanningPolicy.warehouse_id == warehouse_id,
            )
        for policy in db.scalars(query).all():
            policy.status = "INACTIVE"
        db.commit()
    finally:
        db.close()


def _desactivar_bandas(mundo):
    db = mundo.factory()
    try:
        for band in db.scalars(
            select(planning_models.RotationBand).where(
                planning_models.RotationBand.company_id == mundo.company_id,
            )
        ).all():
            band.status = "INACTIVE"
        db.commit()
    finally:
        db.close()


def test_engine_a_sin_politica(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["status"] == "PLAN_NOT_CONFIGURED"
        assert result["recommended_quantity"] is None
        assert result["on_hand"] is not None


def test_engine_b_sin_movimientos(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["status"] == "INSUFFICIENT_HISTORY"
        assert result["recommended_quantity"] is None


def test_engine_c_base(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    _entrada(mundo, warehouse, product, 100, 20)
    _despacho(mundo, warehouse, product, 20, 5)
    _despacho(mundo, warehouse, product, 10, 2)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["net_demand"] == "30.000000"
        assert result["avg_daily_demand"] == "3.000000"
        assert result["projected_demand"] == "15.000000"
        assert result["safety_stock"] == "6.000000"
        assert result["reorder_point"] == "15.000000"
        assert result["on_hand"] == "70.000000"
        assert result["available"] == "70.000000"
        assert result["coverage_days"] == "23.333333"
        assert result["recommended_quantity"] == "0.000000"
        assert result["demand_events"] == 2
        assert result["demand_days"] == 2
        assert result["history_partial"] is False


def test_engine_d_devolucion(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    _entrada(mundo, warehouse, product, 100, 20)
    _despacho(mundo, warehouse, product, 20, 5)
    _despacho(mundo, warehouse, product, 10, 2)
    _devolucion(mundo, warehouse, product, 5, 1)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["returned_quantity"] == "5.000000"
        assert result["net_demand"] == "25.000000"
        assert result["avg_daily_demand"] == "2.500000"


def test_engine_e_no_demanda(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    _entrada(mundo, warehouse, product, 100, 20)
    db = mundo.factory()
    try:
        inventory_service.record_movement(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
            movement_type_id=inventory_service._get_movement_type_by_code(
                db, mundo.company_id, "AJUSTE_NEGATIVO"
            ).id,
            quantity=-10,
            unit_cost=1,
            occurred_at=_dia(3),
            actor=mundo.admin_id,
        )
        db.commit()
    finally:
        db.close()
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["net_demand"] == "0.000000"
        assert result["avg_daily_demand"] == "0.000000"
        assert result["projected_demand"] == "0.000000"
        assert result["coverage_days"] is None
        assert result["recommended_quantity"] == "0.000000"
        assert result["status"] == "OK"


def test_engine_f_reverso(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse, {"demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, warehouse, product, 100, 20)
    db = mundo.factory()
    try:
        movement = inventory_service.record_movement(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
            movement_type_id=inventory_service._get_movement_type_by_code(
                db, mundo.company_id, "SALIDA_DESPACHO"
            ).id,
            quantity=-8,
            unit_cost=1,
            occurred_at=_dia(2),
            actor=mundo.admin_id,
        )
        inventory_service.reverse_movement(
            db,
            movement=movement,
            actor=mundo.admin_id,
            occurred_at=_dia(2),
        )
        inventory_service.record_movement(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
            movement_type_id=inventory_service._get_movement_type_by_code(
                db, mundo.company_id, "SALIDA_DESPACHO"
            ).id,
            quantity=-7,
            unit_cost=1,
            occurred_at=_dia(1),
            actor=mundo.admin_id,
        )
        db.commit()
    finally:
        db.close()
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["net_demand"] == "7.000000"


def test_engine_g_ventana(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    _entrada(mundo, warehouse, product, 100, 20)
    _despacho(mundo, warehouse, product, 4, 10)
    _despacho(mundo, warehouse, product, 6, 9)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["net_demand"] == "6.000000"


def test_engine_h_historia_parcial(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    _entrada(mundo, warehouse, product, 50, 3)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["history_partial"] is True
        assert result["observed_history_days"] == 4


def test_engine_i_recomendacion_positiva(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    _entrada(mundo, warehouse, product, 40, 20)
    _despacho(mundo, warehouse, product, 30, 5)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["avg_daily_demand"] == "3.000000"
        assert result["available"] == "10.000000"
        assert result["recommended_quantity"] == "11.000000"


def test_engine_j_fixed_qty(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse, {"safety_mode": "FIXED_QTY", "safety_value": "10"})
    _entrada(mundo, warehouse, product, 100, 20)
    _despacho(mundo, warehouse, product, 20, 5)
    _despacho(mundo, warehouse, product, 10, 2)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["safety_stock"] == "10.000000"
        assert result["reorder_point"] == "19.000000"


def test_engine_k_turnover(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse, {"rotation_metric": "TURNOVER"})
    _entrada(mundo, warehouse, product, 100, 20)
    _despacho(mundo, warehouse, product, 10, 1)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["avg_on_hand"] == "98.000000"
        assert result["turnover"] == "0.102041"


def test_engine_l_banda(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _desactivar_bandas(mundo)
    _politica(mundo, warehouse)
    codigo_rapida = f"RAPIDA-{uuid.uuid4().hex[:6]}"
    db = mundo.factory()
    try:
        planning_service.create_band(
            db,
            company_id=mundo.company_id,
            data={
                "code": f"LENTA-{uuid.uuid4().hex[:6]}",
                "name": "Lenta",
                "metric": "DEMAND_VELOCITY",
                "lower_bound": "0",
                "upper_bound": "2",
                "status": "ACTIVE",
            },
            actor_id=mundo.admin_id,
        )
        planning_service.create_band(
            db,
            company_id=mundo.company_id,
            data={
                "code": codigo_rapida,
                "name": "Rapida",
                "metric": "DEMAND_VELOCITY",
                "lower_bound": "2",
                "upper_bound": None,
                "status": "ACTIVE",
            },
            actor_id=mundo.admin_id,
        )
        db.commit()
    finally:
        db.close()
    _entrada(mundo, warehouse, product, 100, 20)
    _despacho(mundo, warehouse, product, 20, 5)
    _despacho(mundo, warehouse, product, 10, 2)
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["rotation_band"] is not None
        assert result["rotation_band"]["code"] == codigo_rapida


def test_engine_m_reservado(mundo):
    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    _entrada(mundo, warehouse, product, 100, 20)
    _despacho(mundo, warehouse, product, 20, 5)
    _despacho(mundo, warehouse, product, 10, 2)
    db = mundo.factory()
    try:
        inventory_service.reserve(
            db,
            company_id=mundo.company_id,
            source_document=None,
            product_id=product,
            warehouse_id=warehouse,
            quantity=5,
            actor=mundo.admin_id,
        )
        db.commit()
    finally:
        db.close()
    with mundo.factory() as db:
        result = compute_plan(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse,
            product_id=product,
        )
        assert result["reserved"] == "5.000000"
        assert result["available"] == "65.000000"


def test_engine_n_api(mundo, reloj_mfa):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol_compras = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"compras-{uuid.uuid4().hex[:8]}",
            name="Compras",
            company_id=None,
            permissions=["compras:view"],
            actor=mundo.admin_id,
        )
        rol_maestros = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"maestros-{uuid.uuid4().hex[:8]}",
            name="Maestros",
            company_id=None,
            permissions=["maestros:view"],
            actor=mundo.admin_id,
        )
        db.commit()
        rol_compras_id = rol_compras["id"]
        rol_maestros_id = rol_maestros["id"]
    finally:
        db.close()

    warehouse = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    _entrada(mundo, warehouse, product, 100, 20)

    cab = _operador(mundo, reloj_mfa, rol_compras_id)
    r = mundo.client.get(
        f"{API}/planning/plan?warehouse_id={warehouse}&product_id={product}",
        headers=cab,
    )
    assert r.status_code == 200
    assert r.json()["product_code"] is not None

    cab_maestros = _operador(mundo, reloj_mfa, rol_maestros_id)
    r2 = mundo.client.get(
        f"{API}/planning/plan?warehouse_id={warehouse}&product_id={product}",
        headers=cab_maestros,
    )
    assert r2.status_code == 403

    # almacén de otra empresa
    with mundo.factory() as db:
        from app.modules.organization.models import Company, Warehouse

        company_b = db.scalars(select(Company).where(Company.tenant_id == mundo.tenant_b_id)).first()
        warehouse_b = Warehouse(
            company_id=company_b.id,
            code=f"WHB-{uuid.uuid4().hex[:6]}",
            name="Warehouse B",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(warehouse_b)
        db.flush()
        warehouse_b_id = warehouse_b.id
        db.commit()
    r3 = mundo.client.get(
        f"{API}/planning/plan?warehouse_id={warehouse_b_id}&product_id={product}",
        headers=cab,
    )
    assert r3.status_code == 404


def test_engine_o_api_lista(mundo, reloj_mfa):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol_compras = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"compras-{uuid.uuid4().hex[:8]}",
            name="Compras",
            company_id=None,
            permissions=["compras:view"],
            actor=mundo.admin_id,
        )
        db.commit()
        rol_compras_id = rol_compras["id"]
    finally:
        db.close()

    warehouse = _almacen(mundo, mundo.company_id)
    product_a = _producto(mundo)
    product_b = _producto(mundo)
    product_c = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=warehouse)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, warehouse)
    _entrada(mundo, warehouse, product_a, 100, 20)
    _entrada(mundo, warehouse, product_b, 80, 15)

    cab = _operador(mundo, reloj_mfa, rol_compras_id)

    with mundo.factory() as db:
        code_a = db.get(CatalogItem, product_a).code
        code_b = db.get(CatalogItem, product_b).code
        code_c = db.get(CatalogItem, product_c).code

    r = mundo.client.get(
        f"{API}/planning/plans?warehouse_id={warehouse}",
        headers=cab,
    )
    assert r.status_code == 200
    assert r.json()["total"] == 2
    product_codes = [item["product_code"] for item in r.json()["items"]]
    assert code_a in product_codes
    assert code_b in product_codes
    assert code_c not in product_codes

    r_q = mundo.client.get(
        f"{API}/planning/plans?warehouse_id={warehouse}&q={code_a}",
        headers=cab,
    )
    assert r_q.status_code == 200
    assert r_q.json()["total"] == 1
    assert r_q.json()["items"][0]["product_code"] == code_a

    r_page = mundo.client.get(
        f"{API}/planning/plans?warehouse_id={warehouse}&page_size=51",
        headers=cab,
    )
    assert r_page.status_code == 422
