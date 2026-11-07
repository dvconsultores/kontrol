from __future__ import annotations

import subprocess
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest
from backup_job_apoyo import (
    AHORA,
    acciones,
    configurar,
    contexto,
    crear_mundo,
    fila,
    fila_copia,
    preparar_entorno,
)

from app.modules.scheduler.registry import manejadores
from app.ops import backup_job
from app.ops.backup_pg import BackupError
from app.ops.backup_rpo import TIPO_DESTINO_MONTADO, Copia, Politica, evaluar

HACE_30 = AHORA - timedelta(days=30)


@pytest.fixture
def factory(tmp_path: Path):
    return crear_mundo(tmp_path)


@pytest.fixture
def entorno(monkeypatch, tmp_path: Path):
    return preparar_entorno(monkeypatch, tmp_path)


def _paquete(directorio: Path, nombre: str) -> Path:
    ruta = directorio / f"kontrol-backup-{nombre}.kbk"
    ruta.write_bytes(ruta.name.encode("utf-8"))
    return ruta


def _guardar(factory, **campos: object) -> None:
    """Persiste una copia de prueba."""
    with factory() as db:
        db.add(fila_copia(**campos))
        db.commit()


def test_etiqueta_invalida(factory, entorno):
    raiz = entorno.destinos

    resultado = backup_job.evaluar_destino(raiz, "..", "inst-1", [])

    assert resultado.codigo == "DESTINATION_LABEL_INVALID"


def test_enlace_simbolico_fuera_de_la_raiz(factory, entorno, tmp_path):
    raiz = entorno.destinos
    (raiz / "nas-1").rmdir()
    fuera = tmp_path / "fuera"
    fuera.mkdir()
    (raiz / "nas-1").symlink_to(fuera)

    resultado = backup_job.evaluar_destino(raiz, "nas-1", "inst-1", [])

    assert resultado.codigo == "DESTINATION_OUTSIDE_ROOT"


def test_directorio_inexistente(factory, entorno):
    raiz = entorno.destinos

    resultado = backup_job.evaluar_destino(raiz, "ausente", "inst-1", [])

    assert resultado.codigo == "DESTINATION_UNAVAILABLE"


def test_marcador_ajeno(factory, entorno):
    raiz = entorno.destinos
    destino = raiz / "nas-1"
    (destino / ".kontrol-destination").write_text("ajeno")

    resultado = backup_job.evaluar_destino(raiz, "nas-1", "inst-1", [])

    assert resultado.codigo == "DESTINATION_FOREIGN"


def test_directorio_con_contenido_sin_marcador(factory, entorno):
    raiz = entorno.destinos
    destino = raiz / "nas-1"
    (destino / "archivo.txt").write_text("contenido")

    resultado = backup_job.evaluar_destino(raiz, "nas-1", "inst-1", [])

    assert resultado.codigo == "DESTINATION_NOT_INITIALIZED"


def test_directorio_vacio_recibe_marcador(factory, entorno):
    raiz = entorno.destinos
    destino = raiz / "nas-1"

    resultado = backup_job.evaluar_destino(raiz, "nas-1", "inst-1", [])

    assert (destino / ".kontrol-destination").read_text() == "inst-1"
    assert not (destino / ".kontrol-probe").exists()
    assert resultado.codigo == "OFF_HOST_UNPROVEN"


def test_mismo_dispositivo_no_es_fuera_del_anfitrion(factory, entorno, monkeypatch):
    raiz = entorno.destinos

    resultado = backup_job.evaluar_destino(raiz, "nas-1", "inst-1", [raiz])

    assert resultado.disponible
    assert resultado.fuera_del_anfitrion is False
    assert resultado.codigo == "OFF_HOST_UNPROVEN"

    monkeypatch.setattr(backup_job, "tipo_de_montaje", lambda ruta, info: "nfs4")
    resultado = backup_job.evaluar_destino(raiz, "nas-1", "inst-1", [raiz])

    assert resultado.fuera_del_anfitrion is False
    assert resultado.codigo == "OFF_HOST_UNPROVEN"


def test_red_y_dispositivo_distinto_es_fuera(factory, entorno, monkeypatch):
    raiz = entorno.destinos

    monkeypatch.setattr(backup_job, "tipo_de_montaje", lambda ruta, info: "nfs4")
    resultado = backup_job.evaluar_destino(raiz, "nas-1", "inst-1", [])

    assert resultado.fuera_del_anfitrion is True
    assert resultado.codigo is None


