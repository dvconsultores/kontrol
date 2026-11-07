# GOV-CTL-10 · inventario de suites exigidas

Certificado el 2026-11-06/07 sobre el árbol final. Ejecución: Claude. Código y pruebas: DeepSeek, auditados por Claude.

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; HEAD == origin/develop | PASS · entrada `dbcf510`; origin sin moverse al certificar |
| 2 | RED primero | `test_gov_ctl10_*` sin producto | PASS (RED) · 74 fallidas, 1 error de recolección, 2 no-RED explicadas (`RED.md`) |
| 3 | BD dirigida | migración 0075 subir / bajar / subir | PASS · 3 tablas, 9 disparadores |
| 4 | Pruebas dirigidas | `tests/test_gov_ctl10_*.py`, cada fichero también por separado | PASS · 96 pruebas |
| 5 | Mutaciones | `mutar2.py` | PASS · 48 muertos, 0 equivalentes, 0 supervivientes (`MUTATIONS.md`) |
| 6 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261106t165403p907500n6c32ef`: 4559/0/18 |
| 7 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261106t175317p1507184n0ff4dd`: 2792/0/1785 |
| 8 | vitest · tsc · eslint · build | `node …` | PASS · vitest 1286/1286 (126 ficheros, rc 0); tsc 0; eslint 0; build correcto |
| 9 | ruff · mypy | `ruff check .` · `mypy app` | PASS · ruff limpio; mypy 154 = línea base, 0 nuevos |
| 10 | OpenAPI | contraste con `dbcf510` | PASS · 8 rutas nuevas, 0 retiradas; SoD añade `CTL-10` a su enumeración |
| 11 | E2E CTL-10 ×3 | `gobierno-cierres.spec.ts` en chromium, firefox y webkit, `--retries=0` | PASS · 9/9 en cada corrida |
| 12 | Regresión de Gobierno | `qa/e2e-gobierno-regresion.sh` | PASS · `r20261106t180936p1637104n37aa0e`: 189/189; `rc_scan=0`, `rc_integridad=0` |
| 13 | E2E canónica | `qa/e2e-run.py --con-analizador` | PASS · `r20261106t183424p1697631n8ee9b1`: 451/451, 0 reintentos |
| 14 | Integridad tras la E2E | `qa/gobierno_integridad.py`, 96 controles | PASS · 0 violaciones |
| 15 | Convergencia | `/speckit-converge` | `tasks_appended`: T042 y T043, ambas LOW y abiertas |

Las pruebas añadidas para matar mutantes se aplicaron después de la serie E2E ×3; no tocaron producto ni la especificación E2E. PostgreSQL, SQLite, regresión y canónica son posteriores a todo cambio de producto y de pruebas.

T042 y T043 quedan abiertas: T042 espera decisión de la dueña; T043 no se pudo encargar porque el MCP de DeepSeek no conectó tras el reinicio del 2026-11-07, y no la escribe Claude.

## Métricas (T039), calculadas desde `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv`

- Producto funcional: 134 ÷ 1 277 = 10,49 %.
- Listo para la dueña: 13 ÷ 122 = 10,66 %.
- Aceptado por la dueña: 0 ÷ 122 = 0,0 %.
- Fundamento técnico: 14 ÷ 38 = 36,8 %, sin cambio.
