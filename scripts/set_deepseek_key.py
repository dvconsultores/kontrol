#!/usr/bin/env python3
"""Configura, en local y fuera del repositorio, el MCP `deepseek` de KONTROL.

La entrada vive en `~/.claude.json`, bajo este proyecto. La clave se lee de la variable
`DEEPSEEK_API_KEY` o de un aviso oculto: nunca se imprime, nunca se escribe en el
repositorio y nunca se pega en un chat. `~/.claude.json` se respalda antes de escribir.
Reinicie Claude Code después.

Uso:
    python scripts/set_deepseek_key.py --status   # qué hay montado (sin mostrar la clave)
    python scripts/set_deepseek_key.py            # crea la entrada si falta y pide la clave
    python scripts/set_deepseek_key.py --check    # además la valida contra DeepSeek
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

CLAUDE_JSON = Path.home() / ".claude.json"
BACKUP_DIR = Path.home() / ".claude" / "backups"
DEFAULT_PROJECT = Path(__file__).resolve().parent.parent
SERVER_NAME = "deepseek"
PACKAGE = "@arikusi/deepseek-mcp-server"
MODELS_URL = "https://api.deepseek.com/models"


def npx_absoluto() -> str:
    """Ruta absoluta a `npx`. Claude Code lanzado desde VS Code no hereda el PATH de nvm,
    así que un `npx` a secas deja el MCP «not connected»."""
    ruta = shutil.which("npx")
    if not ruta:
        sys.exit("No se encuentra `npx`. Instale Node (nvm) antes de configurar el MCP.")
    return str(Path(ruta).resolve().parent / "npx")


def entrada_nueva() -> dict:
    npx = npx_absoluto()
    return {
        "type": "stdio",
        "command": npx,
        "args": ["-y", PACKAGE],
        "env": {
            "PATH": f"{Path(npx).parent}:/usr/local/bin:/usr/bin:/bin",
            "REQUEST_TIMEOUT": "120000",
        },
    }


def leer_clave() -> str:
    clave = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if clave:
        print("Se usa DEEPSEEK_API_KEY del entorno.")
        return clave
    clave = getpass.getpass("Clave de la API de DeepSeek (no se muestra): ").strip()
    if not clave:
        sys.exit("No se indicó ninguna clave; no se cambió nada.")
    return clave


def validar(clave: str) -> bool:
    peticion = urllib.request.Request(MODELS_URL, headers={"Authorization": f"Bearer {clave}"})
    try:
        with urllib.request.urlopen(peticion, timeout=20) as respuesta:
            modelos = [m.get("id") for m in json.load(respuesta).get("data", [])]
        print(f"DeepSeek aceptó la clave. Modelos: {', '.join(modelos)}")
        return True
    except urllib.error.HTTPError as e:
        print(f"DeepSeek rechazó la clave (HTTP {e.code}).")
    except urllib.error.URLError as e:
        print(f"No se pudo llegar a DeepSeek: {e.reason}")
    return False


def estado(datos: dict, proyecto: str) -> int:
    servidor = datos.get("projects", {}).get(proyecto, {}).get("mcpServers", {}).get(SERVER_NAME)
    print(f"proyecto .............. {proyecto}")
    print(f"registrado en Claude .. {'sí' if proyecto in datos.get('projects', {}) else 'no'}")
    print(f"entrada `{SERVER_NAME}` ..... {'sí' if servidor else 'NO'}")
    if servidor:
        orden = servidor.get("command", "")
        print(f"orden ................. {orden} {' '.join(servidor.get('args', []))}")
        print(f"la orden existe ....... {'sí' if Path(orden).exists() else 'NO'}")
        print(f"clave configurada ..... {'sí' if servidor.get('env', {}).get('DEEPSEEK_API_KEY') else 'NO'}")
    return 0 if servidor and servidor.get("env", {}).get("DEEPSEEK_API_KEY") else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT,
                        help=f"ruta del repositorio tal como la registra Claude Code (por defecto: {DEFAULT_PROJECT})")
    parser.add_argument("--check", action="store_true", help="valida la clave contra la API de DeepSeek")
    parser.add_argument("--status", action="store_true", help="solo informa del montaje; no escribe ni muestra la clave")
    args = parser.parse_args()
    proyecto = str(args.project.resolve())

    if not CLAUDE_JSON.exists():
        sys.exit(f"No existe {CLAUDE_JSON}. Arranque Claude Code una vez primero.")
    datos = json.loads(CLAUDE_JSON.read_text())

    if args.status:
        sys.exit(estado(datos, proyecto))

    servidores = datos.setdefault("projects", {}).setdefault(proyecto, {}).setdefault("mcpServers", {})
    creada = SERVER_NAME not in servidores
    servidor = servidores.setdefault(SERVER_NAME, entrada_nueva())

    clave = leer_clave()
    if args.check and not validar(clave):
        sys.exit("No se guardó la clave.")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    respaldo = BACKUP_DIR / f".claude.json.{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(CLAUDE_JSON, respaldo)

    servidor.setdefault("env", {})["DEEPSEEK_API_KEY"] = clave
    temporal = CLAUDE_JSON.with_suffix(".json.tmp")
    temporal.write_text(json.dumps(datos, indent=2))
    os.chmod(temporal, 0o600)
    os.replace(temporal, CLAUDE_JSON)

    print(f"{'Entrada creada y clave' if creada else 'Clave'} guardada para {proyecto}. Respaldo: {respaldo}")
    print("Reinicie Claude Code y compruebe con /mcp que `deepseek` aparece conectado.")


if __name__ == "__main__":
    main()
