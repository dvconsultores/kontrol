"""La base efímera de una corrida E2E: compuerta, crear, migrar, sembrar y eliminar.

Cada corrida E2E certificable corre contra una base PostgreSQL que nace para ella y muere
con ella (FR-054-E2EDB-001..015):

    compuerta → crear → migrar a la cabeza → sembrar → … → eliminar → comprobar que no está

Crear y eliminar bases es destructivo, así que nada de aquí actúa sobre una base que no sea,
sin ambigüedad, de una corrida E2E: el nombre cumple el patrón entero, no es ninguna de las
protegidas, el entorno y el servidor son de QA, y —para eliminar— la base lleva la marca que
este mismo arnés le puso al crearla. El nombre que se elimina lo construye el arnés a partir
del identificador de la corrida, o lo lee del catálogo ya filtrado: nunca llega de fuera.

`kaud` (QA manual) y `ktest` (pruebas de backend) quedan fuera de este ciclo de vida.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import e2e_nombres as nombres
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.pool import NullPool

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "resources" / "backend"

#: Entornos en los que se puede crear y eliminar una base (`KONTROL_ENVIRONMENT`).
ENTORNOS = ("local", "dev", "qa")
#: Bases del propio servidor: no son de nadie.
DEL_SISTEMA = frozenset({"postgres", "template0", "template1"})
#: Bases de QA que este ciclo de vida no toca (`KONTROL_E2E_PROTECTED_DBS`).
PROTEGIDAS_POR_DEFECTO = "kaud,ktest"
#: Servidores sobre los que se puede actuar (`KONTROL_E2E_PG_HOSTS`).
SERVIDORES_POR_DEFECTO = "localhost"

#: Usuarios que siembra la base de QA y, por cada uno, sus clones por worker (qa/mfa-e2e-identidades.py).
BASES_DE_USUARIOS = ("DEMO/admin", "DEMO/ua", "DEMO/uab", "DEMO/ub", "DEMO2/uc")
#: La corrida canónica fija `--workers=6`.
WORKERS_E2E = 6

#: Lo que deja la siembra canónica (`qa/e2e-seed.sh`) en una base recién migrada.
LINEA_BASE: dict[str, object] = {
    "installations": 1,
    "tenants": ["DEMO", "DEMO2"],
    "companies": ["DEMO/D1", "DEMO/D2", "DEMO2/E1"],
    "users": sorted([*BASES_DE_USUARIOS, *(f"{u}_w{k}" for u in BASES_DE_USUARIOS for k in range(WORKERS_E2E))]),
    "license": ["FULL_ACCESS"],
    "warehouses": 0,
    "notification_rules": 0,
}
#: Los guiones de los que sale la siembra: su huella es la versión de la siembra.
GUIONES_DE_SIEMBRA = ("e2e-seed.sh", "pg-e2e-seed.py", "spec047-e2e-seed.py", "n6-e2e-seed.py",
                      "mfa-e2e-identidades.py", "n6_world.py", "alcance_de_usuario.py")


class BaseNoEsE2E(RuntimeError):
    """La base no puede identificarse como de una corrida E2E: no se crea ni se elimina nada."""


class CicloDeBaseRoto(RuntimeError):
    """Un paso del ciclo de vida no dejó la base como debía."""


# --------------------------------------------------------------------------- #
# Servidor
# --------------------------------------------------------------------------- #
def _servidor_de(url: str) -> tuple[str, int]:
    u = make_url(url)
    host = (u.host or "localhost").lower()
    return ("localhost" if host in ("127.0.0.1", "::1") else host, u.port or 5432)


@dataclass(frozen=True)
class Servidor:
    """El PostgreSQL de QA: con qué rol se crean y eliminan bases, y cuál es su dueño."""

    admin_url: str
    duena_url: str

    @classmethod
    def del_entorno(cls, entorno: Mapping[str, str] | None = None) -> Servidor:
        """Por defecto, el servidor local que levanta `qa/pg-provision.sh`."""
        e = os.environ if entorno is None else entorno
        puerto = e.get("KONTROL_PGPORT", "55432")
        return cls(
            admin_url=e.get("KONTROL_E2E_ADMIN_DB_URL")
            or f"postgresql+psycopg2://postgres@localhost:{puerto}/postgres",
            duena_url=e.get("KONTROL_E2E_OWNER_DB_URL")
            or f"postgresql+psycopg2://kontrol_migrator:qa@localhost:{puerto}/postgres",
        )

    def destino(self) -> str:
        """Servidor y puerto, sin credenciales: lo único que se escribe en registros."""
        host, puerto = _servidor_de(self.admin_url)
        return f"{host}:{puerto}"

    def rol_dueno(self) -> str:
        rol = make_url(self.duena_url).username or ""
        if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", rol):
            raise CicloDeBaseRoto("el rol dueño de la base de la corrida no es un identificador simple")
        return rol

    def url_de(self, base: str) -> str:
        """La URL con la que el producto, la siembra y las migraciones llegan a la base de la corrida."""
        run = nombres.run_de_base(base)
        if run is None:
            raise BaseNoEsE2E(f"{base!r} no es el nombre de una base de corrida E2E")
        if _servidor_de(self.duena_url) != _servidor_de(self.admin_url):
            raise CicloDeBaseRoto("el rol dueño y el rol administrativo apuntan a servidores distintos")
        url = make_url(self.duena_url).set(database=base).render_as_string(hide_password=False)
        # El nombre de aplicación se añade tal cual, sin codificar los dos puntos: `alembic/env.py`
        # pasa la URL por `configparser`, que no admite un «%» suelto.
        return f"{url}{'&' if '?' in url else '?'}application_name={nombres.aplicacion(run)}"


def motor_administrativo(servidor: Servidor) -> Engine:
    """Motor de un solo uso: sin pool y en autocommit, que es como PostgreSQL crea y elimina bases."""
    return create_engine(servidor.admin_url, future=True, poolclass=NullPool, isolation_level="AUTOCOMMIT")


def _motor_de_lectura(url: str) -> Engine:
    return create_engine(url, future=True, poolclass=NullPool)


# --------------------------------------------------------------------------- #
# Compuerta de identidad
# --------------------------------------------------------------------------- #
def _lista(valor: str) -> set[str]:
    return {parte.strip().lower() for parte in valor.split(",") if parte.strip()}


def _base_de(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return make_url(url).database or None
    except Exception:  # noqa: BLE001 - una URL ilegible no protege nada, pero tampoco autoriza
        return None


def protegidas(admin_url: str, entorno: Mapping[str, str] | None = None) -> set[str]:
    """Las bases que este ciclo de vida no crea, corta ni elimina, se llamen como se llamen."""
    e = os.environ if entorno is None else entorno
    nombres_ = set(DEL_SISTEMA) | _lista(e.get("KONTROL_E2E_PROTECTED_DBS", PROTEGIDAS_POR_DEFECTO))
    for url in (e.get("KONTROL_DB_URL"), e.get("KONTROL_TEST_DB_URL"), admin_url):
        base = _base_de(url)
        if base:
            nombres_.add(base)
    return nombres_


def exigir_base_e2e(nombre: object, *, admin_url: str, entorno: Mapping[str, str] | None = None) -> str:
    """Se niega a seguir si `nombre` no es, sin ambigüedad, la base de una corrida E2E.

    Devuelve el identificador de la corrida. Varias señales, todas necesarias: el nombre
    cumple entero el patrón de las bases de corrida; no es una base protegida; el entorno no
    sirve a usuarios; y el servidor es PostgreSQL y está en la lista de los de QA.
    """
    e = os.environ if entorno is None else entorno
    run = nombres.run_de_base(nombre)
    if run is None:
        raise BaseNoEsE2E(f"{nombre!r} no es el nombre de una base de corrida E2E")
    if nombre in protegidas(admin_url, e):
        raise BaseNoEsE2E(f"{nombre!r} es una base protegida")
    ambiente = e.get("KONTROL_ENVIRONMENT", "local")
    if ambiente not in ENTORNOS:
        raise BaseNoEsE2E(f"KONTROL_ENVIRONMENT={ambiente!r} no es un entorno de QA {ENTORNOS}")
    try:
        url = make_url(admin_url)
    except Exception as error:  # noqa: BLE001
        raise BaseNoEsE2E("la URL administrativa no se puede leer") from error
    if not url.drivername.startswith("postgresql"):
        raise BaseNoEsE2E("el servidor administrativo no es PostgreSQL")
    host, _ = _servidor_de(admin_url)
    if host not in _lista(e.get("KONTROL_E2E_PG_HOSTS", SERVIDORES_POR_DEFECTO)):
        raise BaseNoEsE2E(f"el servidor {host!r} no está entre los permitidos (KONTROL_E2E_PG_HOSTS)")
    return run


def _existe(conn: Connection, nombre: str) -> bool:
    return bool(conn.execute(text("select count(*) from pg_database where datname = :n"), {"n": nombre}).scalar_one())


def _marca_de(conn: Connection, nombre: str) -> dict[str, str] | None:
    """La marca que el arnés dejó en la base, si es suya: dice de qué corrida es."""
    comentario = conn.execute(text(
        "select shobj_description(oid, 'pg_database') from pg_database where datname = :n"), {"n": nombre}).scalar()
    marca = nombres.leer_marca(comentario)
    if marca is None or marca["run"] != nombres.run_de_base(nombre):
        return None
    return marca


# --------------------------------------------------------------------------- #
# Crear
# --------------------------------------------------------------------------- #
def crear_base(servidor: Servidor, run_id: str, *, entorno: Mapping[str, str] | None = None,
               pid: int | None = None, ahora: datetime | None = None) -> str:
    """Crea la base de la corrida, vacía y marcada. Si ya existe, falla: no se reutiliza ninguna."""
    nombre = nombres.nombre_de_base(run_id)
    exigir_base_e2e(nombre, admin_url=servidor.admin_url, entorno=entorno)
    rol = servidor.rol_dueno()
    marca = nombres.marca(run_id, pid or os.getpid(), socket.gethostname(), ahora or datetime.now(UTC))
    admin = motor_administrativo(servidor)
    try:
        with admin.connect() as conn:
            if _existe(conn, nombre):
                raise CicloDeBaseRoto(f"la base {nombre} ya existe: una corrida no reutiliza una base")
            # `template0`: la base no hereda nada de lo que alguien haya dejado en `template1`.
            conn.execute(text(f'CREATE DATABASE "{nombre}" OWNER "{rol}" ENCODING \'UTF8\' TEMPLATE template0'))
            conn.execute(text(f'ALTER DATABASE "{nombre}" SET timezone TO \'UTC\''))
            conn.execute(text(f"COMMENT ON DATABASE \"{nombre}\" IS '{marca}'"))
    finally:
        admin.dispose()
    return nombre


# --------------------------------------------------------------------------- #
# Migrar
# --------------------------------------------------------------------------- #
def cabezas() -> list[str]:
    """Las cabezas del árbol de migraciones del repositorio."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "alembic"))
    return sorted(ScriptDirectory.from_config(config).get_heads())


