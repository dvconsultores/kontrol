# ruff: noqa: E402, F811, F401, I001
import hashlib
import os
import re
import threading
from uuid import uuid4

import pytest
from sqlalchemy import func, select

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
from app.modules.documents.models import Document, DocumentLink, DocumentType
from app.modules.identity_access.models import User
from app.modules.imports import difference_report
from app.modules.imports.models import (
    ImportDifferenceReport,
    ImportFile,
)
from app.modules.imports.service import get_file
from app.modules.master_data.models import CatalogItem, Party, UnitOfMeasure
from app.modules.organization.models import Company
from app.modules.purchasing import service as purchasing_service
from app.modules.purchasing.models import (
    GoodsReceipt,
    GoodsReceiptLine,
    PurchaseOrder,
    PurchaseOrderLine,
)

pytest_plugins = ["mfa_apoyo"]

API = "/api/v1"


def _base_product(mundo, db, *, code=None, name=None):
    unit = UnitOfMeasure(
        company_id=mundo.company_id,
        code=f"U-{uuid4().hex[:8]}",
        name=f"unidad-{uuid4().hex[:8]}",
        symbol=f"u-{uuid4().hex[:6]}",
        decimals=0,
        dimension="CANTIDAD",
        created_by=mundo.admin_id,
    )
    db.add(unit)
    db.flush()

    product = CatalogItem(
        company_id=mundo.company_id,
        item_type="PRODUCT",
        code=code or f"PROD-{uuid4().hex[:8]}",
        name=name or f"producto-{uuid4().hex[:8]}",
        base_unit_id=unit.id,
        created_by=mundo.admin_id,
        status="ACTIVE",
    )
    db.add(product)
    db.flush()
    return product, unit


def _crear_segundo_expediente_despachado(mundo, reloj_mfa, rol_completo):
    """Crea un segundo expediente propio con su propia orden y recepción."""
    cab, file_id, _supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    warehouse_id = _almacen(mundo, mundo.company_id)

    with mundo.factory() as db:
        file = db.get(ImportFile, file_id)
        product, _unit = _base_product(mundo, db)

        order = db.get(PurchaseOrder, file.order_id)
        pol = PurchaseOrderLine(
            order_id=order.id,
            product_id=product.id,
            quantity_ordered=10,
            unit_price=1,
        )
        db.add(pol)
        db.flush()

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

        line = GoodsReceiptLine(
            receipt_id=receipt.id,
            order_line_id=pol.id,
            product_id=product.id,
            quantity_received=10,
            quantity_accepted=10,
            quantity_rejected=0,
            counted_base_quantity=10,
            damaged_quantity=0,
            overage_base_quantity=0,
            count_difference_kinds=None,
            physical_condition="BUENO",
        )
        db.add(line)
        db.commit()

        return cab, file_id, receipt.id, line.id


