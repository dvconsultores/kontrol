# Evidencia · Ciclo 4B, landed cost

**Fecha:** 2026-11-09. **Publicado en:** `7fa4a82` (`develop`). **Datos:** sintéticos.

| Campo | Valor |
|---|---|
| DATABASE_ENGINE | PostgreSQL 16.2 de QA |
| SCHEMA_SOURCE | Alembic, base nueva, cabeza `0089_fusion_gov_landed` |
| BROWSER | Google Chrome, `qa/e2e-run.py --con-analizador` |

## Pruebas financieras (`tests/test_importaciones_landed_cost.py`, PostgreSQL)

16 de 16 en verde, también en SQLite.

| Escenario | Qué demuestra |
|---|---|
| Reparto exacto | Mayor residuo: 33,34/33,33/33,33; 0,03/0,02; 1,67/3,33/5,00 |
| VALUE varias líneas | Suma exacta; solo capas del expediente; la vista previa no escribe y es reproducible |
| QUANTITY | Reparto por cantidad base; unidades incompatibles rechazadas |
| MANUAL | No cuadra: bloqueo con diferencia y sin efecto; cuadra: aplica exacto; más de 2 decimales rechazado |
| Moneda cruzada | Gasto en EUR sobre capa USD: tasa histórica 1,10 vigente a la fecha del gasto, no la posterior 2,00; sin tasa, 409 |
| Aplicar y valoración | 38,46 y 61,54; valoración 325,00 → 425,00; costo efectivo 16,346 y 13,077 |
| Salida posterior FIFO | Costo de salida 6,00 con landed cost; una salida anterior no cambia |
| AVERAGE | Promedio 18,75 con landed cost |
| Doble aplicación | 409 secuencial; la base rechaza una segunda aplicación vigente |
| Concurrencia | Dos aplicaciones simultáneas: exactamente una se consolida |
| Inventario consumido | Aplicación bloqueada entera, sin efecto parcial |
| Reversión | Valoración vuelve exacta; bloqueada con consumo; motivo obligatorio |
| Permisos | 403 para rol sin `compras:approve`; la valoración exige `inventario:view` |
| Aislamiento | 404 sobre expediente de otra empresa o gasto de otro expediente |
| Auditoría | `IMPORT_EXPENSE_CLASSIFIED`, `IMPORT_COST_APPLIED`, `IMPORT_COST_REVERSED` con actor y empresa |

## Resto de puertas

| Puerta | Resultado |
|---|---|
| Alembic, base nueva | upgrade PASS; downgrade a `0087` y upgrade PASS |
| Pruebas dirigidas PostgreSQL | 91 de 91 (landed cost, migraciones, catálogo 419, inventario, gastos) |
| PROC-06 de P1 tras el merge | 8 de 8 |
| E2E Chrome | PASS a 1280, 390 y 320 px, 0 respuestas 500 |
| TSC, ESLint, build, Ruff | Limpios |
| Vitest | 526 de 526 en los módulos afectados |
| mypy | 154, igual a la línea base |

## Defectos reales encontrados y corregidos

- La revisión de fusión tenía un id de 34 caracteres y `alembic_version.version_num` es varchar(32): una base nueva no migraba. Renombrada a `0089_fusion_gov_landed` antes de publicar.
- El historial de commits incluye mensajes «local, sin publicar» de commits que después se publicaron juntos.
