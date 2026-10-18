# Diagnóstico (sin cambios; `-o addopts= -p no:cacheprovider`, SQLite)
| Sonda | Resultado |
|---|---|
| D1 · módulo completo en su orden | 13 passed (4,0 s) |
| D2 · cada prueba **sola** | **10 de 13 fallan**: 02, 03, 04, 05, 08, 11, 12 → `CENTRAL_NOT_CONFIGURED` (la autoridad la configura csync_01); 06, 07 → `estado is None` (la licencia la importa csync_02); 10 → `NoResultFound` (estado de licencia ausente); solo 01, 09 y 13 pasan solas |
| D3 · módulo en **orden inverso** | **11 failed, 2 passed**; incluso csync_01 falla: `'LICENSE' == 'NO_LICENSE'` porque las pruebas que corrieron antes ya importaron una licencia en el mismo mundo |
| Coste del mundo | `setup` 3,0 s (SQLite) / 3,4 s (PostgreSQL) una vez por módulo (`scope="module"`) |
**Causa raíz demostrada (`TEST_STATE_COUPLING`)**: el fixture `_mundo` es de **módulo** (una base de cliente y una de
autoridad compartidas por las 13 pruebas) y las pruebas no establecen sus precondiciones: dependen de lo que dejaron las
anteriores (autoridad configurada por csync_01, licencia importada por csync_02, eventos y corridas acumulados). La
observación registrada («csync_02 depende de csync_01») se queda corta: el acoplamiento afecta a 11 de las 13 pruebas.
Producto: sin defecto (las respuestas `CENTRAL_NOT_CONFIGURED`/estado nulo son las correctas para esos estados).
