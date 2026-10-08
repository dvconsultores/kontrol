"""RL-PG · Lo que solo PostgreSQL prueba del límite de tasa de desafíos: con varias peticiones a la vez por
hilos distintos (sesiones distintas, como trabajadores distintos), el límite es EXACTO: se emiten
`capacidad` desafíos y ni uno más (candado consultivo transaccional alrededor de «contar + insertar»).
Marcador PG-only del repositorio. Nada real.
"""

from __future__ import annotations

import os
import threading

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core import sync_auth_contract as sa
from central_authority import database, main, service
from central_authority.config import Settings
from central_authority.models import Base, SyncChallenge
from tests.central.conftest import pem_privada
from tests.conftest import make_engine

PG_URL = os.environ.get("KONTROL_TEST_DB_URL", "")
pytestmark = pytest.mark.skipif(not PG_URL.startswith("postgresql"), reason="la exactitud del límite entre trabajadores se certifica en PostgreSQL")
CAPACIDAD, PETICIONES = 10, 24


@pytest.fixture
def mundo(monkeypatch):
    ajustes = Settings(_env_file=None, environment="qa", db_url=PG_URL, signing_private_key_pem=pem_privada(Ed25519PrivateKey.generate()),
                       sync_challenge_rate_limit_capacity=CAPACIDAD, sync_challenge_rate_limit_window_seconds=60)
    motor = make_engine()
    Base.metadata.create_all(motor)
    factoria = sessionmaker(bind=motor, class_=Session, expire_on_commit=False)
    monkeypatch.setattr(main, "get_settings", lambda: ajustes)
    app = main.create_app()

    def _db():
        d = factoria()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[database.get_db] = _db
    yield {"c": TestClient(app), "factoria": factoria}
    Base.metadata.drop_all(motor)


def test_rlpg_01_peticiones_concurrentes_emiten_exactamente_la_capacidad_y_el_resto_es_429(mundo):
    c = mundo["c"]
    resultados: list[int] = []
    cerrojo, barrera = threading.Lock(), threading.Barrier(PETICIONES)

    def pedir(i: int) -> None:
        barrera.wait()
        r = c.post(sa.CHALLENGE_TARGET, content=sa.canonical_body({"installation_id": f"KTL-XX-PG-{i:02d}"}), headers={"Content-Type": "application/json"})
        with cerrojo:
            resultados.append(r.status_code)

    hilos = [threading.Thread(target=pedir, args=(i,)) for i in range(PETICIONES)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(resultados) == [200] * CAPACIDAD + [429] * (PETICIONES - CAPACIDAD), resultados
    with mundo["factoria"]() as db:
        assert db.execute(select(func.count()).select_from(SyncChallenge)).scalar_one() == CAPACIDAD
