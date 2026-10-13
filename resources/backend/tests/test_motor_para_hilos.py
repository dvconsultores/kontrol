"""ACS-01…08 · la primitiva `motor_para_hilos` del arnés (SPEC008 · ALMACENES-CARRERA-SQLITE-HILOS).

Un módulo que lanza hilos contra la app necesita una conexión DBAPI por hilo sobre el
mismo datastore. Estas pruebas certifican esa topología, el aislamiento, el entrelazado
controlado de dos inserciones de la misma clave, que un bloqueo de SQLite no se
confunde con un duplicado, la limpieza del fichero temporal y el contrato estático de
la primitiva. Corren igual en SQLite (fichero temporal) y en PostgreSQL (motor de
`make_engine()`), sin `skip`.
"""

from __future__ import annotations

import inspect
import os
import sqlite3
import tempfile
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, event, insert, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.core.integrity import es_violacion_unica
from tests import conftest
from tests.conftest import PREFIJO_DE_SQLITE, motor_para_hilos

PG = os.environ.get("KONTROL_TEST_DB_URL", "").startswith("postgresql")
PLAZO = 10  # segundos: tope de las barreras; una prueba que lo agota falla, no espera


def _directorios_temporales() -> set[Path]:
    return set(Path(tempfile.gettempdir()).glob(f"{PREFIJO_DE_SQLITE}*"))


def _tabla(motor: Engine) -> Table:
    metadatos = MetaData()
    filas = Table(
        "acs_filas", metadatos,
        Column("id", Integer, primary_key=True),
        Column("clave", String(20), nullable=False, unique=True),
    )
    metadatos.create_all(motor)
    return filas


@pytest.fixture
def mundo() -> Iterator[tuple[Engine, Table]]:
    with motor_para_hilos("acs") as motor:
        yield motor, _tabla(motor)


def _id_de_conexion(sesion: Session) -> int:
    return id(sesion.connection().connection.dbapi_connection)


def _en_hilos(*trabajos) -> list[str]:
    """Ejecuta cada trabajo en su hilo y devuelve las excepciones que los mataron (vacío si ninguna)."""
    errores: list[str] = []

    def envoltura(trabajo):
        try:
            trabajo()
        except Exception as exc:  # noqa: BLE001 — se mide exactamente qué mata al hilo
            errores.append(f"{type(exc).__name__}: {exc}"[:200])

    hilos = [threading.Thread(target=envoltura, args=(t,)) for t in trabajos]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(PLAZO * 2)
    assert not any(h.is_alive() for h in hilos), "un hilo no terminó"
    return errores


# ACS-01 · topología: cada hilo concurrente trabaja sobre su propia conexión DBAPI.
def test_acs_01_cada_hilo_concurrente_tiene_su_propia_conexion(mundo):
    motor, filas = mundo
    ids: list[int] = []
    barrera = threading.Barrier(2, timeout=PLAZO)

    def trabajo() -> None:
        with Session(motor) as sesion:
            sesion.execute(select(filas.c.id))  # abre la transacción: la conexión queda en la mano
            ids.append(_id_de_conexion(sesion))
            barrera.wait()  # las dos sesiones sostienen su conexión a la vez

    assert _en_hilos(trabajo, trabajo) == []
    assert len(ids) == 2 and ids[0] != ids[1], ids


# ACS-02 · mismo datastore: lo que confirma un hilo lo lee otro por su propia conexión.
def test_acs_02_lo_confirmado_por_un_hilo_lo_ve_otro_por_otra_conexion(mundo):
    motor, filas = mundo
    ids: dict[str, int] = {}
    vistos: list[int] = []
    confirmado = threading.Barrier(2, timeout=PLAZO)
    leido = threading.Barrier(2, timeout=PLAZO)

    def escritor() -> None:
        with Session(motor) as sesion:
            sesion.execute(insert(filas).values(clave="compartida"))
            sesion.commit()
            sesion.execute(select(filas.c.id))  # vuelve a tomar su conexión y la sostiene
            ids["A"] = _id_de_conexion(sesion)
            confirmado.wait()
            leido.wait()

    def lector() -> None:
        confirmado.wait()
        with Session(motor) as sesion:
            vistos.append(sesion.execute(select(filas.c.id).where(filas.c.clave == "compartida")).scalar_one_or_none() or 0)
            ids["B"] = _id_de_conexion(sesion)
            leido.wait()

    assert _en_hilos(escritor, lector) == []
    assert ids["A"] != ids["B"], ids
    assert vistos == [1], vistos


