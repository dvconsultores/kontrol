"""Modelos de compras y cuentas por pagar (004, data-model.md).

Ciclo: requisición → cotización → orden → recepción (invoca 003) → factura
del proveedor → conciliación triple → devolución/nota → CxP (open items,
pagos, aplicaciones, anticipos, retenciones, aging).

Invariantes (Constitución P4/P5/P8, DOC-01 §5, DOC-03 §12):
- Facturas postadas, pagos aprobados y retenciones son inmutables; corrección
  mediante reverso/nota vinculada.
- Los saldos de CxP se calculan desde documentos y aplicaciones; nunca se editan.
- Snapshot por línea (producto, precio, impuesto, tasa).
- Reglas de aprobación y retención versionadas; prohibido hardcodear (P8).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CodeMixin, CreatedByMixin, TimestampMixin, UUIDMixin


# --------------------------------------------------------------------------- #
# Requisición
# --------------------------------------------------------------------------- #
class PurchaseRequisition(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "purchase_requisitions"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    requester_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cost_center_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    need_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    approval_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)


class RequisitionLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "purchase_requisition_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "requisition_id → purchase_requisitions"
    __table_args__ = (Index("ix_purchase_requisition_lines_uom_id", "uom_id"),)

    requisition_id: Mapped[str] = mapped_column(ForeignKey("purchase_requisitions.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# Cotización
# --------------------------------------------------------------------------- #

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
class SupplierQuote(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "supplier_quotes"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    validity_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class QuoteLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "supplier_quote_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "quote_id → supplier_quotes"
    __table_args__ = (Index("ix_supplier_quote_lines_uom_id", "uom_id"),)

    quote_id: Mapped[str] = mapped_column(ForeignKey("supplier_quotes.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    delivery_days: Mapped[int | None] = mapped_column(nullable=True)
    tax_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)


# --------------------------------------------------------------------------- #
# Orden de compra
# --------------------------------------------------------------------------- #

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
class PurchaseOrder(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "purchase_orders"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    approval_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)


class PurchaseOrderLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "purchase_order_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "order_id → purchase_orders"
    __table_args__ = (Index("ix_purchase_order_lines_uom_id", "uom_id"),)

    order_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity_ordered: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0.0)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    discount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    tax_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    needs_inventory: Mapped[bool] = mapped_column(nullable=False, default=True)
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)  # copia histórica JSON (P4/P8)


# --------------------------------------------------------------------------- #
# Recepción (invoca 003)
# --------------------------------------------------------------------------- #

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity_ordered: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity_received: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
class GoodsReceipt(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "goods_receipts"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        CheckConstraint(
            "(packages_declared IS NULL OR packages_declared >= 0) "
            "AND (packages_received IS NULL OR packages_received >= 0)",
            name="packages_nonneg"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    order_id: Mapped[str] = mapped_column(ForeignKey("purchase_orders.id"), nullable=False, index=True)
    warehouse_id: Mapped[str] = mapped_column(ForeignKey("warehouses.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    #: Veredicto de conformidad de la etapa 7 del DOCX. No se añade un segundo
    #: campo para la misma pregunta: `PENDING → APPROVED | REJECTED` **es** «¿la
    #: recepción es conforme?», y lo que faltaba no era el veredicto sino la
    #: inspección que lo sostiene (etapas 4, 5 y 6).
    quality_status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")

    # --- Etapa 1: confirmar arribo. El instante en que la mercancía llegó no se
    # reconstruye después de que el camión se va (`P23`).
    arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrival_confirmed_by: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # --- Etapa 2: programar descarga y recepción ---
    unloading_scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Etapa 4: comparar lo recibido contra las cuatro fuentes del DOCX. Se
    # guarda la referencia **y** el resultado: saber que se comparó y no contra
    # qué deja la comparación sin valor probatorio.
    packing_list_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    supplier_invoice_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    packing_list_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    supplier_invoice_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    order_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    documentation_match: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    # --- Etapa 5: inspección visual inicial ---
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inspected_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    inspection_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Etapa 6: cantidad de bultos, declarados y contados ---
    packages_declared: Mapped[int | None] = mapped_column(Integer, nullable=True)
    packages_received: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Etapa 11: acta o registro de recepción cuando es conforme ---
    record_issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    record_issued_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class GoodsReceiptLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "goods_receipt_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "receipt_id → goods_receipts"
    __table_args__ = (
        Index("ix_goods_receipt_lines_uom_id", "uom_id"),
        CheckConstraint("damaged_quantity IS NULL OR damaged_quantity >= 0", name="damage_nonneg"),
    )

    receipt_id: Mapped[str] = mapped_column(ForeignKey("goods_receipts.id"), nullable=False, index=True)
    order_line_id: Mapped[str] = mapped_column(ForeignKey("purchase_order_lines.id"), nullable=False)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity_received: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    quantity_accepted: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0.0)
    quantity_rejected: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0.0)
    lot_id: Mapped[str | None] = mapped_column(ForeignKey("inventory_lots.id"), nullable=True)
    lot_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    serials: Mapped[str | None] = mapped_column(Text, nullable=True)  # seriales separados por coma
    quality: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")

    # --- Etapa 6: la observación física, que es de 019; la incidencia que se
    # derive de ella es de 020. Se separan a propósito: lo observado en el muelle
    # no puede depender de que alguien abra después un expediente.
    physical_condition: Mapped[str | None] = mapped_column(String(24), nullable=True)  # BUENO/DAÑADO/PARCIAL
    damaged_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    damage_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    identification_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    reference_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    #: Exceso sobre lo que faltaba por recibir de la línea de orden, en unidad
    #: base y congelado en el momento de recibir. El DOCX manda **registrar** el
    #: sobrante (etapa 8); tratarlo es de la Spec 020.
    overage_base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)


# --------------------------------------------------------------------------- #
# Factura del proveedor y conciliación triple
# --------------------------------------------------------------------------- #

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity_received: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity_accepted: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity_rejected: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
#: Tipos de incidencia. Son los cinco subelementos literales de la etapa 8 del
#: proceso: «Si existen diferencias, registrar: faltantes; sobrantes; daños;
#: referencias incorrectas; diferencias documentales». Ni uno más.
INCIDENT_TYPES = ("FALTANTE", "SOBRANTE", "DANO", "REFERENCIA_INCORRECTA", "DIFERENCIA_DOCUMENTAL")

#: El único que no es de mercancía: afecta al documento, no a una línea.
INCIDENT_TYPE_DOCUMENTAL = "DIFERENCIA_DOCUMENTAL"

#: Tratamientos del §3 del proceso: «Determinar tratamiento: ajuste autorizado;
#: reclamo al proveedor; investigación interna; mercancía en cuarentena».
INCIDENT_RESOLUTIONS = ("AJUSTE_AUTORIZADO", "RECLAMO_PROVEEDOR", "INVESTIGACION_INTERNA", "CUARENTENA")

#: El control crítico 115 del proceso es «Autorización de ajustes»: el único
#: tratamiento que exige pasar por el motor de aprobaciones.
INCIDENT_RESOLUTION_APPROVED = "AJUSTE_AUTORIZADO"

#: Estados. El proceso describe acciones, no estados: cada nombre corresponde a
#: una palabra del documento (registrar, escalar, autorización, tratamiento).
INCIDENT_STATUSES = ("REGISTRADA", "ESCALADA", "PENDIENTE_AUTORIZACION", "RESUELTA", "ANULADA")


class ReceiptIncident(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    """Incidencia de recepción (Spec 020, etapas 8, 9 y 10 del proceso).

    Formaliza como excepción operativa un hecho que la Spec 019 ya observó en el
    muelle. **No repite el hecho**: apunta a la línea de recepción, que es donde
    viven el producto, las cantidades, la unidad, la presentación, el factor
    congelado, el estado físico y el daño observado.

    Tampoco ejecuta el tratamiento: lo registra. Confirmar el inventario y
    escribir el estado de la mercancía es de la Spec 021, que además espera una
    capacidad de la 023 que este ciclo no toca.
    """

    __tablename__ = "receipt_incidents"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        Index("ix_receipt_incidents_receipt", "receipt_id"),
        Index("ix_receipt_incidents_line_type", "receipt_line_id", "incident_type"),
        UniqueConstraint("company_id", "code", name="uq_receipt_incidents_company_code"),
        CheckConstraint(
            "incident_type IN ('FALTANTE', 'SOBRANTE', 'DANO', 'REFERENCIA_INCORRECTA', "
            "'DIFERENCIA_DOCUMENTAL')", name="type"),
        CheckConstraint(
            "status IN ('REGISTRADA', 'ESCALADA', 'PENDIENTE_AUTORIZACION', 'RESUELTA', 'ANULADA')",
            name="status"),
        CheckConstraint(
            "resolution IS NULL OR resolution IN ('AJUSTE_AUTORIZADO', 'RECLAMO_PROVEEDOR', "
            "'INVESTIGACION_INTERNA', 'CUARENTENA')", name="resolution"),
        # Una diferencia documental es del documento: no tiene línea ni cantidad.
        # Las otras cuatro son de mercancía: exigen ambas. La base lo impone
        # porque es la única forma de que no existan filas a medio camino.
        CheckConstraint(
            "(incident_type = 'DIFERENCIA_DOCUMENTAL' "
            " AND receipt_line_id IS NULL AND affected_base_quantity IS NULL) "
            "OR (incident_type <> 'DIFERENCIA_DOCUMENTAL' "
            " AND receipt_line_id IS NOT NULL AND affected_base_quantity IS NOT NULL)",
            name="line_and_quantity_by_type"),
        CheckConstraint("affected_base_quantity IS NULL OR affected_base_quantity > 0",
                        name="quantity_positive"),
        # Resuelta sin tratamiento sería una resolución que no dice qué se
        # decidió, que es justo lo que el contrato prohíbe.
        CheckConstraint("status <> 'RESUELTA' OR resolution IS NOT NULL", name="resolved_has_resolution"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    receipt_id: Mapped[str] = mapped_column(ForeignKey("goods_receipts.id"), nullable=False)
    #: Nula solo para la diferencia documental (ver restricción de arriba).
    receipt_line_id: Mapped[str | None] = mapped_column(
        ForeignKey("goods_receipt_lines.id"), nullable=True)
    incident_type: Mapped[str] = mapped_column(String(32), nullable=False)
    #: En unidad base, tomada del snapshot de la línea. No se recalcula con el
    #: maestro de presentaciones vigente: eso reinterpretaría una recepción
    #: histórica.
    affected_base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    #: Información **complementaria** de la incidencia. El hecho físico vive en
    #: la línea de recepción; esto no lo sustituye ni lo copia.
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="REGISTRADA",
                                        server_default="REGISTRADA")

    # --- Etapa 10: escalar la novedad a Compras ---
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    escalation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Tratamiento (§3): se registra aquí y lo ejecuta la Spec 021 ---
    resolution: Mapped[str | None] = mapped_column(String(32), nullable=True)
    resolution_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    #: Solicitud del motor único de aprobaciones cuando el tratamiento es un
    #: ajuste (control crítico 115). No hay motor local.
    approval_request_id: Mapped[str | None] = mapped_column(
        ForeignKey("approval_requests.id"), nullable=True)
    cancelled_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class SupplierInvoice(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "supplier_invoices"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "supplier_id", "invoice_number", "control_number",
                         name="uq_supplier_invoices_company_supplier_invoice_control"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    invoice_number: Mapped[str] = mapped_column(String(120), nullable=False)  # texto
    control_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    issue_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    tax_total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    reversed_by_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)


class SupplierInvoiceLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "supplier_invoice_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "invoice_id → supplier_invoices"
    __table_args__ = (Index("ix_supplier_invoice_lines_uom_id", "uom_id"),)

    invoice_id: Mapped[str] = mapped_column(ForeignKey("supplier_invoices.id"), nullable=False, index=True)
    order_line_id: Mapped[str | None] = mapped_column(ForeignKey("purchase_order_lines.id"), nullable=True)
    receipt_line_id: Mapped[str | None] = mapped_column(ForeignKey("goods_receipt_lines.id"), nullable=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    tax_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    total: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    uom_symbol_snapshot: Mapped[str | None] = mapped_column(String(16), nullable=True)
    presentation_label_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
class TripleMatch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "triple_matches"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("supplier_invoices.id"), nullable=False, index=True)
    order_line_id: Mapped[str | None] = mapped_column(ForeignKey("purchase_order_lines.id"), nullable=True)
    receipt_line_id: Mapped[str | None] = mapped_column(ForeignKey("goods_receipt_lines.id"), nullable=True)
    invoice_line_id: Mapped[str | None] = mapped_column(ForeignKey("supplier_invoice_lines.id"), nullable=True)
    variance_qty: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False, default=0.0)
    variance_price: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    variance_tax: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    resolution: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


# --------------------------------------------------------------------------- #
# Devoluciones y notas de crédito del proveedor
# --------------------------------------------------------------------------- #
class PurchaseReturn(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, Base):
    __tablename__ = "purchase_returns"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source_document: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    condition: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFECTUOSO")
    inventory_destination: Mapped[str] = mapped_column(String(32), nullable=False, default="CUARENTENA")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


class PurchaseReturnLine(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "purchase_return_lines"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "return_id → purchase_returns"
    __table_args__ = (Index("ix_purchase_return_lines_uom_id", "uom_id"),)

    return_id: Mapped[str] = mapped_column(ForeignKey("purchase_returns.id"), nullable=False, index=True)
    product_id: Mapped[str] = mapped_column(ForeignKey("catalog_items.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    condition: Mapped[str] = mapped_column(String(32), nullable=False, default="DEFECTUOSO")

    # --- Semántica de unidad (Spec 011, R-D0-09-1) ---
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    conversion_factor_snapshot: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    base_quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    uom_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
class SupplierCreditNote(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "supplier_credit_notes"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    invoice_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    number: Mapped[str] = mapped_column(String(120), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    applied: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")


# --------------------------------------------------------------------------- #
# CxP — open items, pagos, aplicaciones, anticipos, programación
# --------------------------------------------------------------------------- #
class OpenItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ap_open_items"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    source_document: Mapped[str | None] = mapped_column(String(200), nullable=True)
    item_type: Mapped[str] = mapped_column(String(16), nullable=False, default="PAYABLE")  # PAYABLE / CREDIT
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    original: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    applied: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="OPEN")  # OPEN / CLOSED


class Payment(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "ap_payments"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False, default="OUT")
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    applied: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    approver_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)


class PaymentInstrument(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ap_payment_instruments"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "payment_id → ap_payments"

    payment_id: Mapped[str] = mapped_column(ForeignKey("ap_payments.id"), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(32), nullable=False)
    account: Mapped[str | None] = mapped_column(String(120), nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    rate: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    value_date: Mapped[date | None] = mapped_column(Date, nullable=True)


class Application(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "ap_applications"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # PAYMENT/ADVANCE/CREDIT/WITHHOLDING
    source_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_open_item_id: Mapped[str] = mapped_column(ForeignKey("ap_open_items.id"), nullable=False, index=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    rate: Mapped[float | None] = mapped_column(Numeric(14, 6), nullable=True)
    date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="APPLIED")


class Advance(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "ap_advances"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    direction: Mapped[str] = mapped_column(String(8), nullable=False, default="OUT")
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="VED")
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    available: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")


class PaymentSchedule(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "ap_payment_schedules"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")


# --------------------------------------------------------------------------- #
# Retención (estructura referida a reglas versionadas; motor fiscal en 007)
# --------------------------------------------------------------------------- #
class Withholding(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "ap_withholdings"
    __scope__ = Scope.COMPANY

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    source_event: Mapped[str | None] = mapped_column(String(200), nullable=True)
    tax_type: Mapped[str] = mapped_column(String(16), nullable=False)  # IVA / ISLR
    rule_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)  # referencia a regla versionada
    base: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    rate_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False, default=0.0)
    period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    certificate: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="CALCULADA")