def _hasta_diferencias(
    mundo, reloj_mfa, rol_completo, con_diferencia_observada=True
):
    cab, file_id, supplier_id = _hasta_despachado(mundo, reloj_mfa, rol_completo)
    warehouse_id = _almacen(mundo, mundo.company_id)

    with mundo.factory() as db:
        file = db.get(ImportFile, file_id)

        product1, _unit1 = _base_product(mundo, db)
        product2, _unit2 = _base_product(mundo, db)

        order = db.get(PurchaseOrder, file.order_id)

        pol1 = PurchaseOrderLine(
            order_id=order.id,
            product_id=product1.id,
            quantity_ordered=10,
            unit_price=1,
        )
        db.add(pol1)
        db.flush()

        pol2 = PurchaseOrderLine(
            order_id=order.id,
            product_id=product2.id,
            quantity_ordered=10,
            unit_price=1,
        )
        db.add(pol2)
        db.flush()

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

        if con_diferencia_observada:
            line1 = GoodsReceiptLine(
                receipt_id=receipt.id,
                order_line_id=pol1.id,
                product_id=product1.id,
                quantity_received=10,
                quantity_accepted=8,
                quantity_rejected=2,
                counted_base_quantity=8,
                damaged_quantity=0,
                overage_base_quantity=0,
                count_difference_kinds="CANTIDAD",
                physical_condition="BUENO",
            )
        else:
            line1 = GoodsReceiptLine(
                receipt_id=receipt.id,
                order_line_id=pol1.id,
                product_id=product1.id,
                quantity_received=10,
                quantity_accepted=10,
                quantity_rejected=0,
                counted_base_quantity=10,
                damaged_quantity=0,
                overage_base_quantity=0,
                count_difference_kinds=None,
                physical_condition="BUENO",
            )
        db.add(line1)
        db.flush()

        line2 = GoodsReceiptLine(
            receipt_id=receipt.id,
            order_line_id=pol2.id,
            product_id=product2.id,
            quantity_received=10,
            quantity_accepted=10,
            quantity_rejected=0,
            counted_base_quantity=10,
            damaged_quantity=0,
            overage_base_quantity=0,
            count_difference_kinds=None,
            physical_condition="BUENO",
        )
        db.add(line2)
        db.flush()

        db.commit()
        return (
            cab,
            file_id,
            supplier_id,
            receipt.id,
            product1.id,
            line1.id,
            product2.id,
            line2.id,
        )


def _registrar_incidencia(
    mundo,
    receipt_id,
    line_id,
    incident_type="FALTANTE",
    quantity=1,
):
    code = f"INC-{uuid4().hex[:8]}"
    with mundo.factory() as db:
        inc = purchasing_service.registrar_incidencia(
            db,
            company_id=mundo.company_id,
            receipt_id=receipt_id,
            code=code,
            incident_type=incident_type,
            receipt_line_id=line_id,
            affected_base_quantity=quantity,
            description=f"incidencia {incident_type}",
            actor=mundo.admin_id,
        )
        db.commit()
        db.refresh(inc)
        return str(inc.id)


def _emitir(mundo, cab, file_id, receipt_id, snapshot_hash=None):
    body = {}
    if snapshot_hash is not None:
        body["expected_snapshot_hash"] = snapshot_hash
    return mundo.client.post(
        f"{API}/importaciones/{file_id}/receipts/{receipt_id}/difference-report",
        json=body,
        headers=cab,
    )


def _estado(mundo, cab, file_id, receipt_id):
    return mundo.client.get(
        f"{API}/importaciones/{file_id}/receipts/{receipt_id}/difference-report",
        headers=cab,
    )


def _detalle(mundo, cab, file_id, report_id):
    return mundo.client.get(
        f"{API}/importaciones/{file_id}/difference-reports/{report_id}",
        headers=cab,
    )


def _pdf(mundo, cab, file_id, report_id, inline=False):
    return mundo.client.get(
        f"{API}/importaciones/{file_id}/difference-reports/{report_id}/pdf",
        params={"inline": "true" if inline else "false"},
        headers=cab,
    )


def _contar_reportes(db, receipt_id):
    return db.scalar(
        select(func.count())
        .select_from(ImportDifferenceReport)
        .where(ImportDifferenceReport.receipt_id == receipt_id)
    )


def _eventos_descarga(db, file_id, report_id):
    eventos = db.scalars(
        select(AuditEvent).where(
            AuditEvent.action == "IMPORT_DIFFERENCE_REPORT_DOWNLOADED",
            AuditEvent.entity_type == "ImportFile",
            AuditEvent.entity_id == file_id,
        )
    ).all()
    return [e for e in eventos if e.after.get("report_id") == report_id]


