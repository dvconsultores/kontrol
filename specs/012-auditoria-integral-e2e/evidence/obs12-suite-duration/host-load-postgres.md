# Carga del anfitrión durante la PostgreSQL instrumentada (45 muestras de 30 s; saneado)
| Métrica | Valor |
|---|---|
| `AVG_LOAD` / `MAX_LOAD` (load1) | 1,84 / 2,97 en 12 CPU (load5 máx 2,18): sin contención |
| `CPU_PROFILE` | media 13,5 %, máx 21,7 % (≈ 1,6–2,6 núcleos: pytest + `clamscan` + `postgres`); `procs_running` máx 6 |
| `MIN_MEM_AVAILABLE` | 2037 MB (máx 3670 MB); swap ocupada ≈ 5,2 GB por el escritorio; actividad de swap muestreada en vuelo: 47 páginas entrantes en 30 s, 0 salientes (sin paginación efectiva) |
| `DISK_IO_PROFILE` | lectura 239 MB, escritura 393 MB (WAL y esquemas de PostgreSQL): bajo para 22 min |
| Cambios de contexto | ≈ 6500 por segundo |
| `clamscan` simultáneos | máx 2 (carreras documentales) · `alembic` máx 1 |
Conclusión: corrida **normal** (1356,5 s; franja histórica 1354–1869 s) sin carga, presión de memoria efectiva ni E/S que
la frenen. Fuente: `host-pg.csv`.