def test_montaje_local_no_es_fuera(factory, entorno, monkeypatch):
    raiz = entorno.destinos

    monkeypatch.setattr(backup_job, "tipo_de_montaje", lambda ruta, info: "ext4")
    resultado = backup_job.evaluar_destino(raiz, "nas-1", "inst-1", [])

    assert resultado.fuera_del_anfitrion is False
    assert resultado.codigo == "OFF_HOST_UNPROVEN"


def test_tipo_de_montaje_respeta_componente(factory, entorno):
    info = (
        "1 1 0:1 / /mnt/a rw - ext4 /dev/a rw\n"
        "2 1 0:2 / /mnt/ab rw - nfs4 s:/x rw\n"
    )

    assert backup_job.tipo_de_montaje(Path("/mnt/a/x"), info) == "ext4"
    assert backup_job.tipo_de_montaje(Path("/mnt/ab/x"), info) == "nfs4"


def test_transferencia_correcta(factory, entorno, tmp_path):
    paquete = _paquete(tmp_path, "origen")
    destino = tmp_path / "destino"
    destino.mkdir()
    esperado = sha256(paquete.read_bytes()).hexdigest()

    backup_job.transferir(paquete, destino, esperado)

    final = destino / paquete.name
    assert final.read_bytes() == paquete.read_bytes()
    assert not list(destino.glob("*.part"))


def test_transferencia_con_hash_distinto(factory, entorno, tmp_path):
    paquete = _paquete(tmp_path, "origen")
    destino = tmp_path / "destino"
    destino.mkdir()

    with pytest.raises(BackupError) as excinfo:
        backup_job.transferir(paquete, destino, "0" * 64)

    assert excinfo.value.code == "TRANSFER_HASH_MISMATCH"
    assert not (destino / paquete.name).exists()
    assert not list(destino.glob("*.part"))


def test_cli_con_tiempo_agotado(factory, entorno, monkeypatch):
    def doble(*args, **kwargs):
        raise subprocess.TimeoutExpired("x", 1)

    monkeypatch.setattr(backup_job.subprocess, "run", doble)

    assert backup_job._ejecutar_cli(["create"], 1) == (124, {"code": "BACKUP_TIMEOUT"})


def test_retencion_purga_la_antigua(factory, entorno):
    configurar(factory)
    _guardar(
        factory,
        backup_id="vieja",
        slot="v",
        started_at=HACE_30,
        snapshot_at=HACE_30,
    )
    _guardar(factory, backup_id="nueva", slot="n")
    fichero_local = _paquete(entorno.staging, "vieja")
    fichero_destino = _paquete(entorno.destinos / "nas-1", "vieja")

    resultado = backup_job.aplicar_retencion(contexto(factory))

    assert resultado.processed == 1
    assert not fichero_local.exists()
    assert not fichero_destino.exists()
    assert fila(factory, "vieja").status == "PURGED"
    assert fila(factory, "vieja").retention_state == "COMPLETED"
    assert acciones(factory).count("INSTALLATION_BACKUP_PURGED") == 2
    assert fila(factory, "nueva").status == "VERIFIED_DESTINATION"


def test_retencion_conserva_manual(factory, entorno):
    configurar(factory)
    _guardar(
        factory,
        backup_id="vieja",
        slot="v",
        origin="MANUAL",
        started_at=HACE_30,
        snapshot_at=HACE_30,
    )
    _guardar(factory, backup_id="nueva", slot="n")
    fichero = _paquete(entorno.staging, "vieja")

    resultado = backup_job.aplicar_retencion(contexto(factory))

    assert resultado.processed == 0
    assert fichero.exists()


def test_retencion_conserva_la_ultima_valida(factory, entorno):
    configurar(factory)
    _guardar(factory, backup_id="sola", slot="s", started_at=HACE_30, snapshot_at=HACE_30)
    fichero = _paquete(entorno.staging, "sola")

    resultado = backup_job.aplicar_retencion(contexto(factory))

    assert resultado.processed == 0
    assert fichero.exists()


