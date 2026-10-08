"""RL · El endpoint de desafío de la Autoridad Central tiene límite de tasa GLOBAL, explícito y configurable
(`CENTRAL-SYNC-SIN-LIMITE-DE-TASA`; FR-010-538..576). Defensa en profundidad: nada del desafío-respuesta
cambia. Mundo sintético con capacidad pequeña; SQLite en memoria o PostgreSQL con `KONTROL_TEST_DB_URL`.
La carrera entre trabajadores va en `test_central_challenge_rate_limit_pg.py`. Nada real.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.core import sync_auth_contract as sa
from central_authority import database, main, rate_limit, service
from central_authority.config import Settings
from central_authority.models import AuditEvent, Base, SyncChallenge
from tests.central.conftest import pem_privada, pem_publica

INST = "KTL-XX-SINTETICA-RL"
CAPACIDAD, VENTANA = 5, 60
MATERIAL = ("BEGIN PUBLIC KEY", "BEGIN PRIVATE KEY", "nonce", "KTL-", "cla_sync_challenges", "capacity", "created_at")


class Mundo:
    def __init__(self, factoria: sessionmaker, ajustes: Settings, cliente: TestClient, identidad: Ed25519PrivateKey) -> None:
        self.factoria, self.ajustes, self.c, self.identidad = factoria, ajustes, cliente, identidad

    def desafio(self, inst: str = INST):
        return self.c.post(sa.CHALLENGE_TARGET, content=sa.canonical_body({"installation_id": inst}), headers={"Content-Type": "application/json"})

    def llenar(self) -> list[dict[str, Any]]:
        emitidos = [self.desafio() for _ in range(CAPACIDAD)]
        assert all(r.status_code == 200 for r in emitidos), [r.status_code for r in emitidos]
        return [r.json() for r in emitidos]

    def filas(self) -> int:
        with self.factoria() as db:
            return int(db.execute(select(func.count()).select_from(SyncChallenge)).scalar_one())

    def auditoria(self, operacion: str) -> int:
        with self.factoria() as db:
            return int(db.execute(select(func.count()).select_from(AuditEvent).where(AuditEvent.operation == operacion)).scalar_one())

    def envejecer(self, segundos: int, *, solo: str | None = None) -> None:
        """El tiempo pasa: las filas de la ventana retroceden `segundos` (el reloj del servidor no se toca)."""
        with self.factoria() as db:
            for fila in db.execute(select(SyncChallenge)).scalars().all():
                if solo is None or fila.id == solo:
                    fila.created_at = fila.created_at - timedelta(seconds=segundos)
                    fila.expires_at = fila.expires_at - timedelta(seconds=segundos)
            db.commit()

    def prueba(self, desafio: dict[str, Any]):
        body = sa.canonical_body({"version": "1.0", "installation_id": INST, "license_jws": "", "modules": [], "requested_at": "2026-10-08T00:00:00+00:00"})
        sobre = sa.build_envelope(installation_id=INST, challenge_id=desafio["challenge_id"], nonce=desafio["nonce"], method="POST",
                                  target=sa.SYNC_TARGET, body_sha256=sa.body_sha256(body))
        cab = {"Content-Type": "application/json", sa.HEADER_PROTOCOL: "1", sa.HEADER_INSTALLATION: INST, sa.HEADER_CHALLENGE: desafio["challenge_id"],
               sa.HEADER_NONCE: desafio["nonce"], sa.HEADER_SIGNATURE: sa.sign_envelope(sobre, self.identidad)}
        return self.c.post(sa.SYNC_TARGET, content=body, headers=cab)


def _ajustes(propietario: Ed25519PrivateKey, **extra: Any) -> Settings:
    valores: dict[str, Any] = {"sync_challenge_rate_limit_capacity": CAPACIDAD, "sync_challenge_rate_limit_window_seconds": VENTANA, **extra}
    return Settings(_env_file=None, environment="qa", db_url="sqlite+pysqlite:///:memory:", signing_private_key_pem=pem_privada(propietario), **valores)


def _mundo(factoria: sessionmaker, ajustes: Settings, monkeypatch) -> Mundo:
    identidad = Ed25519PrivateKey.generate()
    with factoria() as db:
        service.register_installation(db, installation_uuid=INST, public_key_pem=pem_publica(identidad), customer_id="CUS", contract_id="CON",
                                      company_tax_id=None, operator="ana")
        inicio, fin = service.periodo_anual(2031)
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
    return Mundo(factoria, ajustes, TestClient(app), identidad)


@pytest.fixture
def mundo(factoria, propietario, monkeypatch) -> Iterator[Mundo]:
    service._rechazos_de_tasa.update({"pendientes": 0, "ultimo_aviso": None})
    yield _mundo(factoria, _ajustes(propietario), monkeypatch)


# ---------------------------------------------------------------- RL-01..03 · bajo el límite, por encima, Retry-After
def test_rl_01_bajo_el_limite_todos_los_desafios_se_emiten(mundo: Mundo):
    emitidos = mundo.llenar()
    assert len({d["challenge_id"] for d in emitidos}) == CAPACIDAD and mundo.filas() == CAPACIDAD


def test_rl_02_por_encima_del_limite_429_generico_sin_fila_ni_auditoria_nueva(mundo: Mundo):
    mundo.llenar()
    antes = (mundo.filas(), mundo.auditoria("SYNC_CHALLENGE"))
    r = mundo.desafio()
    assert r.status_code == 429 and r.json() == {"code": "SYNC_RATE_LIMITED", "message": "Demasiadas solicitudes de desafío. Inténtelo más tarde."}
    assert (mundo.filas(), mundo.auditoria("SYNC_CHALLENGE")) == antes  # ni fila de desafío ni evento de auditoría por el rechazo
    assert not any(m.lower() in r.text.lower() for m in MATERIAL)


def test_rl_03_retry_after_es_determinista_y_sale_del_mas_antiguo_de_la_ventana(mundo: Mundo):
    emitidos = mundo.llenar()
    r1, r2 = mundo.desafio(), mundo.desafio()
    assert 1 <= int(r1.headers["Retry-After"]) <= VENTANA and int(r2.headers["Retry-After"]) <= int(r1.headers["Retry-After"])
    mundo.envejecer(VENTANA - 10, solo=emitidos[0]["challenge_id"])  # el más antiguo saldrá de la ventana en ~10 s
    espera = int(mundo.desafio().headers["Retry-After"])
    assert 9 <= espera <= 11, espera


# ---------------------------------------------------------------- RL-04..05 · lo ya emitido sigue valiendo y autentica
def test_rl_04_un_429_no_toca_los_desafios_ya_emitidos(mundo: Mundo):
    emitidos = mundo.llenar()
    with mundo.factoria() as db:
        antes = {f.id: (f.nonce_sha256, f.expires_at, f.consumed_at, f.installation_id) for f in db.execute(select(SyncChallenge)).scalars().all()}
    assert mundo.desafio().status_code == 429
    with mundo.factoria() as db:
        despues = {f.id: (f.nonce_sha256, f.expires_at, f.consumed_at, f.installation_id) for f in db.execute(select(SyncChallenge)).scalars().all()}
    assert antes == despues and set(antes) == {d["challenge_id"] for d in emitidos}


def test_rl_05_con_la_emision_limitada_un_desafio_valido_anterior_autentica_y_devuelve_la_licencia(mundo: Mundo):
    c1 = mundo.llenar()[0]
    assert mundo.desafio().status_code == 429
    r = mundo.prueba(c1)
    assert r.status_code == 200 and r.json()["status"] == "LICENSE", r.text
    assert mundo.prueba(c1).json()["code"] == "SYNC_CHALLENGE_USED"  # un solo uso, como siempre


# ---------------------------------------------------------------- RL-06..07 · sin enumeración; installation_id no es autoridad
def test_rl_06_conocida_y_desconocida_reciben_el_mismo_429(mundo: Mundo):
    assert mundo.desafio("KTL-XX-NADIE").status_code == 200  # antes del límite, igual que una conocida
    for _ in range(CAPACIDAD - 1):
        assert mundo.desafio().status_code == 200
    conocida, desconocida = mundo.desafio(), mundo.desafio("KTL-XX-NADIE")
    assert conocida.status_code == desconocida.status_code == 429
    assert conocida.json() == desconocida.json() and conocida.headers["Retry-After"] == desconocida.headers["Retry-After"]


def test_rl_07_rotar_identidades_inventadas_no_esquiva_el_limite_global(mundo: Mundo):
    respuestas = [mundo.desafio(f"KTL-XX-FALSA-{i:03d}").status_code for i in range(CAPACIDAD * 3)]
    assert respuestas[:CAPACIDAD] == [200] * CAPACIDAD and respuestas[CAPACIDAD:] == [429] * (CAPACIDAD * 2)
    assert mundo.filas() == CAPACIDAD  # la tabla queda acotada por el límite


# ---------------------------------------------------------------- RL-08..09 · configuración y ventana deslizante
def test_rl_08_la_politica_es_configurable_y_en_prod_no_se_apaga(factoria, propietario, monkeypatch):
    apagado = _mundo(factoria, _ajustes(propietario, sync_challenge_rate_limit_enabled=False), monkeypatch)
    assert all(apagado.desafio().status_code == 200 for _ in range(CAPACIDAD * 2))
    with pytest.raises(ValueError, match="RATE_LIMIT_ENABLED no puede ser false en prod"):
        Settings(_env_file=None, environment="prod", db_url="sqlite+pysqlite:///:memory:", signing_private_key_pem=pem_privada(propietario),
                 sync_challenge_rate_limit_enabled=False)
    for invalido in ({"sync_challenge_rate_limit_capacity": 0}, {"sync_challenge_rate_limit_window_seconds": 0}, {"sync_challenge_rate_limit_window_seconds": 3601}):
        with pytest.raises(ValueError):
            _ajustes(propietario, **invalido)
    politica = service.politica_de_tasa(Settings(_env_file=None, environment="qa", db_url="sqlite+pysqlite:///:memory:"))
    assert politica == rate_limit.RateLimitPolicy(enabled=True, capacity=120, window_seconds=60)  # por defecto: activo


def test_rl_09_cuando_el_mas_antiguo_sale_de_la_ventana_vuelve_a_haber_hueco_exactamente_para_uno(mundo: Mundo):
    emitidos = mundo.llenar()
    assert mundo.desafio().status_code == 429
    mundo.envejecer(VENTANA + 1, solo=emitidos[0]["challenge_id"])
    assert mundo.desafio().status_code == 200
    assert mundo.desafio().status_code == 429
    mundo.envejecer(VENTANA + 1)  # toda la ventana vence: la capacidad entera vuelve (ráfaga = capacidad)
    assert all(mundo.desafio().status_code == 200 for _ in range(CAPACIDAD))


# ---------------------------------------------------------------- RL-10..12 · health, registros acotados, limpieza
def test_rl_10_el_health_no_se_limita_ni_revela_el_estado_del_limite(mundo: Mundo):
    mundo.llenar()
    for _ in range(3):
        assert mundo.desafio().status_code == 429
    assert mundo.c.get("/health/live").json() == {"status": "ok", "service": "kontrol-central-authority"}
    listo = mundo.c.get("/health/ready")
    assert listo.status_code == 200 and set(listo.json()) == {"status", "service", "database"}


def test_rl_11_los_rechazos_se_registran_acotados_y_sin_identidad_del_llamador(mundo: Mundo, caplog):
    mundo.llenar()
    with caplog.at_level(logging.WARNING, logger="central_authority.service"):
        for _ in range(7):
            assert mundo.desafio("KTL-XX-ATACANTE").status_code == 429
    avisos = [r for r in caplog.records if "límite de tasa" in r.getMessage()]
    assert len(avisos) == 1 and "1 rechazos" in avisos[0].getMessage()  # el primero avisa; los seis siguientes se acumulan para el próximo aviso
    assert "KTL-XX-ATACANTE" not in caplog.text and "nonce" not in caplog.text.lower()
    assert service._rechazos_de_tasa["pendientes"] == 6


def test_rl_12_la_limpieza_perezosa_sigue_igual_y_no_cuenta_lo_que_borra(mundo: Mundo):
    viejo = mundo.desafio().json()
    mundo.envejecer(3 * 3600, solo=viejo["challenge_id"])  # vencido hace horas: la limpieza lo borra al emitir
    assert all(mundo.desafio().status_code == 200 for _ in range(CAPACIDAD))
    with mundo.factoria() as db:
        assert db.get(SyncChallenge, viejo["challenge_id"]) is None
    assert mundo.filas() == CAPACIDAD and mundo.desafio().status_code == 429


# ---------------------------------------------------------------- RL-13 · esquema y contrato intactos
def test_rl_13_esquema_central_cero_y_el_resto_del_protocolo_no_cambia():
    assert {c.name for c in Base.metadata.tables["cla_sync_challenges"].columns} == {
        "id", "installation_id", "nonce_sha256", "protocol_version", "created_at", "expires_at", "consumed_at"}
    assert {i.name for i in Base.metadata.tables["cla_sync_challenges"].indexes} == {"ix_cla_sync_challenges_installation", "ix_cla_sync_challenges_expires_at"}
    assert sorted(Base.metadata.tables) == ["cla_audit_events", "cla_installations", "cla_issuances", "cla_period_lineages", "cla_sync_challenges"]
    decision = rate_limit.decide(policy=rate_limit.RateLimitPolicy(True, 1, 60), now=datetime.now(UTC), issued_in_window=1, oldest_in_window=None)
    assert decision == rate_limit.RateLimitDecision(False, rate_limit.CAPACITY_EXCEEDED, 60)  # sin instante: cerrado, ventana entera


def test_rl_14_un_rechazo_no_deja_transaccion_en_vuelo_y_la_sesion_sigue_usable(mundo: Mundo):
    """Invariante del servicio: tras el 429 no queda transacción abierta (la limpieza perezosa y el candado se
    deshacen) y la misma sesión puede seguir trabajando; la fila no existe."""
    mundo.llenar()
    with mundo.factoria() as db:
        with pytest.raises(service.SyncRateLimited) as exc:
            service.create_sync_challenge(db, settings=mundo.ajustes, installation_uuid=INST)
        assert exc.value.status_code == 429 and 1 <= exc.value.retry_after_seconds <= VENTANA
        assert not db.in_transaction()
        assert db.execute(select(func.count()).select_from(SyncChallenge)).scalar_one() == CAPACIDAD
