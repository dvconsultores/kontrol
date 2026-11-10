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

from app.modules.master_data.models import CatalogItem

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


def test_a_articulo_empresa_ajena_perfil_404(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["maestros:view"])
    cab = _operador(mundo, reloj_mfa, rol_id)

    with mundo.factory() as db:
        from app.modules.organization.models import Company

        company_b = db.scalars(select(Company).where(Company.tenant_id == mundo.tenant_b_id)).first()
        item = CatalogItem(
            company_id=company_b.id,
            item_type="PRODUCT",
            code=f"PROD-B-{uuid.uuid4().hex[:8]}",
            name="Producto Empresa B",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(item)
        db.flush()
        item_id_b = item.id
        db.commit()

    r = mundo.client.get(
        f"{API}/storage/profiles/{item_id_b}",
        headers=cab,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "PRODUCT_NOT_FOUND"


def test_b_articulo_propio_sin_perfil_200(mundo, reloj_mfa):
    rol_id = _crear_rol(mundo, ["maestros:view"])
    cab = _operador(mundo, reloj_mfa, rol_id)

    item_id = _producto(mundo)

    r = mundo.client.get(
        f"{API}/storage/profiles/{item_id}",
        headers=cab,
    )
    assert r.status_code == 200
    assert r.json()["item_id"] == item_id
    assert r.json()["version"] is None
