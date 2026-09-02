# SPEC 012 — MATRIZ DE ALCANCE, AUTORIDAD Y UNICIDAD

> Esta matriz **es** la matriz de alcance, la de autoridad y la de unicidad. No
> se dividen en tres documentos porque las tres columnas describen la misma
> decisión sobre la misma fila, y tres documentos con la misma verdad son tres
> sitios donde puede dejar de coincidir.

Once entidades. **Ninguna `UNKNOWN`.**

| Entidad | `__scope__` | `__scope_authority__` | Directa/Derivada | Columna de empresa | Unicidad |
|---|---|---|---|---|---|
| `payment_terms` | COMPANY | — | Directa | `company_id` obligatoria | `(company_id, code)` |
| `commercial_zones` | COMPANY | — | Directa | `company_id` obligatoria | `(company_id, code)` |
| `sales_channels` | COMPANY | — | Directa | `company_id` obligatoria | `(company_id, code)` |
| `price_lists` | COMPANY | — | Directa | `company_id` obligatoria | `(company_id, code)` |
| `price_list_versions` | COMPANY | `price_list_id → price_lists` | Derivada | **ninguna** | `(price_list_id, version_number)` |
| `price_list_items` | COMPANY | `version_id → price_list_versions` | Derivada | **ninguna** | ver más abajo |
| `price_precedence` | COMPANY | — | Directa | `company_id` obligatoria | `(company_id, order_index)` |
| `discount_policies` | COMPANY | — | Directa | `company_id` obligatoria | `(company_id, code, version)` |
| `credit_policies` | COMPANY | — | Directa | `company_id` obligatoria | `(company_id, code, version)` |
| `customer_commercial_terms` | COMPANY | `customer_id → customers` | Derivada | **ninguna** | `(customer_id)` |
| `sales_commission_policies` | COMPANY | — | Directa | `company_id` obligatoria | `(company_id, code)` — **reservada** |

## Por qué las derivadas no llevan `company_id`

Ocho de las once son de empresa por columna propia. Tres la alcanzan por su
padre, y **no deben duplicarla**.

Una `company_id` redundante en `price_list_items` sería una segunda respuesta a
una pregunta que ya tiene una. Y una segunda respuesta puede discrepar: es
exactamente el defecto que N7 encontró en las tablas de estructura de almacén,
donde `company_id` y `warehouse_id` podían contradecirse y hubo que añadir una
clave foránea compuesta para impedirlo.

Aquí no hace falta esa compuesta porque no hay dos caminos: hay uno.

La cadena completa, con cada eslabón obligatorio:

```
price_list_items.version_id  → price_list_versions   (NOT NULL, FK)
price_list_versions.price_list_id → price_lists      (NOT NULL, FK)
price_lists.company_id       → companies             (NOT NULL, FK)
```

```
customer_commercial_terms.customer_id → customers    (NOT NULL, FK)
customers.party_id           → parties               (NOT NULL, FK)
parties.company_id           → companies             (NOT NULL, FK)
```

Cada modelo declara **su** salto, no la cadena entera. Es la convención vigente
—`ApprovalStep` declara `request_id → approval_requests` y nada más— y es la que
`test_derived_scopes_use_non_nullable_fk_path` sabe verificar.

Rutas derivadas anulables: **0**. Ambiguas: **0**.

## La unicidad de `price_list_items`

Es la única que no es evidente, así que se declara entera:

```
(version_id, item_id, category_id, presentation_id, min_quantity)
```

con la condición de que `item_id` y `category_id` son **excluyentes**: uno de
los dos, nunca ambos, nunca ninguno.

No lleva `company_id` porque `version_id` ya la determina. Añadirla no haría la
unicidad más fuerte: haría posible que dos filas de la misma versión declararan
empresas distintas.

En PostgreSQL, con columnas anulables dentro de la clave, esto exige índices
únicos parciales —uno para la variante por artículo y otro para la de
categoría—, no una `UniqueConstraint` simple: en SQL, `NULL` no es igual a
`NULL`, y una restricción ingenua permitiría duplicados exactos.

## Referencias hacia fuera, y su comprobación

| Desde | Hacia | Alcance del destino | Comprobación obligatoria |
|---|---|---|---|
| `price_lists.currency_id` | `currencies` | COMPANY obligatoria | Misma empresa que la lista |
| `price_list_items.item_id` | `catalog_items` | COMPANY obligatoria | Misma empresa que la lista |
| `price_list_items.category_id` | `taxonomy_nodes` | COMPANY obligatoria | Misma empresa que la lista |
| `price_list_items.presentation_id` | `presentations` | COMPANY obligatoria | Misma empresa que la lista |
| `price_list_items.uom_id` | `units_of_measure` | COMPANY **anulable** | Propia **o de plataforma** |
| `commercial_zones.salesperson_id` | `users` | TENANT | Del tenant, con acceso a la empresa |
| `customer_commercial_terms.*_id` | maestros de 012 | COMPANY | Misma empresa que el cliente |

La quinta fila es la que se sale del patrón y por eso se escribe. Una unidad de
plataforma tiene `company_id` nulo y la ven todas las empresas; comprobar
igualdad estricta rechazaría una unidad legítima. La comprobación es:

```
uom.company_id IS NULL OR uom.company_id = ctx.company_id
```

La sexta también: el vendedor es un usuario, y los usuarios son del tenant. Que
un usuario exista en el tenant **no** significa que pueda operar en esta
empresa. Asignarlo como vendedor de una zona exige comprobar su acceso con
`accessible_company_ids`, que es la autoridad canónica — la misma que N10 tuvo
que aplicar en la elegibilidad de aprobadores, donde se recibía la empresa y no
se usaba.

## Lo que ninguna entidad de 012 es

Ninguna es de tenant. Ninguna es global. Ninguna es de instalación.

Dos empresas del mismo grupo tienen precios, plazos y límites de crédito
distintos; eso es el motivo de existir de esta Spec, y una sola entidad de
tenant lo desmentiría.
