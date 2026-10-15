# Inventario histórico de duraciones (solo lo que la evidencia registra; sin telemetría inventada)
| Ciclo | Motor | HEAD de partida | Segundos | passed/failed/skipped | Analizador | Observación del equipo | Telemetría | Fuente |
|---|---|---|---|---|---|---|---|---|
| OBS-08 (d377db7) | SQLite #1 / #2 | 4fa9e7c | 268,5 / 265,0 | 1637/33/1049 | **sin** analizador (33 rojos fallan rápido) | — | UNAVAILABLE | `046/evidence/document-security-clamav-pg-contract/sqlite-full-*.md` |
| OBS-08 | PostgreSQL | 4fa9e7c | 1065,0 | 2653/37/29 | sin analizador | — | UNAVAILABLE | ídem `postgres-full.md` |
| ClamAV A2 (714b695) | SQLite #1 / #2 | d377db7 | 681,7 / 692,1 | 1679/8/1046 | real 1.4.3 | — | UNAVAILABLE | ídem `sqlite-full-a2.md` |
| ClamAV A2 | PostgreSQL | d377db7 | 1354,3 | 2706/1/26 | real | — | UNAVAILABLE | ídem `postgres-full-a2.md` |
| OBS-10 (d122d6b) | SQLite #1 | 714b695 | **587** | 1692/1/1046 | real | — | UNAVAILABLE | `046/evidence/obs10-legacy-import-sqlite/full-suites.md` |
| OBS-10 | SQLite #2 | 714b695 | **2946** | 1692/1/1046 (idéntica prueba por prueba) | real | «carga de la máquina durante la corrida» (observación sin medida) | **UNAVAILABLE** | ídem |
| OBS-10 | PostgreSQL | 714b695 | 1869 | 2712/1/26 | real | — | UNAVAILABLE | ídem |
| OBS-11 (8d140ba) | SQLite #1 / #2 | d122d6b | 601,5 / 610,4 | 1699/0/1046 | real | — | UNAVAILABLE (solo duración de `date +%s.%N`) | `010/evidence/obs11-sync-time-anchor/sqlite-full-*.md` |
| OBS-11 | PostgreSQL | d122d6b | 1459,3 | 2719/0/26 | real | — | UNAVAILABLE | ídem `postgres-full.md` |
Lecturas: (1) las duraciones históricas se midieron con reloj de pared (`date`), no monotónico; (2) sin analizador la SQLite
completa tardaba ≈ 267 s con 33 rojos rápidos; con analizador real ≈ 590–690 s: la diferencia es una pista, **no** una
comparación semánticamente válida (FR-O12-022); (3) PostgreSQL también varía (1354 → 1869 → 1459 s) sin cambio de pruebas
que lo explique; (4) el 2946 s es un único valor atípico ×5 sin telemetría de anfitrión: `UNKNOWN_HISTORY`.
