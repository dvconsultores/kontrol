"""CLA · Autoridad Central de Licencias, Fase 1 (Spec 004, FR-010-267..318).

Registro de instalaciones, libro de emisiones, `revision` firmada y monótona por instalación + período,
paquete firmado que el verificador y el `import_license` del cliente aceptan, clave privada por
configuración y nunca generada, frontera de importación, health mínimo. La concurrencia y las
migraciones se prueban en PostgreSQL (`test_central_authority_pg.py`).
"""

from __future__ import annotations

import ast
import json
import logging
import pathlib
from datetime import UTC, datetime

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select

from app.core import license_contract as contract
from central_authority import cli, service
from central_authority.config import Settings, SigningKeyError, load_signing_key
from central_authority.models import AuditEvent, Issuance, PeriodLineage
from tests.central.conftest import pem_privada, pem_publica

INSTALACION = "KTL-XX-SINTETICA-0001"
MATERIAL = ("BEGIN PRIVATE KEY", "BEGIN PUBLIC KEY", "MC4CAQAwBQYDK2Vw", "signature_hex", "postgresql://")


def _registrar(db, operator: str = "ana") -> None:
    service.register_installation(db, installation_uuid=INSTALACION, public_key_pem=pem_publica(Ed25519PrivateKey.generate()),
                                  customer_id="CUS-000000", contract_id="CON-000000", company_tax_id="J-00000000-0", operator=operator)


def _emite(db, ajustes: Settings, anio: int = 2027, entitlements=None, operator: str = "ana") -> dict:
    inicio, fin = service.periodo_anual(anio)
    return service.issue_license(db, settings=ajustes, installation_uuid=INSTALACION, period_start=inicio, period_end=fin,
                                 entitlements=entitlements if entitlements is not None else {"companies": 3, "users": 25},
                                 minimum_version="1.0.0", operator=operator)


# ---------------------------------------------------------------- configuración y clave
def test_cla_01_en_prod_sin_clave_de_firma_la_configuracion_no_carga():
    with pytest.raises(ValidationError) as e:
        Settings(_env_file=None, environment="prod", db_url="postgresql+psycopg2://u:p@h/db", signing_private_key_pem=None)
    assert "KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM es obligatoria en prod" in str(e.value) and "clave missing" in str(e.value)
    assert "u:p@h" not in str(e.value)  # el error no reproduce la configuración


def test_cla_01b_en_prod_una_clave_que_no_sirve_tampoco_carga_y_nada_se_genera():
    publica_como_privada = pem_publica(Ed25519PrivateKey.generate())
    with pytest.raises(ValidationError) as e:
        Settings(_env_file=None, environment="prod", db_url="sqlite://", signing_private_key_pem=publica_como_privada)
    assert "clave invalid" in str(e.value) and "BEGIN" not in str(e.value)
    rsa_pem = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    with pytest.raises(SigningKeyError) as e2:
        load_signing_key(rsa_pem)
    assert e2.value.reason == "invalid"
    with pytest.raises(SigningKeyError) as e3:
        load_signing_key("   ")
    assert e3.value.reason == "missing"


def test_cla_02_fuera_de_prod_arranca_sin_clave_pero_no_emite(factoria):
    sin_clave = Settings(_env_file=None, environment="qa", db_url="sqlite://", signing_private_key_pem=None)
    with factoria() as db:
        _registrar(db)
        with pytest.raises(service.CentralError) as e:
            _emite(db, sin_clave)
        assert e.value.code == "SIGNING_KEY_MISSING"
        assert db.execute(select(Issuance)).scalars().all() == []
        assert [a.outcome for a in db.execute(select(AuditEvent)).scalars().all()][-1] == "SIGNING_KEY_MISSING"


