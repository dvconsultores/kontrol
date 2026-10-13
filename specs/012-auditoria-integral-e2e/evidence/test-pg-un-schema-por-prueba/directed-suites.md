# Dirigidas tras T01–T03 (W30/W31) · las 12 suites `db_session` + `tests/test_pg_sesion_aislada.py` · `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, contador PGLIFE

```
### SQLite
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 94%]
.............                                                            [100%]
[PGS-CONTADOR] schemas_creados=0 schemas_soltados=0 conexiones_cortadas=0 residuos=0 duracion_s=44.4
### PostgreSQL (KONTROL_TEST_DB_URL=postgresql+psycopg2://***@localhost:55432/ktest)
........................................................................ [ 31%]
........................................................................ [ 62%]
........................................................................ [ 94%]
.............                                                            [100%]
[PGS-CONTADOR] schemas_creados=13 schemas_soltados=13 conexiones_cortadas=0 residuos=0 duracion_s=33.1
```

229 pruebas (214 de las 12 suites + 15 PGS): **0 fallos** en los dos motores. En PostgreSQL, **13 schemas** (uno por módulo:
12 suites + el módulo PGS) donde antes eran 214 + 15 = 229; residuos 0; conexiones cortadas 0.

PGS cubre: PGS-02/03/04/05 (A escribe, confirma, actualiza, borra; el producto hace `commit` en `initialize`; B y C
parten de cero) · PGS-06/06b (segunda sesión del ámbito) · PGS-08 (0 secuencias en PostgreSQL y SQLite) · PGS-09
(PostgreSQL: mismo schema y motor en todo el módulo y ningún schema nuevo por prueba; SQLite: motor nuevo por prueba) ·
PGS-11 (sonda entera: cada prueba parte de cero, 0 schemas con el pid del hijo) · PGS-10 (sonda que falla: el schema
del módulo se suelta igual) · PGS-07 (dos módulos del mismo proceso: schemas distintos, exactamente uno nuevo por
módulo) · PGS-23 (orden inverso y prueba sola) · PGS-26 (dos procesos a la vez: schemas distintos, 0 residuos) ·
PGS-27 (estático: las 12 suites consumen `sesion_de_prueba`, sin `make_engine`/`create_all`/`skip`) · PGS-28 (estático:
sin reordenación, sin schema de sesión, producto sin `join_transaction_mode`/`create_savepoint`). PGS-07 hilos: no aplica
(ninguna de las 12 usa hilos; las suites con hilos conservan su schema por prueba).
