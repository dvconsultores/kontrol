# Analyze final · véase el delta §13

Todos los contadores exigidos por el encargo en 0 y TRAZABILIDAD 100 %. Comprobaciones mecánicas: `git diff --stat app/
central_authority/ resources/backend/tests/pg_harness.py` vacío; marcas `skip`/`xfail` en `tests/`: 51 → 52 líneas por la cadena literal que comprueba el invariante estático PGS-27 (`"pytest.mark.skip" not in fuente`), ninguna marca nueva (omitidas
1040 = 1040 en SQLite y 28 = 28 en PostgreSQL); `grep -E "make_engine\(|create_all\("` en las 12 suites → 0; `grep
"scope=\"session\""` en el conftest → 0; `grep -E "join_transaction_mode|create_savepoint" app/` → 0; `grep -E "sleep|retry"`
en lo tocado → 0; escaneo de secretos de la evidencia → 0.
