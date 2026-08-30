# SPEC 011 — UNIDADES, PRESENTACIONES Y CONVERSIONES

| Campo | Valor |
|---|---|
| Estado | Ciclo documental · **no implementada** |
| Autoridad principal | `ADR-D0-009` — Unidad, presentación y conversión en toda transacción |
| Riesgo histórico | **MÁXIMO** (`D0-historical-data-risk.md`) |
| Specs afectadas | 015-023, 025, 026, 027, 028, 029, 032, 034, 035, 036, 043 |
| Motor | PostgreSQL **18.x** (`ADR-D0-001` `CONFIRMED_BY_EXECUTION`) |

---

## 1. Propósito

Que una cantidad escrita hoy siga significando lo mismo dentro de diez años,
aunque la configuración del producto haya cambiado tres veces.

Hoy KONTROL guarda `quantity` y nada más. Un `10` en una orden de compra puede
ser diez unidades, diez cajas de cien o diez kilos: **el sistema no lo sabe, y no
existe forma de averiguarlo después**. Esta Spec captura esa semántica en el
momento de escribir, que es el único momento en que existe.

## 2. Punto de partida real — verificado, no supuesto

Leído del código, no de los nombres (§3, §7, §37):

| Comprobación | Estado real |
|---|---|
| `units_of_measure` | **Existe**: `code`, `name`, `symbol`, `dimension`, `decimals`, `company_id` nullable, `status` |
| `unit_conversions` | **Existe** con `factor` en **`Float`**. Un `POST` la escribe; **nada la lee jamás** |
| `presentations` | **Existe**: `product_id`, `unit_id`, `content` (`Float`), `barcode`, `buyable`, `sellable`, `storable`. **Sin un solo endpoint**. Sin factor explícito, sin versión, sin estado |
| `catalog_items.base_unit_id` | **Existe, nullable**, se escribe al crear y **no se usa en ningún cálculo** |
| Líneas transaccionales con cantidad | **21** |
| Con `uom_id` | **2**, ambas nullable; `inventory/service.py:382` escribe `unit_id=None` literal |
| Con `presentation_id` | **0** |
| Con factor congelado | **0** |
| Con cantidad base | **0** |
| Columnas de cantidad o factor en `Float` | **31** · en `Numeric`: **0** |
| Lógica de conversión en la aplicación | **Ninguna** |

`sales_invoice_lines.base_fiscal` es base imponible en moneda, **no** cantidad
base. El `snapshot: Text` de algunas líneas lo envía el cliente por API: no es
autoridad de nada.

> Este es el **patrón Sucursales** en su forma más cara: tres maestros
> construidos, cero transacciones que los usen.

## 3. Alcance

### Incluido

1. Modelo definitivo de unidad de medida, con dimensión y precisión.
2. Unidad base **obligatoria** por producto inventariable, e inmutable con historial.
3. `ProductPresentation`: la presentación con su factor, **versionada por vigencia**.
4. Motor único de conversión, autoridad transversal (P22).
5. Las **cuatro columnas** de snapshot en las **17** líneas `MUST_HAVE_NOW`.
6. Conversión de las 31 columnas de cantidad y factor de `Float` a `NUMERIC`.
7. Migración de datos legados con clasificación en cuatro clases.
8. API de unidades, presentaciones, versiones y previsualización de conversión.
9. Pantallas de unidades y de presentaciones por producto.
10. Contratos declarados para las 14 Specs consumidoras.

### Fuera de alcance

Flujo de compra, recepción, inventario/Kardex, venta, picking, despacho,
facturación fiscal y devoluciones (§39). Variantes, atributos y kits, que son de
la Spec 010 (§17). Motor de precios, de la Spec 012 (§52). Empaquetado físico de
despacho (§20). Peso variable / *catch weight* (§34) y alias de unidad (§31):
`FUTURE_CAPABILITY`.

011 **modifica columnas estructurales compartidas** de otros dominios —es
inevitable para preservar la unidad— pero **no implementa sus procesos**.

## 4. Actores

| Actor | Interés |
|---|---|
| Administrador de maestros | Define unidades y presentaciones |
| Comprador | Pide en la presentación del proveedor |
| Vendedor | Vende en la presentación comercial |
| Supervisor de inventario | Necesita el saldo en una unidad consistente |
| Auditor / fiscal | Necesita reconstruir un documento emitido sin depender del maestro vigente |

## 5. Historias de usuario

