#!/usr/bin/env python3
"""QA end-to-end de copia, desastre y restauración de KONTROL (AD-B11).

Se ejecuta desde la raíz del repositorio con el Python del backend:

    resources/backend/.venv/bin/python qa/backup_restore_cert.py

Entorno requerido:
    KONTROL_TEST_DB_URL
    KONTROL_PG_BIN_DIR
    KONTROL_CLAMSCAN_PATH
    KONTROL_CLAMAV_DB
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
import psycopg2
import psycopg2.sql
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from sqlalchemy.engine import make_url

RAIZ = Path(__file__).resolve().parents[1]
BACKEND = RAIZ / "resources" / "backend"
PY = sys.executable
HTTP_TIMEOUT = 30.0
HEALTH_INTERVAL_S = 0.5
HEALTH_MAX_S = 90.0
TOTP_STEP_S = 30
TOTP_DIGITS = 6
RPO_OBJETIVO_S = 900
RTO_OBJETIVO_S = 14400


class QAError(Exception):
    """Error controlado del propio guion."""


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _duracion(inicio: float) -> float:
    return round(time.monotonic() - inicio, 3)


@dataclass(frozen=True)
class Secretos:
    admin_password: str
    backup_key: str
    secret_key_src: str
    secret_key_dst: str
    mfa_ring: str
    license_public_pem: str
    license_private_pem: str
    manual_key: str | None = None
    tokens: list[str] = field(default_factory=list)

    @classmethod
    def generar(cls) -> Secretos:
        private_key = Ed25519PrivateKey.generate()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("ascii")
        public_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        return cls(
            admin_password=f"Kb{secrets.token_hex(8)}Z9",
            backup_key=base64.urlsafe_b64encode(os.urandom(32)).decode("ascii").rstrip("="),
            secret_key_src=secrets.token_urlsafe(48),
            secret_key_dst=secrets.token_urlsafe(48),
            mfa_ring=(
                f"kbk{secrets.token_hex(4)}:"
                + base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
            ),
            license_public_pem=public_pem,
            license_private_pem=private_pem,
        )

    def valores(self) -> list[str]:
        valores = [
            self.admin_password,
            self.backup_key,
            self.secret_key_src,
            self.secret_key_dst,
            self.mfa_ring,
            self.license_private_pem,
        ]
        if self.manual_key:
            valores.append(self.manual_key)
            valores.append(self.manual_key.replace(" ", ""))
        valores.extend(self.tokens)
        return [v for v in valores if v]


def entorno_producto(
    db_url: str,
    storage: Path,
    volume: Path,
    secret_key: str,
    secretos: Secretos,
) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("KONTROL_TEST_DB_URL", None)
    env.update(
        {
            "KONTROL_DB_URL": db_url,
            "KONTROL_STORAGE_PATH": str(storage),
            "KONTROL_INSTALLATION_VOLUME_PATH": str(volume),
            "KONTROL_BACKUP_PATH": str(RAIZ / "qa" / "backup-runs" / _run_actual / "trabajo" / "copias"),
            "KONTROL_SECRET_KEY": secret_key,
            "KONTROL_MFA_KEYS": secretos.mfa_ring,
            "KONTROL_ENVIRONMENT": "local",
            "KONTROL_LOG_JSON": "false",
            "KONTROL_COOKIE_SECURE": "false",
            "KONTROL_LICENSE_PUBLIC_KEY_PEM": secretos.license_public_pem,
            "KONTROL_DOCUMENT_SCANNER": "clamscan",
            "KONTROL_BACKUP_KEY": secretos.backup_key,
            "PYTHONPATH": str(BACKEND),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env


_run_actual = ""


class Manifiesto:
    def __init__(self, ruta: Path):
        self.ruta = ruta
        self.datos: dict[str, Any] = {"fases": [], "checks": [], "metricas": {}, "veredicto": "PENDING"}

    def escribir(self) -> None:
        self.ruta.write_text(
            json.dumps(self.datos, indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def fase(self, nombre: str, ok: bool, detalle: str, inicio: float) -> None:
        self.datos["fases"].append(
            {"fase": nombre, "ok": ok, "duracion_s": _duracion(inicio), "detalle": detalle}
        )
        self.escribir()

    def check(self, check_id: str, ok: bool, detalle: str) -> None:
        self.datos["checks"].append({"id": check_id, "ok": ok, "detalle": detalle})
        self.escribir()


def _obtener_config() -> tuple[str, str, str, str]:
    db_url = os.environ.get("KONTROL_TEST_DB_URL")
    pg_bin = os.environ.get("KONTROL_PG_BIN_DIR")
    clamscan = os.environ.get("KONTROL_CLAMSCAN_PATH")
    clamav_db = os.environ.get("KONTROL_CLAMAV_DB")
    if not (db_url and pg_bin and clamscan and clamav_db):
        raise QAError(
            "Faltan variables de entorno: KONTROL_TEST_DB_URL, KONTROL_PG_BIN_DIR, "
            "KONTROL_CLAMSCAN_PATH y KONTROL_CLAMAV_DB"
        )
    return db_url, pg_bin, clamscan, clamav_db


def _totp_paso(manual_key: str, paso: int) -> str:
    clave = manual_key.replace(" ", "").upper()
    relleno = "=" * ((8 - len(clave) % 8) % 8)
    try:
        raw = base64.b32decode(clave + relleno, casefold=True)
    except ValueError as exc:
        raise ValueError(f"clave TOTP no válida: {exc}") from exc
    contador = struct.pack(">Q", paso)
    digest = hmac.new(raw, contador, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binario = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binario % (10**TOTP_DIGITS)).zfill(TOTP_DIGITS)


def _paso_actual() -> int:
    return int(time.time() // TOTP_STEP_S)


def _esperar_paso_posterior(ultimo: int) -> int:
    actual = _paso_actual()
    if actual <= ultimo:
        time.sleep((ultimo + 1 - actual) * TOTP_STEP_S)
    return _paso_actual()


def _totp(manual_key: str, paso: int) -> str:
    return _totp_paso(manual_key, paso)


def _puerto_libre() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _esperar_salud(base_url: str) -> None:
    limite = time.monotonic() + HEALTH_MAX_S
    while time.monotonic() < limite:
        try:
            respuesta = httpx.get(f"{base_url}/api/v1/health/ready", timeout=10.0)
            if respuesta.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(HEALTH_INTERVAL_S)
    raise QAError(f"no alcanzó /api/v1/health/ready en {HEALTH_MAX_S}s: {base_url}")


def _parar(proceso: subprocess.Popen[Any]) -> None:
    if proceso.poll() is not None:
        return
    proceso.terminate()
    try:
        proceso.wait(15)
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(15)

def _campos_db_admin(db_url: str) -> dict[str, Any]:
    url = make_url(db_url)
    return {
        "host": url.host or "localhost",
        "port": url.port or 5432,
        "user": url.username or "postgres",
        "password": url.password or "",
    }


def _conexion_admin(db_url: str) -> psycopg2.extensions.connection:
    campos = _campos_db_admin(db_url)
    conn = psycopg2.connect(dbname="postgres", **campos)
    conn.autocommit = True
    return conn


def _formatear_run(run_id: str) -> str:
    return run_id.lower().replace("-", "_")


def crear_bases(db_url: str, run: str) -> None:
    conn = _conexion_admin(db_url)
    try:
        with conn.cursor() as cursor:
            cursor.execute(psycopg2.sql.SQL("CREATE DATABASE {}").format(psycopg2.sql.Identifier(f"kbk_src_{run}")))
            cursor.execute(psycopg2.sql.SQL("CREATE DATABASE {}").format(psycopg2.sql.Identifier(f"kbk_dst_{run}")))
    finally:
        conn.close()


def borrar_bases(db_url: str, run: str) -> None:
    conn = _conexion_admin(db_url)
    try:
        with conn.cursor() as cursor:
            for base in (f"kbk_src_{run}", f"kbk_dst_{run}"):
                cursor.execute(
                    psycopg2.sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                        psycopg2.sql.Identifier(base)
                    )
                )
    finally:
        conn.close()


def bases_residuales(db_url: str, run: str) -> list[str]:
    conn = _conexion_admin(db_url)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT datname FROM pg_database WHERE datname LIKE %s", (f"kbk_%_{run}",))
            return [fila[0] for fila in cursor.fetchall()]
    finally:
        conn.close()


def _estado_licencia(db_url: str, dbname: str) -> dict[str, str | None]:
    """Estado de licencia de la base indicada, con instantes en ISO UTC (EDGE-21)."""
    conn = psycopg2.connect(dbname=dbname, **_campos_db_admin(db_url))
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT license_id, mode, period_start, period_end, last_reliable_date FROM license_states"
            )
            filas = cursor.fetchall()
    finally:
        conn.close()
    if len(filas) != 1:
        raise QAError(f"se esperaba un estado de licencia y hay {len(filas)}")
    license_id, mode, inicio, fin, fiable = filas[0]
    return {
        "license_id": license_id,
        "mode": mode,
        "period_start": _iso_utc(inicio) if inicio else None,
        "period_end": _iso_utc(fin) if fin else None,
        "last_reliable_date": _iso_utc(fiable) if fiable else None,
    }


def verificar_archivo(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    tamaño = 0
    with path.open("rb") as fh:
        for bloque in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(bloque)
            tamaño += len(bloque)
    return digest.hexdigest(), tamaño


def _ordenar_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False)


def _pdf_sintetico(run_id: str) -> bytes:
    return (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
        b"trailer<</Root 1 0 R>>\n"
        + f"% kbk {run_id}\n".encode()
        + b"%%EOF\n"
    )


def sembrar() -> None:
    """Suborden _sembrar; única parte del guion que importa la aplicación."""
    admin_password = os.environ["KBK_CERT_ADMIN_PASSWORD"]
    signing_key_pem = os.environ["KBK_CERT_LICENSE_SIGNING_KEY"]
    from sqlalchemy import select

    from app.core.database import get_session_factory, init_models
    from app.modules.identity_access.models import User
    from app.modules.licensing import service as licensing_service
    from app.modules.organization.models import Company, Installation, Tenant
    from app.modules.setup.api import SetupRequest, initialize

    init_models()
    session_factory = get_session_factory()
    llave_firma = serialization.load_pem_private_key(signing_key_pem.encode("ascii"), password=None)
    with session_factory() as db:
        resultado = initialize(
            db,
            SetupRequest(
                tenant_code="KBKA",
                tenant_name="Tenant A copia",
                company_code="A1",
                company_legal_name="Empresa A copia",
                company_rif="J-11111111-1",
                admin_username="admin.kbk",
                admin_password=admin_password,
            ),
        )
        admin = db.execute(select(User).where(User.id == resultado["admin_user_id"])).scalars().one()
        admin.must_change_password = False
        inst = db.execute(select(Installation)).scalars().one()
        tenant_b = Tenant(
            installation_id=str(inst.id),
            code="KBKB",
            name="Tenant B copia",
            plan="MONO_COMPANY",
            status="ACTIVE",
        )
        db.add(tenant_b)
        db.flush()
        company_b = Company(
            tenant_id=tenant_b.id,
            code="B1",
            legal_name="Empresa B copia",
            rif="J-22222222-2",
            legal_type="JURIDICA",
            status="ACTIVE",
            created_by="kbk-cert",
        )
        db.add(company_b)
        db.flush()
        ahora = _utc_now()
        payload = {
            "issuer": "K",
            "license_id": "LIC-KBK-CERT",
            "installation_id": inst.installation_uuid,
            "customer_id": "C1",
            "contract_id": "C1",
            "company_tax_id": "J-11111111-1",
            "period_start": (ahora - timedelta(days=30)).isoformat(),
            "period_end": (ahora + timedelta(days=120)).isoformat(),
            "critical_warning_start": (ahora + timedelta(days=180)).isoformat(),
            "read_only_start": (ahora + timedelta(days=200)).isoformat(),
            "entitlements": {"companies": 5, "users": 200, "modules": ["*"]},
            "minimum_version": "1.0.0",
            "kid": "kontrol-lic-2026-01",
        }
        firma = llave_firma.sign(_ordenar_json(payload).encode("utf-8")).hex()
        licensing_service.import_license(db, payload=payload, signature_hex=firma, source="MANUAL")
        db.commit()
        salida = {
            "installation_uuid": inst.installation_uuid,
            "tenant_a": str(resultado["tenant_id"]),
            "tenant_b": str(tenant_b.id),
            "company_a": str(resultado["company_id"]),
            "company_b": str(company_b.id),
        }
    print(json.dumps(salida))


def licencia_anterior() -> None:
    """Suborden _licencia_anterior: intenta importar en el destino una licencia de período anterior; imprime el código
    obtenido (EDGE-21)."""
    pem = os.environ["KBK_CERT_LICENSE_SIGNING_KEY"]
    from sqlalchemy import select

    from app.core.database import get_session_factory, init_models
    from app.core.errors import KontrolError
    from app.modules.licensing import service as licensing_service
    from app.modules.organization.models import Installation

    init_models()
    llave = serialization.load_pem_private_key(pem.encode("ascii"), password=None)
    with get_session_factory()() as db:
        inst = db.execute(select(Installation)).scalars().one()
        ahora = _utc_now()
        payload = {
            "issuer": "K",
            "license_id": "LIC-KBK-ANTERIOR",
            "installation_id": inst.installation_uuid,
            "customer_id": "C1",
            "contract_id": "C1",
            "company_tax_id": "J-11111111-1",
            "period_start": (ahora - timedelta(days=60)).isoformat(),
            "period_end": (ahora + timedelta(days=60)).isoformat(),
            "critical_warning_start": (ahora + timedelta(days=90)).isoformat(),
            "read_only_start": (ahora + timedelta(days=100)).isoformat(),
            "entitlements": {"companies": 5, "users": 200, "modules": ["*"]},
            "minimum_version": "1.0.0",
            "kid": "kontrol-lic-2026-01",
        }
        firma = llave.sign(_ordenar_json(payload).encode("utf-8")).hex()
        try:
            licensing_service.import_license(db, payload=payload, signature_hex=firma, source="MANUAL")
            codigo = "ACCEPTED"
        except KontrolError as exc:
            codigo = exc.code
    print(json.dumps({"code": codigo}))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Certificación QA de copia/restauración de KONTROL.",
        epilog="Uso: resources/backend/.venv/bin/python qa/backup_restore_cert.py",
    )
    sub = parser.add_subparsers(dest="subcomando")
    sub.add_parser("_sembrar", help="uso interno")
    sub.add_parser("_licencia_anterior", help="uso interno")
    args = parser.parse_args()
    if args.subcomando == "_sembrar":
        try:
            sembrar()
        except Exception:  # noqa: BLE001 - envoltorio que convierte errores internos en 70
            traceback.print_exc()
            return 70
        return 0

    if args.subcomando == "_licencia_anterior":
        try:
            licencia_anterior()
        except Exception:  # noqa: BLE001 - envoltorio que convierte errores internos en 70
            traceback.print_exc()
            return 70
        return 0

    global _run_actual
    manifest: Manifiesto | None = None
    evidencia: Path | None = None
    trabajo: Path | None = None
    secretos: Secretos | None = None
    puertos: list[int] = []
    proceso_origen: subprocess.Popen[Any] | None = None
    proceso_destino: subprocess.Popen[Any] | None = None
    fase_actual = ""
    origen_db: str | None = None
    destino_db: str | None = None
    try:
        inicio_run = time.monotonic()
        db_url, pg_bin, clamscan, clamav_db = _obtener_config()
        run_id = f"{_utc_now():%Y%m%dT%H%M%SZ}-{secrets.token_hex(3)}"
        _run_actual = run_id
        run = _formatear_run(run_id)
        origen_db = f"kbk_src_{run}"
        destino_db = f"kbk_dst_{run}"
        evidencia = RAIZ / "qa" / "backup-runs" / run_id
        trabajo = evidencia / "trabajo"
        trabajo.mkdir(parents=True, exist_ok=False)
        manifest = Manifiesto(evidencia / "manifest.json")
        manifest.escribir()

        secretos = Secretos.generar()
        storage_src = trabajo / "storage_src"
        storage_dst = trabajo / "storage_dst"
        volume_src = trabajo / "volume_src"
        volume_dst = trabajo / "volume_dst"
        volumen_copias = trabajo / "copias"
        custodia = trabajo / "custodia"
        for ruta in (storage_src, volume_src, volumen_copias, custodia, storage_dst, volume_dst):
            ruta.mkdir(parents=True, exist_ok=True)
        origen_url = (
            f"postgresql+psycopg2://{_campos_db_admin(db_url)['user']}:"
            f"{_campos_db_admin(db_url)['password']}@{_campos_db_admin(db_url)['host']}:"
            f"{_campos_db_admin(db_url)['port']}/{origen_db}"
        )
        destino_url = (
            f"postgresql+psycopg2://{_campos_db_admin(db_url)['user']}:"
            f"{_campos_db_admin(db_url)['password']}@{_campos_db_admin(db_url)['host']}:"
            f"{_campos_db_admin(db_url)['port']}/{destino_db}"
        )
        env_src = entorno_producto(origen_url, storage_src, volume_src, secretos.secret_key_src, secretos)
        env_dst = entorno_producto(destino_url, storage_dst, volume_dst, secretos.secret_key_dst, secretos)

        # P1
        fase_actual = "P1"
        inicio = time.monotonic()
        crear_bases(db_url, run)
        with open(evidencia / "migracion_origen.log", "w", encoding="utf-8") as fh_migracion:
            migracion = subprocess.run(
                [PY, "-m", "alembic", "upgrade", "head"],
                cwd=BACKEND,
                env=env_src,
                check=False,
                stdout=fh_migracion,
                stderr=subprocess.STDOUT,
            )
        if migracion.returncode != 0:
            raise QAError("migración del origen falló (ver migracion_origen.log)")
        manifest.fase(fase_actual, True, "bases creadas y migración origen aplicada", inicio)

        # P2
        fase_actual = "P2"
        inicio = time.monotonic()
        env_siembra = env_src.copy()
        env_siembra["KBK_CERT_ADMIN_PASSWORD"] = secretos.admin_password
        env_siembra["KBK_CERT_LICENSE_SIGNING_KEY"] = secretos.license_private_pem
        resultado_siembra = subprocess.run(
            [PY, str(Path(__file__).resolve()), "_sembrar"],
            env=env_siembra,
            check=False,
            capture_output=True,
            text=True,
        )
        with open(evidencia / "siembra-err.log", "w", encoding="utf-8") as fh_siembra_err:
            fh_siembra_err.write(resultado_siembra.stderr)
        if resultado_siembra.returncode != 0:
            raise QAError("siembra falló (ver siembra-err.log)")
        lineas_siembra = [linea.strip() for linea in resultado_siembra.stdout.splitlines() if linea.strip()]
        datos_siembra = json.loads(lineas_siembra[-1])
        installation_uuid = datos_siembra["installation_uuid"]
        company_a = datos_siembra["company_a"]
        with open(evidencia / "siembra.log", "w", encoding="utf-8") as fh:
            json.dump(datos_siembra, fh, indent=2, ensure_ascii=False)
        manifest.fase(fase_actual, True, "siembra sintética completada", inicio)

        # P3
        fase_actual = "P3"
        inicio = time.monotonic()
        puerto_origen = _puerto_libre()
        puertos.append(puerto_origen)
        origen_log = open(evidencia / "origen.log", "w", encoding="utf-8")
        proceso_origen = subprocess.Popen(
            [
                PY,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(puerto_origen),
            ],
            cwd=BACKEND,
            env=env_src,
            stdout=origen_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
        _esperar_salud(f"http://127.0.0.1:{puerto_origen}")
        base_origen = f"http://127.0.0.1:{puerto_origen}/api/v1"
        manifest.fase(fase_actual, True, f"origen en puerto {puerto_origen}", inicio)

        # P4
        fase_actual = "P4"
        inicio = time.monotonic()
        cliente_origen = httpx.Client(base_url=base_origen, timeout=HTTP_TIMEOUT)
        try:
            login = cliente_origen.post(
                "/auth/login",
                json={
                    "tenant_code": "KBKA",
                    "username": "admin.kbk",
                    "password": secretos.admin_password,
                },
            )
            if login.status_code != 200 or login.json().get("status") != "MFA_ENROLLMENT_REQUIRED":
                raise QAError(f"alta MFA no solicitada: {login.status_code} {login.text}")
            challenge_token = login.json()["challenge_token"]
            enrollment = cliente_origen.post("/auth/mfa/enrollment", json={"challenge_token": challenge_token})
            if enrollment.status_code != 200 or "manual_key" not in enrollment.json():
                raise QAError(f"alta MFA falló: {enrollment.status_code} {enrollment.text}")
            manual_key = enrollment.json()["manual_key"]
            secretos = Secretos(
                admin_password=secretos.admin_password,
                backup_key=secretos.backup_key,
                secret_key_src=secretos.secret_key_src,
                secret_key_dst=secretos.secret_key_dst,
                mfa_ring=secretos.mfa_ring,
                license_public_pem=secretos.license_public_pem,
                license_private_pem=secretos.license_private_pem,
                manual_key=manual_key,
                tokens=list(secretos.tokens),
            )
            paso_usado = _paso_actual()
            confirm = cliente_origen.post(
                "/auth/mfa/enrollment/confirm",
                json={"challenge_token": challenge_token, "code": _totp(manual_key, paso_usado)},
            )
            if confirm.status_code != 200 or "access_token" not in confirm.json():
                raise QAError(f"confirmación MFA falló: {confirm.status_code} {confirm.text}")
            token_previo = confirm.json()["access_token"]
            secretos.tokens.append(token_previo)
            headers = {"Authorization": f"Bearer {token_previo}"}

            tipo = cliente_origen.post(
                "/documentos/tipos",
                headers=headers,
                json={
                    "company_id": company_a,
                    "code": "KBKT",
                    "name": "Tipo copia",
                    "allowed_mime_types": ["application/pdf"],
                    "scan_required": True,
                },
            )
            if tipo.status_code not in (200, 201):
                raise QAError(f"tipo documental falló: {tipo.status_code} {tipo.text}")
            tipo_id = tipo.json()["id"]
            doc_anterior = cliente_origen.post(
                "/documentos",
                headers=headers,
                json={
                    "company_id": company_a,
                    "document_type_id": tipo_id,
                    "title": "Contrato anterior a la copia",
                },
            )
            if doc_anterior.status_code not in (200, 201):
                raise QAError(f"documento falló: {doc_anterior.status_code} {doc_anterior.text}")
            doc_id = doc_anterior.json()["id"]
            pdf = _pdf_sintetico(run_id)
            subida = cliente_origen.post(
                f"/documentos/{doc_id}/versiones",
                headers=headers,
                files={"file": ("contrato.pdf", pdf, "application/pdf")},
            )
            if subida.status_code not in (200, 201):
                raise QAError(f"subida falló: {subida.status_code} {subida.text}")
            descarga = cliente_origen.get(f"/documentos/{doc_id}/descargar", headers=headers)
            if descarga.status_code != 200:
                raise QAError(f"descarga falló: {descarga.status_code} {descarga.text}")
            sha256_documento = hashlib.sha256(descarga.content).hexdigest()
            if sha256_documento != hashlib.sha256(pdf).hexdigest():
                raise QAError("sha256 de documento no coincide")

            exportacion = cliente_origen.post(
                "/reporting/exports",
                headers=headers,
                json={"report_key": "executive_ventas", "format": "CSV"},
            )
            if exportacion.status_code not in (200, 201):
                raise QAError(f"exportación falló: {exportacion.status_code} {exportacion.text}")
            export_id = exportacion.json()["id"]
            descarga_export = cliente_origen.get(
                f"/reporting/exports/{export_id}/download", headers=headers
            )
            if descarga_export.status_code != 200:
                raise QAError(f"descarga exportación falló: {descarga_export.status_code}")
            sha256_exportacion = hashlib.sha256(descarga_export.content).hexdigest()
        finally:
            cliente_origen.close()
        manifest.fase(fase_actual, True, "actividad sintética registrada", inicio)

        # P5
        fase_actual = "P5"
        inicio = time.monotonic()
        resultado_copia = subprocess.run(
            [
                PY,
                "-m",
                "app.ops.backup",
                "create",
                "--dest",
                str(volumen_copias),
                "--pg-bin-dir",
                pg_bin,
            ],
            cwd=BACKEND,
            env=env_src,
            check=False,
            stdout=open(evidencia / "copia.log", "w", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            text=True,
        )
        if resultado_copia.returncode != 0:
            raise QAError("backup create falló")
        with open(evidencia / "copia.log", encoding="utf-8") as fh:
            lineas_copia = [linea.strip() for linea in fh.readlines() if linea.strip()]
        if not lineas_copia:
            raise QAError("backup create no produjo salida")
        datos_copia: dict[str, Any] = {}
        for linea in reversed(lineas_copia):
            try:
                parseado = json.loads(linea)
                if isinstance(parseado, dict) and "status" in parseado:
                    datos_copia = parseado
                    break
            except json.JSONDecodeError:
                continue
        if datos_copia.get("status") != "OK":
            raise QAError(f"backup no OK: {datos_copia}")
        backup_path = Path(datos_copia["path"])
        if not backup_path.is_file():
            raise QAError(f"archivo de copia no existe: {backup_path}")
        sha256_backup, tamaño_backup = verificar_archivo(backup_path)
        backup_cli_s = datos_copia.get("duration_s", _duracion(inicio))
        manifest.fase(
            fase_actual,
            True,
            f"backup {datos_copia.get('backup_id')} {sha256_backup} objetos={datos_copia.get('objects')}",
            inicio,
        )

        # P6
        fase_actual = "P6"
        inicio = time.monotonic()
        cliente_origen = httpx.Client(base_url=base_origen, timeout=HTTP_TIMEOUT)
        try:
            posterior = cliente_origen.post(
                "/documentos",
                headers=headers,
                json={
                    "company_id": company_a,
                    "document_type_id": tipo_id,
                    "title": "Posterior a la copia",
                },
            )
            if posterior.status_code not in (200, 201):
                raise QAError(f"escritura posterior falló: {posterior.status_code} {posterior.text}")
            id_posterior = posterior.json()["id"]
        finally:
            cliente_origen.close()
        t_ultima_escritura = _utc_now()
        manifest.fase(fase_actual, True, "escritura posterior a la instantánea registrada", inicio)

        # P7
        fase_actual = "P7"
        inicio = time.monotonic()
        resultado_verify = subprocess.run(
            [PY, "-m", "app.ops.backup", "verify", str(backup_path)],
            cwd=BACKEND,
            env=env_src,
            check=False,
            stdout=open(evidencia / "verify.log", "w", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            text=True,
        )
        if resultado_verify.returncode != 0:
            raise QAError("backup verify falló")
        contenido_verify = Path(evidencia / "verify.log").read_text(encoding="utf-8")
        datos_verify: dict[str, Any] = {}
        for linea in reversed(contenido_verify.splitlines()):
            try:
                parseado = json.loads(linea)
                if isinstance(parseado, dict) and "status" in parseado:
                    datos_verify = parseado
                    break
            except json.JSONDecodeError:
                continue
        if datos_verify.get("status") != "OK":
            raise QAError(f"verify no OK: {datos_verify}")
        manifest.fase(fase_actual, True, "verificación independiente OK", inicio)

        # P8
        fase_actual = "P8"
        inicio = time.monotonic()
        clave_custodia_origen = volume_src / "installation_private_key.pem"
        if not clave_custodia_origen.is_file():
            raise QAError("no existe installation_private_key.pem del origen")
        shutil.copy2(clave_custodia_origen, custodia / "installation_private_key.pem")
        (custodia / "installation_private_key.pem").chmod(0o600)
        licencia_origen = _estado_licencia(db_url, origen_db)
        contenido_backup = backup_path.read_bytes()
        fragmentos_prohibidos = [
            secretos.admin_password.encode("utf-8"),
            secretos.backup_key.encode("utf-8"),
            b"PGDMP",
            f"kbk {run_id}".encode(),
        ]
        fugas = [f for f in fragmentos_prohibidos if f in contenido_backup]
        if fugas:
            raise QAError(f"backup contiene secretos o marcadores: {fugas!r}")
        manifest.fase(fase_actual, True, "custodia externa y barrido de copia OK", inicio)

        # P9
        fase_actual = "P9"
        inicio = time.monotonic()
        _parar(proceso_origen)
        proceso_origen = None
        conn_admin = _conexion_admin(db_url)
        try:
            with conn_admin.cursor() as cursor:
                cursor.execute(
                    psycopg2.sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                        psycopg2.sql.Identifier(origen_db)
                    )
                )
        finally:
            conn_admin.close()
        shutil.rmtree(storage_src)
        shutil.rmtree(volume_src)
        centinela_falla = False
        try:
            psycopg2.connect(
                dbname=origen_db,
                host=_campos_db_admin(db_url)["host"],
                port=_campos_db_admin(db_url)["port"],
                user=_campos_db_admin(db_url)["user"],
                password=_campos_db_admin(db_url)["password"],
                connect_timeout=3,
            )
        except psycopg2.Error:
            centinela_falla = True
        if not centinela_falla:
            raise QAError("la base origen sigue accesible tras el desastre")
        if storage_src.exists() or volume_src.exists():
            raise QAError("directorios de origen siguen existiendo")
        t_desastre = _utc_now()
        manifest.check("C-00", True, "desastre verificado: base y volúmenes de origen inaccesibles")
        manifest.fase(fase_actual, True, "desastre ejecutado", inicio)

        # P10
        fase_actual = "P10"
        inicio = time.monotonic()
        shutil.copy2(custodia / "installation_private_key.pem", volume_dst / "installation_private_key.pem")
        (volume_dst / "installation_private_key.pem").chmod(0o600)
        t0_rto = time.monotonic()
        resultado_restore = subprocess.run(
            [
                PY,
                "-m",
                "app.ops.backup",
                "restore",
                str(backup_path),
                "--expected-installation-id",
                str(installation_uuid),
                "--storage-root",
                str(storage_dst),
                "--installation-volume",
                str(volume_dst),
                "--pg-bin-dir",
                pg_bin,
            ],
            cwd=BACKEND,
            env=env_dst,
            check=False,
            stdout=open(evidencia / "restore.log", "w", encoding="utf-8"),
            stderr=subprocess.STDOUT,
            text=True,
        )
        if resultado_restore.returncode != 0:
            raise QAError("backup restore falló")
        datos_restore: dict[str, Any] = {}
        with open(evidencia / "restore.log", encoding="utf-8") as fh:
            for linea in reversed([cruda.strip() for cruda in fh.readlines() if cruda.strip()]):
                try:
                    parseado = json.loads(linea)
                    if isinstance(parseado, dict) and "status" in parseado:
                        datos_restore = parseado
                        break
                except json.JSONDecodeError:
                    continue
        if datos_restore.get("status") != "RESTORED" or datos_restore.get("sessions_revoked", 0) < 1:
            raise QAError(f"restore inválido: {datos_restore}")
        restore_cli_s = _duracion(t0_rto)
        manifest.fase(
            fase_actual,
            True,
            f"restauración OK; sesiones revocadas={datos_restore.get('sessions_revoked')}",
            inicio,
        )

        # P11
        fase_actual = "P11"
        inicio = time.monotonic()
        puerto_destino = _puerto_libre()
        puertos.append(puerto_destino)
        destino_log = open(evidencia / "destino.log", "w", encoding="utf-8")
        proceso_destino = subprocess.Popen(
            [
                PY,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(puerto_destino),
            ],
            cwd=BACKEND,
            env=env_dst,
            stdout=destino_log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            text=True,
        )
        _esperar_salud(f"http://127.0.0.1:{puerto_destino}")
        base_destino = f"http://127.0.0.1:{puerto_destino}/api/v1"
        manifest.fase(fase_actual, True, f"destino en puerto {puerto_destino}", inicio)

        # P12
        fase_actual = "P12"
        inicio = time.monotonic()
        cliente_destino = httpx.Client(base_url=base_destino, timeout=HTTP_TIMEOUT)
        try:
            login_dst = cliente_destino.post(
                "/auth/login",
                json={
                    "tenant_code": "KBKA",
                    "username": "admin.kbk",
                    "password": secretos.admin_password,
                },
            )
            c01 = login_dst.status_code == 200 and login_dst.json().get("status") == "MFA_REQUIRED"
            manifest.check("C-01", c01, "MFA restaurado activo")
            if not c01:
                raise QAError("login en destino no exige MFA")
            paso_anterior = paso_usado
            paso_verificacion = _esperar_paso_posterior(paso_anterior)
            challenge_token_dst = login_dst.json()["challenge_token"]
            verify = cliente_destino.post(
                "/auth/mfa/verify",
                json={
                    "challenge_token": challenge_token_dst,
                    "code": _totp(manual_key, paso_verificacion),
                },
            )
            if verify.status_code != 200 or "access_token" not in verify.json():
                raise QAError(f"verificación MFA en destino falló: {verify.status_code} {verify.text}")
            token_nuevo = verify.json()["access_token"]
            secretos.tokens.append(token_nuevo)
            t_primer_login = time.monotonic()
            rto_s = round(t_primer_login - t0_rto, 3)
            headers_dst = {"Authorization": f"Bearer {token_nuevo}"}

            companies = cliente_destino.get("/organization/companies", headers=headers_dst)
            c02 = companies.status_code == 200
            if c02:
                body_companies = companies.json()
                ids = [str(item["id"]) for item in body_companies.get("items", [])]
                c02 = company_a in ids and datos_siembra["company_b"] not in ids
            manifest.check("C-02", c02, "aislamiento de tenant")
            if not c02:
                raise QAError("aislamiento de tenant falló")

            descarga_dst = cliente_destino.get(f"/documentos/{doc_id}/descargar", headers=headers_dst)
            c03 = descarga_dst.status_code == 200 and hashlib.sha256(descarga_dst.content).hexdigest() == sha256_documento
            manifest.check("C-03", c03, "documento anterior restaurado con integridad")
            if not c03:
                raise QAError("documento anterior no restaurado")

            export_dst = cliente_destino.get(
                f"/reporting/exports/{export_id}/download", headers=headers_dst
            )
            c04 = export_dst.status_code == 200 and hashlib.sha256(export_dst.content).hexdigest() == sha256_exportacion
            manifest.check("C-04", c04, "exportación restaurada con integridad")
            if not c04:
                raise QAError("exportación no restaurada")

            posterior_dst = cliente_destino.get(f"/documentos/{id_posterior}", headers=headers_dst)
            c05 = posterior_dst.status_code == 404
            manifest.check("C-05", c05, "punto de corte respetado")
            if not c05:
                raise QAError("documento posterior apareció en destino")

            nuevo_dst = cliente_destino.post(
                "/documentos",
                headers=headers_dst,
                json={
                    "company_id": company_a,
                    "document_type_id": tipo_id,
                    "title": "Escrito tras restaurar",
                },
            )
            c06 = nuevo_dst.status_code in (200, 201)
            if c06:
                nuevo_id = nuevo_dst.json()["id"]
                audit = cliente_destino.get(
                    "/audit/events",
                    headers=headers_dst,
                    params={"action": "DOCUMENT_CREATED", "entity_id": str(nuevo_id)},
                )
                c06 = audit.status_code == 200 and len(audit.json().get("items", [])) >= 1
            manifest.check("C-06", c06, "escritura nueva y trazabilidad en auditoría")
            if not c06:
                raise QAError("escritura nueva no auditada")

            c07 = True
            for sql_mutante in ("UPDATE audit_events SET reason = 'x'", "DELETE FROM audit_events"):
                conexion_dest = psycopg2.connect(
                    dbname=destino_db,
                    host=_campos_db_admin(db_url)["host"],
                    port=_campos_db_admin(db_url)["port"],
                    user=_campos_db_admin(db_url)["user"],
                    password=_campos_db_admin(db_url)["password"],
                )
                conexion_dest.autocommit = True
                try:
                    with conexion_dest.cursor() as cursor:
                        cursor.execute(sql_mutante)
                    c07 = False
                except psycopg2.Error:
                    pass
                finally:
                    conexion_dest.close()
            manifest.check("C-07", c07, "auditoría inmutable")
            if not c07:
                raise QAError("auditoría mutable")

            parametro_inventado = cliente_destino.get(
                "/organization/companies", headers=headers_dst, params={"campo_inventado": 1}
            )
            fecha_naive = cliente_destino.get(
                "/notifications",
                headers=headers_dst,
                params={"created_from": "2026-10-28T10:00:00"},
            )
            c08 = (
                parametro_inventado.status_code == 422
                and "UNKNOWN_QUERY_PARAMETER" in parametro_inventado.text
                and fecha_naive.status_code == 422
                and "NAIVE_DATETIME" in fecha_naive.text
            )
            manifest.check("C-08", c08, "contrato de entrada")
            if not c08:
                raise QAError("contrato de entrada falló")

            me_previo = cliente_destino.get("/auth/me", headers={"Authorization": f"Bearer {token_previo}"})
            c09 = me_previo.status_code == 401
            manifest.check("C-09", c09, "sesión previa al desastre revocada")
            if not c09:
                raise QAError("token previo al desastre sigue válido")

            licencia = cliente_destino.get("/license/status", headers=headers_dst)
            c10 = licencia.status_code == 200 and licencia.json().get("mode") == "FULL_ACCESS"
            manifest.check("C-10", c10, "licencia reverificada")
            if not c10:
                raise QAError("licencia no reverificada")

            conexion_audit = psycopg2.connect(
                dbname=destino_db,
                host=_campos_db_admin(db_url)["host"],
                port=_campos_db_admin(db_url)["port"],
                user=_campos_db_admin(db_url)["user"],
                password=_campos_db_admin(db_url)["password"],
            )
            try:
                with conexion_audit.cursor() as cursor:
                    cursor.execute(
                        "SELECT count(*) FROM audit_events WHERE action = 'INSTALLATION_RESTORED'"
                    )
                    restaurados = cursor.fetchone()[0]
                    cursor.execute(
                        "SELECT count(*) FROM audit_events WHERE action = 'INSTALLATION_BACKUP_CREATED'"
                    )
                    backup_events = cursor.fetchone()[0]
            finally:
                conexion_audit.close()
            c11 = restaurados == 2 and backup_events == 0
            manifest.check("C-11", c11, "eventos de cierre auditado")
            if not c11:
                raise QAError(f"eventos de cierre inesperados: restore={restaurados}, backup={backup_events}")
            licencia_destino = _estado_licencia(db_url, destino_db)
            fiable_origen = licencia_origen["last_reliable_date"]
            fiable_destino = licencia_destino["last_reliable_date"]
            c12 = (
                all(licencia_destino[k] == licencia_origen[k] for k in ("license_id", "mode", "period_start", "period_end"))
                and fiable_origen is not None
                and fiable_destino is not None
                and datetime.fromisoformat(fiable_destino) >= datetime.fromisoformat(fiable_origen)
            )
            manifest.check("C-12", c12, "estado de licencia del punto de copia; la fecha fiable no retrocede (EDGE-21)")
            if not c12:
                raise QAError("el estado de licencia restaurado no coincide con el de origen")
            env_anterior = env_dst.copy()
            env_anterior["KBK_CERT_LICENSE_SIGNING_KEY"] = secretos.license_private_pem
            intento = subprocess.run(
                [PY, str(Path(__file__).resolve()), "_licencia_anterior"],
                env=env_anterior,
                check=False,
                capture_output=True,
                text=True,
            )
            lineas_intento = [linea.strip() for linea in intento.stdout.splitlines() if linea.strip()]
            codigo_intento = json.loads(lineas_intento[-1]).get("code") if intento.returncode == 0 and lineas_intento else None
            c13 = codigo_intento == "LICENSE_PERIOD_DOWNGRADE" and _estado_licencia(db_url, destino_db) == licencia_destino
            manifest.check("C-13", c13, f"licencia de período anterior rechazada en el destino: {codigo_intento}")
            if not c13:
                raise QAError("el destino no rechazó una licencia de período anterior")
        finally:
            cliente_destino.close()
        manifest.fase(fase_actual, True, "pruebas funcionales en destino completadas", inicio)

        # P13
        fase_actual = "P13"
        inicio = time.monotonic()
        snapshot_at = datetime.fromisoformat(datos_copia["snapshot_at_utc"]).astimezone(UTC)
        ventana_perdida = (t_desastre - snapshot_at).total_seconds()
        metrics = {
            "rto_s": rto_s,
            "restore_cli_s": restore_cli_s,
            "backup_cli_s": backup_cli_s,
            "snapshot_at_utc": _iso_utc(snapshot_at),
            "t_ultima_escritura_utc": _iso_utc(t_ultima_escritura),
            "t_desastre_utc": _iso_utc(t_desastre),
            "ventana_perdida_s": ventana_perdida,
            "rpo_objetivo_s": RPO_OBJETIVO_S,
            "rto_objetivo_s": RTO_OBJETIVO_S,
            "rto_resultado": "MET" if rto_s <= RTO_OBJETIVO_S else "NOT_MET",
            "rpo_resultado": "DEPENDS_ON_BACKUP_SCHEDULE",
            "backup_sha256": sha256_backup,
            "backup_size_bytes": tamaño_backup,
            "db_origen": origen_db,
            "db_destino": destino_db,
            "puertos": puertos,
            "duracion_total_s": _duracion(inicio_run),
        }
        manifest.datos["metricas"] = metrics
        manifest.fase(fase_actual, True, "métricas calculadas", inicio)
    except QAError as exc:
        if manifest is not None:
            if fase_actual:
                manifest.fase(fase_actual, False, str(exc), time.monotonic())
            manifest.datos["veredicto"] = "FAIL"
            manifest.escribir()
        print(f"FAIL {fase_actual or 'setup'}: {exc}")
        return 1
    except Exception:  # noqa: BLE001 - envoltorio que convierte errores internos en 70
        traceback.print_exc()
        return 70
    finally:
        limpieza = []
        if proceso_destino is not None:
            try:
                _parar(proceso_destino)
                limpieza.append("destino_parado")
            except Exception as exc:  # noqa: BLE001 - limpieza tolerante a fallos
                limpieza.append(f"destino_parado_fallido:{exc}")
        if proceso_origen is not None:
            try:
                _parar(proceso_origen)
                limpieza.append("origen_parado")
            except Exception as exc:  # noqa: BLE001 - limpieza tolerante a fallos
                limpieza.append(f"origen_parado_fallido:{exc}")
        try:
            if origen_db and destino_db and _run_actual:
                borrar_bases(db_url, _formatear_run(_run_actual))
                limpieza.append("bases_borradas")
        except Exception as exc:  # noqa: BLE001 - limpieza tolerante a fallos
            limpieza.append(f"bases_borrado_fallido:{exc}")
        try:
            if trabajo is not None:
                shutil.rmtree(trabajo)
                limpieza.append("trabajo_borrado")
        except Exception as exc:  # noqa: BLE001 - limpieza tolerante a fallos
            limpieza.append(f"trabajo_borrado_fallido:{exc}")
        try:
            if _run_actual:
                residuales = bases_residuales(db_url, _formatear_run(_run_actual))
                if residuales:
                    limpieza.append(f"bases_residuales:{','.join(residuales)}")
        except Exception as exc:  # noqa: BLE001 - limpieza tolerante a fallos
            limpieza.append(f"verificar_residuos_fallido:{exc}")
        try:
            for puerto in puertos:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sonda:
                    if sonda.connect_ex(("127.0.0.1", puerto)) == 0:
                        limpieza.append(f"puerto_ocupado:{puerto}")
        except Exception as exc:  # noqa: BLE001 - limpieza tolerante a fallos
            limpieza.append(f"verificar_puertos_fallido:{exc}")
        limpio = len(limpieza) > 0 and all(not str(x).startswith(("bases_borrado_fallido", "trabajo_borrado_fallido", "bases_residuales", "puerto_ocupado")) for x in limpieza)
        if manifest is not None and _run_actual:
            manifest.fase("LIMPIEZA", limpio, "; ".join(limpieza), time.monotonic())

    if manifest is None or secretos is None or evidencia is None:
        return 3

    s01 = True
    secretos_barrido = [s for s in secretos.valores() if len(s) >= 8]
    for ruta in evidencia.rglob("*"):
        if not ruta.is_file():
            continue
        try:
            contenido = ruta.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for secreto in secretos_barrido:
            if secreto in contenido:
                s01 = False
                break
        if not s01:
            break
    manifest.check("S-01", s01, "barrido de secretos en evidencia")
    checks = list(manifest.datos["checks"])
    fases = list(manifest.datos["fases"])
    ids_requeridos = {f"C-{n:02d}" for n in range(14)} | {"S-01"}
    ids_presentes = {c["id"] for c in checks}
    checks_ok = ids_requeridos <= ids_presentes and all(c["ok"] for c in checks)
    metricas = manifest.datos.get("metricas", {})
    claves_requeridas = ("rto_s", "restore_cli_s", "backup_cli_s", "snapshot_at_utc", "ventana_perdida_s",
                         "rto_resultado", "rpo_resultado")
    metricas_ok = all(metricas.get(clave) is not None for clave in claves_requeridas)
    manifest.check("M-01", metricas_ok, "métricas de RPO y RTO presentes")
    fases_ok = len(fases) >= 14 and all(f["ok"] for f in fases)
    veredicto = "PASS" if checks_ok and metricas_ok and fases_ok and s01 else "FAIL"
    manifest.datos["veredicto"] = veredicto
    manifest.escribir()

    for fase in fases:
        print(f"{'PASS' if fase['ok'] else 'FAIL'} {fase['fase']}: {fase['detalle']}")
    for check in checks:
        print(f"{'PASS' if check['ok'] else 'FAIL'} {check['id']}: {check['detalle']}")
    print(f"Manifiesto: {manifest.ruta}")

    return 0 if veredicto == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