# ACS-03 · aislamiento: lo no confirmado no se ve, y tras el rollback tampoco.
def test_acs_03_lo_no_confirmado_no_lo_ve_otro_hilo_ni_antes_ni_despues_del_rollback(mundo):
    motor, filas = mundo
    cuentas: list[int] = []
    insertado = threading.Barrier(2, timeout=PLAZO)
    leido = threading.Barrier(2, timeout=PLAZO)
    deshecho = threading.Barrier(2, timeout=PLAZO)

    def escritor() -> None:
        with Session(motor) as sesion:
            sesion.execute(insert(filas).values(clave="fantasma"))
            insertado.wait()
            leido.wait()
            sesion.rollback()
            deshecho.wait()

    def lector() -> None:
        insertado.wait()
        with Session(motor) as sesion:
            cuentas.append(sesion.execute(select(filas.c.id).where(filas.c.clave == "fantasma")).scalars().all().__len__())
        leido.wait()
        deshecho.wait()
        with Session(motor) as sesion:
            cuentas.append(len(sesion.execute(select(filas.c.id).where(filas.c.clave == "fantasma")).scalars().all()))

    assert _en_hilos(escritor, lector) == []
    assert cuentas == [0, 0], cuentas


# ACS-04 · entrelazado controlado: dos INSERT de la misma clave liberados a la vez →
# exactamente un éxito, exactamente un IntegrityError, una fila, ningún otro error.
def test_acs_04_dos_inserts_simultaneos_de_la_misma_clave_dan_un_exito_y_un_integrity_error(mundo):
    motor, filas = mundo
    resultados: list[str] = []
    barrera = threading.Barrier(2, timeout=PLAZO)

    def gancho(conn, cursor, sentencia, parametros, contexto, muchos) -> None:
        if sentencia.lstrip().upper().startswith("INSERT INTO") and threading.current_thread() is not threading.main_thread():
            barrera.wait()  # instrumentación: los dos INSERT se ejecutan a la vez

    def intento() -> None:
        with Session(motor) as sesion:
            try:
                sesion.execute(insert(filas).values(clave="RACE-1"))
                sesion.commit()
                resultados.append("ok")
            except IntegrityError:
                sesion.rollback()
                resultados.append("IntegrityError")

    event.listen(motor, "before_cursor_execute", gancho)
    try:
        errores = _en_hilos(intento, intento)
    finally:
        event.remove(motor, "before_cursor_execute", gancho)

    assert errores == [], errores
    assert sorted(resultados) == ["IntegrityError", "ok"], resultados
    with Session(motor) as sesion:
        assert len(sesion.execute(select(filas.c.id).where(filas.c.clave == "RACE-1")).scalars().all()) == 1


# ACS-05 · un bloqueo de SQLite no es un duplicado: OperationalError, no IntegrityError,
# y `es_violacion_unica` lo rechaza. Biblioteca estándar y un motor propio de la prueba
# (timeout 0 para que el bloqueo sea inmediato en vez de esperar el busy_timeout): la
# primitiva del arnés no se toca y la prueba vale en cualquier corrida.
def test_acs_05_un_bloqueo_de_sqlite_no_se_confunde_con_un_duplicado(tmp_path):
    ruta = tmp_path / "bloqueo.db"
    motor = create_engine(f"sqlite+pysqlite:///{ruta}", future=True, connect_args={"timeout": 0})
    filas = _tabla(motor)
    escritor = sqlite3.connect(str(ruta))
    try:
        escritor.execute("BEGIN IMMEDIATE")
        escritor.execute("INSERT INTO acs_filas (clave) VALUES ('RACE-1')")  # escritura en curso, sin confirmar
        with pytest.raises(OperationalError) as info:
            with motor.begin() as conexion:
                conexion.execute(insert(filas).values(clave="RACE-1"))
        assert not isinstance(info.value, IntegrityError)
        assert "locked" in str(info.value.orig).lower(), info.value.orig
        assert es_violacion_unica(info.value, "acs_filas_clave_key") is False  # type: ignore[arg-type]
        escritor.rollback()
        # Con la escritura deshecha la misma inserción entra; repetirla sí es un duplicado: IntegrityError.
        with motor.begin() as conexion:
            conexion.execute(insert(filas).values(clave="RACE-1"))
        with pytest.raises(IntegrityError):
            with motor.begin() as conexion:
                conexion.execute(insert(filas).values(clave="RACE-1"))
    finally:
        escritor.close()
        motor.dispose()


