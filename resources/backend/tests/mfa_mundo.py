"""Mundo de pruebas reutilizable para el contrato MFA.

Construye una instalación KONTROL con una licencia y un reloj inyectable, y
expone helpers para crear usuarios con roles sensibles y completar altas o
verificaciones MFA por la API.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from mfa_apoyo import clave_de_prueba, codigo_totp
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.database import Base, get_db, init_models
from app.modules.audit.models import AuditEvent
from app.modules.identity_access import service as identity_service
from app.modules.identity_access.models import Role, User, UserRole
from app.modules.identity_access.models import Session as AuthSession
from app.modules.licensing import service as licensing_service
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.setup.api import SetupRequest, _bootstrap_roles, initialize

CONTRASENA = "Kontrol2026Segura!"
API = "/api/v1"


@dataclass
class MundoMfa:
    client: TestClient
    factory: sessionmaker
    tenant_id: str
    company_id: str
    tenant_b_id: str
    admin_id: str


@dataclass
class AltaMfa:
    cabeceras: dict[str, str]
    clave_manual: str
    codigos: list[str]
    respuesta: dict


def construir_mundo_y_app(engine=None):
    """Prepara base de datos, app y cliente según el patrón de prueba del repo."""
    if engine is None:
        from conftest import make_engine

        engine = make_engine()
    init_models()
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)

    import app.core.database as dm

    dm._engine = engine  # type: ignore[attr-defined]
    dm._SessionLocal = factory  # type: ignore[attr-defined]

    db = factory()
    initialize(
        db,
        SetupRequest(
            tenant_code="DEMO",
            tenant_name="Empresa Demo",
            company_code="D1",
            company_legal_name="Demo C.A.",
            company_rif="J-12345678-9",
            admin_username="admin",
            admin_password=CONTRASENA,
        ),
    )
    _import_license(db)

    inst = db.execute(select(Installation).limit(1)).scalars().first()
    assert inst is not None
    tenant = db.execute(select(Tenant).where(Tenant.code == "DEMO")).scalars().first()
    assert tenant is not None
    company = db.execute(
        select(Company).where(Company.tenant_id == str(tenant.id))
    ).scalars().first()
    assert company is not None
    admin_user = db.execute(
        select(User).where(User.username == "admin", User.tenant_id == str(tenant.id))
    ).scalars().first()
    assert admin_user is not None

    tenant_b = Tenant(
        installation_id=str(inst.id),
        code="DEMO2",
        name="Empresa B",
        plan="MONO_COMPANY",
        status="ACTIVE",
    )
    db.add(tenant_b)
    db.flush()
    company_b = Company(
        tenant_id=str(tenant_b.id),
        code="B1",
        legal_name="Empresa B CA",
        rif="J-87654321-0",
        legal_type="JURIDICA",
        functional_currency="VED",
        status="ACTIVE",
    )
    db.add(company_b)
    db.flush()
    user_b = identity_service.create_user(
        db,
        tenant_id=str(tenant_b.id),
        username="admin2",
        email="admin2@b.com",
        password=CONTRASENA,
        created_by=None,
    )
    admin_role_b = _bootstrap_roles(db, str(tenant_b.id), str(user_b.id))
    db.add(UserRole(user_id=str(user_b.id), role_id=str(admin_role_b.id), company_id=None))
    db.commit()

    identity_service.create_role(
        db,
        tenant_id=str(tenant.id),
        code="R_CONSULTA",
        name="Consulta",
        company_id=None,
        permissions=["dashboard:view", "inventario:view"],
        actor=str(admin_user.id),
    )
    identity_service.create_role(
        db,
        tenant_id=str(tenant.id),
        code="R_ALMACEN",
        name="Almacen",
        company_id=None,
        permissions=["inventario:view", "inventario:transition"],
        actor=str(admin_user.id),
    )
    identity_service.create_role(
        db,
        tenant_id=str(tenant.id),
        code="R_GESTOR_MFA",
        name="Gestor MFA",
        company_id=None,
        permissions=["users:view", "users:mfa_reset"],
        actor=str(admin_user.id),
    )
    db.close()

    from app.main import create_app

    app = create_app()

    def _override_get_db():
        d = factory()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app)

    return (
        factory,
        str(tenant.id),
        str(company.id),
        str(tenant_b.id),
        str(admin_user.id),
        client,
    )


def _import_license(db: Session) -> None:
    key = Ed25519PrivateKey.generate()
    pub = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("utf-8")
    )
    inst = db.execute(select(Installation).limit(1)).scalars().first()
    assert inst is not None
    now = datetime.now(UTC)
    payload = {
        "issuer": "K",
        "license_id": "LIC-MFA",
        "installation_id": inst.installation_uuid,
        "customer_id": "C1",
        "contract_id": "C1",
        "company_tax_id": "J-12345678-9",
        "period_start": (now - timedelta(days=30)).isoformat(),
        "period_end": (now + timedelta(days=120)).isoformat(),
        "critical_warning_start": (now + timedelta(days=180)).isoformat(),
        "read_only_start": (now + timedelta(days=200)).isoformat(),
        "entitlements": {"companies": 1, "users": 200, "modules": ["*"]},
        "minimum_version": "1.0.0",
        "kid": "kontrol-lic-2026-01",
    }
    sig = key.sign(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hex()
    os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = pub
    get_settings.cache_clear()
    licensing_service.import_license(db, payload=payload, signature_hex=sig, source="MANUAL")
    get_settings.cache_clear()


@contextmanager
def mundo_mfa(engine=None) -> Iterator[MundoMfa]:
    """Fabrica un mundo de API con licencia, roles sintéticos y claves MFA de prueba."""
    prev_mfa = os.environ.get("KONTROL_MFA_KEYS")
    prev_license = os.environ.get("KONTROL_LICENSE_PUBLIC_KEY_PEM")
    os.environ["KONTROL_MFA_KEYS"] = clave_de_prueba()
    get_settings.cache_clear()
    motor_propio = engine is None

    try:
        factory, tenant_id, company_id, tenant_b_id, admin_id, client = (
            construir_mundo_y_app(engine)
        )
        yield MundoMfa(
            client=client,
            factory=factory,
            tenant_id=tenant_id,
            company_id=company_id,
            tenant_b_id=tenant_b_id,
            admin_id=admin_id,
        )
    finally:
        if prev_mfa is None:
            os.environ.pop("KONTROL_MFA_KEYS", None)
        else:
            os.environ["KONTROL_MFA_KEYS"] = prev_mfa
        if prev_license is None:
            os.environ.pop("KONTROL_LICENSE_PUBLIC_KEY_PEM", None)
        else:
            os.environ["KONTROL_LICENSE_PUBLIC_KEY_PEM"] = prev_license
        get_settings.cache_clear()
        import app.core.database as dm

        if motor_propio and getattr(dm, "_engine", None) is not None:
            dm._engine.dispose()


def crear_usuario(
    mundo: MundoMfa,
    usuario: str,
    *,
    rol: str | None = None,
    admin: bool = False,
    funcional: bool = False,
    tenant: str = "DEMO",
    must_change_password: bool = False,
) -> str:
    """Crea un usuario en el tenant indicado y le asigna un rol opcional."""
    tenant_id = mundo.tenant_id if tenant == "DEMO" else mundo.tenant_b_id
    db: Session = mundo.factory()
    try:
        user = identity_service.create_user(
            db,
            tenant_id=tenant_id,
            username=usuario,
            email=None,
            password=CONTRASENA,
            must_change_password=must_change_password,
            created_by=None,
        )
        db.flush()
        if rol is not None:
            role = db.execute(
                select(Role).where(
                    Role.code == rol,
                    Role.protected.is_(False),
                    Role.company_id.is_(None),
                )
            ).scalars().first()
            if role is None:
                raise AssertionError(f"Rol {rol} no existe en {tenant}")
            db.add(UserRole(user_id=str(user.id), role_id=str(role.id), company_id=None))
        if admin:
            role = db.execute(
                select(Role).where(
                    Role.code == "ADMIN",
                    Role.protected.is_(True),
                    Role.company_id.is_(None),
                )
            ).scalars().first()
            if role is None:
                raise AssertionError(f"Rol ADMIN no existe en {tenant}")
            db.add(UserRole(user_id=str(user.id), role_id=str(role.id), company_id=None))
        if funcional:
            role = (
                db.query(Role)
                .filter(
                    Role.code == "FUNCIONAL_COMPLETO",
                    Role.protected.is_(True),
                    Role.company_id.is_(None),
                )
                .one_or_none()
            )
            assert role is not None, "Rol FUNCIONAL_COMPLETO no encontrado"
            db.add(UserRole(user_id=str(user.id), role_id=str(role.id), company_id=None))
        db.commit()
        return str(user.id)
    finally:
        db.close()


def login(
    client: TestClient,
    usuario: str,
    *,
    tenant: str = "DEMO",
    contrasena: str = CONTRASENA,
):
    """Llama al endpoint de login con las credenciales indicadas."""
    return client.post(
        f"{API}/auth/login",
        json={"tenant_code": tenant, "username": usuario, "password": contrasena},
    )


def alta_por_desafio(
    client: TestClient, reloj, usuario: str, *, tenant: str = "DEMO"
) -> AltaMfa:
    """Completa un alta MFA a partir del desafío de enrollment."""
    r = login(client, usuario, tenant=tenant)
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "MFA_ENROLLMENT_REQUIRED", r.text
    challenge_token = r.json()["challenge_token"]
    assert isinstance(challenge_token, str) and challenge_token, r.text

    r = client.post(f"{API}/auth/mfa/enrollment", json={"challenge_token": challenge_token})
    assert r.status_code == 200, r.text
    alta = r.json()
    manual_key = alta.get("manual_key")
    assert manual_key, r.text
    assert isinstance(manual_key, str), r.text

    reloj.siguiente_paso()
    codigo = codigo_totp(manual_key, reloj.ahora())

    r = client.post(
        f"{API}/auth/mfa/enrollment/confirm",
        json={"challenge_token": challenge_token, "code": codigo},
    )
    assert r.status_code == 200, r.text
    confirmacion = r.json()
    access_token = confirmacion.get("access_token")
    assert isinstance(access_token, str) and access_token, r.text
    recovery_codes = confirmacion.get("recovery_codes")
    assert isinstance(recovery_codes, list), r.text
    return AltaMfa(
        cabeceras={"Authorization": f"Bearer {access_token}"},
        clave_manual=manual_key,
        codigos=[str(c) for c in recovery_codes],
        respuesta=confirmacion,
    )


def entrar_con_totp(
    client: TestClient, reloj, usuario: str, clave_manual: str, *, tenant: str = "DEMO"
) -> dict[str, str]:
    """Inicia sesión con TOTP y devuelve cabeceras Bearer."""
    r = login(client, usuario, tenant=tenant)
    assert r.status_code == 200, r.text
    assert r.json().get("status") == "MFA_REQUIRED", r.text
    challenge_token = r.json()["challenge_token"]

    reloj.siguiente_paso()
    codigo = codigo_totp(clave_manual, reloj.ahora())
    r = client.post(
        f"{API}/auth/mfa/verify", json={"challenge_token": challenge_token, "code": codigo}
    )
    assert r.status_code == 200, r.text
    access_token = r.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


def sesiones_de(mundo: MundoMfa, user_id: str) -> list[AuthSession]:
    """Devuelve las filas de sesión del usuario indicado."""
    db: Session = mundo.factory()
    try:
        return list(
            db.execute(select(AuthSession).where(AuthSession.user_id == user_id))
            .scalars()
            .all()
        )
    finally:
        db.close()


def eventos(mundo: MundoMfa, accion: str | None = None) -> list[AuditEvent]:
    """Devuelve las filas de auditoría, filtradas opcionalmente por acción."""
    db: Session = mundo.factory()
    try:
        query = select(AuditEvent)
        if accion is not None:
            query = query.where(AuditEvent.action == accion)
        return list(db.execute(query).scalars().all())
    finally:
        db.close()
