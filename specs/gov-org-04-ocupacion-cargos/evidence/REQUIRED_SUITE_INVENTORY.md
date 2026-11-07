# GOV-ORG-04 · inventario de suites exigidas

Certificado el 2026-11-07 sobre el árbol final. Ejecución: Claude. Código y pruebas: DeepSeek, auditados por Claude.

| # | Suite | Orden / método | Resultado |
|---|---|---|---|
| 1 | Rama única y reconciliación | `git fetch`; HEAD == origin/develop | PASS · entrada `f544e59`; origin sin movimientos |
| 2 | RED primero | `tests/test_gov_org04_*` contra API ausente | PASS (RED) · 404 en cada ruta (`RED.md`) |
| 3 | BD dirigida | migración 0076 subir / bajar / subir en PostgreSQL | PASS · 5 tablas, disparadores y 2 exclusiones |
| 4 | Pruebas dirigidas | `tests/test_gov_org04_*.py` | PASS · 59 pruebas, 55 repetidas 3 veces |
| 5 | Concurrencia | `test_gov_org04_concurrencia.py` | PASS · 6 carreras reales, 3 corridas |
| 6 | Mutaciones | `mutar2.py` | PASS · 19 muertos, 0 equivalentes, 0 supervivientes (`MUTATIONS.md`) |
| 7 | PostgreSQL completo | `qa/suite_tiempos.py --motor postgres --con-analizador` | PASS · `r20261107t160348p2230431ne80250`: 4628 pasan, 0 fallan, 18 omitidas |
| 8 | SQLite completo | `qa/suite_tiempos.py --motor sqlite --con-analizador` | PASS · `r20261107t170559p2852743ne1d34f`: 2792 pasan, 0 fallan, 1854 omitidas |
| 9 | vitest · tsc · eslint · build | `node …` | PASS · vitest 1371/1371 (133 ficheros); tsc 0; eslint 0; build correcto |
| 10 | ruff · mypy | `ruff check .` · `mypy app` | PASS · ruff limpio; mypy 154 = línea base, 0 nuevos |
| 11 | OpenAPI | contraste con `f544e59` | PASS · 14 rutas nuevas, 0 retiradas; SoD añade `ORG-04` a su enumeración (4 esquemas y 2 parámetros, autorizado por el registro del proceso) |
| 12 | E2E ORG-04 ×3 | `gobierno-ocupacion.spec.ts`, chromium, firefox y webkit, `--retries=0 --repeat-each=3` | PASS · `r20261107t181205p3103851n1ea51e`: 27/27 |
| 13 | Regresión de Gobierno | `qa/e2e-gobierno-regresion.sh` | PASS · `r20261107t182300p3130509n8d4f22`: 198/198, humo 1/1 |
| 14 | E2E canónica | `qa/e2e-run.py --con-analizador` | PASS · `r20261107t184955p3197497ncb2580`: 454/454, 0 reintentos |
| 15 | Integridad tras la E2E | `qa/gobierno_integridad.py`, 118 controles | PASS · 0 violaciones; 22 de ORG-04 |
| 16 | Accesibilidad | axe WCAG 2.2 AA, 1280, 768 y 320, `OCU-E2E-03` | PASS · 0 violaciones serias; `ErrorState` compartido sustituido en ORG-04 |

PostgreSQL y SQLite corrieron antes del último cambio (`T011e`), que solo toca una pantalla y su prueba Vitest; ninguna de las dos suites la recorre. Tras ese cambio se repitieron vitest, tsc, eslint, build, E2E ×3, regresión y canónica.

## Convergencia

`/speckit-converge` sobre `d1656a7`: 11 FR, 4 SC, 14 decisiones de diseño y 5 gates. 0 `missing`, 0 `partial`, 0 `contradicts`; `FuncionarioPage` y `ErrorDeCarga` son añadidos justificados. El hueco de FR-005 (emisor en la consulta por cargo) se halló en la revisión previa y quedó corregido en T011e.

## Observaciones abiertas

- **OBS-A11Y-ERRORSTATE-01 (MEDIUM):** `ErrorState` compartido no alcanza contraste AA sobre fondo de peligro; lo usan 64 módulos. No absorbida: es núcleo compartido.
- **OBS-ORG04-COMISION-01 (LOW):** el tope de un año de la comisión de servicio está implementado y sin prueba propia.
