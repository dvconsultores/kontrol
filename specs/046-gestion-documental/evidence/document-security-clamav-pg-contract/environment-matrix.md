# Matriz de entornos

| Entorno | Analizador requerido | Presente hoy | Mecanismo de instalación | Capa de prueba | Comportamiento si falta | Autoridad |
|---|---|---|---|---|---|---|
| Desarrollo local | configurable (defecto `on`) | no | manual (no documentado en el repo) | manual | 422 `SCAN_FAILED` en cada subida con análisis obligatorio | CL-046-09, FR-046-072 |
| Backend SQLite (`pytest tests`) | el defecto `on` lo exige para cualquier subida; solo las 2 pruebas EICAR lo declaran (`skipif(not KONTROL_CLAMSCAN_PATH)`) | no | ninguno | integración ligera | 35 fallos de subida (+7 de `legacy_import` que **no** son del analizador) | — |
| Backend PostgreSQL (`KONTROL_TEST_DB_URL`) | ídem | no | ninguno | integración (P21) | 35 fallos de subida + 2 de n9 | closeout 046 (certificado con ClamAV real) |
| E2E canónico (`qa/e2e-run.py`) | opcional: el runner detecta `clamscan` y exporta `KONTROL_E2E_SCANNER_AVAILABLE` | no | ninguno | E2E | 4 pruebas omitidas con nombre `ENTORNO-SIN-CLAMSCAN` | `qa/e2e_corrida.py` 212–230; `E2E-CUARENTA-OMITIDAS` |
| CI | no hay flujo CI en el repositorio (`.github` ausente) | — | — | — | — | — |
| Producción (solo ficheros del repo) | `Dockerfile.backend` no instala `clamav`; `compose.yaml` no fija `KONTROL_DOCUMENT_SCAN` | desconocido (no se accede) | no documentado | — | con análisis `on` y sin binario, toda subida con análisis obligatorio se rechaza (falso seguro) | — |

`CI_REQUIREMENT = n/a (sin CI en el repo)`. Observación para 046/054 (no absorbida, OBS-09): la imagen de producción no provee
el analizador que el producto usa por defecto; es una decisión de despliegue, fuera de este ciclo.
