"""Servicios de los maestros comerciales — Spec 012.

Todo lo que aquí se resuelve pasa por la empresa **antes** que por cualquier
otra cosa. No es una precaución: N10 encontró nueve rutas de escritura que
recibían el identificador del padre por la URL y lo usaban tal cual, y esta
Spec es la que más rutas hijas tiene de todo KONTROL.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.commercial.models import (
    CommercialZone,
    CreditPolicy,
    CustomerCommercialTerms,
    DiscountPolicy,
    PaymentTerm,
    PriceList,
    PriceListItem,
    PriceListVersion,
    PricePrecedence,
    SalesChannel,
)
from app.shared.clock import hoy_de_negocio

T = TypeVar("T")

#: Estados de una versión y sus transiciones. Publicar es irreversible: una
#: versión `ACTIVE` equivocada no se corrige, se supera con otra.
TRANSICIONES = {
    "DRAFT": {"ACTIVE", "ARCHIVED"},
    "ACTIVE": {"SUPERSEDED", "ARCHIVED"},
    "SUPERSEDED": {"ARCHIVED"},
    "ARCHIVED": set(),
}


# --------------------------------------------------------------------------- #
# Resolución acotada por empresa
# --------------------------------------------------------------------------- #
def _de_la_empresa(db: Session, modelo: type[T], ident: str, company_id: str,
                   code: str, mensaje: str) -> T:
    """Carga una entidad **directa** de empresa, o 404.

    404 y no 403: un 403 sobre un recurso ajeno confirma que existe, y con
    identificadores adivinables eso es un inventario ajeno servido de a un bit
    por petición.
    """
    fila = db.get(modelo, ident)
    if fila is None or getattr(fila, "company_id", None) != company_id:
        raise NotFoundError(code=code, message=mensaje)
    return fila


def lista_de_precios(db: Session, company_id: str, price_list_id: str) -> PriceList:
    return _de_la_empresa(db, PriceList, price_list_id, company_id,
                          "PRICE_LIST_NOT_FOUND", "Lista de precios no encontrada")


def version_de_la_lista(db: Session, company_id: str, price_list_id: str,
                        version_id: str) -> PriceListVersion:
    """La versión **de esa lista**, con la lista **de esta empresa**.

    Comprobar solo `version_id` dejaría pasar una versión legítima que cuelga de
    una lista de otra empresa. Con tres niveles hay que comprobar los tres
    eslabones, no solo el primero.
    """
    lista = lista_de_precios(db, company_id, price_list_id)
    version = db.get(PriceListVersion, version_id)
    if version is None or str(version.price_list_id) != str(lista.id):
        raise NotFoundError(code="PRICE_LIST_VERSION_NOT_FOUND",
                            message="Versión de lista no encontrada")
    return version


def item_de_la_version(db: Session, company_id: str, price_list_id: str,
                       version_id: str, item_row_id: str) -> PriceListItem:
    version = version_de_la_lista(db, company_id, price_list_id, version_id)
    item = db.get(PriceListItem, item_row_id)
    if item is None or str(item.version_id) != str(version.id):
        raise NotFoundError(code="PRICE_LIST_ITEM_NOT_FOUND",
                            message="Ítem de lista no encontrado")
    return item


# --------------------------------------------------------------------------- #
# Referencias hacia otros maestros
# --------------------------------------------------------------------------- #
def _exige_moneda(db: Session, company_id: str, currency_id: str) -> None:
    from app.modules.treasury.models import Currency

    moneda = db.get(Currency, currency_id)
    if moneda is None or str(moneda.company_id) != str(company_id):
        raise NotFoundError(code="CURRENCY_NOT_FOUND", message="Moneda no encontrada")


def _exige_articulo(db: Session, company_id: str, item_id: str) -> None:
    from app.modules.master_data.models import CatalogItem

    art = db.get(CatalogItem, item_id)
    if art is None or str(art.company_id) != str(company_id):
        raise NotFoundError(code="ITEM_NOT_FOUND", message="Artículo no encontrado")


def _exige_categoria(db: Session, company_id: str, category_id: str) -> None:
    from app.modules.master_data.models import TaxonomyNode

    nodo = db.get(TaxonomyNode, category_id)
    if nodo is None or str(nodo.company_id) != str(company_id):
        raise NotFoundError(code="CATEGORY_NOT_FOUND", message="Categoría no encontrada")


def _exige_presentacion(db: Session, company_id: str, presentation_id: str) -> None:
    from app.modules.master_data.models import Presentation

    pres = db.get(Presentation, presentation_id)
    if pres is None or str(pres.company_id) != str(company_id):
        raise NotFoundError(code="PRESENTATION_NOT_FOUND", message="Presentación no encontrada")


def _exige_unidad(db: Session, company_id: str, uom_id: str) -> None:
    """«Propia **o** de plataforma», no igualdad estricta.

    `units_of_measure.company_id` admite nulo y ese nulo significa unidad de la
    plataforma: la ven todas las empresas y es de solo lectura para ellas.
    Comparar por igualdad rechazaría una unidad perfectamente legítima.
    """
    from app.modules.master_data.models import UnitOfMeasure

    unidad = db.get(UnitOfMeasure, uom_id)
    if unidad is None or (unidad.company_id is not None
                          and str(unidad.company_id) != str(company_id)):
        raise NotFoundError(code="UOM_NOT_FOUND", message="Unidad no encontrada")


def _exige_vendedor(db: Session, company_id: str, user_id: str) -> None:
    """El vendedor es un usuario, y los usuarios son del tenant.

    Que exista en el tenant no significa que pueda operar en esta empresa. La
    autoridad no se reinventa aquí: es `accessible_company_ids`, la misma que
    decide a qué empresa entra una petición.
    """
    from app.core.company_context import accessible_company_ids
    from app.modules.identity_access.models import User

    usuario = db.get(User, user_id)
    if usuario is None or str(company_id) not in accessible_company_ids(db, usuario):
        raise NotFoundError(code="USER_NOT_FOUND", message="Usuario no encontrado")


# --------------------------------------------------------------------------- #
# Maestros directos
# --------------------------------------------------------------------------- #
def listar(db: Session, modelo: type[T], company_id: str,
           status: str | None = None) -> list[T]:
    consulta = select(modelo).where(modelo.company_id == company_id)
    if status:
        consulta = consulta.where(modelo.status == status)
    orden = getattr(modelo, "code", getattr(modelo, "order_index", None))
    return list(db.execute(consulta.order_by(orden)).scalars().all())


def crear_condicion_pago(db: Session, *, company_id: str, actor: str | None,
                         **datos: Any) -> PaymentTerm:
    if datos.get("kind") == "DAYS" and datos.get("days") is None:
        raise KontrolError(code="PAYMENT_TERM_DAYS_REQUIRED",
                           message="Una condición por días necesita los días", status_code=422)
    fila = PaymentTerm(company_id=company_id, created_by=actor, **datos)
    db.add(fila)
    return fila


def crear_zona(db: Session, *, company_id: str, actor: str | None, **datos: Any) -> CommercialZone:
    if datos.get("salesperson_id"):
        _exige_vendedor(db, company_id, datos["salesperson_id"])
    if datos.get("parent_id"):
        _de_la_empresa(db, CommercialZone, datos["parent_id"], company_id,
                       "COMMERCIAL_ZONE_NOT_FOUND", "Zona comercial no encontrada")
    fila = CommercialZone(company_id=company_id, created_by=actor, **datos)
    db.add(fila)
    return fila


def crear_canal(db: Session, *, company_id: str, actor: str | None, **datos: Any) -> SalesChannel:
    fila = SalesChannel(company_id=company_id, created_by=actor, **datos)
    db.add(fila)
    return fila


def crear_politica_descuento(db: Session, *, company_id: str, actor: str | None,
                             **datos: Any) -> DiscountPolicy:
    fila = DiscountPolicy(company_id=company_id, created_by=actor, **datos)
    db.add(fila)
    return fila


def crear_politica_credito(db: Session, *, company_id: str, actor: str | None,
                           **datos: Any) -> CreditPolicy:
    fila = CreditPolicy(company_id=company_id, created_by=actor, **datos)
    db.add(fila)
    return fila


def fijar_precedencia(db: Session, *, company_id: str, actor: str | None,
                      orden: list[dict[str, Any]]) -> list[PricePrecedence]:
    """Reemplaza el orden completo. Es **dato**, no código (`FR-012-010`).

    KONTROL puede sembrar el orden por defecto de `ADR-D0-005`, pero lo siembra
    en esta tabla y la empresa lo reordena. Codificarlo violaría `P8`.
    """
    for fila in db.execute(select(PricePrecedence)
                           .where(PricePrecedence.company_id == company_id)).scalars().all():
        db.delete(fila)
    db.flush()
    creadas = []
    for i, entrada in enumerate(orden):
        fila = PricePrecedence(company_id=company_id, order_index=i,
                               source_kind=entrada["source_kind"],
                               enabled=entrada.get("enabled", True), created_by=actor)
        db.add(fila)
        creadas.append(fila)
    db.flush()
    return creadas


# --------------------------------------------------------------------------- #
# Listas de precios
# --------------------------------------------------------------------------- #
def crear_lista(db: Session, *, company_id: str, actor: str | None, **datos: Any) -> PriceList:
    _exige_moneda(db, company_id, datos["currency_id"])
    if datos.get("channel_id"):
        _de_la_empresa(db, SalesChannel, datos["channel_id"], company_id,
                       "SALES_CHANNEL_NOT_FOUND", "Canal no encontrado")
    fila = PriceList(company_id=company_id, created_by=actor, **datos)
    db.add(fila)
    return fila


def crear_version(db: Session, *, company_id: str, price_list_id: str, actor: str | None,
                  valid_from: date, valid_to: date | None = None) -> PriceListVersion:
    lista = lista_de_precios(db, company_id, price_list_id)
    ultimo = db.execute(
        select(PriceListVersion.version_number)
        .where(PriceListVersion.price_list_id == str(lista.id))
        .order_by(PriceListVersion.version_number.desc()).limit(1)).scalar()
    version = PriceListVersion(
        price_list_id=str(lista.id),
        # Correlativo del servidor: el cliente no lo elige (`FR-012-002`).
        version_number=(ultimo or 0) + 1,
        valid_from=valid_from, valid_to=valid_to, status="DRAFT", created_by=actor)
    db.add(version)
    db.flush()
    return version


def transicionar_version(db: Session, *, company_id: str, price_list_id: str,
                         version_id: str, destino: str, actor: str | None) -> PriceListVersion:
    version = version_de_la_lista(db, company_id, price_list_id, version_id)
    if destino not in TRANSICIONES.get(version.status, set()):
        raise ConflictError(code="PRICE_LIST_VERSION_TRANSITION",
                            message=f"Una versión {version.status} no pasa a {destino}.")
    version.status = destino
    if destino == "ACTIVE":
        version.approved_by = actor
    # Sin `flush`: el veredicto de la exclusión debe llegar al `commit`, donde
    # hay quien lo traduzca en un 409 con su motivo.
    return version


def añadir_item(db: Session, *, company_id: str, price_list_id: str, version_id: str,
                actor: str | None, **datos: Any) -> PriceListItem:
    """Un ítem solo entra en un **borrador** de una versión de **esta** empresa."""
    version = version_de_la_lista(db, company_id, price_list_id, version_id)
    if version.status != "DRAFT":
        raise ConflictError(code="PRICE_LIST_VERSION_NOT_DRAFT",
                            message="Solo un borrador admite ítems nuevos.")
    if bool(datos.get("item_id")) == bool(datos.get("category_id")):
        raise KontrolError(code="PRICE_LIST_ITEM_TARGET",
                           message="Indique un artículo **o** una categoría, no ambos ni ninguno",
                           status_code=422)
    if datos.get("item_id"):
        _exige_articulo(db, company_id, datos["item_id"])
    if datos.get("category_id"):
        _exige_categoria(db, company_id, datos["category_id"])
    if datos.get("presentation_id"):
        _exige_presentacion(db, company_id, datos["presentation_id"])
    if datos.get("uom_id"):
        _exige_unidad(db, company_id, datos["uom_id"])
    item = PriceListItem(version_id=str(version.id), created_by=actor, **datos)
    db.add(item)
    db.flush()
    return item


# --------------------------------------------------------------------------- #
# Condiciones comerciales del cliente
# --------------------------------------------------------------------------- #
def _cliente_de_la_empresa(db: Session, company_id: str, customer_id: str):
    from app.modules.master_data.models import Customer, Party

    cliente = db.get(Customer, customer_id)
    if cliente is None:
        raise NotFoundError(code="CUSTOMER_NOT_FOUND", message="Cliente no encontrado")
    tercero = db.get(Party, cliente.party_id)
    if tercero is None or str(tercero.company_id) != str(company_id):
        raise NotFoundError(code="CUSTOMER_NOT_FOUND", message="Cliente no encontrado")
    return cliente


def fijar_condiciones_cliente(db: Session, *, company_id: str, customer_id: str,
                              actor: str | None, **datos: Any) -> CustomerCommercialTerms:
    cliente = _cliente_de_la_empresa(db, company_id, customer_id)
    referencias = (
        ("price_list_id", PriceList, "PRICE_LIST_NOT_FOUND", "Lista de precios no encontrada"),
        ("payment_term_id", PaymentTerm, "PAYMENT_TERM_NOT_FOUND", "Condición de pago no encontrada"),
        ("commercial_zone_id", CommercialZone, "COMMERCIAL_ZONE_NOT_FOUND", "Zona no encontrada"),
        ("sales_channel_id", SalesChannel, "SALES_CHANNEL_NOT_FOUND", "Canal no encontrado"),
        ("credit_policy_id", CreditPolicy, "CREDIT_POLICY_NOT_FOUND", "Política de crédito no encontrada"),
    )
    for campo, modelo, code, mensaje in referencias:
        if datos.get(campo):
            _de_la_empresa(db, modelo, datos[campo], company_id, code, mensaje)
    if datos.get("salesperson_id"):
        _exige_vendedor(db, company_id, datos["salesperson_id"])

    fila = db.execute(select(CustomerCommercialTerms)
                      .where(CustomerCommercialTerms.customer_id == str(cliente.id))).scalars().first()
    if fila is None:
        fila = CustomerCommercialTerms(customer_id=str(cliente.id), created_by=actor, **datos)
        db.add(fila)
    else:
        for k, v in datos.items():
            setattr(fila, k, v)
    db.flush()
    return fila


# --------------------------------------------------------------------------- #
# Resolución de precio
# --------------------------------------------------------------------------- #
#: Orden por defecto de `ADR-D0-005`. Se **siembra** como dato reordenable; no
#: se impone. Si una empresa no ha configurado su precedencia, se usa este orden
#: y se dice en la respuesta de dónde salió.
ORDEN_POR_DEFECTO = ("CUSTOMER_CONTRACT", "CUSTOMER_LIST", "SEGMENT_LIST",
                     "BRANCH_LIST", "COMPANY_LIST")


def precedencia_vigente(db: Session, company_id: str) -> tuple[list[str], bool]:
    filas = db.execute(
        select(PricePrecedence)
        .where(PricePrecedence.company_id == company_id, PricePrecedence.enabled.is_(True))
        .order_by(PricePrecedence.order_index)).scalars().all()
    if filas:
        return [f.source_kind for f in filas], True
    return list(ORDEN_POR_DEFECTO), False


def _listas_candidatas(db: Session, company_id: str, customer_id: str | None) -> dict[str, list[str]]:
    """Qué lista aporta cada clase de precedencia, para esta empresa."""
    por_clase: dict[str, list[str]] = {k: [] for k in ORDEN_POR_DEFECTO}
    if customer_id:
        cond = db.execute(select(CustomerCommercialTerms)
                          .where(CustomerCommercialTerms.customer_id == customer_id)).scalars().first()
        if cond is not None and cond.price_list_id:
            por_clase["CUSTOMER_LIST"].append(str(cond.price_list_id))
    todas = db.execute(select(PriceList).where(PriceList.company_id == company_id,
                                               PriceList.status == "ACTIVE")).scalars().all()
    for lista in todas:
        if lista.segment:
            por_clase["SEGMENT_LIST"].append(str(lista.id))
        else:
            por_clase["COMPANY_LIST"].append(str(lista.id))
    return por_clase


def resolver_precio(db: Session, *, company_id: str, item_id: str,
                    customer_id: str | None = None, presentation_id: str | None = None,
                    quantity: Decimal | None = None, as_of: date | None = None) -> dict[str, Any]:
    """La **única** autoridad de precio del sistema (`FR-012-014`).

    Determinista: la misma entrada devuelve siempre lo mismo, incluida la
    versión que lo produjo. Si no hay lista aplicable **declara la ausencia**;
    no devuelve cero, porque un cero es un precio y la ausencia de precio no lo
    es (`FR-012-016`).
    """
    _exige_articulo(db, company_id, item_id)
    if presentation_id:
        _exige_presentacion(db, company_id, presentation_id)
    fecha = as_of or hoy_de_negocio()
    cantidad = Decimal(str(quantity)) if quantity is not None else None

    orden, configurada = precedencia_vigente(db, company_id)
    candidatas = _listas_candidatas(db, company_id, customer_id)

    for clase in orden:
        ids = candidatas.get(clase) or []
        if not ids:
            continue
        encontrados = []
        for lista_id in ids:
            version = db.execute(
                select(PriceListVersion)
                .where(PriceListVersion.price_list_id == lista_id,
                       PriceListVersion.status == "ACTIVE",
                       PriceListVersion.valid_from <= fecha)
                .order_by(PriceListVersion.valid_from.desc())).scalars().first()
            if version is None or (version.valid_to is not None and version.valid_to <= fecha):
                continue
            consulta = select(PriceListItem).where(PriceListItem.version_id == str(version.id),
                                                   PriceListItem.item_id == item_id)
            if presentation_id:
                consulta = consulta.where(PriceListItem.presentation_id == presentation_id)
            for item in db.execute(consulta).scalars().all():
                if item.min_quantity is not None and (cantidad is None or cantidad < item.min_quantity):
                    continue
                encontrados.append((version, item))
        if not encontrados:
            continue
        # Empate: vigencia más reciente y, a igualdad, menor precio (`FR-012-012`).
        encontrados.sort(key=lambda p: (-p[0].valid_from.toordinal(), p[1].unit_price))
        if len(encontrados) > 1:
            primero, segundo = encontrados[0], encontrados[1]
            if (primero[0].valid_from == segundo[0].valid_from
                    and primero[1].unit_price == segundo[1].unit_price
                    and str(primero[1].id) != str(segundo[1].id)):
                # Un empate irresoluble **jamás** se resuelve al azar (`FR-012-013`).
                raise KontrolError(
                    code="PRICE_PRECEDENCE_TIE",
                    message="Dos precios empatan y la configuración no permite decidir.",
                    status_code=422,
                    details={"candidates": [str(primero[1].id), str(segundo[1].id)]})
        version, item = encontrados[0]
        lista = db.get(PriceList, version.price_list_id)
        return {
            "resolved": True,
            "unit_price": str(item.unit_price),
            "currency_id": str(lista.currency_id),
            "price_list_id": str(lista.id),
            "price_list_version_id": str(version.id),
            "price_list_item_id": str(item.id),
            "source_kind": clase,
            "precedence_configured": configurada,
        }

    return {"resolved": False, "reason": "NO_APPLICABLE_PRICE_LIST",
            "precedence_configured": configurada}


# --------------------------------------------------------------------------- #
# Validación de descuento
# --------------------------------------------------------------------------- #
def validar_descuento(db: Session, *, company_id: str, scope: str, percent: Decimal,
                      item_id: str | None = None, role: str | None = None) -> dict[str, Any]:
    """Dice si el descuento cabe y si hace falta aprobación. **No aprueba nada.**

    Superar el límite no bloquea: abre una solicitud en la Spec 045, y esa
    solicitud la abre el consumidor. La 012 no crea aprobaciones.
    """
    porcentaje = Decimal(str(percent))
    politicas = db.execute(
        select(DiscountPolicy)
        .where(DiscountPolicy.company_id == company_id,
               DiscountPolicy.status == "ACTIVE",
               DiscountPolicy.scope == scope)
        .order_by(DiscountPolicy.version.desc())).scalars().all()

    aplicables = []
    for p in politicas:
        if p.applies_to == "ALL":
            aplicables.append(p)
        elif p.applies_to == "ITEM" and item_id and p.applies_ref == item_id:
            aplicables.append(p)
        elif p.applies_to == "ROLE" and role and p.applies_ref == role:
            aplicables.append(p)
    if not aplicables:
        # Sin política declarada no se inventa un límite. El catálogo nace vacío.
        return {"allowed": True, "max_percent": None, "requires_approval": False,
                "policy_id": None, "policy_version": None,
                "reason": "NO_POLICY_DECLARED"}

    # La más específica manda; a igualdad, la de versión mayor.
    orden = {"ITEM": 0, "ROLE": 1, "CATEGORY": 2, "ALL": 3}
    aplicables.sort(key=lambda p: (orden.get(p.applies_to, 9), -int(p.version)))
    politica = aplicables[0]
    maximo = politica.max_percent
    umbral = politica.requires_approval_above
    return {
        "allowed": maximo is None or porcentaje <= maximo,
        "max_percent": str(maximo) if maximo is not None else None,
        "requires_approval": umbral is not None and porcentaje > umbral,
        "policy_id": str(politica.id),
        "policy_version": int(politica.version),
    }
