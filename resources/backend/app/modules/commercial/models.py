"""Maestros comerciales — Spec 012.

Once entidades. Ninguna nace con filas: ningún porcentaje, plazo, límite, zona
ni canal viene de fábrica (`P8`, `FR-012-022`, `FR-012-032`).

Ocho llevan su empresa en columna propia. Tres la alcanzan por su padre y **no
la duplican**: una segunda respuesta a una pregunta que ya tiene una puede
discrepar de la primera, que es el defecto que N7 encontró en la estructura de
almacén y tuvo que cerrar con una clave foránea compuesta.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    DDL,
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
    literal_column,
)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.expression import column as sql_column

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import (
    CodeMixin,
    CreatedByMixin,
    NameMixin,
    StatusMixin,
    TimestampMixin,
    UUIDMixin,
    VersionMixin,
)

#: Precisión monetaria. Nunca `float`: la Spec 011 dejó cara esa lección —un
#: `float` en un factor no se nota hasta que no cuadra un cierre (`NFR-012-06`).
DINERO = Numeric(18, 4)
PORCENTAJE = Numeric(9, 4)
CANTIDAD = Numeric(18, 6)


# --------------------------------------------------------------------------- #
# 1. Condiciones de pago
# --------------------------------------------------------------------------- #
class PaymentTerm(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin,
                  StatusMixin, Base):
    """`FR-012-030`: es un maestro, **nunca** una cadena.

    «Contado» y «30 días» son datos de cada empresa, no constantes del producto.
    """

    __tablename__ = "payment_terms"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_payment_terms_company_code"),
        CheckConstraint("kind IN ('CASH','DAYS','INSTALLMENTS','ADVANCE')",
                        name="ck_payment_terms_kind"),
        CheckConstraint(
            "due_offset_from IN ('ISSUE_DATE','DELIVERY_DATE','RECEPTION_DATE')",
            name="ck_payment_terms_due_offset"),
        Index("ix_payment_terms_company", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    #: `[{offset_days, percent}]` para `INSTALLMENTS`.
    installments: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    advance_percent: Mapped[Decimal | None] = mapped_column(PORCENTAJE, nullable=True)
    due_offset_from: Mapped[str] = mapped_column(String(32), nullable=False, default="ISSUE_DATE")
    #: La cadena original del legado, si vino de ahí. **No se borra** (`FR-012-080`).
    legacy_value: Mapped[str | None] = mapped_column(String(255), nullable=True)


# --------------------------------------------------------------------------- #
# 2. Zona comercial
# --------------------------------------------------------------------------- #
class CommercialZone(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin,
                     StatusMixin, Base):
    """Territorio de ventas. **No** es `warehouse_zones` (`FR-012-040/041`).

    Comparten la palabra «zona» y nada más: ninguna clave foránea entre ambas,
    ninguna vista común. Una es dónde está la mercancía; otra, quién vende allí.
    """

    __tablename__ = "commercial_zones"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_commercial_zones_company_code"),
        Index("ix_commercial_zones_company", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("commercial_zones.id"), nullable=True)
    #: El vendedor es un usuario, y los usuarios son del tenant. Que exista en el
    #: tenant no significa que pueda operar en esta empresa: el servicio lo
    #: comprueba con `accessible_company_ids`, que es la autoridad canónica.
    salesperson_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    route: Mapped[str | None] = mapped_column(String(120), nullable=True)
    legacy_value: Mapped[str | None] = mapped_column(String(255), nullable=True)


# --------------------------------------------------------------------------- #
# 3. Canal de venta
# --------------------------------------------------------------------------- #
class SalesChannel(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin,
                   StatusMixin, Base):
    __tablename__ = "sales_channels"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_sales_channels_company_code"),
        Index("ix_sales_channels_company", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    legacy_value: Mapped[str | None] = mapped_column(String(255), nullable=True)


# --------------------------------------------------------------------------- #
# 4. Lista de precios
# --------------------------------------------------------------------------- #
class PriceList(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin,
                StatusMixin, Base):
    __tablename__ = "price_lists"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_price_lists_company_code"),
        Index("ix_price_lists_company", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    #: El maestro monetario **existente**, que es de empresa. Una lista de A solo
    #: puede referenciar una moneda de A: lo comprueba el servicio.
    currency_id: Mapped[str] = mapped_column(ForeignKey("currencies.id"), nullable=False)
    segment: Mapped[str | None] = mapped_column(String(120), nullable=True)
    channel_id: Mapped[str | None] = mapped_column(ForeignKey("sales_channels.id"), nullable=True)
    #: Quién la cargó y de dónde (`FR-012-008`).
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)


# --------------------------------------------------------------------------- #
# 5. Versión de lista — derivada
# --------------------------------------------------------------------------- #
class PriceListVersion(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Una lista **no se edita**: se versiona (`FR-012-002`).

    No lleva `company_id`. Su empresa es la de su lista, y esa ruta es
    obligatoria en cada eslabón.
    """

    __tablename__ = "price_list_versions"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "price_list_id → price_lists"
    __table_args__ = (
        # Dos versiones `ACTIVE` de la misma lista no solapan vigencia. Va en el
        # ORM y no solo en la migración porque las suites levantan el esquema con
        # `create_all`: dejarla únicamente en la migración haría que las pruebas
        # interrogaran un esquema más débil que el de producción, que es
        # exactamente lo que N7 encontró con 80 claves foráneas.
        #
        # El `where` es esencial: dos borradores **sí** pueden solapar, porque un
        # borrador todavía no compite con nadie.
        ExcludeConstraint(
            (sql_column("price_list_id"), "="),
            (func.daterange(sql_column("valid_from", Date),
                            func.coalesce(sql_column("valid_to", Date),
                                          literal_column("'infinity'::date")),
                            literal_column("'[)'")), "&&"),
            name="ex_price_list_versions_no_overlap",
            where=sql_column("status") == "ACTIVE",
        ).ddl_if(dialect="postgresql"),
        UniqueConstraint("price_list_id", "version_number",
                         name="uq_price_list_versions_list_number"),
        CheckConstraint("status IN ('DRAFT','ACTIVE','SUPERSEDED','ARCHIVED')",
                        name="ck_price_list_versions_status"),
        CheckConstraint("valid_to IS NULL OR valid_to > valid_from",
                        name="ck_price_list_versions_range"),
        Index("ix_price_list_versions_list_status", "price_list_id", "status"),
    )

    price_list_id: Mapped[str] = mapped_column(ForeignKey("price_lists.id"), nullable=False, index=True)
    #: Correlativo **del servidor**: el cliente no lo elige.
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    #: Nulo significa **abierta**, no «desconocida».
    valid_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="DRAFT")
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[Any | None] = mapped_column(String(64), nullable=True)


