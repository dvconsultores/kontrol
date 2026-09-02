"""API de maestros comerciales — Spec 012.

Toda operación de este prefijo es de empresa. **Ninguna acepta la empresa en el
cuerpo**: la pone `CompanyContext`, que es la autoridad de la petición.

Cada ruta hija resuelve su padre acotado por esa empresa antes de hacer nada, y
con tres niveles comprueba los tres eslabones. Es el contrato de
`nested-resource-security-contract.md`, y existe porque N10 encontró nueve rutas
que no lo cumplían.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.company_context import CompanyContext, get_company_context
from app.core.database import get_db
from app.core.dependencies import require_permission, require_write_allowed
from app.core.errors import ConflictError
from app.modules.commercial import service as comercial
from app.modules.commercial.models import (
    CommercialZone,
    CreditPolicy,
    DiscountPolicy,
    PaymentTerm,
    PriceList,
    SalesChannel,
)
from app.modules.identity_access.models import User

router = APIRouter(prefix="/comercial", tags=["comercial"])


def _guardar(db: Session, fila: Any) -> Any:
    """Confirma, y traduce el choque de unicidad en un 409 legible.

    Sin esto, un código repetido dentro de la misma empresa termina en 500: la
    restricción hace su trabajo y la respuesta no lo cuenta. La unicidad es
    parte del contrato, así que su violación es un conflicto, no un fallo.

    Los servicios de creación no hacen `flush` justamente para que el choque
    salte aquí, donde hay quien lo traduzca.
    """
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(code="COMMERCIAL_DUPLICATE",
                            message="Ya existe un registro con ese código en esta empresa") from exc
    db.refresh(fila)
    return fila


#: Los esquemas prohíben campos desconocidos. Es lo que impide que un cuerpo con
#: `company_id` pase inadvertido: no se ignora en silencio, se rechaza.
class Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------- #
# Condiciones de pago
# --------------------------------------------------------------------------- #
class PaymentTermIn(Estricto):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    kind: str = Field(pattern="^(CASH|DAYS|INSTALLMENTS|ADVANCE)$")
    days: int | None = Field(default=None, ge=0)
    installments: list[dict[str, Any]] | None = None
    advance_percent: Decimal | None = Field(default=None, ge=0, le=100)
    due_offset_from: str = Field(default="ISSUE_DATE",
                                 pattern="^(ISSUE_DATE|DELIVERY_DATE|RECEPTION_DATE)$")


def _pt(f: PaymentTerm) -> dict[str, Any]:
    return {"id": str(f.id), "code": f.code, "name": f.name, "kind": f.kind,
            "days": f.days, "installments": f.installments,
            "advance_percent": str(f.advance_percent) if f.advance_percent is not None else None,
            "due_offset_from": f.due_offset_from, "status": f.status}


@router.get("/condiciones-pago")
def listar_condiciones_pago(db: Session = Depends(get_db),
                            _: User = Depends(require_permission("comercial", "view")),
                            ctx: CompanyContext = Depends(get_company_context)):
    return {"items": [_pt(f) for f in comercial.listar(db, PaymentTerm, ctx.company_id)]}


@router.post("/condiciones-pago", status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_condicion_pago(body: PaymentTermIn, db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("comercial", "create")),
                         ctx: CompanyContext = Depends(get_company_context)):
    fila = comercial.crear_condicion_pago(db, company_id=ctx.company_id, actor=str(actor.id),
                                              **body.model_dump())
    _guardar(db, fila)
    return _pt(fila)


# --------------------------------------------------------------------------- #
# Zonas y canales
# --------------------------------------------------------------------------- #
class ZonaIn(Estricto):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    parent_id: str | None = None
    salesperson_id: str | None = None
    route: str | None = None


class CanalIn(Estricto):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)


def _basico(f: Any) -> dict[str, Any]:
    return {"id": str(f.id), "code": f.code, "name": f.name, "status": f.status}


@router.get("/zonas")
def listar_zonas(db: Session = Depends(get_db),
                 _: User = Depends(require_permission("comercial", "view")),
                 ctx: CompanyContext = Depends(get_company_context)):
    return {"items": [_basico(f) for f in comercial.listar(db, CommercialZone, ctx.company_id)]}


@router.post("/zonas", status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_zona(body: ZonaIn, db: Session = Depends(get_db),
               actor: User = Depends(require_permission("comercial", "create")),
               ctx: CompanyContext = Depends(get_company_context)):
    fila = comercial.crear_zona(db, company_id=ctx.company_id, actor=str(actor.id),
                                    **body.model_dump())
    _guardar(db, fila)
    return _basico(fila)


@router.get("/canales")
def listar_canales(db: Session = Depends(get_db),
                   _: User = Depends(require_permission("comercial", "view")),
                   ctx: CompanyContext = Depends(get_company_context)):
    return {"items": [_basico(f) for f in comercial.listar(db, SalesChannel, ctx.company_id)]}


@router.post("/canales", status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_canal(body: CanalIn, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("comercial", "create")),
                ctx: CompanyContext = Depends(get_company_context)):
    fila = comercial.crear_canal(db, company_id=ctx.company_id, actor=str(actor.id),
                                     **body.model_dump())
    _guardar(db, fila)
    return _basico(fila)


# --------------------------------------------------------------------------- #
# Políticas
# --------------------------------------------------------------------------- #
class PoliticaDescuentoIn(Estricto):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    scope: str = Field(pattern="^(LINE|DOCUMENT)$")
    applies_to: str = Field(default="ALL", pattern="^(ROLE|ITEM|CATEGORY|ALL)$")
    applies_ref: str | None = None
    #: Sin valor por defecto. Nulo es «no hay límite declarado», no cero.
    max_percent: Decimal | None = Field(default=None, ge=0, le=100)
    requires_approval_above: Decimal | None = Field(default=None, ge=0, le=100)
    stackable: bool = False
    incompatible_with: list[str] | None = None


class PoliticaCreditoIn(Estricto):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    credit_limit: Decimal | None = Field(default=None, ge=0)
    exposure_calculation: str | None = None
    block_on_overdue: bool = False
    grace_days: int | None = Field(default=None, ge=0)


@router.get("/politicas-descuento")
def listar_politicas_descuento(db: Session = Depends(get_db),
                               _: User = Depends(require_permission("comercial", "view")),
                               ctx: CompanyContext = Depends(get_company_context)):
    return {"items": [{**_basico(f), "scope": f.scope, "applies_to": f.applies_to,
                       "max_percent": str(f.max_percent) if f.max_percent is not None else None,
                       "version": int(f.version)}
                      for f in comercial.listar(db, DiscountPolicy, ctx.company_id)]}


@router.post("/politicas-descuento", status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_politica_descuento(body: PoliticaDescuentoIn, db: Session = Depends(get_db),
                             actor: User = Depends(require_permission("comercial", "manage_policies")),
                             ctx: CompanyContext = Depends(get_company_context)):
    fila = comercial.crear_politica_descuento(db, company_id=ctx.company_id, actor=str(actor.id),
                                                  **body.model_dump())
    _guardar(db, fila)
    return _basico(fila)


@router.get("/politicas-credito")
def listar_politicas_credito(db: Session = Depends(get_db),
                             _: User = Depends(require_permission("comercial", "view")),
                             ctx: CompanyContext = Depends(get_company_context)):
    return {"items": [_basico(f) for f in comercial.listar(db, CreditPolicy, ctx.company_id)]}


@router.post("/politicas-credito", status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_politica_credito(body: PoliticaCreditoIn, db: Session = Depends(get_db),
                           actor: User = Depends(require_permission("comercial", "manage_policies")),
                           ctx: CompanyContext = Depends(get_company_context)):
    fila = comercial.crear_politica_credito(db, company_id=ctx.company_id, actor=str(actor.id),
                                                **body.model_dump())
    _guardar(db, fila)
    return _basico(fila)


# --------------------------------------------------------------------------- #
# Precedencia — configuración, no código
# --------------------------------------------------------------------------- #
class EntradaPrecedencia(Estricto):
    source_kind: str = Field(
        pattern="^(CUSTOMER_CONTRACT|CUSTOMER_LIST|SEGMENT_LIST|BRANCH_LIST|COMPANY_LIST)$")
    enabled: bool = True


class PrecedenciaIn(Estricto):
    orden: list[EntradaPrecedencia] = Field(min_length=1)


@router.get("/precedencia")
def leer_precedencia(db: Session = Depends(get_db),
                     _: User = Depends(require_permission("comercial", "view")),
                     ctx: CompanyContext = Depends(get_company_context)):
    orden, configurada = comercial.precedencia_vigente(db, ctx.company_id)
    return {"orden": orden, "configurada": configurada}


@router.put("/precedencia", dependencies=[Depends(require_write_allowed)])
def fijar_precedencia(body: PrecedenciaIn, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("comercial", "manage_policies")),
                      ctx: CompanyContext = Depends(get_company_context)):
    filas = comercial.fijar_precedencia(db, company_id=ctx.company_id, actor=str(actor.id),
                                        orden=[e.model_dump() for e in body.orden])
    db.commit()
    return {"orden": [f.source_kind for f in filas], "configurada": True}


# --------------------------------------------------------------------------- #
# Listas de precios y su jerarquía
# --------------------------------------------------------------------------- #
class ListaIn(Estricto):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    currency_id: str
    segment: str | None = None
    channel_id: str | None = None
    source: str | None = None


class VersionIn(Estricto):
    valid_from: date
    valid_to: date | None = None


class TransicionIn(Estricto):
    target: str = Field(pattern="^(ACTIVE|SUPERSEDED|ARCHIVED)$")


class ItemIn(Estricto):
    item_id: str | None = None
    category_id: str | None = None
    presentation_id: str | None = None
    uom_id: str | None = None
    min_quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal = Field(ge=0)


def _lista(f: PriceList) -> dict[str, Any]:
    return {"id": str(f.id), "code": f.code, "name": f.name, "status": f.status,
            "currency_id": str(f.currency_id), "segment": f.segment,
            "channel_id": str(f.channel_id) if f.channel_id else None, "source": f.source}


def _version(f: Any) -> dict[str, Any]:
    return {"id": str(f.id), "price_list_id": str(f.price_list_id),
            "version_number": f.version_number, "valid_from": str(f.valid_from),
            "valid_to": str(f.valid_to) if f.valid_to else None, "status": f.status}


def _item(f: Any) -> dict[str, Any]:
    return {"id": str(f.id), "version_id": str(f.version_id),
            "item_id": str(f.item_id) if f.item_id else None,
            "category_id": str(f.category_id) if f.category_id else None,
            "presentation_id": str(f.presentation_id) if f.presentation_id else None,
            "uom_id": str(f.uom_id) if f.uom_id else None,
            "min_quantity": str(f.min_quantity) if f.min_quantity is not None else None,
            "unit_price": str(f.unit_price)}


@router.get("/listas-precio")
def listar_listas(db: Session = Depends(get_db),
                  _: User = Depends(require_permission("comercial", "view")),
                  ctx: CompanyContext = Depends(get_company_context)):
    return {"items": [_lista(f) for f in comercial.listar(db, PriceList, ctx.company_id)]}


@router.post("/listas-precio", status_code=201, dependencies=[Depends(require_write_allowed)])
def crear_lista(body: ListaIn, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("comercial", "create")),
                ctx: CompanyContext = Depends(get_company_context)):
    fila = comercial.crear_lista(db, company_id=ctx.company_id, actor=str(actor.id),
                                     **body.model_dump())
    _guardar(db, fila)
    return _lista(fila)


@router.get("/listas-precio/{price_list_id}")
def leer_lista(price_list_id: str, db: Session = Depends(get_db),
               _: User = Depends(require_permission("comercial", "view")),
               ctx: CompanyContext = Depends(get_company_context)):
    from sqlalchemy import select

    from app.modules.commercial.models import PriceListVersion

    lista = comercial.lista_de_precios(db, ctx.company_id, price_list_id)
    versiones = db.execute(select(PriceListVersion)
                           .where(PriceListVersion.price_list_id == str(lista.id))
                           .order_by(PriceListVersion.version_number)).scalars().all()
    return {**_lista(lista), "versions": [_version(v) for v in versiones]}


@router.post("/listas-precio/{price_list_id}/versiones", status_code=201,
             dependencies=[Depends(require_write_allowed)])
def crear_version(price_list_id: str, body: VersionIn, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("comercial", "create")),
                  ctx: CompanyContext = Depends(get_company_context)):
    """El padre se resuelve bajo el contexto **antes** de crear nada."""
    fila = comercial.crear_version(db, company_id=ctx.company_id, price_list_id=price_list_id,
                                       actor=str(actor.id), **body.model_dump())
    _guardar(db, fila)
    return _version(fila)


@router.post("/listas-precio/{price_list_id}/versiones/{version_id}/transicion",
             dependencies=[Depends(require_write_allowed)])
def transicionar_version(price_list_id: str, version_id: str, body: TransicionIn,
                         db: Session = Depends(get_db),
                         actor: User = Depends(require_permission("comercial", "publish")),
                         ctx: CompanyContext = Depends(get_company_context)):
    """Publicar es irreversible. Los dos eslabones se comprueban."""
    fila = comercial.transicionar_version(db, company_id=ctx.company_id,
                                              price_list_id=price_list_id, version_id=version_id,
                                              destino=body.target, actor=str(actor.id))
    _guardar(db, fila)
    return _version(fila)


@router.get("/listas-precio/{price_list_id}/versiones/{version_id}/items")
def listar_items(price_list_id: str, version_id: str, db: Session = Depends(get_db),
                 _: User = Depends(require_permission("comercial", "view")),
                 ctx: CompanyContext = Depends(get_company_context)):
    from sqlalchemy import select

    from app.modules.commercial.models import PriceListItem

    version = comercial.version_de_la_lista(db, ctx.company_id, price_list_id, version_id)
    filas = db.execute(select(PriceListItem)
                       .where(PriceListItem.version_id == str(version.id))).scalars().all()
    return {"items": [_item(f) for f in filas]}


@router.post("/listas-precio/{price_list_id}/versiones/{version_id}/items", status_code=201,
             dependencies=[Depends(require_write_allowed)])
def crear_item(price_list_id: str, version_id: str, body: ItemIn, db: Session = Depends(get_db),
               actor: User = Depends(require_permission("comercial", "create")),
               ctx: CompanyContext = Depends(get_company_context)):
    """Tres niveles, tres eslabones comprobados.

    Una versión legítima que cuelga de una lista de otra empresa no es
    alcanzable comprobando solo `version_id`.
    """
    fila = comercial.añadir_item(db, company_id=ctx.company_id, price_list_id=price_list_id,
                                     version_id=version_id, actor=str(actor.id), **body.model_dump())
    _guardar(db, fila)
    return _item(fila)


# --------------------------------------------------------------------------- #
# Condiciones comerciales del cliente
# --------------------------------------------------------------------------- #
class CondicionesClienteIn(Estricto):
    price_list_id: str | None = None
    payment_term_id: str | None = None
    commercial_zone_id: str | None = None
    sales_channel_id: str | None = None
    credit_policy_id: str | None = None
    salesperson_id: str | None = None


@router.put("/clientes/{customer_id}/condiciones", dependencies=[Depends(require_write_allowed)])
def fijar_condiciones_cliente(customer_id: str, body: CondicionesClienteIn,
                              db: Session = Depends(get_db),
                              actor: User = Depends(require_permission("comercial", "edit")),
                              ctx: CompanyContext = Depends(get_company_context)):
    fila = comercial.fijar_condiciones_cliente(db, company_id=ctx.company_id,
                                                   customer_id=customer_id, actor=str(actor.id),
                                                   **body.model_dump())
    _guardar(db, fila)
    return {"id": str(fila.id), "customer_id": str(fila.customer_id),
            "price_list_id": str(fila.price_list_id) if fila.price_list_id else None,
            "payment_term_id": str(fila.payment_term_id) if fila.payment_term_id else None}


# --------------------------------------------------------------------------- #
# Resolución — la razón de ser de la Spec
# --------------------------------------------------------------------------- #
class ResolverIn(Estricto):
    """**Sin `company_id`.** El esquema es estricto: si llega, se rechaza.

    Lo declaraba el contrato anterior, y era la vulnerabilidad que la Spec 045
    estrenó: el cliente eligiendo en qué empresa opera.
    """

    item_id: str
    customer_id: str | None = None
    presentation_id: str | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    as_of: date | None = None


class DescuentoIn(Estricto):
    scope: str = Field(pattern="^(LINE|DOCUMENT)$")
    percent: Decimal = Field(ge=0, le=100)
    item_id: str | None = None
    role: str | None = None


@router.post("/precio/resolver")
def resolver_precio(body: ResolverIn, db: Session = Depends(get_db),
                    _: User = Depends(require_permission("comercial", "view")),
                    ctx: CompanyContext = Depends(get_company_context)):
    return comercial.resolver_precio(db, company_id=ctx.company_id, **body.model_dump())


@router.post("/descuento/validar")
def validar_descuento(body: DescuentoIn, db: Session = Depends(get_db),
                      _: User = Depends(require_permission("comercial", "view")),
                      ctx: CompanyContext = Depends(get_company_context)):
    return comercial.validar_descuento(db, company_id=ctx.company_id, **body.model_dump())
