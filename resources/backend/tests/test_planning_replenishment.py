# ruff: noqa: E402, F811, F401, I001
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from test_importaciones_seguimiento import (
    _almacen as _almacen_base,
    _operador,
    mundo,
)


def _almacen(mundo, company_id=None):
    return _almacen_base(mundo, company_id or mundo.company_id)

from app.modules.audit.models import AuditEvent
from app.modules.inventory import models as inventory_models
from app.modules.inventory import service as inventory_service
from app.modules.master_data.models import CatalogItem
from app.modules.notifications.models import Alert
from app.modules.organization.models import Company, Warehouse
from app.modules.planning import models as planning_models
from app.modules.planning import service as planning_service
from app.modules.planning.engine import compute_plan
from app.modules.planning.replenishment import evaluate_replenishment_needs
from app.modules.purchasing.models import PurchaseRequisition
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


def _salida(mundo, warehouse_id, product_id, quantity, day):
    db = mundo.factory()
    try:
        inventory_service.record_movement(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            movement_type_id=inventory_service._get_movement_type_by_code(
                db, mundo.company_id, "SALIDA_DESPACHO"
            ).id,
            quantity=-quantity,
            occurred_at=_dia(day),
            actor=mundo.admin_id,
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


def _necesidades_activas(mundo, warehouse_id, product_id):
    db = mundo.factory()
    try:
        needs = list(
            db.scalars(
                select(planning_models.ReplenishmentNeed).where(
                    planning_models.ReplenishmentNeed.company_id == mundo.company_id,
                    planning_models.ReplenishmentNeed.warehouse_id == warehouse_id,
                    planning_models.ReplenishmentNeed.product_id == product_id,
                    planning_models.ReplenishmentNeed.status == "ACTIVE",
                )
            ).all()
        )
        return needs
    finally:
        db.close()


def test_a_deteccion_apagada_no_genera(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": False, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    assert _necesidades_activas(mundo, wh, prod) == []
    db = mundo.factory()
    try:
        alerts = list(db.scalars(select(Alert).where(Alert.company_id == mundo.company_id)).all())
        assert alerts == []
    finally:
        db.close()


def test_b_disponible_mayor_no_genera(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 100, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    assert _necesidades_activas(mundo, wh, prod) == []


def test_c_condicion_genera_necesidad_y_alerta(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    needs = _necesidades_activas(mundo, wh, prod)
    assert len(needs) == 1
    need = needs[0]
    assert need.status == "ACTIVE"
    assert need.trigger_method == "AVAILABLE_AT_OR_BELOW_REORDER_POINT_V1"
    assert Decimal(str(need.trigger_available)) == Decimal("2")
    assert Decimal(str(need.trigger_reorder_point)) == Decimal("3")
    assert Decimal(str(need.trigger_recommended_quantity)) == Decimal("3")
    db = mundo.factory()
    try:
        policy = db.scalars(
            select(planning_models.PlanningPolicy).where(
                planning_models.PlanningPolicy.company_id == mundo.company_id,
                planning_models.PlanningPolicy.warehouse_id == wh,
                planning_models.PlanningPolicy.status == "ACTIVE",
            )
        ).first()
        assert policy is not None
        assert need.trigger_policy_version == policy.version
        alert = db.scalars(select(Alert).where(Alert.id == need.alert_id)).first()
        assert alert is not None
        assert alert.status == "ACTIVE"
        assert alert.dedupe_key == f"replenishment-need:{need.id}"
        assert alert.source_type == "ReplenishmentNeed"
        assert alert.route_key == "replenishment_need"
        audit = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "REPLENISHMENT_NEED_DETECTED",
                AuditEvent.entity_id == str(need.id),
            )
        ).first()
        assert audit is not None
    finally:
        db.close()


def test_d_segunda_evaluacion_no_duplica(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    needs = _necesidades_activas(mundo, wh, prod)
    assert len(needs) == 1
    first = needs[0]
    first_last = first.last_evaluated_at
    first_trigger = first.trigger_available
    db = mundo.factory()
    try:
        first_alert_id = db.scalars(select(Alert.id).where(Alert.id == first.alert_id)).first()
        assert first_alert_id is not None
    finally:
        db.close()
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC) + timedelta(seconds=1))
    needs = _necesidades_activas(mundo, wh, prod)
    assert len(needs) == 1
    second = needs[0]
    assert second.id == first.id
    assert second.last_evaluated_at > first_last
    assert second.trigger_available == first_trigger
    db = mundo.factory()
    try:
        alert_count = len(list(db.scalars(select(Alert).where(Alert.source_id == str(second.id))).all()))
        assert alert_count == 1
    finally:
        db.close()


def test_e_saldo_se_recupera_resuelve(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    need = _necesidades_activas(mundo, wh, prod)[0]
    _entrada(mundo, wh, prod, 50, 1)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    assert _necesidades_activas(mundo, wh, prod) == []
    db = mundo.factory()
    try:
        resolved = db.get(planning_models.ReplenishmentNeed, need.id)
        assert resolved.status == "RESOLVED"
        assert resolved.resolution_reason == "CONDITION_CLEARED"
        assert resolved.resolved_at is not None
        alert = db.get(Alert, resolved.alert_id)
        assert alert is not None
        assert alert.status == "RESOLVED"
        assert alert.resolved_at is not None
        audit = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "REPLENISHMENT_NEED_RESOLVED",
                AuditEvent.entity_id == str(need.id),
            )
        ).first()
        assert audit is not None
    finally:
        db.close()


