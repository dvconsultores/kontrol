"""Ayudante compartido para pruebas de restauración. No contiene casos de prueba."""

from __future__ import annotations

import hashlib
import os
import secrets
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2
import psycopg2.sql
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session as OrmSession

from app.core.database import init_models
from app.modules.documents.models import StoredFile
from app.modules.identity_access.mfa_crypto import encrypt_secret
from app.modules.identity_access.models import MfaFactor
from app.modules.identity_access.models import Session as SesionModelo
from app.modules.identity_access.service import create_user
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.reporting.models import ReportExport
from app.ops.backup_pg import pg_connect_kwargs
from app.shared.audit import record_audit

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")


def es_postgres() -> bool:
    """Devuelve si hay una URL PostgreSQL para las pruebas."""
    return bool(PG_URL and PG_URL.startswith("postgresql"))


def crear_base(prefijo: str) -> str:
    """Crea una base de datos efímera y devuelve su URL SQLAlchemy."""
    nombre = f"{prefijo}_{uuid.uuid4().hex[:10]}"
    admin_url = make_url(PG_URL).set(database="postgres")
    conn = psycopg2.connect(**pg_connect_kwargs(admin_url.render_as_string(hide_password=False)))
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                psycopg2.sql.SQL("CREATE DATABASE {}").format(
                    psycopg2.sql.Identifier(nombre)
                )
            )
    finally:
        conn.close()
    return make_url(PG_URL).set(database=nombre).render_as_string(hide_password=False)


def borrar_base(url: str) -> None:
    """Elimina una base de datos efímera, terminando conexiones activas."""
    db_name = make_url(url).database
    admin_url = make_url(PG_URL).set(database="postgres")
    conn = psycopg2.connect(
        **pg_connect_kwargs(admin_url.render_as_string(hide_password=False))
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                psycopg2.sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    psycopg2.sql.Identifier(db_name)
                )
            )
    finally:
        conn.close()


def migrar(url: str) -> None:
    """Aplica las migraciones de Alembic a una base de datos."""
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=Path(__file__).resolve().parents[1],
        env={**os.environ, "KONTROL_DB_URL": url},
        check=True,
        capture_output=True,
    )


@dataclass
class MundoCopia:
    """Estado sembrado de una instalación de prueba."""

    url: str
    storage_root: Path
    volume: Path
    installation_id: str
    public_key_pem: str
    private_key_pem: str
    tenant_ids: list[str]
    documentos: dict[str, bytes]


def sembrar(url: str, base: Path) -> MundoCopia:
    """Crea una instalación con tenants, documentos, exportación, MFA y sesión."""
    init_models()
    engine = create_engine(url)
    db = OrmSession(engine)

    private_key = Ed25519PrivateKey.generate()
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    public_key_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    volume = base / "volume"
    volume.mkdir(parents=True, exist_ok=True)
    key_file = volume / "installation_private_key.pem"
    key_file.write_text(private_key_pem)
    key_file.chmod(0o600)

    installation_id = f"KTL-QA-{uuid.uuid4().hex[:8]}"
    installation = Installation(
        installation_uuid=installation_id,
        public_key=public_key_pem,
        state="ACTIVE",
    )
    db.add(installation)
    db.flush()

    storage_root = base / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    tenant_ids: list[str] = []
    documentos: dict[str, bytes] = {}

    for i in range(2):
        tenant = Tenant(
            installation_id=installation.id,
            code=f"T{i}{uuid.uuid4().hex[:6]}",
            name=f"Tenant {i}",
        )
        db.add(tenant)
        db.flush()
        tenant_ids.append(str(tenant.id))

        company = Company(
            tenant_id=str(tenant.id),
            code="C1",
            legal_name=f"Empresa {i}",
            rif="J-12345678-9",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        db.add(company)
        db.flush()

        username = f"u{uuid.uuid4().hex[:8]}"
        user = create_user(
            db,
            tenant_id=str(tenant.id),
            username=username,
            email=None,
            password=secrets.token_urlsafe(18),
            must_change_password=False,
            created_by=None,
        )
        db.flush()

        if i == 0:
            factor_id = str(uuid.uuid4())
            kid, blob = encrypt_secret(
                os.urandom(20), aad=f"{str(tenant.id)}|{str(user.id)}|{factor_id}"
            )
            factor = MfaFactor(
                id=factor_id,
                tenant_id=str(tenant.id),
                user_id=str(user.id),
                key_id=kid,
                secret_ciphertext=blob,
                status="ACTIVE",
            )
            db.add(factor)

        sesion = SesionModelo(
            user_id=user.id,
            family_id=str(uuid.uuid4()),
            refresh_token_hash="0" * 64,
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        db.add(sesion)
        db.flush()

        if i == 0:
            record_audit(
                db,
                action="SESSION_REVOKED",
                entity_type="Session",
                entity_id=str(sesion.id),
                tenant_id=str(tenant.id),
                source="API",
            )

        for j in range(2):
            storage_key = f"2026/10/28/{secrets.token_urlsafe(18)}"
            content = os.urandom(256)
            documentos[storage_key] = content
            file_path = storage_root / "documents" / storage_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(content)
            stored = StoredFile(
                company_id=company.id,
                original_name=f"doc-{j}.bin",
                mime_type="application/octet-stream",
                size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                storage_key=storage_key,
                status="AVAILABLE",
                uploaded_at=datetime.now(UTC),
            )
            db.add(stored)

        export_path = storage_root / "exports" / f"report-{uuid.uuid4().hex}.csv"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text("data")
        export = ReportExport(
            company_id=company.id,
            report_key=f"report-{uuid.uuid4().hex}",
            format="CSV",
            file_ref=str(export_path.relative_to(storage_root / "exports")),
            status="DONE",
        )
        db.add(export)

    db.commit()
    db.close()
    engine.dispose()

    return MundoCopia(
        url=url,
        storage_root=storage_root,
        volume=volume,
        installation_id=installation_id,
        public_key_pem=public_key_pem,
        private_key_pem=private_key_pem,
        tenant_ids=tenant_ids,
        documentos=documentos,
    )
