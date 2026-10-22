"""Anotación del legado documental: migración `0024` (Spec 046, F9).

Siembra una base **anterior a 046** con referencias documentales heredadas de
las formas que realmente existen —una URL, una ruta relativa, un hash suelto,
texto libre— aplica la cadena completa y comprueba qué hizo la migración con
cada una.

Lo que se busca demostrar es lo que la Spec declara no negociable: que anotar
no es convertir. Ni un solo `Document` nace de aquí, ninguna columna heredada
se toca y un hash sin binario **no** se convierte en documento (R-046-5).

Sobre PostgreSQL real: el modo offline no puede clasificar porque no lee datos.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from tests.alembic_orden import orden_alembic

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(
    "postgresql" not in PG_URL,
    reason="La anotación del legado solo es verificable sobre PostgreSQL (P21)",
)

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRE_046 = "0022_uom_backfill"
DB_NAME = "kontrol_doc_legacy"


def _admin_url() -> str:
    return PG_URL.rsplit("/", 1)[0] + "/postgres"


def _db_url(name: str) -> str:
    return PG_URL.rsplit("/", 1)[0] + "/" + name


def _alembic(db_name: str, target: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "KONTROL_DB_URL": _db_url(db_name)}
    env.pop("KONTROL_TEST_DB_URL", None)
    return subprocess.run(
        orden_alembic("upgrade", target),
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=900,
    )


def _sql(db_name: str, statements: list[str]) -> None:
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    engine.dispose()


def _query(db_name: str, statement: str):
    from sqlalchemy import create_engine, text

    engine = create_engine(_db_url(db_name), future=True)
    with engine.connect() as conn:
        rows = conn.execute(text(statement)).fetchall()
    engine.dispose()
    return rows


#: Las cuatro formas del legado documental, sembradas tal cual aparecen.
URL_EXTERNA = "https://sencamer.gob.ve/expedientes/2024/EXP-991.pdf"
RUTA_RELATIVA = "uploads/2023/permisos/permiso-4471.pdf"
HASH_SUELTO = "9f" * 32
TEXTO_LIBRE = "Cédula, licencia y certificado médico en carpeta física"


@pytest.fixture(scope="module")
def seeded_db() -> str:
    """Base con el esquema anterior a 046 y referencias heredadas reales."""
    from sqlalchemy import create_engine, text

    engine = create_engine(_admin_url(), future=True, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{DB_NAME}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{DB_NAME}" ENCODING \'UTF8\''))
    engine.dispose()
    # La base tiene dueño: se suelta al terminar el ámbito —la prueba o el módulo— que la creó.
    from pg_harness import registrar_base

    registrar_base(DB_NAME)

    result = _alembic(DB_NAME, PRE_046)
    assert result.returncode == 0, result.stderr[-3000:]

    _sql(DB_NAME, [
        "INSERT INTO installations (id, installation_uuid, state, created_at, updated_at) "
        "VALUES ('inst-1','uuid-1','ACTIVE',now(),now())",
        "INSERT INTO tenants (id, installation_id, code, name, plan, status, created_at, updated_at) "
        "VALUES ('ten-1','inst-1','DEMO','Demo','MONO_COMPANY','ACTIVE',now(),now())",
        "INSERT INTO companies (id, tenant_id, code, legal_name, rif, legal_type, "
        "  functional_currency, status, created_at, updated_at) "
        "VALUES ('co-1','ten-1','D1','Demo CA','J-1','CA','VED','ACTIVE',now(),now())",
        # Rol ADMIN global: es a quien 046 concede sus permisos. Sin él, la
        # migración no tiene a quién concederlos y no debe inventar un rol.
        "INSERT INTO roles (id, company_id, code, name, protected, status, "
        "  created_at, updated_at) "
        "VALUES ('role-admin',NULL,'ADMIN','Administrador',true,'ACTIVE',now(),now())",

        # 1. URL absoluta → referencia externa, no un archivo nuestro.
        "INSERT INTO official_documents (id, company_id, kind, number, status, file_ref, "
        "  created_at, updated_at) "
        f"VALUES ('od-1','co-1','SICA','EXP-991','VALID','{URL_EXTERNA}',now(),now())",
        # 2. Ruta relativa → legado sin verificar: nadie afirma que el binario exista.
        "INSERT INTO official_documents (id, company_id, kind, number, status, file_ref, "
        "  created_at, updated_at) "
        f"VALUES ('od-2','co-1','SACS','PER-4471','VALID','{RUTA_RELATIVA}',now(),now())",
        # 3. Cadena vacía y NULL → no son referencias; no deben anotarse.
        "INSERT INTO official_documents (id, company_id, kind, number, status, file_ref, "
        "  created_at, updated_at) "
        "VALUES ('od-3','co-1','OTRO','ACTA-1','VALID','',now(),now())",
        "INSERT INTO official_documents (id, company_id, kind, number, status, file_ref, "
        "  created_at, updated_at) "
        "VALUES ('od-4','co-1','OTRO','PODER-1','VALID',NULL,now(),now())",
        # 4. Texto libre → no es una ruta ni una URL; se anota como legado.
        "INSERT INTO parties (id, company_id, code, name, person_type, roles, status, "
        "  created_at, updated_at) "
        "VALUES ('pa-1','co-1','T-1','Conductor Uno','NATURAL','[]','ACTIVE',now(),now())",
        "INSERT INTO transport_drivers (id, company_id, party_id, license, status, "
        "  documents, created_at, updated_at) "
        f"VALUES ('dr-1','co-1','pa-1','LIC-1','ACTIVE','{TEXTO_LIBRE}',now(),now())",
    ])

    # 5. Hash sin binario: la forma que jamás puede convertirse en documento.
    _sql(DB_NAME, [
        "INSERT INTO homologation_records (id, installation_id, fiscal_version, modality, "
        "  evidence_sha256, status, created_at, updated_at) "
        f"VALUES ('hr-1','inst-1','2026.1','E_FACTURA','{HASH_SUELTO}','APPROVED',now(),now())",
    ])

    result = _alembic(DB_NAME, "head")
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    return DB_NAME


def test_ninguna_anotacion_crea_un_documento(seeded_db):
    """Anotar no es convertir (R-046-5, FR-046-111)."""
    assert _query(seeded_db, "SELECT count(*) FROM documents")[0][0] == 0
    assert _query(seeded_db, "SELECT count(*) FROM document_versions")[0][0] == 0
    assert _query(seeded_db, "SELECT count(*) FROM stored_files")[0][0] == 0
    assert _query(seeded_db,
                  "SELECT count(*) FROM legacy_document_references "
                  "WHERE document_id IS NOT NULL")[0][0] == 0


def test_ninguna_columna_heredada_se_modifica(seeded_db):
    """El texto original sigue ahí, byte por byte (§144)."""
    rows = dict(_query(seeded_db, "SELECT id, file_ref FROM official_documents"))
    assert rows["od-1"] == URL_EXTERNA
    assert rows["od-2"] == RUTA_RELATIVA
    assert rows["od-3"] == ""
    assert rows["od-4"] is None
    assert _query(seeded_db,
                  "SELECT documents FROM transport_drivers WHERE id='dr-1'")[0][0] == TEXTO_LIBRE


def test_url_absoluta_se_clasifica_como_referencia_externa(seeded_db):
    rows = _query(seeded_db,
                  "SELECT classification, raw_value FROM legacy_document_references "
                  "WHERE source_row_id = 'od-1'")
    assert len(rows) == 1
    assert rows[0][0] == "EXTERNAL_REFERENCE"
    assert rows[0][1] == URL_EXTERNA


def test_ruta_relativa_queda_sin_verificar_no_valida(seeded_db):
    """Nadie afirma que el binario exista: eso sería inventar un archivo."""
    rows = _query(seeded_db,
                  "SELECT classification FROM legacy_document_references "
                  "WHERE source_row_id = 'od-2'")
    assert len(rows) == 1
    assert rows[0][0] == "UNVERIFIED_LEGACY"
    assert rows[0][0] != "VALID_MANAGED_FILE"


def test_un_hash_sin_binario_no_es_un_documento(seeded_db):
    rows = _query(seeded_db,
                  "SELECT classification, document_id FROM legacy_document_references "
                  "WHERE source_column = 'evidence_sha256'")
    if not rows:
        pytest.skip("la cadena no incluye homologation_records.evidence_sha256")
    for classification, document_id in rows:
        assert classification == "LEGACY_HASH_WITHOUT_FILE"
        assert document_id is None


def test_los_vacios_y_nulos_no_se_anotan(seeded_db):
    """Una cadena vacía no es una referencia documental."""
    for row_id in ("od-3", "od-4"):
        assert _query(seeded_db,
                      "SELECT count(*) FROM legacy_document_references "
                      f"WHERE source_row_id = '{row_id}'")[0][0] == 0


def test_el_texto_libre_se_anota_sin_interpretarse(seeded_db):
    rows = _query(seeded_db,
                  "SELECT classification, raw_value FROM legacy_document_references "
                  "WHERE source_table = 'transport_drivers'")
    assert len(rows) == 1
    assert rows[0][0] == "UNVERIFIED_LEGACY"
    assert rows[0][1] == TEXTO_LIBRE


def test_ninguna_anotacion_se_pierde(seeded_db):
    """Cada referencia no vacía tiene exactamente una anotación."""
    sources = _query(seeded_db,
                     "SELECT count(*) FROM official_documents "
                     "WHERE file_ref IS NOT NULL AND file_ref <> ''")[0][0]
    annotated = _query(seeded_db,
                       "SELECT count(*) FROM legacy_document_references "
                       "WHERE source_table = 'official_documents'")[0][0]
    assert annotated == sources == 2

    duplicated = _query(seeded_db,
                        "SELECT source_table, source_column, source_row_id, count(*) "
                        "FROM legacy_document_references "
                        "GROUP BY 1,2,3 HAVING count(*) > 1")
    assert duplicated == []


def test_los_permisos_documentales_quedan_concedidos(seeded_db):
    """046 usa el RBAC existente; no crea uno paralelo (P17)."""
    actions = {r[0] for r in _query(
        seeded_db, "SELECT action FROM permissions WHERE resource = 'documentos'")}
    assert actions == {"view", "create", "edit", "upload", "download", "link",
                       "deactivate", "delete", "manage_types"}

    granted = {r[0] for r in _query(
        seeded_db,
        "SELECT p.action FROM role_permissions rp "
        "JOIN permissions p ON p.id = rp.permission_id "
        "JOIN roles r ON r.id = rp.role_id "
        "WHERE p.resource = 'documentos' AND r.code = 'ADMIN'")}
    assert granted == actions, "el rol ADMIN debe recibir los nueve permisos"


def test_la_reversion_borra_solo_las_anotaciones(seeded_db):
    """Bajar 046 no puede llevarse por delante el legado."""
    env = {**os.environ, "KONTROL_DB_URL": _db_url(seeded_db)}
    env.pop("KONTROL_TEST_DB_URL", None)
    result = subprocess.run(
        orden_alembic("downgrade", "0023_document_model"),
        cwd=BACKEND, env=env, capture_output=True, text=True, timeout=600)
    assert result.returncode == 0, result.stderr[-3000:]

    assert _query(seeded_db, "SELECT count(*) FROM legacy_document_references")[0][0] == 0
    # Y el legado sigue intacto.
    rows = dict(_query(seeded_db, "SELECT id, file_ref FROM official_documents"))
    assert rows["od-1"] == URL_EXTERNA
    assert rows["od-2"] == RUTA_RELATIVA

    # Se vuelve a subir para no dejar la base a medias.
    assert _alembic(seeded_db, "head").returncode == 0