# ---------------------------------------------------------------- registro
def test_cla_03_el_registro_es_idempotente_y_no_sobrescribe(factoria):
    clave = Ed25519PrivateKey.generate()
    with factoria() as db:
        a = service.register_installation(db, installation_uuid=INSTALACION, public_key_pem=pem_publica(clave), customer_id="CUS-1",
                                          contract_id="CON-1", company_tax_id="J-1", operator="ana")
        b = service.register_installation(db, installation_uuid=INSTALACION, public_key_pem=pem_publica(clave), customer_id="CUS-1",
                                          contract_id="CON-1", company_tax_id="J-1", operator="luis")
        assert a.id == b.id and b.registered_by == "ana"
        with pytest.raises(service.CentralError) as e:
            service.register_installation(db, installation_uuid=INSTALACION, public_key_pem=pem_publica(clave), customer_id="CUS-OTRO",
                                          contract_id="CON-1", company_tax_id="J-1", operator="luis")
        assert e.value.code == "INSTALLATION_CONFLICT"
        assert service.get_installation(db, INSTALACION).customer_id == "CUS-1"
        resultados = [x.outcome for x in db.execute(select(AuditEvent).where(AuditEvent.operation == "REGISTER_INSTALLATION")).scalars().all()]
        assert resultados == ["OK", "IDEMPOTENT", "INSTALLATION_CONFLICT"]


def test_cla_03b_una_clave_publica_que_no_es_ed25519_no_se_registra(factoria):
    with factoria() as db, pytest.raises(service.CentralError) as e:
        service.register_installation(db, installation_uuid="KTL-XX-RSA", public_key_pem="no es pem", customer_id="C", contract_id="K",
                                      company_tax_id=None, operator="ana")
    assert e.value.code == "INVALID_PUBLIC_KEY"


def test_cla_04_una_instalacion_desconocida_no_filtra_nada(factoria):
    with factoria() as db:
        _registrar(db)
        with pytest.raises(service.CentralError) as e:
            service.list_issuances(db, "KTL-XX-NO-EXISTE")
        assert e.value.code == "INSTALLATION_NOT_FOUND" and INSTALACION not in str(e.value)


# ---------------------------------------------------------------- emisión y revisión
def test_cla_05_la_primera_emision_del_periodo_es_revision_1_y_cada_reemision_sube(factoria, ajustes, propietario):
    with factoria() as db:
        _registrar(db)
        r1 = _emite(db, ajustes)
        r2 = _emite(db, ajustes, entitlements={"companies": 1})
        r3 = _emite(db, ajustes, entitlements={"companies": 9})
        assert [r1["revision"], r2["revision"], r3["revision"]] == [1, 2, 3]
        assert r1["payload"]["revision"] == 1 and r3["payload"]["entitlements"] == {"companies": 9}
        assert len({r1["license_id"], r2["license_id"], r3["license_id"]}) == 3
        linaje = db.execute(select(PeriodLineage)).scalars().one()
        assert linaje.last_revision == 3
        for r in (r1, r2, r3):  # firmados por el propietario, verificables con el contrato del cliente
            assert contract.verify_license_signature(r["payload"], r["signature_hex"], pem_publica(propietario))
            assert r["payload"]["kid"] == "kontrol-lic-2026-01" and r["payload"]["issuer"] == contract.ISSUER_NAME


def test_cla_06_la_revision_reinicia_por_periodo_y_es_independiente_por_instalacion(factoria, ajustes):
    with factoria() as db:
        _registrar(db)
        service.register_installation(db, installation_uuid="KTL-XX-OTRA", public_key_pem=pem_publica(Ed25519PrivateKey.generate()),
                                      customer_id="CUS-2", contract_id="CON-2", company_tax_id=None, operator="ana")
        assert [_emite(db, ajustes, 2027)["revision"] for _ in range(2)] == [1, 2]
        assert _emite(db, ajustes, 2028)["revision"] == 1
        inicio, fin = service.periodo_anual(2027)
        otra = service.issue_license(db, settings=ajustes, installation_uuid="KTL-XX-OTRA", period_start=inicio, period_end=fin,
                                     entitlements={}, minimum_version="1.0.0", operator="ana")
        assert otra["revision"] == 1


