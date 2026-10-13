# Suites completas tras la corrección (en serie, nunca a la vez; `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` purgado)

| Corrida | Resultado | Duración | Frente a la línea base |
|---|---|---|---|
| SQLite completa #1 | 1616 passed · 43 failed · 1040 skipped | 259,8 s | base 43/1582/1040 (`TEST-PG-UN-SCHEMA-POR-PRUEBA`, con la carrera manifestada): **la prueba objetivo deja de fallar**; aparece `test_auth_session_rotation.py::test_dos_renovaciones_simultaneas_no_pueden_ganar_las_dos` (ver abajo); los otros 42 son los de ClamAV ausente (`ENTORNO-SIN-CLAMSCAN`: `test_documents` 10, `test_documents_legacy_import` 7, `test_documents_security` 25) |
| SQLite completa #2 | 1616 passed · 43 failed · 1040 skipped | 261,3 s | idéntica a la #1, prueba por prueba |
| PostgreSQL completa | 2634 passed · 37 failed · 28 skipped | 862,4 s | base 38/2625/28: los 35 de ClamAV + los 2 de `test_n9_integrity`; el intermitente de reloj conocido (`test_licensing_central::…::test_sync_success_records_run_snapshot_and_event`) no falló esta vez. 0 nuevos |

Listas completas de fallos en `full-suites-failed.txt`. Ni la prueba objetivo ni `tests/test_motor_para_hilos.py` fallan en
ninguna de las tres. 0 directorios `kontrol-test-sqlite-*` tras cada suite; 0 schemas `t_` residuales (`qa/pg-test-residuos.py`:
conexiones del arnés 0).

## `test_dos_renovaciones_simultaneas_no_pueden_ganar_las_dos` (SQLite, las dos corridas)

Es `AUTH-ROTACION-SQLITE-HILOS` (OPEN, dueñas 001/054), ya presente como «intermitente de hilos; no se reclama» en las
suites completas de `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO` y `TEST-PG-UN-SCHEMA-POR-PRUEBA`. Clasificación independiente,
no «reintento hasta verde» (`auth-rotation-attribution.txt`): sola ×10 en el árbol de este ciclo, **9/10 FAIL**; sola ×10
sobre `git archive` de `ffdbaf6` (sin este ciclo), **8/10 FAIL**. Preexistente e independiente del ciclo. Firma de hoy:
`[200, 200]` (las dos renovaciones ganan; `assert 422 == 200` en la comprobación posterior), distinta de la `len([200]) == 1`
que registra la fila del roadmap: con la conexión pysqlite compartida las dos sesiones ven la misma transacción, que es la
misma causa raíz que la de este ciclo (`HARNESS_SHARED_CONNECTION`). Queda anotado en la fila del roadmap y en
`OBSERVACIONES.md` (OBS-02); no se absorbe: ese módulo y su aserción son de su dueña.

## Directorio huérfano del volumen de instalación

Tras la serie interrumpida a la fuerza (véase `acs-results.md`) quedó también `/tmp/kontrol-test-license-*/test_warehouse_structure-*`
(21:56:07, el mismo proceso matado): `pytest_unconfigure` no corre si matan el proceso. Eliminado a mano; las suites
completas y el E2E dejan 0. Mismo límite documentado en `TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO`.
