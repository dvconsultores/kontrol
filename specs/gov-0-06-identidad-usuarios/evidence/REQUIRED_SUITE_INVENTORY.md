# GOV-0-06 · inventario de validación

Validado el 2026-11-08 con la directiva PRODUCT-FIRST de la dueña, que sustituye la certificación exhaustiva por una razonable. Ejecución: Claude. Código y pruebas: DeepSeek, auditados por Claude.

| # | Validación | Resultado |
|---|---|---|
| 1 | Rama y reconciliación | PASS · `develop`, HEAD == origin == `fba4a31` a la entrada |
| 2 | Backend dirigido en PostgreSQL: Gobierno, copias, guardianes y migraciones | PASS · 827 pasan, 0 fallan, sobre el árbol final |
| 3 | Concurrencia ORG-06 | PASS · dentro del punto 2 |
| 4 | Mutaciones ORG-06 | PASS · 19 muertos, 1 equivalente justificado, 0 supervivientes (`MUTATIONS.md`), previas a los últimos arreglos |
| 5 | vitest · tsc · eslint · build | PASS · vitest 1419/1419 una vez; tsc 0; eslint 0; build correcto |
| 6 | ruff · mypy | PASS · ruff limpio; mypy 154 = línea base, 0 nuevos |
| 7 | OpenAPI contra `fba4a31` | PASS · 14 rutas nuevas, 0 retiradas; SoD añade `ORG-06` a su enumeración (4 esquemas y 2 parámetros, autorizado) |
| 8 | E2E representativa | PASS · Chromium 3/3, 0 reintentos, a mediodía; antes 27/27 en tres navegadores ×3 |
| 9 | Integridad | PASS · runner con 136 controles en el punto 2. Sin corrida sobre la base de una E2E |
| 10 | SQLite | Completa 2793/0 anterior a T016l. Dirigida posterior: 6 pasan, 163 omitidas, porque son solo de PostgreSQL: no aporta evidencia |

**Diferido a `FINAL_GOVERNMENT_CERTIFICATION`:** PostgreSQL y SQLite completos sobre el árbol final, regresión de Gobierno, E2E canónica y controles de base tras la E2E.
