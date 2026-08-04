"""Seeds idempotentes de la fundación (FR-001-082, CHK-DB-002).

Se ejecutan con `python -m scripts.seed`. No sobrescriben datos del
cliente; solo crean catálogos base si no existen. Las reglas fiscales
legales NO se siembran aquí (se gestionan versionadas y con fuente).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.database import Base, get_engine, get_session_factory, init_models  # noqa: E402
from app.modules.inventory.models import MovementType  # noqa: E402
from app.modules.master_data.models import UnitOfMeasure  # noqa: E402
from app.modules.system.models import FeatureFlag, SystemSetting  # noqa: E402

FEATURE_FLAGS = [
    ("mfa", "Fase posterior: habilitar MFA completo"),
    ("fiscal_emission", "Deshabilitado en fundación: emisión fiscal fuera de alcance"),
    ("document_storage", "Almacenamiento documental local activo"),
    ("notifications_email", "Notificaciones por correo (SMTP diferido)"),
]

# Unidades de medida base (002-maestros, FR-002-030). Globales (company_id=None).
BASE_UNITS = [
    {"code": "UND", "name": "Unidad", "dimension": "CANTIDAD", "symbol": "u", "decimals": 2},
    {"code": "KG", "name": "Kilogramo", "dimension": "MASA", "symbol": "kg", "decimals": 3},
    {"code": "G", "name": "Gramo", "dimension": "MASA", "symbol": "g", "decimals": 2},
    {"code": "LT", "name": "Litro", "dimension": "VOLUMEN", "symbol": "L", "decimals": 3},
    {"code": "ML", "name": "Mililitro", "dimension": "VOLUMEN", "symbol": "mL", "decimals": 2},
    {"code": "HORA", "name": "Hora", "dimension": "TIEMPO", "symbol": "h", "decimals": 2},
    {"code": "DIA", "name": "Día", "dimension": "TIEMPO", "symbol": "d", "decimals": 0},
    {"code": "CJA", "name": "Caja", "dimension": "EMPAQUE", "symbol": "cja", "decimals": 0},
]

# Tipos de movimiento base (003-inventario-logistica, FR-003-023). Globales.
BASE_MOVEMENT_TYPES = [
    {"code": "ENTRADA_RECEPCION", "name": "Entrada por recepción", "direction": "IN"},
    {"code": "SALIDA_DESPACHO", "name": "Salida por despacho", "direction": "OUT"},
    {"code": "TRANSFERENCIA_SALIDA", "name": "Salida por transferencia", "direction": "OUT"},
    {"code": "TRANSFERENCIA_ENTRADA", "name": "Entrada por transferencia", "direction": "IN"},
    {"code": "AJUSTE_POSITIVO", "name": "Ajuste positivo (entrada)", "direction": "IN"},
    {"code": "AJUSTE_NEGATIVO", "name": "Ajuste negativo (salida)", "direction": "OUT"},
    {"code": "CONTEO", "name": "Ajuste por conteo (diferencia)", "direction": "INTERNAL"},
    {"code": "DEVOLUCION_CLIENTE", "name": "Devolución de cliente", "direction": "IN"},
    {"code": "DEVOLUCION_PROVEEDOR", "name": "Devolución a proveedor", "direction": "OUT"},
    {"code": "REVERSO", "name": "Reverso de movimiento", "direction": "INTERNAL"},
]


def seed() -> None:
    init_models()
    Base.metadata.create_all(get_engine())
    db = get_session_factory()()

    created_flags = 0
    for key, _description in FEATURE_FLAGS:
        flag_exists = db.execute(select(FeatureFlag).where(FeatureFlag.key == key)).scalars().first()
        if not flag_exists:
            db.add(FeatureFlag(key=key, enabled=(key == "document_storage"), audience="ALL", created_by="seed"))
            created_flags += 1

    # Configuración por defecto de la fundación (claves documentadas).
    defaults = {
        "ui.theme": {"name": "light"},
        "observability.log_json": True,
        "security.password_min_length": 10,
    }
    created_settings = 0
    for key, value in defaults.items():
        setting_exists = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalars().first()
        if not setting_exists:
            db.add(SystemSetting(key=key, value=value, updated_by="seed", created_by="seed"))
            created_settings += 1

    # Unidades de medida base (idempotente).
    created_units = 0
    for u in BASE_UNITS:
        unit_exists = db.execute(select(UnitOfMeasure).where(UnitOfMeasure.code == u["code"], UnitOfMeasure.company_id.is_(None))).scalars().first()
        if not unit_exists:
            db.add(UnitOfMeasure(company_id=None, status="ACTIVE", created_by="seed", **u))
            created_units += 1

    # Tipos de movimiento base (idempotente, FR-003-023).
    created_mtypes = 0
    for m in BASE_MOVEMENT_TYPES:
        mtype_exists = db.execute(select(MovementType).where(MovementType.code == m["code"], MovementType.company_id.is_(None))).scalars().first()
        if not mtype_exists:
            db.add(MovementType(company_id=None, status="ACTIVE", affects_balance=True, created_by="seed", **m))
            created_mtypes += 1

    db.commit()
    db.close()
    print(f"Seed OK: {created_flags} flags, {created_settings} settings, {created_units} unidades, {created_mtypes} tipos de movimiento (0 = ya existían / idempotente)")


if __name__ == "__main__":
    seed()
