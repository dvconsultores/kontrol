# Control de envejecimiento determinista (sin sleep)
Copia temporal `tests/test_zz_o11_envejecido.py` (eliminada al terminar; `git status` limpio): por cada edad se fija por
`monkeypatch` la referencia **propiedad de la prueba** `SERVER_TIME = (ahora − edad + 5 min)` y se invoca la prueba objetivo
sin cambiarla. Edades: 0 s, 30 s, 4 min, 5 min, 5 min 1 s, 6 min, 30 min, 60 min.
| Edad del módulo | SQLite | PostgreSQL | Firma |
|---|---|---|---|
| 0 s · 30 s · 4 min | PASS | PASS | activación < `SERVER_TIME` → el sync adopta el servidor |
| 5 min | **FAIL** | **FAIL** | actual 23:22:56.365601 vs esperado 23:22:56 (la activación, con µs, ya es posterior) |
| 5 min 1 s · 6 min · 30 min · 60 min | **FAIL** | **FAIL** | actual = instante de activación; esperado = referencia envejecida (−1 s, −1 min, −25 min, −55 min) |
`DETERMINISTIC_AGED_FAILURE = YES` · `BOUNDARY = 5 min` (la ventaja fija de la referencia) · misma firma en los dos
motores · 5 failed / 12 passed por motor (SQLite 8,82 s; PostgreSQL 6,43 s). Fuente: `<scratch>/o11/envejecido.txt`.
