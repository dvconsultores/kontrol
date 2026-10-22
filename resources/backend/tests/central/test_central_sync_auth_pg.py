"""SYNC-PG · Lo que solo PostgreSQL prueba del sync autenticado: el consumo ATÓMICO del desafío bajo
concurrencia (FR-010-391..392) y la migración `0002` sobre una base con filas previas (FR-010-420..423).

Marcador PG-only del repositorio. Varias peticiones idénticas y válidas con el mismo desafío llegan a
la vez por hilos distintos (sesiones distintas): exactamente una autentica; las demás son
`SYNC_CHALLENGE_USED`. La migración conserva las instalaciones ya registradas, calcula su huella desde
el PEM guardado y deja la unicidad de clave en la base.
"""

from __future__ import annotations

import os
import subprocess
import threading
import uuid
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core import sync_auth_contract as sa
from central_authority import database, main, service
from central_authority.config import Settings
from central_authority.models import Base
from tests.alembic_orden import orden_alembic
from tests.central.conftest import pem_privada, pem_publica
from tests.conftest import make_engine

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL.startswith("postgresql"), reason="el consumo atómico y las migraciones se certifican en PostgreSQL")
BACKEND = Path(__file__).resolve().parents[2]
INST = "KTL-XX-SINTETICA-PG-SYNC"


@pytest.fixture
def mundo(monkeypatch):
    propietario, identidad = Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    ajustes = Settings(_env_file=None, environment="qa", db_url=PG_URL, signing_private_key_pem=pem_privada(propietario))
    motor = make_engine()
    Base.metadata.create_all(motor)
    factoria = sessionmaker(bind=motor, class_=Session, expire_on_commit=False)
    with factoria() as db:
        service.register_installation(db, installation_uuid=INST, public_key_pem=pem_publica(identidad), customer_id="CUS", contract_id="CON",
                                      company_tax_id=None, operator="ana")
        inicio, fin = service.periodo_anual(2030)
        service.issue_license(db, settings=ajustes, installation_uuid=INST, period_start=inicio, period_end=fin, entitlements={"companies": 1},
                              minimum_version="1.0.0", operator="ana")
    monkeypatch.setattr(main, "get_settings", lambda: ajustes)
    app = main.create_app()

    def _db():
        d = factoria()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[database.get_db] = _db
    yield {"c": TestClient(app), "identidad": identidad, "factoria": factoria}
    Base.metadata.drop_all(motor)


def _peticion_valida(mundo) -> tuple[bytes, dict[str, str]]:
    c = mundo["c"]
    desafio = c.post(sa.CHALLENGE_TARGET, content=sa.canonical_body({"installation_id": INST}), headers={"Content-Type": "application/json"}).json()
    body = sa.canonical_body({"version": "1.0", "installation_id": INST, "license_jws": "", "modules": [], "requested_at": "2026-10-07T00:00:00+00:00"})
    sobre = sa.build_envelope(installation_id=INST, challenge_id=desafio["challenge_id"], nonce=desafio["nonce"], method="POST",
                              target=sa.SYNC_TARGET, body_sha256=sa.body_sha256(body))
    cab = {"Content-Type": "application/json", sa.HEADER_PROTOCOL: "1", sa.HEADER_INSTALLATION: INST, sa.HEADER_CHALLENGE: desafio["challenge_id"],
           sa.HEADER_NONCE: desafio["nonce"], sa.HEADER_SIGNATURE: sa.sign_envelope(sobre, mundo["identidad"])}
    return body, cab


