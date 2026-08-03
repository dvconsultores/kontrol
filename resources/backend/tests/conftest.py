"""Configuración de pruebas de KONTROL.

Define variables de entorno controladas ANTES de que se instancie
`app.core.config.Settings` (que usa lru_cache). Ningún secreto real se usa.
"""

from __future__ import annotations

import os
import tempfile

# Clave de prueba (>=32 caracteres). Nunca usar en producción.
os.environ.setdefault(
    "KONTROL_SECRET_KEY",
    "test-secret-key-0123456789abcdef0123456789abcdef",
)
os.environ.setdefault("KONTROL_ENVIRONMENT", "local")
os.environ.setdefault("KONTROL_LOG_JSON", "false")
os.environ.setdefault("KONTROL_COOKIE_SECURE", "false")
os.environ.setdefault("KONTROL_DB_URL", "sqlite+pysqlite:///:memory:")

# Rutas de volúmenes temporales escribibles (no /data en entornos de prueba).
_tmp = tempfile.gettempdir()
os.environ.setdefault("KONTROL_INSTALLATION_VOLUME_PATH", os.path.join(_tmp, "kontrol-test-license"))
os.environ.setdefault("KONTROL_STORAGE_PATH", os.path.join(_tmp, "kontrol-test-storage"))
os.environ.setdefault("KONTROL_BACKUP_PATH", os.path.join(_tmp, "kontrol-test-backups"))

# Limpieza de la caché de settings para entornos repetidos
from app.core.config import get_settings  # noqa: E402

get_settings.cache_clear()
