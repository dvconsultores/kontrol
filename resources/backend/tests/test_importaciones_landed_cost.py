# ruff: noqa: E402, F811, F401, I001
import os
import threading
import uuid
from datetime import date, datetime, UTC
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from test_importaciones_seguimiento import (
    _almacen,
    _hasta_despachado,
    _operador,
    mundo,
    rol_completo,
    rol_solo_lectura,
)

from app.core.errors import ConflictError
from app.modules.audit.models import AuditEvent
from app.modules.imports import landed_cost
from app.modules.imports.landed_cost import apply_allocation
from app.modules.imports.models import (
    ImportCostApplication,
    ImportFile,
)
from app.modules.imports.service import get_file
from app.modules.inventory import service as inventory_service
from app.modules.inventory.models import (
    CostLayer,
    CostingProfile,
    InventoryMovement,
    MovementType,
)
from app.modules.master_data.models import CatalogItem, UnitOfMeasure
from app.modules.organization.models import Company
from app.modules.purchasing.models import GoodsReceipt
from app.modules.treasury import rates
from app.modules.treasury.models import Currency, ExchangeRate, TreasuryRateSnapshot
from app.shared.clock import zona_de_negocio

pytest_plugins = ["mfa_apoyo"]

API = "/api/v1"


def _tasa(mundo, fecha, code, rate, quote="VED"):
    with mundo.factory() as db:
        rates.asegurar_moneda_funcional(db, mundo.company_id, mundo.admin_id)
        moneda_base = rates.moneda_por_codigo(db, mundo.company_id, code)
        if moneda_base is None:
            moneda_base = Currency(
                company_id=mundo.company_id,
                code=code,
                name=code,
                status="ACTIVE",
                created_by=mundo.admin_id,
            )
            db.add(moneda_base)
            db.flush()
        moneda_quote = rates.moneda_por_codigo(db, mundo.company_id, quote)
        if moneda_quote is None:
            moneda_quote = Currency(
                company_id=mundo.company_id,
                code=quote,
                name=quote,
                status="ACTIVE",
                created_by=mundo.admin_id,
            )
            db.add(moneda_quote)
            db.flush()

        # La unicidad por empresa, monedas, rate_type y effective_at es real.
        # El fixture `mundo` es de ámbito módulo: se comparte empresa entre
        # escenarios. Si la observación ya existe, reutilizarla es correcto.
        # `register_rate` y la unicidad comparan el instante normalizado a UTC
        # (`rates._momento`): una fecha civil se guarda como las 00:00 de
        # Caracas en UTC. La comprobación de existencia debe usar ese mismo
        # instante, no la fecha civil.
        momento = rates._momento(fecha)
        existente = db.scalar(
            select(ExchangeRate).where(
                ExchangeRate.company_id == mundo.company_id,
                ExchangeRate.base_currency_id == moneda_base.id,
                ExchangeRate.quote_currency_id == moneda_quote.id,
                ExchangeRate.rate_type == "REFERENCE",
                ExchangeRate.effective_at == momento,
            )
        )
        if existente is not None:
            db.commit()
            return existente

        obs = rates.register_rate(
            db,
            company_id=mundo.company_id,
            base_code=code,
            quote_code=quote,
            rate=Decimal(rate),
            effective_at=fecha,
            actor=mundo.admin_id,
        )
        db.commit()
        return obs


def _gasto(mundo, cabeceras, file_id, **campos):
    payload = {
        "kind": "DIRECT_IMPORT_EXPENSE",
        "concept": f"gasto-{uuid4().hex[:8]}",
        "expense_date": date.today().isoformat(),
        "amount": "1.00",
        "currency": "VED",
        "reference": f"ref-{uuid4().hex[:8]}",
        "supplier_id": None,
        "supplier_invoice_id": None,
        "import_document_id": None,
    }
    payload.update(campos)
    return mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses", json=payload, headers=cabeceras
    )