def test_f_reaparicion_crea_nueva_necesidad(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    old_need = _necesidades_activas(mundo, wh, prod)[0]
    _entrada(mundo, wh, prod, 50, 1)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    _salida(mundo, wh, prod, 52, 0)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    new_needs = _necesidades_activas(mundo, wh, prod)
    assert len(new_needs) == 1
    assert new_needs[0].id != old_need.id
    db = mundo.factory()
    try:
        old = db.get(planning_models.ReplenishmentNeed, old_need.id)
        assert old.status == "RESOLVED"
        alerts = list(
            db.scalars(
                select(Alert).where(
                    Alert.source_type == "ReplenishmentNeed",
                    Alert.source_id.in_([str(old_need.id), str(new_needs[0].id)]),
                )
            ).all()
        )
        assert len(alerts) == 2
        dedupes = {a.dedupe_key for a in alerts}
        assert f"replenishment-need:{old_need.id}" in dedupes
        assert f"replenishment-need:{new_needs[0].id}" in dedupes
    finally:
        db.close()


def test_g_sin_politica_ni_historia_no_genera(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": False, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    assert _necesidades_activas(mundo, wh, prod) == []


def test_h_apagar_deteccion_resuelve_por_politica(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    db = mundo.factory()
    try:
        policy_data = {
            "code": f"POL-{uuid.uuid4().hex[:8]}",
            "name": "Política motor",
            "warehouse_id": wh,
            "demand_source": "INVENTORY_ISSUES",
            "lookback_days": 10,
            "horizon_days": 5,
            "lead_time_days": 3,
            "safety_mode": "DAYS",
            "safety_value": "2",
            "rotation_metric": "DEMAND_VELOCITY",
            "status": "ACTIVE",
            "auto_replenishment_enabled": True,
        }
        planning_service.create_policy(db, company_id=mundo.company_id, data=policy_data, actor_id=mundo.admin_id)
        db.commit()
    finally:
        db.close()
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    need = _necesidades_activas(mundo, wh, prod)[0]
    db = mundo.factory()
    try:
        policy = db.scalars(
            select(planning_models.PlanningPolicy).where(
                planning_models.PlanningPolicy.company_id == mundo.company_id,
                planning_models.PlanningPolicy.warehouse_id == wh,
                planning_models.PlanningPolicy.status == "ACTIVE",
            )
        ).first()
        assert policy is not None
        planning_service.update_policy(
            db,
            company_id=mundo.company_id,
            policy_id=policy.id,
            expected_version=policy.version,
            data={"auto_replenishment_enabled": False},
            actor_id=mundo.admin_id,
        )
        db.commit()
    finally:
        db.close()
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    assert _necesidades_activas(mundo, wh, prod) == []
    db = mundo.factory()
    try:
        resolved = db.get(planning_models.ReplenishmentNeed, need.id)
        assert resolved.status == "RESOLVED"
        assert resolved.resolution_reason == "POLICY_DISABLED"
        alert = db.get(Alert, resolved.alert_id)
        assert alert.status == "RESOLVED"
    finally:
        db.close()


def test_i_producto_inactivo_resuelve(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    need = _necesidades_activas(mundo, wh, prod)[0]
    db = mundo.factory()
    try:
        product = db.get(CatalogItem, prod)
        product.status = "INACTIVE"
        db.commit()
    finally:
        db.close()
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    assert _necesidades_activas(mundo, wh, prod) == []
    db = mundo.factory()
    try:
        resolved = db.get(planning_models.ReplenishmentNeed, need.id)
        assert resolved.status == "RESOLVED"
        assert resolved.resolution_reason == "PRODUCT_INACTIVE"
    finally:
        db.close()


def test_j_api_lista_y_detalle(mundo, reloj_mfa):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    need = _necesidades_activas(mundo, wh, prod)[0]

    rol = _crear_rol(mundo, ["compras:view"])
    cab = _operador(mundo, reloj_mfa, rol)
    r = mundo.client.get(f"{API}/planning/replenishment-needs", headers=cab)
    assert r.status_code == 200
    body = r.json()
    assert body["total"] >= 1
    assert any(item["id"] == str(need.id) for item in body["items"])

    r = mundo.client.get(
        f"{API}/planning/replenishment-needs?status=ACTIVE&warehouse_id={wh}",
        headers=cab,
    )
    assert r.status_code == 200
    assert any(item["id"] == str(need.id) for item in r.json()["items"])

    r = mundo.client.get(f"{API}/planning/replenishment-needs/{need.id}", headers=cab)
    assert r.status_code == 200
    detalle = r.json()
    assert detalle["trigger"]["available"] == "2.000000"
    assert detalle["current"]["reorder_point"] == "3.000000"

    rol_sin = _crear_rol(mundo, ["maestros:view"])
    cab_sin = _operador(mundo, reloj_mfa, rol_sin)
    r = mundo.client.get(f"{API}/planning/replenishment-needs", headers=cab_sin)
    assert r.status_code == 403

    db = mundo.factory()
    try:
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
        prod_b = CatalogItem(
            company_id=company_b.id,
            item_type="PRODUCT",
            code=f"PRODB-{uuid.uuid4().hex[:8]}",
            name="Producto B",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(prod_b)
        db.flush()
        from app.modules.planning.models import PlanningPolicy

        policy_b = PlanningPolicy(
            company_id=company_b.id,
            warehouse_id=wh_b.id,
            code=f"POLB-{uuid.uuid4().hex[:8]}",
            name="Policy B",
            demand_source="INVENTORY_ISSUES",
            lookback_days=10,
            horizon_days=5,
            lead_time_days=3,
            safety_mode="NONE",
            safety_value=Decimal("0"),
            rotation_metric="DEMAND_VELOCITY",
            status="ACTIVE",
            auto_replenishment_enabled=True,
            version=1,
            created_by=mundo.admin_id,
        )
        db.add(policy_b)
        db.flush()
        need_b = planning_models.ReplenishmentNeed(
            company_id=company_b.id,
            warehouse_id=wh_b.id,
            product_id=prod_b.id,
            status="ACTIVE",
            trigger_method="AVAILABLE_AT_OR_BELOW_REORDER_POINT_V1",
            triggered_at=datetime.now(UTC),
            last_evaluated_at=datetime.now(UTC),
            trigger_policy_id=policy_b.id,
            trigger_policy_version=1,
            trigger_policy_code=policy_b.code,
            trigger_available=Decimal("2"),
            trigger_on_hand=Decimal("2"),
            trigger_reserved=Decimal("0"),
            trigger_reorder_point=Decimal("3"),
            trigger_projected_demand=Decimal("5"),
            trigger_avg_daily_demand=Decimal("1"),
            trigger_safety_stock=Decimal("0"),
            trigger_recommended_quantity=Decimal("3"),
            trigger_calculated_at=datetime.now(UTC),
            trigger_snapshot={},
        )
        db.add(need_b)
        db.commit()
        need_b_id = str(need_b.id)
    finally:
        db.close()

    r = mundo.client.get(f"{API}/planning/replenishment-needs/{need_b_id}", headers=cab)
    assert r.status_code == 404
    assert r.json()["code"] == "REPLENISHMENT_NEED_NOT_FOUND"


def test_k_trazabilidad_linea_planificada(mundo, reloj_mfa):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    need = _necesidades_activas(mundo, wh, prod)[0]

    rol = _crear_rol(mundo, ["compras:view", "compras:create"])
    cab = _operador(mundo, reloj_mfa, rol)
    req_id = _crear_requisicion(mundo, cab, warehouse_id=wh)
    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id}/lines",
        headers=cab,
        json={
            "product_id": prod,
            "use_recommendation": True,
            "replenishment_need_id": str(need.id),
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["plan"]["replenishment_need_id"] == str(need.id)

    db = mundo.factory()
    try:
        line_plan = db.scalars(
            select(planning_models.RequisitionLinePlan).where(
                planning_models.RequisitionLinePlan.replenishment_need_id == need.id
            )
        ).first()
        assert line_plan is not None
        current_need = db.get(planning_models.ReplenishmentNeed, need.id)
        assert current_need.status == "ACTIVE"
    finally:
        db.close()

    r = mundo.client.get(f"{API}/planning/replenishment-needs/{need.id}", headers=cab)
    assert r.status_code == 200
    detalle = r.json()
    assert len(detalle["requisitions"]) >= 1
    assert any(req["requisition_id"] == req_id for req in detalle["requisitions"])

    prod2 = _producto(mundo)
    req_id2 = _crear_requisicion(mundo, cab, warehouse_id=wh)
    r = mundo.client.post(
        f"{API}/planning/requisitions/{req_id2}/lines",
        headers=cab,
        json={
            "product_id": prod2,
            "use_recommendation": True,
            "replenishment_need_id": str(need.id),
        },
    )
    assert r.status_code == 422
    assert r.json()["code"] == "REPLENISHMENT_NEED_MISMATCH"


def test_l_visibilidad_alerta(mundo, reloj_mfa):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))
    need = _necesidades_activas(mundo, wh, prod)[0]

    rol = _crear_rol(mundo, ["alertas:view", "compras:view"])
    cab = _operador(mundo, reloj_mfa, rol)
    r = mundo.client.get(f"{API}/alerts?status=ACTIVE", headers=cab)
    assert r.status_code == 200
    alert_ids = [a["id"] for a in r.json()["items"]]
    assert need.alert_id in alert_ids

    rol_solo = _crear_rol(mundo, ["alertas:view"])
    cab_solo = _operador(mundo, reloj_mfa, rol_solo)
    r = mundo.client.get(f"{API}/alerts?status=ACTIVE", headers=cab_solo)
    assert r.status_code == 200
    alert_ids = [a["id"] for a in r.json()["items"]]
    assert need.alert_id not in alert_ids


def test_m_tope_salta_candidatos(mundo):
    wh = _almacen(mundo)
    prod1 = _producto(mundo)
    prod2 = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    for prod in (prod1, prod2):
        _entrada(mundo, wh, prod, 12, 8)
        _salida(mundo, wh, prod, 10, 2)
    result = evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC), limit=1)
    assert result.processed >= 1
    assert result.skipped >= 1
    evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC), limit=100)
    assert len(_necesidades_activas(mundo, wh, prod1)) == 1
    assert len(_necesidades_activas(mundo, wh, prod2)) == 1


