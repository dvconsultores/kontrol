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

from sqlalchemy.exc import IntegrityError

#: SQLSTATE de PostgreSQL para `unique_violation`.
_VIOLACION_UNICA = "23505"


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
