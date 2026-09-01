# LIMPIEZA DE ORM Y ESQUEMA — N8

## 1. El ORM no tenía nada que limpiar

`legacy_scope_id` y `scope_backfill_class` nunca se declararon en ningún modelo.
N3 las añadió por migración y N4 concluyó que no había nada que migrar; entre
una cosa y otra, nadie las conectó.

| | |
|---|---:|
| Atributos ORM retirados | **0** (no existían) |
| Columnas retiradas del esquema | **160** (dos por tabla, en 80) |

## 2. La migración

`0038_n8_drop_legacy_scope`. Un `DROP` por columna, con `downgrade` que las
restituye vacías: una instalación que revirtiera necesitaría el esquema anterior
completo, aunque su contenido nunca tuvo información.

## 3. Instalación limpia

| | |
|---|---:|
| Migraciones desde base vacía | **38** |
| `legacy_scope_id` en el catálogo | **0** |
| `scope_backfill_class` en el catálogo | **0** |
| Head | `0038_n8_drop_legacy_scope` |

## 4. SQL sin conexión

`alembic upgrade 0037:head --sql` produce **160** sentencias `DROP COLUMN`
revisables antes de aplicarlas.

## 5. Deriva

ORM, migraciones y catálogo coinciden. La prueba de paridad que N7 introdujo
sigue verde: compara columna a columna lo que el modelo declara con lo que la
base tiene.

## 6. Lo que se conservó

Las migraciones `0025`–`0031` mantienen su texto original. No se reescriben para
fingir que las columnas nunca existieron: la evidencia de por qué se añadieron
es lo que explica por qué se pueden retirar.
