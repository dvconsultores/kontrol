# VALIDACIÓN SOBRE POSTGRESQL — SPEC 045 (CVG-045-01 / CVG-045-02)

## Instancia

| Parámetro | Valor | Conforme a ADR-D0-001 |
|---|---|---|
| Motor | **PostgreSQL 16.2** (binarios de `pgserver`) | **Parcial**: el ADR fija 18.x. Es PostgreSQL real, no SQLite ni `--sql`; la diferencia de versión queda declarada |
| Puerto | 55432 (TCP, localhost) | — |
| Encoding | UTF8 | ✔ |
| Timezone | **UTC** | ✔ |
| Roles | `kontrol_migrator` (DDL) y `kontrol_app` (sin DDL) | ✔ separación de privilegios |
| Aislamiento de QA | Base por caso; un `schema` por módulo de prueba | ✔ no se usa producción |
| Reproducible | `qa/pg-provision.sh`, `qa/pg-migration-validation.sh`, `qa/pg-e2e-seed.py` | ✔ |

> `pgserver` es dependencia **solo de QA**: no está en `requirements.txt` ni se
> importa desde `app/`. En un entorno con Docker el equivalente es `compose.dev`.

## Suite de pruebas

| Motor | Resultado |
|---|---|
| **PostgreSQL 16.2** | **276 passed** (0 fallos) |
| SQLite (por defecto, sin regresión) | **276 passed** |

El motor se selecciona con `KONTROL_TEST_DB_URL`; sin él, SQLite. Helper
`make_engine()` en `tests/conftest.py`, que asigna un `schema` propio a cada
módulo mediante `connect_args` (no un listener de evento: registrarlo tras abrir
la primera conexión dejaba esa conexión en el pool sin `search_path`, y todas
las pruebas acababan compartiendo `public`).

## Defectos que PostgreSQL reveló y SQLite ocultaba

| # | Defecto | Origen | Corrección |
|---|---|---|---|
| **PG-01** | `0012` alteraba `amount` en **6 tablas que no tienen esa columna** (`purchase_order_lines`, `reconciliations`, `sales_invoices`, `supplier_invoices`, `supplier_quote_lines`, `triple_matches`). `UndefinedColumn` → **la cadena entera se detenía** | **Spec 012** (ajeno a 045) | Retiradas del bucle y añadidos los `_alter` de sus columnas reales |
| **PG-02** | `0014` alteraba `ap_advances.applied`, columna inexistente (la real es `available`) | **Spec 012** (ajeno a 045) | `ap_advances` retirada del bucle |
| **PG-03** | `0015` renombraba la tabla legada pero PostgreSQL **conserva los nombres de constraints e índices** → `pk_approval_requests` colisionaba con la tabla nueva | **045** | Renombrado explícito de `pk_` e `ix_` por dialecto |
| **PG-04** | `0016` fallaba si una fila legada apuntaba a una empresa inexistente: la tabla legada no tiene FK y la nueva sí | **045** | Omisión explícita con traza; la fila se conserva en la tabla legada |
| **PG-05** | Las FK **sí se exigen** en PostgreSQL: 30 pruebas de dominio insertaban referencias inexistentes | **Specs 002-009** (fixtures) | `seed_org_chain()` compartido en `conftest.py`; productos y almacenes reales |
| **PG-06** | Idempotencia bajo concurrencia real: dos `POST /approvals/requests` simultáneos → uno devolvía **500** | **045** | La colisión del índice único parcial se traduce en respuesta idempotente |

> **PG-01 y PG-02 significan que la cadena de migraciones de KONTROL nunca se
> había podido aplicar sobre PostgreSQL.** No es un defecto de 045: es un
> defecto de la remediación de la Spec 012 que solo se hace visible al ejecutar
> sobre el motor de producción, y que este cierre desbloqueó.

## Paridad de esquema ORM ↔ Alembic ↔ PostgreSQL

`alembic check` sobre base limpia:

| Ámbito | Drift |
|---|---|
| **Objetos de la Spec 045** | **0** |
| Tipos monetarios (`modify_type`) | **0** |
| Preexistente, Specs 001-011 | 18 elementos |

Desglose del drift preexistente:

| Tipo | Cantidad | Naturaleza |
|---|---:|---|
| `removed unique constraint` sobre `party_id` / `item_id` | 6 | **Falso positivo**: verificado en BD, `customers.party_id` **sí** tiene UNIQUE. Es la diferencia de representación índice/constraint de autogenerate |
| `removed index` | 6 | Índices creados por migración y no declarados en el ORM. Rendimiento, no corrección |
| `uq_release_versions_inst_version` (removed index + added constraint) | 1 objeto | Misma diferencia de representación |
| `add_index ix_fiscal_rules_rule_code` | 1 | ORM lo declara, la migración no lo crea. Rendimiento |
| `add_constraint uq_license_states_license_id` | 1 | **Real**: el ORM exige unicidad y la BD no la tiene → admite duplicados. **Spec 010** |
| `NOT NULL` en `license_central_config.sync_policy` y `license_entitlement_snapshots.modules` | 2 | **Real, menor**: la BD admite NULL donde el ORM no lo espera. **Spec 010** |

**Drift crítico atribuible a 045: 0.** Los 3 elementos reales pertenecen a la
Spec 010 y quedan escalados.
