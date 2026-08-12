#!/usr/bin/env python3
"""Genera matrices de auditoría (Spec 012, pasada 2) a partir de la evidencia.

Salidas en specs/012-auditoria-integral-e2e/:
  frontend-inventory.md
  frontend-api-matrix.md
  full-stack-integration-matrix.md
  integration-master-matrix.md (resumen por página)
No modifica código productivo.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("/home/maria/Proyectos/kontrol")
EVID = ROOT / "specs/012-auditoria-integral-e2e/evidence"
OUT = ROOT / "specs/012-auditoria-integral-e2e"

menu = json.loads((EVID / "menu-inventory.json").read_text(encoding="utf-8"))
route_audit = json.loads((EVID / "route-audit.json").read_text(encoding="utf-8"))
page_api = json.loads((EVID / "frontend-api-calls.json").read_text(encoding="utf-8"))
be = json.loads((EVID / "backend-endpoints.json").read_text(encoding="utf-8"))

by_norm: dict[str, list[str]] = {}
for r in be:
    by_norm.setdefault(r["norm"], []).append(r["method"])


def norm(p: str) -> str:
    return re.sub(r"\$\{[^}]*\}", "*", p).split("?")[0].rstrip("/")


def matches(pat: str, np: str) -> bool:
    if "*" not in pat:
        return pat == np
    a, b = pat.split("/"), np.split("/")
    return len(a) == len(b) and all(x == y or x == "*" for x, y in zip(a, b))


def resolve(path: str) -> str:
    np_ = norm(path)
    if np_ in by_norm:
        return np_
    for p in by_norm:
        if matches(np_, p):
            return p
    return "SIN_ENDPOINT"


# --------------------------------------------------------------------------- #
# 1. frontend-inventory.md
# --------------------------------------------------------------------------- #
route_by_path = {r["path"]: r for r in route_audit}
lines = ["# Inventario del Frontend — Spec 012 (pasada 2)", "",
         "Fuente: evidencia regenerada (menu-inventory, route-audit, frontend-api-calls).",
         "", "## 1. Menú", "", "| Sección | Etiqueta | Ruta | Ruta declarada |", "|---|---|---|---|"]
for it in menu:
    lines.append(f"| {it['section']} | {it['label']} | `{it['to']}` | {'SÍ' if it.get('declared_in_router') else '**NO**'} |")
lines += ["", "## 2. Rutas → Página", "", "| Ruta | Componente | Import resuelve |", "|---|---|---|"]
for r in route_audit:
    lines.append(f"| `/{r['path']}` | {r['component']} | {'SÍ' if r['import_resolves'] else '**NO**'} |")
lines += ["", "## 3. Páginas → llamadas API (primer literal por página)", "",
          "| Página | Llamadas (muestra) |", "|---|---|"]
for k in sorted(page_api):
    calls = ", ".join(f"`{c}`" for c in page_api[k][:4])
    lines.append(f"| `{k}` | {calls} |")
(OUT / "frontend-inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# --------------------------------------------------------------------------- #
# 2. frontend-api-matrix.md (todas las llamadas, no solo primeras)
# --------------------------------------------------------------------------- #
calls_all: dict[str, list[str]] = {}


def _extract(text: str) -> list[str]:
    """Extrae literales de apiFetch manejando genéricos anidados y templates."""
    out = []
    for m in re.finditer(r"apiFetch", text):
        i = m.end()
        while i < len(text) and text[i] in " \t\r\n":
            i += 1
        if i < len(text) and text[i] == "<":
            depth = 0
            while i < len(text):
                if text[i] == "<":
                    depth += 1
                elif text[i] == ">":
                    depth -= 1
                i += 1
                if depth == 0:
                    break
            while i < len(text) and text[i] in " \t\r\n":
                i += 1
        if i < len(text) and text[i] == "(":
            i += 1
            while i < len(text) and text[i] in " \t\r\n":
                i += 1
            if i < len(text) and text[i] in '"\u0060\'':
                q = text[i]
                i += 1
                if q == "\u0060":
                    # template: cerrar en el primer backtick NO anidado simple;
                    # los templates con ${...} se normalizan luego.
                    end = text.find(q, i)
                    if end != -1:
                        out.append(text[i:end])
                else:
                    end = text.find(q, i)
                    if end != -1:
                        out.append(text[i:end])
    return out


for f in sorted((ROOT / "resources/frontend/src").rglob("*.tsx")):
    found = _extract(f.read_text(encoding="utf-8", errors="replace"))
    if found:
        calls_all[str(f.relative_to(ROOT / "resources/frontend/src"))] = found

lines = ["# Matriz Frontend ↔ API — Spec 012 (pasada 2)", "",
         "Todas las llamadas `apiFetch` del frontend resueltas contra el OpenAPI real (294 rutas).",
         "", "| Página | Llamada | Endpoint backend | Métodos |", "|---|---|---|---|"]
broken = 0
for page, cl in sorted(calls_all.items()):
    for c in cl:
        np_ = norm(c)
        ok = np_ in by_norm or any(matches(np_, p) for p in by_norm)
        if not ok:
            broken += 1
            lines.append(f"| `{page}` | `{c}` | **SIN_ENDPOINT** | — |")
        else:
            lines.append(f"| `{page}` | `{c}` | `{resolve(c)}` | {', '.join(by_norm.get(resolve(c), []))} |")
lines += ["", f"Total llamadas: {sum(len(v) for v in calls_all.values())} · Sin endpoint: {broken}"]
(OUT / "frontend-api-matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# --------------------------------------------------------------------------- #
# 3. full-stack-integration-matrix.md (página → endpoints únicos)
# --------------------------------------------------------------------------- #
lines = ["# Matriz de Integración Full-Stack — Spec 012 (pasada 2)", "",
         "Función (página) → endpoints consumidos → backend (existe) → evidencia.",
         "", "| Página | Endpoints (únicos) | Resuelve backend |", "|---|---|---|"]
for page, cl in sorted(calls_all.items()):
    uniq = sorted({resolve(c) for c in cl})
    ok = all(u != "SIN_ENDPOINT" for u in uniq)
    lines.append(f"| `{page}` | {', '.join(f'`{u}`' for u in uniq[:6])}{'…' if len(uniq) > 6 else ''} | {'SÍ' if ok else '**NO**'} |")
(OUT / "full-stack-integration-matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# --------------------------------------------------------------------------- #
# 4. integration-master-matrix.md (resumen por página)
# --------------------------------------------------------------------------- #
section_of: dict[str, str] = {}
for it in menu:
    section_of.setdefault(it["to"].lstrip("/"), it["section"])

lines = ["# Matriz Maestra de Integración — Spec 012 (pasada 2)", "",
         "Estado por página según: Menú → Ruta → Página → API → Backend → Evidencia.",
         "Estados: COMPLETE_100 / PARTIAL / BROKEN / NOT_IMPLEMENTED / NOT_TESTED / FUTURE_SCOPE.",
         "", "| Ruta | Menú | Sección | Página | API resuelve | Estado (estático) |", "|---|---|---|---|---|---|"]
for r in route_audit:
    p = r["path"]
    s = section_of.get(p, "—")
    label = next((it["label"] for it in menu if it["to"].lstrip("/") == p), "—")
    apicalls = [c for k, v in calls_all.items() if k.split("/")[-1].startswith(p.split("/")[-1]) for c in v]
    ok_api = all(resolve(c) != "SIN_ENDPOINT" for c in apicalls) if apicalls else True
    status = "COMPLETE_100" if (r["import_resolves"] and ok_api) else ("PARTIAL" if r["import_resolves"] else "BROKEN")
    lines.append(f"| `/{p}` | {label} | {s} | {r['component']} | {'SÍ' if ok_api else 'NO'} | {status} |")
(OUT / "integration-master-matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

print("Matrices generadas en", OUT)
print("Llamadas frontend totales:", sum(len(v) for v in calls_all.values()), "| Sin endpoint:", broken)
