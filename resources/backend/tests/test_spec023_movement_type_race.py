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

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.errors import ConflictError
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
    from app.core.errors import NotFoundError

    empresa = empresa_nueva(mundo.factory, mundo.t1, uuid4().hex[:10])
    db = mundo.factory()
    try:
        with pytest.raises(NotFoundError) as exc:
            inv._get_movement_type_by_code(db, empresa, "NO_ES_UN_TIPO_BASE")
        assert exc.value.code == "MOVEMENT_TYPE_NOT_FOUND"
    finally:
        db.close()


# --------------------------------------------------------------------------- #
# El alta explícita (`POST /inventory/movement-types`)
#
# La auto-configuración de arriba quedó protegida en su día; la ruta de alta no.
# Conservaba el mismo consultar-y-luego-insertar, así que dos altas simultáneas
# del mismo código pasaban ambas la consulta y la segunda subía como **500** en
# vez del `409 MOVEMENT_TYPE_DUPLICATE` que el camino secuencial ya contestaba.
# --------------------------------------------------------------------------- #
def _codigo(prefijo: str) -> str:
    return f"{prefijo}{uuid4().hex[:8].upper()}"


def test_el_alta_repetida_responde_conflicto_y_deja_una_sola_fila(mundo):
    """Lo que ya funcionaba tiene que seguir funcionando igual."""
    codigo = _codigo("SEQ")
    cuerpo = {"code": codigo, "name": "Secuencial", "direction": "IN"}

    primera = mundo.post("/inventory/movement-types", "ua", mundo.company_a, cuerpo)
    assert primera.status_code == 200, primera.text
    segunda = mundo.post("/inventory/movement-types", "ua", mundo.company_a, cuerpo)
    assert segunda.status_code == 409, segunda.text
    assert segunda.json()["code"] == "MOVEMENT_TYPE_DUPLICATE"

    db = mundo.factory()
    try:
        assert db.execute(select(func.count()).select_from(MovementType).where(
            MovementType.company_id == mundo.company_a, MovementType.code == codigo)).scalar() == 1
    finally:
        db.close()


def test_dos_altas_simultaneas_del_mismo_codigo_dan_un_conflicto_y_no_un_500(mundo):
    """La carrera se fuerza: sin ella, la prueba pasaría aunque no hubiera captura."""
    empresa = empresa_nueva(mundo.factory, mundo.t1, uuid4().hex[:10])
    codigo = _codigo("RACE")

    def alta(sesion):
        return str(inv.crear_tipo_de_movimiento(
            sesion, company_id=empresa, code=codigo, name="Carrera",
            direction="IN", actor=None).id)

    primero, segundo = carrera(mundo.factory, alta, alta)

    assert not isinstance(primero, Exception), f"quien ganó recibió {primero!r}"
    assert isinstance(segundo, ConflictError), (
        f"quien perdió la carrera recibió {type(segundo).__name__}: {segundo!r}")
    assert segundo.code == "MOVEMENT_TYPE_DUPLICATE"
    assert segundo.status_code == 409

    db = mundo.factory()
    try:
        assert db.execute(select(func.count()).select_from(MovementType).where(
            MovementType.company_id == empresa, MovementType.code == codigo)).scalar() == 1
    finally:
        db.close()


def test_la_carrera_se_resuelve_igual_cada_vez(mundo):
    """No es cazar intermitencias: es demostrar que el resultado es estable."""
    empresa = empresa_nueva(mundo.factory, mundo.t1, uuid4().hex[:10])
    for vuelta in range(8):
        codigo = _codigo(f"REP{vuelta}")

        def alta(sesion, codigo=codigo):
            return str(inv.crear_tipo_de_movimiento(
                sesion, company_id=empresa, code=codigo, name="Repetida",
                direction="IN", actor=None).id)

        primero, segundo = carrera(mundo.factory, alta, alta)
        assert not isinstance(primero, Exception), f"vuelta {vuelta}: ganó nadie"
        assert isinstance(segundo, ConflictError), f"vuelta {vuelta}: perdió con {segundo!r}"

    db = mundo.factory()
    try:
        assert db.execute(select(func.count()).select_from(MovementType).where(
            MovementType.company_id == empresa)).scalar() == 8
    finally:
        db.close()


def test_otro_error_de_integridad_no_se_disfraza_de_duplicado(mundo):
    """Una clave foránea rota no es «ya existe»."""
    db = mundo.factory()
    try:
        with pytest.raises(IntegrityError):
            inv.crear_tipo_de_movimiento(db, company_id=str(uuid4()), code=_codigo("FK"),
                                         name="Empresa inventada", direction="IN", actor=None)
    finally:
        db.rollback()
        db.close()


