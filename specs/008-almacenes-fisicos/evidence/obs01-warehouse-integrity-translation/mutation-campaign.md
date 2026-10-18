# Mutaciones (GOOD→PASS · MUTATED→FAIL · RESTORED→PASS; desde copias GOOD; `__pycache__` purgado; `PYTHONDONTWRITEBYTECODE=1`; juego: O01 + carrera de estructura; cada mutante en SQLite **y** PostgreSQL)
| Id | Mutación | Resultado | Detectada por |
|---|---|---|---|
| M01 | sin rama SQLite | KILLED | SQLite: carrera, 01-05, 09, 10 |
| M02 | catch-all de vuelta en almacén | KILLED | 06, 14 (ambos motores) |
| M03 | clasificador siempre `True` | KILLED | 06-10 |
| M04 | PostgreSQL ignora el nombre de la restricción | KILLED | PostgreSQL: 10 |
| M05 | SQLite por subcadena | KILLED | SQLite: 10 |
| M06 | ubicación se traga el error | KILLED | carrera, 02, 07, 09, 14 |
| M07 | código de dominio cambiado | KILLED | 01 |
| M08 | mensaje con `str(exc.orig)` | KILLED | 01 |
| M09 | `restriccion_unica` sin `LookupError` | KILLED | 11 |
| M10 | sin `rollback` en almacén | KILLED | 14 |
| M11 | SQLite sin comprobar el código extendido 2067 | **EQUIVALENT** | — |
| M12 | `restriccion_unica` sin `TypeError` | KILLED | 11 |
| M13 | catch-all en nodos | KILLED | 08, 14 |
| M14 | catálogo con restricción ajena | KILLED | 04 |
| M15 | alta masiva con restricción ajena | KILLED | 05 |
| M16 | nodos con restricción ajena | KILLED | 03 |
MEANINGFUL 16 · KILLED 15 · SURVIVED 0 · EQUIVALENT 1 · RESTORED 100 % (ficheros idénticos a GOOD; 15/15 en los dos motores).
M11 es equivalente para este esquema. Con la igualdad **exacta** del mensaje, solo una violación `UNIQUE` de SQLite produce
`UNIQUE constraint failed: <t>.<c1>, <t>.<c2>` para esas columnas. Una clave primaria (1555) informa otras columnas
(`warehouses.id`), y ninguna tabla tiene una clave primaria compuesta igual a la restricción. Matarla exigiría fabricar un
`sqlite3.IntegrityError` a mano, y el brief prohíbe los dobles. Se conserva como defensa en profundidad.
Precedencia 404/409 y sesión: estructurales (dependencias y `_get_warehouse` antes del `INSERT`; `rollback` antes de
relanzar). Las fijan O01-09/12/13/14 y M10.