def _id_gasto(mundo, cabeceras, file_id, response):
    """Devuelve el id del gasto recién registrado.

    El contrato real de POST /expenses devuelve el detalle de costos del
    expediente (igual que GET /costs), no el gasto. Localizamos el gasto por
    su concept en la lista "expenses". El request del TestClient de Starlette
    es un httpx.Request: no tiene .json, pero conserva el cuerpo enviado en
    .content, que aquí es el JSON del gasto.
    """
    assert response.status_code == 200, response.text
    detalle = response.json()
    import json

    request_payload = json.loads(response.request.content)
    concept = request_payload["concept"]
    gasto = next(e for e in detalle["expenses"] if e["concept"] == concept)
    return gasto["id"]


def _entrada(
    mundo,
    file_id,
    *,
    unit_cost,
    quantity,
    currency,
    product_id=None,
    base_unit_id=None,
    warehouse_id=None,
):
    with mundo.factory() as db:
        file = db.get(ImportFile, file_id)
        if warehouse_id is None:
            warehouse_id = _almacen(mundo, mundo.company_id)
        receipt = GoodsReceipt(
            company_id=mundo.company_id,
            code=f"REC-{uuid4().hex[:8]}",
            order_id=file.order_id,
            warehouse_id=warehouse_id,
            status="ACCEPTED",
            quality_status="APPROVED",
        )
        db.add(receipt)
        db.flush()

        if product_id is None:
            product = CatalogItem(
                company_id=mundo.company_id,
                item_type="PRODUCT",
                code=f"PROD-{uuid4().hex[:8]}",
                name=f"producto-{uuid4().hex[:8]}",
                base_unit_id=base_unit_id,
                created_by=mundo.admin_id,
                status="ACTIVE",
            )
            db.add(product)
            db.flush()
            product_id = product.id

        movimiento_tipo = MovementType(
            company_id=mundo.company_id,
            code=f"MT-{uuid4().hex[:8]}",
            name=f"mov-{uuid4().hex[:8]}",
            direction="IN",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(movimiento_tipo)
        db.flush()

        inventory_service.record_movement(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            movement_type_id=movimiento_tipo.id,
            quantity=quantity,
            unit_cost=Decimal(unit_cost),
            currency=currency,
            document_ref=f"RECEIPT:{receipt.id}",
            actor=mundo.admin_id,
        )
        db.commit()

        layer = db.scalar(
            select(CostLayer).where(CostLayer.receipt_ref == f"RECEIPT:{receipt.id}")
        )
        return {
            "layer_id": layer.id,
            "product_id": product_id,
            "warehouse_id": warehouse_id,
        }


def _salida(mundo, product_id, warehouse_id, quantity):
    with mundo.factory() as db:
        movement_type = MovementType(
            company_id=mundo.company_id,
            code=f"OUT-{uuid4().hex[:8]}",
            name=f"salida-{uuid4().hex[:8]}",
            direction="OUT",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(movement_type)
        db.flush()
        movement = inventory_service.record_movement(
            db,
            company_id=mundo.company_id,
            warehouse_id=warehouse_id,
            product_id=product_id,
            movement_type_id=movement_type.id,
            quantity=-quantity,
            currency="VED",
            actor=mundo.admin_id,
        )
        db.commit()
        return movement.id


def _clasificar(mundo, cab, file_id, expense_id, cap="CAPITALIZABLE"):
    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/costs",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    expense = next(e for e in r.json()["expenses"] if e["id"] == expense_id)
    payload = {"version": expense["version"], "capitalization": cap}
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{expense_id}/classification",
        json=payload,
        headers=cab,
    )
    assert r.status_code == 200, r.text
    return r


def _previa(mundo, cab, file_id, expense_id, criterion, manual_amounts=None):
    payload = {"criterion": criterion}
    if manual_amounts is not None:
        payload["manual_amounts"] = manual_amounts
    return mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{expense_id}/allocation-preview",
        json=payload,
        headers=cab,
    )


def _aplicar(
    mundo,
    cab,
    file_id,
    expense_id,
    criterion,
    manual_amounts,
    preview_token,
):
    payload = {
        "criterion": criterion,
        "manual_amounts": manual_amounts,
        "preview_token": preview_token,
    }
    return mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{expense_id}/apply",
        json=payload,
        headers=cab,
    )


def _expediente_con_capa_usd(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    capa = _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
    )
    return cab, file_id, supplier_id, capa


