# Carga del anfitrión durante la SQLite instrumentada (19 muestras de 30 s; saneado: sin IP, interfaces, equipo ni usuario)
| Métrica | Valor |
|---|---|
| `AVG_LOAD` / `MAX_LOAD` (load1) | 1,92 / 2,48 en **12 CPU lógicas** (load5 máx 1,90): sin contención de CPU |
| `CPU_PROFILE` | utilización media 12,3 %, máx 15,6 % (≈ 1,5 núcleos): la suite ocupa ~1 núcleo y `clamscan` ~0,2–0,5 más; `procs_running` máx 7 |
| `MIN_MEM_AVAILABLE` | **2105 MB** (máx 3012 MB) de 15 GB; swap total 27,3 GB con **≈ 5,2 GB en uso** por otros procesos del escritorio (muestra puntual): el anfitrión está **ajustado de memoria**, aunque la corrida no mostró síntomas (maxrss 1,67 GB; E/S de disco mínima) |
| `DISK_IO_PROFILE` | lectura 39 MB y escritura 157 MB en toda la corrida (NVMe): irrelevante |
| Cambios de contexto | 3600–7450 por segundo (sistema entero) |
| `clamscan` simultáneos | máx 1 (secuencial, como el producto lo lanza) |
| Procesos `alembic` | 0 en las muestras (las migraciones en subproceso duran < 30 s) |
Conclusión: esta corrida es **normal** (581,6 s, en la franja 587–692 s de las corridas con analizador) y la telemetría no
muestra carga, presión de memoria efectiva ni E/S que la frenen. El único indicador de riesgo del anfitrión es el margen
de memoria (2–3 GB libres y swap ocupada): una corrida bajo presión de memoria del escritorio **sí** podría multiplicar la
duración por paginación, pero eso no se observó aquí y no se afirma para el histórico. Fuente: `host-sqlite.csv`.
