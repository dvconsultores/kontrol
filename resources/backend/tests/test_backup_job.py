from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
from backup_job_apoyo import (
    AHORA,
    CREATE_FAILED,
    STATUS_ABANDONED,
    STATUS_FAILED,
    STATUS_RUNNING,
    STATUS_VERIFIED_DESTINATION,
    STATUS_VERIFIED_DURABLE,
    STATUS_VERIFIED_LOCAL,
    TRANSFER_FAILED,
    VERIFY_FAILED,
    VERIFY_STARTED,
    VERIFY_SUCCEEDED,
    acciones,
    cli_correcta,
    configurar,
    contexto,
    crear_mundo,
    fila,
    fila_copia,
    preparar_entorno,
    unica,
)

from app.modules.audit.models import AuditEvent
from app.modules.system.models import BackupRun
from app.ops import backup_job
from app.ops.backup_pg import BackupError


@pytest.fixture
def factory(tmp_path):
    return crear_mundo(tmp_path)


@pytest.fixture
def entorno(monkeypatch, tmp_path):
    return preparar_entorno(monkeypatch, tmp_path)


def test_sin_configuracion_no_hace_nada(factory):
    resultado = backup_job.ejecutar_copia(contexto(factory))
    assert resultado.seen == 0
    assert resultado.processed == 0
    assert resultado.skipped == 0
    assert resultado.failed == 0


def test_deshabilitada_no_llama_a_la_cli(factory, entorno, monkeypatch):
    configurar(factory, scheduler_enabled=False)
    llamado: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, llamado))
    backup_job.ejecutar_copia(contexto(factory))
    assert llamado == []


def test_configuracion_incorrecta_no_llama_a_la_cli(factory, entorno, monkeypatch):
    configurar(factory, configured_rpo_minutes=None)
    llamado: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, llamado))
    backup_job.ejecutar_copia(contexto(factory))
    assert llamado == []


def test_copia_correcta_deja_verified_destination(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, ordenes))
    resultado = backup_job.ejecutar_copia(contexto(factory))
    assert resultado.processed == 1
    registro = fila(factory, "b1")
    assert registro is not None
    assert registro.status == STATUS_VERIFIED_DESTINATION
    assert registro.verify_state == VERIFY_SUCCEEDED
    assert (entorno.destinos / "nas-1" / "kontrol-backup-b1.kbk").exists()
    assert not (entorno.staging / "kontrol-backup-b1.kbk").exists()
    assert acciones(factory).count("INSTALLATION_BACKUP_VERIFIED") == 2


def test_durable_fuera_del_anfitrion(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, ordenes))
    monkeypatch.setattr(
        backup_job,
        "evaluar_destino",
        lambda *a: SimpleNamespace(disponible=True, fuera_del_anfitrion=True, codigo=None),
    )
    backup_job.ejecutar_copia(contexto(factory))
    registro = unica(factory)
    assert registro.status == STATUS_VERIFIED_DURABLE
    assert registro.durable_off_host is True


def test_verificado_no_antes_de_verify(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []

    def doble(argumentos, tiempo):
        ordenes.append(argumentos)
        if argumentos[0] == "create":
            (entorno.staging / "kontrol-backup-b1.kbk").write_bytes(b"contenido")
            return (0, {"status": "OK", "backup_id": "b1", "snapshot_at_utc": AHORA.isoformat()})
        if argumentos[0] == "verify":
            registro = unica(factory)
            assert registro.status == STATUS_RUNNING
            assert registro.verify_state == VERIFY_STARTED
            assert "INSTALLATION_BACKUP_VERIFIED" not in acciones(factory)
            return (0, {"status": "OK", "objects": 3})
        raise AssertionError(f"argumentos inesperado: {argumentos}")

    monkeypatch.setattr(backup_job, "_ejecutar_cli", doble)
    backup_job.ejecutar_copia(contexto(factory))
    assert ordenes[-1][0] == "verify"


def test_verify_fallido(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []

    def doble(argumentos, tiempo):
        ordenes.append(argumentos)
        if argumentos[0] == "create":
            (entorno.staging / "kontrol-backup-b1.kbk").write_bytes(b"contenido")
            return (0, {"status": "OK", "backup_id": "b1", "snapshot_at_utc": AHORA.isoformat()})
        if argumentos[0] == "verify":
            return (1, {"status": "ERROR"})
        raise AssertionError(f"argumentos inesperado: {argumentos}")

    monkeypatch.setattr(backup_job, "_ejecutar_cli", doble)
    backup_job.ejecutar_copia(contexto(factory))
    registro = unica(factory)
    assert registro.status == STATUS_FAILED
    assert registro.verify_state == VERIFY_FAILED
    assert not (entorno.staging / "kontrol-backup-b1.kbk").exists()
    assert "INSTALLATION_BACKUP_VERIFIED" not in acciones(factory)
    assert "INSTALLATION_BACKUP_FAILED" in acciones(factory)


def test_create_fallido_sanea_codigo(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []
    monkeypatch.setattr(
        backup_job,
        "_ejecutar_cli",
        lambda argumentos, tiempo: (ordenes.append(argumentos) or (1, {"code": "error en /data/x"})),
    )
    backup_job.ejecutar_copia(contexto(factory))
    registro = unica(factory)
    assert registro.error_code == "BACKUP_FAILED"
    assert registro.create_state == CREATE_FAILED


def test_backup_id_ausente_falla_y_no_valida(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []
    monkeypatch.setattr(
        backup_job,
        "_ejecutar_cli",
        lambda argumentos, tiempo: (ordenes.append(argumentos) or (0, {"status": "OK"})),
    )
    backup_job.ejecutar_copia(contexto(factory))
    registro = unica(factory)
    assert registro.status == STATUS_FAILED
    assert registro.create_state == CREATE_FAILED


def test_clave_ausente(factory, entorno, monkeypatch):
    configurar(factory)
    monkeypatch.delenv("KONTROL_BACKUP_KEY")
    llamado: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, llamado))
    backup_job.ejecutar_copia(contexto(factory))
    assert llamado == []
    registro = unica(factory)
    assert registro.error_code == "BACKUP_KEY_MISSING"


def test_segunda_pasada_misma_franja(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, ordenes))
    resultado1 = backup_job.ejecutar_copia(contexto(factory))
    assert resultado1.processed == 1
    resultado2 = backup_job.ejecutar_copia(contexto(factory))
    assert resultado2.skipped == 1
    assert len(ordenes) == 2


def test_franja_siguiente_crea_otra_fila(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, ordenes))
    backup_job.ejecutar_copia(contexto(factory))
    backup_job.ejecutar_copia(contexto(factory, AHORA + timedelta(minutes=5)))
    assert len(ordenes) == 4
    with factory() as session:
        assert session.query(BackupRun).count() == 2


