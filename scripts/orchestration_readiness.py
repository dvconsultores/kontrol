#!/usr/bin/env python3
"""Audita el montaje Claude + DeepSeek de KONTROL sin leer ni mostrar ninguna clave.

De la clave solo se comprueba que exista; su valor no se usa, no se copia y no se imprime.
`--handshake` arranca el servidor MCP fijado con una clave de relleno y sin prueba de
conexión: sirve para ver qué herramientas y modelos declara de verdad, no llama a DeepSeek.

Uso:
    python scripts/orchestration_readiness.py               # comprobaciones estáticas y locales
    python scripts/orchestration_readiness.py --handshake   # además, arranque real del servidor fijado
"""
from __future__ import annotations

import argparse
import json
import os
import re
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import set_deepseek_key as montaje  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
EJECUTOR = ".claude/agents/deepseek-executor.md"
COORDINADOR = ".claude/agents/spec-kit-coordinator.md"
CLAUDE_MD = ".claude/CLAUDE.md"
POLITICA = "docs/governance/ai-orchestration-policy.md"
TOPE_DE_REINTENTOS = 2
HERRAMIENTA_MCP = "deepseek_chat"
HERRAMIENTA_CLAUDE = f"mcp__{montaje.SERVER_NAME}__{HERRAMIENTA_MCP}"
MODELOS = ("deepseek-v4-flash", "deepseek-v4-pro")
HERRAMIENTAS_PROHIBIDAS_AL_EJECUTOR = {"Edit", "Write", "Bash", "NotebookEdit", "Agent", "Task"}
DENY_MINIMO = {"Read(./.env)", "Read(./.env.local)", "Read(./.env.production)", "Read(./resources/backend/.env)"}
# Forma de una clave de DeepSeek o de una asignación con valor; el nombre a secas es legítimo.
CLAVE_INCRUSTADA = re.compile(
    r"sk-[0-9a-fA-F]{32}\b|DEEPSEEK_API_KEY[\"']?\s*[=:]\s*[\"']?(?!\$|<|x{3}|\.{3})[A-Za-z0-9_-]{20,}"
)
CLAVE_DE_RELLENO = "sin-clave-solo-arranque"


def frontmatter(texto: str) -> dict[str, str]:
    partes = texto.split("---", 2)
    if len(partes) < 3:
        return {}
    campos = {}
    for linea in partes[1].strip().splitlines():
        nombre, _, valor = linea.partition(":")
        campos[nombre.strip()] = valor.strip()
    return campos


def leer(repo: Path, relativa: str) -> str:
    ruta = repo / relativa
    return ruta.read_text() if ruta.exists() else ""


def comprobar_claude_md(repo: Path) -> tuple[bool, str]:
    texto = leer(repo, CLAUDE_MD)
    exigido = ["Solo `develop`", "EGRESS_CHECK", "AUDIT_REJECT", "SEARCH/REPLACE", "CLAUDE_ONLY", "DEEPSEEK_ELIGIBLE"]
    faltan = [e for e in exigido if e not in texto]
    return (not faltan and bool(texto)), "completo" if texto and not faltan else f"falta: {faltan or 'el fichero'}"


def comprobar_ejecutor(repo: Path) -> tuple[bool, str]:
    campos = frontmatter(leer(repo, EJECUTOR))
    herramientas = {h.strip() for h in campos.get("tools", "").split(",") if h.strip()}
    if not herramientas:
        return False, "sin lista `tools`: heredaría todas las herramientas"
    prohibidas = sorted(herramientas & HERRAMIENTAS_PROHIBIDAS_AL_EJECUTOR)
    if prohibidas:
        return False, f"puede editar o ejecutar: {prohibidas}"
    if HERRAMIENTA_CLAUDE not in herramientas:
        return False, f"no declara {HERRAMIENTA_CLAUDE}"
    return True, f"solo propone: {sorted(herramientas)}"


def comprobar_coordinador(repo: Path) -> tuple[bool, str]:
    texto = leer(repo, COORDINADOR)
    exigido = ["CLAUDE_ONLY", "DEEPSEEK_ELIGIBLE", "MATERIAL_DECISION_REQUIRED", "No ejecutes `/speckit-implement`"]
    faltan = [e for e in exigido if e not in texto]
    return (not faltan and bool(texto)), "clasifica y no implementa" if texto and not faltan else f"falta: {faltan or 'el fichero'}"


def comprobar_tope_de_reintentos(repo: Path) -> tuple[bool, str]:
    hallado = {}
    for relativa in (CLAUDE_MD, EJECUTOR, COORDINADOR, POLITICA):
        valores = {int(v) for v in re.findall(r"RETRY_MAX:\s*(\d+)", leer(repo, relativa))}
        hallado[relativa] = valores
    malos = {r: sorted(v) for r, v in hallado.items() if v != {TOPE_DE_REINTENTOS}}
    return (not malos), f"RETRY_MAX: {TOPE_DE_REINTENTOS} en los cuatro documentos" if not malos else f"discrepa o falta en: {malos}"


