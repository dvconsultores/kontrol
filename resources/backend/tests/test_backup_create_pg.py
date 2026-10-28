"""Pruebas de copia de seguridad real contra PostgreSQL."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg2
import psycopg2.sql
import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.core.database import init_models
from app.modules.documents.models import StoredFile
from app.modules.licensing.models import LicenseState
from app.modules.organization.models import Company, Installation, Tenant
from app.modules.reporting.models import ReportExport
from app.ops.backup_bundle import BundleReader
from app.ops.backup_create import BackupResult, create_backup
from app.ops.backup_crypto import generate_key_text, parse_key_text
from app.ops.backup_pg import BackupError, pg_connect_kwargs, pg_tool

URL = os.environ.get("KONTROL_TEST_DB_URL", "")
PG_BIN = os.environ.get("KONTROL_PG_BIN_DIR")
pytestmark = pytest.mark.skipif(
    not URL.startswith("postgresql"),
    reason="copia real: solo PostgreSQL",
)


@dataclass(frozen=True)
class MundoOrigen:
    """Datos sembrados para una prueba."""

    db_url: str
    storage_root: Path
    installation_db_id: str
    installation_uuid: str
    tenant_id: str
    datos_a: bytes
    datos_b: bytes
    datos_export: bytes
    clave_a: str
    clave_b: str
    clave_purged: str
    path_a: Path
    path_b: Path
    export_ref: str
    export_path: Path


@pytest.fixture()
def base_de_origen() -> Iterator[str]:
    """Crea una base PostgreSQL temporal con el esquema migrado."""
    admin_url_str = (
        make_url(URL).set(database="postgres").render_as_string(hide_password=False)
    )
    conn = psycopg2.connect(**pg_connect_kwargs(admin_url_str))
    conn.autocommit = True
    cur = conn.cursor()
    database_name = f"kbk_t3_{uuid.uuid4().hex[:10]}"
    cur.execute(
        psycopg2.sql.SQL("CREATE DATABASE {}").format(
            psycopg2.sql.Identifier(database_name)
        )
    )
    conn.close()

    backend_dir = Path(__file__).resolve().parents[1]
    database_url = make_url(URL).set(database=database_name).render_as_string(
        hide_password=False
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env={**os.environ, "KONTROL_DB_URL": database_url},
        check=True,
    )

    try:
        yield database_url
    finally:
        conn = psycopg2.connect(**pg_connect_kwargs(admin_url_str))
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            psycopg2.sql.SQL("DROP DATABASE {} WITH (FORCE)").format(
                psycopg2.sql.Identifier(database_name)
            )
        )
        conn.close()


@pytest.fixture()
def mundo_origen(base_de_origen: str, tmp_path: Path) -> MundoOrigen:
    """Siembra una instalación, documentos y una exportación."""
    init_models()

    engine = create_engine(base_de_origen)
    storage_root = tmp_path / "storage"
    document_root = storage_root / "documents"
    export_root = storage_root / "exports"
    document_root.mkdir(parents=True)
    export_root.mkdir(parents=True)

    datos_a = b"contenido-documento-a"
    datos_b = b"contenido-documento-b"
    datos_export = b"a,b\n1,2\n"

    clave_a = f"2026/10/28/{uuid.uuid4().hex}"
    clave_b = f"2026/10/28/{uuid.uuid4().hex}"
    clave_purged = f"2026/10/28/{uuid.uuid4().hex}"

    path_a = document_root / clave_a
    path_b = document_root / clave_b
    path_a.parent.mkdir(parents=True, exist_ok=True)
    path_b.parent.mkdir(parents=True, exist_ok=True)
    path_a.write_bytes(datos_a)
    path_b.write_bytes(datos_b)

    export_ref = f"{uuid.uuid4().hex}.csv"
    export_path = export_root / export_ref
    export_path.write_bytes(datos_export)

    with Session(engine) as session:
        inst = Installation(
            installation_uuid=f"KTL-QA-{uuid.uuid4().hex[:8].upper()}",
            public_key="clave-publica-sintetica",
            state="ACTIVE",
        )
        session.add(inst)
        session.flush()

        tenant = Tenant(
            installation_id=inst.id,
            code=f"T{uuid.uuid4().hex[:6]}",
            name="Tenant sintético",
        )
        session.add(tenant)
        session.flush()

        company = Company(
            tenant_id=tenant.id,
            code="C1",
            legal_name="Empresa sintética",
            rif="J-12345678-9",
            legal_type="JURIDICA",
            functional_currency="VED",
            status="ACTIVE",
        )
        session.add(company)
        session.flush()

        session.add(
            StoredFile(
                original_name="a.txt",
                mime_type="text/plain",
                size=len(datos_a),
                sha256=hashlib.sha256(datos_a).hexdigest(),
                storage_key=clave_a,
                status="AVAILABLE",
                uploaded_at=datetime.now(UTC),
            )
        )
        session.add(
            StoredFile(
                original_name="b.txt",
                mime_type="text/plain",
                size=len(datos_b),
                sha256=hashlib.sha256(datos_b).hexdigest(),
                storage_key=clave_b,
                status="AVAILABLE",
                uploaded_at=datetime.now(UTC),
            )
        )
        session.add(
            StoredFile(
                original_name="purged.txt",
                mime_type="text/plain",
                size=len(datos_b),
                sha256=hashlib.sha256(datos_b).hexdigest(),
                storage_key=clave_purged,
                status="PURGED",
                uploaded_at=datetime.now(UTC),
            )
        )
        session.add(
            ReportExport(
                company_id=company.id,
                report_key="ventas",
                format="CSV",
                file_ref=export_ref,
                status="DONE",
            )
        )
        session.commit()

        installation_db_id = str(inst.id)
        installation_uuid = inst.installation_uuid
        tenant_id = str(tenant.id)

    engine.dispose()
    return MundoOrigen(
        db_url=base_de_origen,
        storage_root=storage_root,
        installation_db_id=installation_db_id,
        installation_uuid=installation_uuid,
        tenant_id=tenant_id,
        datos_a=datos_a,
        datos_b=datos_b,
        datos_export=datos_export,
        clave_a=clave_a,
        clave_b=clave_b,
        clave_purged=clave_purged,
        path_a=path_a,
        path_b=path_b,
        export_ref=export_ref,
        export_path=export_path,
    )


def _clave() -> bytes:
    return parse_key_text(generate_key_text())


def _count_stored_files(db_url: str) -> int:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(
            "SELECT count(*) FROM stored_files"
        ).scalar_one()
    engine.dispose()
    return int(rows)


def test_bcp01_crea_paquete_consistente(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-01."""
    destination = tmp_path / "out"
    destination.mkdir()
    key = _clave()
    result = create_backup(
        db_url=mundo_origen.db_url,
        storage_root=mundo_origen.storage_root,
        destination_dir=destination,
        key=key,
        pg_bin_dir=PG_BIN,
        audit=False,
    )
    assert isinstance(result, BackupResult)
    bundle_path = result.path
    assert bundle_path.exists()
    assert bundle_path.suffix == ".kbk"

    verify_dir = tmp_path / "vb"
    verify_dir.mkdir()
    expected_tablas = _public_tables(mundo_origen.db_url)
    expected_alembic = _alembic_version(mundo_origen.db_url)

    with BundleReader(bundle_path, key) as reader:
        counts = reader.manifest["counts"]
        assert isinstance(counts, dict)
        assert counts["purged"] == 1

        assert reader.manifest["installation_id"] == (
            mundo_origen.installation_uuid
        )

        tablas = reader.manifest["tables"]
        assert isinstance(tablas, dict)
        assert set(tablas) == expected_tablas

        assert reader.manifest["alembic_revision"] == expected_alembic

        verified = reader.verify(verify_dir)
        assert len(verified.object_paths) == 3

    contenidos = {
        path.read_bytes()
        for path in verified.object_paths.values()
    }
    assert mundo_origen.datos_a in contenidos
    assert mundo_origen.datos_b in contenidos
    assert mundo_origen.datos_export in contenidos


