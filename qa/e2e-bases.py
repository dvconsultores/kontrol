"""Las bases de corrida E2E que hay en el servidor de QA, y la purga de las huérfanas.

Una corrida elimina su base al terminar. Si muere a la fuerza (`kill -9`, un apagón) no hay
quien limpie: la base, el backend y Vite pueden quedarse. Esta orden los enseña y, con
`purgar --confirmar`, los retira. Solo actúa sobre bases que cumplen entero el patrón
`kontrol_e2e_test_<run>`, llevan la marca del arnés y cuyo lanzador ya no existe en esta
máquina; la base de una corrida viva no se toca.

Uso:
    resources/backend/.venv/bin/python qa/e2e-bases.py listar
    resources/backend/.venv/bin/python qa/e2e-bases.py purgar              # dice qué eliminaría
    resources/backend/.venv/bin/python qa/e2e-bases.py purgar --confirmar
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import e2e_base  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("accion", choices=("listar", "purgar"))
    parser.add_argument("--confirmar", action="store_true", help="con purgar: elimina de verdad las huérfanas")
    parser.add_argument("--base", help="con purgar: solo esta, si es huérfana")
    args = parser.parse_args(argv)

    servidor = e2e_base.Servidor.del_entorno()
    if args.accion == "listar":
        bases = e2e_base.listar_bases(servidor)
        print(f"servidor {servidor.destino()} · bases de corrida: {len(bases)}")
        for b in bases:
            print(f"  {b.estado:<9} {b.nombre}  {b.megas} MB · conexiones {b.conexiones} · "
                  f"procesos {len(e2e_base.procesos_de(b.run))} · lanzador {b.pid} · creada {b.creado}")
        return 0

    estado = Path(os.environ.get("KONTROL_E2E_STATE_DIR", "/tmp/kontrol-e2e"))
    try:
        resultado = e2e_base.purgar(servidor, confirmar=args.confirmar, solo=args.base, estado=estado)
    except e2e_base.BaseNoEsE2E as error:
        print(f"NO SE PURGA: {error}")
        return 3
    for b, hecho in resultado:
        print(f"  {hecho:<10} {b.nombre}  ({b.estado})")
    pendientes = sum(1 for _, hecho in resultado if hecho == "PENDIENTE")
    if pendientes:
        print(f"{pendientes} base(s) huérfana(s): repita con --confirmar para eliminarlas")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
