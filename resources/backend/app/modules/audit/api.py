"""API de auditoría (FR-001-070/071/072, FR-001-264/265/266).

El listado es de **tenant** (ARCH-MC-001, matriz de alcance por endpoint:
`TENANT/INSTALLATION`, sin contexto de empresa; la vista por empresa vive en
`/reporting/audit/timeline`). El tenant no lo elige el cliente: sale del
usuario autenticado, que es la única autoridad que la petición tiene sobre esa
pregunta. Ni la consulta ni el cuerpo pueden ampliarlo, y `admin` no significa
«todos los tenants»: no existe rol con esa autoridad.

GOV-CTL-005: el muestreo por día civil de Caracas usa límites UTC semiabiertos
(ADR-020). OD-AUD-01: los eventos sin empresa solo los lee quien tiene la
capacidad en todo el tenant; la proyección no amplía esa visibilidad.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.core.errors import KontrolError
from app.modules.audit.models import AuditEvent
from app.modules.identity_access.models import User
from app.modules.organization.models import Company
from app.shared.audit_catalog import CATALOG_VERSION, label_of, public_actions, safe_details, scope_of
from app.shared.clock import limites_del_dia_utc

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/filters")
def audit_filters(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit", "view")),
):
    """Superficie para que la pantalla construya sus filtros sin ampliar el alcance.

    Las empresas son exactamente las que devuelve `companies_with_capability`:
    una empresa no audible no aparece, y la bandera de todo el tenant resume esa
    misma autoridad (FR-001-266).
    """
    from app.modules.identity_access import authority

    empresas = authority.companies_with_capability(db, user, "audit:view")
    companies = db.execute(
        select(Company)
        .where(Company.tenant_id == user.tenant_id, Company.id.in_(sorted(empresas)))
        .order_by(Company.code)
    ).scalars().all()
    return {
        "catalog_version": CATALOG_VERSION,
        "tenant_wide": authority.has_tenant_wide_capability(db, user, "audit:view"),
        "actions": public_actions(),
        "companies": [
            {"id": str(c.id), "code": c.code, "name": c.legal_name}
            for c in companies
        ],
    }


@router.get("/events")
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    desde: date | None = Query(None),
    hasta: date | None = Query(None),
    username: str | None = None,
    company_id: str | None = None,
    scope: Literal["TENANT", "COMPANY"] | None = None,
    request_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit", "view")),
):
    # El alcance de tenant va primero (FR-001-032/033): el conjunto sobre el que
    # actúan los filtros, el recuento y la paginación ya es solo el propio. Un
    # `total` que contara lo ajeno, o una página recortada después de cortarla,
    # no serían un filtro: serían un disfraz. Un evento sin tenant no es de
    # nadie y aquí no lo lee nadie; la Spec no define eventos globales de
    # auditoría (los de instalación viven en sus propias tablas).
    if desde is not None and hasta is not None and desde > hasta:
        raise KontrolError(
            code="INVALID_DATE_RANGE",
            message="La fecha «Desde» no puede ser posterior a «Hasta».",
            field_errors={"desde": ["Debe ser anterior o igual a «Hasta»."]},
            status_code=422,
        )
    query = select(AuditEvent).where(AuditEvent.tenant_id == user.tenant_id)
    from app.modules.identity_access import authority
    # La capacidad también es por empresa (Spec 003):
    # solo se leen eventos de las empresas donde se tiene audit:view; los del tenant sin empresa, solo con esa autoridad en todas.
    empresas = authority.companies_with_capability(db, user, "audit:view")
    condicion: ColumnElement[bool] = AuditEvent.company_id.in_(sorted(empresas))
    if authority.has_tenant_wide_capability(db, user, "audit:view"):
        condicion = or_(condicion, AuditEvent.company_id.is_(None))
    query = query.where(condicion)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditEvent.entity_id == entity_id)
    if action:
        query = query.where(AuditEvent.action == action)
    if desde is not None:
        query = query.where(AuditEvent.event_time >= limites_del_dia_utc(desde)[0])
    if hasta is not None:
        query = query.where(AuditEvent.event_time < limites_del_dia_utc(hasta)[1])
    if username:
        query = query.where(
            AuditEvent.user_id.in_(
                select(User.id).where(
                    User.tenant_id == user.tenant_id,
                    User.username == username,
                )
            )
        )
    if company_id:
        query = query.where(AuditEvent.company_id == company_id)
    if scope == "TENANT":
        query = query.where(AuditEvent.company_id.is_(None))
    elif scope == "COMPANY":
        query = query.where(AuditEvent.company_id.is_not(None))
    if request_id:
        query = query.where(AuditEvent.request_id == request_id)

    # `total` lo cuenta la base, sobre el mismo `query` del que después se corta la
    # página: un solo conjunto, sin dos listas de filtros que puedan divergir. El
    # orden es solo de los items; contar no lo necesita, y traerse la bitácora
    # entera del tenant para medirla con `len()` era el coste de cada petición.
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    items = db.execute(
        query.order_by(AuditEvent.event_time.desc(), AuditEvent.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).scalars().all()

    user_ids = {e.user_id for e in items if e.user_id is not None}
    company_ids = {e.company_id for e in items if e.company_id is not None}
    usernames: dict[str, str] = {}
    company_names: dict[str, str] = {}
    if user_ids:
        usernames = {
            str(row.id): row.username
            for row in db.execute(
                select(User.id, User.username).where(
                    User.tenant_id == user.tenant_id,
                    User.id.in_(user_ids),
                )
            ).all()
        }
    if company_ids:
        company_names = {
            str(row.id): row.legal_name
            for row, in db.execute(
                select(Company).where(
                    Company.tenant_id == user.tenant_id,
                    Company.id.in_(company_ids),
                )
            ).all()
        }

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "items": [
            {
                "id": str(e.id),
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "user_id": e.user_id,
                "request_id": e.request_id,
                "source": e.source,
                "event_time": e.event_time.isoformat(),
                "company_id": e.company_id,
                "company_name": company_names.get(e.company_id) if e.company_id else None,
                "scope": scope_of(e.action, e.entity_type),
                "action_label": label_of(e.action, e.entity_type),
                "username": usernames.get(e.user_id) if e.user_id else None,
                "reason": e.reason,
                "details": safe_details(
                    e.action,
                    e.entity_type,
                    e.before,
                    e.after,
                    e.evidence,
                ),
            }
            for e in items
        ],
    }
