"""Residuos de la suite de pruebas en PostgreSQL: qué deja una corrida en la base de prueba.

Informa, sin modificar nada, de los schemas temporales (`t_<12 hex>`) que quedan, del
tamaño de la base, de las conexiones abiertas y del espacio libre del volumen de datos.
Es la medida con la que se comprueba que una corrida de `pytest` sobre PostgreSQL devuelve
la base como la encontró.

Con `--purgar` elimina los schemas temporales huérfanos —los de una corrida interrumpida a
la fuerza, que no llegó a limpiar—, y solo esos: los que llevan la marca que les pone el
arnés (`tests/conftest.py`), o, con `--sin-marca`, los anteriores a que existiera la marca.
Nunca toca `public` ni un schema que no tenga el nombre que genera el arnés, y se niega a
actuar si la base no es de prueba.

Uso:
    KONTROL_TEST_DB_URL=postgresql+psycopg2://postgres@localhost:55432/ktest \
    resources/backend/.venv/bin/python qa/pg-test-residuos.py [--json] [--purgar [--sin-marca]]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "resources" / "backend" / "tests"))

from pg_harness import (  # noqa: E402
    PATRON_DE_SCHEMA,
    PREFIJO_DE_APLICACION,
    PREFIJO_DE_MARCA,
    BaseNoEsDePrueba,
    exigir_base_de_prueba,
    motor_administrativo,
)
from sqlalchemy import text  # noqa: E402


def medir(url: str) -> dict:
    admin = motor_administrativo(url)
    try:
        with admin.connect() as c:
            base = c.execute(text("select current_database()")).scalar_one()
            filas = c.execute(text(
                "select n.nspname, obj_description(n.oid, 'pg_namespace') from pg_namespace n "
                "where n.nspname ~ :patron order by 1"), {"patron": PATRON_DE_SCHEMA.pattern}).all()
            conexiones = c.execute(text(
                "select coalesce(state, 'sin estado'), count(*) from pg_stat_activity "
                "where datname = current_database() and pid <> pg_backend_pid() "
                "and backend_type = 'client backend' group by 1 order by 1")).all()
            del_arnes = c.execute(text(
                "select count(*) from pg_stat_activity where datname = current_database() "
                "and application_name like :prefijo"), {"prefijo": PREFIJO_DE_APLICACION + "%"}).scalar_one()
            datos = c.execute(text("show data_directory")).scalar_one()
            return {
                "base": base,
                "tamano_bytes": c.execute(text("select pg_database_size(current_database())")).scalar_one(),
                "tamano": c.execute(text("select pg_size_pretty(pg_database_size(current_database()))")).scalar_one(),
                "relaciones": c.execute(text("select count(*) from pg_class")).scalar_one(),
                # El catálogo conserva su marca de agua tras crear y soltar miles de relaciones:
                # es espacio reutilizable, no fuga. Se mide aparte para no confundirlos.
                "catalogo": c.execute(text(
                    "select pg_size_pretty(sum(pg_total_relation_size(c.oid))) from pg_class c "
                    "join pg_namespace n on n.oid = c.relnamespace "
                    "where n.nspname = 'pg_catalog' and c.relkind = 'r'")).scalar_one(),
                "schemas_temporales": [n for n, _ in filas],
                "con_marca": [n for n, marca in filas if (marca or "").startswith(PREFIJO_DE_MARCA)],
                "conexiones": {estado: n for estado, n in conexiones},
                "conexiones_del_arnes": del_arnes,
                "max_connections": int(c.execute(text("show max_connections")).scalar_one()),
                "libre_en_el_volumen_mb": shutil.disk_usage(datos).free // (1024 * 1024) if Path(datos).exists() else None,
            }
    finally:
        admin.dispose()


def purgar(url: str, *, sin_marca: bool) -> list[str]:
    exigir_base_de_prueba(url)
    admin = motor_administrativo(url)
    eliminados: list[str] = []
    try:
        with admin.connect() as c:
            filas = c.execute(text(
                "select n.nspname, obj_description(n.oid, 'pg_namespace') from pg_namespace n "
                "where n.nspname ~ :patron order by 1"), {"patron": PATRON_DE_SCHEMA.pattern}).all()
            for nombre, marca in filas:
                marcado = (marca or "").startswith(PREFIJO_DE_MARCA)
                if not (marcado or sin_marca) or not PATRON_DE_SCHEMA.fullmatch(nombre):
                    continue
                # Quien siga conectado a ese schema es una corrida viva: no se le quita el suelo.
                vivos = c.execute(text(
                    "select count(*) from pg_stat_activity where application_name = :app"),
                    {"app": PREFIJO_DE_APLICACION + nombre}).scalar_one()
                if vivos:
                    continue
                c.execute(text(f'DROP SCHEMA "{nombre}" CASCADE'))
                eliminados.append(nombre)
    finally:
        admin.dispose()
    return eliminados


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", action="store_true", help="salida en JSON, para comparar corridas")
    parser.add_argument("--purgar", action="store_true", help="elimina los schemas temporales huérfanos que llevan la marca del arnés")
    parser.add_argument("--sin-marca", action="store_true", help="con --purgar, incluye los schemas temporales sin marca (anteriores al arnés actual)")
    args = parser.parse_args()

    url = os.environ.get("KONTROL_TEST_DB_URL")
    if not url or not url.startswith("postgresql"):
        print("KONTROL_TEST_DB_URL no apunta a PostgreSQL: no hay nada que medir.")
        return 2
    if args.purgar:
        try:
            eliminados = purgar(url, sin_marca=args.sin_marca)
        except BaseNoEsDePrueba as e:
            print(f"NO SE PURGA: {e}")
            return 3
        print(f"schemas huérfanos eliminados: {len(eliminados)}")

    m = medir(url)
    if args.json:
        print(json.dumps(m, ensure_ascii=False))
        return 0
    print(f"base ......................... {m['base']}")
    print(f"tamaño ....................... {m['tamano']}")
    print(f"relaciones (pg_class) ........ {m['relaciones']}")
    print(f"de ello, catálogo ............ {m['catalogo']}")
    print(f"schemas temporales ........... {len(m['schemas_temporales'])} (con marca del arnés: {len(m['con_marca'])})")
    print(f"conexiones a la base ......... {sum(m['conexiones'].values())} {m['conexiones']} de {m['max_connections']}")
    print(f"conexiones del arnés ......... {m['conexiones_del_arnes']}")
    print(f"libre en el volumen de datos . {m['libre_en_el_volumen_mb']} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