def test_a_emision_feliz(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)

    r = _estado(mundo, cab, file_id, receipt_id)
    assert r.status_code == 200, r.text
    state = r.json()
    assert state["state"] == "DIFFERENCES_WITHOUT_REPORT"
    assert state["has_differences"] is True
    assert len(state["lines"]) == 1
    assert len(state["incidents"]) == 1

    r = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"])
    assert r.status_code == 200, r.text
    detail = r.json()
    assert detail["revision"] == 1
    assert re.fullmatch(r"DIF-\d{6}-R1", detail["reference"]) is not None
    assert len(detail["lines"]) == 1
    assert detail["lines"][0]["receipt_line_id"] == line1_id
    assert detail["lines"][0]["difference_kinds"] == "CANTIDAD"
    assert detail["incidents"][0]["resolution"] is None
    assert detail["incidents"][0]["incident_type"] == "FALTANTE"

    with mundo.factory() as db:
        report = db.get(ImportDifferenceReport, detail["id"])
        issued_user = db.get(User, report.issued_by)
    assert issued_user is not None
    assert detail["issued_by_name"] == issued_user.username
    uuid_regex = re.compile(
        r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    )
    assert uuid_regex.fullmatch(detail["issued_by_name"]) is None

    r = _estado(mundo, cab, file_id, receipt_id)
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "REPORT_ISSUED"


def test_b_pdf(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)

    state = _estado(mundo, cab, file_id, receipt_id).json()
    detail = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"]).json()
    report_id = detail["id"]

    r = _pdf(mundo, cab, file_id, report_id, inline=False)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    body = r.content
    assert body.startswith(b"%PDF-")
    assert b"%%EOF" in body
    assert hashlib.sha256(body).hexdigest() == detail["file_sha256"]

    r_inline = _pdf(mundo, cab, file_id, report_id, inline=True)
    assert r_inline.status_code == 200, r_inline.text
    assert r_inline.headers["content-disposition"].startswith("inline")
    assert hashlib.sha256(r_inline.content).hexdigest() == detail["file_sha256"]

    with mundo.factory() as db:
        eventos = _eventos_descarga(db, file_id, report_id)
        assert len(eventos) == 2


def test_c_doble_emision(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)

    state = _estado(mundo, cab, file_id, receipt_id).json()
    snapshot = state["current_snapshot_hash"]
    r1 = _emitir(mundo, cab, file_id, receipt_id, snapshot)
    assert r1.status_code == 200, r1.text

    r2 = _emitir(mundo, cab, file_id, receipt_id, snapshot)
    assert r2.status_code == 409, r2.text
    assert r2.json()["code"] == "DIFFERENCE_REPORT_UNCHANGED"

    with mundo.factory() as db:
        assert _contar_reportes(db, receipt_id) == 1


def test_d_revision(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    inc1_id = _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 1)

    state = _estado(mundo, cab, file_id, receipt_id).json()
    r1 = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"]).json()

    # Instantánea inmutable de R1 antes de la revisión
    detalle_r1_antes = _detalle(mundo, cab, file_id, r1["id"]).json()
    filas_r1_antes = {
        "lines": detalle_r1_antes["lines"],
        "incidents": detalle_r1_antes["incidents"],
    }

    inc2_id = _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 1)
    with mundo.factory() as db:
        purchasing_service.escalar_incidencia(
            db,
            company_id=mundo.company_id,
            incident_id=inc1_id,
            notes="revisión",
            actor=mundo.admin_id,
        )
        purchasing_service.resolver_incidencia(
            db,
            company_id=mundo.company_id,
            incident_id=inc2_id,
            resolution="RECLAMO_PROVEEDOR",
            reason="ok",
            actor=mundo.admin_id,
        )
        db.commit()

    r = _estado(mundo, cab, file_id, receipt_id)
    assert r.status_code == 200, r.text
    state2 = r.json()
    assert state2["state"] == "NEW_REVISION_AVAILABLE"

    r_stale = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"])
    assert r_stale.status_code == 409, r_stale.text
    assert r_stale.json()["code"] == "DIFFERENCE_REPORT_STALE"

    r2 = _emitir(mundo, cab, file_id, receipt_id, state2["current_snapshot_hash"])
    assert r2.status_code == 200, r2.text
    detail2 = r2.json()
    assert detail2["revision"] == 2
    assert re.fullmatch(r"DIF-\d{6}-R2", detail2["reference"]) is not None
    assert detail2["supersedes_id"] == r1["id"]
    assert detail2["reference"][:9] == r1["reference"][:9]

    detalle_r1_despues = _detalle(mundo, cab, file_id, r1["id"]).json()
    assert detalle_r1_despues["superseded_by"] == detail2["id"]
    assert detalle_r1_despues["incidents"][0]["resolution"] is None
    assert detalle_r1_despues["lines"] == filas_r1_antes["lines"]
    assert detalle_r1_despues["incidents"] == filas_r1_antes["incidents"]

    with mundo.factory() as db:
        eventos = db.scalars(
            select(AuditEvent).where(
                AuditEvent.action == "IMPORT_DIFFERENCE_REPORT_REISSUED",
                AuditEvent.entity_type == "ImportFile",
                AuditEvent.entity_id == file_id,
            )
        ).all()
        eventos_reemitidos = [
            e for e in eventos if e.after.get("report_id") == detail2["id"]
        ]
        assert len(eventos_reemitidos) == 1

    r_hist = _estado(mundo, cab, file_id, receipt_id)
    assert r_hist.status_code == 200, r_hist.text
    reports = r_hist.json()["reports"]
    assert len(reports) == 2
    assert reports[0]["id"] == detail2["id"]
    assert reports[0]["is_latest"] is True
    assert reports[1]["id"] == r1["id"]
    assert reports[1]["is_latest"] is False


