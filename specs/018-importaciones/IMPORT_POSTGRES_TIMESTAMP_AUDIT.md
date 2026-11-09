# Auditoría de timestamps de Importaciones sobre PostgreSQL

**Delta:** IMP-PG-INTEGRITY-01 (`spec018-pg-integrity-delta.md`).
**Medido:** 2026-11-09, PostgreSQL 16.2 de QA, base nueva creada solo con Alembic. Antes de escribir la migración.
**Método:** `information_schema.columns` sobre la cabeza pública `0084_fusion_importaciones_proc03` y sobre el árbol local con gastos; `sqlalchemy` y `alembic.autogenerate.compare_metadata` para modelo contra esquema; lectura de las migraciones.

## Inventario

Tablas reales con prefijo `import_` en PostgreSQL migrado: 5 publicadas, más 1 local. `exchange_rate_import_batches` contiene «import» pero es de Tesorería y ya cumple el contrato (`CURRENT_TIMESTAMP`); no se toca.

Contrato del modelo, común a las seis por `TimestampMixin` (`app/shared/mixins.py:21`):

- `created_at`: `DateTime(timezone=True)`, `server_default=func.now()`, `NOT NULL`.
- `updated_at`: igual, y además `onupdate=utcnow` en el lado de Python.

| TABLE | MODEL_CREATED_AT_CONTRACT | MODEL_UPDATED_AT_CONTRACT | MIGRATION_CREATED_AT_DEFAULT | MIGRATION_UPDATED_AT_DEFAULT | POSTGRES_COLUMN_DEFAULT | MISMATCH | ACTION_REQUIRED |
|---|---|---|---|---|---|---|---|
| `import_files` | `now()` | `now()` + `onupdate` | Ninguno (`0080`) | Ninguno (`0080`) | Ninguno | SÍ | Migración correctiva |
| `import_documents` | `now()` | `now()` + `onupdate` | Ninguno (`0080`) | Ninguno (`0080`) | Ninguno | SÍ | Migración correctiva |
| `import_tracking_events` | `now()` | `now()` + `onupdate` | Ninguno (`0082`) | Ninguno (`0082`) | Ninguno | SÍ | Migración correctiva |
| `import_financial_links` | `now()` | `now()` + `onupdate` | Ninguno (`0082`) | Ninguno (`0082`) | Ninguno | SÍ | Migración correctiva |
| `import_corrections` | `now()` | `now()` + `onupdate` | Ninguno (`0082`) | Ninguno (`0082`) | Ninguno | SÍ | Migración correctiva |
| `import_expenses` (sin publicar) | `now()` | `now()` + `onupdate` | Ninguno (`0085` local) | Ninguno (`0085` local) | Ninguno | SÍ | Corregir en su propia migración, que no tiene identidad protegida |

`ALL_IMPORT_TIMESTAMP_TABLES_AUDITED = 1`

## Patrón canónico del repositorio

En la cabeza pública, de las 271 tablas con `created_at`:

| Default | Tablas |
|---|---|
| `now()` | 260 |
| `CURRENT_TIMESTAMP` | 6 |
| Ninguno | 5, todas `import_*` |

`updated_at` da exactamente el mismo reparto. El tipo es `timestamp with time zone` en todas. La forma más común en las migraciones es `server_default=sa.func.now()` (161 columnas `created_at` en las últimas 40 migraciones que las crean). Las únicas migraciones del repositorio con la columna sin default son `0080_importaciones`, `0082_importaciones_seguimiento` y la local de gastos.

## Datos existentes

- Las diez columnas publicadas ya son `NOT NULL` desde su creación: una fila con nulo no puede existir, en ninguna base. No hace falta rellenar nada ni fabricar fechas.
- Sin default, una fila solo pudo entrar con la fecha escrita de forma explícita. La aplicación no lo hace, así que por la pantalla no pudo crearse ninguna en `import_files`.
- En la base de QA medida, todas las tablas tienen 0 filas. Esto no se asume para otras bases: la migración solo cambia el default de la columna, no reescribe filas y su prueba lo demuestra con una fila previa.

## Otras diferencias de `import_*` entre modelo y esquema

Salida de `compare_metadata`. No son timestamps; se registran para que no queden ocultas.

| Tabla | Columna | Base | Modelo | Efecto | Acción |
|---|---|---|---|---|---|
| `import_corrections` | `created_by` | `NOT NULL` | Admite nulo | La base es más estricta. Falla solo si el servicio no pasa el actor | **Resultó defecto real:** el servicio no pasaba el actor. Corregido en el servicio |
| `import_financial_links` | `created_by` | `NOT NULL` | Admite nulo | Igual | Igual: corregido en el servicio |
| `import_tracking_events` | `created_by` | `NOT NULL` | Admite nulo | Igual | Igual: corregido en el servicio |
| `import_corrections` | `version` | `INTEGER`, sin default | `BIGINT`, default `1` | Python pone `1` y el rango de `INTEGER` sobra para una versión | Deuda registrada; sin efecto funcional |
| `import_expenses` (local) | `version` | `INTEGER`, sin default | `BIGINT`, default `1` | Migración sin identidad protegida | Alinear con el modelo en su migración |
| `import_expenses` (local) | `created_by` | `NOT NULL` | Admite nulo | El servicio siempre pasa el actor | Se conserva: la base más estricta es correcta aquí |

## Por qué no se vio antes

`qa` y la pila UAT crean el esquema de SQLite con `Base.metadata.create_all`, que sí aplica el `server_default` del modelo. `tests/conftest.py` hace lo mismo sobre PostgreSQL, así que tampoco las pruebas de backend con `KONTROL_TEST_DB_URL` ejecutan estas migraciones. Solo una base creada con Alembic revela la diferencia: es lo que hace `qa/e2e-run.py`.

## Resultado tras corregir

Medido en base nueva: 0 columnas `created_at` o `updated_at` `NOT NULL` sin default en todo el esquema. Una prueba guardiana lo vigila (`tests/test_spec018_migration_timestamps.py`). Migración: `0086_importaciones_timestamps`; la de gastos pasa a `0087_importaciones_gastos`. El número `0085` no se usa: esa migración nunca se publicó.
