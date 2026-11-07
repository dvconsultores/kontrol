"""Manejadores del planificador para la copia de respaldo, retención y evaluación del RPO."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import uuid
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.modules.organization.models import Installation, Tenant
from app.modules.scheduler.service import Contexto, Resultado
from app.modules.system.models import BackupRun, BackupSettings
from app.ops.backup_pg import BackupError
from app.ops.backup_rpo import (
    ESTADOS_VALIDOS,
    Copia,
    Politica,
    codigo_saneado,
    errores_de_politica,
    etiqueta_valida,
    evaluar,
    franja,
    seleccionar_purga,
)
from app.shared.audit import record_audit

BLOQUEO_COPIA = 0x4B4F4E5442434B50  # «KONTBCKP». Distinto del del tick.
MARCADOR_DESTINO = ".kontrol-destination"
SISTEMAS_DE_RED = frozenset({"nfs", "nfs4", "cifs", "smb3", "smbfs", "fuse.sshfs", "glusterfs", "ceph"})
PATRON_PAQUETE = "kontrol-backup-{}.kbk"


def _utc(valor: datetime) -> datetime:
    """Devuelve el datetime convertido a UTC."""
    if valor.tzinfo is None:
        return valor.replace(tzinfo=UTC)
    return valor


def politica_de(cfg: BackupSettings | None) -> Politica:
    """Construye la política de copias a partir de la configuración."""
    if cfg is None:
        return Politica(None, None, None, None, None, None, None, False)
    return Politica(
        cfg.configured_rpo_minutes,
        cfg.schedule_interval_minutes,
        cfg.safety_margin_minutes,
        cfg.retention_days,
        cfg.retention_min_copies,
        cfg.destination_type,
        cfg.destination_label,
        bool(cfg.scheduler_enabled),
    )


def copia_de(run: BackupRun) -> Copia:
    """Convierte una fila de BackupRun en una Copia."""
    return Copia(
        run.backup_id,
        run.origin,
        run.status,
        run.transfer_state,
        _utc(run.started_at),
        _utc(run.snapshot_at) if run.snapshot_at is not None else None,
        run.duration_seconds,
        run.package_size,
        bool(run.durable_off_host),
        bool(run.retention_hold),
    )


def cargar_copias(db: Session) -> list[BackupRun]:
    """Carga las copias válidas y las más recientes no válidas."""
    validas = list(db.scalars(select(BackupRun).where(BackupRun.status.in_(ESTADOS_VALIDOS))).all())
    otras = list(
        db.scalars(
            select(BackupRun)
            .where(BackupRun.status.not_in(ESTADOS_VALIDOS), BackupRun.status != "PURGED")
            .order_by(BackupRun.started_at.desc())
            .limit(50)
        ).all()
    )
    vistos: set[object] = set()
    resultado: list[BackupRun] = []
    for fila in validas + otras:
        if fila.id not in vistos:
            vistos.add(fila.id)
            resultado.append(fila)
    return resultado


def tomar_bloqueo(conexion: Connection) -> bool:
    """Adquiere el bloqueo de copia en PostgreSQL."""
    if conexion.dialect.name != "postgresql":
        return True
    return bool(conexion.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": BLOQUEO_COPIA}).scalar())


def soltar_bloqueo(conexion: Connection) -> None:
    """Libera el bloqueo de copia en PostgreSQL."""
    if conexion.dialect.name == "postgresql":
        conexion.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": BLOQUEO_COPIA})


def recuperar_huerfanas(db: Session, ahora: datetime) -> int:
    """Marca como abandonadas las copias que quedaron RUNNING."""
    huerfanas = list(db.scalars(select(BackupRun).where(BackupRun.status == "RUNNING")).all())
    for fila in huerfanas:
        fila.status = "ABANDONED"
        fila.completed_at = ahora
        fila.error_code = "BACKUP_ABANDONED"
        _auditar(
            db,
            "INSTALLATION_BACKUP_FAILED",
            {"backup_id": fila.backup_id or "", "error_code": "BACKUP_ABANDONED", "origin": fila.origin},
        )
    return len(huerfanas)


def iniciar_registro(
    session_factory: sessionmaker, origen: str, slot: str | None, ahora: datetime, correlacion: str
) -> str | None:
    """Crea una nueva fila de BackupRun y devuelve el id del registro."""
    db = session_factory()
    try:
        registro = BackupRun(
            origin=origen,
            slot=slot,
            status="RUNNING",
            create_state="PENDING",
            verify_state="PENDING",
            transfer_state="PENDING" if origen == "SCHEDULED" else "NOT_APPLICABLE",
            retention_state="PENDING" if origen == "SCHEDULED" else "NOT_APPLICABLE",
            started_at=ahora,
            correlation_id=correlacion,
        )
        db.add(registro)
        db.commit()
        return str(registro.id)
    except IntegrityError:
        db.rollback()
        return None
    finally:
        db.close()


@dataclass(frozen=True)
class DestinoEstado:
    disponible: bool
    fuera_del_anfitrion: bool
    codigo: str | None


def leer_mountinfo() -> str:
    """Lee la información de montajes del sistema."""
    try:
        return Path("/proc/self/mountinfo").read_text()
    except OSError:
        return ""


def tipo_de_montaje(ruta: Path, mountinfo: str) -> str | None:
    """Determina el tipo de sistema de archivos de una ruta."""
    resuelta = ruta.resolve()
    mejor: tuple[int, str | None] = (0, None)
    for linea in mountinfo.splitlines():
        try:
            partes = linea.split(" - ", 1)
            if len(partes) != 2:
                continue
            campos = partes[0].split()
            if len(campos) < 5:
                continue
            punto = Path(campos[4])
            tipo = partes[1].split()[0]
        except (IndexError, ValueError):
            continue
        try:
            punto_resuelto = punto.resolve()
        except OSError:
            continue
        if punto_resuelto == resuelta or punto_resuelto in resuelta.parents:
            largo = len(str(punto_resuelto))
            if largo > mejor[0]:
                mejor = (largo, tipo)
    return mejor[1]


def evaluar_destino(
    raiz: Path, etiqueta: str, instalacion: str, otros: Iterable[Path]
) -> DestinoEstado:
    """Evalúa la disponibilidad y aislamiento de un destino de copias."""
    if not etiqueta_valida(etiqueta):
        return DestinoEstado(False, False, "DESTINATION_LABEL_INVALID")
    raiz_resuelta = raiz.resolve()
    ruta = raiz / etiqueta
    try:
        ruta_resuelta = ruta.resolve()
    except OSError:
        return DestinoEstado(False, False, "DESTINATION_UNAVAILABLE")
    if raiz_resuelta not in ruta_resuelta.parents and ruta_resuelta != raiz_resuelta:
        return DestinoEstado(False, False, "DESTINATION_OUTSIDE_ROOT")
    try:
        if not ruta.is_dir():
            return DestinoEstado(False, False, "DESTINATION_UNAVAILABLE")
        marcador = ruta / MARCADOR_DESTINO
        if not marcador.exists():
            if any(ruta.iterdir()):
                return DestinoEstado(False, False, "DESTINATION_NOT_INITIALIZED")
            marcador.write_text(instalacion)
        elif marcador.read_text() != instalacion:
            return DestinoEstado(False, False, "DESTINATION_FOREIGN")
        sonda = ruta / ".kontrol-probe"
        with sonda.open("w") as f:
            f.write(instalacion)
            f.flush()
            os.fsync(f.fileno())
        sonda.unlink()
    except OSError:
        return DestinoEstado(False, False, "DESTINATION_UNAVAILABLE")
    try:
        stat_destino = ruta.stat()
        for otro in otros:
            try:
                if stat_destino.st_dev == otro.resolve().stat().st_dev:
                    return DestinoEstado(True, False, "OFF_HOST_UNPROVEN")
            except OSError:
                continue
        if tipo_de_montaje(ruta, leer_mountinfo()) in SISTEMAS_DE_RED:
            return DestinoEstado(True, True, None)
        return DestinoEstado(True, False, "OFF_HOST_UNPROVEN")
    except OSError:
        return DestinoEstado(False, False, "DESTINATION_UNAVAILABLE")


def transferir(paquete: Path, destino: Path, sha256: str) -> None:
    """Transfiere y verifica el paquete al destino."""
    parcial = destino / (paquete.name + ".part")
    final = destino / paquete.name
    try:
        with paquete.open("rb") as origen:
            with parcial.open("wb") as salida:
                while True:
                    bloque = origen.read(1024 * 1024)
                    if not bloque:
                        break
                    salida.write(bloque)
                salida.flush()
                os.fsync(salida.fileno())
        digesto = hashlib.sha256()
        with parcial.open("rb") as f:
            while True:
                bloque = f.read(1024 * 1024)
                if not bloque:
                    break
                digesto.update(bloque)
        if digesto.hexdigest() != sha256:
            parcial.unlink(missing_ok=True)
            raise BackupError("TRANSFER_HASH_MISMATCH", "El hash del paquete transferido no coincide")
        os.replace(parcial, final)
        descriptor = os.open(destino, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        parcial.unlink(missing_ok=True)
        raise BackupError("TRANSFER_FAILED", "No se pudo transferir el paquete") from exc


def _ejecutar_cli(argumentos: list[str], tiempo: int) -> tuple[int, dict[str, object]]:
    """Ejecuta el CLI de backup y devuelve código y datos JSON."""
    try:
        proceso = subprocess.run(
            [sys.executable, "-m", "app.ops.backup", *argumentos],
            capture_output=True,
            text=True,
            timeout=tiempo,
        )
    except subprocess.TimeoutExpired:
        return 124, {"code": "BACKUP_TIMEOUT"}
    for linea in reversed(proceso.stdout.splitlines()):
        linea = linea.strip()
        if linea.startswith("{"):
            try:
                return proceso.returncode, json.loads(linea)
            except json.JSONDecodeError:
                break
    return proceso.returncode, {}


def _auditar(db: Session, accion: str, despues: dict[str, object]) -> None:
    """Registra una auditoría para la instalación actual."""
    instalacion = db.scalar(select(Installation).order_by(Installation.created_at, Installation.id))
    if instalacion is None:
        return
    tenants = list(db.scalars(select(Tenant).where(Tenant.installation_id == instalacion.id)).all())
    for tenant in tenants:
        record_audit(
            db,
            action=accion,
            entity_type="Installation",
            entity_id=str(instalacion.id),
            tenant_id=str(tenant.id),
            company_id=None,
            source="SCHEDULER",
            after=despues,
        )


def _fallar(db: Session, fila: BackupRun, codigo: str | None) -> bool:
    """Marca la fila como fallida, audita el fallo y devuelve False."""
    fila.status = "FAILED"
    fila.error_code = codigo_saneado(codigo)
    fila.completed_at = datetime.now(UTC)
    _auditar(
        db,
        "INSTALLATION_BACKUP_FAILED",
        {"backup_id": fila.backup_id or "", "error_code": fila.error_code, "origin": fila.origin},
    )
    db.commit()
    return False


def _copia_programada(contexto: Contexto, run_id: str, p: Politica) -> bool:
    """Ejecuta una copia programada completa y devuelve True si fue exitosa."""
    inicio = monotonic()
    db = contexto.session_factory()
    try:
        ajustes = get_settings()
        staging = Path(ajustes.backup_path)
        rpo = p.rpo_minutos
        intervalo = p.intervalo_minutos
        margen = p.margen_minutos
        if rpo is None or intervalo is None or margen is None:
            return False
        tiempo = max(60, (rpo - intervalo - margen) * 60)
        if not os.environ.get("KONTROL_BACKUP_KEY"):
            fila = db.get(BackupRun, run_id)
            if fila is None:
                return False
            return _fallar(db, fila, "BACKUP_KEY_MISSING")
        fila = db.get(BackupRun, run_id)
        if fila is None:
            return False
        fila.create_state = "STARTED"
        db.commit()
        rc, datos = _ejecutar_cli(["create", "--dest", str(staging), "--no-audit", "--no-ledger"], tiempo)
        if rc != 0 or datos.get("status") != "OK":
            fila.create_state = "FAILED"
            db.commit()
            return _fallar(db, fila, str(datos.get("code") or "BACKUP_FAILED"))
        backup_id = datos.get("backup_id")
        snapshot_texto = datos.get("snapshot_at_utc")
        if not isinstance(backup_id, str) or not backup_id or not isinstance(snapshot_texto, str):
            fila.create_state = "FAILED"
            db.commit()
            return _fallar(db, fila, "BACKUP_FAILED")
        try:
            snapshot = datetime.fromisoformat(snapshot_texto)
        except ValueError:
            fila.create_state = "FAILED"
            db.commit()
            return _fallar(db, fila, "BACKUP_FAILED")
        paquete = staging / PATRON_PAQUETE.format(backup_id)
        try:
            digesto = hashlib.sha256()
            tamano = 0
            with paquete.open("rb") as f:
                while True:
                    bloque = f.read(1024 * 1024)
                    if not bloque:
                        break
                    digesto.update(bloque)
                    tamano += len(bloque)
            sha256 = digesto.hexdigest()
        except OSError:
            fila.create_state = "FAILED"
            db.commit()
            return _fallar(db, fila, "BACKUP_FAILED")
        fila.backup_id = backup_id
        fila.snapshot_at = snapshot
        fila.package_size = tamano
        fila.sha256 = sha256
        fila.create_state = "COMPLETED"
        db.commit()
        fila.verify_state = "STARTED"
        db.commit()
        rc, datos = _ejecutar_cli(["verify", str(paquete), "--no-audit", "--no-ledger"], tiempo)
        if rc != 0 or datos.get("status") != "OK":
            fila.verify_state = "FAILED"
            paquete.unlink(missing_ok=True)
            db.commit()
            return _fallar(db, fila, str(datos.get("code") or "BACKUP_FAILED"))
        fila.verify_state = "SUCCEEDED"
        fila.status = "VERIFIED_LOCAL"
        db.commit()
        instalacion_uuid = ""
        instalacion = db.scalar(select(Installation).order_by(Installation.created_at, Installation.id))
        if instalacion is not None:
            instalacion_uuid = instalacion.installation_uuid or ""
        etiqueta = p.destino_etiqueta or ""
        destino = evaluar_destino(
            Path(ajustes.backup_destinations_path),
            etiqueta,
            instalacion_uuid,
            (staging, Path(ajustes.storage_path)),
        )
        if not destino.disponible:
            codigo = codigo_saneado(destino.codigo)
            fila.transfer_state = "FAILED"
            fila.error_code = codigo
            fila.completed_at = datetime.now(UTC)
            fila.duration_seconds = int(monotonic() - inicio)
            db.commit()
            anterior = db.scalar(
                select(BackupRun)
                .where(BackupRun.id != fila.id, BackupRun.status != "PURGED")
                .order_by(BackupRun.started_at.desc())
            )
            if anterior is None or anterior.error_code != codigo:
                _auditar(
                    db,
                    "INSTALLATION_BACKUP_DESTINATION_UNAVAILABLE",
                    {"destination_label": etiqueta, "error_code": codigo},
                )
                db.commit()
            return False
        try:
            transferir(paquete, Path(ajustes.backup_destinations_path) / etiqueta, fila.sha256 or "")
        except BackupError as exc:
            fila.transfer_state = "FAILED"
            fila.error_code = codigo_saneado(exc.code)
            fila.completed_at = datetime.now(UTC)
            fila.duration_seconds = int(monotonic() - inicio)
            _auditar(
                db,
                "INSTALLATION_BACKUP_FAILED",
                {"backup_id": backup_id, "error_code": fila.error_code, "origin": "SCHEDULED"},
            )
            db.commit()
            return False
        fin = datetime.now(UTC)
        fila.transfer_state = "COMPLETED"
        fila.destination_label = etiqueta
        fila.durable_off_host = destino.fuera_del_anfitrion
        fila.status = "VERIFIED_DURABLE" if destino.fuera_del_anfitrion else "VERIFIED_DESTINATION"
        paquete.unlink(missing_ok=True)
        fila.completed_at = fin
        fila.duration_seconds = int(monotonic() - inicio)
        objetos = datos.get("objects")
        _auditar(db, "INSTALLATION_BACKUP_VERIFIED", {"backup_id": backup_id, "objects": int(objetos) if isinstance(objetos, int) else 0})
        db.commit()
        return True
    finally:
        db.close()


def ejecutar_copia(contexto: Contexto) -> Resultado:
    """Planifica y ejecuta una copia programada."""
    db = contexto.session_factory()
    try:
        cfg = db.scalar(select(BackupSettings))
        p = politica_de(cfg)
        if cfg is None or not p.habilitada or errores_de_politica(p):
            return Resultado()
        clave, _ = franja(contexto.now, p.intervalo_minutos or 1)
        res = Resultado(seen=1)
        if db.scalar(select(BackupRun).where(BackupRun.slot == clave)) is not None:
            res.skipped = 1
            return res
    finally:
        db.close()
    motor = contexto.session_factory.kw["bind"]
    with motor.connect() as conexion:
        adquirido = tomar_bloqueo(conexion)
        conexion.commit()
        if not adquirido:
            return Resultado(seen=1, skipped=1)
        try:
            db = contexto.session_factory()
            try:
                recuperar_huerfanas(db, contexto.now)
                db.commit()
                run_id = iniciar_registro(contexto.session_factory, "SCHEDULED", clave, contexto.now, contexto.correlation_id)
                if run_id is None:
                    return Resultado(seen=1, skipped=1)
                ok = _copia_programada(contexto, run_id, p)
                return Resultado(seen=1, processed=1 if ok else 0, failed=0 if ok else 1)
            finally:
                db.close()
        finally:
            soltar_bloqueo(conexion)
            conexion.commit()


def aplicar_retencion(contexto: Contexto) -> Resultado:
    """Aplica la política de retención purgando copias seleccionadas."""
    db = contexto.session_factory()
    try:
        cfg = db.scalar(select(BackupSettings))
        p = politica_de(cfg)
        if cfg is None or not p.habilitada or errores_de_politica(p):
            return Resultado()
    finally:
        db.close()
    motor = contexto.session_factory.kw["bind"]
    with motor.connect() as conexion:
        adquirido = tomar_bloqueo(conexion)
        conexion.commit()
        if not adquirido:
            return Resultado(seen=1, skipped=1)
        try:
            db = contexto.session_factory()
            try:
                filas = cargar_copias(db)
                seleccionadas = seleccionar_purga(
                    contexto.now, p, [copia_de(r) for r in filas]
                )
                res = Resultado(seen=1)
                ajustes = get_settings()
                raiz = Path(ajustes.backup_destinations_path)
                staging = Path(ajustes.backup_path)
                for copia in seleccionadas:
                    if copia.backup_id is None:
                        continue
                    fila = next((r for r in filas if r.backup_id == copia.backup_id), None)
                    if fila is None:
                        continue
                    nombre = PATRON_PAQUETE.format(copia.backup_id)
                    try:
                        (staging / nombre).unlink(missing_ok=True)
                        if fila.destination_label is not None:
                            (raiz / fila.destination_label / nombre).unlink(missing_ok=True)
                    except OSError:
                        fila.retention_state = "DEGRADED"
                        db.commit()
                        res.failed += 1
                        continue
                    fila.status = "PURGED"
                    fila.retention_state = "COMPLETED"
                    _auditar(db, "INSTALLATION_BACKUP_PURGED", {"backup_id": copia.backup_id})
                    db.commit()
                    res.processed += 1
                return res
            finally:
                db.close()
        finally:
            soltar_bloqueo(conexion)
            conexion.commit()


def evaluar_rpo(contexto: Contexto) -> Resultado:
    """Evalúa el estado del RPO y registra cambios."""
    db = contexto.session_factory()
    try:
        cfg = db.scalar(select(BackupSettings))
        if cfg is None:
            return Resultado()
        filas = cargar_copias(db)
        degradada = any(r.retention_state == "DEGRADED" for r in filas)
        estado = evaluar(
            contexto.now,
            politica_de(cfg),
            [copia_de(r) for r in filas],
            retencion_degradada=degradada,
        ).estado
        if estado != cfg.last_rpo_state:
            _auditar(
                db,
                "INSTALLATION_RPO_STATE_CHANGED",
                {"from_state": cfg.last_rpo_state or "", "to_state": estado},
            )
            cfg.last_rpo_state = estado
            db.commit()
            return Resultado(seen=1, processed=1)
        return Resultado(seen=1)
    finally:
        db.close()


def estado_de_copias(db: Session, ahora: datetime) -> dict[str, object]:
    """Devuelve un resumen del estado actual de las copias."""
    cfg = db.scalar(select(BackupSettings))
    filas = cargar_copias(db)
    copias = [copia_de(r) for r in filas]
    p = politica_de(cfg)
    evaluacion = evaluar(ahora, p, copias, retencion_degradada=any(r.retention_state == "DEGRADED" for r in filas))
    ultima_valida = evaluacion.ultima_valida
    ultima_en_destino = evaluacion.ultima_en_destino
    ultima_fuera = evaluacion.ultima_fuera_del_anfitrion
    referencia = ultima_en_destino or ultima_valida
    ultima_exitosa = None
    for r in filas:
        if r.create_state == "COMPLETED" and r.snapshot_at is not None:
            instante = _utc(r.snapshot_at)
            if ultima_exitosa is None or instante > ultima_exitosa:
                ultima_exitosa = instante
    reciente = None
    for r in filas:
        if r.status != "PURGED":
            if reciente is None or _utc(r.started_at) > _utc(reciente.started_at):
                reciente = r
    next_schedule = None
    if p.habilitada and not errores_de_politica(p):
        _, siguiente = franja(ahora, p.intervalo_minutos or 1)
        next_schedule = siguiente.isoformat()
    return {
        "configured_rpo_minutes": cfg.configured_rpo_minutes if cfg is not None else None,
        "schedule_interval_minutes": cfg.schedule_interval_minutes if cfg is not None else None,
        "safety_margin_minutes": cfg.safety_margin_minutes if cfg is not None else None,
        "retention_days": cfg.retention_days if cfg is not None else None,
        "retention_min_copies": cfg.retention_min_copies if cfg is not None else None,
        "destination_type": cfg.destination_type if cfg is not None else None,
        "destination_label": cfg.destination_label if cfg is not None else None,
        "scheduler_enabled": bool(cfg.scheduler_enabled) if cfg is not None else False,
        "version": cfg.version if cfg is not None else 0,
        "rpo_state": evaluacion.estado,
        "last_successful_backup_at": ultima_exitosa.isoformat() if ultima_exitosa else None,
        "last_valid_backup_at": ultima_valida.instantanea.isoformat() if ultima_valida and ultima_valida.instantanea else None,
        "last_valid_durable_off_host_backup_at": ultima_fuera.instantanea.isoformat() if ultima_fuera and ultima_fuera.instantanea else None,
        "backup_age_seconds": evaluacion.edad_segundos if evaluacion.edad_segundos is not None else None,
        "backup_duration_seconds": referencia.duracion_segundos if referencia else None,
        "package_size_bytes": referencia.tamano if referencia else None,
        "next_schedule_at": next_schedule,
        "last_sanitized_error": codigo_saneado(reciente.error_code) if reciente and reciente.error_code else None,
        "retention_degraded": any(r.retention_state == "DEGRADED" for r in filas),
        "running": any(r.status == "RUNNING" for r in filas),
    }


class RegistroManual:
    """Registro de una copia creada manualmente con la CLI."""

    def __init__(self, session_factory: sessionmaker, run_id: str) -> None:
        self.session_factory = session_factory
        self.run_id = run_id
        self.terminada = False

    def creada(self, backup_id: str, snapshot_at_utc: str, ruta: Path, duracion: float) -> None:
        """Marca la copia como creada y pendiente de verificación."""
        with self.session_factory() as db:
            fila = db.get(BackupRun, self.run_id)
            if fila is None:
                return
            fila.backup_id = backup_id
            fila.snapshot_at = datetime.fromisoformat(snapshot_at_utc)
            fila.package_size = ruta.stat().st_size
            fila.duration_seconds = int(duracion)
            fila.create_state = "COMPLETED"
            fila.status = "CREATED"
            fila.completed_at = datetime.now(UTC)
            db.commit()
            self.terminada = True


@contextmanager
def copia_manual(db_url: str) -> Iterator[RegistroManual]:
    """Contexto para crear una copia manual registrada en el ledger."""
    motor = create_engine(db_url)
    try:
        factory = sessionmaker(bind=motor, expire_on_commit=False)
        with motor.connect() as conexion:
            adquirido = tomar_bloqueo(conexion)
            conexion.commit()
            if not adquirido:
                raise BackupError("BACKUP_ALREADY_RUNNING", "Ya hay una copia en curso")
            try:
                ahora = datetime.now(UTC)
                with factory() as db:
                    recuperar_huerfanas(db, ahora)
                    db.commit()
                run_id = iniciar_registro(factory, "MANUAL", None, ahora, str(uuid.uuid4()))
                if run_id is None:
                    raise BackupError("BACKUP_ALREADY_RUNNING", "Ya hay una copia en curso")
                with factory() as db:
                    fila = db.get(BackupRun, run_id)
                    if fila is not None:
                        fila.create_state = "STARTED"
                        db.commit()
                registro = RegistroManual(factory, run_id)
                try:
                    yield registro
                finally:
                    if not registro.terminada:
                        with factory() as db:
                            fila = db.get(BackupRun, run_id)
                            if fila is not None:
                                fila.create_state = "FAILED"
                                fila.status = "FAILED"
                                fila.error_code = "BACKUP_FAILED"
                                fila.completed_at = datetime.now(UTC)
                                db.commit()
            finally:
                soltar_bloqueo(conexion)
                conexion.commit()
    finally:
        motor.dispose()


def registrar_verificacion(db_url: str, backup_id: str, correcta: bool, codigo: str | None) -> bool:
    """Registra el resultado de la verificación de una copia en el ledger."""
    motor = create_engine(db_url)
    try:
        factory = sessionmaker(bind=motor)
        with factory() as db:
            fila = db.scalar(select(BackupRun).where(BackupRun.backup_id == backup_id))
            if fila is None:
                return False
            if correcta:
                fila.verify_state = "SUCCEEDED"
                if fila.status == "CREATED":
                    fila.status = "VERIFIED_LOCAL"
            else:
                fila.verify_state = "FAILED"
                fila.error_code = codigo_saneado(codigo)
                if fila.status == "CREATED" or fila.status in ESTADOS_VALIDOS:
                    fila.status = "FAILED"
            db.commit()
            return True
    except SQLAlchemyError:
        return False
    finally:
        motor.dispose()


def retener_copia(db_url: str, backup_id: str, valor: bool) -> bool:
    """Alterna la retención de una copia en el ledger."""
    motor = create_engine(db_url)
    try:
        factory = sessionmaker(bind=motor)
        with factory() as db:
            fila = db.scalar(select(BackupRun).where(BackupRun.backup_id == backup_id))
            if fila is None:
                return False
            fila.retention_hold = valor
            db.commit()
            return True
    except SQLAlchemyError:
        return False
    finally:
        motor.dispose()


def identificador_de_paquete(ruta: Path) -> str:
    """Extrae el identificador de un paquete de copia."""
    nombre = ruta.stem
    prefijo = "kontrol-backup-"
    if nombre.startswith(prefijo):
        return nombre[len(prefijo) :]
    return nombre
