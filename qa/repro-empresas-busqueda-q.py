"""Reproduce EMPRESAS-BUSQUEDA-Q contra un backend en 127.0.0.1:8000 sobre la base de QA sembrada con `qa/e2e-seed.sh`.

Uso:  <python> qa/repro-empresas-busqueda-q.py [pre|post]

Para `uab` (DEMO, D1 y D2) y `uc` (DEMO2, E1) lista las empresas sin `q`, con `q` vacía, con un
término inexistente, con términos que coinciden por razón social, RIF y código, y con un parámetro
desconocido. No escribe nada.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("KONTROL_E2E_API", "http://127.0.0.1:8000/api/v1")
PW = os.environ.get("KONTROL_E2E_PASSWORD", "Kontrol2026Segura!")
TERMINOS = (None, "", "ZZZ-NO-EXISTE-EMPRESA-Q", "SEGUNDA", "segunda", "EMPRESA", "J-4047", "D1",
            "__kontrol_unknown_query_probe__=1")


def llamar(method: str, path: str, tok: str | None = None, body: dict | None = None) -> tuple[int, object]:
    cabeceras = {"Content-Type": "application/json"}
    if tok:
        cabeceras["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(API + path, method=method, headers=cabeceras,
                                 data=json.dumps(body).encode() if body else None)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


fase = sys.argv[1] if len(sys.argv) > 1 else "pre"
print(f"== FASE {fase} · GET /organization/companies · backend {API} ==")
for tenant, user in (("DEMO", "uab"), ("DEMO2", "uc")):
    _, sesion = llamar("POST", "/auth/login", body={"tenant_code": tenant, "username": user, "password": PW})
    tok = sesion["access_token"]  # type: ignore[index]
    for q in TERMINOS:
        sufijo = "" if q is None else "?" + (q if "=" in q else "q=" + urllib.parse.quote(q))
        st, b = llamar("GET", "/organization/companies" + sufijo, tok)
        items = b["items"] if isinstance(b, dict) and "items" in b else None
        filas = [f"{c['code']}·{c['legal_name']}" for c in items] if items is not None else b
        n = f"{len(items)}/{b['total']}" if items is not None else "-"
        print(f"{user}/{tenant:5} /organization/companies{sufijo:45} -> {st} n={n} {filas}")