| ID | Como… | Quiero… | Para… |
|---|---|---|---|
| HU-011-01 | administrador | definir las unidades que usa mi empresa | no depender de un catálogo ajeno |
| HU-011-02 | administrador | declarar la unidad base de cada producto | que el inventario tenga un significado único |
| HU-011-03 | administrador | definir que una caja de este producto son 100 unidades | comprar en cajas y controlar en unidades |
| HU-011-04 | administrador | cambiar ese factor sin alterar el pasado | corregir hacia adelante sin falsear el histórico |
| HU-011-05 | comprador | pedir 10 cajas | que el inventario reciba 1.000 unidades |
| HU-011-06 | vendedor | vender 5 bolsas | que el pedido descuente 100 unidades |
| HU-011-07 | supervisor | ver el saldo siempre en unidad base | no sumar peras con cajas |
| HU-011-08 | auditor | reimprimir una factura de hace dos años | verla exactamente como se emitió |
| HU-011-09 | administrador | desactivar una presentación que ya no uso | sin borrar los documentos que la usaron |
| HU-011-10 | usuario de producto simple | no configurar nada | que un producto en unidades funcione sin presentaciones |

## 6. Modelo conceptual

```
UnitOfMeasure ──┐
                ├── CatalogItem.base_unit_id  (obligatoria si es inventariable)
                │
                └── ProductPresentation (producto × presentación)
                        └── ProductPresentationVersion (factor, vigencia)

Línea transaccional:
    quantity + uom_id + presentation_id? + conversion_factor_snapshot + base_quantity
```

> **R-011-1 · La presentación no es un SKU.** Un producto con tres presentaciones
> sigue siendo un producto. Si una diferencia de presentación implica realmente
> otro artículo, eso son variantes y pertenece a la Spec 010 (§16, §17).

> **R-011-2 · Dos conversiones distintas.** La conversión **física** entre
> unidades de la misma dimensión (`KG ↔ G`) y la conversión **comercial** de una
> presentación a la unidad base (`CAJA → 100 UND`) son cosas diferentes y se
> modelan por separado (§33).

> **R-011-3 · La unidad base no cambia con historial.** Antes de que existan
> movimientos, la unidad base de un producto puede corregirse. Después, no puede
> cambiarse por edición: pasar de `UND` a `CAJA` reinterpretaría retroactivamente
> todas las cantidades registradas. Si alguna vez hiciera falta, será un proceso
> controlado con su propia definición, no un `UPDATE`.

> **R-011-4 · `factor = 1` es una conclusión, no un valor por defecto.** Solo se
> escribe cuando puede demostrarse que la cantidad transaccional ya está
> expresada en la unidad base de esa línea. Nunca como comodidad técnica para
> que una migración termine.

## 7. Requisitos funcionales

### Unidad de medida

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-001 | `UnitOfMeasure` con `code`, `name`, `symbol`, `dimension`, `decimals`, `rounding_mode`, `status` | P0 |
| FR-011-002 | `dimension` de vocabulario cerrado: `CANTIDAD`, `PESO`, `VOLUMEN`, `LONGITUD`, `AREA`, `TIEMPO` | P0 |
| FR-011-003 | Catálogo **global** (`company_id` nulo) más unidades **por empresa**; la empresa no puede editar las globales | P0 |
| FR-011-004 | El catálogo global nace **vacío**: KONTROL no entrega unidades predefinidas | P0 |
| FR-011-005 | `UNIQUE (company_id, code)`, admitiendo el mismo código en el ámbito global y en el de una empresa | P0 |
| FR-011-006 | `decimals` y `rounding_mode` pertenecen a la unidad; el producto puede restringir, nunca ampliar | P0 |
| FR-011-007 | Una unidad usada no se borra; se desactiva | P0 |

### Conversión física entre unidades

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-010 | `UnitConversion` solo entre unidades de la **misma dimensión** | P0 |
| FR-011-011 | `factor` en `NUMERIC(18,6)`, `> 0`, **nunca `Float`** | P0 |
| FR-011-012 | Se rechaza `KG ↔ L`: no se inventan conversiones físicamente inválidas | P0 |
| FR-011-013 | La conversión física **no** sustituye a la presentación comercial (R-011-2) | P0 |

### Unidad base del producto

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-020 | Todo producto **inventariable** tiene `base_unit_id` **obligatoria** | P0 |
| FR-011-021 | Un servicio **no** requiere unidad base de inventario; puede tener unidad de facturación | P0 |
| FR-011-022 | Sin movimientos, la unidad base puede cambiarse | P0 |
| FR-011-023 | **Con movimientos, la unidad base no puede cambiarse** por edición: se rechaza (R-011-3) | P0 |
| FR-011-024 | Un producto sin presentaciones funciona: no se obliga a crear una presentación «Unidad» | P0 |

