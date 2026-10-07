"""SYNC · La Autoridad Central autentica a la instalación con desafío-respuesta sobre su identidad
Ed25519 (`CENTRAL-SYNC-AUTHORITY-UNDEFINED`; FR-010-367..429).

Mundo sintético: clave del propietario (firma licencias), clave de la instalación (firma la prueba),
registro central con la pública vinculada por el vendor, un libro con emisiones. La API se ejercita con
`TestClient` sobre la app real; la base es la del módulo (SQLite en memoria o PostgreSQL con
`KONTROL_TEST_DB_URL`). La carrera de consumo y la migración con filas previas van en
`test_central_sync_auth_pg.py`. Nada real: ni claves, ni identificadores, ni licencias.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core import license_contract as contract
from app.core import sync_auth_contract as sa
from central_authority import database, main, service
from central_authority.config import Settings
from central_authority.models import AuditEvent, Installation, SyncChallenge
from tests.central.conftest import pem_privada, pem_publica

INST_A = "KTL-XX-SINTETICA-A"
INST_B = "KTL-XX-SINTETICA-B"
MATERIAL = ("BEGIN PUBLIC KEY", "BEGIN PRIVATE KEY", "nonce_sha256", "public_key", "customer_id", "contract_id", "payload_hash")


class Mundo:
    def __init__(self, factoria: sessionmaker, ajustes: Settings, propietario: Ed25519PrivateKey, cliente: TestClient) -> None:
        self.factoria, self.ajustes, self.propietario, self.c = factoria, ajustes, propietario, cliente
        self.claves = {INST_A: Ed25519PrivateKey.generate(), INST_B: Ed25519PrivateKey.generate()}
        with factoria() as db:
            for inst, clave in self.claves.items():
                service.register_installation(db, installation_uuid=inst, public_key_pem=pem_publica(clave), customer_id=f"CUS-{inst[-1]}",
                                              contract_id="CON", company_tax_id=None, operator="ana")

    def emite(self, inst: str, anio: int, **entitlements: Any) -> dict[str, Any]:
        inicio, fin = service.periodo_anual(anio)
        with self.factoria() as db:
            return service.issue_license(db, settings=self.ajustes, installation_uuid=inst, period_start=inicio, period_end=fin,
                                         entitlements=entitlements or {"companies": 3}, minimum_version="1.0.0", operator="ana")

    def desafio(self, inst: str):
        return self.c.post(sa.CHALLENGE_TARGET, content=sa.canonical_body({"installation_id": inst}), headers={"Content-Type": "application/json"})

    def cuerpo(self, inst: str) -> bytes:
        return sa.canonical_body({"version": "1.0", "installation_id": inst, "license_jws": "", "modules": ["ventas"], "requested_at": "2026-10-07T00:00:00+00:00"})

    def cabeceras(self, inst: str, desafio: dict[str, Any], body: bytes, *, clave: Ed25519PrivateKey | None = None, method: str = "POST",
                  target: str = sa.SYNC_TARGET, version: Any = 1, nonce: str | None = None, firmante_id: str | None = None) -> dict[str, str]:
        sobre = sa.build_envelope(installation_id=firmante_id or inst, challenge_id=str(desafio["challenge_id"]), nonce=nonce or str(desafio["nonce"]),
                                  method=method, target=target, body_sha256=sa.body_sha256(body), protocol_version=1)
        return {
            "Content-Type": "application/json",
            sa.HEADER_PROTOCOL: str(version), sa.HEADER_INSTALLATION: inst, sa.HEADER_CHALLENGE: sobre["challenge_id"],
            sa.HEADER_NONCE: sobre["nonce"], sa.HEADER_SIGNATURE: sa.sign_envelope(sobre, clave or self.claves[inst]),
        }

    def sync(self, inst: str, *, body: bytes | None = None, desafio: dict[str, Any] | None = None, ruta: str = sa.SYNC_TARGET, **kw: Any):
        body = body if body is not None else self.cuerpo(inst)
        desafio = desafio or self.desafio(inst).json()
        return self.c.post(ruta, content=body, headers=self.cabeceras(inst, desafio, body, **kw))

    def desafio_en_base(self, challenge_id: str) -> SyncChallenge | None:
        with self.factoria() as db:
            return db.get(SyncChallenge, challenge_id)

    def auditoria(self, operacion: str) -> list[AuditEvent]:
        with self.factoria() as db:
            return list(db.execute(select(AuditEvent).where(AuditEvent.operation == operacion).order_by(AuditEvent.created_at)).scalars().all())


@pytest.fixture
def mundo(factoria, ajustes, propietario, monkeypatch) -> Iterator[Mundo]:
    monkeypatch.setattr(main, "get_settings", lambda: ajustes)
    app = main.create_app()

    def _db():
        d = factoria()
        try:
            yield d
        finally:
            d.close()

    app.dependency_overrides[database.get_db] = _db
    yield Mundo(factoria, ajustes, propietario, TestClient(app))


# ---------------------------------------------------------------- SYNC-01..03 · el camino bueno y su repetición
def test_sync_01_el_desafio_devuelve_solo_lo_necesario_y_un_nonce_de_256_bits(mundo: Mundo):
    r = mundo.desafio(INST_A)
    assert r.status_code == 200 and set(r.json()) == {"protocol_version", "challenge_id", "nonce", "expires_at"}
    d = r.json()
    assert d["protocol_version"] == 1 and len(d["nonce"]) == 64 and d["nonce"] == d["nonce"].lower() and int(d["nonce"], 16) >= 0
    vence = datetime.fromisoformat(d["expires_at"])
    assert timedelta(seconds=0) < vence - datetime.now(UTC) <= timedelta(seconds=mundo.ajustes.sync_challenge_ttl_seconds)
    assert not any(t in r.text for t in MATERIAL) and "KTL-" not in r.text
    fila = mundo.desafio_en_base(d["challenge_id"])
    assert fila is not None and fila.nonce_sha256 == sa.nonce_digest(d["nonce"]) and fila.consumed_at is None  # se guarda el resumen, no el nonce


def test_sync_02_una_prueba_valida_devuelve_el_artefacto_exacto_del_libro_y_el_cliente_lo_verifica(mundo: Mundo):
    r1 = mundo.emite(INST_A, 2030)
    r = mundo.sync(INST_A)
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["status"] == "LICENSE" and cuerpo["version"] == "1" and cuerpo["license_id"] == r1["license_id"] and cuerpo["revision"] == 1
    assert cuerpo["license"] == {"payload": r1["payload"], "signature_hex": r1["signature_hex"]}  # bytes de firma intactos
    assert contract.verify_license_signature(cuerpo["license"]["payload"], cuerpo["license"]["signature_hex"], pem_publica(mundo.propietario))
    assert mundo.auditoria("SYNC")[-1].outcome == "OK" and mundo.auditoria("SYNC")[-1].issuance_id is not None


def test_sync_03_repetir_la_misma_peticion_identica_se_rechaza_como_usada(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    desafio = mundo.desafio(INST_A).json()
    body = mundo.cuerpo(INST_A)
    cab = mundo.cabeceras(INST_A, desafio, body)
    assert mundo.c.post(sa.SYNC_TARGET, content=body, headers=cab).status_code == 200
    repetida = mundo.c.post(sa.SYNC_TARGET, content=body, headers=cab)
    assert repetida.status_code == 401 and repetida.json()["code"] == "SYNC_CHALLENGE_USED", repetida.text
    assert mundo.desafio_en_base(desafio["challenge_id"]).consumed_at is not None
    assert mundo.auditoria("SYNC")[-1].outcome == "SYNC_CHALLENGE_USED"


# ---------------------------------------------------------------- SYNC-04..08 · desafío, nonce, firma
def test_sync_04_un_desafio_caducado_no_vale_y_no_resucita(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    desafio = mundo.desafio(INST_A).json()
    with mundo.factoria() as db:
        fila = db.get(SyncChallenge, desafio["challenge_id"])
        fila.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
    for _ in range(2):
        r = mundo.sync(INST_A, desafio=desafio)
        assert r.status_code == 401 and r.json()["code"] == "SYNC_CHALLENGE_EXPIRED"
    assert mundo.desafio_en_base(desafio["challenge_id"]).consumed_at is None


def test_sync_05_nonce_o_identificador_de_desafio_incorrectos(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    desafio = mundo.desafio(INST_A).json()
    r = mundo.sync(INST_A, desafio=desafio, nonce="cd" * 32)
    assert r.status_code == 401 and r.json()["code"] == "SYNC_CHALLENGE_INVALID"
    r = mundo.sync(INST_A, desafio={**desafio, "challenge_id": "99999999-9999-9999-9999-999999999999"})
    assert r.status_code == 401 and r.json()["code"] == "SYNC_CHALLENGE_INVALID"
    assert mundo.desafio_en_base(desafio["challenge_id"]).consumed_at is None  # el bueno sigue intacto
    assert mundo.sync(INST_A, desafio=desafio).status_code == 200


def test_sync_06_el_desafio_de_una_instalacion_no_autentica_a_otra(mundo: Mundo):
    mundo.emite(INST_B, 2030)
    desafio_a = mundo.desafio(INST_A).json()
    r = mundo.sync(INST_B, desafio=desafio_a)  # B firma correctamente con su clave, pero el desafío es de A
    assert r.status_code == 401 and r.json()["code"] == "SYNC_CHALLENGE_INVALID"
    assert mundo.desafio_en_base(desafio_a["challenge_id"]).consumed_at is None


def test_sync_07_alterar_el_cuerpo_tras_firmar_invalida_la_prueba_y_no_consume_el_desafio(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    desafio = mundo.desafio(INST_A).json()
    body = mundo.cuerpo(INST_A)
    cab = mundo.cabeceras(INST_A, desafio, body)
    alterado = body.replace(b'"ventas"', b'"compras"')
    r = mundo.c.post(sa.SYNC_TARGET, content=alterado, headers=cab)
    assert r.status_code == 401 and r.json()["code"] == "SYNC_AUTH_INVALID"
    # Ni siquiera una reserialización «equivalente» (con espacios) vale: el hash es de los bytes exactos.
    equivalente = json.dumps(json.loads(body), sort_keys=True, ensure_ascii=False).encode()
    assert equivalente != body and mundo.c.post(sa.SYNC_TARGET, content=equivalente, headers=cab).status_code == 401
    assert mundo.desafio_en_base(desafio["challenge_id"]).consumed_at is None
    assert mundo.c.post(sa.SYNC_TARGET, content=body, headers=cab).status_code == 200  # los bytes firmados sí entran


def test_sync_08_una_firma_de_otra_clave_o_rota_no_vale_y_no_consume(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    desafio = mundo.desafio(INST_A).json()
    r = mundo.sync(INST_A, desafio=desafio, clave=Ed25519PrivateKey.generate())
    assert r.status_code == 401 and r.json()["code"] == "SYNC_AUTH_INVALID"
    body = mundo.cuerpo(INST_A)
    cab = mundo.cabeceras(INST_A, desafio, body)
    cab[sa.HEADER_SIGNATURE] = "00" * 64
    assert mundo.c.post(sa.SYNC_TARGET, content=body, headers=cab).status_code == 401
    cab[sa.HEADER_SIGNATURE] = "no-es-hex"
    assert mundo.c.post(sa.SYNC_TARGET, content=body, headers=cab).status_code == 401
    assert mundo.desafio_en_base(desafio["challenge_id"]).consumed_at is None


# ---------------------------------------------------------------- SYNC-09..13 · método, destino, versión, identidad
def test_sync_09_metodo_y_destino_van_firmados(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    assert mundo.c.get(sa.SYNC_TARGET).status_code == 405
    r = mundo.sync(INST_A, ruta=sa.SYNC_TARGET + "?x=1")
    assert r.status_code == 401 and r.json()["code"] == "SYNC_TARGET_MISMATCH"
    r = mundo.sync(INST_A, target="/v1/license/other")  # firmado para otro destino, enviado al bueno
    assert r.status_code == 401 and r.json()["code"] == "SYNC_AUTH_INVALID"
    r = mundo.sync(INST_A, method="GET")  # firmado como GET, enviado como POST
    assert r.status_code == 401 and r.json()["code"] == "SYNC_AUTH_INVALID"


@pytest.mark.parametrize("version", ["2", "0", "abc", "", "1.0"], ids=["dos", "cero", "texto", "vacia", "decimal"])
def test_sync_10_una_version_de_protocolo_desconocida_se_rechaza_sin_degradar(mundo: Mundo, version: str):
    mundo.emite(INST_A, 2030)
    r = mundo.sync(INST_A, version=version)
    assert r.status_code in (400, 401) and r.json()["code"] in ("SYNC_PROTOCOL_UNSUPPORTED", "SYNC_AUTH_INVALID"), r.text
    if version not in ("",):
        assert r.status_code == 400 and r.json()["code"] == "SYNC_PROTOCOL_UNSUPPORTED"


def test_sync_11_una_instalacion_desconocida_recibe_un_desafio_igual_y_su_prueba_falla_sin_decir_por_que(mundo: Mundo):
    r = mundo.desafio("KTL-XX-NADIE")
    assert r.status_code == 200 and set(r.json()) == {"protocol_version", "challenge_id", "nonce", "expires_at"}
    assert mundo.desafio_en_base(r.json()["challenge_id"]).installation_id is None
    intrusa = Ed25519PrivateKey.generate()
    body = mundo.cuerpo("KTL-XX-NADIE")
    cab = mundo.cabeceras("KTL-XX-NADIE", r.json(), body, clave=intrusa)
    s = mundo.c.post(sa.SYNC_TARGET, content=body, headers=cab)
    assert s.status_code == 401 and s.json()["code"] == "SYNC_AUTH_INVALID"  # el mismo código que una firma inválida
    assert not any(t in s.text for t in MATERIAL) and "KTL-" not in s.text
    assert mundo.auditoria("SYNC_CHALLENGE")[-1].outcome == "UNKNOWN_INSTALLATION"


def test_sync_12_una_clave_publica_aportada_por_el_llamador_no_crea_confianza(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    intrusa = Ed25519PrivateKey.generate()
    desafio = mundo.desafio(INST_A).json()
    body = mundo.cuerpo(INST_A)
    cab = {**mundo.cabeceras(INST_A, desafio, body, clave=intrusa), "X-Kontrol-Public-Key": pem_publica(intrusa)}
    r = mundo.c.post(sa.SYNC_TARGET, content=body, headers=cab)
    assert r.status_code == 401 and r.json()["code"] == "SYNC_AUTH_INVALID"
    with mundo.factoria() as db:
        fila = db.execute(select(Installation).where(Installation.installation_uuid == INST_A)).scalars().one()
    assert fila.public_key_pem.strip() == pem_publica(mundo.claves[INST_A]).strip()  # el registro no cambió


def test_sync_13_la_instalacion_del_cuerpo_debe_ser_la_autenticada(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    mundo.emite(INST_B, 2031)
    body_b = mundo.cuerpo(INST_B)  # A firma su prueba sobre un cuerpo que pide la licencia de B
    r = mundo.sync(INST_A, body=body_b)
    assert r.status_code == 403 and r.json()["code"] == "SYNC_INSTALLATION_MISMATCH", r.text
    assert "2031" not in r.text and INST_B not in r.text
    # Y la petición de A para A sigue devolviendo solo la de A.
    assert mundo.sync(INST_A).json()["payload" if False else "license"]["payload"]["installation_id"] == INST_A


# ---------------------------------------------------------------- SYNC-14..16 · selección, sin licencia, cuerpos rotos
def test_sync_14_sin_emisiones_la_respuesta_canonica_es_no_license(mundo: Mundo):
    r = mundo.sync(INST_A)
    assert r.status_code == 200 and r.json() == {"version": "1", "status": "NO_LICENSE", "server_time": r.json()["server_time"], "license": None}
    assert mundo.auditoria("SYNC")[-1].outcome == "NO_LICENSE"


def test_sync_15_se_devuelve_el_periodo_mas_reciente_y_su_mayor_revision_no_la_ultima_emitida(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    r2_2030 = mundo.emite(INST_A, 2030)
    assert mundo.sync(INST_A).json()["license_id"] == r2_2030["license_id"]
    r1_2031 = mundo.emite(INST_A, 2031)
    assert mundo.sync(INST_A).json()["license_id"] == r1_2031["license_id"]
    r3_2030 = mundo.emite(INST_A, 2030)  # emitida después, pero de un período anterior: no manda
    respuesta = mundo.sync(INST_A).json()
    assert respuesta["license_id"] == r1_2031["license_id"] and respuesta["license_id"] != r3_2030["license_id"]


def test_sync_16_sin_cabeceras_o_con_cuerpo_ilegible(mundo: Mundo):
    mundo.emite(INST_A, 2030)
    r = mundo.c.post(sa.SYNC_TARGET, content=mundo.cuerpo(INST_A), headers={"Content-Type": "application/json"})
    assert r.status_code == 401 and r.json()["code"] == "SYNC_AUTH_INVALID"
    desafio = mundo.desafio(INST_A).json()
    roto = b"{no es json"
    r = mundo.c.post(sa.SYNC_TARGET, content=roto, headers=mundo.cabeceras(INST_A, desafio, roto))
    assert r.status_code == 403 and r.json()["code"] == "SYNC_INSTALLATION_MISMATCH"  # autenticado, pero sin identidad en el cuerpo
    assert mundo.desafio_en_base(desafio["challenge_id"]).consumed_at is not None  # la prueba era válida: se consumió


# ---------------------------------------------------------------- SYNC-17..20 · registro, fugas, limpieza, registros
def test_sync_17_una_clave_de_identidad_pertenece_a_una_sola_instalacion_y_no_se_sustituye(mundo: Mundo):
    with mundo.factoria() as db:
        with pytest.raises(service.CentralError) as exc:
            service.register_installation(db, installation_uuid="KTL-XX-TERCERA", public_key_pem=pem_publica(mundo.claves[INST_A]),
                                          customer_id="CUS-T", contract_id="CON", company_tax_id=None, operator="ana")
        assert exc.value.code == "INSTALLATION_KEY_ALREADY_BOUND"
        with pytest.raises(service.CentralError) as exc:
            service.register_installation(db, installation_uuid=INST_A, public_key_pem=pem_publica(Ed25519PrivateKey.generate()),
                                          customer_id="CUS-A", contract_id="CON", company_tax_id=None, operator="ana")
        assert exc.value.code == "INSTALLATION_CONFLICT"  # otra clave para la misma identidad: sin rotación silenciosa
        fila = db.execute(select(Installation).where(Installation.installation_uuid == INST_A)).scalars().one()
        assert fila.public_key_fingerprint == sa.public_key_fingerprint(pem_publica(mundo.claves[INST_A]))
        assert db.execute(select(Installation).where(Installation.installation_uuid == "KTL-XX-TERCERA")).scalars().first() is None


def test_sync_18_ningun_rechazo_expone_registro_licencia_ni_material(mundo: Mundo):
    mundo.emite(INST_A, 2030, companies=42)
    respuestas = [
        mundo.sync(INST_A, clave=Ed25519PrivateKey.generate()),
        mundo.sync(INST_A, nonce="ef" * 32),
        mundo.sync(INST_A, version="7"),
        mundo.sync(INST_A, body=mundo.cuerpo(INST_B)),
    ]
    for r in respuestas:
        assert r.status_code in (400, 401, 403) and set(r.json()) == {"code", "message"}
        assert not any(t in r.text for t in MATERIAL) and "42" not in r.text and "2030" not in r.text and "cla_" not in r.text


def test_sync_19_la_limpieza_perezosa_borra_lo_vencido_hace_mas_de_una_hora_y_nada_vencido_vuelve_a_valer(mundo: Mundo):
    viejo = mundo.desafio(INST_A).json()
    reciente = mundo.desafio(INST_A).json()
    with mundo.factoria() as db:
        db.get(SyncChallenge, viejo["challenge_id"]).expires_at = datetime.now(UTC) - timedelta(hours=2)
        db.get(SyncChallenge, reciente["challenge_id"]).expires_at = datetime.now(UTC) - timedelta(minutes=5)
        db.commit()
    mundo.desafio(INST_A)  # emite otro: limpia lo vencido hace más de una hora
    assert mundo.desafio_en_base(viejo["challenge_id"]) is None and mundo.desafio_en_base(reciente["challenge_id"]) is not None
    assert mundo.sync(INST_A, desafio=reciente).json()["code"] == "SYNC_CHALLENGE_EXPIRED"
    assert mundo.sync(INST_A, desafio=viejo).json()["code"] == "SYNC_CHALLENGE_INVALID"


def test_sync_20_los_registros_no_llevan_nonce_firma_ni_claves(mundo: Mundo, caplog):
    mundo.emite(INST_A, 2030)
    with caplog.at_level(logging.INFO):
        desafio = mundo.desafio(INST_A).json()
        body = mundo.cuerpo(INST_A)
        cab = mundo.cabeceras(INST_A, desafio, body)
        assert mundo.c.post(sa.SYNC_TARGET, content=body, headers=cab).status_code == 200
        mundo.c.post(sa.SYNC_TARGET, content=body, headers=cab)
    texto = caplog.text
    assert desafio["nonce"] not in texto and cab[sa.HEADER_SIGNATURE] not in texto
    assert "PRIVATE KEY" not in texto and pem_privada(mundo.claves[INST_A]).splitlines()[1] not in texto
