#!/usr/bin/env python3
"""Regenera backend-orphan-endpoints.json con extracción robusta de apiFetch."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("/home/maria/Proyectos/kontrol")
EVID = ROOT / "specs/012-auditoria-integral-e2e/evidence"


def extract_calls(text: str) -> list[str]:
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
                end = text.find(q, i)
                if end != -1:
                    out.append(text[i:end])
    return out


calls = []
for f in sorted((ROOT / "resources/frontend/src").rglob("*.tsx")):
    calls += extract_calls(f.read_text(encoding="utf-8", errors="replace"))


def norm(p: str) -> str:
    return re.sub(r"\$\{[^}]*\}", "*", p).split("?")[0].rstrip("/")


fcall_set = {norm(c) for c in calls if norm(c)}
be = json.loads((EVID / "backend-endpoints.json").read_text(encoding="utf-8"))


def matches(pat: str, np_: str) -> bool:
    if "*" not in pat:
        return pat == np_
    a, b = pat.split("/"), np_.split("/")
    return len(a) == len(b) and all(x == y or x == "*" for x, y in zip(a, b))


orphans = []
for r in be:
    np_ = r["norm"]
    if np_ in fcall_set:
        continue
    if any(matches(c, np_) for c in fcall_set if "*" in c):
        continue
    orphans.append(r)

(EVID / "backend-orphan-endpoints.json").write_text(json.dumps(orphans, indent=2), encoding="utf-8")

sysp = [r for r in orphans if any(s in r["path"] for s in ("docs", "openapi", "health"))]
authp = [r for r in orphans if any(s in r["path"] for s in ("password-reset", "installation-request", "/license/", "licensing/"))]
biz = [r for r in orphans if r not in sysp and r not in authp]

print(f"Llamadas crudas: {len(calls)} | normalizadas únicas: {len(fcall_set)}")
print(f"Orphan reales: {len(orphans)} (sistema {len(sysp)} | auth/licencia {len(authp)} | negocio sin UI {len(biz)})")
print("=== negocio sin UI ===")
for r in biz:
    print(f"  {r['method']:6} {r['path']}")
