# Delta Ciclo 4B · Distribución, preview y aplicación de landed cost

**Spec dueña:** 018, sobre la autoridad de costos de la Spec 003 (FR-003-080 a 083). **Autorización de implement:** encargo de la dueña del 2026-11-09, que nombra este ciclo. **Decisiones de negocio:** DM-IMP-COST-01 a 04, en `IMPORT_COST_ALLOCATION_CONTRACT.md`; no se reabren.

## Resultado para la dueña

En Compras → Importaciones → Expediente → Costos de importación: clasificar un gasto como capitalizable, elegir criterio, ver una vista previa que no cambia nada, aplicar con confirmación, ver el costo resultante por producto, consultar el historial y revertir cuando la regla lo permita. La valoración de inventario y las salidas posteriores usan el costo nuevo.

## Requisitos

- **FR-LC-01:** clasificación explícita del gasto: `CAPITALIZABLE`, `NOT_CAPITALIZABLE` o `UNDETERMINED`. Nace `UNDETERMINED`. Nada la deduce del tipo, el concepto o la factura. Solo `CAPITALIZABLE` se aplica.
- **FR-LC-02:** criterio por aplicación: `VALUE`, `QUANTITY` o `MANUAL`, sin default.
- **FR-LC-03:** la vista previa no escribe nada: ni capas, ni estado del gasto, ni tasas.
- **FR-LC-04:** aplicar es explícito, transaccional e idempotente. La base impide dos aplicaciones vigentes del mismo gasto.
- **FR-LC-05:** si una capa objetivo tiene `quantity_remaining < quantity_in`, se bloquea toda la aplicación.
- **FR-LC-06:** la reversión se vincula a la aplicación, no la borra y solo procede sin consumo.
- **FR-LC-07:** `valuation` y `_consume_cost` usan el costo efectivo. Salidas pasadas no se tocan.
- **FR-LC-08:** un gasto con aplicación vigente no se anula ni se reclasifica.

## Decisiones técnicas (`DERIVED_TECHNICAL_DECISION`)

Ninguna cambia un resultado de negocio. Se pueden revisar sin rehacer datos.

### Qué representa `CostLayer.landed_cost`

**Importe total asignado a la capa**, en `layer.currency`, sobre `quantity_in`. No es unitario.

Motivo: la columna es `Numeric(18,2)`. Un total conserva el céntimo exacto de la asignación; un unitario a dos decimales perdería dinero en cuanto la cantidad no divida exacto. Las dos representaciones dan el mismo resultado de negocio, y el total es la única que lo da sin pérdida.

### Costo efectivo

Una sola definición, en `app/modules/inventory/service.py`, sin motor paralelo:

```
costo_unitario_efectivo(capa) = unit_cost + landed_cost / quantity_in
valor_de_capa(capa)           = quantity_remaining × unit_cost + landed_cost × (quantity_remaining / quantity_in)
```

Con `quantity_in = 0`, el componente de landed cost es 0.

- **FIFO:** cada capa se consume a su costo efectivo.
- **AVERAGE:** el promedio pondera el costo efectivo de las capas participantes. El consumo proporcional existente no cambia.
- **Valoración:** suma `valor_de_capa`.
- **Historia:** una salida ya registrada conserva su `movement.unit_cost`. La aplicación exige capas sin consumo, así que nunca hay costo de venta previo que reescribir.
- **Carrera con una salida:** `_consume_cost` bloquea sus capas (`FOR UPDATE`), igual que la aplicación.

### Valoración por moneda

Hoy `GET /inventory/valuation` rotula `VED` y suma todas las capas aunque estén en monedas distintas. Desde que las capas llevan la moneda de la orden, ese total deja de significar algo. Se corrige sin conversión silenciosa, porque no hay política de reexpresión:

- La respuesta añade `by_currency: [{currency, valuation}]`.
- `currency` es la moneda real si hay una sola; si hay varias es `MIXED` y `valuation` es `null`, porque ese total no existe.
- Sin capas: `valuation = 0` y la moneda funcional.
- Convertir todo a una moneda queda fuera de este ciclo.

### Moneda e importe de valoración

La moneda de valoración es `layer.currency`, la misma en todas las capas del expediente porque salen de una sola orden. Si difieren, se bloquea.

| Caso | `valuation_amount` | Tasa |
|---|---|---|
| Gasto en moneda de la capa | `amount` | Identidad, sin consultar nada |
| Moneda funcional igual a la de la capa | `functional_amount` | La instantánea del gasto |
| Ninguna de las anteriores | `amount × tasa`, `ROUND_HALF_EVEN`, 2 decimales | Tasa gasto → capa **a la fecha del gasto**. Instantánea nueva al aplicar. Sin tasa: `RATE_NOT_AVAILABLE` |

Nunca se usa una tasa de hoy para un gasto pasado ni una tasa 1 por ausencia.

### Bases de reparto

- **VALUE:** `quantity_in × unit_cost` de la capa. Es lo aceptado al precio de la orden, en la moneda de la capa. Fuente: `COST_LAYER_RECEIVED_VALUE`.
- **QUANTITY:** cantidad base de la capa: `quantity_in × (movement.base_quantity / movement.quantity)`, leyendo el movimiento de entrada con `document_ref = receipt_ref`, el mismo producto y almacén y `quantity = quantity_in`. `quantity_in` guarda lo tecleado, no la base. Exige que todos los productos tengan la misma unidad base; si no, `IMPORT_COST_QUANTITY_NOT_COMPARABLE`. Sin movimiento identificable: `IMPORT_COST_QUANTITY_BASE_UNKNOWN`. No hay factor 1 supuesto.
- **MANUAL:** importe por capa, en moneda de valoración, ≥ 0, 2 decimales. Debe sumar exactamente `valuation_amount`; si no, la vista previa muestra la diferencia y no deja aplicar.
- Base total cero: `IMPORT_COST_BASE_ZERO`.