def test_distribuir_redondeo_preciso():
    resultado = landed_cost.distribuir(
        Decimal("100.00"), [("a", Decimal("1")), ("b", Decimal("1")), ("c", Decimal("1"))]
    )
    importes = [asignado for _, _, _, _, asignado in resultado]
    assert importes == [Decimal("33.34"), Decimal("33.33"), Decimal("33.33")]

    resultado = landed_cost.distribuir(
        Decimal("0.05"), [("a", Decimal("1")), ("b", Decimal("1"))]
    )
    importes = [asignado for _, _, _, _, asignado in resultado]
    assert importes == [Decimal("0.03"), Decimal("0.02")]

    resultado = landed_cost.distribuir(
        Decimal("10.00"),
        [("a", Decimal("10")), ("b", Decimal("20")), ("c", Decimal("30"))],
    )
    importes = [asignado for _, _, _, _, asignado in resultado]
    assert importes == [Decimal("1.67"), Decimal("3.33"), Decimal("5.00")]


def test_value_con_residuo_y_aislamiento_de_lineas(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")

    capas = []
    for unit_cost in ["1.00", "2.00", "3.00"]:
        capa = _entrada(
            mundo,
            file_id,
            unit_cost=unit_cost,
            quantity=10,
            currency="USD",
        )
        capas.append(capa)

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)

    _clasificar(mundo, cab, file_id, expense_id)

    with mundo.factory() as db:
        snapshots_antes = db.scalars(select(TreasuryRateSnapshot)).all()

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["distributed_total"] == "10.00"
    assert body["valuation_currency"] == "USD"
    assert body["valuation_amount"] == "10.00"
    assert body["can_apply"] is True
    assert len(body["lines"]) == 3
    lineas = {line["layer_id"]: line["allocated_amount"] for line in body["lines"]}
    for capa, esperado in zip(capas, ["1.67", "3.33", "5.00"], strict=True):
        assert lineas[capa["layer_id"]] == esperado
    token = body["preview_token"]

    with mundo.factory() as db:
        snapshots_despues = db.scalars(select(TreasuryRateSnapshot)).all()
        assert len(snapshots_antes) == len(snapshots_despues)

    # Otro expediente de la misma empresa no contamina las líneas
    cab2, file_id2, supplier_id2 = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _entrada(
        mundo,
        file_id2,
        unit_cost="99.00",
        quantity=10,
        currency="USD",
    )
    r2 = _gasto(
        mundo,
        cab,
        file_id2,
        amount="5.00",
        currency="USD",
        supplier_id=supplier_id2,
        expense_date="2025-01-01",
    )
    expense_id2 = _id_gasto(mundo, cab, file_id2, r2)
    _clasificar(mundo, cab, file_id2, expense_id2)

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    body = r.json()
    assert token == body["preview_token"]
    ids_lineas = {line["layer_id"] for line in body["lines"]}
    assert capas[0]["layer_id"] in ids_lineas
    assert len(body["lines"]) == 3


def test_quantity_comparable_y_no_comparable(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")

    with mundo.factory() as db:
        uom_kg = UnitOfMeasure(
            company_id=mundo.company_id,
            code=f"UOM-{uuid4().hex[:8]}",
            name="Kilogramo",
            symbol="kg",
            status="ACTIVE",
            created_by=mundo.admin_id,
            version=1,
        )
        uom_l = UnitOfMeasure(
            company_id=mundo.company_id,
            code=f"UOM-{uuid4().hex[:8]}",
            name="Litro",
            symbol="L",
            status="ACTIVE",
            created_by=mundo.admin_id,
            version=1,
        )
        db.add_all([uom_kg, uom_l])
        db.commit()
        uom_kg_id = uom_kg.id
        uom_l_id = uom_l.id

    capa_a = _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
        base_unit_id=uom_kg_id,
    )
    capa_b = _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=30,
        currency="USD",
        base_unit_id=uom_kg_id,
    )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="4.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    r = _previa(mundo, cab, file_id, expense_id, "QUANTITY")
    assert r.status_code == 200, r.text
    assert r.json()["can_apply"] is True
    lineas = {line["layer_id"]: line["allocated_amount"] for line in r.json()["lines"]}
    assert lineas[capa_a["layer_id"]] == "1.00"
    assert lineas[capa_b["layer_id"]] == "3.00"

    # Unidades no comparables
    _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
        base_unit_id=uom_l_id,
    )
    r = _previa(mundo, cab, file_id, expense_id, "QUANTITY")
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_COST_QUANTITY_NOT_COMPARABLE"


