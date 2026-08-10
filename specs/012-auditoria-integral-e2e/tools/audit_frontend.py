#!/usr/bin/env python3
"""Auditoría automática de completitud frontend: menú ↔ ruta ↔ página ↔ API.

Extrae de forma programática:
  1. Menú (Sidebar.tsx): sección -> {to, label}.
  2. Router (router.tsx): paths + componente.
  3. Página física por componente (imports de router).
  4. Llamadas apiFetch() por página (candidatas a endpoints).
  5. Escaneo estático: placeholders/TODO/FIXME/console.log/any/ts-ignore.

Salidas en specs/012-auditoria-integral-e2e/evidence/.
No modifica código productivo.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path("/home/maria/Proyectos/kontrol/resources/frontend/src")
EVID = Path("/home/maria/Proyectos/kontrol/specs/012-auditoria-integral-e2e/evidence")
EVID.mkdir(parents=True, exist_ok=True)

SIDEBAR = ROOT / "layout/Sidebar.tsx"
ROUTER = ROOT / "app/router.tsx"


# --------------------------------------------------------------------------- #
# 1. Menú
# --------------------------------------------------------------------------- #
def parse_menu(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    items = []
    # Secciones: title: "..." y luego items con { to: "...", label: "..." }
    section_re = re.compile(r'title:\s*"([^"]+)"')
    item_re = re.compile(r'\{\s*to:\s*"([^"]+)",\s*label:\s*"([^"]+)"')
    # recorrer por bloques de sección
    for sec in section_re.finditer(text):
        start = sec.start()
        nxt = section_re.search(text, sec.end())
        block = text[start : (nxt.start() if nxt else len(text))]
        title = sec.group(1)
        for m in item_re.finditer(block):
            items.append({"section": title, "to": m.group(1), "label": m.group(2)})
    return items


# --------------------------------------------------------------------------- #
# 2. Router: paths + componente + import mapping
# --------------------------------------------------------------------------- #
def parse_router(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    # imports: import { A, B as C } from "@/path"
    imports = {}
    for m in re.finditer(r'import\s*\{([^}]+)\}\s*from\s*"@/([^"]+)"', text):
        for name in m.group(1).split(","):
            name = name.strip()
            if not name:
                continue
            if " as " in name:
                orig, alias = (x.strip() for x in name.split(" as ", 1))
                imports[alias] = m.group(2)
            else:
                imports[name] = m.group(2)
    # rutas
    routes = []
    for m in re.finditer(r'path:\s*"([^"]+)"\s*,\s*element:\s*<([A-Za-z0-9_]+)\s*/>', text):
        routes.append({"path": m.group(1), "component": m.group(2)})
    # index route
    for m in re.finditer(r'\{\s*index:\s*true\s*,\s*element:\s*<([A-Za-z0-9_]+)\s*/>', text):
        routes.append({"path": "", "component": m.group(1)})
    return {"imports": imports, "routes": routes}


def component_file_exists(imports: dict, comp: str) -> tuple[bool, str | None]:
    rel = imports.get(comp)
    if not rel:
        return False, None
    full = ROOT / f"{rel}.tsx"
    if not full.exists():
        # probar index.tsx
        full = ROOT / rel / "index.tsx"
    return full.exists(), str(full)


# --------------------------------------------------------------------------- #
# 3. apiFetch por página
# --------------------------------------------------------------------------- #
def api_calls_in_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    calls = set()
    # apiFetch<T>( "...literal..." )  o apiFetch( "...literal..." )
    for m in re.finditer(r'apiFetch(?:\s*<[^>]*>)?\s*\(\s*(["\'])', text):
        quote = m.group(1)
        body = text[m.end():]
        end = body.find(quote)
        literal = body[:end] if end != -1 else ""
        # template literal simple: apiFetch(`...${...}...`)
        if literal == "`":
            # handle backtick case separately
            pass
        if literal:
            calls.add(literal)
    # template strings con backticks
    for m in re.finditer(r'apiFetch(?:\s*<[^>]*>)?\s*\(\s*`', text):
        body = text[m.end():]
        end = body.find("`")
        tmpl = body[:end] if end != -1 else ""
        # normalizar ${...} -> {} y quedarnos con el prefijo hasta "?"
        norm = re.sub(r'\$\{[^}]*\}', '*', tmpl)
        base = norm.split("?")[0]
        if base.startswith("/"):
            calls.add(base + " (template)")
    return sorted(calls)


def scan_placeholders(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    hits = []
    patterns = {
        "TODO/FIXME/HACK/XXX": r"\b(TODO|FIXME|HACK|XXX)\b",
        "console.log/debugger": r"console\.log|\bdebugger\b",
        "ts-ignore/eslint-disable": r"ts-ignore|eslint-disable",
        "any": r":\s*any\b",
    }
    for label, pat in patterns.items():
        if re.search(pat, text):
            hits.append(label)
    return hits


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main() -> None:
    menu = parse_menu(SIDEBAR)
    router = parse_router(ROUTER)
    route_paths = set(r["path"] for r in router["routes"]) | {""}

    # menú -> ruta (el menú usa "/ruta"; el router declara "ruta")
    menu_audit = []
    for it in menu:
        p = it["to"].lstrip("/")
        declared = p in route_paths
        menu_audit.append({**it, "normalized": p, "declared_in_router": declared})

    # ruta -> página
    route_audit = []
    for r in router["routes"]:
        ok, fpath = component_file_exists(router["imports"], r["component"])
        route_audit.append({"path": r["path"], "component": r["component"],
                            "import_resolves": ok, "file": fpath})

    # páginas -> apiFetch
    page_api = {}
    for f in sorted(ROOT.rglob("*.tsx")):
        calls = api_calls_in_file(f)
        if calls:
            page_api[str(f.relative_to(ROOT))] = calls

    # escaneo estático de páginas
    static_scan = {}
    for f in sorted(ROOT.rglob("*.tsx")):
        hits = scan_placeholders(f)
        if hits:
            static_scan[str(f.relative_to(ROOT))] = hits

    # persistir
    (EVID / "menu-inventory.json").write_text(json.dumps(menu, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVID / "menu-route-audit.json").write_text(json.dumps(menu_audit, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVID / "route-audit.json").write_text(json.dumps(route_audit, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVID / "frontend-api-calls.json").write_text(json.dumps(page_api, ensure_ascii=False, indent=2), encoding="utf-8")
    (EVID / "static-scan.json").write_text(json.dumps(static_scan, ensure_ascii=False, indent=2), encoding="utf-8")

    # reporte resumido
    print("=== MENÚ ===")
    for it in menu_audit:
        print(f"[{it['section']}] {it['label']:28} -> {it['to']:45} {'OK' if it['declared_in_router'] else '!! RUTA NO DECLARADA'}")
    print("\n=== RUTAS SIN PÁGINA ===")
    for r in route_audit:
        if not r["import_resolves"]:
            print(f"  {r['path']:45} {r['component']:25} SIN PÁGINA/IMPORT")
    print("\n=== PÁGINAS CON MARCADORES ESTÁTICOS ===")
    for k, v in static_scan.items():
        print(f"  {k}: {v}")
    print("\n=== TOTALES ===")
    print("menús:", len(menu), "| rutas:", len(router["routes"]), "| páginas con apiFetch:", len(page_api),
          "| páginas con marcadores:", len(static_scan))


if __name__ == "__main__":
    main()
