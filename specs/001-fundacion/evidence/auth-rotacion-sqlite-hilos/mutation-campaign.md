# Mutaciones M-01…M-14 · GOOD→PASS, MUTATED→FAIL, RESTORED→PASS (`mutation-run.txt`, `mutation-script.sh`)

Cada mutación: SEARCH/REPLACE único sobre el fichero, `__pycache__` purgado, `PYTHONDONTWRITEBYTECODE=1`, restauración
desde la copia GOOD comparada byte a byte (nunca `git checkout`), detector en SQLite (`tests/test_auth_rotacion_atomica.py`;
para M-01/02/03/08 además la prueba objetivo ×20 natural). GOOD: 17/17 y objetivo ×5 sin fallos.

| Id | Mutación | MUTATED | Detector | RESTORED |
|---|---|---|---|---|
| M-01 | sin `revoked_at IS NULL` en el UPDATE | 2 failed (natural ×20: 0 fallos) | **SA-01** (`[200, 200]` con I1 forzada), SA-16 | 17 passed |
| M-02 | ignorar rowcount (0 también sigue) | 2 failed (natural ×20: 0) | **SA-01**, SA-16 | 17 passed |
| M-03 | rowcount 0 tratado como éxito | 1 failed (natural ×20: 0) | **SA-01** | 17 passed |
| M-04 | crear la sesión de reemplazo antes de ganar | 3 failed | SA-01, SA-06/10/11 (el perdedor crea sesión), SA-16 | 17 passed |
| M-05 | sin `with_for_update()` | 1 failed | SA-16 (contrato de conservación; en SQLite es inobservable y en PostgreSQL la escritura condicional sigue dando un ganador: por eso la conservación es contrato estático) | 17 passed |
| M-06 | rowcount 0 → 200 con el token viejo | 1 failed | SA-01 | 17 passed |
| M-07 | rowcount 0 → `SESSION_INVALID` 409 | 1 failed | SA-01 | 17 passed |
| M-08 | el fixture vuelve a `make_engine()` | 1 failed; natural ×20: **2 fallos** (vuelve el ruido de la conexión compartida) | SA-16 + la propia prueba objetivo | 17 passed |
| M-09 | «exactamente un ganador» → «al menos uno» | 1 failed | SA-16 | 17 passed |
| M-10 | aceptar `[200, 200]` | 1 failed | SA-16 | 17 passed |
| M-11 | ocultar la excepción del hilo | **1.ª pasada: 2 passed (sobrevivió)** → se añadió SA-15 (comportamental: un hilo que lanza `ValueError` debe aparecer en la lista) → 2.ª pasada 1 failed | **SA-15** | 10 passed |
| M-12 | `OperationalError` → `SESSION_REVOKED` | 1 failed | **SA-14** | 17 passed |
| M-13 | `sleep` antes del 401 | 1 failed | SA-16 | 17 passed |
| M-14 | `datetime.now()` sin zona en vez de `_now()` | 1 failed | SA-16 (reloj canónico; añadido en este ciclo al ver que el valor naive es inobservable en SQLite) | 17 passed |

**14/14 muertas** (12 en la primera pasada; M-11 sobrevivió y se mató con una prueba comportamental nueva, no con un
ajuste del detector existente; M-14 se cubre estáticamente). Lectura importante: M-01/M-02/M-03 **no las detecta la
prueba objetivo natural** (0/20 fallos): sin forzar que las dos lean antes de que ninguna escriba, la carrera casi nunca
se da; por eso SA-01 existe y P25 exige forzarla. 0 directorios `kontrol-test-sqlite-*` al terminar; ficheros idénticos
a GOOD; `git status` solo con los cambios del ciclo.
