# ruff: noqa: E402, F811, F401

pytest_plugins = ("mfa_apoyo",)

from datetime import date
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from test_importaciones_seguimiento import (
    _almacen,
    _crear_expediente,
    _hasta_despachado,
    _operador,
    _proveedor,
    mundo,
    rol_completo,
    rol_solo_lectura,
)  # noqa: F401

from app.modules.imports.models import ImportFile
from app.modules.inventory.models import CostLayer
from app.modules.master_data.models import CatalogItem, Party
from app.modules.organization.models import Company
from app.modules.purchasing.models import GoodsReceipt, SupplierInvoice
from app.modules.treasury import rates
from app.modules.treasury.models import Currency

API = "/api/v1"


def _tasa(mundo, fecha, code, rate):
    with mundo.factory() as db:
        rates.asegurar_moneda_funcional(db, mundo.company_id, mundo.admin_id)
        if rates.moneda_por_codigo(db, mundo.company_id, code) is None:
            db.add(
                Currency(
                    company_id=mundo.company_id,
                    code=code,
                    name=code,
                    status="ACTIVE",
                    created_by=mundo.admin_id,
                )
            )
            db.flush()
        rates.register_rate(
            db,
            company_id=mundo.company_id,
            base_code=code,
            quote_code="VED",
            rate=Decimal(rate),
            effective_at=fecha,
            actor=mundo.admin_id,
        )
        db.commit()


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


def test_flujo_principal(mundo, reloj_mfa, rol_completo):
    cabeceras, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)

    docs = mundo.client.get(f"{API}/importaciones/{file_id}", headers=cabeceras).json()["documents"]
    assert docs, "el expediente despachado debe tener documentos"
    import_document_id = docs[0]["id"]

    with mundo.factory() as db:
        order_id = db.scalar(select(ImportFile.order_id).where(ImportFile.id == file_id))

    _tasa(mundo, date(2025, 1, 10), "USD", "36.125")
    g1 = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="DIRECT_IMPORT_EXPENSE",
        currency="USD",
        amount="1250.50",
        expense_date="2025-01-20",
        reference="ref-usd",
        supplier_id=supplier_id,
        import_document_id=import_document_id,
    )
    assert g1.status_code == 200, g1.text
    r = g1.json()
    assert r["totals"]["functional_total"] == "45174.31"
    assert r["expenses"][0]["rate"]["value"] == "36.125"
    assert r["expenses"][0]["rate"]["identity"] is False
    assert r["totals"]["by_currency"] == [{"currency": "USD", "amount": "1250.50"}]

    _tasa(mundo, date(2025, 1, 10), "EUR", "1.25")
    g2 = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="DIRECT_IMPORT_EXPENSE",
        currency="EUR",
        amount="100.10",
        expense_date="2025-01-20",
        reference="ref-eur",
        supplier_id=supplier_id,
        import_document_id=import_document_id,
    )
    assert g2.status_code == 200, g2.text
    r2 = g2.json()
    gasto_eur = next(
        gasto for gasto in r2["expenses"] if gasto["currency"] == "EUR"
    )
    assert gasto_eur["functional_amount"] == "125.12"
    assert r2["totals"]["functional_total"] == "45299.43"

    g3 = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="DIRECT_IMPORT_EXPENSE",
        currency="VED",
        amount="100.10",
        expense_date="2025-01-20",
        reference="ref-ved",
        supplier_id=supplier_id,
        import_document_id=import_document_id,
    )
    assert g3.status_code == 200, g3.text
    r3 = g3.json()
    gasto_ved = next(e for e in r3["expenses"] if e["currency"] == "VED")
    assert gasto_ved["functional_amount"] == "100.10"
    assert gasto_ved["rate"]["identity"] is True
    assert r3["totals"]["functional_total"] == "45399.53"
    assert [e["currency"] for e in r3["totals"]["by_currency"]] == ["EUR", "USD", "VED"]

    gasto_ved_id = gasto_ved["id"]
    vo = mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{gasto_ved_id}/void",
        json={"reason": "prueba", "version": gasto_ved["version"]},
        headers=cabeceras,
    )
    assert vo.status_code == 200, vo.text
    rv = vo.json()
    assert rv["totals"]["functional_total"] == "45299.43"
    gasto_anulado = next(e for e in rv["expenses"] if e["id"] == gasto_ved_id)
    assert gasto_anulado["status"] == "VOIDED"
    assert gasto_anulado["void_reason"] == "prueba"
    assert gasto_anulado["allowed_actions"]["void"] is False
    assert rv["totals"]["count"] == 2

    receipt_code = f"REC-{uuid4().hex[:8]}"
    codigo_producto = f"PROD-{uuid4().hex[:8]}"
    with mundo.factory() as db:
        item = CatalogItem(
            company_id=mundo.company_id,
            item_type="PRODUCT",
            code=codigo_producto,
            name="Producto de prueba",
            created_by=mundo.admin_id,
        )
        db.add(item)
        db.flush()
        receipt = GoodsReceipt(
            company_id=mundo.company_id,
            code=receipt_code,
            order_id=order_id,
            warehouse_id=_almacen(mundo, mundo.company_id),
            status="ACCEPTED",
            quality_status="APPROVED",
        )
        db.add(receipt)
        db.flush()
        db.add(
            CostLayer(
                company_id=mundo.company_id,
                product_id=item.id,
                warehouse_id=receipt.warehouse_id,
                receipt_ref=f"RECEIPT:{receipt.id}",
                quantity_in=Decimal("10"),
                quantity_remaining=Decimal("4"),
                unit_cost=Decimal("12.50"),
                currency="USD",
                landed_cost=Decimal("0"),
            )
        )
        db.commit()

    cost = mundo.client.get(f"{API}/importaciones/{file_id}/costs", headers=cabeceras)
    assert cost.status_code == 200, cost.text
    rc = cost.json()
    assert rc["layers"][0]["receipt_code"] == receipt_code
    assert "RECEIPT:" not in rc["layers"][0]["receipt_code"]
    assert rc["layers"][0]["product_name"] == "Producto de prueba"
    assert rc["layers"][0]["quantity_in"] == "10"
    assert rc["layers"][0]["quantity_remaining"] == "4"
    assert rc["layers"][0]["partially_consumed"] is True
    assert rc["layers"][0]["landed_cost"] == "0.00"
    assert rc["goods_totals"] == [{"currency": "USD", "amount": "125.00"}]
    assert rc["application"]["status"] == "DISTRIBUTION_NOT_AVAILABLE"
    assert "pending_decisions" not in rc["application"]
    assert "allocation" not in rc
    assert "applied_at" not in rc

    audit = mundo.client.get(f"{API}/importaciones/{file_id}/audit", headers=cabeceras)
    assert audit.status_code == 200, audit.text
    labels = [i["action_label"] for i in audit.json()["items"]]
    assert "Gasto de importación registrado" in labels
    assert "Gasto de importación anulado" in labels


