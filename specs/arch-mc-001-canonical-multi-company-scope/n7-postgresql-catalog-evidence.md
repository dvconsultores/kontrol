# EVIDENCIA DEL CATÁLOGO DE POSTGRESQL — N7

PostgreSQL **18.6** en UTC.

## 1. Por qué se mide en el catálogo y no en el ORM

Un modelo puede declarar `ForeignKey` y que la columna sea texto suelto en la
base. Es exactamente lo que ocurría en 80 tablas: el alcance estaba declarado,
el código escribía bien, y la base no comprobaba nada.

Todo el inventario de esta fase sale de `pg_constraint`, `pg_indexes` e
`information_schema`, no de `Base.metadata`.

## 2. Estado final

| Medida | Valor |
|---|---:|
| Claves foráneas | 327 |
| `company_id` sin referencia | **0** |
| `tenant_id` sin referencia | **0** |
| Rutas derivadas con clave real y obligatoria | 35 / 35 |
| Restricciones de unicidad | 32 |
| `company_id` anulable | 9, todas justificadas |

## 3. Las nueve columnas que siguen admitiendo nulo

Siete son de tablas de **tenant** donde la empresa es un estrechamiento
opcional: `roles`, `user_roles`, `user_scopes`, `idempotency_records`,
`legacy_document_references`, `audit_events`, `outbox_events`. Un rol global
significa «vale donde el usuario opere» — confundirlo con acceso a todas las
empresas fue un defecto real de N1, y el nulo **es** esa distinción.

Dos son de empresa, con razón escrita: `units_of_measure`, porque Spec 011 y
`OQ-MC-01` distinguieron unidades del sistema de las de negocio; y
`stored_files`, porque un archivo existe antes de saber a qué documento
pertenecerá.

Las nueve tienen clave foránea.

## 4. Paridad entre ORM, migraciones y catálogo

Una prueba compara, columna a columna, lo que el ORM declara con lo que la base
tiene. **Deriva: 0.**

Esa prueba existe por un error concreto de esta fase. Las claves se añadieron
primero solo en las migraciones, y como la base de pruebas nace de
`create_all`, las pruebas de corrupción se ejecutaban contra un esquema **sin
las restricciones**: fallaban con `DID NOT RAISE`, que es la forma afortunada de
enterarse. Si la base de pruebas se hubiera construido por migración, habrían
pasado en verde sin que el ORM tuviera nada.

## 5. Consultas usadas

```sql
-- claves foráneas por columna
SELECT con.conrelid::regclass::text, a.attname, con.confrelid::regclass::text
FROM pg_constraint con
JOIN unnest(con.conkey) WITH ORDINALITY k(attnum, ord) ON true
JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum
WHERE con.contype = 'f' AND con.connamespace = current_schema()::regnamespace;

-- obligatoriedad real
SELECT table_name, column_name, is_nullable FROM information_schema.columns
WHERE table_schema = current_schema();
```
