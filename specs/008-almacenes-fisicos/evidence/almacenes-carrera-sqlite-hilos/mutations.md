# Mutaciones M-01…M-12 · GOOD→PASS, MUTATED→FAIL, RESTORED→PASS

Guion `mutations-script.sh` (de Claude, fuera del repositorio; copia enmascarada) y salida completa en `mutations-run.txt`.
Cada mutación se aplica con SEARCH/REPLACE único sobre el fichero, con `__pycache__` purgado y `PYTHONDONTWRITEBYTECODE=1`;
se restaura desde las copias GOOD (comparadas byte a byte, nunca `git checkout`) y se vuelve a correr el detector.
Detector base: `tests/test_motor_para_hilos.py` (8 pruebas) en SQLite; para M-08 y M-04 además la prueba objetivo ×20;
para M-12 la prueba objetivo. GOOD: 9/9 y objetivo ×5 sin fallos. Una primera pasada idéntica (sin nombres de pruebas en
la salida) dio los mismos 12/12 detectados; esta es la segunda, con nombres.

| Id | Mutación | MUTATED | Detectores | RESTORED |
|---|---|---|---|---|
| M-01 | la primitiva devuelve `make_engine()` también en SQLite | 5 failed (1.ª pasada: 6) | ACS-01 (ids iguales), ACS-02 (A = B), ACS-03 (`[1, 0]`: el rollback ajeno), ACS-06 (sin directorio), ACS-08; ACS-04 falló en la 1.ª pasada y no en la 2.ª: bajo la conexión compartida la carrera es intermitente, exactamente la causa raíz | 9 passed |
| M-02 | `:memory:` con el pool por defecto (un `:memory:` privado por conexión) | 6 failed (20,2 s) | ACS-01…04 (`no such table: acs_filas`: la otra conexión es otra base), ACS-06, ACS-08 | 9 passed |
| M-03 | `poolclass=StaticPool` sobre el fichero | 5 failed | ACS-01, 02, 03, 06, 08 | 9 passed |
| M-04 | sin `connect_args={"check_same_thread": False}` | 1 failed; objetivo ×20: 0 fallos | ACS-08 (estático). **Equivalente en comportamiento**: SQLAlchemy 2.0.36 ya fija `check_same_thread=False` para bases en fichero (`create_connect_args` → `{'check_same_thread': False}`, comprobado). El argumento explícito se conserva para que el invariante no dependa del defecto del dialecto, y ACS-08 lo fija | 9 passed |
| M-05 | sin `rmtree` al salir | 3 failed | ACS-06, ACS-07 (directorio presente), ACS-08; dejó 6 directorios, eliminados por el guion | 9 passed |
| M-06 | sin `dispose()` al salir | 2 failed | ACS-06 (pool con conexión viva), ACS-08 | 9 passed |
| M-07 | `timeout=60` en `connect_args` | 1 failed | ACS-08 (`timeout`) | 9 passed |
| M-08 | el fixture de `test_warehouse_structure.py` vuelve a `make_engine()` | objetivo ×20: **12 fallos**; 1 failed | la carrera reaparece (ACS-09) y ACS-08 (`with motor_para_hilos(...)` ausente) | 9 passed |
| M-09 | limpieza fuera del `finally` | 1 failed | ACS-07 (dejó 1 directorio, eliminado por el guion) | 9 passed |
| M-10 | ACS-03 con `commit` en vez de `rollback` | 1 failed | ACS-03 (`[0, 1]`) | 9 passed |
| M-11 | ACS-04 sin barrera | 1 failed | ACS-08 (la barrera es parte del contrato de ACS-04); en resultado ACS-04 pasa igual, como se esperaba: la barrera fuerza el entrelazado, no el veredicto | 9 passed |
| M-12 | aserción de la prueba objetivo debilitada (`or len(results) == 1`) | 1 failed | ACS-08; la prueba objetivo pasa con la aserción debilitada, por eso hace falta el contrato estático | 9 passed |

12/12 detectadas (M-04 solo estáticamente, declarada equivalente en comportamiento con la razón). 0 directorios
`kontrol-test-sqlite-*` al terminar; los tres ficheros idénticos a sus copias GOOD; `git status` de `tests/` con solo
los cambios del ciclo.