def test_negativos(mundo, reloj_mfa, rol_completo, rol_solo_lectura):
    cabeceras, file_id, proveedor_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    docs = mundo.client.get(f"{API}/importaciones/{file_id}", headers=cabeceras).json()["documents"]
    import_document_id = docs[0]["id"]

    with mundo.factory() as db:
        currency = Currency(
            company_id=mundo.company_id,
            code="GBP",
            name="Libra esterlina",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(currency)

        otra = Company(
            tenant_id=mundo.tenant_id,
            code=f"OTRA-{uuid4().hex[:6]}",
            legal_name="Otra Empresa",
            rif=f"J-{uuid4().hex[:8]}",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(otra)
        db.flush()
        party_otra = Party(
            company_id=otra.id,
            code=f"P-{uuid4().hex[:6]}",
            name="Proveedor Otra",
            status="ACTIVE",
            created_by=mundo.admin_id,
        )
        db.add(party_otra)
        db.flush()
        invoice_otra = SupplierInvoice(
            company_id=otra.id,
            supplier_id=party_otra.id,
            invoice_number=f"INV-{uuid4().hex[:8]}",
            issue_date=date.today(),
            currency="VED",
            total=Decimal("100.00"),
            tax_total=Decimal("0"),
            status="VALIDATED",
            created_by=mundo.admin_id,
        )
        db.add(invoice_otra)
        db.commit()
        supplier_otro_id = party_otra.id
        invoice_otra_id = invoice_otra.id

    antes = mundo.client.get(f"{API}/importaciones/{file_id}/costs", headers=cabeceras).json()["totals"]["count"]

    r = _gasto(mundo, cabeceras, file_id, kind="DIRECT_IMPORT_EXPENSE", supplier_id=supplier_otro_id)
    assert r.status_code == 404
    assert r.json()["code"] == "IMPORT_EXPENSE_PARTY_NOT_FOUND"
    assert mundo.client.get(f"{API}/importaciones/{file_id}/costs", headers=cabeceras).json()["totals"]["count"] == antes

    r = _gasto(mundo, cabeceras, file_id, kind="LINKED_SUPPLIER_INVOICE", supplier_invoice_id=invoice_otra_id, amount="10.00")
    assert r.status_code == 404
    assert r.json()["code"] == "IMPORT_EXPENSE_INVOICE_NOT_FOUND"
    assert mundo.client.get(f"{API}/importaciones/{file_id}/costs", headers=cabeceras).json()["totals"]["count"] == antes

    otro_file = _crear_expediente(mundo, cabeceras, proveedor_id)
    r = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="DIRECT_IMPORT_EXPENSE",
        import_document_id=otro_file["documents"][0]["id"] if otro_file.get("documents") else "00000000-0000-0000-0000-000000000000",
        supplier_id=proveedor_id,
    )
    assert r.status_code == 404
    assert r.json()["code"] == "IMPORT_DOCUMENT_NOT_FOUND"

    r = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="DIRECT_IMPORT_EXPENSE",
        currency="GBP",
        amount="10.00",
        import_document_id=import_document_id,
        supplier_id=proveedor_id,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "RATE_NOT_AVAILABLE"
    assert mundo.client.get(f"{API}/importaciones/{file_id}/costs", headers=cabeceras).json()["totals"]["count"] == antes

    r = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="DIRECT_IMPORT_EXPENSE",
        currency="XXX",
        amount="10.00",
        import_document_id=import_document_id,
        supplier_id=proveedor_id,
    )
    assert r.status_code == 422
    assert r.json()["code"] == "IMPORT_EXPENSE_CURRENCY_UNKNOWN"

    solo_lectura = _operador(mundo, reloj_mfa, rol_solo_lectura)
    assert mundo.client.get(f"{API}/importaciones/{file_id}", headers=solo_lectura).status_code == 200
    r = _gasto(mundo, solo_lectura, file_id, kind="DIRECT_IMPORT_EXPENSE", supplier_id=proveedor_id)
    assert r.status_code == 403

    _tasa(mundo, date(2024, 12, 1), "USD", "36.125")
    g = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="DIRECT_IMPORT_EXPENSE",
        currency="USD",
        amount="10.00",
        import_document_id=import_document_id,
        supplier_id=proveedor_id,
    )
    assert g.status_code == 200, g.text
    gasto = g.json()["expenses"][0]
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{gasto['id']}/void",
        json={"reason": "viejo", "version": gasto["version"] - 1},
        headers=cabeceras,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "IMPORT_EXPENSE_STALE"

    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{gasto['id']}/void",
        json={"reason": "primera", "version": gasto["version"]},
        headers=cabeceras,
    )
    assert r.status_code == 200, r.text
    r = mundo.client.post(
        f"{API}/importaciones/{file_id}/expenses/{gasto['id']}/void",
        json={"reason": "segunda", "version": r.json()["expenses"][0]["version"]},
        headers=cabeceras,
    )
    assert r.status_code == 409

    with mundo.factory() as db:
        invoice = SupplierInvoice(
            company_id=mundo.company_id,
            supplier_id=proveedor_id,
            invoice_number=f"INV-{uuid4().hex[:8]}",
            issue_date=date.today(),
            currency="VED",
            total=Decimal("20.00"),
            tax_total=Decimal("0"),
            status="VALIDATED",
            created_by=mundo.admin_id,
        )
        db.add(invoice)
        db.flush()
        invoice_id = invoice.id
        invoice_number = invoice.invoice_number
        db.commit()

    g = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="LINKED_SUPPLIER_INVOICE",
        supplier_invoice_id=invoice_id,
        amount="15.00",
        expense_date=date.today().isoformat(),
        import_document_id=import_document_id,
    )
    assert g.status_code == 200, g.text
    rj = next(e for e in g.json()["expenses"] if e["invoice_number"] == invoice_number)
    assert rj["reference"] == invoice_number
    assert rj["invoice_number"] == invoice_number

    r = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="LINKED_SUPPLIER_INVOICE",
        supplier_invoice_id=invoice_id,
        amount="10.00",
        expense_date=date.today().isoformat(),
        import_document_id=import_document_id,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "IMPORT_EXPENSE_EXCEEDS_INVOICE"
    assert mundo.client.get(f"{API}/importaciones/{file_id}/costs", headers=cabeceras).json()["totals"]["count"] == 1

    cand = mundo.client.get(f"{API}/importaciones/{file_id}/expense-invoice-candidates", headers=cabeceras)
    assert cand.status_code == 200, cand.text
    candidatos = cand.json()["items"]
    factura = next(c for c in candidatos if c["id"] == invoice_id)
    assert factura["available"] == "5.00"

    with mundo.factory() as db:
        db.get(SupplierInvoice, invoice_id).status = "DRAFT"
        db.commit()
    r = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="LINKED_SUPPLIER_INVOICE",
        supplier_invoice_id=invoice_id,
        amount="1.00",
        expense_date=date.today().isoformat(),
        import_document_id=import_document_id,
    )
    assert r.status_code == 409
    assert r.json()["code"] == "IMPORT_EXPENSE_INVOICE_INVALID_STATE"

    recien = _crear_expediente(mundo, cabeceras, proveedor_id)
    r = _gasto(mundo, cabeceras, recien["id"], kind="DIRECT_IMPORT_EXPENSE", supplier_id=proveedor_id)
    assert r.status_code == 409
    assert r.json()["code"] == "IMPORT_INVALID_STATE"

    r = _gasto(
        mundo,
        cabeceras,
        file_id,
        kind="DIRECT_IMPORT_EXPENSE",
        amount="10.001",
        import_document_id=import_document_id,
        supplier_id=proveedor_id,
    )
    assert r.status_code == 422
