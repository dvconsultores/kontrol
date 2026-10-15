# Matriz de causa raíz
| Issue | Reproducido | Igualdad de rutas | Visibilidad entre procesos | Persistencia entre corridas | Colisión | Orden de settings | Control aislado | Causa raíz | Producto | Decisión dueña | Implementación |
|---|---|---|---|---|---|---|---|---|---|---|---|
| almacén compartido | sí (D1, D2) | YES | YES (A↔B) | YES (D4, D5: 121 ficheros) | YES para exportaciones (D3) | correcto (D8) | elimina todo (D6, D7) | **SHARED_PATH_LEAK + STALE_STATE_ACROSS_RUNS + CROSS_PROCESS_COLLISION + HARNESS_CLEANUP_DEFECT** (las cuatro demostradas de forma independiente) | NO | NO | **SÍ** (solo arnés) |
| respaldos compartidos | sí (D1, D2) | YES | YES (marcadores sintéticos) | YES | n/a (sin consumidor) | correcto | elimina (D6) | SHARED_PATH_LEAK (latente: el producto aún no escribe respaldos) | NO | NO | SÍ (misma raíz) |
| `SETTINGS_CAPTURE_DEFECT` / `PRODUCT_PATH_CONTRACT` | no (D8) | — | — | — | — | OK | — | descartadas | — | — | — |
`UNKNOWN = 0`. Pruebas de SHARED_PATH_LEAK: (1) mismo espacio de nombres (D1); (2) A ve lo de B y B lo de A (D2); (3) las
raíces aisladas lo eliminan (D6); (4) producto intacto (D8: lee por `get_settings()`). Pruebas de STALE_STATE: (1) una
corrida normal deja estado (D4, D5); (2) una nueva lo ve (D2/D4); (3) ningún contrato exige que sobreviva
(`cleanup-contract.md`); (4) la raíz por sesión lo elimina (D6).