def test_manual_validaciones_y_aplicacion(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")

    capa_a = _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
    )
    capa_b = _entrada(
        mundo,
        file_id,
        unit_cost="2.00",
        quantity=10,
        currency="USD",
        product_id=capa_a["product_id"],
        warehouse_id=capa_a["warehouse_id"],
    )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    manuales_desbalanceados = {
        capa_a["layer_id"]: "4.00",
        capa_b["layer_id"]: "5.00",
    }
    r = _previa(
        mundo, cab, file_id, expense_id, "MANUAL", manuales_desbalanceados
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["can_apply"] is False
    assert body["blocks"][0]["code"] == "IMPORT_COST_MANUAL_UNBALANCED"
    assert body["blocks"][0]["difference"] == "1.00"
    token = body["preview_token"]

    r = _aplicar(
        mundo,
        cab,
        file_id,
        expense_id,
        "MANUAL",
        manuales_desbalanceados,
        token,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_COST_MANUAL_UNBALANCED"

    with mundo.factory() as db:
        for capa in [capa_a, capa_b]:
            layer = db.get(CostLayer, capa["layer_id"])
            assert layer.landed_cost == Decimal("0.00")

    manuales_ok = {
        capa_a["layer_id"]: "4.00",
        capa_b["layer_id"]: "6.00",
    }
    r = _previa(mundo, cab, file_id, expense_id, "MANUAL", manuales_ok)
    assert r.status_code == 200, r.text
    token = r.json()["preview_token"]
    assert r.json()["can_apply"] is True

    r = _aplicar(mundo, cab, file_id, expense_id, "MANUAL", manuales_ok, token)
    assert r.status_code == 200, r.text

    with mundo.factory() as db:
        layer_a = db.get(CostLayer, capa_a["layer_id"])
        layer_b = db.get(CostLayer, capa_b["layer_id"])
        assert layer_a.landed_cost == Decimal("4.00")
        assert layer_b.landed_cost == Decimal("6.00")

    # Importe con más de dos decimales
    manuales_invalidos = {
        capa_a["layer_id"]: "4.001",
        capa_b["layer_id"]: "5.999",
    }
    r = _previa(mundo, cab, file_id, expense_id, "MANUAL", manuales_invalidos)
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "IMPORT_COST_MANUAL_AMOUNT_INVALID"


def test_moneda_cruzada_y_rate_no_disponible(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    _tasa(mundo, date(2025, 1, 1), "EUR", "40.00")
    _tasa(mundo, date(2025, 1, 1), "EUR", "1.10", quote="USD")
    _tasa(mundo, date(2025, 6, 1), "EUR", "2.00", quote="USD")

    _entrada(
        mundo,
        file_id,
        unit_cost="10.00",
        quantity=10,
        currency="USD",
    )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="100.00",
        currency="EUR",
        supplier_id=supplier_id,
        expense_date="2025-01-10",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["valuation_currency"] == "USD"
    assert body["valuation_amount"] == "110.00"
    token = body["preview_token"]

    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 200, r.text

    with mundo.factory() as db:
        application = db.scalar(
            select(ImportCostApplication).where(
                ImportCostApplication.expense_id == expense_id
            )
        )
        assert application.valuation_currency == "USD"
        assert application.valuation_amount == Decimal("110.00")
        assert application.valuation_rate_snapshot_id is not None
        snapshot = db.get(TreasuryRateSnapshot, application.valuation_rate_snapshot_id)
        assert snapshot.rate == Decimal("1.10")

    # Otro expediente con capa GBP y gasto EUR: no hay tasa cruzada
    cab2, file_id2, supplier_id2 = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "GBP", "60.00")
    _entrada(
        mundo,
        file_id2,
        unit_cost="10.00",
        quantity=10,
        currency="GBP",
    )
    r = _gasto(
        mundo,
        cab,
        file_id2,
        amount="50.00",
        currency="EUR",
        supplier_id=supplier_id2,
        expense_date="2025-01-10",
    )
    expense_id2 = _id_gasto(mundo, cab, file_id2, r)
    _clasificar(mundo, cab, file_id2, expense_id2)
    r = _previa(mundo, cab, file_id2, expense_id2, "VALUE")
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "RATE_NOT_AVAILABLE"


def test_sin_clasificar_y_version_obsoleta(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
    )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    assert r.status_code == 200, r.text
    assert r.json()["can_apply"] is False
    assert r.json()["blocks"][0]["code"] == "IMPORT_COST_NOT_CAPITALIZABLE"
    token = r.json()["preview_token"]

    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_COST_NOT_CAPITALIZABLE"

    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/costs",
        headers=cab,
    )
    expense = next(e for e in r.json()["expenses"] if e["id"] == expense_id)
    payload = {"version": expense["version"] - 1, "capitalization": "CAPITALIZABLE"}
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{expense_id}/classification",
        json=payload,
        headers=cab,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_EXPENSE_STALE"


def test_aplicar_y_valoracion(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")

    capa_a = _entrada(
        mundo,
        file_id,
        unit_cost="12.50",
        quantity=10,
        currency="USD",
    )
    capa_b = _entrada(
        mundo,
        file_id,
        unit_cost="10.00",
        quantity=20,
        currency="USD",
        product_id=capa_a["product_id"],
        warehouse_id=capa_a["warehouse_id"],
    )

    product_id = capa_a["product_id"]
    assert capa_b["product_id"] == product_id

    with mundo.factory() as db:
        valoracion_antes = inventory_service.valuation(
            db, company_id=mundo.company_id, product_id=product_id
        )
    assert valoracion_antes == 325.0

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="100.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["distributed_total"] == "100.00"
    lineas = {line["layer_id"]: line["allocated_amount"] for line in body["lines"]}
    assert lineas[capa_a["layer_id"]] == "38.46"
    assert lineas[capa_b["layer_id"]] == "61.54"
    token = body["preview_token"]

    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 200, r.text

    with mundo.factory() as db:
        valoracion_despues = inventory_service.valuation(
            db, company_id=mundo.company_id, product_id=product_id
        )
        assert valoracion_despues == 425.0

        layer_a = db.get(CostLayer, capa_a["layer_id"])
        layer_b = db.get(CostLayer, capa_b["layer_id"])
        assert inventory_service.effective_unit_cost(layer_a) == Decimal("16.346")
        assert inventory_service.effective_unit_cost(layer_b) == Decimal("13.077")

    r = mundo.client.get(
        f"{API}/inventory/valuation",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    assert any(
        item["currency"] == "USD" for item in r.json()["by_currency"]
    )

    with mundo.factory() as db:
        audit = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "IMPORT_COST_APPLIED",
                AuditEvent.entity_id == file_id,
                AuditEvent.company_id == mundo.company_id,
            )
        )
        assert audit is not None
        assert audit.user_id is not None


def test_salida_posterior_fifo_con_landed_cost(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")

    capa = _entrada(
        mundo,
        file_id,
        unit_cost="5.00",
        quantity=10,
        currency="USD",
    )

    with mundo.factory() as db:
        perfil = CostingProfile(
            company_id=mundo.company_id,
            product_id=capa["product_id"],
            code=f"CP-{uuid4().hex[:8]}",
            method="FIFO",
            currency="USD",
            status="ACTIVE",
            created_by=mundo.admin_id,
            version=1,
        )
        db.add(perfil)
        db.commit()

    # Producto ajeno para verificar que no se altera su coste de salida.
    # Debe vivir en OTRO expediente: si comparte expediente con la capa a la
    # que luego aplicamos landed cost, el bloqueo DM-03 (capa consumida en el
    # expediente) impide legítimamente la aplicación.
    cab2, file_id2, supplier_id2 = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    capa_otro = _entrada(
        mundo,
        file_id2,
        unit_cost="7.00",
        quantity=10,
        currency="USD",
    )
    movimiento_otro = _salida(mundo, capa_otro["product_id"], capa_otro["warehouse_id"], 1)
    with mundo.factory() as db:
        movimiento = db.get(InventoryMovement, movimiento_otro)
        unit_cost_otro_antes = movimiento.unit_cost

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    token = r.json()["preview_token"]
    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 200, r.text

    movimiento_id = _salida(mundo, capa["product_id"], capa["warehouse_id"], 1)
    with mundo.factory() as db:
        movimiento = db.get(InventoryMovement, movimiento_id)
        assert movimiento.unit_cost == Decimal("6.00")

    with mundo.factory() as db:
        movimiento_otro_db = db.get(InventoryMovement, movimiento_otro)
        assert movimiento_otro_db.unit_cost == unit_cost_otro_antes


def test_average_sin_perfil_usando_entradas(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")

    capa_a = _entrada(
        mundo,
        file_id,
        unit_cost="12.50",
        quantity=10,
        currency="USD",
    )
    capa_b = _entrada(
        mundo,
        file_id,
        unit_cost="20.00",
        quantity=10,
        currency="USD",
        product_id=capa_a["product_id"],
        warehouse_id=capa_a["warehouse_id"],
    )
    assert capa_a["product_id"] == capa_b["product_id"]
    product_id = capa_a["product_id"]

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="50.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    manuales = {
        capa_a["layer_id"]: "50.00",
        capa_b["layer_id"]: "0.00",
    }
    r = _previa(mundo, cab, file_id, expense_id, "MANUAL", manuales)
    assert r.status_code == 200, r.text
    token = r.json()["preview_token"]
    r = _aplicar(mundo, cab, file_id, expense_id, "MANUAL", manuales, token)
    assert r.status_code == 200, r.text

    movimiento_id = _salida(mundo, product_id, capa_a["warehouse_id"], 1)
    with mundo.factory() as db:
        movimiento = db.get(InventoryMovement, movimiento_id)
        assert movimiento.unit_cost == Decimal("18.75")


def test_doble_aplicacion_y_duplicado_orm(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    capa = _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
    )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    token = r.json()["preview_token"]
    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 200, r.text

    with mundo.factory() as db:
        layer = db.get(CostLayer, capa["layer_id"])
        landed_primera = layer.landed_cost

    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_COST_ALREADY_APPLIED"

    with mundo.factory() as db:
        layer = db.get(CostLayer, capa["layer_id"])
        assert layer.landed_cost == landed_primera

    # Duplicado por ORM debe fallar por restricción
    with mundo.factory() as db:
        original = db.scalar(
            select(ImportCostApplication).where(
                ImportCostApplication.expense_id == expense_id
            )
        )
        duplicado = ImportCostApplication(
            company_id=original.company_id,
            file_id=original.file_id,
            expense_id=original.expense_id,
            criterion=original.criterion,
            criterion_source=original.criterion_source,
            origin_currency=original.origin_currency,
            origin_amount=original.origin_amount,
            valuation_currency=original.valuation_currency,
            valuation_amount=original.valuation_amount,
            status="APPLIED",
            created_by=mundo.admin_id,
        )
        db.add(duplicado)
        with pytest.raises(IntegrityError):
            db.flush()
        db.rollback()


@pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="requiere PostgreSQL",
)
def test_concurrencia_una_sola_aplicacion(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    capa = _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
    )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    # Un preview_token real y vigente: sin él ambos hilos fallan por token
    # obsoleto antes de competir por el lock de fila.
    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    assert r.status_code == 200, r.text
    preview_token = r.json()["preview_token"]

    resultados = []
    barrier = threading.Barrier(2)

    def aplicar():
        db = mundo.factory()
        try:
            barrier.wait()
            file = get_file(db, mundo.company_id, file_id, for_update=True)
            apply_allocation(
                db,
                file=file,
                expense_id=expense_id,
                criterion="VALUE",
                manual_amounts=None,
                preview_token=preview_token,
                actor_id=mundo.admin_id,
                tenant_id=mundo.tenant_id,
            )
            db.commit()
            resultados.append("ok")
        except ConflictError:
            db.rollback()
            resultados.append("conflict")
        except Exception:
            db.rollback()
            resultados.append("error")
        finally:
            db.close()

    hilos = [threading.Thread(target=aplicar) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    assert resultados.count("ok") == 1
    with mundo.factory() as db:
        layer = db.get(CostLayer, capa["layer_id"])
        assert layer.landed_cost == Decimal("10.00")


def test_capa_consumida_bloquea_aplicacion(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    capa = _entrada(
        mundo,
        file_id,
        unit_cost="5.00",
        quantity=10,
        currency="USD",
    )

    movimiento_id = _salida(mundo, capa["product_id"], capa["warehouse_id"], 2)
    with mundo.factory() as db:
        movimiento = db.get(InventoryMovement, movimiento_id)
        unit_cost_sin_landed = movimiento.unit_cost

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    assert r.status_code == 200, r.text
    assert r.json()["can_apply"] is False
    assert r.json()["blocks"][0]["code"] == "IMPORT_COST_LAYER_CONSUMED"
    token = r.json()["preview_token"]

    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_COST_LAYER_CONSUMED"

    with mundo.factory() as db:
        layer = db.get(CostLayer, capa["layer_id"])
        assert layer.landed_cost == Decimal("0.00")
        movimiento = db.get(InventoryMovement, movimiento_id)
        assert movimiento.unit_cost == unit_cost_sin_landed


def test_reversion_y_bloqueos(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    capa = _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
    )

    with mundo.factory() as db:
        valoracion_antes = inventory_service.valuation(
            db, company_id=mundo.company_id, product_id=capa["product_id"]
        )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    token = r.json()["preview_token"]
    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 200, r.text

    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/costs",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    expense = next(e for e in body["expenses"] if e["id"] == expense_id)
    application = expense["applications"][0]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/cost-applications/{application['id']}/reverse",
        json={"version": application["version"], "reason": "Error"},
        headers=cab,
    )
    assert r.status_code == 200, r.text

    with mundo.factory() as db:
        valoracion_despues = inventory_service.valuation(
            db, company_id=mundo.company_id, product_id=capa["product_id"]
        )
        assert valoracion_despues == valoracion_antes

        app = db.get(ImportCostApplication, application["id"])
        assert app.status == "REVERSED"

        audit = db.scalar(
            select(AuditEvent).where(
                AuditEvent.action == "IMPORT_COST_REVERSED",
                AuditEvent.entity_id == file_id,
                AuditEvent.company_id == mundo.company_id,
            )
        )
        assert audit is not None

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    assert r.status_code == 200, r.text
    assert r.json()["can_apply"] is True

    # Reversión bloqueada cuando hay salida posterior
    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    token = r.json()["preview_token"]
    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 200, r.text

    _salida(mundo, capa["product_id"], capa["warehouse_id"], 1)

    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/costs",
        headers=cab,
    )
    body = r.json()
    expense = next(e for e in body["expenses"] if e["id"] == expense_id)
    application_vigente = next(
        a for a in expense["applications"] if a["status"] != "REVERSED"
    )
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/cost-applications/{application_vigente['id']}/reverse",
        json={"version": application_vigente["version"], "reason": "Error"},
        headers=cab,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_COST_REVERSAL_BLOCKED"

    # Void del gasto con aplicación vigente
    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/costs",
        headers=cab,
    )
    expense = next(e for e in r.json()["expenses"] if e["id"] == expense_id)
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{expense_id}/void",
        json={"version": expense["version"], "reason": "Error"},
        headers=cab,
    )
    assert r.status_code == 409, r.text
    assert r.json()["code"] == "IMPORT_EXPENSE_APPLIED"


