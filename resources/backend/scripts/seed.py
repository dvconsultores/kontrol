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
from app.modules.system.models import FeatureFlag, SystemSetting  # noqa: E402

FEATURE_FLAGS = [
    ("mfa", "Fase posterior: habilitar MFA completo"),
    ("fiscal_emission", "Deshabilitado en fundación: emisión fiscal fuera de alcance"),
    ("document_storage", "Almacenamiento documental local activo"),
    ("notifications_email", "Notificaciones por correo (SMTP diferido)"),
]


def seed() -> None:
    init_models()
    Base.metadata.create_all(get_engine())
    db = get_session_factory()()

    created_flags = 0
    for key, description in FEATURE_FLAGS:
        exists = db.execute(select(FeatureFlag).where(FeatureFlag.key == key)).scalars().first()
        if not exists:
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
        exists = db.execute(select(SystemSetting).where(SystemSetting.key == key)).scalars().first()
        if not exists:
            db.add(SystemSetting(key=key, value=value, updated_by="seed", created_by="seed"))
            created_settings += 1

    db.commit()
    db.close()
    print(f"Seed OK: {created_flags} feature flags, {created_settings} settings (0 = ya existían / idempotente)")


if __name__ == "__main__":
    seed()
