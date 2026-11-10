# ruff: noqa: E402, F811, F401, I001
import os
import uuid
from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_importaciones_seguimiento import (
    _almacen,
    _operador,
    mundo,
)

from app.core.errors import KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.organization.models import Company, Warehouse, WarehouseZone
from app.modules.planning import models as planning_models
from app.modules.planning import service as planning_service
from app.modules.purchasing.models import PurchaseRequisition
from app.modules.storage import models as storage_models

pytest_plugins = ["mfa_apoyo"]

API = "/api/v1"


@pytest.fixture(scope="module")
def rol_config(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"plan{uuid.uuid4().hex[:12]}",
            name="Planificador",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "maestros:edit",
            ],
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


@pytest.fixture(scope="module")
def rol_lectura(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"planlect{uuid.uuid4().hex[:12]}",
            name="Lectura Planning",
            company_id=None,
            permissions=["maestros:view"],
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


def _payload(overrides=None):
    data = {
        "code": f"POL-{uuid4().hex[:8]}",
        "name": "Política base",
        "demand_source": "DISPATCHED_SALES",
        "lookback_days": 10,
        "horizon_days": 5,
        "lead_time_days": 2,
        "safety_mode": "DAYS",
        "safety_value": "3",
        "rotation_metric": "DEMAND_VELOCITY",
        "status": "ACTIVE",
    }
    if overrides:
        data.update(overrides)
    return data


def _band_payload(overrides=None):
    data = {
        "code": f"BAND-{uuid4().hex[:8]}",
        "name": "Banda",
        "metric": "DEMAND_VELOCITY",
        "lower_bound": "0",
        "upper_bound": "10",
        "sort_order": 0,
        "status": "ACTIVE",
    }
    if overrides:
        data.update(overrides)
    return data


def _desactivar_politicas_empresa(mundo):
    with mundo.factory() as db:
        policies = db.scalars(
            select(planning_models.PlanningPolicy).where(
                planning_models.PlanningPolicy.company_id == mundo.company_id,
                planning_models.PlanningPolicy.warehouse_id.is_(None),
            )
        ).all()
        for policy in policies:
            policy.status = "INACTIVE"
        db.commit()


def _desactivar_bandas_empresa(mundo):
    with mundo.factory() as db:
        bands = db.scalars(
            select(planning_models.RotationBand).where(
                planning_models.RotationBand.company_id == mundo.company_id,
                planning_models.RotationBand.status == "ACTIVE",
            )
        ).all()
        for band in bands:
            band.status = "INACTIVE"
        db.commit()


def test_planning_config_a_politica_empresa(mundo, reloj_mfa, rol_config):
    _desactivar_politicas_empresa(mundo)
    cab = _operador(mundo, reloj_mfa, rol_config)
    r = mundo.client.post(f"{API}/planning/policies", json=_payload(), headers=cab)
    assert r.status_code == 200
    body = r.json()
    assert body["version"] == 1
    assert body["warehouse_id"] is None
    r = mundo.client.get(f"{API}/planning/policies", headers=cab)
    assert r.status_code == 200
    assert any(item["code"] == body["code"] for item in r.json()["items"])


def test_planning_config_b_validaciones(mundo, reloj_mfa, rol_config):
    cab = _operador(mundo, reloj_mfa, rol_config)
    casos = [
        (_payload({"lookback_days": 0}), "INVALID_LOOKBACK"),
        (_payload({"horizon_days": 0}), "INVALID_HORIZON"),
        (_payload({"lead_time_days": -1}), "INVALID_LEAD_TIME"),
        (_payload({"safety_mode": "DAYS", "safety_value": "-1"}), "INVALID_SAFETY_STOCK"),
        (_payload({"demand_source": "X"}), "INVALID_DEMAND_SOURCE"),
    ]
    for payload, code in casos:
        r = mundo.client.post(f"{API}/planning/policies", json=payload, headers=cab)
        assert r.status_code == 422, f"{payload}: {r.text}"
        assert r.json()["code"] == code


def test_planning_config_c_alcance_unico(mundo, reloj_mfa, rol_config):
    _desactivar_politicas_empresa(mundo)
    cab = _operador(mundo, reloj_mfa, rol_config)
    r1 = mundo.client.post(f"{API}/planning/policies", json=_payload(), headers=cab)
    assert r1.status_code == 200
    r2 = mundo.client.post(f"{API}/planning/policies", json=_payload(), headers=cab)
    assert r2.status_code == 409
    assert r2.json()["code"] == "PLANNING_POLICY_SCOPE_TAKEN"
    warehouse_id = _almacen(mundo, mundo.company_id)
    r3 = mundo.client.post(
        f"{API}/planning/policies",
        json=_payload({"warehouse_id": warehouse_id}),
        headers=cab,
    )
    assert r3.status_code == 200


def test_planning_config_d_version(mundo, reloj_mfa, rol_config):
    warehouse_id = _almacen(mundo, mundo.company_id)
    cab = _operador(mundo, reloj_mfa, rol_config)
    r = mundo.client.post(
        f"{API}/planning/policies",
        json=_payload({"warehouse_id": warehouse_id}),
        headers=cab,
    )
    pid = r.json()["id"]
    r2 = mundo.client.patch(
        f"{API}/planning/policies/{pid}",
        json={"expected_version": 1, "name": "Actualizada"},
        headers=cab,
    )
    assert r2.status_code == 200
    assert r2.json()["version"] == 2
    r3 = mundo.client.patch(
        f"{API}/planning/policies/{pid}",
        json={"expected_version": 1, "name": "Otra"},
        headers=cab,
    )
    assert r3.status_code == 409
    assert r3.json()["code"] == "VERSION_CONFLICT"


def test_planning_config_e_resolve_policy(mundo):
    _desactivar_politicas_empresa(mundo)
    with mundo.factory() as db:
        warehouse_a = _almacen(mundo, mundo.company_id)
        warehouse_b = _almacen(mundo, mundo.company_id)
        payload = _payload()
        payload["warehouse_id"] = warehouse_a
        payload["valid_from"] = date.today() - timedelta(days=1)
        payload["valid_to"] = date.today() + timedelta(days=1)
        planning_service.create_policy(
            db,
            company_id=mundo.company_id,
            data=dict(payload),
            actor_id=mundo.admin_id,
        )
        planning_service.create_policy(
            db,
            company_id=mundo.company_id,
            data=dict(_payload()),
            actor_id=mundo.admin_id,
        )
        db.commit()
        resolved = planning_service.resolve_policy(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_a,
            on_date=date.today(),
        )
        assert resolved is not None and resolved.warehouse_id == warehouse_a
        resolved_b = planning_service.resolve_policy(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_b,
            on_date=date.today(),
        )
        assert resolved_b is not None and resolved_b.warehouse_id is None


def test_planning_config_e_inactiva_y_vencida(mundo):
    _desactivar_politicas_empresa(mundo)
    with mundo.factory() as db:
        planning_service.create_policy(
            db,
            company_id=mundo.company_id,
            data=dict(_payload({"status": "INACTIVE"})),
            actor_id=mundo.admin_id,
        )
        planning_service.create_policy(
            db,
            company_id=mundo.company_id,
            data=dict(_payload({"valid_to": date.today() - timedelta(days=1)})),
            actor_id=mundo.admin_id,
        )
        resolved = planning_service.resolve_policy(
            db,
            company_id=mundo.company_id,
            warehouse_id=None,
            on_date=date.today(),
        )
        assert resolved is None


def test_planning_config_e_vigencia_invalida(mundo):
    _desactivar_politicas_empresa(mundo)
    with mundo.factory() as db:
        with pytest.raises(KontrolError) as exc_info:
            planning_service.create_policy(
                db,
                company_id=mundo.company_id,
                data=dict(_payload({"valid_to": "no-es-fecha"})),
                actor_id=mundo.admin_id,
            )
        assert exc_info.value.code == "INVALID_VALIDITY"


def test_planning_config_f_bandas(mundo, reloj_mfa, rol_config):
    _desactivar_bandas_empresa(mundo)
    cab = _operador(mundo, reloj_mfa, rol_config)
    codigo_rapida = f"RAP-{uuid4().hex[:6]}"
    r1 = mundo.client.post(
        f"{API}/planning/rotation-bands",
        json=_band_payload({"code": codigo_rapida, "name": "Rapida", "lower_bound": "10", "upper_bound": None}),
        headers=cab,
    )
    assert r1.status_code == 200
    codigo_lenta = f"LEN-{uuid4().hex[:6]}"
    r2 = mundo.client.post(
        f"{API}/planning/rotation-bands",
        json=_band_payload({"code": codigo_lenta, "name": "Lenta", "lower_bound": "0", "upper_bound": "10"}),
        headers=cab,
    )
    assert r2.status_code == 200
    r3 = mundo.client.post(
        f"{API}/planning/rotation-bands",
        json=_band_payload({"lower_bound": "5", "upper_bound": "20"}),
        headers=cab,
    )
    assert r3.status_code == 409
    assert r3.json()["code"] == "ROTATION_BAND_OVERLAP"
    r4 = mundo.client.post(
        f"{API}/planning/rotation-bands",
        json=_band_payload({"lower_bound": "10", "upper_bound": "5"}),
        headers=cab,
    )
    assert r4.status_code == 422
    assert r4.json()["code"] == "INVALID_BAND_RANGE"
    with mundo.factory() as db:
        rapida = planning_service.band_for(
            db,
            company_id=mundo.company_id,
            metric="DEMAND_VELOCITY",
            value=Decimal("12"),
        )
        assert rapida is not None and rapida.name == "Rapida"
        assert rapida.code == codigo_rapida
        lenta = planning_service.band_for(
            db,
            company_id=mundo.company_id,
            metric="DEMAND_VELOCITY",
            value=Decimal("3"),
        )
        assert lenta is not None and lenta.name == "Lenta"
        assert lenta.code == codigo_lenta
        assert planning_service.band_for(
            db,
            company_id=mundo.company_id,
            metric="DEMAND_VELOCITY",
            value=None,
        ) is None


def test_planning_config_g_permisos(mundo, reloj_mfa, rol_config, rol_lectura):
    cab_lectura = _operador(mundo, reloj_mfa, rol_lectura)
    r1 = mundo.client.post(f"{API}/planning/policies", json=_payload(), headers=cab_lectura)
    assert r1.status_code == 403
    r2 = mundo.client.post(f"{API}/planning/rotation-bands", json=_band_payload(), headers=cab_lectura)
    assert r2.status_code == 403
    r3 = mundo.client.get(f"{API}/planning/policies", headers=cab_lectura)
    assert r3.status_code == 200
    r4 = mundo.client.get(f"{API}/planning/rotation-bands", headers=cab_lectura)
    assert r4.status_code == 200


def test_planning_config_h_aislamiento(mundo, reloj_mfa, rol_config):
    _desactivar_politicas_empresa(mundo)
    cab = _operador(mundo, reloj_mfa, rol_config)
    with mundo.factory() as db:
        company_b = db.scalars(select(Company).where(Company.tenant_id == mundo.tenant_b_id)).first()
        warehouse_b = Warehouse(
            company_id=company_b.id,
            code=f"WHB-{uuid4().hex[:6]}",
            name="Warehouse B",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(warehouse_b)
        db.flush()
        r = mundo.client.post(
            f"{API}/planning/policies",
            json=_payload({"warehouse_id": warehouse_b.id}),
            headers=cab,
        )
        assert r.status_code == 404
        assert r.json()["code"] == "WAREHOUSE_NOT_FOUND"
        planning_service.create_policy(
            db,
            company_id=company_b.id,
            data=dict(_payload()),
            actor_id=mundo.admin_id,
        )
        db.commit()
        policy_b_code = db.scalars(
            select(planning_models.PlanningPolicy).where(planning_models.PlanningPolicy.company_id == company_b.id)
        ).first().code
    r = mundo.client.get(f"{API}/planning/policies", headers=cab)
    assert r.status_code == 200
    assert all(item["code"] != policy_b_code for item in r.json()["items"])


def test_planning_config_i_auditoria(mundo, reloj_mfa, rol_config):
    _desactivar_bandas_empresa(mundo)
    warehouse_id = _almacen(mundo, mundo.company_id)
    cab = _operador(mundo, reloj_mfa, rol_config)
    r = mundo.client.post(
        f"{API}/planning/policies",
        json=_payload({"warehouse_id": warehouse_id}),
        headers=cab,
    )
    pid = r.json()["id"]
    mundo.client.patch(
        f"{API}/planning/policies/{pid}",
        json={"expected_version": 1, "name": "Auditada"},
        headers=cab,
    )
    r_band = mundo.client.post(f"{API}/planning/rotation-bands", json=_band_payload(), headers=cab)
    assert r_band.status_code == 200
    with mundo.factory() as db:
        events = db.scalars(
            select(AuditEvent).where(AuditEvent.company_id == mundo.company_id)
        ).all()
        actions = {e.action for e in events}
        assert "PLANNING_POLICY_CREATED" in actions
        assert "PLANNING_POLICY_UPDATED" in actions
        assert "ROTATION_BAND_CREATED" in actions


@pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Solo aplica en PostgreSQL",
)
def test_planning_config_j_esquema(mundo):
    _desactivar_bandas_empresa(mundo)
    with mundo.factory() as db:
        warehouse_id = _almacen(mundo, mundo.company_id)
        band = planning_service.create_band(
            db,
            company_id=mundo.company_id,
            data=dict(_band_payload({"code": f"ESQ-{uuid4().hex[:6]}", "lower_bound": "0", "upper_bound": None})),
            actor_id=mundo.admin_id,
        )
        db.flush()
        requisition = PurchaseRequisition(
            company_id=mundo.company_id,
            requester_id=mundo.admin_id,
            warehouse_id=warehouse_id,
            status="DRAFT",
            code=f"REQ-{uuid4().hex[:8]}",
            created_by=mundo.admin_id,
        )
        db.add(requisition)
        db.flush()
        zone = WarehouseZone(
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            code=f"ZONA-{uuid4().hex[:6]}",
            name="Zona",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(zone)
        db.flush()
        rule = storage_models.StorageRule(
            company_id=mundo.company_id,
            code=f"RULE-{uuid4().hex[:6]}",
            name="Regla banda",
            priority=1,
            status="ACTIVE",
            warehouse_id=warehouse_id,
            target_zone_id=zone.id,
            label_policy="NOT_REQUIRED",
            rotation_band_id=band.id,
            created_by=mundo.admin_id,
        )
        db.add(rule)
        db.commit()
        saved_req = db.get(PurchaseRequisition, requisition.id)
        assert saved_req is not None and saved_req.warehouse_id == warehouse_id
        saved_rule = db.scalars(
            select(storage_models.StorageRule).where(storage_models.StorageRule.id == rule.id)
        ).first()
        assert saved_rule is not None and saved_rule.rotation_band_id == band.id
