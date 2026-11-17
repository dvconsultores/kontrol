# CNT-04-EFFECTIVE-TERM-01 · Cierre

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:** Gobierno · Contratos › Contratos y órdenes › (contrato) › «Supervisor / responsable del contrato» › «Plazo del contrato».
- **WHAT_CAN_USER_DO:**
  - ver el fin del plazo vigente, la fuente («Contrato original» o «Modificación <código>») y el fin original cuando difiere;
  - designar un supervisor con fecha efectiva hasta el fin vigente a esa fecha, que incluye las prórrogas CNT-02 formalizadas;
  - el sistema rechaza una designación más allá del plazo vigente o sobre un contrato terminado.
- **OWNER_UAT_READY:** YES. El proceso ya lo era; se corrige el defecto P0 sin cambiar su clasificación.
- **PRODUCT_STATUS:** OWNER_UAT_READY · CURRENT_PRODUCT_DEFECT=NO.
- **MISSING_GATES:** ninguno del ciclo. El refactor de hardcode de CNT-04 sigue pendiente (REFACTOR_HARDCODED_POLICY, fuera de alcance).

## Cambio

- **Autoridad única nueva:** `service_contratos_terminos.terminos_efectivos`. La usan CNT-03, CNT-04, CNT-07 y CNT-09. CNT-08 reutiliza la misma primitiva `_vigente_a` de CNT-02.
- **`designar()`:** el máximo es `terminos_efectivos(db, contrato, desde)["fecha_fin"]`. Después se aplica `exigir_vigente_en(desde)`.
- **Respuesta de `supervision`:** se añaden `fecha_fin_original`, `fecha_fin_vigente`, `fuente_plazo` y `modificacion_plazo`, y se retira `fecha_fin`.
- **Pantalla:** nueva sección «Plazo del contrato».
- **Sin migración** (alembic 0122, una cabeza) y **sin cambio de esquema**.

## Evidencia

| Prueba | Resultado |
|---|---|
| PG nuevas `test_gov_cnt04_plazo_efectivo.py` | 9/9 |
| PG dirigida CNT-02/03/04/07/08/09 | 77/77 |
| Mutaciones M1–M6 | 6/6 muertas (ver `ATTEMPT_LOG.md`) |
| Vitest completo | 2319/2319 (209 ficheros) |
| typecheck · lint · build | OK |
| ruff | limpio |
| mypy | 157 errores de línea base; ninguno en ficheros tocados |
| E2E CNT-04 plazo (nueva) | 1/1, anchos 1280/390/320, Axe 0 serious/critical a 390 y 320 |
| E2E CNT-02/07/08 | pasan |
| E2E CNT-01 | pasa sola; inestable con 5 workers (ver deudas) |
| OpenAPI | rutas sin cambio; las respuestas son dicts |

### PG completa sobre 2dbaf7a9

5676 passed, 18 skipped, 25 failed.

- **BASELINE_FAILURE (4):**
  - `test_n10_convergence::test_el_orm_y_la_base_no_difieren_en_nada`;
  - `test_naive_datetime_input::test_guard_d01_ningun_datetime_desnudo`;
  - `test_spec019_receipt` ×2.
- **FLAKY_WITH_EVIDENCE (21):**
  - La corrida cruzó la medianoche (terminó el 17/11 a las 01:28). Las pruebas fijaban «hoy» como el 16/11 y el reloj de negocio ya estaba en el 17/11. Por eso aparecen «La vigencia no puede empezar antes de hoy» y `'2026-11-17' == '2026-11-16'`.
  - Afectan a ORG-06, PROC-02/03/06/08/10/11 y TRE-01/02. Ninguna toca contratos.
  - Al volver a correrlas el 17/11 a las 01:29 sobre 2dbaf7a9: 21/21, RC=0.
- **NEW_FAILURE:** 0.

## DeepSeek

`deepseek-v4-pro`, 8 llamadas (el tope), 4 reintentos, 4 rechazos y 4 aceptaciones, $0,020970, OWNER_EXCEPTION_USED=0.

Claude diseñó, auditó, aplicó y certificó. DeepSeek escribió todo el código semántico y todas las pruebas.

## Deudas

- **OBS-E2E-CNT01-REAUTH-300S-01:** la E2E de CNT-01 con 5 workers supera la ventana de reautenticación de 300 s (REAUTH_REQUIRED). Pasa sola.
- **OBS-PG-MIDNIGHT-CROSSING-01:** algunas pruebas de SoD y fechas capturan «hoy» fuera del reloj de negocio y fallan si la suite cruza la medianoche.
- **Axe a 1280:** no se ejecutó; solo se corrió a 390 y 320.
- **Auditoría de parametrización:** quedan 10 defectos actuales abiertos. CNT-04 pasa a CURRENT_PRODUCT_DEFECT=NO.