def test_bloqueo_no_adquirido(factory, entorno, monkeypatch):
    configurar(factory)
    llamado: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, llamado))
    monkeypatch.setattr(backup_job, "tomar_bloqueo", lambda *a, **k: False)
    resultado = backup_job.ejecutar_copia(contexto(factory))
    assert resultado.skipped == 1
    assert llamado == []


def test_huerfana_pasa_a_abandoned(factory, entorno, monkeypatch):
    configurar(factory)
    with factory() as session:
        session.add(fila_copia(status=STATUS_RUNNING, slot="viejo", backup_id=None))
        session.commit()
    llamado: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, llamado))
    backup_job.ejecutar_copia(contexto(factory))
    with factory() as session:
        registros = session.query(BackupRun).all()
    assert any(registro.status == STATUS_ABANDONED for registro in registros)
    assert any(registro.error_code == "BACKUP_ABANDONED" for registro in registros)
    assert acciones(factory).count("INSTALLATION_BACKUP_FAILED") == 2


def test_destino_inexistente(factory, entorno, monkeypatch):
    configurar(factory)
    (entorno.destinos / "nas-1").rmdir()
    ordenes: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, ordenes))
    resultado1 = backup_job.ejecutar_copia(contexto(factory))
    assert resultado1.failed == 1
    resultado2 = backup_job.ejecutar_copia(contexto(factory, AHORA + timedelta(minutes=5)))
    assert resultado2.failed == 1
    registro = fila(factory, "b1")
    assert registro is not None
    assert registro.transfer_state == TRANSFER_FAILED
    assert registro.status == STATUS_VERIFIED_LOCAL
    assert (entorno.staging / "kontrol-backup-b1.kbk").exists()
    assert acciones(factory).count("INSTALLATION_BACKUP_DESTINATION_UNAVAILABLE") == 2


def test_fallo_de_transferencia_conserva_copia_local(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, ordenes))
    monkeypatch.setattr(
        backup_job,
        "transferir",
        lambda *a, **k: (_ for _ in ()).throw(BackupError("TRANSFER_FAILED", "x")),
    )
    backup_job.ejecutar_copia(contexto(factory))
    registro = unica(factory)
    assert registro.status == STATUS_VERIFIED_LOCAL
    assert registro.transfer_state == TRANSFER_FAILED
    assert (entorno.staging / "kontrol-backup-b1.kbk").exists()
    assert "INSTALLATION_BACKUP_FAILED" in acciones(factory)


def test_duracion_no_depende_del_reloj_logico(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, ordenes))
    futuro = AHORA + timedelta(days=3650)
    resultado = backup_job.ejecutar_copia(contexto(factory, futuro))
    assert resultado.processed == 1
    assert fila(factory, "b1").duration_seconds >= 0


def test_clave_no_aparece_en_ledger_ni_auditoria(factory, entorno, monkeypatch):
    configurar(factory)
    ordenes: list = []
    monkeypatch.setattr(backup_job, "_ejecutar_cli", cli_correcta(entorno.staging, ordenes))
    backup_job.ejecutar_copia(contexto(factory))
    clave = entorno.clave
    with factory() as session:
        filas = session.query(BackupRun).all()
        for registro in filas:
            assert clave not in repr([getattr(registro, columna.name) for columna in BackupRun.__table__.columns])
        eventos = session.query(AuditEvent).all()
        for evento in eventos:
            assert clave not in repr(evento.after)
