"""OBS-CERT-GOV-01: runner canónico de integridad de Gobierno.

Ejecuta los controles de integridad versionados en los módulos hermanos
``qa/gobierno_integridad_org.py``, ``qa/gobierno_integridad_ctl.py``,
``qa/gobierno_integridad_tre.py`` y ``qa/gobierno_integridad_caja.py``.
Los controles ya no viven en el scratchpad; este runner es la vía oficial
para listarlos y ejecutarlos contra una base PostgreSQL.

Uso:
    python qa/gobierno_integridad.py [--db-url URL] [--grupo ORG|CTL|TRE|CAJA] [--listar] [--json]

Códigos de salida:
    0 — lista mostrada correctamente, o ejecución sin violaciones.
    1 — ejecución completada con al menos una violación.
    2 — no se pudo determinar la URL de base de datos y no se solicitó --listar.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

# Permitir importar los módulos hermanos del mismo directorio sin depender
# del directorio de trabajo actual.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import gobierno_integridad_caja as caja  # noqa: E402
import gobierno_integridad_ctl as ctl  # noqa: E402
import gobierno_integridad_org as org  # noqa: E402
import gobierno_integridad_tre as tre  # noqa: E402

GRUPO_ORG = org.GRUPO
GRUPO_CTL = ctl.GRUPO
GRUPO_TRE = tre.GRUPO
GRUPO_CAJA = caja.GRUPO

CLAVE_ORG = "ORG"
CLAVE_CTL = "CTL"
CLAVE_TRE = "TRE"
CLAVE_CAJA = "CAJA"

MODULOS_POR_CLAVE = {
    CLAVE_ORG: org,
    CLAVE_CTL: ctl,
    CLAVE_TRE: tre,
    CLAVE_CAJA: caja,
}


def controles() -> list[tuple[str, str, str, str]]:
    """Devuelve la lista completa de controles.

    Cada elemento es ``(grupo, id, descripción, sql)``. Los ``INFO`` de cada
    módulo no forman parte de esta lista.
    """

    resultado: list[tuple[str, str, str, str]] = []
    for grupo, modulo in (
        (GRUPO_ORG, org),
        (GRUPO_CTL, ctl),
        (GRUPO_TRE, tre),
        (GRUPO_CAJA, caja),
    ):
        for identificador, descripcion, sql in modulo.CHECKS:
            resultado.append((grupo, identificador, descripcion, sql))
    return resultado


def _crear_conexion(db_url: str) -> Connection:
    engine = create_engine(db_url)
    return engine.connect()


def ejecutar(conn: Connection, grupo: str | None = None) -> dict[str, Any]:
    """Ejecuta todos los controles usando la conexión dada.

    ``grupo`` es la clave corta ``"ORG"``, ``"CTL"``, ``"TRE"`` o ``"CAJA"`` (o
    ``None`` para todos).

    Devuelve un diccionario con la misma estructura que la salida JSON:
    ``{"info": {...}, "controles": [...], "total": int}``.
    """

    conn.execute(text("SET TRANSACTION READ ONLY"))

    info: dict[str, int] = {}
    for clave, modulo in MODULOS_POR_CLAVE.items():
        if grupo and clave != grupo:
            continue
        for etiqueta, sql in modulo.INFO.items():
            info[f"{modulo.GRUPO}.{etiqueta}"] = int(conn.execute(text(sql)).scalar_one())

    controles_resultado: list[dict[str, Any]] = []
    total_violaciones = 0

    for clave, modulo in MODULOS_POR_CLAVE.items():
        if grupo and clave != grupo:
            continue
        for identificador, descripcion, sql in modulo.CHECKS:
            error: str | None = None
            violaciones = 0
            try:
                with conn.begin_nested():
                    resultado = conn.execute(text(sql))
                    fila = resultado.fetchone()
                    if fila is not None:
                        violaciones = int(fila[0])
            except Exception as exc:  # noqa: BLE001 — informar y continuar
                error = type(exc).__name__
                violaciones = 1
            total_violaciones += violaciones
            controles_resultado.append(
                {
                    "id": identificador,
                    "grupo": modulo.GRUPO,
                    "descripcion": descripcion,
                    "violaciones": violaciones,
                    "error": error,
                }
            )

    return {
        "info": info,
        "controles": controles_resultado,
        "total": total_violaciones,
    }


def _obtener_url_db(args: argparse.Namespace) -> str | None:
    if args.db_url:
        return args.db_url
    return os.environ.get("KONTROL_SCAN_DB_URL")


def _listar(grupo: str | None) -> None:
    for clave, modulo in MODULOS_POR_CLAVE.items():
        if grupo and clave != grupo:
            continue
        for identificador, descripcion, _sql in modulo.CHECKS:
            print(f"{identificador}\t{modulo.GRUPO}\t{descripcion}")


def _imprimir_ejecucion(resultado: dict[str, Any], como_json: bool) -> None:
    for etiqueta, valor in resultado["info"].items():
        print(f"gobierno_integridad: {etiqueta}={valor}")

    for control in resultado["controles"]:
        if control["error"] is not None:
            print(
                f"gobierno_integridad: {control['id']} ERROR {control['error']}"
            )
        else:
            print(
                "gobierno_integridad: "
                f"{control['id']} {control['descripcion']}: "
                f"{control['violaciones']}"
            )

    print(f"gobierno_integridad: total violaciones={resultado['total']}")

    if como_json:
        print(json.dumps(resultado, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta los controles de integridad de Gobierno."
    )
    parser.add_argument("--db-url", help="URL de conexión a PostgreSQL.")
    parser.add_argument(
        "--grupo",
        choices=(CLAVE_ORG, CLAVE_CTL, CLAVE_TRE, CLAVE_CAJA),
        help="Ejecutar únicamente los controles del grupo indicado.",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Listar los controles sin conectar a la base de datos.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Añadir al final una representación JSON de la ejecución.",
    )
    args = parser.parse_args(argv)

    if args.listar:
        _listar(args.grupo)
        return 0

    db_url = _obtener_url_db(args)
    if db_url is None:
        print(
            "gobierno_integridad: no se ha indicado --db-url ni "
            "KONTROL_SCAN_DB_URL",
            file=sys.stderr,
        )
        return 2

    conn = _crear_conexion(db_url)
    try:
        resultado = ejecutar(conn, args.grupo)
    finally:
        conn.close()

    _imprimir_ejecucion(resultado, args.json)
    return 1 if resultado["total"] > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
