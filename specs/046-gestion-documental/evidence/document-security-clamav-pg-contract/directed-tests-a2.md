# Pruebas dirigidas con el analizador real · CLAM-01…15 y DOCENV-01…20 (`directed-series-a2.txt`)

Entorno: `eval "$(python qa/clamav_qa.py entorno)"` (motor 1.4.3; main 63 · daily 28153 · bytecode 339).

| Id | Qué | Resultado |
|---|---|---|
| CLAM-01 | aprovisionamiento sin sudo, solo en el prefijo (dobles de descarga/extracción/firmas) | PASS |
| CLAM-02 | idempotente: segunda provisión sin descargas (doble) y real: 14,4 s sin bajar nada (`provisioning-run.txt`) | PASS |
| CLAM-03 | versión distinta de 1.4.x rechazada | PASS |
| CLAM-04/05/06 | preflight real: motor 1.4.x, tres bases con versión y fecha, PDF CLEAN, EICAR INFECTED | PASS (SQLite y PostgreSQL) |
| CLAM-07 / CLAM-08 | sin binario / sin firmas: el preflight falla y lo dice (QAC-01/02, QAC-03) | PASS |
| CLAM-09 | firmas rotas con el analizador real: rc ∉ {0, 1}, nunca CLEAN | PASS |
| CLAM-10 / 10b | binario que falla al analizar (rc 2) / que dice OK a todo: el preflight falla (QAC-03/04, QAC-05) | PASS |
| CLAM-11 | variables exactas que lee `scanning.ClamAVScanner` | PASS |
| CLAM-12 | prefijo fuera del repositorio; `git ls-files` sin `.deb/.cvd/.cld` | PASS |
| CLAM-13 | sin `sudo`/instalación en el sistema; `apt-get download` + `dpkg-deb -x` + suma verificada | PASS |
| CLAM-14 / CLAM-15 | producto sin referencia al provisionador; `Dockerfile.backend` sin cambio | PASS |
| runner | `--con-analizador` exige `clamav_qa.asegurar()` y no arranca sin él | PASS (contrato) |
| DOCENV-01 | sin analizador: 422 `SCAN_FAILED` (ciclo anterior; contrato intacto) | PROVEN |
| DOCENV-02/03/04 | PDF limpio aceptado, EICAR rechazado (`FILE_INFECTED`, nada almacenado), error de proceso → `SCAN_FAILED` | PASS con analizador real: `test_documents.py` y `test_documents_security.py` completos en PostgreSQL |
| DOCENV-05…11 | las siete carreras en PostgreSQL: 409 del perdedor, misma clave, tenant, una V2, tres a la vez, documentos distintos no se esperan, primera versión | **PASS (ejecutadas de verdad)** |
| DOCENV-12/13 | SQLite: 9 nodos omitidos con razón; cobertura no concurrente ejecutada con analizador (75 passed) | PASS |
| DOCENV-14/15 | sin bypass; `SCAN_FAILED` nunca aceptado | PASS (contrato) |
| DOCENV-16 | OpenAPI | sin cambio (producto 0) |
| DOCENV-17 | UoM/almacenes/auth/ACS | 78 passed + 1 skip |
| DOCENV-18 | las cuatro E2E con analizador | véase `global-e2e-a2.md` |
| DOCENV-19/20 | producción intacta · migración/esquema 0 | sí |

Corridas: SQLite documentos + CLAM: **7 failed · 75 passed · 9 skipped** (374 s; los 7 = OBS-10 `legacy_import`, no del
analizador; los 9 = 7 carreras + SVG + contrato); PostgreSQL documentos + n9 + CLAM: **93 passed · 1 skipped** (663 s): los 35
fallos del analizador, los 2 de n9 y las siete carreras pasan. Tiempo: cada subida analiza de verdad (≈ 7–8 s).
