"""Spec 023 · delta dirigido — el tipo de movimiento base no se crea dos veces.

`_get_movement_type_by_code` busca el tipo y, si falta y es uno de los base, lo
crea. Buscar y crear no es atómico: en una instalación nueva, dos operaciones
simultáneas de la misma empresa pasan ambas la búsqueda y la segunda choca con
`uq_movement_types_company_code`. Nadie capturaba esa colisión, así que salía
como un **500 en plena recogida**.

Nunca se había visto porque la base de e2e llevaba meses con los tipos ya
creados. Apareció al reinstalar esa base de cero durante el ciclo de la Spec 013
—que es exactamente el primer día de un cliente real—.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import func, select

from app.modules.inventory import service as inv
from app.modules.inventory.models import MovementType
from tests.concurrency import carrera, empresa_nueva

pytest_plugins = ("tests.conftest_multicompany",)


def test_dos_operaciones_simultaneas_no_crean_dos_tipos_ni_dan_un_500(mundo):
    empresa = empresa_nueva(mundo.factory, mundo.t1, uuid4().hex[:10])

    def pedir(sesion):
        return str(inv._get_movement_type_by_code(sesion, empresa, "RECLASIFICACION").id)

    primero, segundo = carrera(mundo.factory, pedir, pedir)
    assert not isinstance(segundo, Exception), f"quien perdió la carrera recibió {segundo!r}"
    assert segundo == primero, "cada operación se quedó con un tipo distinto"

    db = mundo.factory()
    try:
        cuantos = db.execute(select(func.count()).select_from(MovementType).where(
            MovementType.company_id == empresa,
            MovementType.code == "RECLASIFICACION")).scalar()
        assert cuantos == 1
    finally:
        db.close()


def test_un_tipo_que_no_es_base_sigue_sin_inventarse(mundo):
    """La captura de la carrera no puede convertirse en crear cualquier cosa."""
    import pytest

    from app.core.errors import NotFoundError

    empresa = empresa_nueva(mundo.factory, mundo.t1, uuid4().hex[:10])
    db = mundo.factory()
    try:
        with pytest.raises(NotFoundError) as exc:
            inv._get_movement_type_by_code(db, empresa, "NO_ES_UN_TIPO_BASE")
        assert exc.value.code == "MOVEMENT_TYPE_NOT_FOUND"
    finally:
        db.close()
