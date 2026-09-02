# SPEC 012 — INTEGRIDAD EN POSTGRESQL

PostgreSQL **18.6**, UTC. Instalación limpia migrada a `0041_spec012_exclusions`.

## Catálogo

| | Antes | Después |
|---|---:|---:|
| Modelos ORM | 166 | **177** |
| Tablas | 166 | **177** |
| Migraciones | 39 | **41** |
| Claves foráneas | 331 | **356** |

## Las once, en el catálogo

| Comprobación | Resultado |
|---|---:|
| Tablas creadas | 11 / 11 |
| `company_id` con FK a `companies` en las directas | 8 / 8 |
| `company_id` obligatoria en las directas | 8 / 8 |
| Derivadas **sin** `company_id` | 3 / 3 |
| Unicidad que incluye la empresa | 8 / 8 |
| Restricción de exclusión de solape | presente |
| Índices únicos parciales de ítems | 2 |
| Importes en coma flotante | **0** |

## Paridad ORM ↔ Alembic ↔ PostgreSQL

Desviación **0** en tablas, columnas, obligatoriedad y claves foráneas.

## Pruebas hostiles, por SQLSTATE

Se verifica el código de error real, no el mensaje: el mensaje viene traducido y
depende de la configuración regional.

| Caso | SQLSTATE | Resultado |
|---|---|---|
| Empresa inventada en `payment_terms` | `23503` | **PASS** |
| Empresa nula en `payment_terms` | `23502` | **PASS** |
| Versión sin lista | `23502` | **PASS** |
| Ítem con versión inventada | `23503` | **PASS** |
| Ítem sin artículo ni categoría | `23514` | **PASS** |
| Ítem con artículo **y** categoría | `23514` | **PASS** |
| Dos versiones activas que solapan | exclusión → `409` | **PASS** |
| Dos borradores que solapan | permitido | **PASS** |

## Dos detalles que la ejecución obligó a corregir

**La prueba de la clave foránea necesitaba un artículo real.** Sin él, la
restricción de «artículo o categoría» saltaba primero y la prueba habría pasado
sin comprobar nunca la clave foránea. Falla por el motivo correcto o no prueba
nada.

**Los dos borradores solapados son un caso positivo.** Sin el `WHERE status =
'ACTIVE'` la exclusión los prohibiría, y la restricción impediría trabajar en
vez de proteger. Se comprueba que **sí** se permiten.
