"""Nombres de las bases efímeras del E2E (FR-054-E2EDB-002, 003).

Cada corrida E2E certificable tiene su base PostgreSQL, llamada
``kontrol_e2e_test_<run>``. El nombre lleva los marcadores ``e2e`` y ``test``
y solo lo que cumple el patrón entero se reconoce como base E2E. Este módulo es
puro: no toca la base, el entorno ni el reloj.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

PREFIJO = "kontrol_e2e_test_"
PREFIJO_DE_MARCA = "kontrol-e2e "
PREFIJO_DE_APLICACION = "kontrol-e2e:"
PATRON_DE_RUN = re.compile(r"r[0-9]{8}t[0-9]{6}p[0-9]{1,7}n[0-9a-f]{6}")
PATRON_DE_BASE = re.compile(r"kontrol_e2e_test_(r[0-9]{8}t[0-9]{6}p[0-9]{1,7}n[0-9a-f]{6})")
PATRON_DE_MAQUINA = re.compile(r"[A-Za-z0-9._-]{1,64}")
PATRON_DE_MARCA = re.compile(
    r"kontrol-e2e run=(?P<run>r[0-9]{8}t[0-9]{6}p[0-9]{1,7}n[0-9a-f]{6}) "
    r"pid=(?P<pid>[0-9]{1,7}) maquina=(?P<maquina>[A-Za-z0-9._-]{1,64}) "
    r"creado=(?P<creado>[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\+00:00)"
)


def _exigir_run(run_id: object) -> str:
    """Valida que `run_id` sea un str que cumple entero PATRON_DE_RUN."""
    if not isinstance(run_id, str) or PATRON_DE_RUN.fullmatch(run_id) is None:
        raise ValueError(f"run_id inválido: {run_id!r}")
    return run_id


def _exigir_pid(pid: object) -> int:
    """Valida que `pid` sea un int (no bool) entre 1 y 9_999_999."""
    if isinstance(pid, bool) or not isinstance(pid, int) or not 1 <= pid <= 9_999_999:
        raise ValueError(f"pid inválido: {pid!r}")
    return pid


def _exigir_fecha(ahora: object, nombre: str) -> datetime:
    """Valida que `ahora` sea un datetime con zona horaria."""
    if not isinstance(ahora, datetime) or ahora.tzinfo is None or ahora.utcoffset() is None:
        raise ValueError(f"{nombre} inválido: {ahora!r}")
    return ahora


def nuevo_run_id(ahora: datetime, pid: int, nonce: str) -> str:
    """Construye un run_id rYYYYMMDDtHHMMSSpPPPPPnNNNNNN a partir de UTC."""
    utc = _exigir_fecha(ahora, "ahora").astimezone(UTC)
    _exigir_pid(pid)
    if not isinstance(nonce, str) or re.fullmatch(r"[0-9a-f]{6}", nonce) is None:
        raise ValueError(f"nonce inválido: {nonce!r}")
    return f"r{utc:%Y%m%d}t{utc:%H%M%S}p{pid}n{nonce}"


def nombre_de_base(run_id: str) -> str:
    """Devuelve el nombre de la base efímera para `run_id`."""
    return PREFIJO + _exigir_run(run_id)


def run_de_base(nombre: object) -> str | None:
    """Devuelve el run_id de una base E2E, o None si no la reconoce."""
    if not isinstance(nombre, str):
        return None
    coincidencia = PATRON_DE_BASE.fullmatch(nombre)
    if coincidencia is None:
        return None
    return coincidencia.group(1)


def es_base_e2e(nombre: object) -> bool:
    """Indica si `nombre` es una base E2E reconocible."""
    return run_de_base(nombre) is not None


def aplicacion(run_id: str) -> str:
    """Devuelve el nombre de aplicación PostgreSQL para `run_id`."""
    return PREFIJO_DE_APLICACION + _exigir_run(run_id)


def marca(run_id: str, pid: int, maquina: str, creado: datetime) -> str:
    """Construye la marca textual de una corrida E2E."""
    run_validado = _exigir_run(run_id)
    pid_validado = _exigir_pid(pid)
    if not isinstance(maquina, str) or PATRON_DE_MAQUINA.fullmatch(maquina) is None:
        raise ValueError(f"maquina inválida: {maquina!r}")
    iso = _exigir_fecha(creado, "creado").astimezone(UTC).isoformat(timespec="seconds")
    return (
        f"{PREFIJO_DE_MARCA}run={run_validado} pid={pid_validado} "
        f"maquina={maquina} creado={iso}"
    )


def leer_marca(texto: object) -> dict[str, str] | None:
    """Extrae los campos de una marca E2E, o None si no encaja entera."""
    if not isinstance(texto, str):
        return None
    coincidencia = PATRON_DE_MARCA.fullmatch(texto)
    if coincidencia is None:
        return None
    return dict(coincidencia.groupdict())