def test_e_sin_diferencias(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )

    # Registra una incidencia y luego anúlala: no debe contar como diferencia.
    inc_id = _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)
    with mundo.factory() as db:
        purchasing_service.anular_incidencia(
            db,
            company_id=mundo.company_id,
            incident_id=inc_id,
            reason="error de registro",
            actor=mundo.admin_id,
        )
        lineas = db.scalars(
            select(GoodsReceiptLine).where(GoodsReceiptLine.receipt_id == receipt_id)
        ).all()
        for line in lineas:
            line.count_difference_kinds = None
            line.damaged_quantity = 0
            line.overage_base_quantity = 0
            line.quantity_accepted = line.quantity_received
            line.quantity_rejected = 0
        db.commit()

    r = _estado(mundo, cab, file_id, receipt_id)
    assert r.status_code == 200, r.text
    state = r.json()
    assert state["state"] == "NO_DIFFERENCES"
    assert state["has_differences"] is False

    r_post = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"])
    assert r_post.status_code == 422, r_post.text
    assert r_post.json()["code"] == "DIFFERENCE_REPORT_NO_DIFFERENCES"

    with mundo.factory() as db:
        assert _contar_reportes(db, receipt_id) == 0


def test_f_diferencia_documental(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, _line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo, con_diferencia_observada=False
    )
    _registrar_incidencia(
        mundo,
        receipt_id,
        None,
        "DIFERENCIA_DOCUMENTAL",
        quantity=None,
    )

    r = _estado(mundo, cab, file_id, receipt_id)
    assert r.status_code == 200, r.text
    state = r.json()
    assert state["has_differences"] is True

    detail = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"]).json()
    assert detail["lines"] == []
    assert len(detail["incidents"]) == 1
    assert detail["incidents"][0]["receipt_line_id"] is None
    assert detail["incidents"][0]["affected_base_quantity"] is None


def test_g_solo_observadas_sin_incidencia(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, _line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    r = _estado(mundo, cab, file_id, receipt_id)
    assert r.status_code == 200, r.text
    state = r.json()
    assert state["has_differences"] is True
    assert state["state"] == "DIFFERENCES_WITHOUT_REPORT"


def test_h_permisos_solo_lectura(mundo, reloj_mfa, rol_completo, rol_solo_lectura):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)

    cab_lectura = _operador(mundo, reloj_mfa, rol_solo_lectura)

    r_estado = _estado(mundo, cab_lectura, file_id, receipt_id)
    assert r_estado.status_code == 200, r_estado.text

    state = r_estado.json()
    detail = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"]).json()

    r_pdf = _pdf(mundo, cab_lectura, file_id, detail["id"], inline=False)
    assert r_pdf.status_code == 200, r_pdf.text

    r_post = _emitir(mundo, cab_lectura, file_id, receipt_id, state["current_snapshot_hash"])
    assert r_post.status_code == 403, r_post.text


