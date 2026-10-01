"""TEST-SCHEMAS-PG-SIN-LIMPIEZA · reproducción: qué deja la suite en PostgreSQL, corrida a corrida.

Ejecuta el mismo subconjunto de pruebas varias veces contra la base de prueba y mide, antes
y después de cada corrida y mientras dura, los schemas temporales, el tamaño de la base y
las conexiones. Una infraestructura limpia vuelve cada vez al mismo punto de partida; una
que pierde recursos crece en cada vuelta.

Uso:
    KONTROL_TEST_DB_URL=postgresql+psycopg2://postgres@localhost:55432/ktest \
    resources/backend/.venv/bin/python qa/repro-pg-test-residuos.py [--repeticiones 3] tests/test_fiscal.py ...
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BACKEND = RAIZ / "resources" / "backend"

_spec = importlib.util.spec_from_file_location("residuos", RAIZ / "qa" / "pg-test-residuos.py")
residuos = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(residuos)


def linea(etiqueta: str, m: dict) -> str:
    return (f"{etiqueta:<22} schemas temporales={len(m['schemas_temporales']):>4} · tamaño={m['tamano']:>8} · "
            f"(catálogo {m['catalogo']:>7}) · relaciones={m['relaciones']:>6} · conexiones={sum(m['conexiones'].values()):>3} · "
            f"libre={m['libre_en_el_volumen_mb']} MB")


def muestrear(url: str, pico: dict, fin: threading.Event) -> None:
    """Mientras dura la corrida, anota el máximo de conexiones y de schemas temporales."""
    while not fin.is_set():
        try:
            m = residuos.medir(url)
            pico["conexiones"] = max(pico["conexiones"], sum(m["conexiones"].values()))
            pico["schemas"] = max(pico["schemas"], len(m["schemas_temporales"]))
            pico["tamano_mb"] = max(pico["tamano_mb"], m["tamano_bytes"] // (1024 * 1024))
            pico["libre_min_mb"] = min(pico["libre_min_mb"], m["libre_en_el_volumen_mb"] or pico["libre_min_mb"])
        except Exception:  # noqa: BLE001, S110 - una muestra perdida no invalida la medida
            pass
        fin.wait(0.5)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repeticiones", type=int, default=3)
    parser.add_argument("--salida", type=Path, help="guarda la salida de pytest de cada corrida en FICHERO.<n>")
    parser.add_argument("pruebas", nargs="+", help="rutas de pytest, relativas a resources/backend")
    args = parser.parse_args()
    url = os.environ["KONTROL_TEST_DB_URL"]

    print(f"subconjunto: {' '.join(args.pruebas)} · repeticiones: {args.repeticiones}")
    inicial = residuos.medir(url)
    print(linea("antes", inicial))
    for vuelta in range(1, args.repeticiones + 1):
        pico = {"conexiones": 0, "schemas": 0, "tamano_mb": 0, "libre_min_mb": 10**9}
        fin = threading.Event()
        hilo = threading.Thread(target=muestrear, args=(url, pico, fin), daemon=True)
        hilo.start()
        t0 = time.time()
        r = subprocess.run([str(BACKEND / ".venv/bin/python"), "-m", "pytest", *args.pruebas, "-p", "no:cacheprovider"],
                           cwd=BACKEND, capture_output=True, text=True)
        duracion = time.time() - t0
        fin.set()
        hilo.join()
        if args.salida:
            Path(f"{args.salida}.{vuelta}").write_text(r.stdout)
        resumen = (r.stdout.strip().splitlines() or ["(sin salida)"])[-1]
        print(f"corrida {vuelta}: {resumen} · {duracion:.0f} s · pico de conexiones={pico['conexiones']} · "
              f"pico de schemas={pico['schemas']} · pico de tamaño={pico['tamano_mb']} MB · "
              f"mínimo libre={pico['libre_min_mb']} MB", flush=True)
        print(linea(f"tras la corrida {vuelta}", residuos.medir(url)), flush=True)
    final = residuos.medir(url)
    print(f"\nRESIDUO: schemas huérfanos={len(final['schemas_temporales']) - len(inicial['schemas_temporales'])} · "
          f"crecimiento={(final['tamano_bytes'] - inicial['tamano_bytes']) / 1024 / 1024:.0f} MB · "
          f"conexiones residuales={sum(final['conexiones'].values()) - sum(inicial['conexiones'].values())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
