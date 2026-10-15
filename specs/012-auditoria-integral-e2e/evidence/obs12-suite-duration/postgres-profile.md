# Perfil PostgreSQL completa instrumentada (etapa 1; `ktest` 55432; orden canónica + `--durations=0`; analizador por envoltorio)
| Registro | Valor |
|---|---|
| `TOTAL_DURATION` | **1356,5 s monotónicos** (pared 1356,5 s; desvío −0,0 s) · pytest interno 1324,5 s → ≈ 32 s de arranque + colección |
| `RESULT_COUNTS` | 2718 passed · 1 failed · 26 skipped; el único fallo es el mismo artefacto del envoltorio (`test_clam_04_05_06…`, `MEASUREMENT_ERROR` conocido); funcionalmente 2719/0/26 como la línea base |
| `SCANNER_ENGINE` / `SCANNER_DB` | ClamAV 1.4.3 · main 63 · daily 28153 · bytecode 339 |
| CPU del árbol (`getrusage`) | usuario 1517,1 s + sistema 161,5 s = **1679 s de CPU en 1357 s de pared (≈ 1,24 núcleos)**: igual que en SQLite, limitada por su propio trabajo (pytest + `clamscan` + servidor PostgreSQL aparte) |
| `maxrss` · ctx · E/S | 1745 MB · voluntarios 1 082 947 · involuntarios 66 352 · bloques leídos 60 544 · escritos 0 |
| Suma listada | 1313 s = setup **194 s** + call 1095 s + teardown 25 s (1711 pruebas): el setup por prueba (un esquema `t_…` por prueba, PGLIFE) y el teardown pesan 3× más que en SQLite |
| Distribución | ≥ 5 s: 64 fases · 1–5 s: 168 · < 0,5 s: 1912 |
| `TOP30` | 446 s = **33 %**; top 10 = 213 s (16 %); resto 910 s repartido en ≈ 2700 nodos (coste de esquema + migración por módulo) |
| `WAIT_EVENTS` | las siete carreras documentales PostgreSQL-only duran 13–20 s cada una = **2–3 análisis concurrentes de 6,4 s** (`clamscan` simultáneos máx 2 en las muestras) más la carrera en sí (ms); `test_e2e_corrida.py` 99,8 s en 11 pruebas (≈ 9–21 s cada una: base efímera + backend uvicorn real + sonda; PROCESS_STARTUP legítimo); ningún techo de hilo/subproceso consumido |
| Familias | documentos con analizador **494 s (36 %)** (`documents_security` 380 s + `documents` 114 s); corridas E2E reales 100 s; n9 integridad 28 s (análisis); migraciones en subproceso (0018, UoM backfill) ≈ 45 s; módulos funcionales de 15–25 s por fichero (esquema por prueba) |
Fuente: `<scratch>/o12/corrida-pg.*`, `host-pg.csv`, `clamscan-pg.csv`.
