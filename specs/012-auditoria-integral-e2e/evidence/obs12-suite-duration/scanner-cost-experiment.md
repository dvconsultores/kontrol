# Coste del analizador — experimento acotado y semánticamente válido
`METHOD`: en las corridas instrumentadas `KONTROL_CLAMSCAN_PATH` apunta a un **envoltorio de medición fuera del
repositorio** que registra por invocación el tiempo monotónico, el código de salida y el tamaño del fichero, y transfiere
argumentos, stdout, stderr y código de salida intactos al `clamscan` real del caché, con la misma base de firmas. El análisis
no cambia de semántica (mismos CLEAN/INFECTED), el producto no cambia y el analizador no se apaga: `COMPARABLE = YES`.
`SCANNER_OFF_COMPARISON_INVALID = YES` (no se hizo ninguna suite completa con `KONTROL_DOCUMENT_SCAN=off`).
| Registro | SQLite | PostgreSQL |
|---|---|---|
| Invocaciones de `clamscan` en la suite | 48 (46 limpios rc 0, 2 EICAR rc 1, 0 errores) | 80 (78 rc 0, 2 rc 1, 0 errores; +32 por las siete carreras PG-only, n9 y las corridas E2E reales) |
| Tiempo total del analizador | **307 s** de 581,6 s (**53 %**) | **511 s** de 1356,5 s (**38 %**) |
| Por análisis | media 6,39 s · mediana 6,39 s · mín 6,33 · máx 6,71 s (desviación < 6 %): **coste estable** dominado por la carga de las firmas (3,6 M) en cada proceso, independiente del tamaño del fichero (bytes a KB) | media 6,39 s · mediana 6,38 s · mín 6,23 · máx 6,95 s (con 2 concurrentes) |
| `PREFLIGHT_TIME` | 13,8 s (`test_clam_04_05_06…`: dos análisis reales + arranque sin firmas) | 14,0 s |
| `PROVISIONING_TIME` | 0 en la suite (caché válida; ≈ 3 min 54 s una sola vez) | 0 |
| Sobrecoste del envoltorio | ≈ 30–40 ms por invocación (arranque de Python): < 1 % |
`SCANNER_COST_ESTIMATE` ≈ 6,4 s × nº de subidas analizadas; en SQLite ≈ 307 s + 14 s de preflight ≈ **55 % de la suite**.
Clasificación: `SCANNER_COST`, **coste legítimo y estable de seguridad** (decisión A + A2 de la dueña: `clamscan` por
proceso, sin demonio, sin debilitar); no es defecto y no se optimiza en este ciclo. Reducirlo (demonio `clamd`, caché de
firmas, menos subidas por prueba) sería una decisión de la dueña fuera de OBS-12.
