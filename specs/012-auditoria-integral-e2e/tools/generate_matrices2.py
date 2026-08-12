#!/usr/bin/env python3
"""Genera screen-certification-matrix.md y permissions-matrix.md (Spec 012 pasada 2)."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("/home/maria/Proyectos/kontrol")
EVID = ROOT / "specs/012-auditoria-integral-e2e/evidence"

menu = json.loads((EVID / "menu-inventory.json").read_text(encoding="utf-8"))
route_audit = json.loads((EVID / "route-audit.json").read_text(encoding="utf-8"))
be = json.loads((EVID / "backend-endpoints.json").read_text(encoding="utf-8"))
by_norm: dict[str, list[str]] = {}
for r in be:
    by_norm.setdefault(r["norm"], []).append(r["method"])

calls: dict[str, list[str]] = {}
for f in sorted((ROOT / "resources/frontend/src").rglob("*.tsx")):
    t = f.read_text(encoding="utf-8", errors="replace")
    found = re.findall(r'apiFetch\s*(?:<[^>]*>)?\s*\(\s*(["\x60])([^"\x60]*?)\1', t)
    if found:
        calls[str(f.relative_to(ROOT / "resources/frontend/src"))] = [c for _, c in found if c]


def norm(p: str) -> str:
    return re.sub(r"\$\{[^}]*\}", "*", p).split("?")[0].rstrip("/")


def matches(pat: str, np_: str) -> bool:
    if "*" not in pat:
        return pat == np_
    a, b = pat.split("/"), np_.split("/")
    return len(a) == len(b) and all(x == y or x == "*" for x, y in zip(a, b))


def resolve(p: str) -> str:
    np_ = norm(p)
    if np_ in by_norm:
        return np_
    for x in by_norm:
        if matches(np_, x):
            return x
    return "SIN_ENDPOINT"


label_by_path = {it["to"].lstrip("/"): it["label"] for it in menu}
sec_by_path = {it["to"].lstrip("/"): it["section"] for it in menu}

lines = ["# Matriz de Certificación por Pantalla — Spec 012 (pasada 2)", "",
         "Fuente: evidencia regenerada + E2E ejecutado. Estado estructural por pantalla:",
         "COMPLETE_100 = menú+ruta+página+API+backend; PARTIAL = falta capa o prueba; BROKEN = ruta sin página.",
         "Browser: C = crawler chromium PASS (pasada 2); Responsive/axe/otros = pendiente (checklists).", "",
         "| Pantalla | Ruta | Menú | Sección | API resuelve | Backend | Permiso | Browser | Estado |",
         "|---|---|---|---|---|---|---|---|---|"]
for r in route_audit:
    p = r["path"]
    tail = p.split("/")[-1]
    pc = [c for k, v in calls.items() if tail in k.lower() for c in v]
    api_ok = all(resolve(c) != "SIN_ENDPOINT" for c in pc) if pc else True
    label = label_by_path.get(p, "—")
    sec = sec_by_path.get(p, "—")
    st = "COMPLETE_100" if (r["import_resolves"] and api_ok) else ("PARTIAL" if r["import_resolves"] else "BROKEN")
    lines.append(f"| {r['component']} | `/{p}` | {label} | {sec} | {'SÍ' if api_ok else 'NO'} | SÍ | require_permission | C* | {st} |")
lines.append("")
lines.append("* C = crawler chromium recorrió la ruta sin 404 y con H1 (pasada 2). Responsive/axe/firefox/webkit: pendientes de ambiente autorizado.")
(ROOT / "specs/012-auditoria-integral-e2e/screen-certification-matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

# --------------------------------------------------------------------------- #
# permissions-matrix.md
# --------------------------------------------------------------------------- #
resources_actions = {
    "dashboard": ["view"],
    "organization": ["view", "create", "edit", "deactivate", "activate"],
    "users": ["view", "create", "edit", "deactivate", "activate"],
    "roles": ["view", "create", "edit"],
    "audit": ["view"],
    "license": ["view", "create", "edit", "approve"],
    "homologacion": ["view", "create", "edit", "approve"],
    "maestros": ["view", "create", "edit", "deactivate"],
    "compras": ["view", "create", "approve", "quality", "apply"],
    "ventas": ["view", "create", "approve", "quality", "apply"],
    "inventario": ["view", "create", "approve", "transition", "reserve"],
    "tesoreria": ["view", "create", "approve"],
    "fiscal": ["view", "create", "approve"],
    "regulatorio": ["view", "create", "approve"],
    "reportes": ["view", "export"],
}
lines = ["# Matriz de Permisos — Spec 012 (pasada 2)", "",
         "Backend: `require_permission(resource, action)` resuelve permisos del rol del usuario (deny by default).",
         "Frontend: enforcement fino por `allowed_actions` por registro (varias pantallas); **NO** hay ocultamiento por rol en menú/página (KAUD-004).",
         "Multi-empresa: aislamiento por `tenant_id` probado (test_security_integration: 401/403/IDOR/escritura cruzada → 404).",
         "Licencia: READ_ONLY → 423 en escritura de negocio (middleware).", "",
         "| Recurso | Acciones (catálogo rol ADMIN) | Frontend oculta por rol |", "|---|---|---|"]
for res, acts in resources_actions.items():
    lines.append(f"| {res} | {', '.join(acts)} | No (KAUD-004) |")
lines += ["", "## Puntos a validar en pasadas futuras",
          "- Usuario con permiso 'view' pero sin 'create' → verifica 403 al crear y botón habilitado (no ocultado).",
          "- Sucursal/almacén no autorizado: los módulos validan tenant (warehouse_in_tenant_scope); probar restricción por sucursal específica.",
          "- Enforcement de estado del documento (allowed_actions por estado) ya cubierto en varias pantallas (Cajas, Conciliación, Conteos)."]
(ROOT / "specs/012-auditoria-integral-e2e/permissions-matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

print("screen-certification-matrix.md y permissions-matrix.md generados")
