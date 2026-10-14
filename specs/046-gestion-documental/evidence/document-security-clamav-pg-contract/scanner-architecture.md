# Arquitectura del analizador (`app/modules/documents/scanning.py`, `service.py`)

| Registro | Valor |
|---|---|
| `SCANNER_INTERFACE` | `FileSecurityScanner` (ABC): `scan(path) -> ScanResult`, `available() -> bool`; resultados `PENDING_SCAN / CLEAN / INFECTED / SCAN_FAILED / SKIPPED` |
| `PRODUCTION_IMPLEMENTATION` | `ClamAVScanner` por línea de órdenes (`clamscan --no-summary --stdout [--database=…] <ruta>`; 0 limpio, 1 infectado, 2 error; timeout 120 s). Se elige `clamscan` y no el demonio «para que una instalación independiente no tenga que mantener un servicio más» |
| `EXECUTABLE` · `CONFIG_KEY` | `KONTROL_CLAMSCAN_PATH` o `shutil.which("clamscan")`; base de firmas `KONTROL_CLAMAV_DB`; `KONTROL_DOCUMENT_SCAN=off` → `DisabledScanner` (`SKIPPED`, declarado) |
| `FAIL_CLOSED_BEHAVIOR` | binario ausente → `available() False` → `ScanResult(SCAN_FAILED, reason=scanner_unavailable)`; error/timeout del proceso → `SCAN_FAILED`. En `service.upload`: si `doc_type.scan_required` y el resultado no es `CLEAN` → 422 `SCAN_FAILED` (o `FILE_INFECTED`), auditoría `DOCUMENT_SCAN_REJECTED`, nada almacenado; con `scan_required=False` el archivo se guarda con su `security_status` y **no se entrega** mientras no sea `CLEAN` (`FILE_NOT_SCANNED`) |
| `UNIT_TEST_ABSTRACTION` · `EXISTING_FAKE_SCANNER` | `set_scanner(scanner)` «para pruebas, no para producción»; `DisabledScanner` real; en `test_documents.py` un `Ausente()` ad hoc solo para probar el falso seguro; **no existe** un falso que diga `CLEAN`, y la suite de seguridad lo prohíbe como evidencia (§159: «un mock no sirve») |
| `AUTHORITY_SOURCE` | Spec 046: CL-046-09 / FR-046-072 / AC-046-28 («capacidad de despliegue configurable; sin analizador, `SKIPPED` declarado»), §26 («un analizador ausente no significa limpio»), ESC-046-01 (closeout §7: analizador **real** en QA, ClamAV 1.4.3 + `freshclam` 3,28 M firmas, EICAR) |

`UNKNOWN = 0`. Producción: `Dockerfile.backend` no instala `clamav` (solo `curl`); `compose.yaml` no define `KONTROL_DOCUMENT_SCAN` ni
`KONTROL_CLAMSCAN_PATH` (no se accede a producción; solo ficheros del repo).
