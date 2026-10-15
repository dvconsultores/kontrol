# Modelo de coste del analizador
| Elemento | Hecho (código / evidencia) |
|---|---|
| Arquitectura | `ClamAVScanner.scan()` lanza **un proceso `clamscan` por análisis** (`subprocess.run`, `--no-summary --stdout --database=<db>`, timeout 120 s); no hay demonio `clamd`: cada invocación **carga la base de firmas** (main 3,29 M + daily 0,36 M firmas) |
| Familias de pruebas con analizador real | `test_documents.py` (25 pruebas, 2 marcadas `skipif(not KONTROL_CLAMSCAN_PATH)`), `test_documents_security.py` (35), `test_documents_legacy_import.py` (8; importación sin análisis), `test_documents_migration_0024.py` (10), `test_clamav_qa.py` (preflight real cuando hay ruta) |
| `PROVISIONING_TIME` | ≈ 3 min 54 s una sola vez (descarga + firmas); **no** forma parte de la suite (caché) |
| `PREFLIGHT_TIME` | ≈ 14,4–14,6 s (E2E con `--con-analizador` y `test_clamav_qa` real: dos análisis + arranque sin firmas) |
| `PER_SCAN_TIME` | ≈ 7–8 s observados (ClamAV cycle, carga de firmas por proceso); se mide exactamente en la etapa 1 con un envoltorio de medición **fuera del repositorio** que registra cada invocación |
| `TEST_EXECUTION_TIME` | el resto de la prueba (HTTP, BD, hash) es de milisegundos |
| Comparación válida | contar invocaciones reales y su duración dentro de la suite canónica (sin apagar el analizador); `SCANNER_OFF_COMPARISON_INVALID = YES` para una suite completa con `KONTROL_DOCUMENT_SCAN=off` (cambia la semántica: SKIPPED en vez de CLEAN y pruebas de rechazo distintas) |
