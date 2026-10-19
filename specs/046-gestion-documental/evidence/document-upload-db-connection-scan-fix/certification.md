# Certificación — B1 (DOCUMENT-UPLOAD-HOLDS-DB-CONNECTION-DURING-SCAN)

**Árbol certificado:** HEAD `ecd756a` + `documents/api.py` (+6 líneas) + `tests/test_document_upload_connection_boundary.py`.
Todas las corridas usan `clamscan` real (`--con-analizador`).

| Puerta | Corrida | Resultado | Línea base | Veredicto |
|---|---|---|---|---|
| SQLite #1 | `r20261019t145513p1413553n885712` | rc 0 · **1885/0/1046** · 691,2 s · NORMAL | 1876/0/1046 (+9 nuevas) | PASS |
| SQLite #2 | `r20261019t150659p1495543nbff1f9` | rc 0 · **1885/0/1046** · 691,1 s · NORMAL | 1876/0/1046 (+9 nuevas) | PASS |
| PostgreSQL | `r20261019t151844p1578284nd886b1` | rc 1 · **2904/1/26** · 1979,6 s · NORMAL (1,37× la mediana) | 2896/0/26 (+9 nuevas) | **1 FALLO PREVIO ATRIBUIDO**, ver `postgres-failure-attribution.md` |
| E2E | `r20261019t161819p1920149n31f7ef` | rc 0 · **284/0/0** · suite 309,2 s · limpieza LIMPIA · protegidas sin cambio | 284/0/0 | PASS |
| OpenAPI | — | **544/533/11**, esquema `BearerAccessToken` | 544/533/11 | PASS, OPENAPI_CHANGE = 0 |

- **PostgreSQL:** el fallo es `test_e2ecorrida_01`. La huella de `ktest` cambió por el autovacuum y autoanalyze de
  catálogos dentro de la ventana de la corrida simulada. El experimento controlado lo separa de B1:
  - X1, con la prueba nueva: 234/0/9;
  - X2, sin ella: 1 fallo.
- **2904 pasan:** son 2896 + 8. La novena prueba nueva pasa; el contador sale de las 2905 previstas menos el fallo
  ajeno.

## E2E — equipo y telemetría

- **Precheck:** MemAvailable 4,6 GB, swap usada 3,5 GB, carga 0,41, puertos 8000 y 5173 libres, 0 clamscan.
- **Muestreo de 1 Hz:** 321 muestras. Memoria disponible mínima 827 MB, swap máxima 8 308 MB, carga máxima 9,94, hasta
  5 clamscan simultáneos.
- **`backend.log`:** 0 `QueuePool limit`, 0 «Error no controlado», 0 respuestas 500.
- **Lectura:** con una presión del equipo mayor que la de la E2E 273/7 de `f93232b`, no hubo agotamiento del pool. La
  carga documental ya no retiene su conexión durante clamscan.

## Revalidación dirigida

- **`tests/test_documents*.py`** con el producto nuevo, que cubre documentos, seguridad, almacenamiento, idempotencia,
  carreras y contrato de carreras:
  - SQLite: 111/0/27;
  - PostgreSQL: 129/0/9.
- **Middleware de licencia, auditoría, escaneo e idempotencia:** incluidos en las suites completas; las corridas SQLite
  no tienen fallos.
- **Prueba nueva:** 9/9 en los dos motores, sola, en orden inverso y en módulo. En rojo contra HEAD falla 5/9.
