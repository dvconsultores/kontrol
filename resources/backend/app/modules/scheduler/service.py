"""Tick del planificador de plataforma (Spec 047 · ADR-D0-015).

# Spec 047 · Planificador de plataforma

El temporizador del sistema decide **cuándo**; este tick decide **qué**
(R-D0-15-2). No hay cola, worker, hilo ni bucle de espera (R-D0-15-3): el tick
corre una vez y termina.

Un solo tick a la vez por instalación (R-D0-15-4): un bloqueo consultivo de
PostgreSQL tomado en una **conexión dedicada** y mantenido todo el tick. Si el
proceso muere, PostgreSQL lo libera al cerrarse la conexión.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.core.logging import get_logger
from app.modules.scheduler.models import POLITICAS_RECUPERACION, SchedulerHandlerRun, SchedulerRun

log = get_logger("kontrol.spec047.scheduler")

#: «KONTROLG». Distinto del de la instalación de la Spec 004.
BLOQUEO_TICK = 0x4B4F4E54524F4C47

SALIDA_OK = 0
SALIDA_FALLO = 1
SALIDA_CON_ERRORES = 2


@dataclass
class Resultado:
    seen: int = 0
    processed: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass(frozen=True)
class Contexto:
    session_factory: sessionmaker
    now: datetime
    correlation_id: str


@dataclass(frozen=True)
class Manejador:
    code: str
    owner_spec: str
    enabled: bool
    catch_up: str
    execute: Callable[[Contexto], Resultado]


@dataclass
class ResultadoTick:
    status: str
    correlation_id: str
    exit_code: int
    handlers: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"status": self.status, "correlation_id": self.correlation_id,
                "exit_code": self.exit_code, "handlers": self.handlers}


def _reloj() -> datetime:
    return datetime.now(UTC)


def _con_zona(momento: datetime) -> datetime:
    if momento.tzinfo is None or momento.utcoffset() is None:
        raise ValueError("NAIVE_DATETIME")
    return momento


def _tomar_bloqueo(conexion) -> bool:
    if conexion.dialect.name != "postgresql":
        return True
    return bool(conexion.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": BLOQUEO_TICK}).scalar())


def _soltar_bloqueo(conexion) -> None:
    if conexion.dialect.name == "postgresql":
        conexion.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": BLOQUEO_TICK})


def validar_registro(manejadores: Sequence[Manejador]) -> None:
    codigos = [m.code for m in manejadores]
    if len(codigos) != len(set(codigos)):
        raise ValueError("DUPLICATE_HANDLER_CODE")
    for m in manejadores:
        if not m.owner_spec or m.catch_up not in POLITICAS_RECUPERACION:
            raise ValueError(f"INVALID_HANDLER:{m.code}")


def tick(session_factory: sessionmaker, *, now: datetime | None = None,
         manejadores: Sequence[Manejador] | None = None) -> ResultadoTick:
    """Ejecuta un tick completo y deja su registro. Nunca lanza por un manejador."""
    ahora = _con_zona(now) if now is not None else _reloj()
    if manejadores is None:
        from app.modules.scheduler.registry import manejadores as registrados

        manejadores = registrados()
    validar_registro(manejadores)
    correlacion = str(uuid.uuid4())
    motor = session_factory.kw["bind"]

    with motor.connect() as conexion:
        adquirido = _tomar_bloqueo(conexion)
        conexion.commit()
        try:
            with session_factory() as db:
                run = SchedulerRun(correlation_id=correlacion, scheduled_for=ahora, started_at=_reloj(),
                                   status="STARTED" if adquirido else "SKIPPED_OVERLAP")
                if not adquirido:
                    run.finished_at = _reloj()
                db.add(run)
                db.commit()
                run_id = str(run.id)
            if not adquirido:
                log.info("spec047.tick_skipped_overlap", extra={"correlation_id": correlacion})
                return ResultadoTick("SKIPPED_OVERLAP", correlacion, SALIDA_OK)
            return _ejecutar(session_factory, run_id, correlacion, ahora, manejadores)
        finally:
            if adquirido:
                _soltar_bloqueo(conexion)
                conexion.commit()


def _ejecutar(session_factory: sessionmaker, run_id: str, correlacion: str, ahora: datetime,
              manejadores: Sequence[Manejador]) -> ResultadoTick:
    total = Resultado()
    errores = 0
    detalle: list[dict] = []
    try:
        for m in manejadores:
            inicio = _reloj()
            if not m.enabled:
                estado, res, codigo = "DISABLED", Resultado(), None
            else:
                try:
                    res = m.execute(Contexto(session_factory=session_factory, now=ahora,
                                             correlation_id=correlacion))
                    estado, codigo = "COMPLETED", None
                except Exception as error:
                    res, estado, codigo = Resultado(), "FAILED", type(error).__name__[:64]
                    log.warning("spec047.handler_failed", extra={"handler": m.code, "error_code": codigo})
            if estado == "FAILED" or res.failed:
                errores += 1
            for campo in ("seen", "processed", "skipped", "failed"):
                setattr(total, campo, getattr(total, campo) + getattr(res, campo))
            with session_factory() as db:
                db.add(SchedulerHandlerRun(
                    run_id=run_id, handler_code=m.code, owner_spec=m.owner_spec, catch_up=m.catch_up,
                    status=estado, started_at=inicio, finished_at=_reloj(), items_seen=res.seen,
                    items_processed=res.processed, items_skipped=res.skipped, items_failed=res.failed,
                    error_code=codigo))
                db.commit()
            detalle.append({"handler": m.code, "owner_spec": m.owner_spec, "status": estado,
                            "seen": res.seen, "processed": res.processed, "skipped": res.skipped,
                            "failed": res.failed, "error_code": codigo})
        estado_tick = "COMPLETED_WITH_ERRORS" if errores else "COMPLETED"
        salida = SALIDA_CON_ERRORES if errores else SALIDA_OK
        codigo_tick = None
    except Exception as error:  # fallo operacional del propio tick, no de un manejador
        estado_tick, salida, codigo_tick = "FAILED", SALIDA_FALLO, type(error).__name__[:64]
    with session_factory() as db:
        run = db.get(SchedulerRun, run_id)
        run.status = estado_tick
        run.finished_at = _reloj()
        run.items_seen, run.items_processed = total.seen, total.processed
        run.items_skipped, run.items_failed = total.skipped, total.failed
        run.error_code = codigo_tick
        db.commit()
    log.info("spec047.tick_finished", extra={"correlation_id": correlacion, "status": estado_tick})
    return ResultadoTick(estado_tick, correlacion, salida, detalle)