def test_i_aislamiento(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)

    state = _estado(mundo, cab, file_id, receipt_id).json()
    r = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"])
    assert r.status_code == 200, r.text

    # Segundo expediente propio, con su propia orden y recepción.
    _cab2, file2_id, receipt2_id, line2_id = _crear_segundo_expediente_despachado(
        mundo, reloj_mfa, rol_completo
    )
    _registrar_incidencia(mundo, receipt2_id, line2_id, "FALTANTE", 2)

    # Recepción del segundo expediente consultada por el primero.
    r_receipt_ajeno = _estado(mundo, cab, file_id, receipt2_id)
    assert r_receipt_ajeno.status_code == 404, r_receipt_ajeno.text
    assert r_receipt_ajeno.json()["code"] == "IMPORT_RECEIPT_NOT_IN_FILE"

    state2 = _estado(mundo, cab, file2_id, receipt2_id).json()
    detail2 = _emitir(mundo, cab, file2_id, receipt2_id, state2["current_snapshot_hash"]).json()

    # Detalle del reporte del segundo expediente por la ruta del primero.
    r_detalle_ajeno = _detalle(mundo, cab, file_id, detail2["id"])
    assert r_detalle_ajeno.status_code == 404, r_detalle_ajeno.text
    assert r_detalle_ajeno.json()["code"] == "IMPORT_DIFFERENCE_REPORT_NOT_FOUND"

    r_pdf_ajeno = _pdf(mundo, cab, file_id, detail2["id"], inline=False)
    assert r_pdf_ajeno.status_code == 404, r_pdf_ajeno.text
    assert r_pdf_ajeno.json()["code"] == "IMPORT_DIFFERENCE_REPORT_NOT_FOUND"

    # Expediente de otra empresa.
    with mundo.factory() as db:
        other_company_id = db.scalar(
            select(Company.id).where(Company.tenant_id == mundo.tenant_b_id)
        )
        proveedor_externo = Party(
            company_id=other_company_id,
            code=f"PROV-{uuid4().hex[:8]}",
            name="Proveedor externo",
            person_type="JURIDICA",
            roles=["SUPPLIER"],
        )
        db.add(proveedor_externo)
        db.flush()
        file_externo = ImportFile(
            company_id=other_company_id,
            code=f"IMP-{uuid4().hex[:12]}",
            supplier_id=str(proveedor_externo.id),
            currency="VED",
            status="NEGOTIATING",
        )
        db.add(file_externo)
        db.commit()
        file_externo_id = file_externo.id

    r_file_otro = _estado(mundo, cab, file_externo_id, receipt_id)
    assert r_file_otro.status_code == 404, r_file_otro.text
    assert r_file_otro.json()["code"] == "IMPORT_NOT_FOUND"