def comprobar_modelos_documentados(repo: Path) -> tuple[bool, str]:
    texto = leer(repo, EJECUTOR)
    faltan = [m for m in MODELOS if m not in texto]
    return (not faltan), f"el ejecutor nombra {list(MODELOS)}" if not faltan else f"el ejecutor no nombra: {faltan}"


def comprobar_settings(repo: Path) -> tuple[bool, str]:
    try:
        permisos = json.loads(leer(repo, ".claude/settings.json") or "{}").get("permissions", {})
    except ValueError:
        return False, "settings.json no es JSON válido"
    deny = set(permisos.get("deny", []))
    faltan = sorted(DENY_MINIMO - deny)
    sin_psql = not any("psql" in d and "PROD" in d for d in deny)
    if faltan or sin_psql:
        return False, f"faltan deny: {faltan}{' y el de psql productivo' if sin_psql else ''}"
    preaprobada = [a for a in permisos.get("allow", []) if "deepseek" in a]
    return True, f"deny íntegro ({len(deny)}); herramienta de DeepSeek preaprobada: {'sí' if preaprobada else 'no'}"


def comprobar_spec_kit(repo: Path) -> tuple[bool, str]:
    try:
        integracion = json.loads(leer(repo, ".specify/integration.json") or "{}")
    except ValueError:
        return False, "integration.json no es JSON válido"
    skills = sorted(p.parent.name for p in (repo / ".claude/skills").glob("speckit-*/SKILL.md"))
    constitucion = (repo / ".specify/memory/constitution.md").exists()
    bien = "claude" in json.dumps(integracion) and len(skills) >= 9 and constitucion
    return bien, f"{len(skills)} skills speckit-*, constitución {'presente' if constitucion else 'AUSENTE'}"


def comprobar_mcp_del_repo(repo: Path) -> tuple[bool, str]:
    texto = leer(repo, ".mcp.json")
    try:
        servidores = json.loads(texto).get("mcpServers", {})
    except ValueError:
        return False, ".mcp.json no es JSON válido"
    if montaje.SERVER_NAME in servidores or montaje.KEY_NAME in texto:
        return False, "el servidor con clave no puede vivir en un fichero versionado"
    return True, f"JSON válido, sin secretos, servidores: {sorted(servidores) or 'ninguno'}"


def comprobar_entrada_local(repo: Path) -> tuple[bool, str]:
    if not montaje.CLAUDE_JSON.exists():
        return False, f"no existe {montaje.CLAUDE_JSON}"
    datos = json.loads(montaje.CLAUDE_JSON.read_text())
    servidor = datos.get("projects", {}).get(str(repo), {}).get("mcpServers", {}).get(montaje.SERVER_NAME)
    if not servidor:
        return False, f"sin entrada `{montaje.SERVER_NAME}` para {repo}"
    orden = servidor.get("command", "")
    if not (Path(orden).is_absolute() and os.access(orden, os.X_OK)):
        return False, f"la orden no es una ruta absoluta ejecutable: {orden}"
    if montaje.PACKAGE_SPEC not in servidor.get("args", []):
        return False, f"versión sin fijar: {servidor.get('args')} (se espera {montaje.PACKAGE_SPEC})"
    if str(Path(orden).parent) not in servidor.get("env", {}).get("PATH", ""):
        return False, "el PATH de la entrada no incluye el directorio de node"
    return True, f"{orden} -y {montaje.PACKAGE_SPEC}"


def comprobar_clave_local(repo: Path) -> tuple[bool, str]:
    """Solo presencia. El valor no se devuelve, no se compara y no se imprime."""
    if not montaje.CLAUDE_JSON.exists():
        return False, "PRESENT=NO"
    datos = json.loads(montaje.CLAUDE_JSON.read_text())
    servidor = datos.get("projects", {}).get(str(repo), {}).get("mcpServers", {}).get(montaje.SERVER_NAME, {})
    presente = montaje.KEY_NAME in servidor.get("env", {})
    no_vacia = bool(servidor.get("env", {}).get(montaje.KEY_NAME))
    return no_vacia, f"PRESENT={'YES' if presente else 'NO'} NONEMPTY={'YES' if no_vacia else 'NO'}"


def comprobar_sin_clave_en_el_repo(repo: Path) -> tuple[bool, str]:
    listado = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             cwd=repo, capture_output=True, check=True).stdout.split(b"\0")
    con_clave = []
    for nombre in filter(None, listado):
        ruta = repo / nombre.decode()
        if not ruta.is_file() or ruta.stat().st_size > 2_000_000:
            continue
        try:
            if CLAVE_INCRUSTADA.search(ruta.read_text(errors="ignore")):
                con_clave.append(nombre.decode())
        except OSError:
            continue
    return (not con_clave), f"{len(listado) - 1} ficheros sin claves incrustadas" if not con_clave else f"SECRET_EXPOSURE en: {con_clave}"