def test_cla_07_el_paquete_sigue_el_contrato_doc07_y_la_revision_va_firmada(factoria, ajustes, propietario):
    with factoria() as db:
        _registrar(db)
        r = _emite(db, ajustes, 2027)
    p = r["payload"]
    assert p["period_start"] == "2027-04-01T00:00:00-04:00" and p["period_end"] == "2028-03-31T23:59:59-04:00"
    assert p["critical_warning_start"] == "2028-04-21T00:00:00-04:00" and p["read_only_start"] == "2028-05-01T00:00:00-04:00"
    assert p["installation_id"] == INSTALACION and p["customer_id"] == "CUS-000000" and p["company_tax_id"] == "J-00000000-0"
    assert contract.parse_license_payload(p).revision == 1
    sin_revision = {k: v for k, v in p.items() if k != "revision"}
    assert not contract.verify_license_signature(sin_revision, r["signature_hex"], pem_publica(propietario))  # quitarla rompe la firma
    manipulado = {**p, "revision": 2}
    assert not contract.verify_license_signature(manipulado, r["signature_hex"], pem_publica(propietario))


def test_cla_08_el_libro_reproduce_el_artefacto_exacto_y_no_se_edita(factoria, ajustes):
    with factoria() as db:
        _registrar(db)
        r = _emite(db, ajustes)
        fila = service.get_issuance(db, r["license_id"])
        assert fila["payload"] == r["payload"] and fila["signature_hex"] == r["signature_hex"]
        assert fila["payload_hash"] == contract.payload_hash(r["payload"]) and fila["issued_by"] == "ana" and fila["revision"] == 1
        with pytest.raises(service.CentralError) as e:
            service.get_issuance(db, "LIC-NO-EXISTE")
        assert e.value.code == "ISSUANCE_NOT_FOUND"
    # No existe operación de actualización ni borrado del libro en el servicio ni en la CLI.
    publicas = {n for n in dir(service) if not n.startswith("_")}
    assert not any(any(v in n.lower() for v in ("update", "delete", "edit", "borrar", "editar")) for n in publicas)
    ordenes = {a.dest for a in cli.construir_parser()._actions}  # noqa: SLF001
    assert "orden" in ordenes
    assert set(cli.construir_parser()._subparsers._group_actions[0].choices) == {  # noqa: SLF001
        "register-installation", "issue-license", "reissue-license", "show-issuance", "list-issuances"}


def test_cla_09_un_fallo_al_firmar_deshace_todo_y_el_numero_no_se_consume(factoria, ajustes, monkeypatch):
    with factoria() as db:
        _registrar(db)
        _emite(db, ajustes)  # revision 1
        def firma_rota(*a, **k):
            raise RuntimeError("firma rota")
        monkeypatch.setattr(service.contract, "sign_license_payload", firma_rota)
        with pytest.raises(RuntimeError):
            _emite(db, ajustes)
        monkeypatch.undo()
        assert db.execute(select(PeriodLineage)).scalars().one().last_revision == 1
        assert len(db.execute(select(Issuance)).scalars().all()) == 1
        assert _emite(db, ajustes)["revision"] == 2  # sin huecos por fallo: el 2 nunca se consideró emitido


def test_cla_10_periodo_invalido_derechos_invalidos_e_instalacion_desconocida(factoria, ajustes):
    with factoria() as db:
        _registrar(db)
        inicio, fin = service.periodo_anual(2027)
        with pytest.raises(service.CentralError) as e:
            service.issue_license(db, settings=ajustes, installation_uuid=INSTALACION, period_start=fin, period_end=inicio,
                                  entitlements={}, minimum_version="1.0.0", operator="ana")
        assert e.value.code == "INVALID_PERIOD"
        with pytest.raises(service.CentralError) as e:
            service.issue_license(db, settings=ajustes, installation_uuid="KTL-XX-NO", period_start=inicio, period_end=fin,
                                  entitlements={}, minimum_version="1.0.0", operator="ana")
        assert e.value.code == "INSTALLATION_NOT_FOUND"
        with pytest.raises(service.CentralError) as e:
            service.issue_license(db, settings=ajustes, installation_uuid=INSTALACION, period_start=inicio, period_end=fin,
                                  entitlements=[1], minimum_version="1.0.0", operator="ana")  # type: ignore[arg-type]
        assert e.value.code == "INVALID_ENTITLEMENTS"
        assert db.execute(select(Issuance)).scalars().all() == []