def test_j_evidencia(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    inc_id = _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)

    # Sin evidencia previa: emitir un reporte y comprobar evidencia vacía.
    state = _estado(mundo, cab, file_id, receipt_id).json()
    detail_sin_evidencia = _emitir(
        mundo, cab, file_id, receipt_id, state["current_snapshot_hash"]
    ).json()
    assert detail_sin_evidencia["evidence"] == []
    assert detail_sin_evidencia["evidence_count"] == 0
    incident_code = detail_sin_evidencia["incidents"][0]["code"]

    # Adjuntar evidencia documental a la incidencia.
    with mundo.factory() as db:
        tipo = db.scalar(
            select(DocumentType).where(
                DocumentType.company_id == mundo.company_id,
                DocumentType.code == "RECEIPT-INCIDENT",
            )
        )
        if tipo is None:
            tipo = DocumentType(
                company_id=mundo.company_id,
                code="RECEIPT-INCIDENT",
                name="Evidencia de incidencia",
            )
            db.add(tipo)
            db.flush()

        doc = Document(
            company_id=mundo.company_id,
            document_type_id=tipo.id,
            title="Evidencia faltante",
            status="ACTIVE",
        )
        db.add(doc)
        db.flush()

        link = DocumentLink(
            document_id=str(doc.id),
            company_id=mundo.company_id,
            resource_type="ReceiptIncident",
            resource_id=inc_id,
            role="ATTACHMENT",
        )
        db.add(link)
        db.commit()

    # Con evidencia ya existe una nueva revisión; comprobamos que se incluye.
    state_con_evidencia = _estado(mundo, cab, file_id, receipt_id).json()
    assert state_con_evidencia["state"] == "NEW_REVISION_AVAILABLE"
    detail = _emitir(
        mundo, cab, file_id, receipt_id, state_con_evidencia["current_snapshot_hash"]
    ).json()

    assert detail["evidence_count"] == 1
    assert len(detail["evidence"]) == 1
    ev = detail["evidence"][0]
    assert ev["resource_type"] == "ReceiptIncident"
    assert ev["resource_code"] == incident_code
    assert ev["document_title"] == "Evidencia faltante"
    assert ev["version_number"] is None


def test_k_desde_recepciones(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)

    state = _estado(mundo, cab, file_id, receipt_id).json()
    detail = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"]).json()

    r = mundo.client.get(
        f"{API}/importaciones/receipt-difference-reports/{receipt_id}",
        headers=cab,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["import_file_id"] == file_id
    assert len(data["reports"]) == 1
    assert data["reports"][0]["id"] == detail["id"]
    assert data["reports"][0]["reference"] == detail["reference"]


def test_l_integridad_hash(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)

    state = _estado(mundo, cab, file_id, receipt_id).json()
    detail = _emitir(mundo, cab, file_id, receipt_id, state["current_snapshot_hash"]).json()

    with mundo.factory() as db:
        report = db.get(ImportDifferenceReport, detail["id"])
        report.file_sha256 = "0" * 64
        db.commit()

    r = _pdf(mundo, cab, file_id, detail["id"], inline=False)
    assert r.status_code == 500, r.text
    assert r.json()["code"] == "STORAGE_HASH_MISMATCH"


@pytest.mark.skipif(
    not os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql"),
    reason="Concurrencia solo verificable en PostgreSQL",
)
def test_m_concurrencia(mundo, reloj_mfa, rol_completo):
    cab, file_id, _sup, receipt_id, _p1, line1_id, _p2, _line2_id = _hasta_diferencias(
        mundo, reloj_mfa, rol_completo
    )
    _registrar_incidencia(mundo, receipt_id, line1_id, "FALTANTE", 2)

    state = _estado(mundo, cab, file_id, receipt_id).json()
    snapshot = state["current_snapshot_hash"]

    resultados = []
    lock = threading.Lock()

    def _trabajador():
        with mundo.factory() as db:
            file = get_file(db, mundo.company_id, file_id)
            try:
                report = difference_report.issue_report(
                    db,
                    file=file,
                    receipt_id=receipt_id,
                    expected_snapshot_hash=snapshot,
                    actor_id=mundo.admin_id,
                    tenant_id=mundo.tenant_id,
                )
                db.commit()
                with lock:
                    resultados.append(("ok", report.id))
            except ConflictError as e:
                db.rollback()
                with lock:
                    resultados.append(("conflict", e.code))

    hilos = [threading.Thread(target=_trabajador) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()

    assert len(resultados) == 2
    oks = [r for r in resultados if r[0] == "ok"]
    conflicts = [r for r in resultados if r[0] == "conflict"]
    assert len(oks) == 1
    assert len(conflicts) == 1
    assert conflicts[0][1] in ("DIFFERENCE_REPORT_UNCHANGED", "DIFFERENCE_REPORT_CONCURRENT")

    with mundo.factory() as db:
        assert _contar_reportes(db, receipt_id) == 1
