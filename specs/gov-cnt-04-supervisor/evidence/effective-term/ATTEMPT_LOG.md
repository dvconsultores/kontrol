# CNT-04-EFFECTIVE-TERM-01 · Registro de intentos (DeepSeek)

**Modelo:** `deepseek-v4-pro` en todas las llamadas.

**Control de salida previo a cada llamada:**

```
EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0
```

| # | Tarea | Tokens (entrada/salida) | Coste | Auditoría | Motivo |
|---|---|---|---|---|---|
| 1 | T001 · autoridad neutral y uso en CNT-04 | 2883/2371 | $0,003206 | REJECT | ruff I001: `service_contratos_terminos` quedó antes de `service_contratos_supervision` en `service_contratos_ejecucion.py`. El resto del parche era correcto y quedó aplicado |
| 2 | T002 · 9 pruebas PG | 3234/3738 | $0,004548 | REJECT | ruff I001 en los imports. Además, la prueba CNT-08 leía `["contrato"]["fecha_fin_vigente"]`, pero la clave real es `["resumen"]["fecha_fin_vigente"]`: el error venía del encargo de Claude |
| 3 | T003 · pantalla y Vitest | 3054/2806 | $0,003659 | PASS | — |
| 4 | T004 · E2E de la dueña | 5425/4305 | $0,006105 | REJECT | Localizaba una `section` anidada que no existe, y el acto de designación lo emitía un cargo de FIRMAR (el encargo pedía `firmanteSinLimiteId`) |
| 5 | T001 · reintento 1 | 546/257 | $0,000461 | PASS | — |
| 6 | T002 · reintento 1 | 974/689 | $0,001023 | PASS | — |
| 7 | T004 · reintento 1 | 1484/1070 | $0,001466 | PASS | — |

**Totales:**

- 7 llamadas, de un tope de 8;
- 3 reintentos semánticos, con un máximo de 1 por tarea;
- 3 rechazos y 4 aceptaciones;
- coste total: $0,020468;
- OWNER_EXCEPTION_USED=0.

Claude no corrigió ningún parche a mano. Cada rechazo se resolvió con un reintento que incluía el motivo exacto, sobre el fichero con el intento anterior ya aplicado.

## Mutaciones

Se ejecutaron con `mutar.py` sobre PostgreSQL contra `tests/test_gov_cnt04_plazo_efectivo.py`. Cada mutación se restauró al terminar.

| Mutación | Cambio | Resultado | La mata |
|---|---|---|---|
| M1 · EFFECTIVE_END → ORIGINAL_END | `fin_vigente = contrato.fecha_fin` | Muerta | Prórroga formalizada: 422 donde se esperaba 201 |
| M2 · include_draft_modification | `_formalizadas` admite BORRADOR | Muerta | Borrador sin `monto_nuevo`: 500 |
| M3 · cutoff = hoy | `terminos_efectivos(db, contrato, hoy)` | Muerta | Corte histórico: 422 donde se esperaba 201 |
| M4 · corte ignorado (la última siempre) | `terminos_efectivos(db, contrato, date.max)` | Muerta | Corte histórico: 201 donde se esperaba 422 |
| M5 · ignore_termination | `exigir_vigente_en(...)` → `pass` | Muerta | Terminación: 201 donde se esperaba 409 |
| M6 · la respuesta expone el fin original como vigente | `fecha_fin_vigente` = `contrato.fecha_fin` | Muerta | Aserciones de `fecha_fin_vigente` |

**Resultado:** 6/6 muertas.