def test_permisos_solo_lectura(mundo, reloj_mfa, rol_completo, rol_solo_lectura):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    capa = _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
    )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    cab_ro = _operador(mundo, reloj_mfa, rol_solo_lectura)

    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/costs",
        headers=cab,
    )
    expense = next(e for e in r.json()["expenses"] if e["id"] == expense_id)

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{expense_id}/classification",
        json={"version": expense["version"], "capitalization": "CAPITALIZABLE"},
        headers=cab_ro,
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "PERMISSION_DENIED"

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    token = r.json()["preview_token"]

    r = _aplicar(mundo, cab_ro, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "PERMISSION_DENIED"

    # Aplicar con el operador completo para luego intentar reversión con RO
    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 200, r.text

    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/costs",
        headers=cab,
    )
    body = r.json()
    expense = next(e for e in body["expenses"] if e["id"] == expense_id)
    application = expense["applications"][0]

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/cost-applications/{application['id']}/reverse",
        json={"version": application["version"], "reason": "Error"},
        headers=cab_ro,
    )
    assert r.status_code == 403, r.text
    assert r.json()["code"] == "PERMISSION_DENIED"

    with mundo.factory() as db:
        layer = db.get(CostLayer, capa["layer_id"])
        assert layer.landed_cost == Decimal("10.00")


