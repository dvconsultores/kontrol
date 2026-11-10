# ruff: noqa: E402, F811, F401, I001
import concurrent.futures
import os
import re
import uuid
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from test_importaciones_seguimiento import (
    _almacen,
    _operador,
    mundo,
    rol_completo,
    rol_solo_lectura,
)

from app.core.errors import ConflictError, KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.imports.models import ImportFile
from app.modules.master_data.models import CatalogItem, Party, TaxonomyNode, UnitConversion, UnitOfMeasure
from app.modules.organization.models import Company, Warehouse, WarehouseZone, ZoneType
from app.modules.storage import service as storage_service
from app.modules.storage import models as storage_models

pytest_plugins = ["mfa_apoyo"]

API = "/api/v1"


@pytest.fixture(scope="module")
def rol_almacen(mundo):
    from app.modules.identity_access import service as identity_service

    db = mundo.factory()
    try:
        rol = identity_service.create_role(
            db,
            tenant_id=mundo.tenant_id,
            code=f"alm{uuid.uuid4().hex[:12]}",
            name="Almacenista Storage",
            company_id=None,
            permissions=[
                "maestros:view",
                "maestros:create",
                "maestros:edit",
                "organization:view",
                "organization:edit",
                "inventario:view",
                "inventario:create",
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
            code=f"lect{uuid.uuid4().hex[:12]}",
            name="Lectura Storage",
            company_id=None,
            permissions=["maestros:view", "inventario:view"],
            actor=mundo.admin_id,
        )
        db.commit()
        return rol["id"]
    finally:
        db.close()


def _mundo_almacen(mundo) -> dict:
    suffix = uuid4().hex[:6]
    with mundo.factory() as db:
        warehouse_id = _almacen(mundo, mundo.company_id)
        zone_type_1 = ZoneType(
            company_id=mundo.company_id,
            code=f"TIPO1-{suffix}",
            name="Tipo Uno",
            created_by=mundo.admin_id,
            status="ACTIVE",
        )
        zone_type_2 = ZoneType(
            company_id=mundo.company_id,
            code=f"TIPO2-{suffix}",
            name="Tipo Dos",
            created_by=mundo.admin_id,
            status="ACTIVE",
        )
        zone_type_3 = ZoneType(
            company_id=mundo.company_id,
            code=f"TIPO3-{suffix}",
            name="Tipo Tres",
            created_by=mundo.admin_id,
            status="ACTIVE",
        )
        db.add_all([zone_type_1, zone_type_2, zone_type_3])
        db.flush()
        zone_1 = WarehouseZone(
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            zone_type_id=zone_type_1.id,
            code=f"Z1-{suffix}",
            name="Zona Uno",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        zone_2 = WarehouseZone(
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            zone_type_id=zone_type_2.id,
            code=f"Z2-{suffix}",
            name="Zona Dos",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add_all([zone_1, zone_2])
        db.flush()
        root = TaxonomyNode(
            company_id=mundo.company_id,
            code=f"FAMILIA-{suffix}",
            name="Familia",
            level="RUBRO",
            applies_to=["PRODUCT"],
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(root)
        db.flush()
        child = TaxonomyNode(
            company_id=mundo.company_id,
            code=f"CATEGORIA-{suffix}",
            name="Categoría",
            level="CATEGORIA",
            applies_to=["PRODUCT"],
            parent_id=root.id,
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(child)
        db.flush()
        product = CatalogItem(
            company_id=mundo.company_id,
            item_type="PRODUCT",
            category_id=child.id,
            code=f"PROD-{uuid4().hex[:8]}",
            name="Producto Storage",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(product)
        db.flush()
        kg = UnitOfMeasure(
            code=f"KG-{uuid4().hex[:6]}",
            name="Kilogramo",
            dimension="MASA",
            symbol="kg",
            decimals=3,
            company_id=None,
            created_by=mundo.admin_id,
            status="ACTIVE",
        )
        g = UnitOfMeasure(
            code=f"G-{uuid4().hex[:6]}",
            name="Gramo",
            dimension="MASA",
            symbol="g",
            decimals=0,
            company_id=None,
            created_by=mundo.admin_id,
            status="ACTIVE",
        )
        litro = UnitOfMeasure(
            code=f"L-{uuid4().hex[:6]}",
            name="Litro",
            dimension="VOLUMEN",
            symbol="L",
            decimals=3,
            company_id=None,
            created_by=mundo.admin_id,
            status="ACTIVE",
        )
        db.add_all([kg, g, litro])
        db.flush()
        conv = UnitConversion(
            from_unit_id=g.id,
            to_unit_id=kg.id,
            factor=Decimal("0.001"),
            rounding=4,
            validity="ACTIVE",
        )
        db.add(conv)
        db.commit()
        return {
            "warehouse_id": str(warehouse_id),
            "zone_type_1": str(zone_type_1.id),
            "zone_type_2": str(zone_type_2.id),
            "zone_type_3": str(zone_type_3.id),
            "zone_1": str(zone_1.id),
            "zone_2": str(zone_2.id),
            "root": str(root.id),
            "child": str(child.id),
            "product": str(product.id),
            "kg": str(kg.id),
            "g": str(g.id),
            "l": str(litro.id),
        }


@pytest.fixture
def ids(mundo):
    return _mundo_almacen(mundo)


def test_regla_por_familia_clasifica(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.post(
        f"{API}/storage/conditions",
        json={"code": "REF", "name": "Refrigerado"},
        headers=cab,
    )
    assert r.status_code == 200, r.text
    condition_id = r.json()["id"]
    r = mundo.client.put(
        f"{API}/storage/profiles/{ids['product']}",
        json={
            "expected_version": None,
            "weight_value": "10",
            "weight_unit_id": ids["kg"],
            "condition_ids": [condition_id],
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "FAMILIA-REF",
            "name": "Familia Refrigerada",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "condition_id": condition_id,
            "target_zone_id": ids["zone_1"],
            "label_policy": "REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    rule_code = r.json()["code"]
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={ids['warehouse_id']}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["result"] == "CLASSIFIED"
    assert data["rule"]["code"] == rule_code
    assert data["zone_ids"] == [ids["zone_1"]]
    assert data["label_required"] is True
    assert data["reasons"]
    for reason in data["reasons"]:
        assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", reason)
    assert "Zona Uno" in data["target_label"]


def test_peso_normalizado(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.put(
        f"{API}/storage/profiles/{ids['product']}",
        json={"expected_version": None, "weight_value": "10000", "weight_unit_id": ids["g"]},
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "PESO-1",
            "name": "Peso normalizado",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "min_weight": "5",
            "max_weight": "20",
            "weight_unit_id": ids["kg"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={ids['warehouse_id']}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    assert r.json()["result"] == "CLASSIFIED"

    r = mundo.client.put(
        f"{API}/storage/profiles/{ids['product']}",
        json={"expected_version": r.json().get("version", 1), "weight_value": "30000", "weight_unit_id": ids["g"]},
        headers=cab,
    )
    if r.status_code == 409:
        r = mundo.client.put(
            f"{API}/storage/profiles/{ids['product']}",
            json={"expected_version": 1, "weight_value": "30000", "weight_unit_id": ids["g"]},
            headers=cab,
        )
    assert r.status_code in (200, 409), r.text
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={ids['warehouse_id']}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    assert r.json()["result"] == "NO_RULE"


def test_sin_regla(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={ids['warehouse_id']}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["result"] == "NO_RULE"
    assert data["zone_ids"] == []
    assert "No existe una regla de almacenamiento aplicable" in data["reasons"]


def test_ambigua(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "AMB-1",
            "name": "Ambigua Uno",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "AMB-2",
            "name": "Ambigua Dos",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "target_zone_id": ids["zone_2"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={ids['warehouse_id']}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["result"] == "AMBIGUOUS"
    assert data["rule"] is None
    assert "AMB-1" in data["candidate_rules"]
    assert "AMB-2" in data["candidate_rules"]


def test_prioridad_y_especificidad(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "PRI-2",
            "name": "Prioridad dos",
            "priority": 2,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "PRI-1-ESPECIFICA",
            "name": "Prioridad uno especifica",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "min_weight": "5",
            "max_weight": "15",
            "weight_unit_id": ids["kg"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.put(
        f"{API}/storage/profiles/{ids['product']}",
        json={"expected_version": None, "weight_value": "10", "weight_unit_id": ids["kg"]},
        headers=cab,
    )
    if r.status_code == 409:
        r = mundo.client.put(
            f"{API}/storage/profiles/{ids['product']}",
            json={"expected_version": 1, "weight_value": "10", "weight_unit_id": ids["kg"]},
            headers=cab,
        )
    assert r.status_code in (200, 409), r.text
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={ids['warehouse_id']}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["result"] == "CLASSIFIED"
    assert data["rule"]["code"] == "PRI-1-ESPECIFICA"


def test_criterio_faltante(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.put(
        f"{API}/storage/profiles/{ids['product']}",
        json={"expected_version": None, "condition_ids": []},
        headers=cab,
    )
    if r.status_code == 409:
        r = mundo.client.put(
            f"{API}/storage/profiles/{ids['product']}",
            json={"expected_version": 1, "condition_ids": []},
            headers=cab,
        )
    assert r.status_code in (200, 409), r.text
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "FALTANTE",
            "name": "Criterio Faltante",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "min_weight": "5",
            "max_weight": "15",
            "weight_unit_id": ids["kg"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={ids['warehouse_id']}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["result"] == "NO_RULE"
    assert "Peso" in data["missing_criteria"]


def test_uom_incompatible(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "UOM-MAL",
            "name": "UOM Incorrecta",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "min_weight": "5",
            "max_weight": "15",
            "weight_unit_id": ids["l"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "UOM_DIMENSION_MISMATCH"
    r = mundo.client.put(
        f"{API}/storage/profiles/{ids['product']}",
        json={"expected_version": None, "weight_value": "10", "weight_unit_id": ids["l"]},
        headers=cab,
    )
    if r.status_code == 409:
        r = mundo.client.put(
            f"{API}/storage/profiles/{ids['product']}",
            json={"expected_version": 1, "weight_value": "10", "weight_unit_id": ids["l"]},
            headers=cab,
        )
    assert r.status_code in (422, 409), r.text
    if r.status_code == 422:
        assert r.json()["code"] == "UOM_DIMENSION_MISMATCH"


def test_zona_invalida(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    with mundo.factory() as db:
        other_company = db.scalars(select(Company).where(Company.tenant_id == mundo.tenant_b_id)).first()
        other_zt = ZoneType(company_id=other_company.id, code="OTRO-TIPO", name="Otro Tipo", created_by=mundo.admin_id, status="ACTIVE")
        other_wh = Warehouse(company_id=other_company.id, code=f"WH-{uuid4().hex[:8]}", name="Otro Almacen", created_by=mundo.admin_id)
        db.add_all([other_zt, other_wh])
        db.flush()
        other_zone = WarehouseZone(company_id=other_company.id, warehouse_id=other_wh.id, zone_type_id=other_zt.id, code="OTRA-Z", name="Otra Zona", status="ACTIVE", created_by=mundo.admin_id)
        db.add(other_zone)
        db.commit()
        other_zone_id = str(other_zone.id)

    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "ZONA-OTRA",
            "name": "Zona Otra Empresa",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "target_zone_id": other_zone_id,
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "ZONE_NOT_FOUND"

    with mundo.factory() as db:
        zone = db.get(WarehouseZone, ids["zone_1"])
        zone.status = "INACTIVE"
        db.commit()
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "ZONA-INACTIVA",
            "name": "Zona Inactiva",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "ZONE_INACTIVE"
    with mundo.factory() as db:
        zone = db.get(WarehouseZone, ids["zone_1"])
        zone.status = "ACTIVE"
        db.commit()

    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "ZONA-OTRO-ALM",
            "name": "Zona Otro Almacen",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "target_zone_id": ids["zone_2"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    if r.status_code == 409:
        assert r.json()["code"] == "ZONE_OTHER_WAREHOUSE"


def test_tipo_de_zona_sin_zonas(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "TIPO-SIN-ZONA",
            "name": "Tipo Sin Zona",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": None,
            "taxonomy_id": ids["root"],
            "target_zone_type_id": ids["zone_type_3"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={ids['warehouse_id']}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["result"] == "NO_RULE"
    assert any("Sin zonas del tipo" in reason for reason in data["reasons"])


def test_clasificacion_instantanea_y_vigencia(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "INST",
            "name": "Instantanea",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    rule_id = r.json()["id"]
    rule_version = r.json()["version"]
    with mundo.factory() as db:
        c1 = storage_service.classify(
            db,
            company_id=mundo.company_id,
            warehouse_id=ids["warehouse_id"],
            item_id=ids["product"],
            state="DISPONIBLE",
            actor_id=mundo.admin_id,
        )
        db.commit()
        c1_id = str(c1.id)
    with mundo.factory() as db:
        c1 = db.get(storage_models.StorageClassification, c1_id)
        assert c1.status == "CURRENT"
        assert c1.rule_version == rule_version
        assert c1.rule_code == "INST"
        snapshot_target = c1.target_label
    with mundo.factory() as db:
        c2 = storage_service.classify(
            db,
            company_id=mundo.company_id,
            warehouse_id=ids["warehouse_id"],
            item_id=ids["product"],
            state="DISPONIBLE",
            actor_id=mundo.admin_id,
        )
        db.commit()
        c2_id = str(c2.id)
    with mundo.factory() as db:
        c1_after = db.get(storage_models.StorageClassification, c1_id)
        c2_after = db.get(storage_models.StorageClassification, c2_id)
        assert c1_after.status == "SUPERSEDED"
        assert c2_after.status == "CURRENT"

    r = mundo.client.patch(
        f"{API}/storage/rules/{rule_id}",
        json={"expected_version": rule_version, "name": "Instantanea Actualizada"},
        headers=cab,
    )
    assert r.status_code == 200, r.text
    with mundo.factory() as db:
        c2_after = db.get(storage_models.StorageClassification, c2_id)
        d = storage_service.classification_dict(db, c2_after)
        assert d["stale"] is True
        assert c2_after.rule_code == "INST"
        assert c2_after.target_label == snapshot_target

    r = mundo.client.patch(
        f"{API}/storage/rules/{rule_id}",
        json={"expected_version": rule_version, "name": "Version Vieja"},
        headers=cab,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "VERSION_CONFLICT"


def test_permisos(mundo, reloj_mfa, rol_lectura, ids):
    cab = _operador(mundo, reloj_mfa, rol_lectura)
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": "PERMISO",
            "name": "Sin Permiso",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 403
    r = mundo.client.put(
        f"{API}/storage/profiles/{ids['product']}",
        json={"expected_version": None, "condition_ids": []},
        headers=cab,
    )
    assert r.status_code == 403
    r = mundo.client.put(
        f"{API}/storage/warehouse-policies/{ids['warehouse_id']}",
        json={"expected_version": None, "mode": "ENFORCED", "on_no_rule": "BLOCK"},
        headers=cab,
    )
    assert r.status_code == 403
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={ids['warehouse_id']}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 200


def test_aislamiento(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    with mundo.factory() as db:
        other_company = db.scalars(select(Company).where(Company.tenant_id == mundo.tenant_b_id)).first()
        other_item = CatalogItem(
            company_id=other_company.id,
            item_type="PRODUCT",
            code=f"ISO-PROD-{uuid4().hex[:8]}",
            name="Producto Aislado",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(other_item)
        other_condition = storage_models.StorageCondition(
            company_id=other_company.id,
            code=f"ISO-COND-{uuid4().hex[:8]}",
            name="Condición Aislada",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(other_condition)
        db.commit()
        other_item_id = str(other_item.id)
        other_condition_id = str(other_condition.id)

    r = mundo.client.put(
        f"{API}/storage/profiles/{other_item_id}",
        json={"expected_version": None, "condition_ids": []},
        headers=cab,
    )
    assert r.status_code == 404
    r = mundo.client.put(
        f"{API}/storage/profiles/{ids['product']}",
        json={"expected_version": None, "condition_ids": [other_condition_id]},
        headers=cab,
    )
    assert r.status_code == 404
    r = mundo.client.get(
        f"{API}/storage/evaluate?warehouse_id={uuid4()}&item_id={ids['product']}",
        headers=cab,
    )
    assert r.status_code == 404


def test_politica(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.get(
        f"{API}/storage/warehouse-policies/{ids['warehouse_id']}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["mode"] == "DISABLED"
    assert data["version"] is None
    r = mundo.client.put(
        f"{API}/storage/warehouse-policies/{ids['warehouse_id']}",
        json={"expected_version": None, "mode": "ENFORCED", "on_no_rule": "BLOCK"},
        headers=cab,
    )
    assert r.status_code == 200, r.text
    assert r.json()["version"] == 1
    r = mundo.client.put(
        f"{API}/storage/warehouse-policies/{ids['warehouse_id']}",
        json={"expected_version": None, "mode": "ENFORCED", "on_no_rule": "BLOCK"},
        headers=cab,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "VERSION_CONFLICT"


def test_auditoria(mundo, reloj_mfa, rol_almacen, ids):
    cab = _operador(mundo, reloj_mfa, rol_almacen)
    r = mundo.client.post(
        f"{API}/storage/rules",
        json={
            "code": f"AUD-{uuid4().hex[:8]}",
            "name": "Regla Auditoria",
            "priority": 1,
            "status": "ACTIVE",
            "warehouse_id": ids["warehouse_id"],
            "taxonomy_id": ids["root"],
            "target_zone_id": ids["zone_1"],
            "label_policy": "NOT_REQUIRED",
        },
        headers=cab,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.put(
        f"{API}/storage/profiles/{ids['product']}",
        json={"expected_version": None, "condition_ids": []},
        headers=cab,
    )
    if r.status_code == 409:
        r = mundo.client.put(
            f"{API}/storage/profiles/{ids['product']}",
            json={"expected_version": 1, "condition_ids": []},
            headers=cab,
        )
    assert r.status_code in (200, 409), r.text
    r = mundo.client.put(
        f"{API}/storage/warehouse-policies/{ids['warehouse_id']}",
        json={"expected_version": None, "mode": "ENFORCED", "on_no_rule": "ALLOW_ANY"},
        headers=cab,
    )
    if r.status_code == 409:
        r = mundo.client.put(
            f"{API}/storage/warehouse-policies/{ids['warehouse_id']}",
            json={"expected_version": 1, "mode": "ENFORCED", "on_no_rule": "ALLOW_ANY"},
            headers=cab,
        )
    assert r.status_code in (200, 409), r.text
    with mundo.factory() as db:
        storage_service.classify(
            db,
            company_id=mundo.company_id,
            warehouse_id=ids["warehouse_id"],
            item_id=ids["product"],
            state="DISPONIBLE",
            actor_id=mundo.admin_id,
        )
        db.commit()
    with mundo.factory() as db:
        actions = set(
            db.scalars(
                select(AuditEvent.action).where(AuditEvent.company_id == mundo.company_id)
            ).all()
        )
        assert "STORAGE_RULE_CREATED" in actions
        assert "PRODUCT_STORAGE_PROFILE_SAVED" in actions
        assert "WAREHOUSE_STORAGE_POLICY_SAVED" in actions
        assert "STORAGE_CLASSIFIED" in actions


@pytest.mark.skipif(not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"), reason="Requiere PostgreSQL")
def test_concurrencia_reclasificacion(mundo, reloj_mfa, rol_almacen, ids):
    def _clasificar():
        with mundo.factory() as db:
            storage_service.classify(
                db,
                company_id=mundo.company_id,
                warehouse_id=ids["warehouse_id"],
                item_id=ids["product"],
                state="DISPONIBLE",
                actor_id=mundo.admin_id,
            )
            db.commit()

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(_clasificar) for _ in range(2)]
        for future in futures:
            future.result()

    with mundo.factory() as db:
        current_count = db.scalars(
            select(storage_models.StorageClassification).where(
                storage_models.StorageClassification.company_id == mundo.company_id,
                storage_models.StorageClassification.warehouse_id == ids["warehouse_id"],
                storage_models.StorageClassification.item_id == ids["product"],
                storage_models.StorageClassification.receipt_id.is_(None),
                storage_models.StorageClassification.status == "CURRENT",
            )
        ).all()
        assert len(current_count) == 1
