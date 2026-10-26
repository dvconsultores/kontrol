"""API de autenticación, usuarios, sesiones y contraseñas (FR-001-010..023)."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import (
    AuthContext,
    get_current_auth,
    get_current_user,
    read_bearer_credentials,
    require_permission,
    require_recent_reauth,
)
from app.core.errors import KontrolError
from app.modules.identity_access import mfa_service
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Session as AuthSession
from app.modules.identity_access.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "kontrol_refresh"


class LoginRequest(BaseModel):
    tenant_code: str = Field(min_length=1)
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_code: str
    username: str


class ResetConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str
    new_password: str


class ResetAcknowledged(BaseModel):
    """Respuesta fija: no revela si la cuenta existe ni contiene el código."""

    ok: bool = True


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    email: EmailStr | None = None
    password: str = Field(min_length=10)
    must_change_password: bool = True


def _set_refresh_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    max_age = settings.refresh_token_days * 24 * 3600
    response.set_cookie(
        key=REFRESH_COOKIE,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path="/api/v1/auth",
        max_age=max_age,
    )


def _resolve_tenant_id(db: Session, tenant_code: str) -> str:
    from sqlalchemy import select

    from app.modules.organization.models import Tenant

    tenant = db.execute(select(Tenant).where(Tenant.code == tenant_code)).scalars().first()
    if not tenant:
        raise KontrolError(code="AUTH_INVALID_CREDENTIALS", message="Credenciales inválidas", status_code=401)
    return str(tenant.id)


class MfaVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: str = Field(min_length=1)
    code: str | None = None
    recovery_code: str | None = None

    @model_validator(mode="after")
    def _exactamente_uno(self) -> MfaVerifyRequest:
        if (self.code is None) == (self.recovery_code is None):
            raise ValueError("Debe enviar exactamente uno de code o recovery_code")
        return self


class MfaEnrollmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: str | None = None


class MfaEnrollmentConfirmRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_token: str | None = None
    code: str = Field(min_length=1)


class ReauthRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    password: str = Field(min_length=1)
    code: str | None = None
    recovery_code: str | None = None


def _authenticated_payload(user: User, session: AuthSession, extra: dict | None = None) -> dict:
    payload = {
        "status": "AUTHENTICATED",
        "access_token": identity_service.issue_access_token(user, session),
        "token_type": "bearer",
        "expires_in": get_settings().access_token_minutes * 60,
        "must_change_password": user.must_change_password,
        "user": {"id": str(user.id), "username": user.username},
    }
    if extra:
        payload.update(extra)
    return payload


def _sesion_emitida(res: mfa_service.LoginResult) -> tuple[AuthSession, str]:
    """La sesión y el refresh de un login completado; su ausencia sería un fallo interno, nunca un acceso sin sesión."""
    if res.session is None or res.refresh_token is None:
        raise RuntimeError("login completado sin sesión emitida")
    return res.session, res.refresh_token


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    tenant_id = _resolve_tenant_id(db, body.tenant_code)
    user = identity_service.verify_password_stage(
        db,
        tenant_id=tenant_id,
        username=body.username,
        password=body.password,
        request_id=getattr(request.state, "request_id", None),
    )
    res = mfa_service.start_login(
        db,
        user=user,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
    )
    if res.status == "AUTHENTICATED":
        session, refresh = _sesion_emitida(res)
        _set_refresh_cookie(response, refresh)
        return _authenticated_payload(res.user, session)
    if res.status == "MFA_REQUIRED":
        return {
            "status": "MFA_REQUIRED",
            "challenge_token": res.challenge_token,
            "expires_in": 300,
            "methods": ["TOTP", "RECOVERY_CODE"],
        }
    return {
        "status": "MFA_ENROLLMENT_REQUIRED",
        "challenge_token": res.challenge_token,
        "expires_in": 300,
    }


@router.post("/refresh")
def refresh(
    request: Request,
    response: Response,
    kontrol_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE),
    db: Session = Depends(get_db),
):
    if not kontrol_refresh:
        raise KontrolError(code="AUTH_REQUIRED", message="Debe iniciar sesión", status_code=401)
    session, new_refresh, user = identity_service.rotate_session(db, refresh_token=kontrol_refresh, request_id=getattr(request.state, "request_id", None))
    _set_refresh_cookie(response, new_refresh)
    access = identity_service.issue_access_token(user, session)
    return {"access_token": access, "token_type": "bearer", "expires_in": get_settings().access_token_minutes * 60}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Usuario actual + permisos efectivos (resource:action) para el guard de UI
    (FR-001-042; KAUD-004). El backend sigue siendo la autoridad."""
    permissions = identity_service.get_user_permissions(db, user)
    return {
        "user": {"id": str(user.id), "username": user.username, "tenant_id": user.tenant_id,
                 "must_change_password": user.must_change_password},
        "permissions": permissions,
    }


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh = request.cookies.get(REFRESH_COOKIE)
    if refresh:
        try:
            payload = security.decode_token(refresh, expected_type="refresh")
            if payload.get("sid"):
                identity_service.revoke_session(db, session_id=payload["sid"])
        except Exception:
            pass
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    return {"ok": True}


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    user, session = auth.user, auth.session
    identity_service.change_password(
        db,
        user=user,
        current_password=body.current_password,
        new_password=body.new_password,
        current_family_id=session.family_id,
        request_id=getattr(request.state, "request_id", None),
    )
    return {"ok": True}


