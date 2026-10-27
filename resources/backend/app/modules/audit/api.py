"""API de auditoría (FR-001-070/071/072).

El listado es de **tenant** (ARCH-MC-001, matriz de alcance por endpoint:
`TENANT/INSTALLATION`, sin contexto de empresa; la vista por empresa vive en
`/reporting/audit/timeline`). El tenant no lo elige el cliente: sale del
usuario autenticado, que es la única autoridad que la petición tiene sobre esa
pregunta. Ni la consulta ni el cuerpo pueden ampliarlo, y `admin` no significa
«todos los tenants»: no existe rol con esa autoridad.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permission
from app.modules.audit.models import AuditEvent
from app.modules.identity_access.models import User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/events")
def list_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("audit", "view")),
):
    # El alcance de tenant va primero (FR-001-032/033): el conjunto sobre el que
    # actúan los filtros, el recuento y la paginación ya es solo el propio. Un
    # `total` que contara lo ajeno, o una página recortada después de cortarla,
    # no serían un filtro: serían un disfraz. Un evento sin tenant no es de
    # nadie y aquí no lo lee nadie; la Spec no define eventos globales de
    # auditoría (los de instalación viven en sus propias tablas).
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

    # `total` lo cuenta la base, sobre el mismo `query` del que después se corta la
    # página: un solo conjunto, sin dos listas de filtros que puedan divergir. El
    # orden es solo de los items; contar no lo necesita, y traerse la bitácora
    # entera del tenant para medirla con `len()` era el coste de cada petición.
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    items = db.execute(
        query.order_by(AuditEvent.event_time.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
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
            }
            for e in items
        ],
    }