def arranque_del_servidor(repo: Path) -> tuple[bool, str, dict]:
    """Arranca el paquete fijado por stdio, sin clave real, y lee lo que declara."""
    if not shutil.which("npx"):
        return False, "no se encuentra npx", {}
    npx = montaje.npx_absoluto()
    entorno = {**montaje.entorno_base(npx), "HOME": str(Path.home()),
               montaje.KEY_NAME: CLAVE_DE_RELLENO, "SKIP_CONNECTION_TEST": "true"}
    proceso = subprocess.Popen([npx, "-y", montaje.PACKAGE_SPEC], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL, env=entorno, text=True)

    def pedir(identificador: int, metodo: str, parametros: dict | None = None) -> dict:
        proceso.stdin.write(json.dumps({"jsonrpc": "2.0", "id": identificador, "method": metodo,
                                        "params": parametros or {}}) + "\n")
        proceso.stdin.flush()
        limite = time.time() + 90
        while time.time() < limite:
            listo, _, _ = select.select([proceso.stdout], [], [], 1)
            if not listo:
                continue
            linea = proceso.stdout.readline()
            if not linea:
                break
            try:
                mensaje = json.loads(linea)
            except ValueError:
                continue
            if mensaje.get("id") == identificador:
                return mensaje.get("result", {})
        return {}

    try:
        inicio = pedir(1, "initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                         "clientInfo": {"name": "kontrol-readiness", "version": "1"}})
        proceso.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        proceso.stdin.flush()
        herramientas = pedir(2, "tools/list").get("tools", [])
    except BrokenPipeError:
        return False, f"el servidor terminó durante el saludo (código {proceso.poll()})", {}
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proceso.kill()

    declarado = {
        "serverInfo": inicio.get("serverInfo"),
        "protocolVersion": inicio.get("protocolVersion"),
        "tools": [{"name": h["name"], "required": h["inputSchema"].get("required", []),
                   "optional": sorted(set(h["inputSchema"].get("properties", {})) - set(h["inputSchema"].get("required", []))),
                   "model": h["inputSchema"].get("properties", {}).get("model", {}),
                   "output": sorted(h.get("outputSchema", {}).get("properties", {}))} for h in herramientas],
    }
    version = (inicio.get("serverInfo") or {}).get("version")
    nombres = [h["name"] for h in herramientas]
    modelos = next((h["inputSchema"]["properties"].get("model", {}).get("enum", [])
                    for h in herramientas if h["name"] == HERRAMIENTA_MCP), [])
    if version != montaje.PACKAGE_VERSION:
        return False, f"el servidor dice ser {version}, se fijó {montaje.PACKAGE_VERSION}", declarado
    if HERRAMIENTA_MCP not in nombres:
        return False, f"el servidor no expone {HERRAMIENTA_MCP}: {nombres}", declarado
    ausentes = [m for m in MODELOS if m not in modelos]
    if ausentes:
        return False, f"el servidor no acepta los modelos {ausentes}: {modelos}", declarado
    return True, f"v{version}; herramientas {nombres}; modelos {modelos}", declarado


COMPROBACIONES = [
    ("Claude configuration", comprobar_claude_md),
    ("Executor patch-only", comprobar_ejecutor),
    ("Coordinator", comprobar_coordinador),
    ("Retry cap = 2", comprobar_tope_de_reintentos),
    ("Model names documented", comprobar_modelos_documentados),
    ("Settings deny", comprobar_settings),
    ("Spec Kit", comprobar_spec_kit),
    ("Repo .mcp.json", comprobar_mcp_del_repo),
    ("No key in repository", comprobar_sin_clave_en_el_repo),
    ("DeepSeek MCP local entry", comprobar_entrada_local),
    ("DeepSeek API key", comprobar_clave_local),
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--handshake", action="store_true",
                        help="arranca el servidor fijado (sin clave real) y comprueba herramientas y modelos")
    parser.add_argument("--dump", type=Path, metavar="FICHERO",
                        help="con --handshake, guarda en JSON lo que el servidor declara")
    args = parser.parse_args(argv)

    resultados = [(nombre, *comprobacion(REPO)) for nombre, comprobacion in COMPROBACIONES]
    if args.handshake:
        bien, detalle, declarado = arranque_del_servidor(REPO)
        resultados.append(("MCP server handshake", bien, detalle))
        if args.dump:
            args.dump.write_text(json.dumps(declarado, indent=2, ensure_ascii=False) + "\n")

    for nombre, bien, detalle in resultados:
        print(f"{'PASS' if bien else 'FAIL'}  {nombre:<26} {detalle}")
    fallos = [nombre for nombre, bien, _ in resultados if not bien]
    print(f"\nREADINESS = {'PASS' if not fallos else 'FAIL'} ({len(resultados) - len(fallos)}/{len(resultados)})")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