# ---------------------------------------------------------------- compatibilidad con el cliente
def test_cla_11_el_cliente_acepta_el_paquete_de_la_autoridad_como_reemision_del_periodo(factoria, ajustes, propietario, monkeypatch, tmp_path):
    """Caso A de la auditoría de compatibilidad: el `import_license` del cliente parsea un paquete con
    `revision`, la firma verifica sobre el mismo dict y lo aplica. El cliente aún no compara `revision`."""
    from sqlalchemy.orm import Session, sessionmaker

    from app.core.config import get_settings
    from app.core.database import Base as BaseCliente
    from app.core.database import init_models
    from app.modules.licensing import service as cliente
    from app.modules.licensing.models import LicenseState
    from app.modules.organization.models import Installation
    from app.modules.setup.api import SetupRequest, initialize
    from tests.conftest import make_engine

    monkeypatch.setenv("KONTROL_LICENSE_PUBLIC_KEY_PEM", pem_publica(propietario))
    monkeypatch.setenv("KONTROL_INSTALLATION_VOLUME_PATH", str(tmp_path))
    get_settings.cache_clear()
    motor = make_engine()
    init_models()
    BaseCliente.metadata.create_all(motor)
    fab = sessionmaker(bind=motor, class_=Session, expire_on_commit=False)
    with fab() as dbc:
        initialize(dbc, SetupRequest(tenant_code="DEMO", tenant_name="Demo", company_code="D1", company_legal_name="Demo C.A.",
                                     company_rif="J-12345678-9", admin_username="admin", admin_password="Kontrol2026Segura!"))
        uuid_cliente = dbc.execute(select(Installation)).scalars().first().installation_uuid
        dbc.commit()
    with factoria() as db:
        service.register_installation(db, installation_uuid=uuid_cliente, public_key_pem=pem_publica(Ed25519PrivateKey.generate()),
                                      customer_id="CUS-9", contract_id="CON-9", company_tax_id="J-9", operator="ana")
        inicio, fin = service.periodo_anual(datetime.now(UTC).year if datetime.now(UTC).month >= 4 else datetime.now(UTC).year - 1)
        r1 = service.issue_license(db, settings=ajustes, installation_uuid=uuid_cliente, period_start=inicio, period_end=fin,
                                   entitlements={"companies": 3}, minimum_version="1.0.0", operator="ana")
        r2 = service.issue_license(db, settings=ajustes, installation_uuid=uuid_cliente, period_start=inicio, period_end=fin,
                                   entitlements={"companies": 1}, minimum_version="1.0.0", operator="ana")
    with fab() as dbc:
        estado = cliente.import_license(dbc, payload=r1["payload"], signature_hex=r1["signature_hex"], source="MANUAL")
        dbc.commit()
        assert estado.license_id == r1["license_id"] and estado.mode == "FULL_ACCESS"
        estado = cliente.import_license(dbc, payload=r2["payload"], signature_hex=r2["signature_hex"], source="MANUAL")
        dbc.commit()
        assert estado.license_id == r2["license_id"] and estado.entitlements == {"companies": 1}
        assert dbc.execute(select(LicenseState)).scalars().one().license_id == r2["license_id"]
    get_settings.cache_clear()
    BaseCliente.metadata.drop_all(motor)


def test_cla_12_una_legacy_sintetica_sigue_verificando_y_sus_bytes_no_cambian(propietario):
    legacy = {"issuer": "QA", "license_id": "LIC-LEGACY", "installation_id": INSTALACION, "customer_id": "C", "contract_id": "K",
              "company_tax_id": "J-0", "period_start": "2027-04-01T00:00:00-04:00", "period_end": "2028-03-31T23:59:59-04:00",
              "critical_warning_start": "2028-04-21T00:00:00-04:00", "read_only_start": "2028-05-01T00:00:00-04:00",
              "entitlements": {"companies": 3}, "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01"}
    antes = json.dumps(legacy, sort_keys=True, ensure_ascii=False).encode("utf-8")
    firma = propietario.sign(antes).hex()
    assert contract.canonical_bytes(legacy) == antes
    assert contract.verify_license_signature(legacy, firma, pem_publica(propietario))
    assert contract.parse_license_payload(legacy).revision is None
    assert not contract.verify_license_signature({**legacy, "revision": None}, firma, pem_publica(propietario))


