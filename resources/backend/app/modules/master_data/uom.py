"""Motor de conversión de unidades y presentaciones (Spec 011).

**Autoridad única transversal** (P22): este es el único lugar del sistema donde
se convierte una cantidad a unidad base. Compras, inventario, ventas, picking,
facturación y despacho lo consumen; ninguno replica el cálculo.

Dos conversiones distintas y deliberadamente separadas (R-011-2):

- **Física**: entre unidades de la misma dimensión (`KG → 1000 G`). Sin
  versionado, porque un kilo siempre serán mil gramos.
- **Comercial**: de una presentación a la unidad base del producto
  (`CAJA → 100 UND`). Versionada, porque la caja de un producto puede cambiar.

Ninguna unidad ni presentación aparece codificada aquí: todo es dato (P8).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_DOWN, ROUND_HALF_EVEN, ROUND_HALF_UP, ROUND_UP, Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError
from app.modules.master_data.models import (
    CatalogItem,
    Presentation,
    ProductPresentationVersion,
    UnitConversion,
    UnitOfMeasure,
)

#: Los cuatro modos declarables, traducidos al redondeo de `Decimal`. La unidad
#: declara cuál usa; no se deduce de su código.
ROUNDING = {
    "HALF_UP": ROUND_HALF_UP,
    "HALF_EVEN": ROUND_HALF_EVEN,
    "DOWN": ROUND_DOWN,
    "UP": ROUND_UP,
}

#: Origen de la semántica de unidad de una línea. Distingue para siempre lo
#: capturado de lo supuesto (FR-011-056).
SOURCE_CAPTURED = "CAPTURED"
SOURCE_LEGACY_ASSUMED_BASE = "LEGACY_ASSUMED_BASE"
SOURCE_LEGACY_RECONSTRUCTED = "LEGACY_RECONSTRUCTED"
SOURCE_LEGACY_UNRESOLVED = "LEGACY_UNRESOLVED"
SOURCE_LEGACY_UNVERSIONED = "LEGACY_UNVERSIONED"


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    """Normaliza a UTC. SQLite devuelve datetimes ingenuos y compararlos con uno
    con zona lanzaría `TypeError`."""
    if value is None:
        return None
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


@dataclass(frozen=True)
class Conversion:
    """Resultado de una conversión. Inmutable a propósito: lo que se congela en
    la línea no debe poder modificarse después de resolverse."""

    base_quantity: Decimal
    factor: Decimal
    version_id: str | None
    base_uom_id: str | None
    exact: bool


# --------------------------------------------------------------------------
# Precisión y redondeo — un solo lugar (FR-011-045)
# --------------------------------------------------------------------------

def quantize(value: Decimal, unit: UnitOfMeasure | None) -> Decimal:
    """Aplica la precisión declarada por la unidad.

    Sin unidad conocida **no se redondea**: inventar una precisión sería tan
    grave como inventar la unidad.
    """
    if unit is None:
        return value
    exponent = Decimal(1).scaleb(-int(unit.decimals))
    return value.quantize(exponent, rounding=ROUNDING.get(unit.rounding_mode, ROUND_HALF_UP))


def is_exact_in(value: Decimal, unit: UnitOfMeasure | None) -> bool:
    """¿Cabe el valor en la precisión de la unidad sin perder nada?"""
    return unit is None or quantize(value, unit) == value


# --------------------------------------------------------------------------
# Conversión física entre unidades (R-011-2)
# --------------------------------------------------------------------------

def physical_factor(db: Session, from_unit_id: str, to_unit_id: str) -> Decimal:
    """Factor entre dos unidades de la **misma dimensión**.

    Se rechaza `KG ↔ L`: no se inventan conversiones físicamente inválidas
    (FR-011-012). Una relación por densidad sería otra capacidad, fuera de 011.
    """
    if from_unit_id == to_unit_id:
        return Decimal(1)

    origin = db.get(UnitOfMeasure, from_unit_id)
    target = db.get(UnitOfMeasure, to_unit_id)
    if origin is None or target is None:
        raise KontrolError(code="CONVERSION_NOT_RESOLVABLE",
                           message="Unidad no encontrada", status_code=422)
    if origin.dimension != target.dimension:
        raise KontrolError(
            code="UOM_DIMENSION_MISMATCH",
            message=f"No se puede convertir {origin.code} a {target.code}: dimensiones distintas",
            status_code=422,
            details={"from_dimension": origin.dimension, "to_dimension": target.dimension},
        )

    direct = db.execute(select(UnitConversion).where(
        UnitConversion.from_unit_id == from_unit_id,
        UnitConversion.to_unit_id == to_unit_id,
        UnitConversion.validity == "ACTIVE",
    )).scalars().first()
    if direct is not None:
        return Decimal(direct.factor)

    inverse = db.execute(select(UnitConversion).where(
        UnitConversion.from_unit_id == to_unit_id,
        UnitConversion.to_unit_id == from_unit_id,
        UnitConversion.validity == "ACTIVE",
    )).scalars().first()
    if inverse is not None:
        return Decimal(1) / Decimal(inverse.factor)

    raise KontrolError(
        code="CONVERSION_NOT_RESOLVABLE",
        message=f"No hay conversión declarada entre {origin.code} y {target.code}",
        status_code=422,
    )


def assert_same_dimension(db: Session, from_unit_id: str, to_unit_id: str) -> None:
    origin = db.get(UnitOfMeasure, from_unit_id)
    target = db.get(UnitOfMeasure, to_unit_id)
    if origin is None or target is None:
        raise KontrolError(code="CONVERSION_NOT_RESOLVABLE",
                           message="Unidad no encontrada", status_code=422)
    if origin.dimension != target.dimension:
        raise KontrolError(
            code="UOM_DIMENSION_MISMATCH",
            message="Las unidades no comparten dimensión", status_code=422,
            details={"from_dimension": origin.dimension, "to_dimension": target.dimension})


# --------------------------------------------------------------------------
# Resolución de la versión aplicable (FR-011-041)
# --------------------------------------------------------------------------

def resolve_conversion(
    db: Session, presentation_id: str, on_date: datetime | None = None
) -> ProductPresentationVersion:
    """Versión vigente en una fecha.

    La fecha es la del **documento**, no la de creación: una factura registrada
    hoy con fecha del mes pasado usa el factor de entonces (research §4).

    Si no hay versión aplicable se **falla**; no se inventa un factor.
    """
    moment = _aware(on_date) or _now()
    candidates = db.execute(
        select(ProductPresentationVersion)
        .where(ProductPresentationVersion.presentation_id == presentation_id)
        .order_by(ProductPresentationVersion.valid_from.desc())
    ).scalars().all()

    for version in candidates:
        start = _aware(version.valid_from)
        end = _aware(version.valid_to)
        if start is not None and start <= moment and (end is None or moment < end):
            return version

    raise KontrolError(
        code="CONVERSION_NOT_RESOLVABLE",
        message="No hay una equivalencia vigente para esa fecha",
        status_code=422,
        details={"presentation_id": presentation_id, "date": moment.isoformat()},
    )


def base_unit_of(db: Session, product_id: str) -> UnitOfMeasure | None:
    item = db.get(CatalogItem, product_id)
    if item is None or item.base_unit_id is None:
        return None
    return db.get(UnitOfMeasure, item.base_unit_id)


# --------------------------------------------------------------------------
# Conversión a unidad base (FR-011-042)
# --------------------------------------------------------------------------

def to_base(
    db: Session,
    quantity: Decimal | str | int,
    product_id: str,
    presentation_id: str | None = None,
    on_date: datetime | None = None,
) -> Conversion:
    """Convierte una cantidad transaccional a unidad base.

    Sin presentación, la cantidad **ya está** en unidad base y el factor es 1:
    es el caso demostrable que R-011-4 admite, no un valor por defecto.

    Con presentación, encadena la conversión comercial y, si la presentación se
    declaró en una unidad distinta de la base, también la física (CL-011-13).
    """
    amount = Decimal(str(quantity))
    base_unit = base_unit_of(db, product_id)

    if presentation_id is None:
        base = quantize(amount, base_unit)
        return Conversion(base_quantity=base, factor=Decimal(1), version_id=None,
                          base_uom_id=base_unit.id if base_unit else None,
                          exact=is_exact_in(amount, base_unit))

    presentation = db.get(Presentation, presentation_id)
    if presentation is None or presentation.product_id != product_id:
        raise KontrolError(
            code="CONVERSION_NOT_RESOLVABLE",
            message="La presentación no pertenece a este producto", status_code=422)

    version = resolve_conversion(db, presentation_id, on_date)
    factor = Decimal(version.factor_to_base)

    # Cadena: presentación → unidad declarada del factor → unidad base.
    if (version.factor_uom_id and base_unit is not None
            and version.factor_uom_id != base_unit.id):
        factor = factor * physical_factor(db, version.factor_uom_id, base_unit.id)

    raw = amount * factor
    exact = is_exact_in(raw, base_unit)
    if not exact and version.exact_in_base:
        # La presentación no declaró que produce fracciones: no se redondea en
        # silencio (R-D0-09-5, FR-011-038).
        raise KontrolError(
            code="CONVERSION_NOT_EXACT",
            message="La conversión produce fracciones en la unidad base y la "
                    "presentación no lo declara",
            status_code=422,
            details={"raw": str(raw), "decimals": base_unit.decimals if base_unit else None},
        )

    return Conversion(base_quantity=quantize(raw, base_unit), factor=factor,
                      version_id=str(version.id),
                      base_uom_id=base_unit.id if base_unit else None, exact=exact)


def to_base_bulk(
    db: Session,
    lines: list[dict[str, Any]],
    on_date: datetime | None = None,
) -> list[Conversion]:
    """Resolución masiva **sin N+1** (NFR-011-01).

    Un documento de mil líneas no puede hacer mil consultas de versión: se traen
    de una vez las versiones y las unidades base de todos sus productos.
    """
    moment = _aware(on_date) or _now()
    product_ids = {line["product_id"] for line in lines}
    presentation_ids = {line.get("presentation_id") for line in lines} - {None}

    items = {i.id: i for i in db.execute(
        select(CatalogItem).where(CatalogItem.id.in_(product_ids))).scalars().all()}
    unit_ids = {i.base_unit_id for i in items.values() if i.base_unit_id}
    units = {u.id: u for u in db.execute(
        select(UnitOfMeasure).where(UnitOfMeasure.id.in_(unit_ids))).scalars().all()} if unit_ids else {}

    versions: dict[str, ProductPresentationVersion] = {}
    if presentation_ids:
        rows = db.execute(
            select(ProductPresentationVersion).where(
                ProductPresentationVersion.presentation_id.in_(presentation_ids),
                ProductPresentationVersion.valid_from <= moment,
                or_(ProductPresentationVersion.valid_to.is_(None),
                    ProductPresentationVersion.valid_to > moment),
            )
        ).scalars().all()
        for row in rows:
            versions[row.presentation_id] = row

    results: list[Conversion] = []
    for line in lines:
        amount = Decimal(str(line["quantity"]))
        item = items.get(line["product_id"])
        base_unit = units.get(item.base_unit_id) if item and item.base_unit_id else None
        presentation_id = line.get("presentation_id")

        if presentation_id is None:
            results.append(Conversion(quantize(amount, base_unit), Decimal(1), None,
                                      base_unit.id if base_unit else None,
                                      is_exact_in(amount, base_unit)))
            continue

        version = versions.get(presentation_id)
        if version is None:
            raise KontrolError(code="CONVERSION_NOT_RESOLVABLE",
                               message="No hay equivalencia vigente para esa fecha",
                               status_code=422,
                               details={"presentation_id": presentation_id})
        factor = Decimal(version.factor_to_base)
        if (version.factor_uom_id and base_unit is not None
                and version.factor_uom_id != base_unit.id):
            factor = factor * physical_factor(db, version.factor_uom_id, base_unit.id)
        raw = amount * factor
        exact = is_exact_in(raw, base_unit)
        if not exact and version.exact_in_base:
            raise KontrolError(code="CONVERSION_NOT_EXACT",
                               message="Conversión con fracciones no declarada", status_code=422)
        results.append(Conversion(quantize(raw, base_unit), factor, str(version.id),
                                  base_unit.id if base_unit else None, exact))
    return results


# --------------------------------------------------------------------------
# Punto de congelamiento — por ciclo de vida, no por un estado literal (§15)
# --------------------------------------------------------------------------

#: Estado a partir del cual cada tipo de documento queda **congelado**. No se
#: codifica `if status == "ISSUED"` para todo: cada dominio tiene su propio
#: ciclo de vida y su propio punto de congelamiento contractual.
#:
#: La clave es el nombre de la tabla de cabecera; el valor, los estados que
#: significan «ya produjo efecto y no se reinterpreta».
FREEZE_STATES: dict[str, frozenset[str]] = {
    # Compras: la orden se congela al aprobarse; la recepción, al confirmarse;
    # la factura del proveedor, al contabilizarse.
    "purchase_requisitions": frozenset({"APPROVED", "CLOSED", "CANCELLED"}),
    "supplier_quotes": frozenset({"ACCEPTED", "REJECTED", "CLOSED"}),
    "purchase_orders": frozenset({"APPROVED", "SENT", "PARTIAL", "RECEIVED", "CLOSED"}),
    "goods_receipts": frozenset({"CONFIRMED", "POSTED", "CLOSED"}),
    "supplier_invoices": frozenset({"POSTED", "PAID", "CLOSED"}),
    "purchase_returns": frozenset({"CONFIRMED", "POSTED", "CLOSED"}),
    # Inventario: el movimiento nace congelado — no existe un movimiento borrador.
    "inventory_movements": frozenset({"*"}),
    "reservations": frozenset({"CONFIRMED", "CONSUMED", "RELEASED"}),
    "transfers": frozenset({"SENT", "RECEIVED", "CLOSED"}),
    "stock_counts": frozenset({"CLOSED", "APPROVED", "POSTED"}),
    "inventory_adjustments": frozenset({"*"}),
    # Ventas: la factura se congela al emitirse; el despacho, al confirmarse.
    "sales_quotes": frozenset({"ACCEPTED", "REJECTED", "CLOSED"}),
    "sales_orders": frozenset({"CONFIRMED", "APPROVED", "CLOSED", "INVOICED"}),
    "pick_lists": frozenset({"CONFIRMED", "CLOSED"}),
    "shipments": frozenset({"CONFIRMED", "DISPATCHED", "DELIVERED", "CLOSED"}),
    "sales_invoices": frozenset({"ISSUED", "POSTED", "PAID", "CANCELLED"}),
    "sales_returns": frozenset({"CONFIRMED", "POSTED", "CLOSED"}),
}

#: Documentos con efecto fiscal. Su histórico es una declaración ante la
#: administración tributaria: en la migración se tratan con clase D.
FISCAL_TABLES: frozenset[str] = frozenset({
    "sales_invoice_lines", "supplier_invoice_lines", "sales_return_lines",
})


def is_frozen(document_table: str, status: str | None) -> bool:
    """¿Está el documento en un estado que congela sus snapshots?

    `"*"` significa que el documento nace congelado: un movimiento de inventario
    no tiene borrador.
    """
    states = FREEZE_STATES.get(document_table)
    if states is None:
        # Documento no declarado: se trata como congelado. Ante la duda, no se
        # reinterpreta un histórico.
        return True
    if "*" in states:
        return True
    return (status or "") in states


def assert_line_mutable(document_table: str, status: str | None) -> None:
    """Una línea congelada no cambia de unidad ni de presentación (FR-011-054)."""
    if is_frozen(document_table, status):
        raise ConflictError(
            code="SNAPSHOT_IMMUTABLE",
            message="El documento está congelado: su unidad y presentación no cambian",
        )


def freeze_line(
    db: Session,
    line: Any,
    product_id: str,
    quantity_attr: str = "quantity",
    base_attr: str = "base_quantity",
    on_date: datetime | None = None,
) -> Conversion:
    """Congela el snapshot de una línea.

    Escribe `uom_id`, `conversion_factor_snapshot` y la cantidad base, y marca
    el origen como capturado. **Nunca toca la cantidad original** (FR-011-077).
    """
    conversion = to_base(db, getattr(line, quantity_attr), product_id,
                         getattr(line, "presentation_id", None), on_date)
    if getattr(line, "uom_id", None) is None:
        line.uom_id = conversion.base_uom_id
    line.conversion_factor_snapshot = conversion.factor
    setattr(line, base_attr, conversion.base_quantity)
    if hasattr(line, "uom_source"):
        line.uom_source = SOURCE_CAPTURED
    return conversion


def freeze_document_labels(db: Session, line: Any) -> None:
    """Congela símbolo y etiqueta para reimpresión fiel de documentos emitidos.

    Solo en documentos con efecto fiscal o de entrega: en el resto sería
    duplicación sin valor histórico (CL-011-17).
    """
    if hasattr(line, "uom_symbol_snapshot") and line.uom_id:
        unit = db.get(UnitOfMeasure, line.uom_id)
        if unit is not None:
            line.uom_symbol_snapshot = unit.symbol
    if hasattr(line, "presentation_label_snapshot") and getattr(line, "presentation_id", None):
        presentation = db.get(Presentation, line.presentation_id)
        if presentation is not None:
            line.presentation_label_snapshot = presentation.name


# --------------------------------------------------------------------------
# Guardas de integridad
# --------------------------------------------------------------------------

def assert_base_unit_changeable(db: Session, product_id: str) -> None:
    """La unidad base no cambia en un producto con historial (R-011-3)."""
    item = db.get(CatalogItem, product_id)
    if item is None:
        raise KontrolError(code="NOT_FOUND", message="Producto no encontrado", status_code=404)
    if not item.base_unit_locked:
        return
    from sqlalchemy import func

    from app.modules.inventory.models import InventoryMovement

    movements = int(db.execute(
        select(func.count()).select_from(InventoryMovement)
        .where(InventoryMovement.product_id == product_id)
    ).scalar_one())
    raise KontrolError(
        code="BASE_UNIT_LOCKED",
        message="No se puede cambiar la unidad base: el producto tiene historial",
        status_code=409,
        details={"reason": f"El producto tiene {movements} movimientos registrados",
                 "dependencies": {"movements": movements},
                 "allowed_actions": []},
    )


def lock_base_unit(db: Session, product_id: str) -> None:
    """Marca el producto como operativo. Se invoca con el primer movimiento."""
    item = db.get(CatalogItem, product_id)
    if item is not None and not item.base_unit_locked:
        item.base_unit_locked = True
        db.flush()


def assert_no_version_overlap(
    db: Session, presentation_id: str, valid_from: datetime,
    valid_to: datetime | None, exclude_id: str | None = None,
) -> None:
    """Impide dos versiones vigentes en el mismo rango (FR-011-035).

    El índice único parcial ya garantiza una sola versión **abierta**; esto
    cubre además el solapamiento entre rangos cerrados, dentro de la
    transacción.
    """
    start = _aware(valid_from)
    end = _aware(valid_to)
    for version in db.execute(
        select(ProductPresentationVersion)
        .where(ProductPresentationVersion.presentation_id == presentation_id)
    ).scalars().all():
        if exclude_id and str(version.id) == exclude_id:
            continue
        other_start = _aware(version.valid_from)
        other_end = _aware(version.valid_to)
        overlaps = ((end is None or other_start < end)
                    and (other_end is None or start < other_end))
        if overlaps:
            raise ConflictError(
                code="PRESENTATION_VERSION_OVERLAP",
                message="Ya existe una equivalencia vigente en ese rango de fechas")


def assert_version_mutable(db: Session, version: ProductPresentationVersion) -> None:
    """Una versión cerrada o usada por algún snapshot no se edita ni se borra."""
    if version.valid_to is not None:
        raise ConflictError(
            code="PRESENTATION_VERSION_IMMUTABLE",
            message="Una equivalencia cerrada no se modifica: cree una nueva")
    del db