# --------------------------------------------------------------------------- #
# 6. Ítem de versión — derivada
# --------------------------------------------------------------------------- #
class PriceListItem(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """El precio de un artículo o de una categoría, en una versión concreta.

    `item_id` y `category_id` son **excluyentes**: uno de los dos, nunca ambos,
    nunca ninguno. La categoría es `taxonomy_nodes`, que es lo que KONTROL usa
    para clasificar artículos; no existe ninguna `item_categories`.
    """

    __tablename__ = "price_list_items"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "version_id → price_list_versions"
    __table_args__ = (
        CheckConstraint(
            "(item_id IS NOT NULL AND category_id IS NULL) OR "
            "(item_id IS NULL AND category_id IS NOT NULL)",
            name="ck_price_list_items_target"),
        CheckConstraint("unit_price >= 0", name="ck_price_list_items_price"),
        CheckConstraint("min_quantity IS NULL OR min_quantity > 0",
                        name="ck_price_list_items_min_qty"),
        Index("ix_price_list_items_version", "version_id"),
        Index("ix_price_list_items_lookup", "version_id", "item_id", "min_quantity"),
        # La unicidad lleva columnas anulables dentro de la clave, y en SQL
        # `NULL` no es igual a `NULL`: una `UNIQUE` ingenua permitiría
        # duplicados exactos. Índices parciales, uno por variante, con los nulos
        # normalizados.
        Index("uq_price_list_items_by_item", "version_id", "item_id",
              func.coalesce(sql_column("presentation_id"), literal_column("''")),
              func.coalesce(sql_column("min_quantity"), literal_column("-1")),
              unique=True, postgresql_where=sql_column("item_id").isnot(None)
              ).ddl_if(dialect="postgresql"),
        Index("uq_price_list_items_by_category", "version_id", "category_id",
              func.coalesce(sql_column("presentation_id"), literal_column("''")),
              func.coalesce(sql_column("min_quantity"), literal_column("-1")),
              unique=True, postgresql_where=sql_column("category_id").isnot(None)
              ).ddl_if(dialect="postgresql"),
    )

    version_id: Mapped[str] = mapped_column(ForeignKey("price_list_versions.id"), nullable=False)
    item_id: Mapped[str | None] = mapped_column(ForeignKey("catalog_items.id"), nullable=True)
    category_id: Mapped[str | None] = mapped_column(ForeignKey("taxonomy_nodes.id"), nullable=True)
    presentation_id: Mapped[str | None] = mapped_column(ForeignKey("presentations.id"), nullable=True)
    #: Unidad de la Spec 011. Su `company_id` **admite nulo**: la unidad de
    #: plataforma la ven todas las empresas. La comprobación es «propia o de
    #: plataforma», no igualdad estricta.
    uom_id: Mapped[str | None] = mapped_column(ForeignKey("units_of_measure.id"), nullable=True)
    min_quantity: Mapped[Decimal | None] = mapped_column(CANTIDAD, nullable=True)
    unit_price: Mapped[Decimal] = mapped_column(DINERO, nullable=False)


# --------------------------------------------------------------------------- #
# 7. Precedencia
# --------------------------------------------------------------------------- #
class PricePrecedence(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """El orden en que se buscan las listas. **Dato, no código** (`FR-012-010`).

    KONTROL puede sembrar el orden por defecto de `ADR-D0-005` como punto de
    partida editable: el valor vive en una tabla y la empresa lo reordena. Eso
    no viola `P8`; codificarlo sí lo haría.
    """

    __tablename__ = "price_precedence"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "order_index", name="uq_price_precedence_company_order"),
        UniqueConstraint("company_id", "source_kind", name="uq_price_precedence_company_kind"),
        CheckConstraint(
            "source_kind IN ('CUSTOMER_CONTRACT','CUSTOMER_LIST','SEGMENT_LIST',"
            "'BRANCH_LIST','COMPANY_LIST')",
            name="ck_price_precedence_kind"),
        Index("ix_price_precedence_company", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# --------------------------------------------------------------------------- #
# 8. Política de descuento
# --------------------------------------------------------------------------- #
class DiscountPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin,
                     StatusMixin, VersionMixin, Base):
    """**Ningún porcentaje viene de fábrica** (`FR-012-022`)."""

    __tablename__ = "discount_policies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", "version",
                         name="uq_discount_policies_company_code_version"),
        CheckConstraint("scope IN ('LINE','DOCUMENT')", name="ck_discount_policies_scope"),
        CheckConstraint("applies_to IN ('ROLE','ITEM','CATEGORY','ALL')",
                        name="ck_discount_policies_applies"),
        CheckConstraint("max_percent IS NULL OR (max_percent >= 0 AND max_percent <= 100)",
                        name="ck_discount_policies_max"),
        Index("ix_discount_policies_company", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    scope: Mapped[str] = mapped_column(String(16), nullable=False)
    applies_to: Mapped[str] = mapped_column(String(16), nullable=False, default="ALL")
    applies_ref: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: **Sin valor por defecto.** Nulo significa «no hay límite declarado», no cero.
    max_percent: Mapped[Decimal | None] = mapped_column(PORCENTAJE, nullable=True)
    #: Umbral que dispara la Spec 045. No bloquea: abre solicitud (`FR-012-023`).
    requires_approval_above: Mapped[Decimal | None] = mapped_column(PORCENTAJE, nullable=True)
    stackable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    incompatible_with: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)