def test_syncpg_01_peticiones_identicas_concurrentes_con_el_mismo_desafio_autentican_exactamente_una(mundo):
    for ronda in range(4):
        body, cab = _peticion_valida(mundo)
        barrera = threading.Barrier(4, timeout=15)
        resultados: list[tuple[int, str]] = []
        candado = threading.Lock()

        def disparar(barrera=barrera, body=body, cab=cab, resultados=resultados, candado=candado) -> None:
            barrera.wait()
            r = mundo["c"].post(sa.SYNC_TARGET, content=body, headers=cab)
            with candado:
                resultados.append((r.status_code, r.json().get("code", r.json().get("status"))))

        hilos = [threading.Thread(target=disparar) for _ in range(4)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join(timeout=60)
            assert not h.is_alive()
        assert sorted(resultados) == [(200, "LICENSE"), (401, "SYNC_CHALLENGE_USED"), (401, "SYNC_CHALLENGE_USED"), (401, "SYNC_CHALLENGE_USED")], (ronda, resultados)


def _alembic(url: str, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "KONTROL_CENTRAL_DB_URL": url, "KONTROL_CENTRAL_ENVIRONMENT": "qa"}
    return subprocess.run(orden_alembic("-c", "central_authority/alembic.ini", *args), cwd=BACKEND, env=env,
                          capture_output=True, text=True)


@pytest.fixture
def base_central_limpia():
    admin = create_engine(PG_URL.rsplit("/", 1)[0] + "/postgres", isolation_level="AUTOCOMMIT", future=True)
    nombre = f"cla_sync_{uuid.uuid4().hex[:8]}"
    with admin.connect() as c:
        c.execute(text(f'create database "{nombre}"'))
    url = PG_URL.rsplit("/", 1)[0] + f"/{nombre}"
    yield url
    with admin.connect() as c:
        c.execute(text(f'drop database "{nombre}" with (force)'))
    admin.dispose()


def test_syncpg_02_la_migracion_0002_conserva_las_filas_previas_calcula_su_huella_y_deja_la_unicidad(base_central_limpia):
    assert _alembic(base_central_limpia, "upgrade", "0001_cla_fase1").returncode == 0
    motor = create_engine(base_central_limpia, future=True)
    claves = {f"KTL-XX-PREVIA-{i}": pem_publica(Ed25519PrivateKey.generate()) for i in range(2)}
    with motor.begin() as c:
        for inst, pem in claves.items():
            c.execute(text("insert into cla_installations (id, installation_uuid, public_key_pem, customer_id, contract_id, registered_by, created_at) "
                           "values (:id, :u, :p, 'CUS', 'CON', 'ana', now())"), {"id": str(uuid.uuid4()), "u": inst, "p": pem})
    r = _alembic(base_central_limpia, "upgrade", "head")
    assert r.returncode == 0, r.stderr[-800:]
    insp = inspect(motor)
    assert "cla_sync_challenges" in insp.get_table_names()
    with motor.connect() as c:
        assert c.execute(text("select version_num from cla_alembic_version")).scalar_one() == "0002_cla_sync_auth"
        filas = c.execute(text("select installation_uuid, public_key_fingerprint from cla_installations order by installation_uuid")).all()
    assert [(u, h) for u, h in filas] == [(u, sa.public_key_fingerprint(p)) for u, p in sorted(claves.items())]  # conservadas, con huella
    assert all(not i["nullable"] for i in insp.get_columns("cla_installations") if i["name"] == "public_key_fingerprint")
    indices = {i["name"]: i for i in insp.get_indexes("cla_installations")}
    assert indices["uq_cla_installations_public_key_fingerprint"]["unique"] is True
    assert {"ix_cla_sync_challenges_installation", "ix_cla_sync_challenges_expires_at"} <= {i["name"] for i in insp.get_indexes("cla_sync_challenges")}
    # La unicidad vive en la base: la misma clave para otra instalación no entra ni saltándose el servicio.
    with pytest.raises(IntegrityError), motor.begin() as c:
        c.execute(text("insert into cla_installations (id, installation_uuid, public_key_pem, public_key_fingerprint, customer_id, contract_id, "
                       "registered_by, created_at) values (:id, 'KTL-XX-DUPLICADA', :p, :h, 'CUS', 'CON', 'ana', now())"),
                  {"id": str(uuid.uuid4()), "p": list(claves.values())[0], "h": sa.public_key_fingerprint(list(claves.values())[0])})
    for tabla in Base.metadata.tables.values():
        assert {c.name for c in tabla.columns} == {c["name"] for c in inspect(motor).get_columns(tabla.name)}, tabla.name
    assert _alembic(base_central_limpia, "downgrade", "0001_cla_fase1").returncode == 0
    assert "cla_sync_challenges" not in inspect(motor).get_table_names()
    assert "public_key_fingerprint" not in {c["name"] for c in inspect(motor).get_columns("cla_installations")}
    motor.dispose()