def test_bcp02_objeto_borrado_falla_y_no_deja_paquete(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-02."""
    mundo_origen.path_a.unlink()
    destination = tmp_path / "out"
    destination.mkdir()
    key = _clave()
    with pytest.raises(BackupError) as excinfo:
        create_backup(
            db_url=mundo_origen.db_url,
            storage_root=mundo_origen.storage_root,
            destination_dir=destination,
            key=key,
            pg_bin_dir=PG_BIN,
            audit=False,
        )
    assert excinfo.value.code == "BACKUP_INCONSISTENT"
    assert not list(destination.glob("*.kbk"))


def test_bcp03_sha256_distinto_falla(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-03."""
    mundo_origen.path_a.write_bytes(b"contenido alterado")
    destination = tmp_path / "out"
    destination.mkdir()
    key = _clave()
    with pytest.raises(BackupError) as excinfo:
        create_backup(
            db_url=mundo_origen.db_url,
            storage_root=mundo_origen.storage_root,
            destination_dir=destination,
            key=key,
            pg_bin_dir=PG_BIN,
            audit=False,
        )
    assert excinfo.value.code == "BACKUP_INCONSISTENT"
    assert not list(destination.glob("*.kbk"))


def test_bcp04_escritura_concurrente_no_entra_en_instantanea(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-04."""
    destination = tmp_path / "out"
    destination.mkdir()
    key = _clave()
    new_ref = f"2026/10/28/{uuid.uuid4().hex}"
    new_path = mundo_origen.storage_root / "documents" / new_ref
    new_path.parent.mkdir(parents=True, exist_ok=True)
    new_datos = b"post-snapshot"

    def insertar_despues_de_snapshot() -> None:
        engine = create_engine(mundo_origen.db_url)
        with Session(engine) as session:
            session.add(
                StoredFile(
                    original_name="nuevo.txt",
                    mime_type="text/plain",
                    size=len(new_datos),
                    sha256=hashlib.sha256(new_datos).hexdigest(),
                    storage_key=new_ref,
                    status="AVAILABLE",
                    uploaded_at=datetime.now(UTC),
                )
            )
            session.commit()
        new_path.write_bytes(new_datos)
        engine.dispose()

    rows_antes = _count_stored_files(mundo_origen.db_url)

    result = create_backup(
        db_url=mundo_origen.db_url,
        storage_root=mundo_origen.storage_root,
        destination_dir=destination,
        key=key,
        pg_bin_dir=PG_BIN,
        audit=False,
        after_snapshot=insertar_despues_de_snapshot,
    )
    with BundleReader(result.path, key) as reader:
        manifest = reader.manifest

        objetos = manifest["objects"]
        assert isinstance(objetos, list)
        assert all(obj["ref"] != new_ref for obj in objetos)

        tablas = manifest["tables"]
        assert isinstance(tablas, dict)
        stored_files_info = tablas["stored_files"]
        assert isinstance(stored_files_info, dict)
        assert stored_files_info["rows"] == rows_antes

    destination2 = tmp_path / "out2"
    destination2.mkdir()
    result2 = create_backup(
        db_url=mundo_origen.db_url,
        storage_root=mundo_origen.storage_root,
        destination_dir=destination2,
        key=key,
        pg_bin_dir=PG_BIN,
        audit=False,
    )
    with BundleReader(result2.path, key) as reader:
        manifest2 = reader.manifest

        objetos2 = manifest2["objects"]
        assert isinstance(objetos2, list)
        assert any(obj["ref"] == new_ref for obj in objetos2)


def test_bcp05_purga_concurrente_falla(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-05."""
    destination = tmp_path / "out"
    destination.mkdir()
    key = _clave()

    def purgar_despues_de_snapshot() -> None:
        mundo_origen.path_a.unlink()

    with pytest.raises(BackupError) as excinfo:
        create_backup(
            db_url=mundo_origen.db_url,
            storage_root=mundo_origen.storage_root,
            destination_dir=destination,
            key=key,
            pg_bin_dir=PG_BIN,
            audit=False,
            after_snapshot=purgar_despues_de_snapshot,
        )
    assert excinfo.value.code == "BACKUP_INCONSISTENT"
    assert not list(destination.glob("*.kbk"))


def test_bcp06_pg_bin_dir_inexistente(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-06."""
    destination = tmp_path / "out"
    destination.mkdir()
    key = _clave()
    with pytest.raises(BackupError) as excinfo:
        create_backup(
            db_url=mundo_origen.db_url,
            storage_root=mundo_origen.storage_root,
            destination_dir=destination,
            key=key,
            pg_bin_dir="/ruta/que/no/existe",
            audit=False,
        )
    assert excinfo.value.code == "PG_TOOLS_MISSING"


def test_bcp07_no_contiene_datos_en_claro(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-07."""
    destination = tmp_path / "out"
    destination.mkdir()
    key = _clave()
    result = create_backup(
        db_url=mundo_origen.db_url,
        storage_root=mundo_origen.storage_root,
        destination_dir=destination,
        key=key,
        pg_bin_dir=PG_BIN,
        audit=False,
    )
    contenido = result.path.read_bytes()
    assert mundo_origen.datos_a not in contenido
    assert mundo_origen.datos_b not in contenido
    assert b"PGDMP" not in contenido
    assert mundo_origen.installation_uuid.encode() not in contenido


def test_bcp08_audit_true_crea_evento(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-08.

    Requiere que la acción esté registrada en el catálogo de auditoría.
    """
    destination = tmp_path / "out"
    destination.mkdir()
    key = _clave()
    result = create_backup(
        db_url=mundo_origen.db_url,
        storage_root=mundo_origen.storage_root,
        destination_dir=destination,
        key=key,
        pg_bin_dir=PG_BIN,
        audit=True,
    )
    engine = create_engine(mundo_origen.db_url)
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(
            """
            SELECT count(*) FROM audit_events
            WHERE action = 'INSTALLATION_BACKUP_CREATED'
              AND entity_type = 'Installation'
              AND entity_id = %s
            """,
            (mundo_origen.installation_db_id,),
        ).scalar_one()
        assert rows == 1
        backup_id = conn.exec_driver_sql(
            """
            SELECT after->>'backup_id'
            FROM audit_events
            WHERE action = 'INSTALLATION_BACKUP_CREATED'
              AND entity_type = 'Installation'
              AND entity_id = %s
            """,
            (mundo_origen.installation_db_id,),
        ).scalar_one()
        assert backup_id == result.backup_id
    engine.dispose()


def _public_tables(db_url: str) -> set[str]:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        rows = conn.exec_driver_sql(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public'
            """
        ).scalars()
        names = set(rows)
    engine.dispose()
    return names


def _alembic_version(db_url: str) -> str:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        value = conn.exec_driver_sql(
            "SELECT version_num FROM alembic_version"
        ).scalar_one()
    engine.dispose()
    return value


def test_bcp09_pg_dump_falla(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-09: mata el mutante «omit DB dump validation», rc de pg_dump."""
    destination = tmp_path / "out"
    destination.mkdir()
    falso = tmp_path / "pgfalso"
    falso.mkdir()
    dump_script = falso / "pg_dump"
    dump_script.write_text(
        f'#!/bin/sh\nif [ "$1" = "--version" ]; then exec "{pg_tool("pg_dump", PG_BIN)}"'
        " --version; fi\nexit 1\n"
    )
    os.chmod(dump_script, 0o755)

    key = _clave()
    with pytest.raises(BackupError) as exc_info:
        create_backup(
            db_url=mundo_origen.db_url,
            storage_root=mundo_origen.storage_root,
            destination_dir=destination,
            key=key,
            pg_bin_dir=str(falso),
            audit=False,
        )
    assert exc_info.value.code == "PG_DUMP_FAILED"
    assert not list(destination.glob("*.kbk"))


def test_bcp10_clave_no_embebida(
    mundo_origen: MundoOrigen,
    tmp_path: Path,
) -> None:
    """BCP-10: mata el mutante «embed key»."""
    destination = tmp_path / "out"
    destination.mkdir()
    texto = generate_key_text()
    key = parse_key_text(texto)

    result = create_backup(
        db_url=mundo_origen.db_url,
        storage_root=mundo_origen.storage_root,
        destination_dir=destination,
        key=key,
        pg_bin_dir=PG_BIN,
        audit=False,
    )

    with BundleReader(result.path, key) as reader:
        serializado = json.dumps(reader.manifest)
        assert texto not in serializado
        assert key.hex() not in serializado
        encryption = reader.manifest["encryption"]
        assert isinstance(encryption, dict)
        assert encryption["key_source"] == "external"


def test_bcp11_manifiesto_con_estado_de_licencia(
    mundo_origen: MundoOrigen, tmp_path: Path
) -> None:
    """BCP-11: el manifiesto recoge el estado de licencia de la instalación (convergencia F1)."""
    ahora = datetime.now(UTC)
    engine = create_engine(mundo_origen.db_url)
    with Session(engine) as session:
        session.add(
            LicenseState(
                installation_id=mundo_origen.installation_uuid,
                license_id="LIC-BCP-11",
                mode="FULL_ACCESS",
                period_start=ahora - timedelta(days=30),
                period_end=ahora + timedelta(days=120),
                entitlements={},
                last_reliable_date=ahora,
            )
        )
        session.commit()
    engine.dispose()

    destination = tmp_path / "out"
    destination.mkdir()
    key = _clave()

    result = create_backup(
        db_url=mundo_origen.db_url,
        storage_root=mundo_origen.storage_root,
        destination_dir=destination,
        key=key,
        pg_bin_dir=PG_BIN,
        audit=False,
    )

    with BundleReader(result.path, key) as reader:
        licencias = reader.manifest["license"]

    assert isinstance(licencias, list) and len(licencias) == 1
    entrada = licencias[0]
    assert isinstance(entrada, dict)
    assert entrada["license_id"] == "LIC-BCP-11" and entrada["mode"] == "FULL_ACCESS"
    assert entrada["period_end"] is not None and entrada["last_reliable_date"] is not None