def test_aislamiento_empresa_y_expense_ajeno(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
    )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    # Expediente de otra empresa
    with mundo.factory() as db:
        other_company_id = db.scalar(
            select(Company.id).where(Company.tenant_id == mundo.tenant_b_id)
        )
        from app.modules.master_data.models import Party

        proveedor_externo = Party(
            company_id=other_company_id,
            code=f"PROV-{uuid.uuid4().hex[:8]}",
            name="Proveedor externo",
            person_type="JURIDICA",
            roles=["SUPPLIER"],
        )
        db.add(proveedor_externo)
        db.flush()
        file_externo = ImportFile(
            company_id=other_company_id,
            code=f"IMP-{uuid.uuid4().hex[:12]}",
            supplier_id=str(proveedor_externo.id),
            currency="VED",
            status="NEGOTIATING",
        )
        db.add(file_externo)
        db.commit()
        file_externo_id = file_externo.id

    r = _previa(mundo, cab, file_externo_id, expense_id, "VALUE")
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "IMPORT_NOT_FOUND"

    r = _aplicar(mundo, cab, file_externo_id, expense_id, "VALUE", None, "token")
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "IMPORT_NOT_FOUND"

    # Expense de otro expediente propio en la ruta de este expediente
    cab2, file_id2, supplier_id2 = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    r = _gasto(
        mundo,
        cab,
        file_id2,
        amount="5.00",
        currency="USD",
        supplier_id=supplier_id2,
        expense_date="2025-01-01",
    )
    expense_ajeno = _id_gasto(mundo, cab, file_id2, r)

    r = _previa(mundo, cab, file_id, expense_ajeno, "VALUE")
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "IMPORT_EXPENSE_NOT_FOUND"


