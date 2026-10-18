# Contrato de configuración
| Variable | Tipo / validación | Por defecto | Uso |
|---|---|---|---|
| `KONTROL_DOCUMENT_SCAN` | `on` / `off|false|0` (contrato previo, sin cambio) | `on` | apagado **explícito y auditable** → `DisabledScanner` (`SKIPPED`, solo aceptable con `scan_required = false`) |
| `KONTROL_DOCUMENT_SCANNER` | `^(clamscan|clamd)$` (pydantic; otro valor → `ValidationError` al arrancar) | `clamscan` | elección **explícita** del adaptador; la composición de producción fija `clamd` |
| `KONTROL_CLAMD_HOST` | cadena no vacía | `clamd` (nombre DNS del servicio) | sin IP fija |
| `KONTROL_CLAMD_PORT` | entero 1–65535 | `3310` | puerto interno de la red de Compose |
| `KONTROL_CLAMSCAN_PATH` / `KONTROL_CLAMAV_DB` | (sin cambio) | — | solo para `clamscan` (QA, desarrollo) |
Reglas: no hay valor que apague el análisis por accidente (`off` sigue siendo deliberado); no hay secretos nuevos; el
frontend no interviene; `clamd` que falla → `SCAN_FAILED` (nunca `clamscan`, nunca «sin análisis»). Defaults seguros: el
valor por defecto `clamscan` conserva el comportamiento de QA/desarrollo y, en producción, `compose.yaml` fija `clamd`
explícitamente (sin ambas cosas el producto sigue fallando cerrado).
