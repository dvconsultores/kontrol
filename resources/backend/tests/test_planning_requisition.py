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


def _dia(k):
    return inicio_del_dia_de_negocio(hoy_de_negocio() - timedelta(days=k)) + timedelta(hours=12)


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


def _crear_rol(mundo, permissions):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"rol-{uuid.uuid4().hex[:8]}",
            name="Rol Prueba",
            company_id=None,
            permissions=permissions,
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


def _crear_requisicion(mundo, cab, warehouse_id=None):
    r = mundo.client.post(
        f"{API}/purchasing/requisitions",
        headers=cab,
        json={"code": f"REQ-{uuid.uuid4().hex[:8]}", "warehouse_id": warehouse_id},
    )
    assert r.status_code == 200
    return r.json()["id"]


def test_a_almacen_ajeno(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create"])
    cab = _operador(mundo, reloj_mfa, rol_id)

    with mundo.factory() as db:
        from app.modules.organization.models import Company, Warehouse

        company_b = db.scalars(select(Company).where(Company.tenant_id == mundo.tenant_b_id)).first()
        wh_b = Warehouse(
            company_id=company_b.id,
            code=f"WHB-{uuid.uuid4().hex[:6]}",
            name="Warehouse B",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(wh_b)
        db.flush()
        wh_b_id = wh_b.id
        db.commit()

    r = mundo.client.post(
        f"{API}/purchasing/requisitions",
        headers=cab,
        json={"code": f"REQ-{uuid.uuid4().hex[:8]}", "warehouse_id": wh_b_id},
    )
    assert r.status_code == 404
    assert r.json()["code"] == "WAREHOUSE_NOT_FOUND"


def test_b_sin_almacen(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create"])
    cab = _operador(mundo, reloj_mfa, rol_id)
    req_id = _crear_requisicion(mundo, cab)
    product = _producto(mundo)

    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={"product_id": product, "quantity": "7"},
    )
    assert r.status_code == 422
    assert r.json()["code"] == "REQUISITION_WAREHOUSE_REQUIRED"


def test_c_sin_politica(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create"])
    cab = _operador(mundo, reloj_mfa, rol_id)
    wh = _almacen(mundo, mundo.company_id)
    _desactivar_politicas(mundo, warehouse_id=wh)
    _desactivar_politicas(mundo, warehouse_id=None)
    req_id = _crear_requisicion(mundo, cab, wh)
    product = _producto(mundo)

    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={"product_id": product, "quantity": "7"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["plan"]["status"] == "PLAN_NOT_CONFIGURED"
    assert data["plan"]["requested_base_quantity"] == "7.000000"
    assert data["plan"]["difference"] is None
    assert data["plan"]["accepted_recommendation"] is False

    r2 = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={"product_id": product, "use_recommendation": True},
    )
    assert r2.status_code == 422
    assert r2.json()["code"] == "RECOMMENDATION_NOT_AVAILABLE"


def _preparar_politica_y_stock(mundo, wh):
    product = _producto(mundo)
    _desactivar_politicas(mundo, warehouse_id=wh)
    _desactivar_politicas(mundo, warehouse_id=None)
    _politica(mundo, wh)
    _entrada(mundo, wh, product, 35, 20)
    _despacho(mundo, wh, product, 20, 5)
    _despacho(mundo, wh, product, 10, 2)
    return product


def _leer_plan(mundo, cab, wh, product):
    r = mundo.client.get(
        f"{API}/planning/plan?warehouse_id={wh}&product_id={product}",
        headers=cab,
    )
    assert r.status_code == 200
    data = r.json()
    assert Decimal(data["recommended_quantity"]) > 0
    return data


def test_d_aceptar_sugerencia(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create"])
    cab = _operador(mundo, reloj_mfa, rol_id)
    wh = _almacen(mundo, mundo.company_id)
    product = _preparar_politica_y_stock(mundo, wh)
    plan = _leer_plan(mundo, cab, wh, product)
    recommended = plan["recommended_quantity"]
    version = plan["policy"]["version"]
    req_id = _crear_requisicion(mundo, cab, wh)

    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={
            "product_id": product,
            "use_recommendation": True,
            "expected_policy_version": version,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["plan"]["requested_base_quantity"] == recommended
    assert data["plan"]["difference"] == "0.000000"
    assert data["plan"]["accepted_recommendation"] is True
    line_id = data["line_id"]

    with mundo.factory() as db:
        from app.modules.audit.models import AuditEvent

        event = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "REQUISITION_LINE_PLANNED",
                AuditEvent.entity_id == line_id,
            )
        ).first()
        assert event is not None


def test_e_cambiar_cantidad(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create"])
    cab = _operador(mundo, reloj_mfa, rol_id)
    wh = _almacen(mundo, mundo.company_id)
    product = _preparar_politica_y_stock(mundo, wh)
    plan = _leer_plan(mundo, cab, wh, product)
    recommended = Decimal(plan["recommended_quantity"])
    req_id = _crear_requisicion(mundo, cab, wh)

    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={"product_id": product, "quantity": "50"},
    )
    assert r.status_code == 200
    data = r.json()
    expected = (Decimal("50") - recommended).quantize(Decimal("0.000001"))
    assert data["plan"]["difference"] == str(expected)
    assert data["plan"]["accepted_recommendation"] is False


def test_f_politica_vencida(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create", "maestros:view", "maestros:edit"])
    cab = _operador(mundo, reloj_mfa, rol_id)
    wh = _almacen(mundo, mundo.company_id)
    product = _preparar_politica_y_stock(mundo, wh)
    plan = _leer_plan(mundo, cab, wh, product)
    version = plan["policy"]["version"]
    policy_id = plan["policy"]["id"]
    req_id = _crear_requisicion(mundo, cab, wh)

    r = mundo.client.patch(
        f"{API}/planning/policies/{policy_id}",
        headers=cab,
        json={"expected_version": version, "name": "Nueva política"},
    )
    assert r.status_code == 200

    r2 = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={
            "product_id": product,
            "use_recommendation": True,
            "expected_policy_version": version,
        },
    )
    assert r2.status_code == 409
    assert r2.json()["code"] == "PLANNING_POLICY_STALE"


def test_g_instantanea_inmutable(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create", "maestros:view", "maestros:edit"])
    cab = _operador(mundo, reloj_mfa, rol_id)
    wh = _almacen(mundo, mundo.company_id)
    product = _preparar_politica_y_stock(mundo, wh)
    plan = _leer_plan(mundo, cab, wh, product)
    recommended = plan["recommended_quantity"]
    version = plan["policy"]["version"]
    horizon = plan["horizon_days"]
    policy_id = plan["policy"]["id"]
    req_id = _crear_requisicion(mundo, cab, wh)

    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={
            "product_id": product,
            "use_recommendation": True,
            "expected_policy_version": version,
        },
    )
    assert r.status_code == 200

    r = mundo.client.patch(
        f"{API}/planning/policies/{policy_id}",
        headers=cab,
        json={"expected_version": version, "horizon_days": horizon + 3},
    )
    assert r.status_code == 200

    r = mundo.client.get(
        f"{API}/planning/requisitions/{req_id}",
        headers=cab,
    )
    assert r.status_code == 200
    line = r.json()["lines"][0]
    assert line["plan"]["horizon_days"] == horizon
    assert line["plan"]["policy_version"] == version
    assert line["plan"]["recommended_quantity"] == recommended


def test_h_presentacion(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create", "maestros:view", "maestros:create", "maestros:edit"])
    cab = _operador(mundo, reloj_mfa, rol_id)
    wh = _almacen(mundo, mundo.company_id)
    _desactivar_politicas(mundo, warehouse_id=wh)
    _desactivar_politicas(mundo, warehouse_id=None)

    hex_id = uuid.uuid4().hex[:6]
    r_u = mundo.client.post(
        f"{API}/maestros/unidades",
        headers=cab,
        json={
            "code": f"U{hex_id}",
            "name": "Unidad",
            "symbol": "u",
            "dimension": "CANTIDAD",
            "decimals": 0,
            "rounding_mode": "HALF_UP",
        },
    )
    assert r_u.status_code == 200
    unit_id = r_u.json()["id"]

    with mundo.factory() as db:
        product = CatalogItem(
            company_id=mundo.company_id,
            item_type="PRODUCT",
            code=f"PROD-{uuid.uuid4().hex[:8]}",
            name="Producto Presentación",
            status="ACTIVE",
            created_by=mundo.admin_id,
            base_unit_id=unit_id,
        )
        db.add(product)
        db.flush()
        product_id = product.id
        db.commit()

    r_p = mundo.client.post(
        f"{API}/maestros/productos/{product_id}/presentaciones",
        headers=cab,
        json={
            "code": f"CAJA{hex_id}",
            "name": "Caja",
            "exact_in_base": True,
            "factor_to_base": "12",
        },
    )
    assert r_p.status_code == 200
    presentation_id = r_p.json()["id"]

    req_id = _crear_requisicion(mundo, cab, wh)
    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={"product_id": product_id, "quantity": "2", "presentation_id": presentation_id},
    )
    assert r.status_code == 200
    assert r.json()["plan"]["requested_base_quantity"] == "24.000000"

    r = mundo.client.get(
        f"{API}/planning/requisitions/{req_id}",
        headers=cab,
    )
    assert r.status_code == 200
    line = r.json()["lines"][0]
    assert line["quantity"] == "24.000000"
    assert line["unit_id"] == unit_id


def test_i_no_editable(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create"])
    cab = _operador(mundo, reloj_mfa, rol_id)
    wh = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    req_id = _crear_requisicion(mundo, cab, wh)

    with mundo.factory() as db:
        from app.modules.purchasing.models import PurchaseRequisition

        req = db.get(PurchaseRequisition, req_id)
        req.status = "APPROVED"
        db.commit()

    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={"product_id": product, "quantity": "1"},
    )
    assert r.status_code == 409
    assert r.json()["code"] == "REQUISITION_NOT_EDITABLE"


def test_j_permisos(mundo, reloj_mfa):
    rol_view = _crear_rol(mundo, ["compras:view"])
    cab_view = _operador(mundo, reloj_mfa, rol_view)
    rol_create = _crear_rol(mundo, ["compras:view", "compras:create"])
    cab_create = _operador(mundo, reloj_mfa, rol_create)
    wh = _almacen(mundo, mundo.company_id)
    product = _producto(mundo)
    req_id = _crear_requisicion(mundo, cab_create, wh)

    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab_view,
        json={"product_id": product, "quantity": "1"},
    )
    assert r.status_code == 403

    r = mundo.client.get(
        f"{API}/planning/requisitions/{req_id}",
        headers=cab_view,
    )
    assert r.status_code == 200


def test_k_aislamiento(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view"])
    cab = _operador(mundo, reloj_mfa, rol_id)

    with mundo.factory() as db:
        from app.modules.organization.models import Company
        from app.modules.purchasing.models import PurchaseRequisition

        company_b = db.scalars(select(Company).where(Company.tenant_id == mundo.tenant_b_id)).first()
        req_b = PurchaseRequisition(
            company_id=company_b.id,
            code=f"REQ-{uuid.uuid4().hex[:8]}",
            status="DRAFT",
            created_by=mundo.admin_id,
        )
        db.add(req_b)
        db.flush()
        req_b_id = req_b.id
        db.commit()

    r = mundo.client.get(
        f"{API}/planning/requisitions/{req_b_id}",
        headers=cab,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "REQUISITION_NOT_FOUND"


def test_requisition_detail(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["compras:view", "compras:create"])
    cab = _operador(mundo, reloj_mfa, rol_id)
    wh = _almacen(mundo, mundo.company_id)
    req_id = _crear_requisicion(mundo, cab, wh)

    r = mundo.client.get(
        f"{API}/planning/requisitions/{req_id}",
        headers=cab,
    )
    assert r.status_code == 200
    assert r.json()["warehouse_id"] == wh
    assert r.json()["status"] == "DRAFT"
    assert r.json()["lines"] == []