@router.post("/password-reset/request", status_code=202, response_model=ResetAcknowledged)
def reset_request(body: ResetRequest, request: Request, db: Session = Depends(get_db)):
    """Respuesta idéntica exista o no la cuenta (R-RST-02); sin canal fuera de
    banda no se emite código; la recuperación soportada es la rotura de cristal
    local."""
    identity_service.request_password_reset(
        db,
        tenant_code=body.tenant_code,
        username=body.username,
        request_id=getattr(request.state, "request_id", None),
    )
    return ResetAcknowledged()


@router.post("/password-reset/confirm", response_model=ResetAcknowledged)
def reset_confirm(body: ResetConfirmRequest, request: Request, db: Session = Depends(get_db)):
    identity_service.confirm_password_reset(db, token=body.token, new_password=body.new_password, request_id=getattr(request.state, "request_id", None))
    return ResetAcknowledged()


@router.get("/sessions")
def sessions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sessions = identity_service.list_sessions(db, user_id=str(user.id))
    return [
        {
            "id": str(s.id),
            "ip": s.ip,
            "user_agent": s.user_agent,
            "created_at": s.created_at.isoformat(),
            "expires_at": s.expires_at.isoformat(),
            "revoked": s.revoked_at is not None,
        }
        for s in sessions
    ]


