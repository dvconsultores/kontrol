"""Funciones puras de soporte para copias de seguridad de PostgreSQL.

Este módulo no accede a red ni escribe en disco. Expone utilidades para
localizar las herramientas nativas de PostgreSQL, validar su versión y
calcular huellas de tablas dentro de una transacción de solo lectura.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import psycopg2.extensions
import psycopg2.sql
from sqlalchemy.engine import make_url


class BackupError(Exception):
    """Error de copia de seguridad con código estable de máquina."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def libpq_env(db_url: str) -> dict[str, str]:
    """Devuelve variables de entorno libpq a partir de una URL SQLAlchemy.

    Nunca se construye una URL con contraseña para argumentos ni se incluye la
    URL original en el resultado.
    """
    url = make_url(db_url)
    env: dict[str, str] = {
        "PGHOST": url.host or "",
        "PGPORT": str(url.port or 5432),
        "PGUSER": url.username or "",
        "PGDATABASE": url.database or "",
    }
    if url.password:
        env["PGPASSWORD"] = url.password
    return env


def pg_connect_kwargs(db_url: str) -> dict[str, str]:
    """Argumentos de `psycopg2.connect` desde una URL SQLAlchemy.

    No construye una DSN con contraseña.
    """
    url = make_url(db_url)
    kwargs: dict[str, str] = {
        "host": url.host or "",
        "port": str(url.port or 5432),
        "user": url.username or "",
        "dbname": url.database or "",
    }
    if url.password:
        kwargs["password"] = url.password
    return kwargs


def pg_tool(name: str, pg_bin_dir: str | None) -> str:
    """Localiza una herramienta PostgreSQL.

    `name` debe ser ``"pg_dump"`` o ``"pg_restore"``. Si se indica
    ``pg_bin_dir``, el ejecutable debe existir y ser ejecutable. En caso
    contrario se busca en el ``PATH``.
    """
    if name not in {"pg_dump", "pg_restore"}:
        raise BackupError("PG_TOOLS_MISSING", f"Herramienta no admitida: {name}")

    if pg_bin_dir:
        candidate = Path(pg_bin_dir) / name
        if not candidate.is_file() or not os.access(candidate, os.X_OK):
            raise BackupError(
                "PG_TOOLS_MISSING",
                f"No se encontró {name} ejecutable en {pg_bin_dir}",
            )
        return str(candidate)

    found = shutil.which(name)
    if not found:
        raise BackupError(
            "PG_TOOLS_MISSING",
            f"No se encontró {name} en el PATH",
        )
    return found


def tool_major(path: str) -> int:
    """Devuelve el primer número mayor de la salida de ``--version``."""
    result = subprocess.run(
        [path, "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"(\d+)(?:\.\d+)?", result.stdout)
    if not match:
        raise BackupError(
            "PG_TOOLS_INCOMPATIBLE",
            f"No se pudo determinar la versión de {path}",
        )
    return int(match.group(1))


def check_tool_compatible(path: str, server_version_num: int) -> None:
    """Comprueba que la herramienta no sea anterior al servidor."""
    if tool_major(path) < server_version_num // 10000:
        raise BackupError(
            "PG_TOOLS_INCOMPATIBLE",
            "La herramienta PostgreSQL es anterior al servidor",
        )


SESSION_SETTINGS = (
    "SET LOCAL TIME ZONE 'UTC'",
    "SET LOCAL DateStyle = 'ISO, YMD'",
    "SET LOCAL extra_float_digits = 3",
    "SET LOCAL bytea_output = 'hex'",
    "SET LOCAL IntervalStyle = 'iso_8601'",
)


def table_fingerprints(
    cur: psycopg2.extensions.cursor,
) -> dict[str, dict[str, object]]:
    """Calcula número de filas y digest MD5 de las tablas públicas.

    La conexión debe estar dentro de una transacción repetible de solo
    lectura para que las huellas correspondan a la misma instantánea.
    """
    for setting in SESSION_SETTINGS:
        cur.execute(setting)

    cur.execute(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
    )
    tablenames = [row[0] for row in cur.fetchall()]

    fingerprints: dict[str, dict[str, object]] = {}
    for tablename in tablenames:
        identifier = psycopg2.sql.Identifier(tablename)
        query = psycopg2.sql.SQL(
            "SELECT count(*), "
            "md5(coalesce(string_agg(md5(t::text), '' ORDER BY md5(t::text)), '')) "
            "FROM public.{} t"
        ).format(identifier)
        cur.execute(query)
        row = cur.fetchone()
        if row is None:
            raise BackupError(
                "BACKUP_INCONSISTENT",
                f"No se pudo calcular la huella de {tablename}",
            )
        rows, digest = row
        fingerprints[tablename] = {"rows": int(rows), "digest": digest}

    return fingerprints


def audit_triggers(cur: psycopg2.extensions.cursor) -> list[str]:
    """Devuelve los nombres ordenados de triggers no internos sobre audit_events."""
    cur.execute(
        """
        SELECT tgname
        FROM pg_trigger
        WHERE tgrelid = 'audit_events'::regclass
          AND NOT tgisinternal
        ORDER BY tgname
        """
    )
    return [row[0] for row in cur.fetchall()]


def server_version_num(cur: psycopg2.extensions.cursor) -> int:
    """Devuelve ``SHOW server_version_num`` como entero."""
    cur.execute("SHOW server_version_num")
    row = cur.fetchone()
    if row is None:
        raise BackupError("PG_TOOLS_INCOMPATIBLE", "No se pudo leer la versión del servidor")
    return int(row[0])