def test_cla_13_el_cliente_rechaza_cerrado_un_paquete_firmado_con_revision_invalida(factoria, ajustes, propietario, monkeypatch, tmp_path):
    from sqlalchemy.orm import Session, sessionmaker

    from app.core.config import get_settings
    from app.core.database import Base as BaseCliente
    from app.core.database import init_models
    from app.core.errors import KontrolError
    from app.modules.licensing import service as cliente
    from app.modules.organization.models import Installation
    from app.modules.setup.api import SetupRequest, initialize
    from tests.conftest import make_engine

    monkeypatch.setenv("KONTROL_LICENSE_PUBLIC_KEY_PEM", pem_publica(propietario))
    monkeypatch.setenv("KONTROL_INSTALLATION_VOLUME_PATH", str(tmp_path))
    get_settings.cache_clear()
    motor = make_engine()
    init_models()
    BaseCliente.metadata.create_all(motor)
    fab = sessionmaker(bind=motor, class_=Session, expire_on_commit=False)
    with fab() as dbc:
        initialize(dbc, SetupRequest(tenant_code="DEMO", tenant_name="Demo", company_code="D1", company_legal_name="Demo C.A.",
                                     company_rif="J-12345678-9", admin_username="admin", admin_password="Kontrol2026Segura!"))
        uuid_cliente = dbc.execute(select(Installation)).scalars().first().installation_uuid
        dbc.commit()
        malo = {"issuer": "QA", "license_id": "LIC-MALA", "installation_id": uuid_cliente, "customer_id": "C", "contract_id": "K",
                "company_tax_id": "J-0", "period_start": "2027-04-01T00:00:00-04:00", "period_end": "2028-03-31T23:59:59-04:00",
                "entitlements": {}, "minimum_version": "1.0.0", "kid": "kontrol-lic-2026-01", "revision": 0}
        firma = contract.sign_license_payload(malo, propietario)
        with pytest.raises(KontrolError) as e:
            cliente.import_license(dbc, payload=malo, signature_hex=firma, source="MANUAL")
        assert e.value.code == "LICENSE_INVALID_REVISION" and e.value.status_code == 423
    get_settings.cache_clear()
    BaseCliente.metadata.drop_all(motor)


# ---------------------------------------------------------------- frontera, health, CLI, registros
def test_cla_14_la_autoridad_no_importa_nada_del_cliente_salvo_el_contrato_puro():
    raiz = pathlib.Path(__file__).resolve().parents[2] / "central_authority"
    prohibidos = ("app.core.config", "app.core.database", "app.core.errors", "app.core.dependencies", "app.modules", "app.shared", "app.main")
    for fichero in raiz.rglob("*.py"):
        arbol = ast.parse(fichero.read_text())
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.ImportFrom):
                modulos = [f"{nodo.module}.{a.name}" for a in nodo.names]
            elif isinstance(nodo, ast.Import):
                modulos = [a.name for a in nodo.names]
            else:
                modulos = []
            for m in modulos:
                assert not m.startswith(prohibidos), f"{fichero.name} importa {m}"
                if m.startswith("app."):
                    assert m == "app.core.license_contract" or m.startswith("app.core.license_contract."), f"{fichero.name} importa {m}"
    assert not (pathlib.Path(__file__).resolve().parents[2] / "central_authority" / "alembic" / "versions" / "0001_cla_fase1.py").read_text().count("app.")


def test_cla_15_health_minimo_sin_informacion_sensible(ajustes, monkeypatch):
    from central_authority import database, main
    monkeypatch.setattr(main, "get_settings", lambda: ajustes)
    monkeypatch.setattr(database, "get_settings", lambda: ajustes)
    database.get_engine.cache_clear()
    app = main.create_app()
    c = TestClient(app)
    assert c.get("/health/live").json() == {"status": "ok", "service": "kontrol-central-authority"}
    listo = c.get("/health/ready")
    assert listo.status_code == 200 and set(listo.json()) == {"status", "service", "database"}
    for texto in (c.get("/health/live").text, listo.text):
        assert not any(t in texto for t in MATERIAL) and "sqlite" not in texto and "version" not in texto
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404
    assert c.post("/v1/license/sync", json={}).status_code in (404, 405)  # el sync NO está expuesto
    database.get_engine.cache_clear()


