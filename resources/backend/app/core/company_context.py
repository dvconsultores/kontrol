"""Contexto de empresa por petición (ARCH-MC-001, ADR-D0-014).

Antes de esta remediación el backend no sabía en qué empresa ocurría una
petición, y por eso usaba el `tenant_id` como sustituto. Este módulo es la pieza
que faltaba.

**El cliente propone; el servidor decide.** La cabecera `X-Kontrol-Company` es
una sugerencia, nunca una autorización: se valida que la empresa exista, sea del
tenant autenticado, esté activa y que el usuario tenga acceso. Manipularla desde
el navegador no abre ninguna puerta.

Se eligió cabecera por petición —y no sesión ni claim en el token— por una razón
concreta: dos pestañas deben poder operar en empresas distintas sin que una
acción lanzada desde la primera termine ejecutándose en la segunda. Con estado
global eso es un fallo silencioso, y aquí los fallos silenciosos emiten facturas.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.errors import ConflictError, KontrolError, NotFoundError
from app.modules.identity_access.models import User
from app.modules.organization.models import Company

#: Cabecera por la que el cliente propone la empresa.
COMPANY_HEADER = "X-Kontrol-Company"


@dataclass(frozen=True)
class CompanyContext:
    """La empresa en la que ocurre esta petición, ya validada."""

    tenant_id: str
    company_id: str
    company: Company
    user_id: str
    #: Sucursales a las que el usuario está limitado; vacío = sin restricción.
    branch_ids: tuple[str, ...] = field(default=())

    def __str__(self) -> str:                      # pragma: no cover - diagnóstico
        return f"CompanyContext(company={self.company_id})"


# --------------------------------------------------------------------------
# Acceso del usuario a las empresas de su tenant
# --------------------------------------------------------------------------

def accessible_company_ids(db: Session, user: User) -> list[str]:
    """Empresas del tenant a las que este usuario puede acceder.

    Pertenecer al tenant **no** concede acceso a todas sus empresas: sería
    reproducir en los permisos el mismo defecto que se está corrigiendo en los
    datos. El alcance se lee de `user_scopes` y `user_roles`, que ya existen; no
    se crea un sistema paralelo (Spec 003).

    Un alcance con `company_id` nulo significa «todas las del tenant»: es la
    convención que la columna anulable ya expresaba.
    """
    from app.modules.identity_access.models import UserRole, UserScope

    del_tenant = list(db.execute(
        select(Company.id).where(Company.tenant_id == user.tenant_id)).scalars().all())

    ámbitos = db.execute(
        select(UserScope.company_id).where(UserScope.user_id == str(user.id))).scalars().all()
    roles = db.execute(
        select(UserRole.company_id).where(UserRole.user_id == str(user.id))).scalars().all()

    declarados = list(ámbitos) + list(roles)
    if not declarados or any(c is None for c in declarados):
        # Sin alcance declarado, o con uno global: todas las del tenant.
        return del_tenant
    permitidas = {c for c in declarados if c}
    return [c for c in del_tenant if c in permitidas]


def resolve_company(db: Session, user: User, requested: str | None) -> CompanyContext:
    """Resuelve y **valida** la empresa de la petición.

    El orden de las comprobaciones importa: se responde `404` tanto para una
    empresa inexistente como para una a la que no se tiene acceso. Distinguirlas
    confirmaría su existencia a quien no debería saberlo.
    """
    accesibles = accessible_company_ids(db, user)

    if requested is None:
        if len(accesibles) == 1:
            # Con una sola empresa no se pide elegir: no hay información en la
            # pregunta.
            requested = accesibles[0]
        elif not accesibles:
            raise NotFoundError(code="COMPANY_NOT_FOUND",
                                message="El usuario no tiene acceso a ninguna empresa")
        else:
            raise KontrolError(
                code="COMPANY_CONTEXT_REQUIRED",
                message="Indique la empresa en la que desea operar",
                status_code=400,
                details={"companies": accesibles})

    if requested not in accesibles:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")

    company = db.get(Company, requested)
    if company is None or company.tenant_id != user.tenant_id:
        raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    if company.status != "ACTIVE":
        raise ConflictError(code="COMPANY_INACTIVE",
                            message="La empresa no está activa")

    return CompanyContext(
        tenant_id=user.tenant_id, company_id=str(company.id), company=company,
        user_id=str(user.id), branch_ids=_branch_scope(db, user, str(company.id)))


def _branch_scope(db: Session, user: User, company_id: str) -> tuple[str, ...]:
    """Sucursales a las que el usuario está limitado dentro de esta empresa.

    Vacío significa **sin restricción**, no «ninguna»: el alcance más fino solo
    se aplica cuando alguien lo declaró.
    """
    from app.modules.identity_access.models import UserScope

    filas = db.execute(select(UserScope.branch_id, UserScope.company_id)
                       .where(UserScope.user_id == str(user.id))).all()
    ramas = [b for b, c in filas if b and (c is None or c == company_id)]
    return tuple(ramas)


# --------------------------------------------------------------------------
# Dependencia de FastAPI
# --------------------------------------------------------------------------

def get_company_context(request: Request,
                        db: Session = Depends(get_db)) -> CompanyContext:
    """Contexto de empresa de esta petición. Úsese en toda ruta de empresa."""
    from app.core.dependencies import get_current_user

    user = get_current_user(request, db)
    return resolve_company(db, user, request.headers.get(COMPANY_HEADER))


def company_context_for(db: Session, user: User, company_id: str) -> CompanyContext:
    """Contexto explícito, para trabajos sin petición HTTP.

    Un trabajo de fondo **debe** abrirlo a propósito. No existe un contexto por
    defecto: ejecutar en la empresa equivocada por omisión es justo lo que esta
    remediación evita.
    """
    return resolve_company(db, user, company_id)
