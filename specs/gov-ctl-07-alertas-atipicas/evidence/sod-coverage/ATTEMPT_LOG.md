# GOV-SOD-COVERAGE-01 · Registro de intentos (DeepSeek)

**Modelo:** `deepseek-v4-pro` en todas las llamadas.

**Control de salida previo a cada llamada:**

```
EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0 REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0
```

| # | Tarea | Tokens (entrada/salida) | Coste | Auditoría | Motivo |
|---|---|---|---|---|---|
| 1 | T001 · autoridad y consumidores | 7345/7729 | $0,009809 | REJECT parcial | Se aceptaron los bloques de `service_alertas.py` y `service_reporte_control.py`. Se rechazó `service_sod_eventos.py` por seis motivos (ver abajo) |
| 2 | T001 · reintento 1 (`service_sod_eventos.py`) | 5341/4536 | $0,006270 | REJECT | Aplicado: ruff limpio. Después, mypy: `call-overload` en `_resolver_ctl01`, porque el diccionario se indexaba por `regla.id` (tipado `UUID`) y se consultaba con `str` |
| 3 | T001 · reintento 2 (`_resolver_ctl01`) | 633/690 | $0,000876 | PASS | — |
| 4 | T002 · 11 pruebas PG | 8427/6841 | $0,009507 | REJECT | Las 11 pruebas pasaban, pero ruff dio I001 (orden de imports) y B007 (`accion` sin uso en un bucle) |
| 5 | T003 · pantalla REP-10 y Vitest | 5136/3243 | $0,004945 | REJECT | Aplicado: Vitest y eslint en verde. Después, tsc: TS2322, porque los datos base infieren `regla_codigo: string` y el caso BUD-08 asigna `null` |
| 6 | T004 · E2E y Axe 1280 de CNT-04 | 7646/6159 | $0,008574 | PASS | E2E 2/2 al primer intento |
| 7 | T002 · reintento 1 | 543/479 | $0,000653 | PASS | — |
| 8 | T003 · reintento 1 | 1107/670 | $0,001064 | PASS | — |

**Motivos del rechazo 1** de `service_sod_eventos.py`:

- R1. `dict(PROCESOS)` lanza `ValueError`, porque PROCESOS tiene tuplas de 3.
- R2. La etiqueta de proceso de PROC-11 y BUD-08 no se consultaba en PROCESOS.
- R3. PROC-11 perdía `regla_version`.
- R4. Los metadatos del adaptador estaban duplicados en cada normalizador.
- R5. `normalizar()` despachaba por acción con `if`/`elif`, así que un productor nuevo obligaba a editarlo. Se sustituyó por un `resolver` por adaptador.
- R6. ruff marcaba F401 y UP035.

**Totales:**

- 8 llamadas, de un tope de 8;
- 4 reintentos semánticos (T001 ×2, T002 ×1, T003 ×1), dentro de `RETRY_MAX: 2`;
- 4 rechazos y 4 aceptaciones;
- coste total: $0,041698;
- OWNER_EXCEPTION_USED=0.

Claude no corrigió ningún parche a mano. Tampoco usó `ruff --fix`, que habría sido una corrección no atribuida. Cada rechazo se resolvió con un reintento que llevaba el motivo exacto.

## Mutaciones

Se ejecutaron con `mutar_sod.py` sobre PostgreSQL contra `tests/test_gov_sod_cobertura.py`. Cada mutación se restauró al terminar.

| Mutación | Cambio | Resultado | La matan |
|---|---|---|---|
| M1 · BUD-08 fuera del catálogo canónico | `PRODUCTORES.pop(BUD08_ACCION)` | Muerta | 8 pruebas, entre ellas `test_autoridad_y_catalogo` y `test_bud08_productor_real` |
| M2 · sin adaptador PROC-11 | `PRODUCTORES.pop(PROC11_ACCION)` | Muerta | 8 pruebas, entre ellas `test_proc11_productor_real` |
| M3 · `entity_id` de BUD-08 leído como regla | resolver de CTL-01 y nombre de regla en BUD-08 | Muerta | `test_bud08_entity_id_no_es_regla` |
| M4 · código de proceso erróneo | BUD-08 con `proceso="CTL-01"` | Muerta | `test_rep10_total_y_agrupacion`, `test_bud08_productor_real` |
| M5 · sin filtro de tenant y empresa | `consultar` solo filtra por acción | Muerta | `test_aislamiento_empresa_y_tenant` |
| M6 · REP-10 solo cuenta CTL-01 | filtro `GOV_SOD_CONFLICT_BLOCKED` en REP-10 | Muerta | 7 pruebas, entre ellas `test_sin_listas_divergentes` y `test_rep10_total_y_agrupacion` |

**Resultado:** 6/6 muertas.
