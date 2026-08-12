#!/usr/bin/env python3
"""Genera database-inventory.md desde database-schema-audit.json (Spec 012 pasada 2)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("/home/maria/Proyectos/kontrol")
EVID = ROOT / "specs/012-auditoria-integral-e2e/evidence"
d = json.loads((EVID / "database-schema-audit.json").read_text(encoding="utf-8"))
tables = d["tables"]  # list[ {table, columns} ]
issues = d["issues"]

mod_prefix = {}
col_count = 0
for entry in tables:
    t = entry["table"]
    cols = entry["columns"]
    col_count += len(cols)
    mod = t.split("_")[0] if t != "audit_events" else "audit"
    mod_prefix.setdefault(mod, []).append(t)

lines = ["# Inventario de Base de Datos — Spec 012 (pasada 2)", "",
         f"Modelos SQLAlchemy inventariados: **{len(tables)} tablas** · {col_count} columnas.",
         "Nota: la herramienta reporta sobre metadata ORM (SQLite no concluye tipos reales PG).", "",
         "## Resumen por prefijo de módulo", "", "| Módulo (prefijo) | Tablas |", "|---|---|"]
for mod, tl in sorted(mod_prefix.items()):
    lines.append(f"| `{mod}_*` | {len(tl)} |")
lines += ["", "## Drift ORM ↔ Alembic", "",
          "- Head de migraciones: `0013_seed_business_permissions` (single head, sin ramas).",
          "- Cadena 0001→0013 compila offline en dialecto PostgreSQL (`tests/test_migrations_offline.py`, 3 PASS).",
          "- Money/tasas: **54 columnas Float restantes** (18 dinero crítico — ver KAUD-011); el resto en Numeric(18,2)/(14,6).",
          "- `DateTime(timezone=True)` en ORM (48 usos); el reporte `DATETIME` (334) es falso positivo de SQLite.",
          "- 1 columna BIGINT: `fiscal_number_series.next_number` (contador de correlativos).",
          "- Verificación final de drift real (alembic check / upgrade) **pendiente en PostgreSQL** (ambiente autorizado).",
          "", "## Tablas (muestra por módulo)", ""]
for mod, tl in sorted(mod_prefix.items()):
    lines.append(f"### `{mod}_*` ({len(tl)})")
    lines.append("")
    for t in sorted(tl):
        lines.append(f"- `{t}`")
    lines.append("")

(ROOT / "specs/012-auditoria-integral-e2e/database-inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"database-inventory.md generado: {len(tables)} tablas, {col_count} columnas")