def test_cla_16_la_cli_registra_emite_y_consulta_sin_imprimir_la_clave(factoria, ajustes, propietario, monkeypatch, tmp_path, capsys):
    from central_authority import cli as cli_mod
    monkeypatch.setattr(cli_mod, "get_settings", lambda: ajustes)
    monkeypatch.setattr(cli_mod, "get_session_factory", lambda: factoria)
    clave_inst = tmp_path / "instalacion.pem"
    clave_inst.write_text(pem_publica(Ed25519PrivateKey.generate()))
    assert cli_mod.main(["register-installation", "--operator", "ana", "--installation-id", INSTALACION, "--public-key-file", str(clave_inst),
                         "--customer-id", "CUS-1", "--contract-id", "CON-1", "--company-tax-id", "J-1"]) == 0
    assert cli_mod.main(["issue-license", "--operator", "ana", "--installation-id", INSTALACION, "--anio", "2027",
                         "--entitlements", '{"companies": 3}']) == 0
    salida = capsys.readouterr().out
    emitido = json.loads(salida.strip().split("\n}\n")[-1] + ("}" if not salida.strip().endswith("}") else ""))
    assert emitido["revision"] == 1 and emitido["payload"]["revision"] == 1
    assert contract.verify_license_signature(emitido["payload"], emitido["signature_hex"], pem_publica(propietario))
    assert cli_mod.main(["reissue-license", "--operator", "luis", "--installation-id", INSTALACION, "--anio", "2027"]) == 0
    assert cli_mod.main(["list-issuances", "--operator", "ana", "--installation-id", INSTALACION]) == 0
    assert cli_mod.main(["show-issuance", "--operator", "ana", "--license-id", emitido["license_id"]]) == 0
    todo = salida + capsys.readouterr().out
    assert "BEGIN PRIVATE KEY" not in todo and pem_privada(propietario).splitlines()[1] not in todo
    assert cli_mod.main(["issue-license", "--operator", "ana", "--installation-id", "KTL-XX-NO", "--anio", "2027"]) == 2
    assert json.loads(capsys.readouterr().err.strip())["error"] == "INSTALLATION_NOT_FOUND"
    assert cli_mod.main(["issue-license", "--operator", "ana", "--installation-id", INSTALACION, "--entitlements", "{}"]) == 2  # sin período
    assert json.loads(capsys.readouterr().err.strip())["error"] == "INVALID_PERIOD"


def test_cla_17_los_registros_no_llevan_material(factoria, ajustes, propietario, caplog):
    with caplog.at_level(logging.DEBUG), factoria() as db:
        _registrar(db)
        r = _emite(db, ajustes)
    texto = "\n".join(x.getMessage() for x in caplog.records)
    assert r["license_id"] in texto and "revision 1" in texto
    assert not any(t in texto for t in MATERIAL) and r["signature_hex"] not in texto and pem_privada(propietario).splitlines()[1] not in texto


def test_cla_18_el_despliegue_es_independiente_del_cliente():
    raiz = pathlib.Path(__file__).resolve().parents[4]
    compose_cliente = (raiz / "compose.yaml").read_text()
    assert "central" not in compose_cliente.lower()
    compose_central = (raiz / "compose.central.yaml").read_text()
    assert "KONTROL_CENTRAL_SIGNING_PRIVATE_KEY_PEM" in compose_central and "KONTROL_DB_URL" not in compose_central
    assert "kontrol-net" not in compose_central.replace("kontrol-central-net", "")
    dockerfile = (raiz / "Dockerfile.central").read_text()
    assert "COPY resources/backend/app ./app" not in dockerfile and "license_contract.py" in dockerfile
    assert "central_authority/alembic.ini" in (raiz / "resources/backend/central_authority/entrypoint.sh").read_text()
    assert "kontrol_central" in compose_central and "@central-db" in compose_central
