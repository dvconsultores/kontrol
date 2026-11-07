# P0-RUNTIME-LOCK-API-BOOT-FAILURE · registro de intentos

| Intento | Modelo | Coste | Resultado | Motivo |
|---|---|---|---|---|
| P0_ATTEMPT_1 | deepseek-v4-pro | $0,003134 | AUDIT_PASS, aplicado; insuficiente | Mi diseño no contemplaba la inclusión perezosa de routers: arranca, pero el verificador no se instala |
| P0_RETRY_1 | deepseek-v4-pro | $0,00319 | AUDIT_PASS, aplicado | Pruebas en verde |

P0_RETRY_2 sin usar.

# P0-B · RUNTIME-LOCK-OPERATIONS-CATALOG-EMPTY · registro de intentos

`NEW_ROOT_CAUSE = 1`: presupuesto propio por subtarea.

| Intento | Modelo | Coste | Resultado | Motivo |
|---|---|---|---|---|
| P0-B1 | deepseek-v4-pro | $0,002114 | Producción: AUDIT_PASS. Generador: AUDIT_REJECT | `camino` fuera del bucle de métodos |
| P0-B1 RETRY_1 | deepseek-v4-flash | $0,000353 | AUDIT_PASS, aplicado | Instantáneas idénticas |
| P0-B2 | deepseek-v4-flash | $0,001384 | AUDIT_PASS, aplicado | 25 bloques en 10 ficheros |
| P0-B3 | deepseek-v4-pro | $0,003475 | AUDIT_REJECT | Rutas sin registrar, `setattr` (B010), anotación, caché sin aislar |
| P0-B3 RETRY_1 | deepseek-v4-pro | $0,004112 | AUDIT_PASS con una desviación, aplicado | `operacion: dict`, corregida en RETRY_2 |
| P0-B3 RETRY_2 | deepseek-v4-flash | $0,000313 | AUDIT_PASS, aplicado | Mata M3 y corrige la anotación |

Coste total: $0,011751 en 6 llamadas. P0-B1 RETRY_2 sin usar. P0-B3 agotó sus 2 reintentos y terminó aprobado.

`T052-A1` no se tocó: `T052-A1_RETRY_BUDGET_EXHAUSTED = 1`.
