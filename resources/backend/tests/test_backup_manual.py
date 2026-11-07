"""Pruebas del registro manual de copias en el ledger."""

from pathlib import Path

import pytest
from backup_job_apoyo import AHORA, crear_mundo, fila_copia, unica

from app.ops import backup_create, backup_job
from app.ops.backup_job import (
    BackupError,
    copia_de,
    copia_manual,
    identificador_de_paquete,
    registrar_verificacion,
    retener_copia,
)
from app.ops.backup_rpo import ESTADOS_VALIDOS, TIPO_DESTINO_MONTADO, Politica, evaluar


@pytest.fixture
def factory(tmp_path):
    """Crea una base SQLite con las tablas del sistema."""
    return crear_mundo(tmp_path)


def test_copia_manual_deja_created_no_valida(factory, tmp_path):
    url = str(factory.kw["bind"].url)
    fichero = tmp_path / "x.kbk"
    fichero.write_bytes(b"1234")

    with copia_manual(url) as r:
        r.creada("m1", AHORA.isoformat(), fichero, 2.0)

    fila = unica(factory)
    assert fila.status == "CREATED"
    assert fila.create_state == "COMPLETED"
    assert fila.origin == "MANUAL"
    assert fila.package_size == 4
    assert "CREATED" not in ESTADOS_VALIDOS
    politica = Politica(15, 5, 2, 7, 1, TIPO_DESTINO_MONTADO, "nas-1", True)
    assert evaluar(AHORA, politica, [copia_de(fila)]).estado == "NO_VALID_BACKUP"


def test_excepcion_en_copia_manual_deja_fallida(factory):
    url = str(factory.kw["bind"].url)

    with pytest.raises(RuntimeError):
        with copia_manual(url):
            raise RuntimeError("fallo")

    fila = unica(factory)
    assert fila.status == "FAILED"
    assert fila.create_state == "FAILED"
    assert fila.error_code == "BACKUP_FAILED"


def test_bloqueo_ocupado_rechaza_copia_manual(factory, monkeypatch):
    url = str(factory.kw["bind"].url)
    monkeypatch.setattr(backup_job, "tomar_bloqueo", lambda conexion: False)

    with pytest.raises(BackupError) as exc:
        with copia_manual(url):
            pass

    assert exc.value.code == "BACKUP_ALREADY_RUNNING"
    with factory() as db:
        assert db.query(backup_job.BackupRun).count() == 0


def test_programada_activa_bloquea_la_manual(factory, monkeypatch):
    url = str(factory.kw["bind"].url)
    monkeypatch.setattr(backup_job, "iniciar_registro", lambda *a: None)

    with pytest.raises(BackupError) as exc:
        with copia_manual(url):
            pass

    assert exc.value.code == "BACKUP_ALREADY_RUNNING"


def test_verificacion_correcta_valida(factory, tmp_path):
    url = str(factory.kw["bind"].url)
    fichero = tmp_path / "x.kbk"
    fichero.write_bytes(b"1234")

    with copia_manual(url) as r:
        r.creada("m1", AHORA.isoformat(), fichero, 2.0)

    assert registrar_verificacion(url, "m1", True, None)
    fila = unica(factory)
    assert fila.status == "VERIFIED_LOCAL"
    assert fila.verify_state == "SUCCEEDED"


def test_verificacion_fallida_no_valida(factory, tmp_path):
    url = str(factory.kw["bind"].url)
    fichero = tmp_path / "x.kbk"
    fichero.write_bytes(b"1234")

    with copia_manual(url) as r:
        r.creada("m1", AHORA.isoformat(), fichero, 2.0)

    assert registrar_verificacion(url, "m1", False, "CODIGO")
    fila = unica(factory)
    assert fila.status == "FAILED"
    assert fila.verify_state == "FAILED"
    assert fila.error_code == "CODIGO"


def test_verificacion_fallida_invalida_copia_ya_validada(factory):
    url = str(factory.kw["bind"].url)
    with factory() as db:
        fila = fila_copia(backup_id="d1", status="VERIFIED_DURABLE")
        db.add(fila)
        db.commit()

    assert registrar_verificacion(url, "d1", False, "X")
    with factory() as db:
        fila = db.query(backup_job.BackupRun).one()
        assert fila.status == "FAILED"


def test_verificacion_de_copia_desconocida(factory):
    url = str(factory.kw["bind"].url)
    assert not registrar_verificacion(url, "no-existe", True, None)


def test_retener_y_soltar(factory):
    url = str(factory.kw["bind"].url)
    with factory() as db:
        fila = fila_copia(backup_id="r1")
        db.add(fila)
        db.commit()

    assert retener_copia(url, "r1", True)
    with factory() as db:
        assert db.query(backup_job.BackupRun).one().retention_hold is True

    assert retener_copia(url, "r1", False)
    with factory() as db:
        assert db.query(backup_job.BackupRun).one().retention_hold is False


def test_identificador_de_paquete():
    assert identificador_de_paquete(Path("/x/kontrol-backup-abc.kbk")) == "abc"
    assert identificador_de_paquete(Path("/x/abc.kbk")) == "abc"


def test_clave_no_llega_a_pg_dump():
    codigo = Path(backup_create.__file__).read_text()
    assert 'k != "KONTROL_BACKUP_KEY"' in codigo


def test_tick_recibe_la_clave_por_nombre():
    kontrol = Path(__file__).resolve().parents[3] / "kontrol.py"
    codigo = kontrol.read_text()
    assert '"-e", "KONTROL_BACKUP_KEY", "backend", *SCHEDULER_TICK' in codigo
    assert "KONTROL_BACKUP_KEY=" not in codigo
