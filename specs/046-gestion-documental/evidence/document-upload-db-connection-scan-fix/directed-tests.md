# Pruebas dirigidas y mutaciones — B1

Prueba nueva: `resources/backend/tests/test_document_upload_connection_boundary.py`.

- **Escrita por:** DeepSeek (F02b corrección 2 + F02c).
- **Montaje:** analizador controlado con `threading.Event`, sin `sleep`, `skip` ni `xfail`. Telemetría de pool,
  transacción y verbo SQL mediante `event.listen`. Pool de producción (QueuePool 5 + 10, 30 s).
- **Motores:**
  - PostgreSQL: `make_engine(pool_pre_ping=True, pool_recycle=1800)`.
  - SQLite: `motor_para_hilos`, un fichero servido con QueuePool.

| Prueba | Qué demuestra |
|---|---|
| B01 | Durante el análisis detenido, `checkedout() == 0`. No hay checkout entre el commit de la frontera y `scan_start`. Tras soltar: 200, 1 versión, 1 `DOCUMENT_FILE_UPLOADED` y checkouts == checkins. |
| B02 | Antes del análisis solo hay `SELECT`: 0 INSERT, 0 UPDATE y 0 DELETE. |
| B03 | Después del análisis, las escrituras van entre un `begin` y un único `commit`, sin commit intermedio. |
| B04 | Con el analizador real (envoltorio de `ClamAVScanner`), `checkedout() == 0` al empezar y al terminar el análisis. 200 y 1 versión. |
| B05 | INFECTED → 422 `FILE_INFECTED`, sin versión ni fichero. No se afirma nada de la auditoría de rechazo, que es otra deuda. |
| B06 | SCAN_FAILED → 422 `SCAN_FAILED`, sin versión ni fichero. |
| B07 | Idempotencia: la segunda subida da 200 `idempotent_hit` con la misma versión. El analizador se llama una vez y queda 1 versión. |
| B08 | Una escritura pendiente inyectada antes de la frontera da 500 `INTERNAL_ERROR`. El analizador no se llama. 0 filas marcadoras, 0 versiones y 0 ficheros. |
| B09 | Contrato AST: la guarda va después del primer `if idempotency_key`, el `db.commit()` inmediatamente después de la guarda, y ambos antes del `try` que llama a `service.upload_version`. |

## Resultados (con `clamscan` real)

| Ejecución | SQLite | PostgreSQL |
|---|---|---|
| Módulo | 9/0/0 | 9/0/0 |
| Orden inverso | 9/0/0 | 9/0/0 |
| Cada prueba sola (×9) | 9 × 1/0/0 | 9 × 1/0/0 |
| **Rojo contra el `api.py` de HEAD** | **5 fallos** (B01, B03, B04, B08, B09) / 4 pasan | **5 fallos** (B01, B03, B04, B08, B09) / 4 pasan |

- **Rojo contra HEAD:**
  - B01 falla con `assert 1 == 0` sobre `checkedout()`: la retención medida.
  - Las cuatro que pasan (B02, B05, B06 y B07) son contratos conservados y pasan antes y después, como corresponde.
  - El `api.py` se restauró idéntico (`cmp`).
- **ruff:** limpio.
- **mypy de `api.py`:** sin errores nuevos (los 7 de HEAD, idénticos).
- **Revalidación de las pruebas documentales existentes con el producto nuevo:** `tests/test_documents*.py`, que
  incluye seguridad, carreras VERSION_CONFLICT de PostgreSQL, idempotencia y contrato de carreras.
  - SQLite: 111/0/27.
  - PostgreSQL: 129/0/9.
  - Las omisiones son las preexistentes por motor, las carreras marcadas de DOCENV-12.

## Mutaciones (`mutations.json`)

- **Resultado:** 14 significativas. KILLED 14, SURVIVED 0, EQUIVALENT 0, RESTORED 14/14, con producto idéntico
  verificado por `cmp`.
- **Ejecución:** con `PYTHONDONTWRITEBYTECODE=1` y `__pycache__` purgado en cada paso.

| ID | Mutación | La mata |
|---|---|---|
| M01 | quitar el commit de B1 | B01 |
| M02 | mover B1 después del servicio | B01 |
| M03 | mover B1 antes de la búsqueda del documento | B01 |
| M04 | mover B1 antes de la idempotencia | B09 |
| M05 | eliminar la guarda | B08 |
| M06 | invertir la guarda | B01 |
| M07 | `rollback` en vez de `commit` | B01 |
| M08 | forzar un checkout (`db.execute(select(1))`) antes del análisis | B01 |
| M09 | saltar el analizador | B01 |
| M10 | aceptar INFECTED | B05 |
| M11 | romper la idempotencia | B07 |
| M12 | romper la conversión VERSION_CONFLICT → acierto idempotente | `test_la_misma_clave_en_carrera_devuelve_la_version_ganadora` (PostgreSQL; neutro en SQLite, donde la carrera no existe) |
| M13 | perder `DOCUMENT_FILE_UPLOADED` | B01 |
| M14 | intercambiar los códigos de error del análisis | B05 |

No se mutó deuda ajena: archivado, borrado y auditoría de rechazo.
