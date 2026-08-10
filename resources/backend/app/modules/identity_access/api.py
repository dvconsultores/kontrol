"""API de autenticación, usuarios, sesiones y contraseñas (FR-001-010..023)."""

from __future__ import annotations

from fastapi import APIRouter, Cookie, Depends, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.errors import KontrolError
from app.modules.identity_access import service as identity_service
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
    tenant_code: str
    username: str


class ResetConfirmRequest(BaseModel):
    token: str
    new_password: str


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


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    tenant_id = _resolve_tenant_id(db, body.tenant_code)
    user = identity_service.authenticate(
        db,
        tenant_id=tenant_id,
        username=body.username,
        password=body.password,
        request_id=getattr(request.state, "request_id", None),
    )
    access = security.create_access_token(str(user.id), extra={"tenant_id": tenant_id})
    session, refresh = identity_service.create_session(db, user=user, ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    _set_refresh_cookie(response, refresh)
    return {
        "access_token": access,
        "token_type": "bearer",
        "expires_in": get_settings().access_token_minutes * 60,
        "must_change_password": user.must_change_password,
        "user": {"id": str(user.id), "username": user.username},
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
    access = security.create_access_token(str(user.id), extra={"tenant_id": user.tenant_id})
    return {"access_token": access, "token_type": "bearer", "expires_in": get_settings().access_token_minutes * 60}


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
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    identity_service.change_password(
        db,
        user=user,
        current_password=body.current_password,
        new_password=body.new_password,
        request_id=getattr(request.state, "request_id", None),
    )
    return {"ok": True}


@router.post("/password-reset/request")
def reset_request(body: ResetRequest, request: Request, db: Session = Depends(get_db)):
    tenant_id = _resolve_tenant_id(db, body.tenant_code)
    token = identity_service.request_password_reset(db, tenant_id=tenant_id, username=body.username, request_id=getattr(request.state, "request_id", None))
    # En la fundación el token se devuelve al cliente para el flujo demo;
    # en producción se envía por correo seguro (SMTP diferido).
    return {"ok": True, "reset_token": token}


@router.post("/password-reset/confirm")
def reset_confirm(body: ResetConfirmRequest, request: Request, db: Session = Depends(get_db)):
    identity_service.confirm_password_reset(db, token=body.token, new_password=body.new_password, request_id=getattr(request.state, "request_id", None))
    return {"ok": True}


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


# Usuarios (administración)
users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.get("")
def list_users(db: Session = Depends(get_db), _: User = Depends(require_permission("users", "view"))):
    from sqlalchemy import select

    users = db.execute(select(User).order_by(User.created_at.desc())).scalars().all()
    return [
        {
            "id": str(u.id),
            "username": u.username,
            "email": u.email,
            "status": u.status,
            "must_change_password": u.must_change_password,
            "last_login": u.last_login.isoformat() if u.last_login else None,
            "roles": identity_service.get_user_roles(db, str(u.id)),
            "allowed_actions": {"view": True, "edit": True, "deactivate": True, "delete": False},
        }
        for u in users
    ]


@users_router.post("")
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
    role_id: str = Field(min_length=1)
    company_id: str | None = None


@users_router.post("/{user_id}/roles", dependencies=[Depends(require_permission("roles", "edit"))])
def assign_role(user_id: str, body: UserRoleAssign, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    identity_service.assign_role_to_user(db, user_id=user_id, role_id=body.role_id, company_id=body.company_id, actor=str(actor.id))
    return {"ok": True}


@users_router.delete("/{user_id}/roles/{role_id}", dependencies=[Depends(require_permission("roles", "edit"))])
def remove_role(user_id: str, role_id: str, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    identity_service.remove_role_from_user(db, user_id=user_id, role_id=role_id, actor=str(actor.id))
    return {"ok": True}


# Roles / permisos (administración)
roles_router = APIRouter(prefix="/roles", tags=["roles"])


@roles_router.get("")
def list_roles(db: Session = Depends(get_db), _: User = Depends(require_permission("roles", "view"))):
    return {"items": identity_service.list_roles(db)}
