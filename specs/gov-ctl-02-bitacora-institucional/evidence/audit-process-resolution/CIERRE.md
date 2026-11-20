# Cierre · CTL-02-AUDIT-PROCESS-RESOLUTION (2026-11-19)

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:**
  - Gobierno › Bitácora institucional (lista y detalle).
  - Gobierno › Auditoría institucional (filtro «Proceso»).
- **WHAT_CAN_USER_DO:**
  - Ver, en cada evento de Gobierno, su proceso y su módulo (por ejemplo «Tesorería · Tasas oficiales»), en la lista y en el detalle, junto al actor efectivo, la autoridad, la unidad y la correlación.
  - Filtrar la auditoría institucional por cualquiera de los 39 procesos canónicos.
- **HOW_IS_PROCESS_RESOLVED:**
  - Partiendo del `owner_spec` del catálogo de eventos (`AuditActionSpec`), se busca el proceso en el registro `procesos.PROCESOS` y de ahí se obtiene el módulo.
  - Se resuelve al consultar, sin migración: los eventos históricos también quedan clasificados.
- **WHAT_IS_THE_CANONICAL_PROCESS_AUTHORITY:**
  - `app/modules/government/procesos.py`: 39 procesos, 8 módulos y `resolver_proceso`.
  - AUDIT_PROCESS_AUTHORITIES=1 · PARTIAL_PROCESS_CATALOGS=0.
- **HOW_ARE_PROCESS_EVENTS_CLASSIFIED:**
  - PROCESS_EVENT: evento de Gobierno con `owner_spec` registrado.
  - AUTH_EVENT: las 9 acciones de autenticación.
  - PLATFORM_EVENT: eventos de módulos que no son de Gobierno.
  - SYSTEM_EVENT: acciones sin especificación en el catálogo.
- **HOW_ARE_PLATFORM_EVENTS_HANDLED:**
  - Llevan su clase, sin proceso inventado.
  - La bitácora muestra «Proceso no especificado» y la autenticación muestra «Autenticación».
- **HOW_IS_NEW_EVENT_COVERAGE_GUARDED:**
  - `test_ctl02_p05_*` falla si un evento de Gobierno no resuelve su proceso (lo demuestra la mutación M8).
  - `test_ctl02_p06_*` exige que los `owner_spec` sean únicos, que cada proceso tenga eventos y que cada código exista en la matriz del roadmap.
- **HOW_DOES_CTL04_REUSE_THIS_AUTHORITY:**
  - `service_auditoria` toma de la autoridad el orden, la condición de proceso y la validación del filtro, y elimina su lista de 19 procesos.
  - Certificado en este ciclo por decisión de la dueña (OD-PR-01): mutación M9, PG y paso E2E.
- **HOW_IS_EXPORT_KEPT_IN_PARITY:**
  - El CSV de la muestra de CTL-04 usa el mismo `_proceso_de` que la pantalla (`test_ctl02_p10_*`, mutación M7).
  - Las alertas SoD (CTL-05) y REP-10 toman los nombres de la autoridad (`test_ctl02_p07_*`).
- **OWNER_UAT_READY:** YES (`OWNER_UAT_CARD.md`, partes A–F).
- **ACCESSIBLE:** YES (Axe a 1280, 390 y 320 en la E2E).
- **PRODUCT_STATUS:** FUNCTIONAL_PRODUCT. Falta `OWNER_ACCEPTED`, que solo puede conceder la dueña.
- **MISSING_GATES:** la UAT de la dueña.

## Evidencia

| Puerta | Resultado |
|---|---|
| Defecto reproducido antes del cambio | Suite del ciclo con los servicios de 9f2c3dde: 20 fallidas y 3 pasadas. Después: 23/23 |
| Mutaciones | 9 de 9 muertas (M1–M9) |
| PG dirigida | 595/595 |
| PG completa | 5896 pasadas, 18 omitidas y 5 fallidas, todas fuera de este ciclo (ver la tabla siguiente) |
| E2E | 12/12 (la nueva más identidad, auditoría y tasas), limpieza LIMPIA |
| Humo UAT | 1/1 |
| Vitest | 2537/2537 |
| typecheck, lint y build | 0 |
| ruff | limpio |
| mypy | 157 de línea base y 0 en los ficheros tocados |
| OpenAPI | 908 rutas, ninguna nueva; solo se añaden los campos opcionales `modulo` y `modulo_nombre` a `BitacoraEvento` y `BitacoraEventoDetalle` |
| Migración | Ninguna (cabeza 0128_gov_tre04_pago) |

### Clasificación de la PG completa (reproducida)

| Prueba | Aislada en el árbol del ciclo | Aislada en HEAD 9f2c3dde | Clase |
|---|---|---|---|
| `test_iso_barridos::test_barrido_cabecera_manipulada` | PASA | — | TIME_WINDOW_BASELINE (la sesión caduca durante una corrida larga) |
| `test_n10_convergence::test_el_orm_y_la_base_no_difieren_en_nada` (`import_*.created_by`) | FALLA | FALLA | BASELINE_FAILURE |
| `test_naive_datetime_input::test_guard_d01_ningun_datetime_desnudo` (`aperturas:body.abierta_en`) | FALLA | FALLA | BASELINE_FAILURE |
| `test_spec019_receipt` ×2 (`RECEIPT_EMPTY`, 409) | FALLA | FALLA | BASELINE_FAILURE |

NEW_FAILURE=0 · ENVIRONMENT_FAILURE=0.

## DeepSeek

- 4 llamadas de un tope de 8: T04 y T05, más un reintento de cada una.
- 10.022 tokens de entrada y 7.203 de salida; coste $0,010626.
- Claude implementó T01, T02, T03 y T06. El detalle está en `ATTEMPT_LOG.md`.

## Roadmap

- CTL-02: defecto NO (corregido), prioridad NONE.
- CTL-04: defecto NO; sigue en P1.
- CURRENT_PRODUCT_DEFECTS pasa de 3 a 1 (queda BUD-02). Siguiente candidato: BUD-02.

## Commits

- Código: b61fd449.
- Documentación: 24b64376.
- Entrada: 9f2c3dde. P1 no había avanzado (`origin/develop` == 9f2c3dde), así que no hubo fusión.
