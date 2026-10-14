# Mutaciones M-01…M-12 · GOOD→PASS, MUTATED→FAIL, RESTORED→PASS (`mutation-run.txt`, `mutation-script.sh`)

SEARCH/REPLACE único por mutación, `__pycache__` purgado, `PYTHONDONTWRITEBYTECODE=1`, restauración desde copias GOOD
comparadas byte a byte. Detectores: `tests/test_uom_concurrencia_hilos.py` (O2-02/04/11) + la prueba objetivo; para las
mutaciones de la primitiva, además `tests/test_motor_para_hilos.py`. GOOD: 4/4.

| Id | Mutación | MUTATED | Detector | RESTORED |
|---|---|---|---|---|
| M-01 | el fixture objetivo vuelve a `make_engine()` | 1 failed | O2-04 (estático) | 4 passed |
| M-02 | O2-02 sobre la conexión compartida (`make_engine()` en su fixture) | 1 failed | **O2-02** (`len(conexiones) == 2` y/o hilo muerto) | 4 passed |
| M-03 | `motor_para_hilos` con `:memory:` privado por conexión | 7 failed | O2-02 (no ve la presentación: datastores distintos), ACS-01/02/03/04/06/08 | 4 passed |
| M-04 | ocultar la excepción del hilo en la prueba objetivo | 1.ª pasada: **sobrevivió** (3 passed: con conexiones propias no hay excepción que ocultar) → O2-04 exige la línea `errores.append(…)` → 2.ª pasada 1 failed | O2-04 | 4 passed |
| M-05 | aceptar un vector incompleto (`set(results) <= {200, 409}` sin longitud) | 1 failed | O2-04 | 4 passed |
| M-06 | `len(abiertas) >= 1` | 1 failed | O2-04 | 4 passed |
| M-07 | reintento (bucle que limpia `errores`) | 1.ª pasada: **sobrevivió** → O2-04 prohíbe `.clear(`, `range(`, `while ` en el bloque → 2.ª pasada 1 failed | O2-04 | 4 passed |
| M-08 | `sleep` en el hilo | 1 failed | O2-04 | 4 passed |
| M-09 | cerrojo que serializa la carrera | 1 failed | O2-04 (`Lock(`) | 4 passed |
| M-10 | `skipif` en la prueba objetivo | 1 failed | O2-04 | 4 passed |
| M-11 | O2-11 vaciada (sin hilo que lance) | 1.ª y 2.ª pasada: **sobrevivió** (el detector era la propia O2-11) → O2-04 exige el contenido de O2-11 y se corre el módulo entero → 3.ª pasada 1 failed | O2-04 | 4 passed |
| M-12 | `motor_para_hilos` sin `rmtree` | 3 failed | ACS-06, ACS-07, ACS-08 | 4 passed |

**12/12 muertas**; M-04, M-07 y M-11 solo después de reforzar el contrato estático (se documenta la primera pasada).
Equivalentes contadas: 0. Nota honesta: M-04 y M-07 son inobservables en comportamiento con el arnés corregido (ya no
hay excepciones que ocultar ni reintentar); por eso su guardia es estática, como en los ciclos anteriores. 0 directorios
`kontrol-test-sqlite-*` al terminar; ficheros idénticos a GOOD.
