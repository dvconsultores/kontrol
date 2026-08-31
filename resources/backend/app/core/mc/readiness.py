"""Preparación para las restricciones finales (ARCH-MC-001, apoyo a N4 y N7).

Responde, sin escribir nada, a la pregunta que decide si N7 podrá ejecutarse:
¿cuántas filas impedirían hoy poner la clave foránea, el `NOT NULL` o el único?

Descubrirlo en N7 sería tarde: la migración habría avanzado sobre una premisa
falsa.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Connection


def fk_bloqueantes(cx: Connection, tabla: str) -> int:
    """Filas cuyo `company_id` no existe hoy en `companies`."""
    return cx.execute(text(
        f"SELECT count(*) FROM {tabla} t "
        "WHERE t.company_id IS NOT NULL "
        "  AND NOT EXISTS (SELECT 1 FROM companies c WHERE c.id = t.company_id)"
    )).scalar_one()


def not_null_bloqueantes(cx: Connection, tabla: str) -> int:
    """Filas que quedarían nulas: hoy no tienen valor alguno."""
    return cx.execute(text(
        f"SELECT count(*) FROM {tabla} WHERE company_id IS NULL")).scalar_one()


def colisiones_unicas(cx: Connection, tabla: str, columnas: list[str]) -> int:
    """Choques que aparecerían al estrechar un único de tenant a empresa.

    El único se evalúa **como quedará**: sobre la empresa reconstruida. Aquí se
    mide el peor caso —todas las filas del mismo tenant colapsando en una sola
    empresa—, que es lo que ocurriría si el backfill fuera determinista.
    """
    cols = ", ".join(columnas)
    return cx.execute(text(
        f"SELECT coalesce(sum(n - 1), 0) FROM ("
        f"  SELECT count(*) AS n FROM {tabla} GROUP BY {cols} HAVING count(*) > 1"
        f") x")).scalar_one()


def secuencias(cx: Connection) -> list[dict]:
    """Secuencias de PostgreSQL y la tabla a la que sirven."""
    filas = cx.execute(text(
        "SELECT sequence_name FROM information_schema.sequences "
        "WHERE sequence_schema = current_schema()")).all()
    return [{"secuencia": r[0]} for r in filas]
