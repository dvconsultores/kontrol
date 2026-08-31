# N4 — INFORME DE PREFLIGHT PREVIO AL BACKFILL

**Cero escrituras.** Ejecutado sobre PostgreSQL 18.6 en UTC. Puede repetirse
contra producción sin riesgo: no modifica ninguna fila, ni el esquema, ni la
versión de Alembic.

## 1. Base y conjunto de datos

| Campo | Valor |
|---|---|
| Motor | PostgreSQL **18.6** |
| Zona horaria | UTC |
| Origen | Fixture legacy representativo `kontrol_legacy` |
| Naturaleza | Sembrado a propósito con las formas reales del legado |
| Tenants | 2 |
| Empresas | 3 |
| Tablas analizadas | **80** |
| Filas que requieren reconstrucción | **8** |

> El entorno no tiene datos de producción. La cifra absoluta es pequeña **a
> propósito**: lo que este preflight demuestra no es el volumen, sino que cada
> forma del legado se clasifica como debe y que ninguna se inventa. Sobre una
> base real el mismo ejecutor da el mismo tipo de informe, con otras cifras.

## 2. Clasificación global

| Clase | Filas | Significado |
|---|---:|---|
| `MC-A` | 3 | Determinista: el tenant tuvo una sola empresa en el intervalo |
| `MC-B` | 1 | Reconstruible por una ruta histórica única |
| `MC-C` | 2 | Ambigua: más de una empresa posible |
| `MC-D` | 0 | Sin evidencia |
| `MC-E` | 1 | **Crítica** sin evidencia: fiscal, financiera o de inventario |
| `OK` | 1 | Ya contiene una empresa real; nada que reconstruir |

## 3. Por dominio

| Dominio | MC-A | MC-B | MC-C | MC-D | MC-E | OK |
|---|---:|---:|---:|---:|---:|---:|
| fiscal | 1 | 0 | 0 | 0 | 1 | 0 |
| inventory | 0 | 1 | 0 | 0 | 0 | 0 |
| master_data | 2 | 0 | 2 | 0 | 0 | 1 |

## 4. Por tabla con filas

| Dominio | Tabla | Filas | MC-A | MC-B | MC-C | MC-D | MC-E | OK |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| master_data | `parties` | 4 | 2 | 0 | 1 | 0 | 0 | 1 |
| fiscal | `fiscal_number_series` | 2 | 1 | 0 | 0 | 0 | 1 | 0 |
| master_data | `catalog_items` | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| inventory | `inventory_balances` | 1 | 0 | 1 | 0 | 0 | 0 | 0 |

Las otras **76** tablas de alcance de empresa están vacías en este conjunto.
Su plan de backfill queda definido igualmente; ver §7.

## 5. Prueba de cero escrituras

| Comprobación | Resultado |
|---|---|
| Conteos antes = después | **True** |
| Versión de Alembic sin cambio | **True** |
| Versión | `0032_mc_expand_tenant_scoped` |

## 6. Preparación para las restricciones de N7

| Comprobación | Resultado |
|---|---|
| Filas que hoy impedirían la FK a `companies` | **7** en 4 tablas |
| Filas que quedarían nulas con `NOT NULL` | **0** |
| Únicos con `company_id` revisados | **13** |
| Colisiones al estrechar de tenant a empresa | **0** |
| Secuencias de PostgreSQL | **0** — las claves primarias son UUID |

### Filas que bloquean la clave foránea

| Tabla | Filas |
|---|---:|
| `catalog_items` | 1 |
| `fiscal_number_series` | 2 |
| `inventory_balances` | 1 |
| `parties` | 3 |

Son exactamente las que todavía guardan el tenant. Desaparecen al ejecutar el
backfill: ninguna es un dato corrupto preexistente.

### Únicos revisados

| Tabla | Columnas | Colisiones |
|---|---|---:|
| `approval_policies` | `company_id`, `process_type`, `version` | 0 |
| `approval_requests` | `company_id`, `document_type`, `document_id`, `fingerprint` | 0 |
| `document_categories` | `company_id`, `code` | 0 |
| `document_types` | `company_id`, `code` | 0 |
| `documents` | `company_id`, `document_type_id`, `document_number` | 0 |
| `inventory_lots` | `company_id`, `product_id`, `lot_number` | 0 |
| `location_types` | `company_id`, `code` | 0 |
| `movement_types` | `company_id`, `code` | 0 |
| `product_serials` | `company_id`, `serial` | 0 |
| `supplier_invoices` | `company_id`, `supplier_id`, `invoice_number`, `control_number` | 0 |
| `units_of_measure` | `company_id`, `code` | 0 |
| `warehouses` | `company_id`, `code` | 0 |
| `zone_types` | `company_id`, `code` | 0 |

Ninguno colisiona al estrechar su alcance. El caso que sí cambia de
significado es `units_of_measure`, resuelto por la decisión de producto:
la unidad de negocio es de la empresa; la de sistema, con `company_id` nulo,
sigue siendo de la plataforma.

## 7. Qué ocurriría si se autorizase el backfill hoy

- **3 filas** se rellenarían por determinismo de intervalo.
- **1 fila** se rellenaría derivando de su autoridad.
- **2 filas** quedarían sin rellenar, marcadas para revisión manual.
- **0 filas** quedarían sin evidencia.
- **1 fila** bloquearía la ola fiscal.
- **1 fila** no se tocaría: ya es correcta.

## 8. Decisión

`BACKFILL NOT_STARTED` · `BACKFILL AUTHORIZED: NO`
