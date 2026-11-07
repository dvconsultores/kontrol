"""Pruebas de integridad de los modelos de política y ledger de backups."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.database import Base
from app.modules.system.models import BackupRun, BackupSettings


@pytest.fixture()
def sesion() -> Session:
    """Sesión SQLite en memoria con solo las tablas de backup."""
    motor = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(motor, tables=[BackupSettings.__table__, BackupRun.__table__])
    return Session(motor)


def _copia(**campos: object) -> BackupRun:
    """Crea una copia con valores válidos, sobrescribibles por `campos`."""
    valores: dict[str, object] = {
        "origin": "SCHEDULED",
        "status": "VERIFIED_LOCAL",
        "create_state": "COMPLETED",
        "verify_state": "SUCCEEDED",
        "transfer_state": "NOT_APPLICABLE",
        "retention_state": "NOT_APPLICABLE",
        "started_at": datetime.now(UTC),
    }
    valores.update(campos)
    return BackupRun(**valores)


def test_rpo_de_15_minutos_se_acepta(sesion: Session) -> None:
    configuracion = BackupSettings(configured_rpo_minutes=15)
    sesion.add(configuracion)
    sesion.commit()


def test_rpo_mayor_de_15_se_rechaza(sesion: Session) -> None:
    configuracion = BackupSettings(configured_rpo_minutes=16)
    sesion.add(configuracion)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        sesion.commit()


def test_segunda_fila_de_configuracion_se_rechaza(sesion: Session) -> None:
    sesion.add(BackupSettings())
    sesion.commit()
    sesion.add(BackupSettings())
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        sesion.commit()


def test_dos_copias_en_curso_se_rechazan(sesion: Session) -> None:
    sesion.add(_copia(status="RUNNING"))
    sesion.add(_copia(status="RUNNING"))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        sesion.commit()


def test_copia_en_curso_y_terminada_conviven(sesion: Session) -> None:
    sesion.add(_copia(status="RUNNING"))
    sesion.add(_copia(status="VERIFIED_LOCAL"))
    sesion.commit()


def test_misma_franja_se_rechaza(sesion: Session) -> None:
    sesion.add(_copia(slot="s"))
    sesion.add(_copia(slot="s"))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        sesion.commit()


def test_estado_desconocido_se_rechaza(sesion: Session) -> None:
    sesion.add(_copia(status="DESCONOCIDO"))
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        sesion.commit()


def test_destino_s3_se_rechaza(sesion: Session) -> None:
    configuracion = BackupSettings(destination_type="S3")
    sesion.add(configuracion)
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        sesion.commit()
