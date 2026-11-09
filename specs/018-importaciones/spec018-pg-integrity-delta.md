# Delta IMP-PG-INTEGRITY-01 · Importaciones sobre PostgreSQL migrado

**Spec dueña:** 018. **Autorización de implement:** encargo de la dueña del 2026-11-09, que nombra este bloque.
**Evidencia:** `evidence/pg-integrity/`. **Auditoría previa:** `IMPORT_POSTGRES_TIMESTAMP_AUDIT.md`.

## Problema

En PostgreSQL creado con Alembic, crear un expediente da HTTP 500 por `NotNullViolation` en `import_files.created_at`. Los ciclos 1 a 3 solo se verificaron en navegador sobre SQLite, cuyo esquema sale de los modelos.

## Requisitos

- **FR-PG-01:** las seis tablas `import_*` tienen `now()` como default de `created_at` y `updated_at` en un esquema migrado.
- **FR-PG-02:** la corrección es una migración nueva, descendiente de la cabeza pública, que no reescribe filas. El downgrade solo retira ese default.
- **FR-PG-03:** ninguna tabla del esquema migrado queda con `created_at` o `updated_at` `NOT NULL` sin default. Una prueba lo vigila.
- **FR-PG-04:** la migración local de gastos desciende de la correctiva y nace con el contrato correcto.
- **FR-PG-05:** las pruebas de Importaciones crean datos válidos y pasan sobre PostgreSQL, sin desactivar claves foráneas.
- **FR-PG-06:** la carga de `@/lib/format` no arrastra todos los idiomas de `date-fns`; `importaciones.test.tsx` pasa con su espera original.
- **FR-PG-07:** la E2E canónica recorre los ciclos 1 a 3 y gastos en Chrome, sobre PostgreSQL migrado.

## Decisión de orquestación

`LOCAL_RULE_CONFLICT = 1`: `CLAUDE.md` clasifica las migraciones como `CLAUDE_ONLY`. `OWNER_ORCHESTRATION_DECISION_APPLIED = 1`: la dueña decidió en este encargo que DeepSeek las escribe y Claude audita, aplica y certifica. Prevalece por la precedencia de `CLAUDE.md`. Ese fichero no se cambia.

## Tareas

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T-PG-01 | Auditoría de timestamps | CLAUDE | n-a | NO | SÍ | 0 | `IMPORT_POSTGRES_TIMESTAMP_AUDIT.md` | Consultas sobre PostgreSQL | Publicada con mediciones |
| T-PG-02 | Migración correctiva, reajuste de gastos y prueba de migración (PG-A) | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `alembic/versions/*`, cabezas en pruebas, prueba nueva | Prueba de migración en PostgreSQL | Upgrade, downgrade y upgrade pasan con una fila previa |
| T-PG-03 | Datos válidos en pruebas e import de `date-fns` (PG-B) | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | Pruebas de importaciones, `lib/format.ts` | Pytest PostgreSQL y Vitest | Verdes sin ampliar esperas |
| T-PG-04 | Integración y E2E (PG-C), solo si algo falla | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | Según el fallo | E2E Chrome PostgreSQL | La E2E pasa completa |
| T-PG-05 | Certificación, documentación y publicación | CLAUDE | n-a | NO | SÍ | 0 | Evidencia, matriz, tarjeta | Puertas finales | `HEAD == origin/develop` |

## Fuera de alcance

Distribución, preview y aplicación de landed cost (ciclo 4B). Producción: no se toca.

## Cierre

Resultado y deuda en `evidence/pg-integrity/EVIDENCE.md`. Inventario de despliegue en `evidence/pg-integrity/DEPLOYMENT_INVENTORY.md`.

Durante la ejecución se añadieron a las tareas T-PG-03 y T-PG-04: registrar `created_by` en el servicio, las notificaciones en teléfono, el aviso veraz de Costos y la precarga en `importaciones.test.tsx`. Las dos primeras las destapó la E2E; ninguna estaba en el encargo inicial.
