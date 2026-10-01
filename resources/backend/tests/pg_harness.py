"""Ciclo de vida de lo que la suite crea en PostgreSQL.

Cada recurso que el arnés crea en la base de prueba —un schema temporal con su motor, o
una base entera en las pruebas de migración— tiene aquí un dueño y un final:

    crear → usar → cerrar conexiones → soltar → comprobar que se soltó

`conftest.make_engine` crea los schemas a través de este módulo y dos fixtures de
`conftest.py` abren y cierran los ámbitos: lo que nace durante una prueba se suelta al
terminar la prueba, y lo que nace en una fixture de módulo, al terminar el módulo. Pase la
prueba o falle.

Nada de aquí actúa sobre una base que no sea, sin ambigüedad, de prueba; y solo se elimina
lo que este mismo proceso creó.
"""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import NullPool

#: El nombre que el arnés da a un schema temporal. Solo se elimina lo que lo cumple.
PATRON_DE_SCHEMA = re.compile(r"^t_[0-9a-f]{12}$")
#: Comentario con que el arnés firma cada schema que crea.
PREFIJO_DE_MARCA = "kontrol-test "
#: `application_name` de las conexiones de un motor de prueba: `kontrol-test:<schema>`.
PREFIJO_DE_APLICACION = "kontrol-test:"
#: Entornos en los que la suite puede crear y destruir (`KONTROL_ENVIRONMENT`).
ENTORNOS_DE_PRUEBA = ("local", "dev", "qa")


class BaseNoEsDePrueba(RuntimeError):
    """La base indicada no puede identificarse como de prueba: no se crea ni se destruye nada."""


def _destino(url: str) -> tuple[str, int, str]:
    u = make_url(url)
    return ((u.host or "localhost").lower().replace("127.0.0.1", "localhost"), u.port or 5432, u.database or "")


def exigir_base_de_prueba(url: str) -> None:
    """Se niega a seguir si la base no es de prueba.

    Varias señales, todas necesarias: la URL es la que se declaró expresamente para pruebas
    (`KONTROL_TEST_DB_URL`); el nombre de la base dice que es de prueba; no es la base que
    el producto tiene configurada (`KONTROL_DB_URL`); y el entorno no es de los que sirven a
    usuarios. Crear y soltar schemas es destructivo: ante la duda, no se hace.
    """
    declarada = os.environ.get("KONTROL_TEST_DB_URL")
    if not declarada or url != declarada:
        raise BaseNoEsDePrueba("la URL no es la declarada en KONTROL_TEST_DB_URL")
    if not url.startswith("postgresql"):
        raise BaseNoEsDePrueba("la URL de prueba no es de PostgreSQL")
    host, puerto, base = _destino(url)
    if "test" not in base.lower():
        raise BaseNoEsDePrueba(f"el nombre de la base ({base!r}) no dice que sea de prueba: debe contener «test»")
    entorno = os.environ.get("KONTROL_ENVIRONMENT", "local")
    if entorno not in ENTORNOS_DE_PRUEBA:
        raise BaseNoEsDePrueba(f"KONTROL_ENVIRONMENT={entorno!r} no es un entorno de prueba {ENTORNOS_DE_PRUEBA}")
    producto = os.environ.get("KONTROL_DB_URL", "")
    if producto.startswith("postgresql") and _destino(producto) == (host, puerto, base):
        raise BaseNoEsDePrueba("la base de prueba es la misma que la configurada para el producto (KONTROL_DB_URL)")


def motor_administrativo(url: str) -> Engine:
    """Motor de un solo uso para DDL y medidas: sin pool, cada sentencia en su transacción."""
    return create_engine(url, future=True, poolclass=NullPool, isolation_level="AUTOCOMMIT")


# --------------------------------------------------------------------------- #
# Registro por ámbitos: quién creó qué, y cuándo le toca soltarlo
# --------------------------------------------------------------------------- #
class ResiduoDePrueba(RuntimeError):
    """Un recurso de prueba no pudo soltarse: la suite dejaría sucia la base."""


