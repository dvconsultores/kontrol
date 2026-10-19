# Atribución del único fallo de la certificación PostgreSQL

**Corrida:** `r20261019t151844p1578284nd886b1`, `--motor postgres --con-analizador`.

- Resultado: rc 1, 2904/1/26, 1979,6 s, anomalía NORMAL con razón 1,37 sobre la mediana de 8 corridas.
- Prueba que falla: `tests/test_e2e_corrida.py::test_e2ecorrida_01_una_corrida_verde_usa_su_base_y_no_deja_nada`, en la
  línea 137.
- Error: `assert de_prueba in m["protegidas_antes"] and m["protegidas_sin_cambios"] is True`. La huella de la base
  protegida `ktest` cambió durante la corrida simulada.

**Veredicto:** el fallo es previo, intermitente y ajeno a B1.

- La causa es la actividad interna de PostgreSQL (autovacuum y autoanalyze de catálogos) contada como «escrituras» por
  la huella de la herramienta QA (`qa/e2e_base.py::huella`, Spec 054).
- No se absorbe: queda registrado como deuda **E2E-HARNESS-PROTECTED-FINGERPRINT-COUNTS-AUTOVACUUM**.
- Ni producto, ni pruebas, ni `qa/` cambian en este ciclo.

## Experimento controlado

**Montaje:**
- PostgreSQL de QA con `clamscan` real.
- Misma secuencia de módulos que en la suite: de `test_documents*` a `test_e2e_corrida`.
- `-v` con marca de tiempo por prueba.
- Muestreo de 1 Hz de `pg_stat_activity` (`datname = 'ktest'`) y de `pg_stat_database` (`sessions`, tuplas escritas).

| Experimento | Secuencia | Resultado |
|---|---|---|
| X1 | **con** `test_document_upload_connection_boundary.py` | **234 passed, 0 failed**, 9 skipped |
| X2 | **sin** la prueba nueva (el árbol de producto con B1 es el mismo) | **1 failed** (`test_e2ecorrida_01`), 224 passed, 9 skipped |

El fallo aparece **sin** la prueba nueva, así que no lo provoca este ciclo.

## Mecanismo medido (X2)

- `test_e2ecorrida_01` corrió de 18:14:34 a 18:14:49 (CEST).
- Muestras de `ktest` (`hora sesiones escrituras conexiones_cliente`):
  - de 18:14:28 a 18:14:34: `10418 69222407 []`;
  - **18:14:35: `10418 69222594 []`**, +187 tuplas, las mismas sesiones y **ninguna conexión cliente abierta**;
  - de 18:14:36 a 18:14:52: sin cambios.
- `pg_stat_all_tables` de `ktest` muestra autovacuum y autoanalyze a las **16:14:34–16:14:35 UTC** (18:14:34–35 CEST)
  sobre `pg_catalog.pg_class`, `pg_attribute`, `pg_depend`, `pg_trigger`, `pg_index`, `pg_constraint`, `pg_attrdef`,
  `pg_type`, `pg_statistic`, `pg_shdescription` y `pg_db_role_setting`. Sus contadores acumulan unos 300 ciclos de
  autovacuum en el día, empujados por la creación y el borrado masivo de esquemas de prueba.
- `tup_inserted + tup_updated + tup_deleted` de `pg_stat_database` incluye esas escrituras de catálogo, que hace un
  trabajador de autovacuum. No es una sesión cliente ni nadie que se conecte a `ktest`.
- La aserción «la base protegida no cambia» depende, por tanto, de que autovacuum no caiga dentro de una ventana de unos
  15 s justo después de la mayor rotación de catálogo de la suite.
  - En las 8 corridas PostgreSQL anteriores no cayó.
  - En la de este ciclo, cuyo equipo iba un 37 % más lento repartido por toda la suite, y en X2 sí cayó.

## Por qué no se reintenta ni se arregla aquí

- La regla prohíbe reintentar para probar suerte y absorber deudas ajenas.
- La corrección (que la huella excluya la actividad de autovacuum, o compare solo sesiones cliente y tuplas de tablas
  de usuario) toca `qa/` y la Spec 054. Es una decisión propia, con su gate.
