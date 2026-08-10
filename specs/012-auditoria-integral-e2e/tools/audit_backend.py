#!/usr/bin/env python3
"""Auditoría backend: inventario de rutas OpenAPI + comparación con llamadas frontend.

Salidas en specs/012-auditoria-integral-e2e/evidence/.
No modifica código ni datos.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

os.environ.setdefault("KONTROL_SECRET_KEY", "test-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ.setdefault("KONTROL_DB_URL", "sqlite+pysqlite:///:memory:")
_tmp = tempfile.gettempdir()
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", os.path.join(_tmp, "kontrol-audit-license"))
os.environ.setdefault("KONTROL_STORAGE_PATH", os.path.join(_tmp, "kontrol-audit-storage"))
os.environ.setdefault("KONTROL_BACKUP_PATH", os.path.join(_tmp, "kontrol-audit-backups"))

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()

from app.main import create_app  # noqa: E402

EVID = Path("/home/maria/Proyectos/kontrol/specs/012-auditoria-integral-e2e/evidence")
EVID.mkdir(parents=True, exist_ok=True)

app = create_app()
API_PREFIX = get_settings().api_prefix  # /api/v1
routes = []
for r in app.routes:
    methods = getattr(r, "methods", None)
    if methods:
        for m in sorted(methods - {"HEAD", "OPTIONS"}):
            p = r.path
            if p.startswith(API_PREFIX):
                p = p[len(API_PREFIX):]
            routes.append({"method": m, "path": p})

# normalizado: {param} -> *
norm = [{"method": r["method"], "path": r["path"], "norm": re.sub(r"\{[^}]+\}", "*", r["path"])} for r in routes]

(EVID / "backend-endpoints.json").write_text(
    json.dumps(norm, ensure_ascii=False, indent=2), encoding="utf-8")

by_norm = {}
for r in norm:
    by_norm.setdefault(r["norm"], []).append(r["method"])

def _pattern_matches(pat: str, norm_path: str) -> bool:
    """pat usa '*' para params; norm_path usa '*' igualmente."""
    if "*" not in pat:
        return False
    pat_parts = pat.split("/")
    p_parts = norm_path.split("/")
    if len(pat_parts) != len(p_parts):
        return False
    for a, b in zip(pat_parts, p_parts):
        if a != b and a != "*":
            return False
    return True


# ---------- Comparación con frontend ----------
fc = json.loads((EVID / "frontend-api-calls.json").read_text(encoding="utf-8"))
report = []
unmatched = []
matched = 0
for page, calls in fc.items():
    for call in calls:
        base = call.replace(" (template)", "")
        base = base.split("?")[0]
        # normalizar * (template) -> patrón
        has_param = "*" in base
        norm_call = base  # ya usa * para params
        candidates = [p for p in by_norm if p.rstrip("/") == norm_call.rstrip("/") or p == norm_call]
        status = "OK" if candidates else ("TEMPLATE_OK" if has_param and any(
            _pattern_matches(norm_call, p) for p in by_norm) else "NO_ENDPOINT")
        if status == "NO_ENDPOINT":
            unmatched.append({"page": page, "call": call})
            report.append({"page": page, "call": call, "status": "NO_ENDPOINT", "candidate": None})
        else:
            matched += 1
            report.append({"page": page, "call": call, "status": status,
                           "candidate": candidates[0] if status == "OK" else None})

(EVID / "api-coverage.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------- Dirección inversa: endpoints sin consumidor frontend ----------
frontend_call_set = set()
for page, calls in fc.items():
    for call in calls:
        base = call.replace(" (template)", "").split("?")[0]
        frontend_call_set.add(base.rstrip("/"))

orphans = []
for r in norm:
    if r["norm"].rstrip("/") in frontend_call_set:
        continue
    # template con '*' : buscar si algún call frontend lo cubre
    covered = False
    for c in frontend_call_set:
        if "*" in c and _pattern_matches(c, r["norm"]):
            covered = True
            break
    if not covered:
        orphans.append(r)
(EVID / "backend-orphan-endpoints.json").write_text(
    json.dumps(orphans, ensure_ascii=False, indent=2), encoding="utf-8")

print("Rutas backend (método+path):", len(norm))
print("Llamadas frontend comparadas:", len(report), "| OK:", matched, "| sin endpoint:", len(unmatched))
print("Endpoints backend sin consumidor frontend:", len(orphans))
print("\n=== ENDPOINTS BACKEND SIN CONSUMIDOR FRONTEND (muestra) ===")
for o in orphans[:40]:
    print(f"  {o['method']:6} {o['path']}")


def _pattern_matches(pat: str, norm_path: str) -> bool:
    """pat usa '*' para params; norm_path usa '*' igualmente."""
    if "*" not in pat:
        return False
    pat_parts = pat.split("/")
    p_parts = norm_path.split("/")
    if len(pat_parts) != len(p_parts):
        return False
    for a, b in zip(pat_parts, p_parts):
        if a != b and a != "*":
            return False
    return True