@dataclass
class Ambito:
    """Un tramo de la corrida —una prueba, un módulo— y lo que se creó mientras estuvo abierto."""

    nombre: str
    motores: list[tuple[str, str, Engine]] = field(default_factory=list)  # (url, schema, motor)
    bases: list[str] = field(default_factory=list)


@dataclass
class Informe:
    """Lo que la corrida creó y soltó. Se imprime al terminar si algo no cuadra."""

    schemas_creados: int = 0
    schemas_soltados: int = 0
    bases_soltadas: int = 0
    #: (ámbito, schema, conexiones) — conexiones que una prueba dejó abiertas y hubo que cortar.
    conexiones_cortadas: list[tuple[str, str, int]] = field(default_factory=list)
    #: Lo que no se pudo soltar.
    residuos: list[str] = field(default_factory=list)


_PILA: list[Ambito] = []
#: Lo que se crea sin ningún ámbito abierto. Lo suelta la red de seguridad del final de la sesión.
_SESION = Ambito("sesión")
INFORME = Informe()


def ambito_vigente() -> Ambito:
    return _PILA[-1] if _PILA else _SESION


def abrir_ambito(nombre: str) -> Ambito:
    ambito = Ambito(nombre)
    _PILA.append(ambito)
    return ambito


def cerrar_ambito(ambito: Ambito) -> None:
    """Suelta todo lo que se creó en el ámbito. Si algo no se deja soltar, lo dice con un error."""
    fallos: list[str] = []
    # Un ámbito que quedara abierto por encima se cierra antes: nada sobrevive a su dueño.
    while _PILA and _PILA[-1] is not ambito:
        fallos += _liberar(_PILA.pop())
    if _PILA and _PILA[-1] is ambito:
        _PILA.pop()
    fallos += _liberar(ambito)
    if fallos:
        INFORME.residuos += fallos
        raise ResiduoDePrueba("; ".join(fallos))


def cerrar_sesion() -> None:
    """Red de seguridad: suelta lo que quede en cualquier ámbito, también lo creado fuera de todos."""
    fallos: list[str] = []
    while _PILA:
        fallos += _liberar(_PILA.pop())
    fallos += _liberar(_SESION)
    INFORME.residuos += fallos


def _liberar(ambito: Ambito) -> list[str]:
    fallos: list[str] = []
    while ambito.motores:
        url, schema, motor = ambito.motores.pop()
        try:
            soltar_schema(url, schema, motor, contexto=ambito.nombre)
        except Exception as e:  # noqa: BLE001 - se intenta soltar todo y se informa de lo que no se pudo
            fallos.append(f"schema {schema} ({ambito.nombre}): {type(e).__name__}: {e}")
    while ambito.bases:
        nombre = ambito.bases.pop()
        try:
            soltar_base(nombre)
        except Exception as e:  # noqa: BLE001
            fallos.append(f"base {nombre} ({ambito.nombre}): {type(e).__name__}: {e}")
    return fallos


# --------------------------------------------------------------------------- #
# Schemas temporales
# --------------------------------------------------------------------------- #
def crear_motor_de_prueba(url: str, **kwargs) -> Engine:
    """Crea un schema temporal y el motor que trabaja en él, y los apunta al ámbito abierto."""
    exigir_base_de_prueba(url)
    schema = f"t_{uuid.uuid4().hex[:12]}"
    marca = f"{PREFIJO_DE_MARCA}pid={os.getpid()} creado={datetime.now(UTC).isoformat(timespec='seconds')}"
    admin = motor_administrativo(url)
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(text(f"COMMENT ON SCHEMA \"{schema}\" IS '{marca}'"))
    finally:
        admin.dispose()

    # El schema se fija en `connect_args`, no con un listener de evento: si se
    # registra el listener después de abrir la primera conexión, ésta queda en
    # el pool SIN `search_path` y todas las pruebas acaban compartiendo
    # `public`. Detectado al ejecutar la suite sobre PostgreSQL real.
    connect_args = dict(kwargs.pop("connect_args", {}))
    connect_args["options"] = f"-csearch_path={schema}"
    # El nombre de aplicación permite ver, desde el servidor, qué conexiones son de este schema.
    connect_args["application_name"] = PREFIJO_DE_APLICACION + schema
    motor = create_engine(url, future=True, connect_args=connect_args, **kwargs)
    ambito_vigente().motores.append((url, schema, motor))
    INFORME.schemas_creados += 1
    return motor


