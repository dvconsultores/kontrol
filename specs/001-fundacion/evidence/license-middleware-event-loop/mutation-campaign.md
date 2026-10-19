# Mutaciones (GOOD→PASS · MUTATED→FAIL · RESTORED→PASS; juego: regresión nueva + 4 suites de licencia = 72 pruebas; SQLite **y** PostgreSQL)
| Id | Mutación | Resultado | Detectada por |
|---|---|---|---|
| M01 | vuelve `self._get_mode()` síncrono | KILLED | L07, L09, L10, U01 (ambos motores) |
| M02 | `run_in_threadpool` sin `await` | KILLED | L02, L04, L05, L06, L07… (12) |
| M03 | no ejecuta `_get_mode` | KILLED | 12 pruebas |
| M04 | lo ejecuta dos veces | KILLED | L02, L07, L10 |
| M05 | ignora READ_ONLY | KILLED | L04, L06 |
| M06 | invierte el código de READ_ONLY | KILLED | L04, L05 y suites de licencia existentes |
| M07 | ignora SECURITY_SUSPENSION | KILLED | L05 |
| M08 | quita una exención válida | KILLED | L06 |
| M09 | añade una exención indebida (`/api/v1/`) | KILLED | 11 pruebas |
| M10 | cambia el 423 por 403 | KILLED | 15 pruebas (nuevas y existentes) |
| M11 | comprueba la licencia después de la operación | KILLED | L04, L05, L10 |
MEANINGFUL 11 · KILLED 11 · SURVIVED 0 · EQUIVALENT 0 · RESTORED 100 % (idéntico a GOOD; 72/72 en los dos motores).
