# N3 — INFORME DE EXPANSIÓN DE ESQUEMA

Fecha: 2026-08-31 · PostgreSQL **18.6** en UTC

## 1. Qué hace N3, y qué deliberadamente no

Solo esquema. **Ni un dato se toca.** Se añaden columnas vacías para que el
backfill tenga dónde escribir sin destruir lo que hay.

Reinterpretar `company_id` ahora —sustituir el tenant por una empresa deducida—
borraría la única evidencia que queda de a quién pertenecía la fila. Por eso la
evidencia se preserva primero y se reconstruye después.

## 2. Migraciones

| Migración | Ola | Tablas |
|---|---|---:|
| `0025_mc_expand_masters` | maestros y transversales | 14 |
| `0026_mc_expand_purchasing` | compras | 14 |
| `0027_mc_expand_inventory` | inventario | 11 |
| `0028_mc_expand_sales` | ventas | 8 |
| `0029_mc_expand_treasury` | tesorería | 11 |
| `0030_mc_expand_fiscal` | fiscal | 11 |
| `0031_mc_expand_regulatory` | regulatorio | 11 |
| `0032_mc_expand_tenant_scoped` | alcance de tenant | 5 |
| **Total** | | **85** |

Ocho migraciones pequeñas y auditables, no una monolítica. Cada una puede
revisarse y revertirse por separado.

## 3. Qué añade cada tipo

### A las 80 tablas de empresa cuyo `company_id` guarda el tenant

| Columna | Para qué |
|---|---|
| `legacy_scope_id` | Recibirá el valor original cuando el backfill lo sustituya. Se crea ahora, vacía, para que la evidencia tenga dónde ir antes de hacer falta |
| `scope_backfill_class` | Guardará la clase `MC-A`..`MC-E` con la que la fila se clasificó, para que la decisión viva en el dato y no solo en un informe |

### A las 5 tablas que son del tenant con nombre falso

`tenant_id` con **clave foránea real** a `tenants`, vacía y anulable. El traslado
del valor y la retirada de `company_id` llegan en el backfill y en la
contracción.

`outbox_events` queda fuera: **ya tenía** `tenant_id` propio.

## 4. Lo que N3 no toca

| Grupo | Tablas | Por qué |
|---|---:|---|
| Ya correctas, con FK a `companies` | 8 | Specs 008, 045 y 046 |
| Derivadas | 35 | Alcanzan su empresa por FK obligatoria; no necesitan columna |
| Instalación y global | 16 | No son de empresa |
| Del tenant con `company_id` que sí designa empresa | 3 | `user_roles`, `user_scopes`, `audit_events`: la fila es del tenant, la columna designa empresa. Pasan a FK real en N7 |

## 5. Verificación

| Prueba | Resultado |
|---|---|
| Base vacía → `alembic upgrade head` | **PASS** |
| Generación de SQL en modo offline | **PASS** — 172 sentencias, solo esquema |
| Base legacy → `head` | **PASS** — 8 migraciones aplicadas |
| Conteos antes = después | **idénticos** |
| Huella de `parties(id, company_id, created_at)` | **sin cambio** |
| Columnas nuevas rellenadas | **0** |

La huella es un `sha256` del contenido de la columna que el backfill sustituirá.
Que no cambie es la prueba de que N3 no reinterpretó nada.

## 6. Estado de las tablas

Ninguna alcanza `BACKFILLED`. El máximo estado tras esta fase es
`PREFLIGHT_READY` / `CLASSIFIED`.
