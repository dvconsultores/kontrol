# GOV-PROC-02 · inventario de validación

Validado el 2026-11-08, con la estrategia PRODUCT-FIRST. Ejecución: Claude. Código y pruebas: DeepSeek, auditados por Claude.

| # | Validación | Resultado |
|---|---|---|
| 1 | Pruebas de PROC-02 en PostgreSQL | PASS · 9/9: primaria y N1 a N6 |
| 2 | Backend dirigido en PostgreSQL: Gobierno, auditoría, aislamiento, arquitectura, copias, migraciones | PASS · 1199 pasan, 0 fallan, antes del renombrado de esquemas; tras él, 33/33 de lo afectado |
| 3 | Migración 0079 | PASS · de cero a cabeza, abajo y arriba en PostgreSQL; cabeza única |
| 4 | vitest · tsc · eslint · build | PASS · vitest 1444/1444 una vez; tsc 0; eslint 0; build correcto |
| 5 | ruff · mypy | PASS · ruff limpio; mypy 154 = línea base, 0 nuevos |
| 6 | OpenAPI contra `de7c74c` | PASS · 14 rutas nuevas, 0 retiradas; SoD añade `PROC-02` a su enumeración (4 esquemas y 2 parámetros, autorizado) |
| 7 | E2E representativa | PASS · COM-E2E-01 y 02, Chromium, 0 reintentos: crear, editar, acto, miembros, activar con otra persona, inhibición y su resolución, consulta a fecha, SNC, terminar y cerrar |
| 8 | Verificación desechable | PASS · sustitución con acto, composición a fecha y CSV. No queda como prueba del repositorio |

**Sin ejercitar por interfaz:** descartar, retirar un miembro en borrador y designar un miembro con la comisión vigente. Su API sí está probada o verificada.

**Diferido a `FINAL_GOVERNMENT_CERTIFICATION`:** suites completas, regresión de Gobierno, E2E canónica, tres navegadores, mutaciones, Axe en estas pantallas, controles de base tras la E2E.
