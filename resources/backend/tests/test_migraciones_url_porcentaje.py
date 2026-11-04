"""MIG · Alembic acepta una URL de base con «%» (MIGRACIONES-URL-CON-PORCENTAJE; dueña 052).

`alembic/env.py` (cliente) y `central_authority/alembic/env.py` pasaban `KONTROL_DB_URL` /
`KONTROL_CENTRAL_DB_URL` por `config.set_main_option("sqlalchemy.url", …)`: eso es `configparser`, que
interpreta «%» como interpolación, así que una credencial codificada (`%40`, `%23`, `%25`) rompía
`alembic upgrade head` —lo primero que hace el contenedor— antes de conectar. Ahora la URL va directa a
SQLAlchemy, como en el runtime. Aquí se prueba: la frontera (MIG-01), que la URL que recibe SQLAlchemy es
**exactamente** la lógica (sin doble escape, con su query), que la migración real llega a la cabeza en
ambos `env.py`, que el camino canónico por subproceso no imprime credenciales, y el contrato de los
entrypoints. El PostgreSQL de QA autentica por `trust`: aquí se certifica el parseo y la URL lógica,
no la autenticación con una clave con «%».
"""
from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
import sqlalchemy
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

BACKEND = Path(__file__).resolve().parents[1]
RAIZ = BACKEND.parents[1]
PG = os.environ.get("KONTROL_TEST_DB_URL", "")
#: Cabeza declarada del árbol del cliente y de la Central: una revisión nueva se declara aquí, no entra en silencio.
CABEZA_CLIENTE = "0070_gov_ctl06_hallazgos"
CABEZA_CENTRAL = "0002_cla_sync_auth"
#: Credenciales sintéticas, codificadas: `p@ss` → `p%40ss`, `p#ss` → `p%23ss`, `p%ss` → `p%25ss`.
MATRIZ = {
    "U1_sin_porcentaje": ("postgres", None, ""),
    "U2_arroba": ("postgres", "p%40ss", ""),
    "U3_almohadilla": ("postgres", "p%23ss", ""),
    "U4_porcentaje": ("postgres", "p%25ss%25w", ""),
    "U5_query": ("postgres", "p%40ss", "?application_name=mig%20pct&connect_timeout=5"),
    "U6_usuario_codificado": ("po%73tgres", "p%25w", ""),
}
pg_only = pytest.mark.skipif("postgresql" not in PG, reason="la migración real se certifica sobre PostgreSQL")


def _url(nombre: str, usuario: str, clave: str | None, query: str) -> str:
    base = make_url(PG)
    cred = usuario if clave is None else f"{usuario}:{clave}"
    return f"postgresql+psycopg2://{cred}@{base.host}:{base.port}/{nombre}{query}"


@pytest.fixture
def base_nueva() -> Iterator[str]:
    """Una base vacía por prueba, creada y eliminada con el motor administrativo (antes de parchear nada)."""
    admin = create_engine(make_url(PG).set(database="postgres").render_as_string(hide_password=False),
                          isolation_level="AUTOCOMMIT")
    nombre = f"kontrol_test_migpct_{os.getpid()}_{abs(hash(os.urandom(4))) % 100000}"
    with admin.connect() as cx:
        cx.execute(text(f'CREATE DATABASE "{nombre}" ENCODING \'UTF8\''))
    try:
        yield nombre
    finally:
        with admin.connect() as cx:
            cx.execute(text(f'DROP DATABASE IF EXISTS "{nombre}"'))
        admin.dispose()


def _version(url: str, tabla: str) -> list[str]:
    motor = create_engine(url)
    try:
        with motor.connect() as cx:
            return sorted(cx.execute(text(f"select version_num from {tabla}")).scalars().all())
    finally:
        motor.dispose()


def _migrar_en_proceso(monkeypatch: pytest.MonkeyPatch, *, ini: str, variable: str, url: str, limpiar_cache) -> list[str]:
    """Corre `alembic upgrade head` por el `env.py` real y devuelve las URL que llegaron a `create_engine`."""
    original = sqlalchemy.create_engine
    recibidas: list[str] = []

    def registrador(u, *a, **k):
        recibidas.append(u if isinstance(u, str) else u.render_as_string(hide_password=False))
        return original(u, *a, **k)

    monkeypatch.setenv(variable, url)
    limpiar_cache()
    monkeypatch.setattr(sqlalchemy, "create_engine", registrador)
    try:
        command.upgrade(Config(str(BACKEND / ini)), "head")
    finally:
        monkeypatch.setattr(sqlalchemy, "create_engine", original)
        limpiar_cache()
    return recibidas


def _cache_cliente() -> None:
    from app.core.config import get_settings

    get_settings.cache_clear()


def _cache_central() -> None:
    from central_authority.config import get_settings

    get_settings.cache_clear()


