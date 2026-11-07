"""Apoyo de las pruebas de copia programada. Pytest no lo recoge."""
from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, init_models
from app.modules.audit.models import AuditEvent
from app.modules.organization.models import Installation, Tenant
from app.modules.scheduler.service import Contexto
from app.modules.system.models import BackupRun, BackupSettings
from app.ops import backup_job
from app.ops.backup_rpo import TIPO_DESTINO_MONTADO

AHORA = datetime(2026, 11, 7, 12, 0, tzinfo=UTC)
ORIGIN_SCHEDULED = "SCHEDULED"
STATUS_RUNNING = "RUNNING"
STATUS_VERIFIED_DESTINATION = "VERIFIED_DESTINATION"
STATUS_VERIFIED_DURABLE = "VERIFIED_DURABLE"
STATUS_VERIFIED_LOCAL = "VERIFIED_LOCAL"
STATUS_FAILED = "FAILED"
STATUS_ABANDONED = "ABANDONED"
CREATE_COMPLETED = "COMPLETED"
CREATE_FAILED = "FAILED"
VERIFY_STARTED = "STARTED"
VERIFY_SUCCEEDED = "SUCCEEDED"
VERIFY_FAILED = "FAILED"
TRANSFER_COMPLETED = "COMPLETED"
TRANSFER_FAILED = "FAILED"
RETENTION_PENDING = "PENDING"


def crear_mundo(tmp_path: Path) -> sessionmaker:
    init_models()
    motor = create_engine(f"sqlite:///{tmp_path / 't.db'}")
    Base.metadata.create_all(motor)
    fabrica = sessionmaker(bind=motor, expire_on_commit=False)
    with fabrica() as session:
        instalacion = Installation(installation_uuid="inst-1")
        session.add(instalacion)
        session.flush()
        session.add_all(
            [
                Tenant(installation_id=instalacion.id, code="tenant-a", name="Tenant A"),
                Tenant(installation_id=instalacion.id, code="tenant-b", name="Tenant B"),
            ]
        )
        session.commit()
    return fabrica


def preparar_entorno(monkeypatch, tmp_path: Path) -> SimpleNamespace:
    staging = tmp_path / "staging"
    destinos = tmp_path / "destinos"
    storage = tmp_path / "storage"
    staging.mkdir()
    (destinos / "nas-1").mkdir(parents=True)
    storage.mkdir()
    clave = secrets.token_hex(16)
    monkeypatch.setenv("KONTROL_BACKUP_KEY", clave)
    monkeypatch.setattr(
        backup_job,
        "get_settings",
        lambda: SimpleNamespace(
            backup_path=staging,
            backup_destinations_path=destinos,
            storage_path=storage,
        ),
    )
    return SimpleNamespace(staging=staging, destinos=destinos, clave=clave)


def configurar(factory: sessionmaker, **cambios) -> BackupSettings:
    valores = {
        "configured_rpo_minutes": 15,
        "schedule_interval_minutes": 5,
        "safety_margin_minutes": 2,
        "retention_days": 7,
        "retention_min_copies": 1,
        "destination_type": TIPO_DESTINO_MONTADO,
        "destination_label": "nas-1",
        "scheduler_enabled": True,
    }
    valores.update(cambios)
    registro = BackupSettings(**valores)
    with factory() as session:
        session.add(registro)
        session.commit()
        session.refresh(registro)
    return registro


def contexto(factory: sessionmaker, ahora: datetime = AHORA) -> Contexto:
    return Contexto(session_factory=factory, now=ahora, correlation_id="c")


def acciones(factory: sessionmaker) -> list[str]:
    with factory() as session:
        return [evento.action for evento in session.query(AuditEvent).all()]


def fila(factory: sessionmaker, backup_id: str) -> BackupRun | None:
    with factory() as session:
        return session.query(BackupRun).filter_by(backup_id=backup_id).one_or_none()


def unica(factory: sessionmaker) -> BackupRun:
    with factory() as session:
        return session.query(BackupRun).one()


def fila_copia(**cambios) -> BackupRun:
    valores = {
        "origin": ORIGIN_SCHEDULED,
        "status": STATUS_VERIFIED_DESTINATION,
        "create_state": CREATE_COMPLETED,
        "verify_state": VERIFY_SUCCEEDED,
        "transfer_state": TRANSFER_COMPLETED,
        "retention_state": RETENTION_PENDING,
        "started_at": AHORA,
        "snapshot_at": AHORA,
        "destination_label": "nas-1",
    }
    valores.update(cambios)
    return BackupRun(**valores)


def cli_correcta(
    staging: Path,
    ordenes: list,
    ids: tuple[str, str] = ("b1", "b2"),
) -> Callable:
    iterador = iter(ids)

    def doble(argumentos, tiempo):
        ordenes.append(argumentos)
        if argumentos[0] == "create":
            backup_id = next(iterador)
            (staging / f"kontrol-backup-{backup_id}.kbk").write_bytes(b"contenido")
            return (0, {"status": "OK", "backup_id": backup_id, "snapshot_at_utc": AHORA.isoformat()})
        if argumentos[0] == "verify":
            return (0, {"status": "OK", "objects": 3})
        raise AssertionError(f"argumentos inesperado: {argumentos}")

    return doble