### Reparto y residuo (`LARGEST_REMAINDER`)

Aritmética exacta en céntimos, sin `float`:

1. `exacto_i = valuation_amount × base_i / total_bases`.
2. `redondeado_i` = `exacto_i` truncado a 2 decimales.
3. `residuo = valuation_amount − Σ redondeado_i`, en céntimos.
4. Cada céntimo va a la capa de mayor fracción descartada. Empate: `created_at` y después `id` de la capa.
5. `asignado_i = redondeado_i + ajuste_i`. Invariante: `Σ asignado_i = valuation_amount`.

### Vista previa obsoleta

La vista previa devuelve `preview_token`: sha256 de gasto (id, version, clasificación, importe), de cada capa (id, restante, landed, costo), del criterio, de los importes manuales y de `valuation_amount`. Aplicar recalcula y compara. Si difiere: 409 `IMPORT_COST_PREVIEW_STALE`. No se guarda nada al previsualizar.

### Doble aplicación

Índice único parcial sobre `import_cost_applications(expense_id) WHERE status = 'APPLIED'`, en PostgreSQL y SQLite. El gasto y las capas se bloquean con `FOR UPDATE`. Si la base rechaza por el índice, se responde 409 `IMPORT_COST_ALREADY_APPLIED`.

## Modelo de datos

- `import_expenses.capitalization`, `NOT NULL`, `server_default 'UNDETERMINED'`, con `CHECK`.
- `import_cost_applications`: empresa, expediente, gasto, criterio, `criterion_source`, `status` (`APPLIED`, `REVERSED`), moneda e importe de origen, instantánea y valor de la tasa del gasto, moneda e importe de valoración, instantánea de valoración si la hubo, `applied_at`, `applied_by`, `reversed_at`, `reversed_by`, `reversal_reason`, `version`, timestamps y `created_by`.
- `import_cost_allocations`: empresa, aplicación, capa, producto, `allocation_base`, `participation`, `exact_share`, `rounded_share`, `residual_adjustment`, `allocated_amount`, `currency`, `before_landed_cost`, `after_landed_cost`, `before_unit_cost`, `after_unit_cost`, timestamps y `created_by`. Único por aplicación y capa.

Todo relacional, sin JSON libre. Toda tabla nueva con `now()` en `created_at` y `updated_at`.

## API

| Ruta | Permiso | Efecto |
|---|---|---|
| `GET /importaciones/{id}/costs` | `compras:view` | Añade clasificación, aplicaciones, asignaciones, costo efectivo y bloqueos |
| `POST /importaciones/{id}/expenses/{gasto}/classification` | `compras:approve` | Clasifica |
| `POST /importaciones/{id}/expenses/{gasto}/allocation-preview` | `compras:view` | Solo lectura |
| `POST /importaciones/{id}/expenses/{gasto}/apply` | `compras:approve` | Aplica |
| `POST /importaciones/{id}/cost-applications/{aplicacion}/reverse` | `compras:approve` | Revierte, con motivo |

Auditoría: `IMPORT_EXPENSE_CLASSIFIED`, `IMPORT_COST_APPLIED`, `IMPORT_COST_REVERSED`. La vista previa no se audita porque no cambia estado.

## Tareas

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T-LC-A | Modelo, migración, clasificación, reparto y vista previa | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `imports/*`, migración, prueba nueva | Prueba funcional del reparto | Vista previa real y cuadrada, sin escrituras |
| T-LC-B | Aplicación, reversión, motor, valoración y auditoría | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `imports/*`, `inventory/*`, catálogo de auditoría | Prueba funcional sobre PostgreSQL | Salida posterior y valoración usan el costo nuevo |
| T-LC-C | Pantalla completa, valorización y notificación en teléfono | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `compras/importaciones/*`, `inventario/valorizacion/*`, `index.css` | Vitest dirigido | Flujo operable en 1280, 390 y 320 |
| T-LC-D | E2E de usuario sobre PostgreSQL | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `e2e/importaciones.spec.ts` | E2E Chrome | Flujo principal pasa |
| T-LC-E | Certificación, documentos y publicación | CLAUDE | n-a | NO | SÍ | 0 | Evidencia, matriz, tarjeta | Cierre técnico | `HEAD == origin/develop` |

`LOCAL_RULE_CONFLICT = 1`: `CLAUDE.md` reserva migraciones y fórmulas monetarias a Claude. La dueña decidió que DeepSeek escriba todo el código una vez fijados fórmula, escala, redondeo y contrato, que es lo que fija este documento.

## Fuera de alcance

Reporte formal de diferencias, reubicación, clasificación por atributos, zonas A a E, etiquetado, `IMP-CONFIRM-UUID-01`, y convertir la valoración a una sola moneda.

## Cierre

Publicado en `7fa4a82`. Evidencia en `evidence/landed-cost/EVIDENCE.md`. `OWNER_ACCEPTED` lo concede solo la dueña.
