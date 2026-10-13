# POC candidato A · schema por módulo + transacción externa por prueba (SAVEPOINT) — temporal, no confirmada

Ficheros temporales `tests/poc_pgs_licensing_central.py` (copia de `test_licensing_central.py` con la fixture
sustituida) y `tests/poc_pgs_aislamiento.py` (adversarial: A escribe y hace `commit`, `update`, `rollback`; B debe ver la
base vacía; C comprueba que las tres comparten schema; D abre una segunda sesión sobre la misma conexión). Eliminados
tras la medición. Fixture de la POC:

```python
@pytest.fixture(scope="module")
def _poc_motor_del_modulo():
    engine = make_engine()  # PGLIFE lo apunta al ámbito del módulo
    init_models(); Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture()
def db_session(_poc_motor_del_modulo):
    conexion = _poc_motor_del_modulo.connect(); externa = conexion.begin()
    session = Session(bind=conexion, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
    finally:
        session.close(); externa.rollback(); conexion.close()
```

## PostgreSQL

```
### HEAD (schema por prueba) · test_licensing_central (15 pruebas)
...............                                                          [100%]
[PGS-CONTADOR] schemas_creados=15 schemas_soltados=15 conexiones_cortadas=0 residuos=0 duracion_s=13.2
### POC A · poc_pgs_licensing_central (15) + poc_pgs_aislamiento (4)
...................                                                      [100%]
[PGS-CONTADOR] schemas_creados=2 schemas_soltados=2 conexiones_cortadas=0 residuos=0 duracion_s=4.9
```

| Métrica | HEAD | POC A |
|---|---|---|
| TESTS | 15 | 19 (15 + 4 adversariales) |
| SCHEMAS / CREATE_ALL_CALLS | 15 | **2** (uno por módulo) |
| RELATIONS_CREATED | 12 615 | **1 682** |
| DURATION | 13,2 s | **4,9 s** (−63 % con 4 pruebas más) |
| ISOLATION_PASS · COMMIT_PASS · SECOND_SESSION_PASS · PGLIFE_PASS · RESIDUALS | — | PASS · PASS (commits de producto `initialize`/`import_license`/`sync_license` y de prueba, absorbidos por el SAVEPOINT) · PASS · PASS (ámbito de módulo) · 0 |
| SEQUENCE_PASS · THREAD_PASS | n/a (0 secuencias) · n/a (sin hilos en las 12) | ídem |

## SQLite (misma fixture, solo para conocer el comportamiento)

```
.FFFFFFFFFFFFFF.FFF
E  ConflictError: La instalación ya fue inicializada   (×14)
E  AssertionError: la fila que A confirmó sigue ahí: el aislamiento no se sostiene
```

Con `pysqlite` + `StaticPool` (una sola conexión en memoria) la transacción externa no contiene los `commit`: el estado
pasa de una prueba a otra. Conclusión: **el mecanismo A es solo para PostgreSQL**; en SQLite se conserva la base en
memoria nueva por prueba (milisegundos; FR-PGS-011). Diseño final: HYBRID por motor dentro de una misma fixture del
conftest (`sesion_de_prueba`), y las 12 suites la consumen.

Candidato B (TRUNCATE de 203 tablas por prueba) no se mide: no aporta nada frente a A en estas 12 suites (ninguna usa
sesiones secundarias ni hilos) y añade el riesgo de omitir una tabla. Candidato C (plantilla/clonado): requiere
`CREATE DATABASE … TEMPLATE` por prueba (más caro que un schema) o privilegios: descartado sin implementar.
