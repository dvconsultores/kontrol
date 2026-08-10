"""Servicio de autenticación e identidad (FR-001-010/011/012/013/020/021/022/023).

- Login con bloqueo por fuerza bruta y rate limiting.
- Sesiones con refresh token rotable y revocable.
- Cambio de contraseña (obligatorio y voluntario).
- Recuperación con token de un solo uso.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt as pyjwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.modules.identity_access.models import (
    PasswordReset,
    Permission,
    Role,
    RolePermission,
    User,
    UserRole,
)
from app.modules.identity_access.models import (
    Session as AuthSession,
)
from app.shared import audit as audit_service


def _now() -> datetime:
    return datetime.now(UTC)


def _audit(db: Session, **kwargs: Any) -> None:
    audit_service.record_audit(db, **kwargs)


# --------------------------------------------------------------------------- #
# Usuarios
# --------------------------------------------------------------------------- #
def create_user(
    db: Session,
    *,
    tenant_id: str,
    username: str,
    email: str | None,
    password: str,
    must_change_password: bool = True,
    created_by: str | None = None,
) -> User:
    existing = db.execute(select(User).where(User.username == username, User.tenant_id == tenant_id)).scalars().first()
    if existing:
        raise ConflictError(code="USER_DUPLICATE", message="Ya existe un usuario con este nombre de usuario")

    user = User(
        tenant_id=tenant_id,
        username=username,
        email=email,
        password_hash=security.hash_password(password),
        status="ACTIVE",
        must_change_password=must_change_password,
        created_by=created_by,
    )
    db.add(user)
    db.flush()
    _audit(
        db,
        action="USER_CREATED",
        entity_type="User",
        entity_id=str(user.id),
        tenant_id=tenant_id,
        user_id=created_by,
        after={"username": username},
    )
    return user


def get_user_by_username(db: Session, tenant_id: str, username: str) -> User | None:
    return db.execute(select(User).where(User.username == username, User.tenant_id == tenant_id)).scalars().first()


def get_user(db: Session, user_id: str) -> User:
    user = db.get(User, user_id)
    if not user:
        raise NotFoundError(code="USER_NOT_FOUND", message="Usuario no encontrado")
    return user


# --------------------------------------------------------------------------- #
# Autenticación
# --------------------------------------------------------------------------- #
def authenticate(db: Session, *, tenant_id: str, username: str, password: str, request_id: str | None = None) -> User:
    settings = get_settings()
    user = get_user_by_username(db, tenant_id, username)
    if not user:
        raise KontrolError(code="AUTH_INVALID_CREDENTIALS", message="Credenciales inválidas", status_code=401)

    # Bloqueo por fuerza bruta
    if user.lockout_until and user.lockout_until > _now():
        _audit(db, action="LOGIN_BLOCKED", entity_type="User", entity_id=str(user.id), tenant_id=tenant_id, request_id=request_id)
        db.commit()
        raise KontrolError(code="AUTH_ACCOUNT_LOCKED", message="Cuenta temporalmente bloqueada por intentos fallidos", status_code=423)

    if not security.verify_password(password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= settings.lockout_after_failures:
            user.lockout_until = _now() + timedelta(minutes=settings.lockout_minutes)
            user.failed_attempts = 0
        _audit(db, action="LOGIN_FAILED", entity_type="User", entity_id=str(user.id), tenant_id=tenant_id, request_id=request_id)
        db.commit()
        raise KontrolError(code="AUTH_INVALID_CREDENTIALS", message="Credenciales inválidas", status_code=401)

    if user.status != "ACTIVE":
        _audit(db, action="LOGIN_FAILED", entity_type="User", entity_id=str(user.id), tenant_id=tenant_id, request_id=request_id, reason="USUARIO_INACTIVO")
        db.commit()
        raise KontrolError(code="AUTH_USER_INACTIVE", message="El usuario está desactivado", status_code=403)

    user.failed_attempts = 0
    user.lockout_until = None
    user.last_login = _now()
    _audit(db, action="LOGIN_SUCCESS", entity_type="User", entity_id=str(user.id), tenant_id=tenant_id, request_id=request_id)
    db.commit()
    return user


def create_session(db: Session, *, user: User, ip: str | None, user_agent: str | None) -> tuple[AuthSession, str]:
    settings = get_settings()
    jti = security.sha256_hex(security.generate_secret_token())
    refresh_token = security.create_refresh_token(str(user.id), session_id="pending", jti=jti)
    # El session_id se fija tras crear la sesión; se regenera para evitar circularidad.
    session = AuthSession(
        user_id=str(user.id),
        refresh_token_hash=security.sha256_hex(refresh_token),
        ip=ip,
        user_agent=user_agent,
        expires_at=_now() + timedelta(days=settings.refresh_token_days),
    )
    db.add(session)
    db.flush()
    # Regenerar refresh con session_id real y actualizar hash
    new_token = security.create_refresh_token(str(user.id), session_id=str(session.id), jti=jti)
    session.refresh_token_hash = security.sha256_hex(new_token)
    db.commit()
    db.refresh(session)
    return session, new_token


def rotate_session(db: Session, *, refresh_token: str, request_id: str | None = None) -> tuple[AuthSession, str, User]:
    """Renueva la sesión: valida refresh, rota token y devuelve nueva sesión + access token."""
    try:
        payload = security.decode_token(refresh_token, expected_type="refresh")
    except pyjwt.PyJWTError:
        raise KontrolError(code="SESSION_INVALID", message="Sesión inválida o expirada", status_code=401) from None

    session = db.get(AuthSession, payload.get("sid"))
    if not session or session.revoked_at is not None:
        raise KontrolError(code="SESSION_REVOKED", message="Sesión revocada", status_code=401)
    if session.refresh_token_hash != security.sha256_hex(refresh_token):
        raise KontrolError(code="SESSION_INVALID", message="Sesión inválida", status_code=401)
    if session.expires_at < _now():
        session.revoked_at = _now()
        db.commit()
        raise KontrolError(code="SESSION_EXPIRED", message="Sesión expirada", status_code=401)

    user = db.get(User, session.user_id)
    if not user or user.status != "ACTIVE":
        raise KontrolError(code="AUTH_USER_INACTIVE", message="El usuario no está activo", status_code=403)

    # Rotación: revocar la anterior y crear una nueva.
    session.revoked_at = _now()
    new_session, new_refresh = create_session(db, user=user, ip=session.ip, user_agent=session.user_agent)
    _audit(db, action="SESSION_REFRESHED", entity_type="User", entity_id=str(user.id), tenant_id=user.tenant_id, request_id=request_id)
    db.commit()
    return new_session, new_refresh, user


def revoke_session(db: Session, *, session_id: str, user_id: str | None = None, request_id: str | None = None) -> None:
    session = db.get(AuthSession, session_id)
    if not session:
        raise NotFoundError(code="SESSION_NOT_FOUND", message="Sesión no encontrada")
    if user_id and session.user_id != user_id:
        raise PermissionDeniedError()
    session.revoked_at = _now()
    user = db.get(User, session.user_id)
    _audit(db, action="SESSION_REVOKED", entity_type="Session", entity_id=str(session.id), tenant_id=user.tenant_id if user else None, request_id=request_id)
    db.commit()


def list_sessions(db: Session, *, user_id: str) -> list[AuthSession]:
    return list(db.execute(select(AuthSession).where(AuthSession.user_id == user_id).order_by(AuthSession.created_at.desc())).scalars().all())


# --------------------------------------------------------------------------- #
# Cambio de contraseña
# --------------------------------------------------------------------------- #
def change_password(
    db: Session,
    *,
    user: User,
    current_password: str,
    new_password: str,
    request_id: str | None = None,
) -> None:
    if not security.verify_password(current_password, user.password_hash):
        raise KontrolError(code="AUTH_CURRENT_PASSWORD_INVALID", message="La contraseña actual es incorrecta", status_code=401)
    errors = security.validate_password_policy(new_password)
    if errors:
        raise KontrolError(code="PASSWORD_POLICY", message="La contraseña no cumple la política", field_errors={"new_password": errors}, status_code=422)
    user.password_hash = security.hash_password(new_password)
    user.must_change_password = False
    _audit(db, action="PASSWORD_CHANGED", entity_type="User", entity_id=str(user.id), tenant_id=user.tenant_id, request_id=request_id, reason="CAMBIO")
    db.commit()


# --------------------------------------------------------------------------- #
# Recuperación de contraseña
# --------------------------------------------------------------------------- #
def request_password_reset(db: Session, *, tenant_id: str, username: str, request_id: str | None = None) -> str:
    """Crea un token de un solo uso (devuelve el token en claro para el demo/setup)."""
    user = get_user_by_username(db, tenant_id, username)
    if not user:
        # No revelar existencia
        raise KontrolError(code="AUTH_INVALID_CREDENTIALS", message="Credenciales inválidas", status_code=401)
    token = security.generate_secret_token(32)
    reset = PasswordReset(
        user_id=str(user.id),
        token_hash=security.sha256_hex(token),
        expires_at=_now() + timedelta(minutes=30),
    )
    db.add(reset)
    _audit(db, action="PASSWORD_RESET_REQUESTED", entity_type="User", entity_id=str(user.id), tenant_id=tenant_id, request_id=request_id)
    db.commit()
    return token


def confirm_password_reset(db: Session, *, token: str, new_password: str, request_id: str | None = None) -> None:
    errors = security.validate_password_policy(new_password)
    if errors:
        raise KontrolError(code="PASSWORD_POLICY", message="La contraseña no cumple la política", field_errors={"new_password": errors}, status_code=422)
    reset = db.execute(select(PasswordReset).where(PasswordReset.token_hash == security.sha256_hex(token))).scalars().first()
    if not reset or reset.used_at is not None or reset.expires_at < _now():
        raise KontrolError(code="RESET_TOKEN_INVALID", message="El enlace de recuperación no es válido o expiró", status_code=401)
    user = db.get(User, reset.user_id)
    if not user:
        raise KontrolError(code="RESET_USER_NOT_FOUND", message="El usuario no existe", status_code=401)
    user.password_hash = security.hash_password(new_password)
    user.must_change_password = False
    reset.used_at = _now()
    _audit(db, action="PASSWORD_RESET_CONFIRMED", entity_type="User", entity_id=str(user.id), tenant_id=user.tenant_id, request_id=request_id)
    db.commit()


# --------------------------------------------------------------------------- #
# Roles / permisos
# --------------------------------------------------------------------------- #
def get_user_permissions(db: Session, user: User) -> list[str]:
    """Permisos efectivos del usuario (resource:action)."""
    from sqlalchemy import select

    from app.modules.identity_access.models import Permission, RolePermission

    role_ids = [ur.role_id for ur in user.user_roles]
    if not role_ids:
        return []
    rows = db.execute(select(Permission.resource, Permission.action).join(RolePermission, RolePermission.permission_id == Permission.id).where(RolePermission.role_id.in_(role_ids))).all()
    return [f"{r}:{a}" for r, a in rows]


def user_has_permission(user: User, permissions: list[str], resource: str, action: str) -> bool:
    """Verifica permiso en la lista efectiva (deny by default)."""
    return f"{resource}:{action}" in permissions


def list_roles(db: Session, *, company_id: str | None = None) -> list[dict]:
    """Roles activos con sus permisos (FR-001-040)."""
    q = select(Role).where(Role.status == "ACTIVE")
    if company_id:
        q = q.where(Role.company_id == company_id)
    roles = db.execute(q.order_by(Role.name)).scalars().all()
    result: list[dict] = []
    for r in roles:
        perms = db.execute(
            select(Permission.resource, Permission.action)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == str(r.id))
        ).all()
        result.append(
            {
                "id": str(r.id),
                "code": r.code,
                "name": r.name,
                "protected": r.protected,
                "status": r.status,
                "permissions": sorted(f"{res}:{act}" for res, act in perms),
            }
        )
    return result


def get_user_roles(db: Session, user_id: str) -> list[dict]:
    """Roles asignados a un usuario (FR-001-040)."""
    rows = db.execute(
        select(Role.id, Role.code, Role.name, UserRole.company_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    ).all()
    return [{"id": str(rid), "code": rcode, "name": rname, "company_id": cid} for rid, rcode, rname, cid in rows]


def assign_role_to_user(
    db: Session,
    *,
    user_id: str,
    role_id: str,
    company_id: str | None = None,
    actor: str | None = None,
) -> None:
    """Asigna un rol a un usuario (FR-001-040); idempotente por par."""
    user = get_user(db, user_id)
    role = db.get(Role, role_id)
    if not role:
        raise NotFoundError(code="ROLE_NOT_FOUND", message="Rol no encontrado")
    existing = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    ).scalars().first()
    if existing:
        raise ConflictError(code="ROLE_ALREADY_ASSIGNED", message="El usuario ya tiene este rol")
    db.add(UserRole(user_id=user_id, role_id=role_id, company_id=company_id))
    _audit(
        db,
        action="ROLE_ASSIGNED",
        entity_type="UserRole",
        entity_id=f"{user_id}:{role_id}",
        tenant_id=user.tenant_id,
        user_id=actor,
        after={"role_id": role_id, "user_id": user_id},
    )
    db.commit()


def remove_role_from_user(
    db: Session,
    *,
    user_id: str,
    role_id: str,
    actor: str | None = None,
) -> None:
    """Quita un rol de un usuario (FR-001-040)."""
    user = get_user(db, user_id)
    row = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    ).scalars().first()
    if not row:
        raise NotFoundError(code="ROLE_NOT_ASSIGNED", message="El usuario no tiene este rol")
    db.delete(row)
    _audit(
        db,
        action="ROLE_REMOVED",
        entity_type="UserRole",
        entity_id=f"{user_id}:{role_id}",
        tenant_id=user.tenant_id,
        user_id=actor,
        after={"role_id": role_id, "user_id": user_id},
    )
    db.commit()
