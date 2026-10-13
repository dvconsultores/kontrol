# Análisis de `Settings` / `get_settings` (SPEC001) frente al volumen de instalación

| Registro | Valor |
|---|---|
| Definición | `app/core/config.py:75` `installation_volume_path: str = "/data/license-state"`; `get_settings` `@lru_cache` (líneas 111-114) construye `Settings()` desde el entorno (pydantic-settings) |
| `SETTINGS_ACCESS_PATTERN` | el servicio de licencias llama `get_settings()` **en tiempo de ejecución** en cada uso: `_private_key_path()` (línea 58-59), `resolve_key_reference` (79), `get_or_create_installation` (`os.makedirs(get_settings().installation_volume_path)`, 145) |
| `IMPORT_TIME_CAPTURE` | `app/main.py:47` `settings = get_settings()` (usa `app_name`, `app_version`, `environment`, `cors_origins`, `api_prefix`; **no** el volumen) y `central_authority/alembic/env.py:25` (migraciones de la Autoridad; sin volumen). Ningún módulo captura `installation_volume_path` al importar |
| `RUNTIME_LOOKUP` | sí, para el volumen: tras `get_settings.cache_clear()` el siguiente `_private_key_path()` lee la variable actual |
| `CACHE_BEHAVIOR` | `lru_cache` sin argumentos: una única instancia hasta `cache_clear()`; los mundos ya lo invocan al cambiar `ANCLA`/`TRUST_KEYS` (patrón existente en 30+ ficheros) |
| `BEFORE_SCOPE_CLEAR` / `AFTER_SCOPE_CLEAR` | el arnés debe limpiar la caché **al fijar** la variable del ámbito y **al restaurarla** (si no, la instancia cacheada apunta al volumen anterior) |
| Producto | **0 cambios necesarios**: no hay captura del volumen en tiempo de importación ni referencias globales al camino |
