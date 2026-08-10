#!/usr/bin/env python3
"""T-05: convierte columnas de dinero/tasas de Float a Numeric en los modelos.

Mecánico y acotado: solo las 58 columnas identificadas por la auditoría.
- money -> Numeric(18, 2)
- rate  -> Numeric(14, 6)
Añade Numeric al import de sqlalchemy cuando hace falta.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BACKEND = Path("/home/maria/Proyectos/kontrol/resources/backend")
EVID = Path("/home/maria/Proyectos/kontrol/specs/012-auditoria-integral-e2e/evidence")

data = json.loads((EVID / "database-schema-audit.json").read_text(encoding="utf-8"))
money_floats = [i for i in data["issues"] if i["type"] == "FLOAT"]

RATE_COLUMNS = {"rate", "rate_snapshot", "fiscal_rate", "exchange_rate_snapshot"}


def table_to_file() -> dict[str, Path]:
    mapping = {}
    for f in BACKEND.glob("app/modules/*/models.py"):
        text = f.read_text(encoding="utf-8")
        for m in re.finditer(r'__tablename__\s*=\s*"([^"]+)"', text):
            mapping[m.group(1)] = f
    return mapping


def transform() -> None:
    t2f = table_to_file()
    changed_files: set[Path] = set()
    total = 0
    for item in money_floats:
        table, col = item["table"], item["column"]
        f = t2f.get(table)
        if not f:
            print(f"!! tabla sin archivo: {table}")
            continue
        text = f.read_text(encoding="utf-8")
        newtype = "Numeric(14, 6)" if col in RATE_COLUMNS else "Numeric(18, 2)"
        # buscar:  col: Mapped[float ...] = mapped_column(Float
        pat = re.compile(rf"({re.escape(col)}:\s*Mapped\[[^\]]*\]\s*=\s*mapped_column\()Float")
        if not pat.search(text):
            print(f"!! no encontrado: {table}.{col}")
            continue
        text, n = pat.subn(lambda m: m.group(1) + newtype, text)
        total += n
        # añadir Numeric al import de sqlalchemy si no está
        if "Numeric" not in text.split("\n")[0][:2000] and not re.search(r"import.*\bNumeric\b", text):
            text = re.sub(r"from sqlalchemy import ([^\n]+)", lambda m: f"from sqlalchemy import {m.group(1)}, Numeric", text, count=1)
        f.write_text(text, encoding="utf-8")
        changed_files.add(f)
    print("columnas transformadas:", total, "| archivos tocados:", len(changed_files))
    for f in sorted(changed_files):
        print(" -", f.relative_to(BACKEND))


if __name__ == "__main__":
    transform()