def test_tras_el_conflicto_la_sesion_sigue_sirviendo(mundo):
    """El savepoint es lo que evita que el conflicto se lleve por delante el resto."""
    empresa = empresa_nueva(mundo.factory, mundo.t1, uuid4().hex[:10])
    codigo = _codigo("REC")
    db = mundo.factory()
    try:
        inv.crear_tipo_de_movimiento(db, company_id=empresa, code=codigo, name="Primero",
                                     direction="IN", actor=None)
        db.commit()

        with pytest.raises(ConflictError):
            inv.crear_tipo_de_movimiento(db, company_id=empresa, code=codigo, name="Repetido",
                                         direction="IN", actor=None)

        # Y la misma sesión, sin rollback de por medio, sigue pudiendo trabajar.
        otro = inv.crear_tipo_de_movimiento(db, company_id=empresa, code=_codigo("REC2"),
                                            name="Después del conflicto", direction="OUT",
                                            actor=None)
        db.commit()
        assert otro.id is not None
    finally:
        db.close()


def test_tras_la_colision_real_la_sesion_sigue_sirviendo(mundo):
    """El savepoint, comprobado por el camino difícil.

    La prueba de arriba resuelve el conflicto con la consulta previa, así que
    nunca llega a la violación: sirve para el contrato, no para el savepoint. Aquí
    la colisión ocurre de verdad, y lo que se mide es que la sesión que la recibe
    siga pudiendo trabajar. Sin `begin_nested`, PostgreSQL deja la transacción
    abortada y cualquier cosa que venga después muere con ella.
    """
    empresa = empresa_nueva(mundo.factory, mundo.t1, uuid4().hex[:10])
    codigo, despues = _codigo("SVP"), _codigo("SVPOK")

    def alta(sesion):
        return str(inv.crear_tipo_de_movimiento(
            sesion, company_id=empresa, code=codigo, name="Savepoint",
            direction="IN", actor=None).id)

    def alta_y_continuar(sesion):
        try:
            inv.crear_tipo_de_movimiento(sesion, company_id=empresa, code=codigo,
                                         name="Savepoint", direction="IN", actor=None)
        except ConflictError:
            otro = inv.crear_tipo_de_movimiento(sesion, company_id=empresa, code=despues,
                                                name="Después de chocar", direction="OUT",
                                                actor=None)
            sesion.flush()
            return str(otro.id)
        return "NO_HUBO_CONFLICTO"

    _, segundo = carrera(mundo.factory, alta, alta_y_continuar)
    assert not isinstance(segundo, Exception), (
        f"la sesión que perdió quedó inservible: {type(segundo).__name__}: {segundo!r}")
    assert segundo != "NO_HUBO_CONFLICTO", "no se llegó a la colisión"

    db = mundo.factory()
    try:
        assert db.execute(select(func.count()).select_from(MovementType).where(
            MovementType.company_id == empresa, MovementType.code == despues)).scalar() == 1
    finally:
        db.close()


def test_dos_altas_simultaneas_de_codigos_distintos_entran_las_dos(mundo):
    """Capturar la colisión no puede convertirse en serializar las altas."""
    empresa = empresa_nueva(mundo.factory, mundo.t1, uuid4().hex[:10])
    a, b = _codigo("DISA"), _codigo("DISB")
    s1, s2 = mundo.factory(), mundo.factory()
    try:
        uno = inv.crear_tipo_de_movimiento(s1, company_id=empresa, code=a, name="A",
                                           direction="IN", actor=None)
        s1.flush()
        # La primera sigue **sin confirmar**: si el arreglo bloqueara de más,
        # esta segunda se quedaría esperando en vez de entrar.
        dos = inv.crear_tipo_de_movimiento(s2, company_id=empresa, code=b, name="B",
                                           direction="OUT", actor=None)
        s2.commit()
        s1.commit()
        assert uno.id != dos.id
    finally:
        s1.close()
        s2.close()


def test_el_mismo_codigo_en_otra_empresa_es_otro_tipo(mundo):
    """La identidad incluye la empresa: el índice es (company_id, code)."""
    codigo = _codigo("MC")
    cuerpo = {"code": codigo, "name": "Dos empresas", "direction": "IN"}
    a = mundo.post("/inventory/movement-types", "ua", mundo.company_a, cuerpo)
    b = mundo.post("/inventory/movement-types", "ub", mundo.company_b, cuerpo)
    assert a.status_code == 200, a.text
    assert b.status_code == 200, b.text
    assert a.json()["id"] != b.json()["id"]
