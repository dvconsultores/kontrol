# SPEC 012 — REVALIDACIÓN CONTRA ARCH-MC-001 FINAL

> Medido el 2026-09-02 contra el código vigente en `f24b4c0`. Ninguna fila de
> este documento procede de la documentación anterior de la Spec 012.

## Baseline del repositorio, verificada

| Magnitud | Valor |
|---|---:|
| PostgreSQL | 18.6 · UTC |
| Modelos ORM · tablas | 166 · 166 |
| Entidades sin alcance | 0 |
| Claves foráneas | 331 |
| Rutas · operaciones | 294 · 404 |
| Operaciones con contrato de empresa | 342 |
| Migraciones | 39 (`0039_n10_scope_reconciliation`) |

Sin cambios desde el cierre de N10.

## Las dependencias de la Spec 012, medidas

| Entidad | Alcance real | Autoridad | Lo que la Spec 012 suponía |
|---|---|---|---|
| `parties` | **COMPANY** | `company_id` obligatoria, FK a `companies` | Suponía tenant; **corregido** |
| `customers` | **COMPANY** | `party_id → parties` | No lo declaraba |
| `suppliers` | **COMPANY** | `party_id → parties` | No lo declaraba |
| `catalog_items` | **COMPANY** | `company_id` obligatoria | Suponía tenant; **corregido** |
| `taxonomy_nodes` | **COMPANY** | `company_id` obligatoria | No lo nombraba (ver más abajo) |
| `units_of_measure` | **COMPANY** | `company_id` **anulable**: nulo = unidad de plataforma | Suponía empresa sin excepción |
| `presentations` | **COMPANY** | `company_id` obligatoria | Correcto |
| `currencies` | **COMPANY** | `company_id` obligatoria | Suponía «maestro existente» sin decir su alcance |
| `exchange_rates` | **COMPANY** | `company_id` obligatoria | Ídem |
| `warehouse_zones` | **COMPANY** | `company_id` obligatoria | Correcto: es otra cosa y la Spec ya lo decía |

### La premisa del bloqueo, resuelta

La Spec 012 se bloqueó porque `parties.company_id` guardaba el tenant y
`CustomerCommercialTerms` no habría podido distinguir la relación comercial de la
empresa A de la de la B.

Hoy `parties.company_id` es una empresa real, obligatoria y con clave foránea a
`companies`. La causa desapareció en origen.

### Tres cosas que la medición cambió

**1. `units_of_measure` admite empresa nula.** Una unidad con `company_id` nulo
es de la plataforma, la ven todas las empresas y es de solo lectura para ellas.
Un `PriceListItem` que referencie una unidad **no** puede comprobar
`uom.company_id == ctx.company_id`: la comprobación correcta es «propia o de
plataforma». Escrito así, sin la excepción, la Spec 012 habría rechazado
unidades legítimas.

**2. La categoría se llama `taxonomy_nodes`.** `data-model.md` decía «o
categoría» sin nombrar la tabla, y no existe ninguna `item_categories`. La
categoría de un artículo es `catalog_items.category_id → taxonomy_nodes`, de
empresa. Se nombra.

**3. `currencies` y `exchange_rates` son de empresa, no del tenant.** La
migración `0032` los había clasificado como de tenant; N7 corrigió esa
clasificación y N10 retiró del esquema la columna que quedaba. Una lista de
precios de la empresa A solo puede referenciar una moneda de A: es una
consistencia de par, no una clave foránea suelta.

## Lo que la auditoría original decía, reverificado

Ninguna de las once entidades de la Spec 012 existe. Ninguna tabla, ninguna
clave foránea, ninguna vigencia. Y sigue sin haber `price_1`..`price_5`: el
problema nunca fue un maestro mal modelado sino la ausencia de maestro.

El precio y el descuento se siguen tecleando en `Numeric(18,2)` sin origen ni
regla, y las cuatro condiciones comerciales del cliente siguen siendo
`String(120)` de texto libre.

## Dos contradicciones internas de la Spec 012

Encontradas al reconciliar, no heredadas de ARCH-MC-001:

**`spec.md` decía nueve entidades y `data-model.md` describía once.** La lista de
`spec.md` incluía `PriceRule`, que el modelo no tiene, y omitía
`price_precedence`, `customer_commercial_terms` y `sales_commission_policies`,
que sí están. Ambos quedan reconciliados en once, con `PriceRule` retirada por no
existir en ningún artefacto que la defina.

**El contrato de resolución de precio recibía `company_id` en el cuerpo.**
`POST /comercial/precio/resolver` lo declara en su carga útil. Es exactamente la
vulnerabilidad que la Spec 045 estrenó y que N5 cerró: el cliente eligiendo en
qué empresa opera. Se corrigió el contrato: la empresa la pone `CompanyContext`.