### Presentación y factor

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-030 | `ProductPresentation` relaciona producto y presentación; **el factor vive aquí**, no en la presentación genérica | P0 |
| FR-011-031 | Marcas de uso: `buyable`, `sellable`, `storable`, `dispatchable` | P0 |
| FR-011-032 | `factor_to_base` en `NUMERIC(18,6)`, estrictamente `> 0` | P0 |
| FR-011-033 | Factores **decimales** admitidos: un saco de 25,5 KG es válido | P0 |
| FR-011-034 | Versionado por vigencia: `valid_from`, `valid_to` | P0 |
| FR-011-035 | **Sin solapamiento**: dos versiones vigentes del mismo par producto-presentación en la misma fecha se rechazan en base de datos | P0 |
| FR-011-036 | Cambiar un factor **crea una versión nueva**; jamás sobrescribe la anterior | P0 |
| FR-011-037 | Una presentación usada no se borra; se desactiva | P0 |
| FR-011-038 | Una presentación cuyo factor no sea exacto en unidad base debe declararlo explícitamente (R-D0-09-5) | P0 |

### Motor de conversión

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-040 | **Una sola** autoridad de conversión; ningún módulo replica el cálculo (P22) | P0 |
| FR-011-041 | `resolve_conversion(product, presentation, date)` devuelve la versión aplicable | P0 |
| FR-011-042 | `to_base(quantity, ...)` devuelve la cantidad base y el factor aplicado | P0 |
| FR-011-043 | El **backend** es la autoridad: nunca acepta `base_quantity` del cliente sin recalcularla | P0 |
| FR-011-044 | El frontend puede previsualizar; su resultado no es vinculante | P0 |
| FR-011-045 | El redondeo ocurre en **un solo lugar**, según `decimals` y `rounding_mode` de la unidad base | P0 |
| FR-011-046 | Resolución **masiva** para procesos con muchas líneas: sin N+1 | P1 |

### Snapshot histórico

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-050 | Toda línea `MUST_HAVE_NOW` conserva `uom_id`, `presentation_id?`, `conversion_factor_snapshot` y `base_quantity` (R-D0-09-1) | P0 |
| FR-011-051 | `base_quantity` se calcula al escribir y **se almacena**; jamás se recalcula desde el maestro (R-D0-09-2) | P0 |
| FR-011-052 | Cambiar un factor **no** altera ningún documento emitido ni ningún saldo histórico (R-D0-09-4) | P0 |
| FR-011-053 | El snapshot se fija al **emitir o aprobar**; mientras el documento sea editable se recalcula (CL-011-04) | P0 |
| FR-011-054 | Cambiar la presentación de una línea **editable** recalcula; sobre una línea emitida se rechaza | P0 |
| FR-011-055 | Una factura reimpresa usa **su** snapshot; nunca consulta el factor vigente | P0 |
| FR-011-056 | `uom_source` distingue lo capturado de lo supuesto: `CAPTURED`, `LEGACY_ASSUMED_BASE`, `LEGACY_RECONSTRUCTED`, `LEGACY_UNRESOLVED`, `LEGACY_UNVERSIONED` | P0 |
| FR-011-057 | Se conserva el símbolo de la unidad y la etiqueta de la presentación **solo** en documentos emitidos, para reimpresión fiel | P1 |

### Tipos numéricos

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-060 | Las 31 columnas de cantidad y factor pasan de `Float` a `NUMERIC` | P0 |
| FR-011-061 | Ninguna cantidad, factor ni cantidad base usa `Float` en el modelo nuevo | P0 |
| FR-011-062 | La cantidad admite decimales: 2,75 metros y 0,750 litros son válidos | P0 |
| FR-011-063 | La conversión de `Float` a `NUMERIC` **reporta** toda fila cuyo valor cambie | P0 |
| FR-011-064 | Coherencia verificable: `base_quantity = quantity × conversion_factor_snapshot`, con el redondeo declarado | P0 |

### Migración legada

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-070 | Cada línea histórica se **clasifica** antes de tocarse: `DETERMINISTIC_BACKFILL`, `RECONSTRUCTIBLE_WITH_EVIDENCE`, `AMBIGUOUS`, `NON_RECONSTRUCTIBLE_FISCAL` | P0 |
| FR-011-071 | `factor = 1` solo cuando puede demostrarse que la cantidad ya está en unidad base (R-011-4) | P0 |
| FR-011-072 | La reconstrucción exige candidata **única**; varias degradan a `AMBIGUOUS` | P0 |
| FR-011-073 | Una línea `AMBIGUOUS` queda con `uom_id` nulo y marcada; **no** se le asigna la unidad más probable | P0 |
| FR-011-074 | Una línea fiscal emitida no reconstruible **no se toca**; se registra la incidencia | P0 |
| FR-011-075 | Si las incidencias fiscales superan el umbral declarado, la migración **aborta** | P0 |
| FR-011-076 | Reporte auditable con los once recuentos y detalle por línea afectada | P0 |
| FR-011-077 | La `quantity` original **nunca** se modifica durante el backfill | P0 |

