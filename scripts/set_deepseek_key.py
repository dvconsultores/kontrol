#!/usr/bin/env python3
"""Configura, en local y fuera del repositorio, el MCP `deepseek` de KONTROL.

La entrada vive en `~/.claude.json`, bajo este proyecto, con el servidor fijado a una
versión exacta. La clave nunca se imprime, nunca se escribe en el repositorio y nunca se
pega en un chat. Se toma, por este orden, de:

  1. la variable de entorno `DEEPSEEK_API_KEY`;
  2. `--reuse-from RUTA`: la entrada `deepseek` que otro proyecto ya tiene en este mismo
     `~/.claude.json` (se copia en memoria, sin mostrarla);
  3. la entrada de este proyecto, si ya tenía clave (se conserva);
  4. un aviso oculto.

`~/.claude.json` se respalda antes de escribir. Reinicie Claude Code después.

Uso:
    python scripts/set_deepseek_key.py --status          # qué hay montado (sin mostrar la clave)
    python scripts/set_deepseek_key.py                    # crea o actualiza la entrada
    python scripts/set_deepseek_key.py --check            # además valida la clave contra DeepSeek
    python scripts/set_deepseek_key.py --reuse-from RUTA  # reutiliza la clave de otro proyecto
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
# Versión verificada. `npx -y` sin versión traería en cada arranque lo último publicado
# de un paquete que recibe la clave y el código delegado; se sube a mano, tras probarla.
PACKAGE_VERSION = "2.3.0"
PACKAGE_SPEC = f"{PACKAGE}@{PACKAGE_VERSION}"
KEY_NAME = "DEEPSEEK_API_KEY"
MODELS_URL = "https://api.deepseek.com/models"


def npx_absoluto() -> str:
    """Ruta absoluta a `npx`. Claude Code lanzado desde VS Code no hereda el PATH de nvm,
    así que un `npx` a secas deja el MCP «not connected»."""
    ruta = shutil.which("npx")
    if not ruta:
        sys.exit("No se encuentra `npx`. Instale Node (nvm) antes de configurar el MCP.")
    # Sin resolver enlaces: `bin/npx` apunta a `lib/node_modules/npm/bin/npx-cli.js`, y
    # desde ese directorio npx no encuentra `node`.
    return os.path.abspath(ruta)


def entorno_base(npx: str) -> dict:
    return {
        "PATH": f"{Path(npx).parent}:/usr/local/bin:/usr/bin:/bin",
        "REQUEST_TIMEOUT": "120000",
        # Sin cambio silencioso de modelo: qué modelo ejecuta una tarea lo decide Claude.
        "FALLBACK_ENABLED": "false",
    }


def asegurar_entrada(servidores: dict) -> bool:
    """Crea la entrada o la lleva a la versión fijada. Conserva la clave y cualquier
    variable que ya tuviera. Devuelve si la entrada es nueva."""
    npx = npx_absoluto()
    creada = SERVER_NAME not in servidores
    servidor = servidores.setdefault(SERVER_NAME, {})
    servidor["type"] = "stdio"
    servidor["command"] = npx
    servidor["args"] = ["-y", PACKAGE_SPEC]
    servidor["env"] = {**entorno_base(npx), **servidor.get("env", {})}
    return creada


def clave_de_otro_proyecto(datos: dict, origen: str) -> str:
    servidor = datos.get("projects", {}).get(origen, {}).get("mcpServers", {}).get(SERVER_NAME, {})
    clave = servidor.get("env", {}).get(KEY_NAME, "").strip()
    if not clave:
        sys.exit(f"{origen} no tiene una entrada `{SERVER_NAME}` con clave; no se cambió nada.")
    return clave


def resolver_clave(datos: dict, servidor: dict, origen: str | None) -> tuple[str, str]:
    """Devuelve la clave y de dónde salió. Nunca la imprime."""
    clave = os.environ.get(KEY_NAME, "").strip()
    if clave:
        return clave, f"la variable {KEY_NAME} del entorno"
    if origen:
        return clave_de_otro_proyecto(datos, origen), f"la entrada local de {origen}"
    clave = servidor.get("env", {}).get(KEY_NAME, "").strip()
    if clave:
        return clave, "la entrada que este proyecto ya tenía"
    clave = getpass.getpass("Clave de la API de DeepSeek (no se muestra): ").strip()
    if not clave:
        sys.exit("No se indicó ninguna clave; no se cambió nada.")
    return clave, "el aviso oculto"


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
    if not servidor:
        return 1
    orden = servidor.get("command", "")
    args = servidor.get("args", [])
    fijada = PACKAGE_SPEC in args
    con_clave = bool(servidor.get("env", {}).get(KEY_NAME))
    print(f"orden ................. {orden} {' '.join(args)}")
    print(f"la orden existe ....... {'sí' if Path(orden).exists() else 'NO'}")
    print(f"versión fijada ........ {'sí, ' + PACKAGE_VERSION if fijada else 'NO (se espera ' + PACKAGE_SPEC + ')'}")
    print(f"clave configurada ..... {'sí' if con_clave else 'NO'}")
    return 0 if con_clave and fijada and Path(orden).exists() else 1


def guardar(datos: dict) -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    respaldo = BACKUP_DIR / f".claude.json.{datetime.now():%Y%m%d-%H%M%S}"
    shutil.copy2(CLAUDE_JSON, respaldo)
    os.chmod(respaldo, 0o600)
    temporal = CLAUDE_JSON.with_suffix(".json.tmp")
    temporal.write_text(json.dumps(datos, indent=2))
    os.chmod(temporal, 0o600)
    os.replace(temporal, CLAUDE_JSON)
    return respaldo


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", type=Path, default=DEFAULT_PROJECT,
                        help=f"ruta del repositorio tal como la registra Claude Code (por defecto: {DEFAULT_PROJECT})")
    parser.add_argument("--reuse-from", type=Path, metavar="RUTA",
                        help="reutiliza la clave de la entrada `deepseek` que ese otro proyecto ya tiene en ~/.claude.json")
    parser.add_argument("--check", action="store_true", help="valida la clave contra la API de DeepSeek")
    parser.add_argument("--status", action="store_true", help="solo informa del montaje; no escribe ni muestra la clave")
    args = parser.parse_args(argv)
    proyecto = str(args.project.resolve())

    if not CLAUDE_JSON.exists():
        sys.exit(f"No existe {CLAUDE_JSON}. Arranque Claude Code una vez primero.")
    datos = json.loads(CLAUDE_JSON.read_text())

    if args.status:
        sys.exit(estado(datos, proyecto))

    servidores = datos.setdefault("projects", {}).setdefault(proyecto, {}).setdefault("mcpServers", {})
    creada = asegurar_entrada(servidores)
    servidor = servidores[SERVER_NAME]

    origen = str(args.reuse_from.resolve()) if args.reuse_from else None
    clave, procedencia = resolver_clave(datos, servidor, origen)
    print(f"Se usa la clave de {procedencia}.")
    if args.check and not validar(clave):
        sys.exit("No se guardó nada.")

    servidor["env"][KEY_NAME] = clave
    respaldo = guardar(datos)

    print(f"Entrada {'creada' if creada else 'actualizada'} para {proyecto}: {PACKAGE_SPEC}. Respaldo: {respaldo}")
    print("Reinicie Claude Code y compruebe con /mcp que `deepseek` aparece conectado.")


if __name__ == "__main__":
    main()
