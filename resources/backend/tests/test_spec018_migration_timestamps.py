import os
import subprocess
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(
    not PG_URL.startswith("postgresql"),
    reason="Las migraciones de timestamps de importaciones solo se verifican sobre PostgreSQL",
)

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backend")
CABEZA_PUBLICA = "0084_fusion_importaciones_proc03"
CABEZA_FINAL = "0091_location_validations"


def _postgres_admin_url():
    return PG_URL.rsplit("/", 1)[0] + "/postgres"


def _db_url(name):
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _crear_base(name):
    engine = create_engine(_postgres_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        engine.dispose()


def _borrar_base(name):
    engine = create_engine(_postgres_admin_url(), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        engine.dispose()


def _alembic(name, target, comando="upgrade"):
    env = {**os.environ, "KONTROL_DB_URL": _db_url(name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    result = subprocess.run(
        orden_alembic(comando, target),
        cwd=BACKEND,
        env=env,
        capture_output=True,
        text=True,
        timeout=900,
    )
    assert result.returncode == 0, (
        f"Alembic {comando} {target} falló:\n"
        f"stdout[-2000:]: {result.stdout[-2000:]}\n"
        f"stderr[-2000:]: {result.stderr[-2000:]}"
    )


def _sql(name, statements):
    engine = create_engine(_db_url(name))
    try:
        with engine.begin() as conn:
            for stmt, params in statements:
                conn.execute(text(stmt), params)
    finally:
        engine.dispose()


def _rows(name, statement, **params):
    engine = create_engine(_db_url(name))
    try:
        with engine.connect() as conn:
            result = conn.execute(text(statement), params)
            return result.fetchall()
    finally:
        engine.dispose()


def _insert(name, statement, **params):
    engine = create_engine(_db_url(name))
    try:
        with engine.begin() as conn:
            conn.execute(text(statement), params)
    finally:
        engine.dispose()


def _sembrar_entidades(name):
    installation_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    company_id = str(uuid.uuid4())
    party_id = str(uuid.uuid4())

    _sql(
        name,
        [
            (
                """
                INSERT INTO installations (id, installation_uuid, state)
                VALUES (:id, :installation_uuid, 'PENDING')
                """,
                {"id": installation_id, "installation_uuid": str(uuid.uuid4())},
            ),
            (
                """
                INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at)
                VALUES (:id, :installation_id, :code, :nombre, 'MONO_COMPANY', 'ACTIVE', now(), now())
                """,
                {
                    "id": tenant_id,
                    "installation_id": installation_id,
                    "code": f"T{tenant_id[:8]}",
                    "nombre": "Tenant prueba",
                },
            ),
            (
                """
                INSERT INTO companies (id, tenant_id, code, legal_name, rif, created_at, updated_at)
                VALUES (:id, :tenant_id, :code, :legal_name, :rif, now(), now())
                """,
                {
                    "id": company_id,
                    "tenant_id": tenant_id,
                    "code": f"C{company_id[:8]}",
                    "legal_name": "Empresa prueba",
                    "rif": f"J{company_id[:8]}",
                },
            ),
            (
                """
                INSERT INTO parties (id, company_id, code, name, roles, created_at, updated_at)
                VALUES (:id, :company_id, :code, :name, CAST(:roles AS json), now(), now())
                """,
                {
                    "id": party_id,
                    "company_id": company_id,
                    "code": f"P{party_id[:8]}",
                    "name": "Tercero prueba",
                    "roles": '["SUPPLIER"]',
                },
            ),
        ],
    )
    return company_id, party_id


def test_especificacion_018_timestamps_importaciones():
    name = f"kontrol_spec018_{uuid.uuid4().hex[:12]}"
    _crear_base(name)
    try:
        _alembic(name, CABEZA_PUBLICA)
        company_id, supplier_id = _sembrar_entidades(name)

        import_file_id = str(uuid.uuid4())
        fecha_creacion = datetime(2023, 6, 15, 10, 30, 0, tzinfo=UTC)
        fecha_actualizacion = datetime(2023, 6, 15, 11, 45, 0, tzinfo=UTC)
        _sql(
            name,
            [
                (
                    """
                    INSERT INTO import_files (
                        id, created_at, updated_at, code, company_id, supplier_id, currency, status
                    )
                    VALUES (
                        :id, :created_at, :updated_at, :code, :company_id, :supplier_id, :currency, 'NEGOTIATING'
                    )
                    """,
                    {
                        "id": import_file_id,
                        "created_at": fecha_creacion,
                        "updated_at": fecha_actualizacion,
                        "code": f"IF{import_file_id[:8]}",
                        "company_id": company_id,
                        "supplier_id": supplier_id,
                        "currency": "VED",
                    },
                )
            ],
        )

        with pytest.raises(IntegrityError) as exc_info:
            _insert(
                name,
                """
                INSERT INTO import_files (id, code, company_id, supplier_id, currency, status)
                VALUES (:id, :code, :company_id, :supplier_id, :currency, 'NEGOTIATING')
                """,
                id=str(uuid.uuid4()),
                code=f"IF{uuid.uuid4().hex[:8]}",
                company_id=company_id,
                supplier_id=supplier_id,
                currency="VED",
            )
        assert "created_at" in str(exc_info.value)

        _alembic(name, "0086_importaciones_timestamps")

        fila = _rows(
            name,
            "SELECT created_at, updated_at FROM import_files WHERE id = :id",
            id=import_file_id,
        )
        assert len(fila) == 1
        creado, actualizado = fila[0]
        assert creado == fecha_creacion
        assert actualizado == fecha_actualizacion

        nuevo_id = str(uuid.uuid4())
        _insert(
            name,
            """
            INSERT INTO import_files (id, code, company_id, supplier_id, currency, status)
            VALUES (:id, :code, :company_id, :supplier_id, :currency, 'NEGOTIATING')
            """,
            id=nuevo_id,
            code=f"IF{nuevo_id[:8]}",
            company_id=company_id,
            supplier_id=supplier_id,
            currency="VED",
        )

        tablas = [
            "import_files",
            "import_documents",
            "import_tracking_events",
            "import_financial_links",
            "import_corrections",
        ]
        for tabla in tablas:
            defaults = _rows(
                name,
                """
                SELECT column_name, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :tabla
                  AND column_name IN ('created_at', 'updated_at')
                ORDER BY column_name
                """,
                tabla=tabla,
            )
            assert len(defaults) == 2, f"{tabla} debería tener created_at y updated_at"
            for columna, valor, nullable in defaults:
                assert valor is not None, f"{tabla}.{columna} no tiene default"
                assert nullable == "NO", f"{tabla}.{columna} debería ser NOT NULL"

        _alembic(name, CABEZA_PUBLICA, comando="downgrade")

        for tabla in tablas:
            defaults = _rows(
                name,
                """
                SELECT column_name, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = :tabla
                  AND column_name IN ('created_at', 'updated_at')
                ORDER BY column_name
                """,
                tabla=tabla,
            )
            assert len(defaults) == 2
            for _, valor in defaults:
                assert valor is None, f"{tabla} aún tiene default tras downgrade"

        fila = _rows(
            name,
            "SELECT created_at, updated_at FROM import_files WHERE id = :id",
            id=import_file_id,
        )
        assert len(fila) == 1
        creado, actualizado = fila[0]
        assert creado == fecha_creacion
        assert actualizado == fecha_actualizacion

        with pytest.raises(IntegrityError) as exc_info:
            _insert(
                name,
                """
                INSERT INTO import_files (id, code, company_id, supplier_id, currency, status)
                VALUES (:id, :code, :company_id, :supplier_id, :currency, 'NEGOTIATING')
                """,
                id=str(uuid.uuid4()),
                code=f"IF{uuid.uuid4().hex[:8]}",
                company_id=company_id,
                supplier_id=supplier_id,
                currency="VED",
            )
        assert "created_at" in str(exc_info.value)

        _alembic(name, "head")

        versiones = _rows(name, "SELECT version_num FROM alembic_version")
        assert len(versiones) == 1
        assert versiones[0][0] == CABEZA_FINAL
    finally:
        _borrar_base(name)


def test_guardian_sin_columnas_not_null_sin_default():
    name = f"kontrol_spec018_guard_{uuid.uuid4().hex[:12]}"
    _crear_base(name)
    try:
        _alembic(name, "head")

        infractoras = _rows(
            name,
            """
            SELECT table_name || '.' || column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND column_name IN ('created_at', 'updated_at')
              AND is_nullable = 'NO'
              AND column_default IS NULL
            ORDER BY table_name, column_name
            """,
        )
        assert not infractoras, (
            "Columnas NOT NULL sin default en la cabeza final: "
            + ", ".join(fila[0] for fila in infractoras)
        )
    finally:
        _borrar_base(name)
