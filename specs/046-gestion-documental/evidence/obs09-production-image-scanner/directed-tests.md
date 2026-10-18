# Pruebas dirigidas
## O09-01…25 (`tests/test_documents_clamd.py`, 29 pruebas con `ClamdFalso`; 9,3 s)
| Id | Qué fija | Resultado |
|---|---|---|
| O09-01 | `stream: OK` → CLEAN, `scanner = clamd`, sin firma | PASS |
| O09-02 | `stream: <firma> FOUND` → INFECTED con firma | PASS |
| O09-03 | conexión rechazada → SCAN_FAILED `connection_refused` | PASS |
| O09-04 | el demonio cierra al conectar → SCAN_FAILED | PASS |
| O09-05 | tiempo agotado → SCAN_FAILED `timeout` en el plazo del adaptador | PASS |
| O09-06 | respuesta fuera del protocolo → `protocol_error` (respuesta recortada) | PASS |
| O09-07 | respuesta truncada o desbordada → `truncated_response` | PASS |
| O09-08 | orden `zINSTREAM\0`, el contenido viaja íntegro, la ruta nunca, trozos ≤ 64 KiB | PASS |
| O09-09 | 3 MiB + 17 B → 49 trozos (48 × 64 KiB + 17 B) | PASS |
| O09-10 | 50 MiB (máximo documental) → 800 trozos, CLEAN | PASS |
| O09-11 | el máximo + 1 lo corta KONTROL (413) antes del análisis; el adaptador no decide tamaños | PASS |
| O09-12 | selección `clamd` explícita por configuración (host, puerto, timeout 120 s) y singleton | PASS |
| O09-13 | `clamscan` explícito y predeterminado; `off` sigue siendo deliberado | PASS |
| O09-14 | sin alternativa implícita: clamd caído sigue siendo clamd y SCAN_FAILED; `get_scanner` sin `try`; el cuerpo del adaptador no menciona clamscan/Disabled/subprocess | PASS |
| O09-15 | seis modos de fallo → SCAN_FAILED; el servicio solo acepta CLEAN (literal intacto) | PASS |
| O09-16 | el adaptador no conoce el almacén documental | PASS |
| O09-17 | host configurable, nombre de servicio por defecto, sin IP fija, vacío inválido | PASS |
| O09-18 | puerto 0, −1, 65536, 70000, `abc` inválidos; 3310/`"3311"` válidos (5 casos) | PASS |
| O09-19 | el contenido no aparece en ningún resultado; sin `logging`/`print` en el módulo | PASS |
| O09-20 | FOUND → INFECTED con firma (incluido `Heuristics.Limits.Exceeded`) | PASS |
| O09-21 | solo `stream: OK` exacto es CLEAN; `OKAY`, `ok`, vacío → protocol_error; `OK FOUND` → INFECTED | PASS |
| O09-22 | `… ERROR` → scanner_error; `UNKNOWN COMMAND` → protocol_error; bytes raros no limpian; respuesta recortada a 200 | PASS |
| O09-23 | `clamav`, `CLAMD`, `off`, vacío… → `ValidationError` al construir `Settings` | PASS |
| O09-24 | el adaptador no usa base de firmas ni binario; `Dockerfile.backend` sin ClamAV | PASS |
| O09-25 | el demonio cae tras arrancar → SCAN_FAILED y sigue así (sin reintento ni alternativa) | PASS |
## CLAMD-QA-01…11 (`tests/test_clamd_qa.py`, 15 pruebas; 2,6 s)
Configuración local = despliegue con directivas locales sustituidas y límites intactos · límites 60M/60M/100M ≥ 50 MiB · versión del
protocolo · contrato estático de imagen y composición (todos los campos) · aprovisionamiento idempotente sin privilegios · demonio
falso: arranque, PONG, parada y carpeta eliminada · demonio que muere → declarado y sin residuos · 4 servidores de fallo + corte del
flujo → ramas exactas de SCAN_FAILED con el adaptador real · veredicto que no aprueba con una sola desviación (incluido fail-open
y ruta en el flujo) · runtime declarado y orden `estatico` · contrato estático del QA.
## Demonio real (`python qa/clamd_qa.py certificar`, rc 0; `clamd-qa-report.json`)
clamd 1.4.3 · firmas 28153 (2026-10-14) · arranque 6,3 s · CLEAN 3 ms · EICAR `Eicar-Test-Signature` 3 ms · 3 MiB 0,16 s ·
**50 MiB 1,6 s CLEAN** · 50 MiB + 1 CLEAN · 60 MiB + 1 → `scanner_error` (`INSTREAM size limit exceeded. ERROR`) · caído →
`connection_refused` · cuelga → `timeout` 2,0 s · basura → `protocol_error` · truncada → `truncated_response` · corte →
`truncated_response` · ERROR → `scanner_error` · ruta en el flujo: NO · 12/12 veredictos · estático 20/20 · runtime: `COMPOSE_RUNTIME_UNAVAILABLE`.
## Regresiones (con `clamscan` real; `-o addopts= -p no:cacheprovider`)
| Conjunto | SQLite | PostgreSQL |
|---|---|---|
| O09 + CLAMD-QA + documentos (7 módulos) + n9 + reporting + clamav_qa + almacén (O06) + telemetría (O12) + volumen + motor_para_hilos + UoM + almacenes + auth + licenciamiento + migraciones + keepalive + ciclo E2E (+ `test_e2e_corrida` en PG) | **278 passed · 0 failed · 54 skipped** (487 s) | **342 passed · 0 failed · 9 skipped** (765 s) |
Residuos propios tras las dirigidas: 0 (los 22 `kontrol-qa-clamd-*` que dejaba el arranque fallido de CQ-07 motivaron la
corrección de `Demonio._limpiar()`; ahora CQ-07 exige que no quede carpeta).
