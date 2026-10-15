# Matriz de clasificación (corridas instrumentadas del 2026-10-15; SQLite 581,6 s · PostgreSQL 1356,5 s)
| Categoría | Evidencia | Pruebas afectadas | Tiempo estimado | Confianza causal | Corrección en el repositorio | Decisión de la dueña |
|---|---|---|---|---|---|---|
| **SCANNER_COST** | registro del envoltorio: 48 / 80 invocaciones de 6,39 s de mediana (desviación < 6 %); carga de firmas por proceso | documentos, seguridad documental, carreras PG-only, n9, preflight | **SQLite 321 s (55 %) · PG 525 s (39 %)**, estable | alta (medido por invocación) | **no** (coste legítimo de seguridad; decisión A + A2) | solo si se quisiera reducirlo (demonio, caché de firmas): fuera de OBS-12 |
| **PROCESS_STARTUP** | perfil: keepalive (uvicorn real) 23 s; `test_e2e_corrida` (PG) 100 s; volumen de instalación / sesión aislada (pytest anidado) 34 s; migraciones en subproceso ≈ 45 s (PG); arranque + colección de pytest 28–32 s | ficheros de arnés y migraciones | SQLite ≈ 85 s (15 %) · PG ≈ 210 s (15 %) | alta (duraciones por prueba + procesos muestreados) | no (procesos reales por contrato de cada prueba) | no |
| **HARNESS_WAIT** (legítima) | keepalive espera 5,3 s de ociosidad por contrato; sondeos de 50–200 ms salen en cuanto se cumple la condición | keepalive, concurrencia PG | ≈ 11 s | alta | no | no |
| **THREAD_WAIT** | carreras con Barrier/join: la parte de hilos dura ms; el resto es el analizador (2–3 concurrentes) | 7 carreras documentales, licencias, UoM, auth | < 5 s en total | alta | no (techos no consumidos) | no |
| **SQLITE_LOCK_WAIT** | ninguna prueba SQLite con hilos supera 3,5 s (y es setup); `busy_timeout` 5 s nunca se consume | — | 0 s observados | alta | no | no |
| **TEST_ORDER** | colección y orden idénticos a la canónica (mismo recuento 2745); la diferencia ×5 histórica fue «idéntica prueba por prueba» | — | 0 | alta | no | no |
| PGLIFE (esquema por prueba) → se clasifica como **OTHER (coste estructural del motor)** | setup 194 s + teardown 25 s en PG frente a 63 + 0 en SQLite; resto de la suite 910 s en ≈ 2700 nodos | todas las PG | ≈ 330 s de diferencia estructural SQLite→PG | media-alta (fases de pytest) | no (TEST-PG-UN-SCHEMA-POR-PRUEBA cerrada; coste aceptado) | no |
| **MACHINE_LOAD / CPU_CONTENTION** | load1 media 1,8–1,9 (máx 3,0) en 12 CPU; utilización 12–14 %; involuntarios 25 k / 66 k | ninguna en estas corridas | 0 observado | alta para hoy; **no observable** para el histórico | no | no |
| **MEMORY_PRESSURE** | MemAvailable mín 2,0–2,1 GB de 15 GB; swap del escritorio ≈ 5,2 GB ocupada; paginación en vuelo ≈ 0 | ninguna hoy | 0 observado; **riesgo latente** (el anfitrión trabaja con 2–3 GB libres) | alta para hoy; no observable para el histórico | no (observabilidad: sí, etapa 2) | no |
| **DISK_IO** | 39/157 MB (SQLite), 239/393 MB (PG) en NVMe | — | 0 | alta | no | no |
| **NETWORK_EXTERNAL_WAIT** | sin red externa en las suites (autoridad y backends locales); E2E fuera de este perfil | — | 0 | alta | no | no |
| **MEASUREMENT_ERROR** | (a) histórico medido con reloj de pared; (b) en las corridas instrumentadas, un fallo artificial por el envoltorio del analizador; (c) `-qq` canónico oculta el resumen | — | — | alta | **sí, en el QA**: contrato de medición monotónico con perfil y telemetría (etapa 2) | no (no material) |
| **NOT_REPRODUCED** | el atípico de 2946 s no se reprodujo (581,6 s hoy con la misma colección) | — | — | — | — | — |
Suma de contribuciones SQLite: analizador 321 + procesos 85 + esperas legítimas 11 + resto de ≈ 2680 nodos ≈ 165 s ≈ 582 s
(**UNKNOWN = 0**). PostgreSQL: analizador 525 + procesos 210 + estructural ≈ 330 + resto ≈ 290 s ≈ 1357 s (**UNKNOWN = 0**).
`ACTIVE_PATHOLOGICAL_DELAY = 0`: ninguna prueba consume un techo ni espera sin causa.
