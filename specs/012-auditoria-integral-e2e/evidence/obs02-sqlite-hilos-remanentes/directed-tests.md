# Pruebas dirigidas O2-01…O2-20 · `directed-series-after.txt`

| Id | Qué | SQLite | PostgreSQL |
|---|---|---|---|
| O2-01 | inventario completo, UNKNOWN 0 | `threaded-test-inventory.md` | — |
| O2-02 | UoM topología actual reproducida: 1 conexión 10/10; falso verde 5/30; POC (a) 7/35 | PROVEN | — |
| O2-03 | UoM control con conexiones propias, mismo datastore: POC (b) 0/35 excepciones; O2-02 I1 ×10 `[200, 409]` | 10/10 | ×5 5/5 |
| O2-04 | invariante funcional intacta (`len(abiertas) == 1`) + contrato estático | PASS | PASS |
| O2-05 | documentos: clasificación por prueba | `documents-security-target.md` (ENVIRONMENT_BLOCKED) | — |
| O2-06 | ClamAV bloquea antes de la carrera: sí (422 `SCAN_FAILED` en `_upload`) | PROVEN | — |
| O2-07 | control `motor_para_hilos` para documentos | N/A: carrera no alcanzable y PostgreSQL por construcción | N/A |
| O2-08 | una `Session` por petición | sí (`_override_get_db`) | sí |
| O2-09 | conexión DBAPI distinta por petición tras la corrección | O2-02 `len(conexiones) == 2` | ídem |
| O2-10 | mismo datastore | O2-02 (el perdedor ve la versión del ganador: 409) y ACS-02 | ídem |
| O2-11 | excepciones de hilo visibles | PASS | PASS |
| O2-12 | vector incompleto no es PASS | O2-04 + aserción en el objetivo | ídem |
| O2-13 | ACS-01…08 | 8/8 | 8/8 |
| O2-14 | almacenes (carrera incluida) | PASS (1 skip preexistente PG-only) | PASS |
| O2-15 | auth (rotación + SA) | PASS | PASS |
| O2-16 | PostgreSQL sin cambio | — | objetivo ×10 10/10; módulos 79 passed |
| O2-17 | producto 0 | `git diff --stat -- app/` vacío | — |
| O2-18 | migración 0, esquema 0 | `git diff --stat -- alembic/` vacío | — |
| O2-19 | sin skip/xfail/retry/sleep/cerrojo/busy_timeout | O2-04; `motor_para_hilos` sin cambio (ACS-08) | — |
| O2-20 | orden: objetivo sola ×20 y módulo ×10 | 20/20 · 10/10 | 10/10 |

Series: 55/55 corridas PASS; 59 passed + 1 skipped (controles SQLite); 79 passed (PostgreSQL).