def test_fallo_de_borrado_deja_degradado(factory, entorno, monkeypatch):
    configurar(factory)
    _guardar(
        factory,
        backup_id="vieja",
        slot="v",
        started_at=HACE_30,
        snapshot_at=HACE_30,
    )
    _guardar(factory, backup_id="nueva", slot="n")
    _paquete(entorno.staging, "vieja")

    def doble(self, missing_ok=False):
        raise OSError("x")

    monkeypatch.setattr(Path, "unlink", doble)

    resultado = backup_job.aplicar_retencion(contexto(factory))

    assert resultado.failed == 1
    assert fila(factory, "vieja").retention_state == "DEGRADED"
    assert fila(factory, "vieja").status == "VERIFIED_DESTINATION"


def test_retencion_con_bloqueo_ocupado(factory, entorno, monkeypatch):
    configurar(factory)
    _guardar(
        factory,
        backup_id="vieja",
        slot="v",
        started_at=HACE_30,
        snapshot_at=HACE_30,
    )
    _guardar(factory, backup_id="nueva", slot="n")
    fichero = _paquete(entorno.staging, "vieja")

    monkeypatch.setattr(backup_job, "tomar_bloqueo", lambda conexion: False)

    resultado = backup_job.aplicar_retencion(contexto(factory))

    assert resultado.skipped == 1
    assert fichero.exists()
    assert fila(factory, "vieja").status == "VERIFIED_DESTINATION"


def test_evaluar_rpo_audita_solo_la_transicion(factory, entorno):
    configurar(factory)
    _guardar(factory, backup_id="b1", slot="s", snapshot_at=AHORA - timedelta(minutes=1))

    resultado = backup_job.evaluar_rpo(contexto(factory))

    assert resultado.processed == 1

    resultado = backup_job.evaluar_rpo(contexto(factory))

    assert resultado.processed == 0
    assert acciones(factory).count("INSTALLATION_RPO_STATE_CHANGED") == 2


def test_durable_sin_marca_fuera_no_certifica():
    politica = Politica(15, 5, 2, 7, 1, TIPO_DESTINO_MONTADO, "nas-1", True)
    copia = Copia(
        "b",
        "SCHEDULED",
        "VERIFIED_DURABLE",
        "COMPLETED",
        AHORA - timedelta(minutes=1),
        AHORA - timedelta(minutes=1),
        60,
        1,
        False,
        False,
    )

    resultado = evaluar(AHORA, politica, [copia])

    assert resultado.estado == "RPO_MET"


def test_estado_sin_configuracion(factory, entorno):
    with factory() as db:
        estado = backup_job.estado_de_copias(db, AHORA)

    assert estado["rpo_state"] == "DISABLED"
    assert estado["version"] == 0


def test_estado_incluye_ultima_copia_sin_configuracion(factory, entorno):
    _guardar(factory, backup_id="b1", slot="s")

    with factory() as db:
        estado = backup_job.estado_de_copias(db, AHORA)

    assert estado["rpo_state"] == "DISABLED"
    assert estado["last_valid_backup_at"] is not None


def test_estado_informa_campos(factory, entorno):
    configurar(factory)
    _guardar(
        factory,
        backup_id="b1",
        slot="s",
        snapshot_at=AHORA - timedelta(minutes=1),
        duration_seconds=60,
        package_size=10,
    )

    with factory() as db:
        estado = backup_job.estado_de_copias(db, AHORA)

    assert estado["backup_age_seconds"] == 60
    assert estado["package_size_bytes"] == 10
    assert estado["backup_duration_seconds"] == 60
    assert estado["next_schedule_at"] is not None
    assert estado["running"] is False
    assert estado["rpo_state"] == "RPO_MET"


def test_estado_no_expone_rutas_ni_hash(factory, entorno):
    configurar(factory)
    _guardar(factory, backup_id="b1", slot="s", sha256="f" * 64)

    with factory() as db:
        estado = backup_job.estado_de_copias(db, AHORA)

    assert "f" * 64 not in str(estado)
    assert str(entorno.staging) not in str(estado)


def test_registro_termina_con_las_tres_copias():
    codigos = [manejador.code for manejador in manejadores()]

    assert codigos[-3:] == [
        "installation_backup",
        "backup_retention",
        "backup_rpo_evaluation",
    ]
    for codigo in codigos[-3:]:
        manejador = next(m for m in manejadores() if m.code == codigo)
        assert manejador.owner_spec == "001"


def test_hay_un_solo_temporizador():
    raiz = Path(__file__).resolve().parents[3]
    directorio = raiz / "scripts" / "scheduler"
    timers = list(directorio.glob("*.timer"))
    services = list(directorio.glob("*.service"))

    assert len(timers) == 1
    assert len(services) == 1
