# Registro de intentos · CTL-02-AUDIT-PROCESS-RESOLUTION

- **Modelo:** `deepseek-v4-pro` vía `mcp__deepseek__deepseek_chat`, sin sesión ni `thinking`.
- **Tope:** 8 llamadas.
- **EGRESS_CHECK:** en cada llamada, ENV_FILES=0, SECRETS=0, PROD_URLS=0, TOKENS=0, PRIVATE_KEYS=0, REAL_PII=0, REAL_PAYROLL=0 y BANK_DATA=0. Los briefs solo llevan código, contratos y nombres sintéticos.
- **Coste:** $0,435 por millón de tokens de entrada y $0,87 por millón de salida.

## Trabajo de Claude (declarado)

| Tarea | Ejecutor | Motivo |
|---|---|---|
| T01 autoridad de procesos (`procesos.py`) | CLAUDE | Arquitectura de la autoridad; cambio transversal |
| T02 consumidores (CTL-02, CTL-04, CTL-07/REP-10, CTL-05), esquema de la bitácora y tipo `BitacoraEvento` | CLAUDE | Cambio transversal y contrato |
| T03 PG del ciclo (`test_gov_ctl02_procesos.py`, 23 pruebas) y GX02 de CTL-04 comparada contra la autoridad | CLAUDE | Evidencia del defecto y de las mutaciones; cambio de contrato esperado |
| T06 mutaciones, hardcode, tarjeta, roadmap y cierre | CLAUDE | Cierre |

## Llamadas

| # | Tarea | Tokens (entrada/salida) | Coste | Resultado | Motivo |
|---|---|---|---|---|---|
| 1 | T04 · pantalla y Vitest | 3037/2217 | $0,003250 | REJECT parcial | Los bloques de las dos páginas, válidos, se aplicaron. El Vitest nuevo dejaba `waitFor` importado sin uso: lint y tsc (TS6133) |
| 2 | T04 · reintento 1 | 404/67 | $0,000234 | PASS | Quita el import. Typecheck 0, lint limpio y Vitest de la carpeta 12/12 |
| 3 | T05 · E2E | 5238/4093 | $0,005839 | REJECT | `pulsarYEsperar` sin uso (TS6133, lint); `obtenerOpciones` sin definir (TS2304); propiedad de más `funcionario_id` (TS2353); Axe a 768 en lugar de 390 |
| 4 | T05 · reintento 1 | 1343/826 | $0,001303 | PASS | 5 bloques válidos. Typecheck y lint limpios; E2E 1/1 contra el backend real |

## Totales

- **Llamadas:** 4 de 8 (OWNER_EXCEPTION_USED=0); 2 tareas base y 2 reintentos.
- **Tokens:** 10.022 de entrada y 7.203 de salida.
- **Coste:** $0,010626.
- **Garantías:**
  - ningún parche se corrigió a mano para atribuírselo a DeepSeek;
  - el informe del puente llegó sangrado y ese marco se quitó antes de comparar;
  - para el aplicador se convirtió la línea de ruta en `FILE: ruta`, que es un cambio de formato y no del parche;
  - no se usó `ruff --fix`.

## Mutaciones (Claude)

Script fuera del repositorio (`mutar_ctl02.py`):
- cada mutación exige un ancla única;
- corre sus pruebas con `-x`;
- restaura el original en `finally`.

| Id | Mutación | Prueba que la mata | Resultado |
|---|---|---|---|
| M1 | Volver a un catálogo parcial (sin TRE-09) | `test_ctl02_p02_*[TRE-09]` | MUERTA |
| M2 | Ignorar la metadata del catálogo | `test_ctl02_p01_defecto_bud08_sin_proceso` | MUERTA |
| M3 | Mapear BUD-08 a un proceso incorrecto (BUD-09) | `test_ctl02_p01_defecto_bud08_sin_proceso` | MUERTA |
| M4 | Tratar un evento de plataforma como de proceso | `test_ctl02_p03_clases_plataforma_autenticacion_y_sistema` | MUERTA |
| M5 | Omitir CNT (CNT-01) | `test_ctl02_p02_*[CNT-01]` | MUERTA |
| M6 | Omitir REP (REP-10) | `test_ctl02_p02_*[REP-10]` | MUERTA |
| M7 | Exportación (CSV de la muestra de CTL-04) sin proceso | `test_ctl02_p10_exportacion_con_el_mismo_proceso_que_la_pantalla` | MUERTA |
| M8 | Evento nuevo sin metadata (se quita CTL-07): **solo** la guardia | `test_ctl02_p05_guardia_todo_evento_de_gobierno_resuelve_su_proceso` | MUERTA |
| M9 | El filtro de CTL-04 vuelve a una lista parcial | `test_ctl02_p09_filtros_aceptan_todo_proceso_canonico` | MUERTA |

**Resultado:** 9 de 9 muertas.

## Defecto reproducido

- **Antes:** con `service_auditoria`, `service_bitacora`, `schemas_bitacora`, `service_sod_eventos`, `service_reporte_control`, `service_rendicion` y `api_rendicion` de 9f2c3dde, la suite del ciclo da 20 fallidas y 3 pasadas.
  - Entre las fallidas están `test_ctl02_p01_defecto_bud08_sin_proceso` (proceso vacío), las 8 parametrizaciones de procesos antes huérfanos y el filtro de CTL-04.
  - Las 3 que pasan son pruebas unitarias de la autoridad nueva.
- **Después:** 23/23.
- CTL02_DEFECT_REPRODUCED_BEFORE=YES · CTL02_DEFECT_FIXED_AFTER=YES.
