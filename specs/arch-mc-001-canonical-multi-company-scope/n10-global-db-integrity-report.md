# N10 — INTEGRIDAD EN POSTGRESQL

PostgreSQL **18.6**, UTC. Instalación limpia migrada a `head`
(`0039_n10_scope_reconciliation`) y comparada contra el ORM.

## Paridad ORM ↔ Alembic ↔ PostgreSQL

| Comparación | Desviación |
|---|---:|
| Tablas | **0** |
| Columnas | **0** |
| Obligatoriedad | **0** |
| Claves foráneas | **0** |

Antes de N10 no era cero.

## Lo que había

**Cinco columnas `tenant_id` en la base y en ningún modelo.** Las añadió la
migración `0032`, que afirmaba que `currencies`, `exchange_rates`,
`idempotency_records`, `legacy_document_references` y `report_definitions` eran
del tenant y anunciaba que el traslado del valor y la retirada de la columna
falsa llegarían «en el backfill y en la contracción».

No llegaron, y no por descuido: **N7 revisó la clasificación y la corrigió**.
Las tres primeras son de empresa —`create_currency` exige empresa, la API lista
por empresa, y una prueba de N5 ya demostraba que una moneda de A no sirve en
B—, con lo que el plan de `0032` perdió su motivo. Para las otras dos tampoco se
sostuvo.

Quedaron cinco columnas con clave foránea real, vacías, que ningún código
escribe ni lee y que el ORM nunca declaró. `0039` las retira. `0032` sigue en el
árbol y su `downgrade` las devuelve: la historia no se borra.

**Dos columnas obligatorias en el ORM y anulables en la base** desde `0010`:
`license_central_config.sync_policy` y `license_entitlement_snapshots.modules`.
Se ajusta la base al contrato, que es lo que el código da por cierto.

## Catálogo actual

| | |
|---|---:|
| Tablas funcionales | 166 |
| Claves foráneas (restricciones) | 331 |
| Restricciones únicas | 80 |
| Índices únicos | 214 |
| Columnas `company_id` | 107 (96 obligatorias) |
| Columnas `tenant_id` | 5 |
| `legacy_scope_id` / `scope_backfill_class` | 0 |

## La prueba que lo mantiene

`test_el_orm_y_la_base_no_difieren_en_nada` construye su propia base **con
Alembic** —no con `create_all`— y compara tablas, columnas, obligatoriedad y
claves foráneas en las dos direcciones.

Ese detalle es el que la hace válida. El resto de las suites levanta el esquema
desde el ORM; comparar el ORM contra eso sería preguntarle a alguien si está de
acuerdo consigo mismo. Es la trampa que N7 encontró en las pruebas de
corrupción, y la prueba lleva una comprobación explícita de que el esquema lo
construyó Alembic para que no pueda recaer en ella en silencio.