@router.delete("/sessions/{session_id}")
def revoke_session(session_id: str, request: Request, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    identity_service.revoke_session(db, session_id=session_id, user_id=str(user.id), request_id=getattr(request.state, "request_id", None))
    return {"ok": True}


@router.post("/mfa/verify")
def mfa_verify(body: MfaVerifyRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    res = mfa_service.verify_login(
        db,
        challenge_token=body.challenge_token,
        code=body.code,
        recovery_code=body.recovery_code,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        request_id=getattr(request.state, "request_id", None),
    )
    session, refresh = _sesion_emitida(res)
    _set_refresh_cookie(response, refresh)
    return _authenticated_payload(
        res.user,
        session,
        extra={"recovery_codes_remaining": res.recovery_codes_remaining},
    )


@router.post("/mfa/enrollment")
def mfa_enrollment(
    body: MfaEnrollmentRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Con `challenge_token` (alta forzada desde el login) no requiere sesión: el desafío es la credencial.
    Sin él, alta voluntaria o reemplazo: exige `Authorization: Bearer`."""
    if body.challenge_token:
        res = mfa_service.start_enrollment(
            db,
            challenge_token=body.challenge_token,
            user=None,
            session=None,
            request_id=getattr(request.state, "request_id", None),
        )
    else:
        auth = get_current_auth(read_bearer_credentials(request), db)
        res = mfa_service.start_enrollment(
            db,
            challenge_token=None,
            user=auth.user,
            session=auth.session,
            request_id=getattr(request.state, "request_id", None),
        )
    response.headers["Cache-Control"] = "no-store"
    return res


@router.post("/mfa/enrollment/confirm")
def mfa_enrollment_confirm(
    body: MfaEnrollmentConfirmRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Con `challenge_token` (alta forzada desde el login) no requiere sesión: el desafío es la credencial.
    Sin él, alta voluntaria o reemplazo: exige `Authorization: Bearer`."""
    if body.challenge_token:
        res = mfa_service.confirm_enrollment(
            db,
            challenge_token=body.challenge_token,
            user=None,
            session=None,
            code=body.code,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=getattr(request.state, "request_id", None),
        )
    else:
        auth = get_current_auth(read_bearer_credentials(request), db)
        res = mfa_service.confirm_enrollment(
            db,
            challenge_token=None,
            user=auth.user,
            session=auth.session,
            code=body.code,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            request_id=getattr(request.state, "request_id", None),
        )
    response.headers["Cache-Control"] = "no-store"
    if res.login:
        session, refresh = _sesion_emitida(res.login)
        _set_refresh_cookie(response, refresh)
        return _authenticated_payload(
            res.login.user,
            session,
            extra={"recovery_codes": res.recovery_codes},
        )
    return {"recovery_codes": res.recovery_codes}


@router.get("/mfa")
def mfa(auth: AuthContext = Depends(get_current_auth), db: Session = Depends(get_db)):
    user = auth.user
    return mfa_service.mfa_status(db, user=user)


@router.post("/mfa/recovery-codes", dependencies=[Depends(require_recent_reauth)])
def mfa_recovery_codes(
    request: Request,
    response: Response,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    user, session = auth.user, auth.session
    response.headers["Cache-Control"] = "no-store"
    return {
        "recovery_codes": mfa_service.regenerate_recovery_codes(
            db,
            user=user,
            session=session,
            request_id=getattr(request.state, "request_id", None),
        )
    }


@router.delete("/mfa", status_code=204, dependencies=[Depends(require_recent_reauth)])
def mfa_disable(
    request: Request,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    user, session = auth.user, auth.session
    mfa_service.remove_own_factor(
        db,
        user=user,
        session=session,
        request_id=getattr(request.state, "request_id", None),
    )
    return Response(status_code=204)


@router.post("/reauth")
def reauth(
    body: ReauthRequest,
    request: Request,
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    user, session = auth.user, auth.session
    return {
        "reauth_valid_until": mfa_service.reauthenticate(
            db,
            user=user,
            session=session,
            password=body.password,
            code=body.code,
            recovery_code=body.recovery_code,
            request_id=getattr(request.state, "request_id", None),
        ).isoformat()
    }


# Usuarios (administración)
users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("")
def list_users(db: Session = Depends(get_db), actor: User = Depends(require_permission("users", "view"))):
    """Los usuarios **del tenant de quien pregunta**.

    Era un `select(User)` sin `where`. Devolvía nombre, correo, último acceso y
    roles de todos los usuarios de la instalación: el censo completo entregado a
    quien solo administra su tenant.
    """
    from sqlalchemy import select

    users = db.execute(
        select(User).where(User.tenant_id == actor.tenant_id)
        .order_by(User.created_at.desc())).scalars().all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "status": u.status,
            "must_change_password": u.must_change_password,
            "mfa_enabled": u.mfa_enabled,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "roles": identity_service.get_user_roles(db, str(u.id)),
            "allowed_actions": {"view": True, "edit": True, "deactivate": True, "delete": False},
        }
        for u in users
    ]


@users_router.post("", dependencies=[Depends(require_recent_reauth)])
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("users", "create")),
):
    errors = security.validate_password_policy(body.password)
    if errors:
        raise KontrolError(code="PASSWORD_POLICY", message="La contraseña no cumple la política", field_errors={"password": errors}, status_code=422)
    user = identity_service.create_user(
        db,
        tenant_id=actor.tenant_id,
        username=body.username,
        email=body.email,
        password=body.password,
        must_change_password=body.must_change_password,
        created_by=str(actor.id),
    )
    db.commit()
    db.refresh(user)
    return {"id": str(user.id), "username": user.username}


class UserRoleAssign(BaseModel):
    # Campos ocultos (protected, status…) en el cuerpo son un 422, no algo ignorado en silencio (Spec 003).
    model_config = ConfigDict(extra="forbid")
    role_id: str = Field(min_length=1)
    company_id: str | None = None


@users_router.post("/{user_id}/roles", dependencies=[Depends(require_permission("roles", "edit")), Depends(require_recent_reauth)])
def assign_role(user_id: str, body: UserRoleAssign, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    identity_service.assign_role_to_user(db, tenant_id=actor.tenant_id, user_id=user_id,
                                         role_id=body.role_id, company_id=body.company_id,
                                         actor=str(actor.id))
    return {"ok": True}


@users_router.delete("/{user_id}/roles/{role_id}", dependencies=[Depends(require_permission("roles", "edit")), Depends(require_recent_reauth)])
def remove_role(user_id: str, role_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    identity_service.remove_role_from_user(db, tenant_id=actor.tenant_id, user_id=user_id,
                                           role_id=role_id, actor=str(actor.id))
    return {"ok": True}


@users_router.post("/{user_id}/mfa/reset", status_code=204, dependencies=[Depends(require_recent_reauth)])
def mfa_reset(
    user_id: str,
    request: Request,
    actor: User = Depends(require_permission("users", "mfa_reset")),
    auth: AuthContext = Depends(get_current_auth),
    db: Session = Depends(get_db),
):
    session = auth.session
    mfa_service.admin_reset(
        db,
        actor=actor,
        target_user_id=user_id,
        session=session,
        request_id=getattr(request.state, "request_id", None),
    )
    return Response(status_code=204)


# Roles / permisos (administración)
roles_router = APIRouter(prefix="/roles", tags=["roles"])


@roles_router.get("")
def list_roles(db: Session = Depends(get_db), actor: User = Depends(require_permission("roles", "view"))):
    return {"items": identity_service.list_roles_for_actor(db, actor)}


class RoleCreate(BaseModel):
    """Lo que el llamador posee del alta de un rol. `extra="forbid"`: `protected`, `status`, `created_by` o
    cualquier campo interno en el cuerpo es un 422, no un campo ignorado en silencio."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64, pattern=r"^\S+$")
    name: str = Field(min_length=1, max_length=200)
    company_id: str | None = None
    permissions: list[str] = Field(default_factory=list)


class RoleOut(BaseModel):
    id: str
    code: str
    name: str
    protected: bool
    status: str
    company_id: str | None
    permissions: list[str]


@roles_router.post("", status_code=201, response_model=RoleOut, dependencies=[Depends(require_recent_reauth)])
def create_role(
    body: RoleCreate,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("roles", "create")),
):
    """Alta de un rol personalizado con sus permisos (FR-001-040; `ROLES-SIN-API-DE-ALTA`). El tenant es el
    del actor; `company_id` opcional acota el rol a una empresa de ese tenant; los permisos se nombran como
    `recurso:accion`. No asigna el rol a ningún usuario."""
    return identity_service.create_role(
        db,
        tenant_id=actor.tenant_id,
        code=body.code,
        name=body.name,
        company_id=body.company_id,
        permissions=body.permissions,
        actor=str(actor.id),
    )
