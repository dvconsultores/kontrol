# PostgreSQL completa — `qa/suite_tiempos.py --motor postgres --con-analizador` (04:33–04:56)
**2739 passed · 0 failed · 26 skipped** (= 2719 + 20) · rc 0 · **1349,9 s monotónicos** (desvío 0) · pytest interno 1318,0 s ·
analizador 1.4.3 · anomalía `SIN_REFERENCIA` · residuos 0 · esquemas `t_` 0 y conexiones del arnés 0 al cierre · anfitrión:
load1 media 1,7 (máx 2,4), CPU 13,5 % (máx 20,6 %), **MemAvailable mín 1576 MB, swap máx 6268 MB, paginación entrante
210 098 / saliente 364 108 páginas** (≈ 0,8 GB / 1,4 GB: el escritorio paginó durante la corrida), disco 733 MB leídos /
263 MB escritos · CPU del árbol 1511 s · top 30 = 452,8 s (34 %).
Lectura: la corrida es normal (1349,9 s, franja 1354–1869 s) **aunque el anfitrión estuvo paginando**: el contrato ya deja
visible la presión de memoria que antes era invisible; con más corridas registradas, una duración atípica podrá
correlacionarse con estas columnas en vez de con una observación de memoria.