def test_auditoria_clasificacion_aplicacion_y_reversion(mundo, reloj_mfa, rol_completo):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    _tasa(mundo, date(2025, 1, 1), "USD", "36.125")
    _entrada(
        mundo,
        file_id,
        unit_cost="1.00",
        quantity=10,
        currency="USD",
    )

    r = _gasto(
        mundo,
        cab,
        file_id,
        amount="10.00",
        currency="USD",
        supplier_id=supplier_id,
        expense_date="2025-01-01",
    )
    expense_id = _id_gasto(mundo, cab, file_id, r)
    _clasificar(mundo, cab, file_id, expense_id)

    r = _previa(mundo, cab, file_id, expense_id, "VALUE")
    token = r.json()["preview_token"]
    r = _aplicar(mundo, cab, file_id, expense_id, "VALUE", None, token)
    assert r.status_code == 200, r.text

    r = mundo.client.get(
        f"{API}/importaciones/{file_id}/costs",
        headers=cab,
    )
    expense = next(e for e in r.json()["expenses"] if e["id"] == expense_id)
    application = expense["applications"][0]
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/cost-applications/{application['id']}/reverse",
        json={"version": application["version"], "reason": "Error"},
        headers=cab,
    )
    assert r.status_code == 200, r.text

    with mundo.factory() as db:
        acciones = [
            "IMPORT_EXPENSE_CLASSIFIED",
            "IMPORT_COST_APPLIED",
            "IMPORT_COST_REVERSED",
        ]
        for accion in acciones:
            audit = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.action == accion,
                    AuditEvent.entity_id == file_id,
                    AuditEvent.company_id == mundo.company_id,
                    AuditEvent.user_id.is_not(None),
                )
            )
            assert audit is not None, f"Falta auditoría {accion}"
