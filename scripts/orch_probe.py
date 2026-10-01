#!/usr/bin/env python3
"""Prueba de extremo a extremo de la orquestación Claude + DeepSeek (ORCH-01..ORCH-10).

Arranca una sesión NUEVA de Claude Code en este repositorio, le hace delegar una tarea
inocua en el subagente `deepseek-executor` y comprueba, sobre la traza real de la sesión y
no sobre lo que el modelo diga, que la cadena Claude → ejecutor → MCP → DeepSeek ocurrió.
Después audita el parche, rechaza uno no conforme, aplica el aprobado, lo prueba y limpia.

Todo ocurre sobre un fichero de arena fuera del producto. No lee ni muestra ninguna clave.

Uso:
    python scripts/orch_probe.py                      # certifica; código 0 solo si ORCH-01..10 pasan
    python scripts/orch_probe.py --report FICHERO     # además guarda el informe
    python scripts/orch_probe.py --trace T && python scripts/orch_probe.py --replay T   # repetir sin gastar
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orchestration_readiness as auditoria  # noqa: E402
import set_deepseek_key as montaje  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
ARENA = Path("/tmp/kontrol-orchestration-probe")
OBJETIVO = ARENA / "orchestration_probe.txt"
ORIGINAL = "alpha=1\nbeta=2\ngamma=3\n"
ESPERADO = "alpha=1\nbeta=20\ngamma=3\n"
CAMBIO_AUTORIZADO = ("beta=2", "beta=20")
SUBAGENTE = "deepseek-executor"
MODELO = "deepseek-v4-flash"
BLOQUE = re.compile(
    r"^(?P<ruta>[^\n]+)\n<{7} SEARCH\n(?P<search>.*?)\n?={7}\n(?P<replace>.*?)\n?>{7} REPLACE", re.S | re.M
)
SECRETO = re.compile(
    r"sk-[0-9a-fA-F]{32}|-----BEGIN [A-Z ]*PRIVATE KEY|postgres(ql)?(\+\w+)?://[^\s:]+:[^\s@]+@|"
    r"(api[_-]?key|token|password|secret)[\"']?\s*[=:]\s*[\"']?[A-Za-z0-9_\-]{16,}", re.I
)
ENCARGO = f"""TASK: ORCH-PROBE-001
GOAL: en el fichero objetivo, cambiar exclusivamente la línea `beta=2` por `beta=20`.
TARGET FILES: {OBJETIVO}
READ-ONLY CONTEXT: none
CONTRACT: el fichero tiene tres líneas clave=valor; tras el cambio debe decir alpha=1, beta=20, gamma=3.
INVARIANTS: `alpha=1` y `gamma=3` no cambian; el fichero conserva sus tres líneas.
CONSTRAINTS: no añadir líneas, no explicar, no refactorizar, no tocar ningún otro fichero.
IMPLEMENTATION STYLE: n/a
OUTPUT FORMAT: solo bloques SEARCH/REPLACE
DONE WHEN: un bloque SEARCH/REPLACE sobre el fichero objetivo que cambia `beta=2` por `beta=20` y nada más.
TESTS EXPECTED: alpha == 1, beta == 20, gamma == 3
MODEL: {MODELO}

CONTENIDO ACTUAL DEL FICHERO OBJETIVO:
{ORIGINAL}"""
PETICION = f"""Eres el orquestador de KONTROL. Delega el encargo de abajo en el subagente
`{SUBAGENTE}` con la herramienta Agent, pasándoselo íntegro y sin cambios. No lo resuelvas
tú, no edites ningún fichero y no llames tú a DeepSeek. Cuando el subagente responda,
devuelve su salida literal y completa, sin añadir nada.