### API, permisos y auditoría

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-080 | Endpoints de unidad: listar, detalle, crear, editar, activar, desactivar | P0 |
| FR-011-081 | Endpoints de presentación por producto y de versiones de factor | P0 |
| FR-011-082 | Endpoint de **previsualización** de conversión, informativo | P1 |
| FR-011-083 | `allowed_actions` y `can_delete` calculados en backend | P0 |
| FR-011-084 | Permisos con la convención vigente del proyecto, sin sistema paralelo | P0 |
| FR-011-085 | Auditoría por la capacidad transversal, sin tabla local | P0 |
| FR-011-086 | `If-Match` con el mecanismo existente, sin crear otro | P0 |
| FR-011-087 | Aislamiento multiempresa en toda consulta y escritura | P0 |

### Frontend

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-090 | Pantalla de unidades con URL propia | P0 |
| FR-011-091 | Presentaciones del producto en **página completa**, no modal | P0 |
| FR-011-092 | La conversión se muestra en lenguaje claro: «CAJA equivale a 100 UND», no «Factor = 100» | P0 |
| FR-011-093 | Previsualización visible: «10 CAJAS = 1.000 UND» | P1 |
| FR-011-094 | Historial de versiones del factor, sin permitir editar una versión en uso | P0 |
| FR-011-095 | Entradas numéricas **vacías** al inicio; el factor se valida `> 0` | P0 |
| FR-011-096 | Selectores de catálogo grande con búsqueda asíncrona | P1 |
| FR-011-097 | Un producto sin presentaciones no muestra configuración innecesaria | P0 |

### Contratos para Specs futuras

| ID | Requisito | Prioridad |
|---|---|---|
| FR-011-100 | Contrato de conversión reutilizable por 015-023, 025-036 sin acoplarse a tablas | P0 |
| FR-011-101 | Contrato de precio por unidad o por presentación, sin implementar motor de precios (§52) | P1 |
| FR-011-102 | Contrato de despacho: unidad de empaque desacoplada de la presentación comercial (§20) | P1 |
| FR-011-103 | Contrato de recepción: verificar contra la presentación de la orden (§21) | P1 |
| FR-011-104 | Contrato de seriales: coherencia entre cantidad base y número de seriales (§73) | P1 |
| FR-011-105 | Contrato de reportes: cantidad original con su unidad, y cantidad base (§76) | P1 |

## 8. Requisitos no funcionales

| ID | Requisito |
|---|---|
| NFR-011-01 | Resolver la conversión de 1.000 líneas sin N+1 |
| NFR-011-02 | La caché de conversiones **nunca** altera la precisión histórica |
| NFR-011-03 | Índices justificados por consulta real |
| NFR-011-04 | WCAG 2.2 AA en las pantallas de 011 |
| NFR-011-05 | Responsive de 320 a 1920 px sin scroll horizontal |
| NFR-011-06 | Páginas completas con URL propia; modal solo para confirmación breve |
| NFR-011-07 | **Toda la evidencia sobre PostgreSQL 18.x**; nunca en modo `--sql` para la migración de datos |
| NFR-011-08 | Sin unidades ni presentaciones codificadas: todo es dato (P8) |

## 9. Reglas no negociables

1. Una transacción histórica **no** depende de la configuración vigente para interpretarse.
2. `base_quantity` se calcula al escribir y se almacena; jamás se recalcula.
3. La unidad base **no cambia** en un producto con movimientos.
4. Cambiar un factor **crea una versión**; nunca sobrescribe.
5. Una factura emitida **nunca** se recalcula: se reimprime desde su snapshot.
6. El inventario se lleva **siempre** en unidad base.
7. Una presentación **no** es un SKU.
8. Ninguna cantidad ni factor usa `Float`.
9. `factor = 1` es una **conclusión demostrada**, nunca un valor por defecto.
10. Una línea sin unidad conocida se marca; **no** se le inventa una.
11. Un documento fiscal emitido no reconstruible **no se toca**.
12. La conversión se calcula en **un solo lugar** del sistema.
