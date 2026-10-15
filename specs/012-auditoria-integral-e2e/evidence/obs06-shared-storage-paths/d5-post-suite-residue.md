# D5 · Residuo tras un grupo representativo (`tests/test_reporting.py` + `tests/test_n9_integrity.py`, arnés sin cambios)
| Categoría (nivel superior de `<tmp>/kontrol-test-storage`) | Antes | Después | Nuevos |
|---|---|---|---|
| `exports/` | 67 | 69 | **+2** (CSV y PDF de `test_export_*`; la corrida completa deja 3) |
| `documents/` | 55 | 55 | 0 (n9 corre sobre PostgreSQL: 3 omitidas en SQLite) |
| `sonda/` (marcadores del diagnóstico, retirados después) | 6 | 6 | 0 |
Resultado del grupo: 16 passed, 3 skipped (3,2 s). Inventario histórico al empezar el ciclo: 121 ficheros / 484 KB
(`documents/2026/10/13` 8, `/14` 31, `/15` 16; `exports/` 66) acumulados en tres días sin que ninguna prueba los
necesite después de su sesión. Tamaños aproximados: KB por fichero. Edad: del 2026-10-13 16:55 al 2026-10-15 04:49.
