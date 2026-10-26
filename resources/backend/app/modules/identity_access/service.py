"""Servicio de autenticación e identidad (FR-001-010/011/012/013/020/021/022/023).

- Login con bloqueo por fuerza bruta y rate limiting.
- Sesiones con refresh token rotable y revocable.
- Cambio de contraseña (obligatorio y voluntario).
- Recuperación con token de un solo uso.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, overload

import jwt as pyjwt
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.core import clock, security
from app.core.config import get_settings
from app.core.errors import ConflictError, KontrolError, NotFoundError, PermissionDeniedError
from app.modules.identity_access import mfa_policy
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
    """Reloj único de las decisiones de seguridad."""
    return clock.now()


@overload
def _as_utc(dt: datetime) -> datetime: ...


@overload
def _as_utc(dt: None) -> None: ...


def _as_utc(dt: datetime | None) -> datetime | None:
    """Normaliza a UTC (adjunta UTC si el driver devolvió naive — p. ej. SQLite).

    Evita `TypeError: can't compare offset-naive and offset-aware datetimes`
    (KAUD-013). Con PostgreSQL + DateTime(timezone=True) los valores ya vienen
    aware y se devuelven sin cambio.
    """
    if dt is None or dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=UTC)


PASSWORD_RESET_TTL = timedelta(minutes=15)
RESET_REQUEST_AUDIT_WINDOW = timedelta(minutes=15)


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


def get_user_in_tenant(db: Session, user_id: str, tenant_id: str) -> User:
    """El usuario, **dentro del tenant de quien pregunta**.

    `get_user` busca por id y devuelve a cualquiera de la instalación. Sirve
    para el propio portador del token; no sirve para administrar a terceros,
    que es donde se usaba: un administrador de T1 asignaba y retiraba roles a
    usuarios de T2 sin que nada lo impidiera.
    """
    user = db.get(User, user_id)
    if not user or str(user.tenant_id) != str(tenant_id):
        raise NotFoundError(code="USER_NOT_FOUND", message="Usuario no encontrado")
    return user


# --------------------------------------------------------------------------- #
# Autenticación
# --------------------------------------------------------------------------- #
def register_auth_failure(db: Session, user: User) -> None:
    settings = get_settings()
    user.failed_attempts += 1
    if user.failed_attempts >= settings.lockout_after_failures:
        user.lockout_until = _now() + timedelta(minutes=settings.lockout_minutes)
        user.failed_attempts = 0


def is_locked(user: User) -> bool:
    return user.lockout_until is not None and _as_utc(user.lockout_until) > _now()


def verify_password_stage(
    db: Session, *, tenant_id: str, username: str, password: str, request_id: str | None = None
) -> User:
    user = get_user_by_username(db, tenant_id, username)
    if not user:
        raise KontrolError(code="AUTH_INVALID_CREDENTIALS", message="Credenciales inválidas", status_code=401)

    # Bloqueo por fuerza bruta
    if is_locked(user):
        _audit(db, action="LOGIN_BLOCKED", entity_type="User", entity_id=str(user.id), tenant_id=tenant_id, request_id=request_id)
        db.commit()
        raise KontrolError(code="AUTH_ACCOUNT_LOCKED", message="Cuenta temporalmente bloqueada por intentos fallidos", status_code=423)

    if not security.verify_password(password, user.password_hash):
        register_auth_failure(db, user)
        _audit(db, action="LOGIN_FAILED", entity_type="User", entity_id=str(user.id), tenant_id=tenant_id, request_id=request_id)
        db.commit()
        raise KontrolError(code="AUTH_INVALID_CREDENTIALS", message="Credenciales inválidas", status_code=401)

    if user.status != "ACTIVE":
        _audit(db, action="LOGIN_FAILED", entity_type="User", entity_id=str(user.id), tenant_id=tenant_id, request_id=request_id, reason="USUARIO_INACTIVO")
        db.commit()
        raise KontrolError(code="AUTH_USER_INACTIVE", message="El usuario está desactivado", status_code=403)

    return user


def complete_login_bookkeeping(db: Session, user: User, *, request_id: str | None = None) -> None:
    user.failed_attempts = 0
    user.lockout_until = None
    user.last_login = _now()
    _audit(db, action="LOGIN_SUCCESS", entity_type="User", entity_id=str(user.id), tenant_id=user.tenant_id, request_id=request_id)


def authenticate(db: Session, *, tenant_id: str, username: str, password: str, request_id: str | None = None) -> User:
    user = verify_password_stage(db, tenant_id=tenant_id, username=username, password=password, request_id=request_id)
    complete_login_bookkeeping(db, user, request_id=request_id)
    db.commit()
    return user


def create_session(
    db: Session,
    *,
    user: User,
    ip: str | None,
    user_agent: str | None,
    auth_method: str = "PASSWORD",
    mfa_verified_at: datetime | None = None,
    reauth_at: datetime | None = None,
    family_id: str | None = None,
    credential_stamp: str | None,
) -> tuple[AuthSession, str]:
    settings = get_settings()
    jti = security.sha256_hex(security.generate_secret_token())
    session_id = str(uuid.uuid4())
    refresh_token = security.create_refresh_token(str(user.id), session_id="pending", jti=jti)
    # El session_id se fija tras crear la sesión; se regenera para evitar circularidad.
    session = AuthSession(
        id=session_id,
        family_id=family_id or session_id,
        user_id=str(user.id),
        refresh_token_hash=security.sha256_hex(refresh_token),
        ip=ip,
        user_agent=user_agent,
        auth_method=auth_method,
        mfa_verified_at=mfa_verified_at,
        reauth_at=reauth_at,
        credential_stamp=credential_stamp,
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


def issue_access_token(user: User, session: AuthSession) -> str:
    return security.create_access_token(
        str(user.id),
        extra={"tenant_id": user.tenant_id, "sid": session.family_id},
    )


def rotate_session(db: Session, *, refresh_token: str, request_id: str | None = None) -> tuple[AuthSession, str, User]:
    """Renueva la sesión: valida refresh, rota token y devuelve nueva sesión + access token."""
    try:
        payload = security.decode_token(refresh_token, expected_type="refresh")
    except pyjwt.PyJWTError:
        raise KontrolError(code="SESSION_INVALID", message="Sesión inválida o expirada", status_code=401) from None

    # Bloqueo de fila antes de leer el estado: entre comprobar `revoked_at` y
    # escribirlo hay una ventana, y sin cerrarla dos peticiones simultáneas con
    # el **mismo** refresh token prosperan las dos. Eso anularía la garantía de
    # un solo uso —que es justamente lo que permite detectar un token robado— y
    # dejaría una sesión viva que nadie volvería a usar.
    #
    # Sobre PostgreSQL, el motor de producción (P21), la segunda transacción
    # espera aquí y encuentra la sesión ya revocada. SQLite ignora `FOR UPDATE`
    # y no retiene ningún bloqueo entre leer y escribir: dos transacciones pueden
    # leer la misma sesión sin revocar antes de que ninguna escriba (demostrado
    # en AUTH-ROTACION-SQLITE-HILOS), así que la propiedad de la rotación la
    # decide además la escritura condicional de más abajo, igual en los dos motores.
    session = db.execute(
        select(AuthSession).where(AuthSession.id == payload.get("sid")).with_for_update()
    ).scalars().first()
    if not session or session.revoked_at is not None:
        raise KontrolError(code="SESSION_REVOKED", message="Sesión revocada", status_code=401)
    if session.refresh_token_hash != security.sha256_hex(refresh_token):
        raise KontrolError(code="SESSION_INVALID", message="Sesión inválida", status_code=401)
    if _as_utc(session.expires_at) < _now():
        session.revoked_at = _now()
        db.commit()
        raise KontrolError(code="SESSION_EXPIRED", message="Sesión expirada", status_code=401)

    user = db.get(User, session.user_id)
    if not user or user.status != "ACTIVE":
        raise KontrolError(code="AUTH_USER_INACTIVE", message="El usuario no está activo", status_code=403)

    if session.credential_stamp is None or session.credential_stamp != user.credential_stamp:
        _revoke_family(db, session.family_id)
        db.commit()
        raise KontrolError(code="SESSION_REVOKED", message="Sesión revocada", status_code=401)

    if session.mfa_verified_at is None and mfa_policy.requires_mfa(mfa_policy.user_policy_class(db, user)):
        _revoke_family(db, session.family_id)
        db.commit()
        raise KontrolError(code="MFA_REQUIRED", message="Debe completar el segundo factor", status_code=401)

    # Rotación: la revocación es un UPDATE condicional sobre `revoked_at IS NULL`
    # y solo quien actualiza exactamente una fila es dueño de la rotación; la otra
    # petición concurrente actualiza cero filas y recibe el mismo 401 que un token
    # ya usado. Solo el dueño crea la sesión de reemplazo.
    ahora = _now()
    revocadas = db.execute(
        update(AuthSession)
        .where(AuthSession.id == session.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=ahora, updated_at=ahora)
    ).rowcount
    if revocadas == 0:
        raise KontrolError(code="SESSION_REVOKED", message="Sesión revocada", status_code=401)
    if revocadas != 1:
        raise RuntimeError(f"rotación de sesión {session.id}: {revocadas} filas revocadas, se esperaba exactamente una")
    new_session, new_refresh = create_session(db, user=user, ip=session.ip, user_agent=session.user_agent,
        auth_method=session.auth_method, mfa_verified_at=session.mfa_verified_at, reauth_at=session.reauth_at,
        family_id=session.family_id, credential_stamp=session.credential_stamp)
    _audit(db, action="SESSION_REFRESHED", entity_type="User", entity_id=str(user.id), tenant_id=user.tenant_id, request_id=request_id)
    db.commit()
    return new_session, new_refresh, user


def _rotar_sello(user: User) -> None:
    user.credential_stamp = secrets.token_hex(16)


def _invalidar_tokens_de_reset(db: Session, *, user_id: str, excepto_id: str | None = None) -> int:
    query = (
        update(PasswordReset)
        .where(
            PasswordReset.user_id == user_id,
            PasswordReset.used_at.is_(None),
            PasswordReset.invalidated_at.is_(None),
        )
        .values(invalidated_at=_now(), updated_at=_now())
    )
    if excepto_id is not None:
        query = query.where(PasswordReset.id != excepto_id)
    return db.execute(query).rowcount


def _revoke_family(db: Session, family_id: str) -> int:
    return db.execute(
        update(AuthSession)
        .where(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=_now(), updated_at=_now())
    ).rowcount


def revoke_session(db: Session, *, session_id: str, user_id: str | None = None, request_id: str | None = None) -> None:
    session = db.get(AuthSession, session_id)
    if not session:
        raise NotFoundError(code="SESSION_NOT_FOUND", message="Sesión no encontrada")
    if user_id and session.user_id != user_id:
        raise PermissionDeniedError()
    _revoke_family(db, session.family_id)
    user = db.get(User, session.user_id)
    _audit(db, action="SESSION_REVOKED", entity_type="Session", entity_id=str(session.id), tenant_id=user.tenant_id if user else None, request_id=request_id)
    db.commit()


def revoke_user_sessions(
    db: Session,
    *,
    user_id: str,
    except_family_id: str | None = None,
    reason: str,
    actor_id: str | None = None,
    request_id: str | None = None,
) -> int:
    query = update(AuthSession).where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
    if except_family_id is not None:
        query = query.where(AuthSession.family_id != except_family_id)
    revoked = db.execute(query.values(revoked_at=_now(), updated_at=_now())).rowcount
    if revoked > 0:
        user = db.get(User, user_id)
        _audit(
            db,
            action="SESSIONS_REVOKED_SECURITY_CHANGE",
            entity_type="User",
            entity_id=user_id,
            tenant_id=user.tenant_id if user else None,
            user_id=actor_id or user_id,
            request_id=request_id,
            reason=reason,
            evidence={"reason": reason, "sessions_revoked": revoked},
        )
    return revoked


def current_session_row(db: Session, family_id: str) -> AuthSession | None:
    return db.execute(
        select(AuthSession)
        .where(
            AuthSession.family_id == family_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > _now(),
        )
        .order_by(AuthSession.created_at.desc())
    ).scalars().first()


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
    current_family_id: str | None = None,
) -> None:
    if not security.verify_password(current_password, user.password_hash):
        raise KontrolError(code="AUTH_CURRENT_PASSWORD_INVALID", message="La contraseña actual es incorrecta", status_code=401)
    errors = security.validate_password_policy(new_password)
    if errors:
        raise KontrolError(code="PASSWORD_POLICY", message="La contraseña no cumple la política", field_errors={"new_password": errors}, status_code=422)
    user.password_hash = security.hash_password(new_password)
    user.must_change_password = False
    _rotar_sello(user)
    if current_family_id:
        db.execute(
            update(AuthSession)
            .where(
                AuthSession.family_id == current_family_id,
                AuthSession.revoked_at.is_(None),
            )
            .values(credential_stamp=user.credential_stamp, updated_at=_now())
        )
    n = _invalidar_tokens_de_reset(db, user_id=str(user.id))
    if n:
        _audit(
            db,
            action="PASSWORD_RESET_TOKEN_INVALIDATED",
            entity_type="User",
            entity_id=str(user.id),
            tenant_id=user.tenant_id,
            request_id=request_id,
            reason="PASSWORD_CHANGED",
            evidence={"invalidated_tokens": n},
        )
    _audit(db, action="PASSWORD_CHANGED", entity_type="User", entity_id=str(user.id), tenant_id=user.tenant_id, request_id=request_id, reason="CAMBIO")
    revoke_user_sessions(
        db,
        user_id=str(user.id),
        except_family_id=current_family_id,
        reason="PASSWORD_CHANGED",
        request_id=request_id,
    )
    db.commit()


# --------------------------------------------------------------------------- #
# Recuperación de contraseña
# --------------------------------------------------------------------------- #
def issue_password_reset_token(db: Session, *, user: User, source: str, request_id: str | None = None) -> str:
    """Emite un token de recuperación de un solo uso.

    El token en claro solo lo recibe quien llama (la CLI de rotura de cristal);
    nunca se registra.
    """
    if source not in {"SELF", "CLI"}:
        raise ValueError(f"source inválido: {source}")
    n = _invalidar_tokens_de_reset(db, user_id=str(user.id))
    token = security.generate_secret_token(32)
    db.add(
        PasswordReset(
            user_id=str(user.id),
            token_hash=security.sha256_hex(token),
            expires_at=_now() + PASSWORD_RESET_TTL,
            source=source,
        )
    )
    if n:
        _audit(
            db,
            action="PASSWORD_RESET_TOKEN_INVALIDATED",
            entity_type="User",
            entity_id=str(user.id),
            tenant_id=user.tenant_id,
            request_id=request_id,
            reason="REISSUED",
            evidence={"invalidated_tokens": n},
        )
    if source == "CLI":
        _audit(
            db,
            action="PASSWORD_RESET_ADMIN_INITIATED",
            entity_type="User",
            entity_id=str(user.id),
            tenant_id=user.tenant_id,
            request_id=request_id,
            source="CLI",
        )
    db.commit()
    return token


def request_password_reset(db: Session, *, tenant_code: str, username: str, request_id: str | None = None) -> None:
    """Registra la petición de recuperación sin emitir token.

    Sin canal fuera de banda no hay token (D-01); nunca se revela si el
    tenant o el usuario existen.
    """
    from app.modules.audit.models import AuditEvent
    from app.modules.organization.models import Tenant

    tenant_id: str | None = None
    user: User | None = None
    tenant_row = db.execute(select(Tenant.id).where(Tenant.code == tenant_code)).scalars().first()
    if tenant_row:
        tenant_id = str(tenant_row)
        user = get_user_by_username(db, tenant_id, username)
    existing_event = db.execute(
        select(AuditEvent.id)
        .where(
            AuditEvent.action == "PASSWORD_RESET_REQUESTED",
            AuditEvent.entity_id == (str(user.id) if user else None),
            # created_at lo escribe la BD con el reloj real: la ventana se mide con ese mismo reloj, no con el inyectado.
            AuditEvent.created_at >= datetime.now(UTC) - RESET_REQUEST_AUDIT_WINDOW,
        )
        .limit(1)
    ).scalars().first()
    if user is not None and existing_event is None:
        _audit(
            db,
            action="PASSWORD_RESET_REQUESTED",
            entity_type="User",
            entity_id=str(user.id),
            tenant_id=tenant_id,
            request_id=request_id,
            reason="NOT_DELIVERABLE",
        )
        db.commit()


def confirm_password_reset(db: Session, *, token: str, new_password: str, request_id: str | None = None) -> None:
    errors = security.validate_password_policy(new_password)
    if errors:
        raise KontrolError(code="PASSWORD_POLICY", message="La contraseña no cumple la política", field_errors={"new_password": errors}, status_code=422)

    token_hash = security.sha256_hex(token)
    reset = db.execute(select(PasswordReset).where(PasswordReset.token_hash == token_hash)).scalars().first()
    if reset is None:
        _audit(
            db,
            action="PASSWORD_RESET_FAILED",
            entity_type="User",
            entity_id=None,
            request_id=request_id,
            reason="INVALID",
        )
        db.commit()
        raise KontrolError(code="RESET_TOKEN_INVALID", message="El código de recuperación no es válido", status_code=400)

    if reset.used_at is not None or reset.invalidated_at is not None:
        _audit(
            db,
            action="PASSWORD_RESET_FAILED",
            entity_type="User",
            entity_id=reset.user_id,
            request_id=request_id,
            reason="USED",
        )
        db.commit()
        raise KontrolError(code="RESET_TOKEN_USED", message="El código de recuperación ya se usó o fue reemplazado", status_code=400)

    if _as_utc(reset.expires_at) <= _now():
        _audit(
            db,
            action="PASSWORD_RESET_FAILED",
            entity_type="User",
            entity_id=reset.user_id,
            request_id=request_id,
            reason="EXPIRED",
        )
        db.commit()
        raise KontrolError(code="RESET_TOKEN_EXPIRED", message="El código de recuperación caducó", status_code=400)

    user = db.get(User, reset.user_id)
    if user is None or user.status != "ACTIVE":
        reset.invalidated_at = _now()
        _audit(
            db,
            action="PASSWORD_RESET_FAILED",
            entity_type="User",
            entity_id=reset.user_id,
            request_id=request_id,
            reason="INVALID",
        )
        db.commit()
        raise KontrolError(code="RESET_TOKEN_INVALID", message="El código de recuperación no es válido", status_code=400)

    ahora = _now()
    consumido = db.execute(
        update(PasswordReset)
        .where(
            PasswordReset.id == reset.id,
            PasswordReset.used_at.is_(None),
            PasswordReset.invalidated_at.is_(None),
        )
        .values(used_at=ahora, updated_at=ahora)
    ).rowcount
    if consumido != 1:
        db.rollback()
        raise KontrolError(code="RESET_TOKEN_USED", message="El código de recuperación ya se usó o fue reemplazado", status_code=400)

    user.password_hash = security.hash_password(new_password)
    user.must_change_password = False
    _rotar_sello(user)
    m = _invalidar_tokens_de_reset(db, user_id=str(user.id), excepto_id=str(reset.id))
    k = revoke_user_sessions(db, user_id=str(user.id), reason="PASSWORD_RESET", request_id=request_id)
    _audit(
        db,
        action="PASSWORD_RESET_COMPLETED",
        entity_type="User",
        entity_id=str(user.id),
        tenant_id=user.tenant_id,
        request_id=request_id,
        reason=reset.source,
        evidence={"revoked_sessions": k, "invalidated_tokens": m},
    )
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


#: Candado consultivo (PostgreSQL) que serializa «comprobar duplicado + insertar» en el alta de roles: `roles`
#: no tiene restricción de unicidad en la base (`ix_roles_code` es un índice simple), así que sin él dos altas
#: simultáneas del mismo código podrían entrar las dos. Sección crítica de milisegundos; SQLite serializa solo.
_BLOQUEO_ALTA_ROL = 7_003_040


def create_role(
    db: Session,
    *,
    tenant_id: str,
    code: str,
    name: str,
    company_id: str | None,
    permissions: list[str],
    actor: str | None,
) -> dict:
    """Alta de un rol **personalizado** con sus permisos, en una sola operación (FR-001-040/043/072;
    `ROLES-SIN-API-DE-ALTA`).

    Lo que decide el servidor y no el cuerpo: `protected = False` (los roles protegidos solo los crea el
    arranque), `status = "ACTIVE"`, `created_by`. Los permisos se nombran como `recurso:accion`, igual que
    los publica `list_roles`, y **todos** deben existir en el catálogo: uno desconocido rechaza el alta
    entera (422) sin crear nada; el alta nunca crea permisos. El alcance sigue el modelo vigente del
    catálogo de la instalación: `company_id` nulo = toda la instalación; si viene, la empresa debe ser del
    tenant de quien pide (el mismo control que `assign_role_to_user`). La identidad es `(code, company_id)`:
    un duplicado responde `409 ROLE_DUPLICATE`, también bajo concurrencia. Rol y permisos se confirman juntos
    o no se confirma nada. No asigna el rol a nadie.
    """
    from app.modules.organization.models import Company

    code, name = code.strip(), name.strip()
    if company_id is not None:
        empresa = db.get(Company, company_id)
        if empresa is None or str(empresa.tenant_id) != str(tenant_id):
            raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    solicitados = sorted(set(permissions))
    catalogo = {f"{p.resource}:{p.action}": p for p in db.execute(select(Permission)).scalars().all()}
    desconocidos = [c for c in solicitados if c not in catalogo]
    if desconocidos:
        raise KontrolError(
            code="PERMISSION_UNKNOWN",
            message="Uno o más permisos no existen en el catálogo",
            field_errors={"permissions": desconocidos},
            status_code=422,
        )
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:clave)"), {"clave": _BLOQUEO_ALTA_ROL})
    duplicado = db.execute(
        select(Role).where(Role.code == code, Role.company_id.is_(None) if company_id is None else Role.company_id == company_id)
    ).scalars().first()
    if duplicado is not None:
        raise ConflictError(code="ROLE_DUPLICATE", message="Ya existe un rol con ese código en ese alcance")
    rol = Role(code=code, name=name, company_id=company_id, protected=False, status="ACTIVE", created_by=actor)
    db.add(rol)
    db.flush()
    for clave in solicitados:
        db.add(RolePermission(role_id=str(rol.id), permission_id=str(catalogo[clave].id)))
    db.flush()
    _audit(
        db,
        action="ROLE_CREATED",
        entity_type="Role",
        entity_id=str(rol.id),
        tenant_id=tenant_id,
        user_id=actor,
        after={"code": code, "name": name, "company_id": company_id, "permissions": solicitados},
    )
    db.commit()
    return {
        "id": str(rol.id),
        "code": rol.code,
        "name": rol.name,
        "protected": rol.protected,
        "status": rol.status,
        "company_id": rol.company_id,
        "permissions": solicitados,
    }


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
    tenant_id: str,
    user_id: str,
    role_id: str,
    company_id: str | None = None,
    actor: str | None = None,
) -> None:
    """Asigna un rol a un usuario (FR-001-040); idempotente por par."""
    from app.modules.organization.models import Company

    user = get_user_in_tenant(db, user_id, tenant_id)
    antes = mfa_policy.user_policy_class(db, user)
    if company_id is not None:
        # La empresa llegaba del cuerpo sin comprobarse. Acotar un rol a una
        # empresa de otro tenant no es un alcance: es una fila sin sentido en la
        # tabla que decide quién administra qué.
        empresa = db.get(Company, company_id)
        if empresa is None or str(empresa.tenant_id) != str(tenant_id):
            raise NotFoundError(code="COMPANY_NOT_FOUND", message="Empresa no encontrada")
    role = db.get(Role, role_id)
    if not role:
        raise NotFoundError(code="ROLE_NOT_FOUND", message="Rol no encontrado")
    existing = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    ).scalars().first()
    if existing:
        raise ConflictError(code="ROLE_ALREADY_ASSIGNED", message="El usuario ya tiene este rol")
    asignacion = UserRole(user_id=user_id, role_id=role_id, company_id=company_id)
    db.add(asignacion)
    db.flush()
    db.expire(user)
    despues = mfa_policy.user_policy_class(db, user)
    if antes != despues:
        revoke_user_sessions(db, user_id=user_id, reason="POLICY_CLASS_CHANGED", actor_id=actor)
    _audit(
        db,
        action="ROLE_ASSIGNED",
        entity_type="UserRole",
        # `f"{user_id}:{role_id}"` son 73 caracteres en una columna de 36: la
        # ruta terminaba en 500 en cuanto la asignación no era duplicada. La
        # entidad auditada es la asignación, que tiene id propio.
        entity_id=str(asignacion.id),
        tenant_id=user.tenant_id,
        user_id=actor,
        after={"role_id": role_id, "user_id": user_id},
    )
    db.commit()


def remove_role_from_user(
    db: Session,
    *,
    tenant_id: str,
    user_id: str,
    role_id: str,
    actor: str | None = None,
) -> None:
    """Quita un rol de un usuario (FR-001-040)."""
    user = get_user_in_tenant(db, user_id, tenant_id)
    antes = mfa_policy.user_policy_class(db, user)
    row = db.execute(
        select(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
    ).scalars().first()
    if not row:
        raise NotFoundError(code="ROLE_NOT_ASSIGNED", message="El usuario no tiene este rol")
    db.delete(row)
    db.flush()
    db.expire(user)
    despues = mfa_policy.user_policy_class(db, user)
    if antes != despues:
        revoke_user_sessions(db, user_id=user_id, reason="POLICY_CLASS_CHANGED", actor_id=actor)
    _audit(
        db,
        action="ROLE_REMOVED",
        entity_type="UserRole",
        entity_id=str(row.id),
        tenant_id=user.tenant_id,
        user_id=actor,
        after={"role_id": role_id, "user_id": user_id},
    )
    db.commit()
