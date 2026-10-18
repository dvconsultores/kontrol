"""Distinguir una colisión de unicidad de cualquier otro error de integridad.

Capturar `IntegrityError` a secas para traducirlo a un conflicto de dominio
mezcla cosas distintas: una fila repetida, un `CHECK` incumplido o una clave
foránea rota llegan todas como `IntegrityError`. Si se traducen igual, una tasa
cero rechazada por la base se contesta como «ya existe», y el error real queda
escondido detrás de un mensaje plausible.

Encontrado al revalidar las mutaciones de la Spec 013 contra el código final:
con la validación del servicio retirada, la base rechazaba la tasa cero y el
servicio respondía `DUPLICATE_OBSERVATION`.
"""

from __future__ import annotations

import sqlite3

from sqlalchemy import Table, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import FromClause

#: SQLSTATE de PostgreSQL para `unique_violation`.
_VIOLACION_UNICA = "23505"

#: Código extendido de SQLite para `SQLITE_CONSTRAINT_UNIQUE`.
_SQLITE_VIOLACION_UNICA = 2067


def es_violacion_unica(error: IntegrityError, restriccion: str) -> bool:
    """`True` solo si el error es la violación única de **esa** restricción.

    PostgreSQL informa el nombre de la restricción o del índice único en
    `diag.constraint_name`. Cualquier otro caso —otra restricción, un `CHECK`,
    una clave foránea, u otro motor que no aporte diagnóstico— devuelve `False`,
    y quien captura debe volver a lanzar el error original.
    """
    origen = getattr(error, "orig", None)
    if getattr(origen, "pgcode", None) != _VIOLACION_UNICA:
        return False
    return getattr(getattr(origen, "diag", None), "constraint_name", None) == restriccion


def restriccion_unica(tabla: FromClause, nombre: str) -> UniqueConstraint:
    """Resuelve la restricción única `nombre` declarada en `tabla`.

    Se resuelve al importar, de modo que un nombre equivocado falla al arrancar
    y no en la primera colisión.
    """
    if not isinstance(tabla, Table):
        raise TypeError(f"{tabla!r} no es una Table")
    for restriccion in tabla.constraints:
        if isinstance(restriccion, UniqueConstraint) and restriccion.name == nombre:
            return restriccion
    raise LookupError(f"{tabla.name} no declara la restricción única {nombre}")


def es_violacion_unica_de(error: IntegrityError, restriccion: UniqueConstraint) -> bool:
    """`True` solo si el error es la violación única de **esa** restricción.

    SQLite no informa el nombre de la restricción; su señal es el código
    extendido y la lista de columnas con el formato fijo de SQLite, que se
    deriva de las columnas declaradas. Cualquier otro caso → False y quien
    captura relanza.
    """
    if es_violacion_unica(error, str(restriccion.name)):
        return True
    origen = getattr(error, "orig", None)
    if not isinstance(origen, sqlite3.IntegrityError):
        return False
    if getattr(origen, "sqlite_errorcode", None) != _SQLITE_VIOLACION_UNICA:
        return False
    tabla = restriccion.table.name
    columnas = ", ".join(f"{tabla}.{c.name}" for c in restriccion.columns)
    return str(origen) == f"UNIQUE constraint failed: {columnas}"