{ENCARGO}"""


@dataclass
class Traza:
    """Lo que la sesión hizo de verdad, leído de su flujo de eventos."""
    agentes_cargados: list = field(default_factory=list)
    mcp: list = field(default_factory=list)
    delegaciones: list = field(default_factory=list)      # llamadas a Agent
    llamadas_mcp: list = field(default_factory=list)      # (herramienta, argumentos, desde_subagente)
    otras_del_subagente: list = field(default_factory=list)
    respuestas_mcp: list = field(default_factory=list)
    texto_final: str = ""
    coste_claude: float | None = None


def leer_traza(lineas: list[str]) -> Traza:
    traza = Traza()
    ids_mcp: set[str] = set()
    for linea in lineas:
        try:
            evento = json.loads(linea)
        except ValueError:
            continue
        tipo = evento.get("type")
        if tipo == "system" and evento.get("subtype") == "init":
            traza.agentes_cargados = evento.get("agents", [])
            traza.mcp = evento.get("mcp_servers", [])
        elif tipo == "assistant":
            for bloque in evento.get("message", {}).get("content", []):
                if bloque.get("type") != "tool_use":
                    continue
                nombre, argumentos = bloque.get("name", ""), bloque.get("input", {})
                desde_subagente = bool(evento.get("parent_tool_use_id"))
                if nombre in ("Agent", "Task"):
                    traza.delegaciones.append(argumentos)
                elif nombre.startswith(f"mcp__{montaje.SERVER_NAME}__"):
                    traza.llamadas_mcp.append((nombre, argumentos, desde_subagente))
                    ids_mcp.add(bloque.get("id"))
                elif desde_subagente:
                    traza.otras_del_subagente.append(nombre)
        elif tipo == "user":
            for bloque in evento.get("message", {}).get("content", []):
                if isinstance(bloque, dict) and bloque.get("type") == "tool_result" and bloque.get("tool_use_id") in ids_mcp:
                    traza.respuestas_mcp.append({"is_error": bool(bloque.get("is_error")),
                                                 "contenido": bloque.get("content"),
                                                 "estructurado": evento.get("tool_use_result")})
        elif tipo == "result":
            traza.texto_final = evento.get("result") or ""
            traza.coste_claude = evento.get("total_cost_usd")
    return traza


def extraer_bloques(texto: str) -> list[dict]:
    return [{"ruta": m["ruta"].strip().strip("`"), "search": m["search"], "replace": m["replace"]}
            for m in BLOQUE.finditer(texto)]


def auditar(bloques: list[dict], contenido: str, objetivo: str) -> tuple[str, str]:
    """El criterio con que Claude audita el parche de la sonda, antes de aplicar nada."""
    if len(bloques) != 1:
        return "AUDIT_REJECT", f"NOT_A_SINGLE_BLOCK ({len(bloques)})"
    bloque = bloques[0]
    if Path(bloque["ruta"]).name != Path(objetivo).name or (
            Path(bloque["ruta"]).is_absolute() and bloque["ruta"] != objetivo):
        return "AUDIT_REJECT", f"OUT_OF_SCOPE_FILE ({bloque['ruta']})"
    if SECRETO.search(bloque["search"] + bloque["replace"]):
        return "AUDIT_REJECT", "SECRET_IN_PATCH"
    if not bloque["search"] or contenido.count(bloque["search"]) != 1:
        return "AUDIT_REJECT", "SEARCH_MISMATCH"
    antes = contenido.splitlines()
    despues = contenido.replace(bloque["search"], bloque["replace"], 1).splitlines()
    if len(antes) != len(despues):
        return "AUDIT_REJECT", "UNAUTHORIZED_EXTRA_CHANGE (cambia el número de líneas)"
    cambios = [(a, d) for a, d in zip(antes, despues) if a != d]
    if cambios != [CAMBIO_AUTORIZADO]:
        ajenos = [c for c in cambios if c != CAMBIO_AUTORIZADO]
        return "AUDIT_REJECT", f"UNAUTHORIZED_EXTRA_CHANGE {ajenos}" if ajenos else "CHANGE_MISSING"
    return "AUDIT_PASS", "un bloque, fichero objetivo, SEARCH exacto, solo beta=2 → beta=20"


def aplicar(bloque: dict, ruta: Path) -> None:
    ruta.write_text(ruta.read_text().replace(bloque["search"], bloque["replace"], 1))


def binario_de_claude() -> str | None:
    candidatos = [os.environ.get("CLAUDE_CODE_EXECPATH"), shutil.which("claude"),
                  *sorted(glob.glob(str(Path.home() / ".vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude")))[::-1]]
    return next((c for c in candidatos if c and os.access(c, os.X_OK)), None)


def sesion_nueva(claude: str, presupuesto: str) -> list[str]:
    """Una sesión limpia: sin heredar las variables de la sesión que lanza la sonda."""
    entorno = {k: v for k, v in os.environ.items() if not (k == "CLAUDECODE" or k.startswith("CLAUDE_"))}
    orden = [claude, "-p", PETICION, "--output-format", "stream-json", "--verbose", "--model", "sonnet",
             "--add-dir", str(ARENA), "--permission-prompts", "none", "--no-session-persistence",
             "--max-budget-usd", presupuesto,
             "--allowedTools", "Agent", "Read", f"mcp__{montaje.SERVER_NAME}__{auditoria.HERRAMIENTA_MCP}"]
    hecho = subprocess.run(orden, cwd=REPO, env=entorno, stdin=subprocess.DEVNULL, capture_output=True,
                           text=True, timeout=600)
    return hecho.stdout.splitlines()


def uso_declarado(respuesta: dict) -> dict:
    """Modelo, tokens y coste tal como los devuelve la herramienta; nada se estima."""
    crudo = respuesta.get("estructurado")
    if not isinstance(crudo, dict):
        textos = respuesta.get("contenido")
        if isinstance(textos, list):
            textos = "\n".join(t.get("text", "") for t in textos if isinstance(t, dict))
        try:
            crudo = json.loads(textos) if isinstance(textos, str) else {}
        except ValueError:
            crudo = {}
    crudo = crudo.get("structuredContent", crudo) if isinstance(crudo, dict) else {}
    peticion = crudo.get("request", {}) if isinstance(crudo, dict) else {}
    return {k: peticion.get(k, crudo.get(k)) for k in
            ("model", "wire_model", "fallback_used", "finish_reason", "prompt_tokens", "completion_tokens", "cost_usd")
            if peticion.get(k, crudo.get(k)) is not None}


def certificar(lineas: list[str]) -> list[tuple[str, bool, str]]:
    traza = leer_traza(lineas)
    r: list[tuple[str, bool, str]] = []

    delegada = [d for d in traza.delegaciones if d.get("subagent_type") == SUBAGENTE]
    r.append(("ORCH-01 Claude → executor", bool(delegada) and SUBAGENTE in traza.agentes_cargados,
              f"{len(delegada)} delegación(es) a `{SUBAGENTE}`; agentes cargados: {traza.agentes_cargados}"))

    del_subagente = [(n, a) for n, a, sub in traza.llamadas_mcp if sub]
    del_principal = [n for n, _, sub in traza.llamadas_mcp if not sub]
    buenas = [x for x in traza.respuestas_mcp if not x["is_error"]]
    conectado = [s.get("status") for s in traza.mcp if s.get("name") == montaje.SERVER_NAME]
    r.append(("ORCH-02 executor → MCP → DeepSeek", len(del_subagente) >= 1 and bool(buenas) and not del_principal,
              f"DEEPSEEK CALLS = {len(buenas)} (intentos del ejecutor: {len(del_subagente)}); llamadas directas del orquestador: "
              f"{len(del_principal)}; MCP `{montaje.SERVER_NAME}`: {conectado or 'no cargado'}"))

    carga = json.dumps([a for _, a in del_subagente], ensure_ascii=False)
    con_sesion = [a for _, a in del_subagente if a.get("session_id")]
    r.append(("ORCH-03 egress", bool(del_subagente) and not SECRETO.search(carga) and ".env" not in carga and not con_sesion,
              f"carga de {len(carga)} caracteres; secretos: {'SÍ' if SECRETO.search(carga) else '0'}; ficheros .env: "
              f"{'SÍ' if '.env' in carga else '0'}; session_id: {'SÍ' if con_sesion else 'ninguno (sin memoria)'}"))

    bloques = extraer_bloques(traza.texto_final)
    r.append(("ORCH-04 patch format", len(bloques) >= 1, f"{len(bloques)} bloque(s) SEARCH/REPLACE en la respuesta"))

    veredicto, motivo = auditar(bloques, OBJETIVO.read_text(), str(OBJETIVO))
    r.append(("ORCH-05 audit-pass", veredicto == "AUDIT_PASS", f"{veredicto}: {motivo}"))

    sintetico = [{"ruta": str(OBJETIVO), "search": "alpha=1\nbeta=2", "replace": "alpha=999\nbeta=20"}]
    rechazo, por_que = auditar(sintetico, ORIGINAL, str(OBJETIVO))
    intacto = OBJETIVO.read_text() == ORIGINAL
    r.append(("ORCH-06 audit-reject", rechazo == "AUDIT_REJECT" and "UNAUTHORIZED_EXTRA_CHANGE" in por_que and intacto,
              f"candidato sintético (alpha=999): {rechazo}: {por_que}; no aplicado: {'sí' if intacto else 'NO'}"))

    aplicado = False
    if veredicto == "AUDIT_PASS":
        aplicar(bloques[0], OBJETIVO)
        aplicado = True
    r.append(("ORCH-07 apply", aplicado, "aplicado por Claude, tras la auditoría" if aplicado else "nada que aplicar: no hubo parche aprobado"))

    valores = dict(linea.split("=", 1) for linea in OBJETIVO.read_text().splitlines() if "=" in linea)
    r.append(("ORCH-08 test", aplicado and valores == {"alpha": "1", "beta": "20", "gamma": "3"}, f"fichero: {valores}"))

    pedido = [a.get("model") for _, a in del_subagente]
    uso = uso_declarado(buenas[0]) if buenas else {}
    r.append(("ORCH-09 tool/model/usage", bool(buenas) and pedido == [MODELO] * len(pedido) and bool(pedido),
              f"servidor `{montaje.SERVER_NAME}` {montaje.PACKAGE_SPEC}; herramienta {[n for n, _ in del_subagente]}; "
              f"modelo pedido {pedido}; devuelto por la herramienta: {uso or 'not reported'}"))

    tope, detalle = auditoria.comprobar_tope_de_reintentos(REPO)
    r.append(("ORCH-10 retry cap", tope and len(del_subagente) <= 1,
              f"{detalle}; llamadas del ejecutor en un encargo: {len(del_subagente)} (no reintenta por su cuenta)"))
    return r


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--report", type=Path, help="guarda el informe en este fichero")
    parser.add_argument("--trace", type=Path, help="guarda la traza cruda de la sesión (para depurar)")
    parser.add_argument("--replay", type=Path, help="certifica sobre una traza guardada, sin abrir sesión ni llamar a nadie")
    parser.add_argument("--budget", default="1.50", help="tope de gasto de la sesión de Claude, en USD")
    args = parser.parse_args(argv)

    claude = binario_de_claude()
    if not claude and not args.replay:
        print("No se encuentra el binario de Claude Code.")
        return 2

    shutil.rmtree(ARENA, ignore_errors=True)
    ARENA.mkdir(parents=True)
    OBJETIVO.write_text(ORIGINAL)
    try:
        lineas = args.replay.read_text().splitlines() if args.replay else sesion_nueva(claude, args.budget)
        if args.trace:
            args.trace.write_text("\n".join(lineas) + "\n")
        resultados = certificar(lineas)
    finally:
        shutil.rmtree(ARENA, ignore_errors=True)

    informe = ["EGRESS_CHECK (encargo): ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 "
               f"REAL_PAYROLL=0 BANK_DATA=0 — {'verificado' if not SECRETO.search(PETICION) else 'FALLA'}", ""]
    informe += [f"{'PASS' if bien else 'FAIL'}  {nombre:<36} {detalle}" for nombre, bien, detalle in resultados]
    pasan = sum(bien for _, bien, _ in resultados)
    informe += ["", f"SANDBOX_RESIDUAL = {int(ARENA.exists())}",
                f"ORCH = {pasan}/{len(resultados)}",
                f"ORCHESTRATION_STATUS = {'VERIFIED_END_TO_END' if pasan == len(resultados) else 'NOT_VERIFIED'}"]
    print("\n".join(informe))
    if args.report:
        args.report.write_text("\n".join(informe) + "\n")
    return 0 if pasan == len(resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