def soltar_schema(url: str, schema: str, motor: Engine | None, *, contexto: str = "") -> None:
    """Cierra las conexiones del motor, elimina el schema y comprueba que ya no existe.

    Solo actúa sobre una base de prueba y sobre un schema con el nombre y la marca del arnés.
    """
    exigir_base_de_prueba(url)
    if not PATRON_DE_SCHEMA.fullmatch(schema):
        raise ResiduoDePrueba(f"{schema!r} no es un schema temporal del arnés: no se elimina")
    if motor is not None:
        motor.dispose()
    admin = motor_administrativo(url)
    try:
        with admin.connect() as conn:
            fila = conn.execute(text(
                "select obj_description(oid, 'pg_namespace') from pg_namespace where nspname = :n"),
                {"n": schema}).first()
            if fila is None:
                return
            if not (fila[0] or "").startswith(PREFIJO_DE_MARCA):
                raise ResiduoDePrueba(f"el schema {schema} no lleva la marca del arnés: no se elimina")
            # Tras `dispose()` no debería quedar nadie conectado a este schema. Si queda, es una
            # conexión que la prueba no cerró: se anota y se corta, para no dejar el schema huérfano.
            aplicacion = PREFIJO_DE_APLICACION + schema
            abiertas = conn.execute(text(
                "select count(*) from pg_stat_activity where application_name = :a"), {"a": aplicacion}).scalar_one()
            if abiertas:
                INFORME.conexiones_cortadas.append((contexto, schema, abiertas))
                conn.execute(text(
                    "select pg_terminate_backend(pid) from pg_stat_activity "
                    "where application_name = :a and pid <> pg_backend_pid()"), {"a": aplicacion})
            conn.execute(text("SET lock_timeout = '30s'"))
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            queda = conn.execute(text(
                "select count(*) from pg_namespace where nspname = :n"), {"n": schema}).scalar_one()
            if queda:
                raise ResiduoDePrueba(f"el schema {schema} sigue existiendo después de eliminarlo")
            INFORME.schemas_soltados += 1
    finally:
        admin.dispose()


# --------------------------------------------------------------------------- #
# Bases temporales (pruebas de migración)
# --------------------------------------------------------------------------- #
def _url_de_mantenimiento() -> str:
    url = os.environ.get("KONTROL_TEST_DB_URL", "")
    exigir_base_de_prueba(url)
    return make_url(url).set(database="postgres").render_as_string(hide_password=False)


def registrar_base(nombre: str) -> None:
    """Apunta al ámbito abierto una base entera que la prueba acaba de crear, para soltarla con él."""
    ambito_vigente().bases.append(nombre)


def soltar_base(nombre: str) -> None:
    """Elimina una base temporal del servidor de pruebas. Nunca la de prueba ni las del sistema."""
    protegidas = {"postgres", "template0", "template1", _destino(os.environ.get("KONTROL_TEST_DB_URL", ""))[2]}
    if nombre in protegidas or not re.fullmatch(r"[a-z0-9_]+", nombre):
        raise ResiduoDePrueba(f"{nombre!r} no es una base temporal de prueba: no se elimina")
    admin = motor_administrativo(_url_de_mantenimiento())
    try:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{nombre}" WITH (FORCE)'))
            queda = conn.execute(text("select count(*) from pg_database where datname = :n"), {"n": nombre}).scalar_one()
            if queda:
                raise ResiduoDePrueba(f"la base {nombre} sigue existiendo después de eliminarla")
            INFORME.bases_soltadas += 1
    finally:
        admin.dispose()