# --------------------------------------------------------------------------- #
# 9. Política de crédito
# --------------------------------------------------------------------------- #
class CreditPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin, NameMixin,
                   StatusMixin, VersionMixin, Base):
    """Distinta de la condición de pago (`R-D0-05-4`).

    Una dice **cuándo se paga**; la otra, **cuánto riesgo se admite**.
    """

    __tablename__ = "credit_policies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", "version",
                         name="uq_credit_policies_company_code_version"),
        CheckConstraint("credit_limit IS NULL OR credit_limit >= 0",
                        name="ck_credit_policies_limit"),
        CheckConstraint("grace_days IS NULL OR grace_days >= 0",
                        name="ck_credit_policies_grace"),
        Index("ix_credit_policies_company", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    credit_limit: Mapped[Decimal | None] = mapped_column(DINERO, nullable=True)
    exposure_calculation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    block_on_overdue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    grace_days: Mapped[int | None] = mapped_column(Integer, nullable=True)


# --------------------------------------------------------------------------- #
# 10. Condiciones comerciales del cliente — derivada
# --------------------------------------------------------------------------- #
class CustomerCommercialTerms(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Extiende `customers` por clave foránea; **no lo duplica** (`FR-012-051`).

    No lleva `company_id`: la empresa es la de su cliente, que la alcanza por
    `party_id → parties`.
    """

    __tablename__ = "customer_commercial_terms"
    __scope__ = Scope.COMPANY
    __scope_authority__ = "customer_id → customers"
    __table_args__ = (
        UniqueConstraint("customer_id", name="uq_customer_commercial_terms_customer"),
    )

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    price_list_id: Mapped[str | None] = mapped_column(ForeignKey("price_lists.id"), nullable=True)
    payment_term_id: Mapped[str | None] = mapped_column(ForeignKey("payment_terms.id"), nullable=True)
    commercial_zone_id: Mapped[str | None] = mapped_column(ForeignKey("commercial_zones.id"), nullable=True)
    sales_channel_id: Mapped[str | None] = mapped_column(ForeignKey("sales_channels.id"), nullable=True)
    credit_policy_id: Mapped[str | None] = mapped_column(ForeignKey("credit_policies.id"), nullable=True)
    salesperson_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    blocked_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    blocked_at: Mapped[str | None] = mapped_column(String(64), nullable=True)
    block_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# 11. Comisiones — RESERVADA
# --------------------------------------------------------------------------- #
class SalesCommissionPolicy(UUIDMixin, TimestampMixin, CreatedByMixin, CodeMixin,
                            NameMixin, StatusMixin, Base):
    """**Reservada** (`FR-012-090`). La Spec 012 no calcula comisión ni toca nómina.

    Existe para que añadirla luego no obligue a rediseñar. No tiene servicio, ni
    ruta, ni interfaz: solo la tabla y su alcance declarado.
    """

    __tablename__ = "sales_commission_policies"
    __scope__ = Scope.COMPANY
    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_sales_commission_policies_company_code"),
        Index("ix_sales_commission_policies_company", "company_id"),
    )

    company_id: Mapped[str] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    basis: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


# --------------------------------------------------------------------------- #
# La extensión que la exclusión necesita
# --------------------------------------------------------------------------- #
# `EXCLUDE USING gist` con un `=` sobre una columna de texto necesita
# `btree_gist`. La migración la crea; esto la crea también cuando el esquema
# nace de `create_all`, para que las pruebas no interroguen un esquema más débil
# que el de producción.
event.listen(
    PriceListVersion.__table__,
    "before_create",
    DDL("CREATE EXTENSION IF NOT EXISTS btree_gist").execute_if(dialect="postgresql"),
)
