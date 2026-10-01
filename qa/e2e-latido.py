"""Latido del backend de QA: cuánto tarda en contestar una petición trivial mientras corre otra cosa.

Un backend de un solo proceso atiende de una en una lo que es trabajo de CPU. Si una
petición pesada lo ocupa, todas las demás esperan, también las triviales. Este guion pide
`/health/ready` cada medio segundo mientras dura la orden que se le pasa —por ejemplo una
corrida E2E— y dice cuánto llegó a tardar: es la medida de la saturación.

Uso:
    resources/backend/.venv/bin/python qa/e2e-latido.py -- <orden> [args…]
"""
from __future__ import annotations

import os
import statistics
import subprocess
import sys
import threading
import time
import urllib.request

API = os.environ.get("KONTROL_E2E_API", "http://127.0.0.1:8000/api/v1")


def latir(tiempos: list[float], fallos: list[str], fin: threading.Event) -> None:
    while not fin.is_set():
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(f"{API}/health/ready", timeout=60) as r:
                r.read()
            tiempos.append((time.perf_counter() - t0) * 1000)
        except Exception as e:  # noqa: BLE001 - un latido perdido también es un dato
            fallos.append(type(e).__name__)
        fin.wait(0.5)


def main() -> int:
    orden = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not orden:
        print(__doc__)
        return 2
    tiempos: list[float] = []
    fallos: list[str] = []
    fin = threading.Event()
    hilo = threading.Thread(target=latir, args=(tiempos, fallos, fin), daemon=True)
    hilo.start()
    codigo = subprocess.run(orden).returncode
    fin.set()
    hilo.join()
    if tiempos:
        ordenados = sorted(tiempos)
        p95 = ordenados[int(len(ordenados) * 0.95) - 1]
        print(f"\nLATIDO /health/ready: {len(tiempos)} muestras · mediana {statistics.median(tiempos):.0f} ms · "
              f"p95 {p95:.0f} ms · máximo {max(tiempos):.0f} ms · por encima de 1 s: "
              f"{sum(t > 1000 for t in tiempos)} · perdidos: {len(fallos)}")
    return codigo


if __name__ == "__main__":
    sys.exit(main())