# ----------------------------------------------------------------------------- MIG-01 · la frontera
def test_mig_01_configparser_rechaza_una_url_con_porcentaje_y_los_env_ya_no_pasan_por_ahi():
    cfg = Config(str(BACKEND / "alembic.ini"))
    with pytest.raises(ValueError, match="invalid interpolation syntax"):
        cfg.set_main_option("sqlalchemy.url", "postgresql+psycopg2://postgres:p%40ss@localhost:5432/x")
    for env in ("alembic/env.py", "central_authority/alembic/env.py"):
        texto = (BACKEND / env).read_text()
        assert 'set_main_option("sqlalchemy.url"' not in texto, f"{env} vuelve a meter la URL en configparser"
        assert "engine_from_config" not in texto, f"{env} vuelve a leer la URL desde configparser"
        assert "create_engine(settings.db_url" in texto, f"{env} no construye el motor con la URL lógica"


# ----------------------------------------------------------------------------- MIG-02…06/09 · matriz, cliente
@pg_only
@pytest.mark.parametrize("caso", list(MATRIZ))
def test_mig_02_06_la_url_logica_llega_intacta_y_la_base_queda_en_la_cabeza(caso: str, base_nueva: str, monkeypatch):
    usuario, clave, query = MATRIZ[caso]
    url = _url(base_nueva, usuario, clave, query)
    recibidas = _migrar_en_proceso(monkeypatch, ini="alembic.ini", variable="KONTROL_DB_URL", url=url, limpiar_cache=_cache_cliente)
    assert len(recibidas) == 1, recibidas
    assert make_url(recibidas[0]) == make_url(url), "la URL que vio SQLAlchemy no es la lógica (doble escape o query perdida)"
    assert make_url(recibidas[0]).query == make_url(url).query
    assert _version(url, "alembic_version") == [CABEZA_CLIENTE]


# ----------------------------------------------------------------------------- MIG-07 · control directo
def test_mig_07_la_misma_url_es_valida_para_sqlalchemy_y_el_runtime():
    u = make_url("postgresql+psycopg2://po%73tgres:p%25ss%25w@localhost:5432/kontrol?application_name=mig%20pct")
    assert (u.username, u.password, u.database, dict(u.query)) == ("postgres", "p%ss%w", "kontrol", {"application_name": "mig pct"})


# ----------------------------------------------------------------------------- MIG-08/13 · camino canónico por subproceso, sin credenciales en la salida
@pg_only
def test_mig_08_13_el_camino_canonico_migra_con_porcentaje_y_no_imprime_la_url(base_nueva: str):
    url = _url(base_nueva, "postgres", "p%25ss%40w", "?application_name=mig%20pct")
    env = {k: v for k, v in os.environ.items() if k not in ("KONTROL_DB_URL", "KONTROL_TEST_DB_URL")}
    r = subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env={**env, "KONTROL_DB_URL": url},
                       capture_output=True, text=True, check=False)
    assert r.returncode == 0, r.stdout[-800:] + r.stderr[-800:]
    salida = r.stdout + r.stderr
    for fragmento in ("p%25ss%40w", "p%ss@w", "postgres:p", url):
        assert fragmento not in salida, "la salida de la migración lleva credenciales"
    assert _version(url, "alembic_version") == [CABEZA_CLIENTE]


# ----------------------------------------------------------------------------- MIG-09/10/11 · cabeza declarada
def test_mig_09_10_la_cabeza_del_arbol_es_la_declarada_en_ambos_entornos():
    for ini, raiz, cabeza in (("alembic.ini", "alembic", CABEZA_CLIENTE), ("central_authority/alembic.ini", "central_authority/alembic", CABEZA_CENTRAL)):
        cfg = Config(str(BACKEND / ini))
        cfg.set_main_option("script_location", str(BACKEND / raiz))
        assert ScriptDirectory.from_config(cfg).get_heads() == [cabeza], f"{ini}: una revisión nueva se declara aquí"


# ----------------------------------------------------------------------------- MIG-14 · entrypoints: migrar, luego arrancar; sin reintentos ni esperas
@pytest.mark.parametrize("ruta", ["scripts/entrypoint.sh", "central_authority/entrypoint.sh"])
def test_mig_14_el_entrypoint_migra_antes_de_arrancar_y_no_reintenta(ruta: str):
    lineas = (BACKEND / ruta).read_text().splitlines()
    migra = next(i for i, linea in enumerate(lineas) if linea.strip().startswith("alembic") and "upgrade head" in linea)
    arranca = next(i for i, linea in enumerate(lineas) if linea.strip() == 'exec "$@"')
    assert migra < arranca, f"{ruta}: arranca antes de migrar"
    assert not any(p in linea for linea in lineas for p in ("sleep", "retry", "until ", "while ")), f"{ruta}: reintentos o esperas"


# ----------------------------------------------------------------------------- MIG-17 · la Central, misma raíz, mismo arreglo
@pg_only
@pytest.mark.parametrize("caso", ["U1_sin_porcentaje", "U4_porcentaje", "U5_query"])
def test_mig_17_la_central_migra_con_porcentaje_y_la_url_llega_intacta(caso: str, base_nueva: str, monkeypatch):
    usuario, clave, query = MATRIZ[caso]
    url = _url(base_nueva, usuario, clave, query)
    recibidas = _migrar_en_proceso(monkeypatch, ini="central_authority/alembic.ini", variable="KONTROL_CENTRAL_DB_URL", url=url, limpiar_cache=_cache_central)
    assert len(recibidas) == 1 and make_url(recibidas[0]) == make_url(url), recibidas
    assert _version(url, "cla_alembic_version") == [CABEZA_CENTRAL]
