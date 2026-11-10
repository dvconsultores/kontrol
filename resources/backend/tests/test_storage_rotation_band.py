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

from app.core.errors import KontrolError
from app.modules.inventory import models as inventory_models
from app.modules.inventory import service as inventory_service
from app.modules.master_data.models import CatalogItem
from app.modules.organization.models import WarehouseZone
from app.modules.planning import models as planning_models
from app.modules.planning import service as planning_service
from app.modules.planning.engine import compute_plan
from app.modules.storage import service as storage_service
from app.shared.clock import hoy_de_negocio, inicio_del_dia_de_negocio

pytest_plugins = ["mfa_apoyo"]


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


def _montaje(mundo):
    wh = _almacen(mundo, mundo.company_id)
    _desactivar_politicas(mundo, wh)
    _desactivar_bandas(mundo)
    _politica(mundo, wh)

    sufijo = uuid.uuid4().hex[:8]
    db = mundo.factory()
    try:
        lenta = planning_service.create_band(
            db,
            company_id=mundo.company_id,
            data={
                "code": f"LENTA-{sufijo}",
                "name": "Lenta",
                "metric": "DEMAND_VELOCITY",
                "lower_bound": Decimal("0"),
                "upper_bound": Decimal("2"),
                "sort_order": 0,
                "status": "ACTIVE",
            },
            actor_id=mundo.admin_id,
        )
        rapida = planning_service.create_band(
            db,
            company_id=mundo.company_id,
            data={
                "code": f"RAPIDA-{sufijo}",
                "name": "Rápida",
                "metric": "DEMAND_VELOCITY",
                "lower_bound": Decimal("2"),
                "upper_bound": None,
                "sort_order": 1,
                "status": "ACTIVE",
            },
            actor_id=mundo.admin_id,
        )
        zona = WarehouseZone(
            company_id=mundo.company_id,
            warehouse_id=wh,
            code=f"ZR-{sufijo}",
            name="Zona rápida",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(zona)
        db.flush()
        db.refresh(zona)
        db.refresh(lenta)
        db.refresh(rapida)
        db.commit()

        regla = storage_service.create_rule(
            db,
            company_id=mundo.company_id,
            data={
                "code": f"RR-{sufijo}",
                "name": "Regla rotación",
                "priority": 1,
                "status": "ACTIVE",
                "warehouse_id": wh,
                "target_zone_id": zona.id,
                "label_policy": "NOT_REQUIRED",
                "rotation_band_id": rapida.id,
            },
            actor_id=mundo.admin_id,
        )
        db.commit()
        return {
            "wh": wh,
            "lenta_id": lenta.id,
            "rapida_id": rapida.id,
            "lenta_code": lenta.code,
            "rapida_code": rapida.code,
            "zona_id": zona.id,
            "regla_id": regla.id,
        }
    finally:
        db.close()


def test_rotation_band_rapida(mundo):
    montaje = _montaje(mundo)
    product_id = _producto(mundo)
    _entrada(mundo, montaje["wh"], product_id, 100, 20)
    _despacho(mundo, montaje["wh"], product_id, 20, 5)
    _despacho(mundo, montaje["wh"], product_id, 10, 2)

    db = mundo.factory()
    try:
        result = storage_service.evaluate(
            db,
            company_id=mundo.company_id,
            warehouse_id=montaje["wh"],
            item_id=product_id,
        )
        assert result["result"] == "CLASSIFIED"
        assert result["target_zone_id"] == montaje["zona_id"]
        assert any(r.startswith("Banda de rotación:") for r in result["reasons"])
        assert result["inputs"]["rotation_band"] == montaje["rapida_code"]
    finally:
        db.close()


def test_rotation_band_lenta_sin_regla(mundo):
    montaje = _montaje(mundo)
    product_id = _producto(mundo)
    _entrada(mundo, montaje["wh"], product_id, 100, 5)
    _despacho(mundo, montaje["wh"], product_id, 5, 2)

    db = mundo.factory()
    try:
        result = storage_service.evaluate(
            db,
            company_id=mundo.company_id,
            warehouse_id=montaje["wh"],
            item_id=product_id,
        )
        assert result["result"] == "NO_RULE"
    finally:
        db.close()


def test_rotation_band_sin_politica(mundo):
    montaje = _montaje(mundo)
    _desactivar_politicas(mundo, montaje["wh"])
    product_id = _producto(mundo)
    _entrada(mundo, montaje["wh"], product_id, 100, 5)

    db = mundo.factory()
    try:
        result = storage_service.evaluate(
            db,
            company_id=mundo.company_id,
            warehouse_id=montaje["wh"],
            item_id=product_id,
        )
        assert result["result"] == "NO_RULE"
        assert "Banda de rotación" in result["missing_criteria"]
    finally:
        db.close()


def test_rotation_band_classify_input(mundo):
    montaje = _montaje(mundo)
    product_id = _producto(mundo)
    _entrada(mundo, montaje["wh"], product_id, 100, 20)
    _despacho(mundo, montaje["wh"], product_id, 20, 5)
    _despacho(mundo, montaje["wh"], product_id, 10, 2)

    db = mundo.factory()
    try:
        classification = storage_service.classify(
            db,
            company_id=mundo.company_id,
            warehouse_id=montaje["wh"],
            item_id=product_id,
            state="DISPONIBLE",
            actor_id=mundo.admin_id,
        )
        db.commit()
        assert classification.input_rotation_band == montaje["rapida_code"]
    finally:
        db.close()


def test_rotation_band_otra_empresa(mundo):
    montaje = _montaje(mundo)

    with mundo.factory() as db:
        from app.modules.organization.models import Company, Warehouse

        company_b = db.scalars(select(Company).where(Company.tenant_id == mundo.tenant_b_id)).first()
        db.commit()

        banda_b = planning_models.RotationBand(
            company_id=company_b.id,
            code=f"BANDA-B-{uuid.uuid4().hex[:6]}",
            name="Banda B",
            metric="DEMAND_VELOCITY",
            lower_bound=Decimal("0"),
            upper_bound=None,
            sort_order=0,
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(banda_b)
        db.flush()
        db.refresh(banda_b)
        db.commit()
        banda_b_id = banda_b.id

    db = mundo.factory()
    try:
        with pytest.raises(KontrolError) as exc_info:
            storage_service.create_rule(
                db,
                company_id=mundo.company_id,
                data={
                    "code": f"RRX-{uuid.uuid4().hex[:8]}",
                    "name": "Regla banda ajena",
                    "priority": 1,
                    "status": "ACTIVE",
                    "warehouse_id": montaje["wh"],
                    "target_zone_id": montaje["zona_id"],
                    "label_policy": "NOT_REQUIRED",
                    "rotation_band_id": banda_b_id,
                },
                actor_id=mundo.admin_id,
            )
        assert exc_info.value.code == "ROTATION_BAND_NOT_FOUND"
    finally:
        db.close()


def test_rule_dict_rotation_band_code(mundo):
    montaje = _montaje(mundo)
    db = mundo.factory()
    try:
        from app.modules.storage import models as storage_models

        regla = db.get(storage_models.StorageRule, montaje["regla_id"])
        assert storage_service.rule_dict(db, regla)["rotation_band_code"] == montaje["rapida_code"]
    finally:
        db.close()
