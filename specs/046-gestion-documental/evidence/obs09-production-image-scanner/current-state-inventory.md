# Inventario del estado actual (etapa 1, solo lectura)
| Registro | Valor |
|---|---|
| `CURRENT_SCANNER_ARCHITECTURE` | `FileSecurityScanner` (ABC: `scan(path)`, `available()`) con dos adaptadores: `ClamAVScanner` (`clamscan` por proceso) y `DisabledScanner` (`SKIPPED`, solo con `KONTROL_DOCUMENT_SCAN=off`); selección en `get_scanner()` por la variable de entorno, singleton de módulo `_scanner`; `set_scanner()` para pruebas |
| `CURRENT_SCANNER_IMPLEMENTATION` | `app/modules/documents/scanning.py` (145 líneas): `subprocess.run([clamscan, --no-summary, --stdout, --database=…, path], timeout=120)`; rc 0 → CLEAN, 1 → INFECTED (firma de la línea `FOUND`), otro → `SCAN_FAILED`; `TimeoutExpired`/`OSError` → `SCAN_FAILED` |
| `CURRENT_RUNTIME_DEPENDENCY` | binario `clamscan` (`KONTROL_CLAMSCAN_PATH` o `PATH`) y base de firmas (`KONTROL_CLAMAV_DB`) **en el mismo contenedor del backend** |
| `CURRENT_FAIL_CLOSED_CONTRACT` | sin binario → `SCAN_FAILED` (`scanner_unavailable`); error → `SCAN_FAILED`; `service.upload_version` rechaza con 422 `SCAN_FAILED`/`FILE_INFECTED` todo lo que no sea `CLEAN` cuando `doc_type.scan_required` y audita `DOCUMENT_SCAN_REJECTED` |
| `CURRENT_TIMEOUT_CONTRACT` | 120 s por análisis (`ClamAVScanner.__init__`) |
| `CURRENT_UPLOAD_CALL_GRAPH` | `api` → `service.upload_version`: temporal → tamaño (`max_size = min(doc_type.max_size_bytes or GLOBAL_MAX_SIZE, GLOBAL_MAX_SIZE)`, corte temprano 413 `FILE_TOO_LARGE`) → MIME real → política → `scanning.get_scanner().scan(temp_path)` → hash → `get_storage().put` → verificación → `StoredFile` + `FileSecurityScan` |
| `CURRENT_SCANNER_CONFIGURATION_OWNER` | variables de entorno leídas directamente en `scanning.py` (no en `Settings`): `KONTROL_DOCUMENT_SCAN`, `KONTROL_CLAMSCAN_PATH`, `KONTROL_CLAMAV_DB` |
| `CURRENT_PRODUCTION_COMPOSE_STATE` | `compose.yaml`: servicios `frontend`, `backend`, `watchtower` (perfil); **ningún servicio de analizador**; el backend no recibe ninguna variable de analizador → `ClamAVScanner()` sin binario → toda subida con `scan_required` falla cerrada con 422 `SCAN_FAILED` |
| `CURRENT_DOCUMENT_MAX_SIZE` | `GLOBAL_MAX_SIZE = 50 MiB` (`service.py:48`; por tipo puede ser menor); `Settings.max_upload_bytes` (25 MiB) **no** interviene en documentos |
| `CURRENT_CLAMSCAN_INVOCATION` | un proceso por análisis; carga de firmas en cada proceso: ≈ 6,4 s (OBS-12) |
| `CURRENT_CLAMAV_SIGNATURE_SOURCE` | en producción: ninguna; en QA: `qa/clamav_qa.py` (`freshclam` al prefijo de usuario) |
| `CURRENT_QA_SCANNER_BOOTSTRAP` | `qa/clamav_qa.py provisionar|preflight|entorno` (decisión A + A2); `qa/e2e-run.py --con-analizador`; `qa/suite_tiempos.py --con-analizador` |
| `CURRENT_SCANNER_LOGGING_BEHAVIOR` | no registra contenido; `details` lleva `reason`/`code`; la firma detectada se audita (`DOCUMENT_SCAN_REJECTED`) |
| `Dockerfile.backend` | `python:3.13-slim`, `curl`, requisitos, `app/`, `alembic`, usuario `kontrol` (uid 10001), sin ClamAV; `HEALTHCHECK` por `/health/live` |
| Imagen actual construida localmente | **no medible aquí** (`BASE_BACKEND_IMAGE_SIZE`, `BASE_BUILD_TIME`: `COMPOSE_RUNTIME_UNAVAILABLE`); por construcción del `Dockerfile.backend`: `BASE_BACKEND_HAS_CLAMSCAN = NO`, `BASE_BACKEND_HAS_SIGNATURES = NO`, `BASE_UPLOAD_WITHOUT_SCANNER_RESULT = 422 SCAN_FAILED` (probado en el ciclo ENTORNO-SIN-CLAMSCAN: 35 pruebas documentales fallaban sin analizador exactamente así) |
Spec 046 FR-046-072: «El análisis es una capacidad de despliegue configurable; sin analizador, el estado es `SKIPPED` y se
declara» — en la implementación vigente el `SKIPPED` solo existe con `KONTROL_DOCUMENT_SCAN=off` (deliberado); un analizador
configurado y ausente es `SCAN_FAILED`.