def _ejecutar(orden: list[str], *, cwd: Path, env: Mapping[str, str], registro: Path) -> int:
    with open(registro, "ab") as salida:
        return subprocess.run(orden, cwd=cwd, env=dict(env), stdout=salida, stderr=subprocess.STDOUT,
                              check=False).returncode


def migrar(url: str, *, env: Mapping[str, str], registro: Path) -> dict[str, object]:
    """Lleva la base a la cabeza con las migraciones canónicas y comprueba que llegó."""
    esperadas = cabezas()
    if len(esperadas) != 1:
        raise CicloDeBaseRoto(f"el árbol de migraciones tiene {len(esperadas)} cabezas: {esperadas}")
    codigo = _ejecutar([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND,
                       env={**env, "KONTROL_DB_URL": url}, registro=registro)
    if codigo != 0:
        raise CicloDeBaseRoto(f"alembic upgrade head terminó con código {codigo} (ver {registro.name})")
    motor = _motor_de_lectura(url)
    try:
        with motor.connect() as conn:
            actuales = sorted(conn.execute(text("select version_num from alembic_version")).scalars().all())
    finally:
        motor.dispose()
    if actuales != esperadas:
        raise CicloDeBaseRoto(f"la base quedó en {actuales} y la cabeza es {esperadas}")
    return {"esperada": esperadas[0], "actual": actuales[0], "cabezas": len(esperadas)}


# --------------------------------------------------------------------------- #
# Sembrar
# --------------------------------------------------------------------------- #
def version_de_siembra() -> str:
    """Huella de los guiones de siembra: dos corridas con la misma huella sembraron lo mismo."""
    resumen = hashlib.sha256()
    for nombre in GUIONES_DE_SIEMBRA:
        resumen.update(nombre.encode())
        resumen.update((RAIZ / "qa" / nombre).read_bytes())
    return resumen.hexdigest()[:16]


def linea_base(url: str) -> dict[str, object]:
    """Lo que hay en la base de lo que la siembra promete."""
    motor = _motor_de_lectura(url)
    try:
        with motor.connect() as conn:
            def cuenta(tabla: str) -> int:
                return int(conn.execute(text(f"select count(*) from {tabla}")).scalar_one())

            def lista(consulta: str) -> list[str]:
                return [str(valor) for valor in conn.execute(text(consulta)).scalars().all()]

            return {
                "installations": cuenta("installations"),
                "tenants": lista("select code from tenants order by 1"),
                "companies": lista("select t.code || '/' || c.code from companies c "
                                   "join tenants t on t.id = c.tenant_id order by 1"),
                "users": lista("select t.code || '/' || u.username from users u "
                               "join tenants t on t.id = u.tenant_id order by 1"),
                "license": lista("select mode from license_states order by 1"),
                "warehouses": cuenta("warehouses"),
                "notification_rules": cuenta("notification_rules"),
            }
    finally:
        motor.dispose()


def sembrar(url: str, *, env: Mapping[str, str], registro: Path) -> dict[str, object]:
    """Siembra la base con el guion canónico, una sola vez, y comprueba la línea base."""
    antes = linea_base(url)
    if antes["installations"] or antes["tenants"] or antes["users"]:
        raise CicloDeBaseRoto("la base ya tiene datos: una corrida no se siembra dos veces")
    # La URL viaja en el entorno, no en la línea de órdenes: lleva la clave del rol de QA.
    codigo = _ejecutar(["bash", str(RAIZ / "qa" / "e2e-seed.sh")], cwd=RAIZ,
                       env={**env, "KONTROL_DB_URL": url, "KONTROL_E2E_PYTHON": sys.executable}, registro=registro)
    if codigo != 0:
        raise CicloDeBaseRoto(f"la siembra terminó con código {codigo} (ver {registro.name})")
    despues = linea_base(url)
    if despues != LINEA_BASE:
        distinto = {clave: despues[clave] for clave in LINEA_BASE if despues[clave] != LINEA_BASE[clave]}
        raise CicloDeBaseRoto(f"la siembra no dejó la línea base esperada: {distinto}")
    return {"version": version_de_siembra(), "linea_base": despues}


# --------------------------------------------------------------------------- #
# Eliminar
# --------------------------------------------------------------------------- #
def conexiones(servidor: Servidor, nombre: str) -> int:
    """Cuántas sesiones hay abiertas contra la base."""
    admin = motor_administrativo(servidor)
    try:
        with admin.connect() as conn:
            return _conexiones(conn, nombre)
    finally:
        admin.dispose()


def _conexiones(conn: Connection, nombre: str) -> int:
    return int(conn.execute(text(
        "select count(*) from pg_stat_activity where datname = :n and pid <> pg_backend_pid()"),
        {"n": nombre}).scalar_one())


def soltar_base(servidor: Servidor, nombre: str, *, entorno: Mapping[str, str] | None = None,
                espera: float = 10.0) -> dict[str, object]:
    """Elimina la base de una corrida y comprueba que ya no está. Hacerlo dos veces no hace nada.

    Quien usaba la base ya debe haberse detenido. Si, pasado un margen, alguien sigue
    conectado, se cortan sus sesiones —solo las de esta base— y se dice cuántas eran.
    """
    exigir_base_e2e(nombre, admin_url=servidor.admin_url, entorno=entorno)
    admin = motor_administrativo(servidor)
    try:
        with admin.connect() as conn:
            if not _existe(conn, nombre):
                return {"estado": "AUSENTE", "cortadas": 0}
            if _marca_de(conn, nombre) is None:
                raise BaseNoEsE2E(f"la base {nombre} no lleva la marca del arnés: no se elimina")
            limite = time.monotonic() + espera
            while _conexiones(conn, nombre) and time.monotonic() < limite:
                time.sleep(0.2)
            abiertas = _conexiones(conn, nombre)
            # `WITH (FORCE)` corta las sesiones de esta base y de ninguna otra.
            conn.execute(text(f'DROP DATABASE "{nombre}"' + (" WITH (FORCE)" if abiertas else "")))
            if _existe(conn, nombre):
                raise CicloDeBaseRoto(f"la base {nombre} sigue existiendo después de eliminarla")
            return {"estado": "ELIMINADA", "cortadas": abiertas}
    finally:
        admin.dispose()


# --------------------------------------------------------------------------- #
# Huérfanas
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class BaseDeCorrida:
    """Una base con nombre de corrida que existe en el servidor, y de quién es."""

    nombre: str
    run: str
    estado: str  # VIVA · HUERFANA · AJENA · SIN_MARCA
    pid: int | None
    maquina: str | None
    creado: str | None
    megas: int
    conexiones: int


def _arranque_del_proceso(pid: int) -> float | None:
    """Cuándo arrancó el proceso `pid` (segundos desde la época), o `None` si no existe."""
    try:
        campos = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        ticks = int(campos[19])
        arranque_del_sistema = next(
            int(linea.split()[1]) for linea in Path("/proc/stat").read_text().splitlines()
            if linea.startswith("btime"))
        return arranque_del_sistema + ticks / os.sysconf("SC_CLK_TCK")
    except (OSError, IndexError, ValueError, StopIteration):
        return None


def lanzador_vivo(marca: Mapping[str, str]) -> bool:
    """¿Sigue en marcha el proceso que creó la base?

    El número de proceso se recicla: solo es el lanzador si ya existía cuando se creó la base.
    """
    arranque = _arranque_del_proceso(int(marca["pid"]))
    if arranque is None:
        return False
    return arranque <= datetime.fromisoformat(marca["creado"]).timestamp() + 1.0


def listar_bases(servidor: Servidor) -> list[BaseDeCorrida]:
    """Las bases de corrida que hay en el servidor. Solo las que cumplen el patrón entero."""
    admin = motor_administrativo(servidor)
    try:
        with admin.connect() as conn:
            filas = conn.execute(text(
                "select datname, pg_database_size(datname) / (1024 * 1024) from pg_database "
                "where datname like 'kontrol\\_e2e\\_test\\_%' order by 1")).all()
            bases: list[BaseDeCorrida] = []
            for nombre, megas in filas:
                run = nombres.run_de_base(nombre)
                if run is None:
                    continue
                marca = _marca_de(conn, nombre)
                if marca is None:
                    estado = "SIN_MARCA"
                elif marca["maquina"] != socket.gethostname():
                    estado = "AJENA"
                else:
                    estado = "VIVA" if lanzador_vivo(marca) else "HUERFANA"
                bases.append(BaseDeCorrida(
                    nombre=nombre, run=run, estado=estado, pid=int(marca["pid"]) if marca else None,
                    maquina=marca["maquina"] if marca else None, creado=marca["creado"] if marca else None,
                    megas=int(megas), conexiones=_conexiones(conn, nombre)))
            return bases
    finally:
        admin.dispose()


def procesos_de(run_id: str) -> list[int]:
    """Los procesos de esta máquina que una corrida arrancó: llevan su identificador en el entorno."""
    senal = f"KONTROL_E2E_RUN_ID={run_id}".encode()
    hallados: list[int] = []
    for carpeta in Path("/proc").iterdir():
        if not carpeta.name.isdigit() or int(carpeta.name) == os.getpid():
            continue
        try:
            variables = (carpeta / "environ").read_bytes().split(b"\0")
        except OSError:
            continue
        if senal in variables:
            hallados.append(int(carpeta.name))
    return sorted(hallados)


def detener_procesos(run_id: str, *, gracia: float = 10.0) -> int:
    """Detiene lo que quedó en marcha de una corrida muerta. Devuelve cuántos procesos eran."""
    procesos = procesos_de(run_id)
    for senal in (signal.SIGTERM, signal.SIGKILL):
        for pid in procesos_de(run_id):
            try:
                os.kill(pid, senal)
            except ProcessLookupError:
                pass
        limite = time.monotonic() + gracia
        while procesos_de(run_id) and time.monotonic() < limite:
            time.sleep(0.2)
        if not procesos_de(run_id):
            break
    return len(procesos)


def purgar(servidor: Servidor, *, confirmar: bool, solo: str | None = None,
           entorno: Mapping[str, str] | None = None, estado: Path | None = None,
           ) -> list[tuple[BaseDeCorrida, str]]:
    """Elimina las bases huérfanas. Sin `confirmar` solo dice cuáles eliminaría.

    Nunca toca la base de una corrida viva, la de otra máquina ni una sin la marca del arnés.
    De una huérfana se detiene primero lo que su corrida dejó en marcha, y con la base se va
    su estado efímero.
    """
    resultado: list[tuple[BaseDeCorrida, str]] = []
    for base in listar_bases(servidor):
        if solo is not None and base.nombre != solo:
            continue
        if base.estado != "HUERFANA":
            resultado.append((base, "CONSERVADA"))
        elif not confirmar:
            resultado.append((base, "PENDIENTE"))
        else:
            detener_procesos(base.run)
            soltar_base(servidor, base.nombre, entorno=entorno, espera=2.0)
            if estado is not None:
                shutil.rmtree(estado / base.run, ignore_errors=True)
            resultado.append((base, "ELIMINADA"))
    return resultado


# --------------------------------------------------------------------------- #
# Huella de las bases que no se tocan
# --------------------------------------------------------------------------- #
def huella(servidor: Servidor, bases: list[str]) -> dict[str, dict[str, Any] | None]:
    """Sesiones y clientes conectados a cada base, leídos sin conectarse a la base medida.

    La huella prueba únicamente la actividad de clientes: ignora tup_*, xact_* y el
    mantenimiento interno de PostgreSQL (autovacuum/autoanalyze), que no mueven sessions
    ni generan filas en pg_stat_activity con backend_type 'client backend'.
    """
    nombre_admin = make_url(servidor.admin_url).database
    for base in bases:
        if base == nombre_admin:
            raise CicloDeBaseRoto(f"la huella no puede medir la base desde la que observa: {nombre_admin}")

    admin = motor_administrativo(servidor)
    try:
        with admin.connect() as conn:
            conn.execute(text("select pg_stat_clear_snapshot()"))
            vivas = {
                fila.datname: (int(fila.oid), int(fila.sessions))
                for fila in conn.execute(
                    text(
                        "select d.datname, d.oid, s.sessions "
                        "from pg_database d "
                        "join pg_stat_database s on s.datid = d.oid "
                        "where d.datname = any(:bases)"
                    ),
                    {"bases": bases},
                )
            }
            clientes: dict[str, list[list]] = {base: [] for base in bases}
            for fila in conn.execute(
                text(
                    "select datname, pid, backend_start, state_change "
                    "from pg_stat_activity "
                    "where datname = any(:bases) "
                    "and backend_type = 'client backend' "
                    "and pid <> pg_backend_pid() "
                    "order by datname, pid"
                ),
                {"bases": bases},
            ):
                clientes[fila.datname].append(
                    [int(fila.pid), fila.backend_start.isoformat(),
                     fila.state_change.isoformat() if fila.state_change is not None else None]
                )
            return {
                base: (
                    {"oid": vivas[base][0], "sesiones": vivas[base][1], "clientes": clientes[base]}
                    if base in vivas else None
                )
                for base in bases
            }
    finally:
        admin.dispose()
