# GOV-CTL-02 · inventario de validación

Validado el 2026-11-08 con la estrategia PRODUCT-FIRST. Ejecución: Claude. Código y pruebas: DeepSeek, auditados por Claude.

| # | Validación | Resultado |
|---|---|---|
| 1 | Pruebas de CTL-02 en PostgreSQL | PASS · contexto 5/5 (primaria y negativas: rechazo, sin identidad, instantánea, otros módulos), API 5/5 (primaria, otro ente, autenticación, capacidad, sin vínculo) |
| 2 | Backend dirigido en PostgreSQL: Gobierno, auditoría, autenticación, aislamiento, arquitectura, copias, migraciones | PASS · 1212 pasan, 0 fallan |
| 3 | Migración 0078 | PASS · de cero a cabeza, abajo y arriba en PostgreSQL; disparadores append-only intactos; cabeza única |
| 4 | vitest · tsc · eslint · build | PASS · vitest 1430/1430 una vez; tsc 0; eslint 0; build correcto |
| 5 | ruff · mypy | PASS · ruff limpio; mypy 154 = línea base, 0 nuevos |
| 6 | OpenAPI contra `69c6b8a` | PASS · 3 rutas nuevas, 7 esquemas nuevos, 0 retiradas, 0 cambiadas |
| 7 | E2E representativa | PASS · BIT-E2E-01, Chromium, 0 reintentos, con Axe a 1280, 768 y 320 px |

**Sin campaña de mutaciones, por directiva. Diferido a `FINAL_GOVERNMENT_CERTIFICATION`:** PostgreSQL y SQLite completos, regresión de Gobierno, E2E canónica, tres navegadores y controles de base tras la E2E.
