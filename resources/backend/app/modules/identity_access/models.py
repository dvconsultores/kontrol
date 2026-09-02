"""Módulo de identidad y acceso: User, Role, Permission, RolePermission,
UserRole, UserScope, Session y PasswordReset (data-model.md §2.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.scope import Scope
from app.shared.mixins import CreatedByMixin, TimestampMixin, UUIDMixin


class User(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    __tablename__ = "users"
    __scope__ = Scope.TENANT

    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    mfa_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_attempts: Mapped[int] = mapped_column(default=0, nullable=False)
    lockout_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user_roles: Mapped[list[UserRole]] = relationship(back_populates="user", cascade="all, delete-orphan")
    user_scopes: Mapped[list[UserScope]] = relationship(back_populates="user", cascade="all, delete-orphan")
    sessions: Mapped[list[Session]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Role(UUIDMixin, TimestampMixin, CreatedByMixin, Base):
    """Catálogo de roles de la **instalación**, no del tenant.

    Se declaraba `TENANT` y no hay por dónde llegar a un tenant: la tabla no
    tiene `tenant_id` ni ninguna relación que lleve a uno. Y el comportamiento
    coincide con la estructura, no con la etiqueta: los roles los crea el
    arranque —`ADMIN`, con `company_id` nulo—, no existe ruta para crear otros,
    y `setup` reutiliza el existente cuando se da de alta un segundo tenant. Hay
    un catálogo, no uno por tenant.

    `company_id` anulable **estrecha** el alcance: un rol puede valer en toda la
    instalación o solo en una empresa.

    Que hoy sea así no significa que deba serlo siempre. Roles propios por
    tenant es una capacidad futura, registrada con responsable en el registro de
    deuda de N10; el día que se implemente, `list_roles` y `assign_role_to_user`
    tendrán que filtrar, y esa es exactamente la razón de escribir aquí lo que
    hoy es cierto en vez de dejar puesta una etiqueta que no lo era.
    """

    __tablename__ = "roles"
    __scope__ = Scope.INSTALLATION

    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    protected: Mapped[bool] = mapped_column(default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")

    role_permissions: Mapped[list[RolePermission]] = relationship(back_populates="role", cascade="all, delete-orphan")
    user_roles: Mapped[list[UserRole]] = relationship(back_populates="role", cascade="all, delete-orphan")


class Permission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "permissions"
    __scope__ = Scope.GLOBAL

    resource: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False, default="COMPANY")
    constraints: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)


class RolePermission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "role_permissions"
    #: Sigue a `Role`: une un rol de la instalación con un permiso global.
    __scope__ = Scope.INSTALLATION
    __scope_authority__ = "role_id → roles"

    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)
    permission_id: Mapped[str] = mapped_column(ForeignKey("permissions.id"), nullable=False, index=True)
    constraints: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    role: Mapped[Role] = relationship(back_populates="role_permissions")


class UserRole(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_roles"
    __scope__ = Scope.TENANT
    #: Sin columna de ámbito propia: su tenant es el de su usuario, y esa ruta
    #: es obligatoria. Una ruta que puede ser nula no es una ruta.
    __scope_authority__ = "user_id → users"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    role_id: Mapped[str] = mapped_column(ForeignKey("roles.id"), nullable=False, index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="user_roles")
    role: Mapped[Role] = relationship(back_populates="user_roles")


class UserScope(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "user_scopes"
    __scope__ = Scope.TENANT
    #: Sin columna de ámbito propia: su tenant es el de su usuario, y esa ruta
    #: es obligatoria. Una ruta que puede ser nula no es una ruta.
    __scope_authority__ = "user_id → users"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    company_id: Mapped[str | None] = mapped_column(ForeignKey("companies.id"), nullable=True)
    branch_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    establishment_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    warehouse_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    cost_center_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    validity: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, default=dict)

    user: Mapped[User] = relationship(back_populates="user_scopes")


class Session(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "sessions"
    __scope__ = Scope.TENANT
    #: Sin columna de ámbito propia: su tenant es el de su usuario, y esa ruta
    #: es obligatoria. Una ruta que puede ser nula no es una ruta.
    __scope_authority__ = "user_id → users"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    refresh_token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")


class PasswordReset(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "password_resets"
    __scope__ = Scope.TENANT
    #: Sin columna de ámbito propia: su tenant es el de su usuario, y esa ruta
    #: es obligatoria. Una ruta que puede ser nula no es una ruta.
    __scope_authority__ = "user_id → users"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
