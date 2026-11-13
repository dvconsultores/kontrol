# Estados §3 · atribución final de la línea base de QA

**Ciclo:** `SPEC018_ZONA_TEMPORAL`, preflight §5, 2026-11-12.

**Qué se revisó:** la suite completa del cierre de §3 (`EVIDENCE.md`). Llegó al 100 % y su resumen corto dio 74 fallos y 72 errores, pero no escribió la línea final. Su atribución se apoyaba en corridas aisladas de cada familia.

**Cómo se comprobó:** no se repitió la suite completa. Se volvieron a correr una vez, sobre el HEAD reconciliado `4a5efc9`, solo las familias señaladas, con la orden canónica:
- `PATH` con los binarios de PostgreSQL de QA;
- `eval "$(python3 qa/clamav_qa.py entorno)"` (ClamAV real);
- `KONTROL_TEST_DB_URL=…/ktest`.

**Resultado (familias de documentos, respaldo PostgreSQL, `iso_relaciones_inv_md`, `n9_integrity`, `pg_harness_lifecycle` y las pruebas de §3):** 289 PASS, 1 skip y 3 fallos. Los 3 fallos eran de `pg_harness_lifecycle` y se produjeron porque, a la vez, corría otra suite de este ciclo sobre el mismo servidor. Repetidos en solitario: 28/28 PASS.

| Familia | ENTRY_HEAD_REPRODUCED | FINAL_HEAD_REPRODUCED | Causa de entorno | Causa de producto | Regresión nueva |
|---|---|---|---|---|---|
| `documents*` (SCAN_FAILED / FILE_NOT_SCANNED) | Sí, sin ClamAV | No: con ClamAV real, PASS | Analizador ausente; el producto falla cerrado, como debe | No | NO |
| `backup_create_pg` / `backup_restore_pg` | Sí, sin `pg_dump`/`pg_restore` en el `PATH` | No: con los binarios de QA en el `PATH`, PASS | Herramientas fuera del `PATH` | No | NO |
| `iso_relaciones_inv_md` (72 errores) | Sí, con esquemas creados en paralelo | No: PASS | Carrera al crear `btree_gist` en la corrida paralela | No | NO |
| `n9_integrity` | Sí, sin ClamAV | No: PASS | Analizador ausente | No | NO |
| `pg_harness_lifecycle` | Sí (`data_directory`, y residuos con corridas simultáneas) | Corriendo en solitario: 28/28 PASS | Permiso de superusuario o actividad paralela en el servidor | No | NO |
| `n10_convergence` (1) | Sí | Sí: solo `import_*.created_by` | — | Línea base conocida | NO |
| `naive_datetime_input` (1) | Sí | Sí | — | Línea base conocida | NO |
| `spec019_receipt` (2) | Sí | Sí | — | Línea base conocida (recepción sin líneas) | NO |

```text
NEW_FAILURES=0 (sostenido por las corridas de familias en el entorno canónico; sin repetir la suite completa)
EVIDENCE=qa local (salida fuera del repositorio: sondas/tz/atribucion.txt); pg_harness_lifecycle en solitario 28/28
```
