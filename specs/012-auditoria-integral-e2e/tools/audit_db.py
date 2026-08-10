#!/usr/bin/env python3
"""Auditoría estática de base de datos: modelos SQLAlchemy.

Salidas: specs/012-auditoria-integral-e2e/evidence/database-schema-audit.json
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("KONTROL_SECRET_KEY", "x" * 40)
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_DB_URL", "sqlite+pysqlite:///:memory:")
_tmp = tempfile.gettempdir()
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", os.path.join(_tmp, "kontrol-audit-license"))
os.environ.setdefault("KONTROL_STORAGE_PATH", os.path.join(_tmp, "kontrol-audit-storage"))
os.environ.setdefault("KONTROL_BACKUP_PATH", os.path.join(_tmp, "kontrol-audit-backups"))

from app.core.config import get_settings  # noqa: E402
get_settings.cache_clear()

from app.core.database import Base, init_models  # noqa: E402
init_models()

EVID = Path("/home/maria/Proyectos/kontrol/specs/012-auditoria-integral-e2e/evidence")
EVID.mkdir(parents=True, exist_ok=True)

MONEY_FLOAT_HINT = ("amount", "price", "total", "base", "rate", "value", "monto", "precio", "iva", "igft", "retencion", "balance", "cost", "importe")
TEXT_NUMERIC_FIELDS = ("rif", "cedula", "phone", "telefono", "serial", "imei", "number", "code", "control", "account", "bank_account")

tables = []
issues = []
for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
    cols = []
    for col in table.columns:
        ctype = str(col.type)
        low = col.name.lower()
        # 1) dinero en Float
        if "FLOAT" in ctype.upper() and any(h in low for h in MONEY_FLOAT_HINT):
            issues.append({"type": "MONEY_FLOAT", "table": table.name, "column": col.name, "type": ctype})
        # 2) campos que deben ser texto pero son numéricos
        if any(t in low for t in TEXT_NUMERIC_FIELDS) and ("INT" in ctype.upper() or "FLOAT" in ctype.upper() or "NUMERIC" in ctype.upper()):
            issues.append({"type": "NUMERIC_AS_IDENTIFIER", "table": table.name, "column": col.name, "type": ctype})
        # 3) DateTime sin timezone (naive)
        if "DATETIME" in ctype.upper() and "TIMEZONE" not in ctype.upper():
            issues.append({"type": "NAIVE_DATETIME", "table": table.name, "column": col.name, "type": ctype})
        cols.append({"name": col.name, "type": ctype, "nullable": col.nullable, "pk": col.primary_key})
    tables.append({"table": table.name, "columns": cols})

(EVID / "database-schema-audit.json").write_text(
    json.dumps({"tables": tables, "issues": issues}, ensure_ascii=False, indent=2), encoding="utf-8")

print("TABLAS:", len(tables))
print("TOTAL COLUMNAS:", sum(len(t["columns"]) for t in tables))
print("ISSUES:", len(issues))
from collections import Counter
c = Counter(i["type"] for i in issues)
print("Por tipo:", dict(c))
print("\n=== ISSUES (muestra) ===")
for i in issues[:40]:
    print(f"  [{i['type']}] {i['table']}.{i['column']} : {i['type']}")