# ACS-06 · limpieza: en SQLite el directorio nace con el contexto y muere con él, y el pool
# queda vacío; en PostgreSQL no se crea ningún directorio.
def test_acs_06_el_datastore_temporal_existe_dentro_del_contexto_y_no_despues():
    antes = _directorios_temporales()
    with motor_para_hilos("acs-limpieza") as motor:
        nuevos = _directorios_temporales() - antes
        with motor.connect() as conexion:
            conexion.execute(text("SELECT 1"))
        if PG:
            assert motor.dialect.name == "postgresql"
            assert nuevos == set(), nuevos
        else:
            assert motor.dialect.name == "sqlite"
            assert len(nuevos) == 1, nuevos
            directorio = nuevos.pop()
            assert directorio.name.startswith(f"{PREFIJO_DE_SQLITE}acs-limpieza-")
            assert (directorio / "base.db").is_file()
            assert motor.pool.checkedin() >= 1  # la conexión volvió al pool: hay algo que liberar
    assert _directorios_temporales() - antes == set()
    if not PG:
        assert motor.pool.checkedin() == 0 and motor.pool.checkedout() == 0  # `dispose()` hecho


# ACS-07 · limpieza también cuando lo de dentro falla.
def test_acs_07_el_datastore_temporal_se_elimina_aunque_el_contexto_falle():
    antes = _directorios_temporales()
    with pytest.raises(RuntimeError, match="fallo sintético"):
        with motor_para_hilos("acs-fallo") as motor:
            with motor.connect() as conexion:
                conexion.execute(text("SELECT 1"))
            raise RuntimeError("fallo sintético")
    assert _directorios_temporales() - antes == set()


# ACS-08 · contrato estático: la primitiva no toca tiempos ni pool, `make_engine()` no cambia
# y la prueba objetivo conserva sus aserciones sin reintentos, esperas ni cerrojos.
def test_acs_08_contrato_estatico_de_la_primitiva_y_de_la_prueba_objetivo():
    fuente = inspect.getsource(motor_para_hilos).replace(str(motor_para_hilos.__doc__), "")  # el código, no su docstring
    for prohibido in ("timeout", "StaticPool", ":memory:", "sleep", "PRAGMA", "isolation_level", "poolclass"):
        assert prohibido not in fuente, prohibido
    assert 'connect_args={"check_same_thread": False}' in fuente
    assert "tempfile.mkdtemp(" in fuente and "motor.dispose()" in fuente and "shutil.rmtree(directorio)" in fuente
    assert 'if os.environ.get("KONTROL_TEST_DB_URL"):' in fuente and "yield make_engine()" in fuente

    fuente_make_engine = inspect.getsource(conftest.make_engine)
    assert "StaticPool" in fuente_make_engine and ":memory:" in fuente_make_engine

    fuente_acs_04 = inspect.getsource(test_acs_04_dos_inserts_simultaneos_de_la_misma_clave_dan_un_exito_y_un_integrity_error)
    assert 'event.listen(motor, "before_cursor_execute", gancho)' in fuente_acs_04 and "barrera.wait()" in fuente_acs_04

    objetivo = Path(__file__).with_name("test_warehouse_structure.py").read_text(encoding="utf-8")
    assert 'with motor_para_hilos("warehouse-structure") as engine:' in objetivo
    assert "= make_engine()" not in objetivo
    inicio = objetivo.index("def test_concurrencia_de_codigo_resuelta_por_constraint")
    bloque = objetivo[inicio:]
    bloque = bloque[: bloque.index("\ndef ")] if "\ndef " in bloque else bloque
    assert "barrier = threading.Barrier(2)" in bloque
    assert "assert sorted(results) == [200, 409], results" in bloque
    assert 'headers=h).json()["total"] == 1' in bloque
    for prohibido in ("sleep(", "Lock(", "retry", "skip", "xfail", "timeout", " or len(results)"):
        assert prohibido not in bloque, prohibido