def test_n_registro_manejador():
    from app.modules.scheduler.registry import manejadores

    matches = [m for m in manejadores() if m.code == "planning_replenishment_detection"]
    assert len(matches) == 1
    assert matches[0].owner_spec == "015"
    assert matches[0].catch_up == "OWNER_IDEMPOTENT"


@pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Concurrencia solo en PostgreSQL",
)
def test_o_concurrencia_no_duplica(mundo):
    wh = _almacen(mundo)
    prod = _producto(mundo)
    _politica(mundo, wh, {"auto_replenishment_enabled": True, "safety_mode": "NONE", "safety_value": "0", "demand_source": "INVENTORY_ISSUES"})
    _entrada(mundo, wh, prod, 12, 8)
    _salida(mundo, wh, prod, 10, 2)

    def run_eval():
        evaluate_replenishment_needs(mundo.factory, now=datetime.now(UTC))

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(run_eval) for _ in range(2)]
        for future in futures:
            future.result()

    needs = _necesidades_activas(mundo, wh, prod)
    assert len(needs) == 1
    db = mundo.factory()
    try:
        alert_count = len(
            list(
                db.scalars(
                    select(Alert).where(
                        Alert.company_id == mundo.company_id,
                        Alert.source_type == "ReplenishmentNeed",
                        Alert.source_id == str(needs[0].id),
                    )
                ).all()
            )
        )
        assert alert_count == 1
    finally:
        db.close()
