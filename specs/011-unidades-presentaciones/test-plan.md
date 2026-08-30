# PLAN DE PRUEBAS — SPEC 011

**Motor obligatorio: PostgreSQL 18.x** (P21, `ADR-D0-001` `CONFIRMED_BY_EXECUTION`).
SQLite solo donde la baseline lo permita para pruebas unitarias auxiliares, y
declarándolo.

## 1. Unidad (§86)

| Grupo | Casos |
|---|---|
| Conversión a base | Sin presentación · con presentación · factor decimal · cadena presentación→unidad→base |
| Factor | Entero · decimal · cero · negativo · nulo |
| Precisión | 0 decimales · 6 decimales · producto que restringe la unidad |
| Redondeo | Los cuatro modos · fracción no declarada → rechazo |
| Selección de versión | Antes de la primera · entre dos · después de la última · en el borde exacto |
| Inmutabilidad | Versión cerrada · versión en uso · snapshot escrito |
| Unidad base | Cambio sin movimientos · con movimientos · producto frente a servicio |
| Estados | Activa · inactiva · `can_delete` |
| Dimensión | Conversión válida · entre dimensiones distintas |
| Coherencia | `base = quantity × factor` en los cuatro modos de redondeo |

## 2. Integración sobre PostgreSQL (§87)

Crear unidad · crear presentación · asignarla a un producto · versionar el factor
· convertir · resolver con factor histórico · desactivar · duplicado · versión
concurrente · aislamiento multiempresa.

Añadidos por el alcance real:

- Producto **simple** de extremo a extremo, sin presentaciones.
- Producto **complejo** con tres presentaciones.
- Servicio con unidad de facturación y **sin** unidad base.
- `allowed_actions` en tres estados de permiso.

## 3. Contrato (§88)

OpenAPI ↔ frontend: DTO, **serialización decimal** (que un `NUMERIC` no vuelva a
convertirse en `float` al serializar), códigos de error, `allowed_actions`,
fechas de vigencia y forma del snapshot.

## 4. Concurrencia — solo PostgreSQL (§83)

| Caso | Resultado |
|---|---|
| Dos versiones abiertas simultáneas para la misma presentación | Una prospera; la otra 409 |
| Dos ediciones de la misma unidad con `If-Match` | Una prospera; la otra 409 |
| Emitir un documento mientras se activa una versión nueva | El snapshot es coherente: o el anterior o el nuevo, nunca mezclado |
| Alta simultánea del mismo código de unidad | Una sola fila |

## 5. Migración — los seis casos obligatorios

Todos sobre **PostgreSQL real**, con datos sembrados a propósito. **Nunca** en
modo `--sql`: el modo offline no lee datos y no puede clasificar.

| # | Escenario | Resultado exigido |
|---|---|---|
| 1 | Todos los productos con unidad base | Clase A; `quantity` intacta; `uom_source = LEGACY_ASSUMED_BASE` |
| 2 | Producto sin unidad base, una sola unidad en su evidencia | Clase B; unidad asignada; regla registrada |
| 3 | Producto sin unidad base, **dos** unidades en su evidencia | Clase C; `uom_id` nulo; **no** se elige la más frecuente |
| 4 | Línea de **factura emitida** en clase C | Clase D; **cero escrituras** sobre la línea; incidencia registrada; migración **abortada** si supera el umbral |
| 5 | Reejecución sobre base ya migrada | Idempotente |
| 6 | Base real pre-011 con datos de compras, ventas e inventario | Cadena completa aplica; recuentos intactos; invariante del reporte se cumple |

Comprobaciones transversales:

- El caso 4 se verifica **por inspección de la base tras el aborto**, no por el
  código de salida: ninguna columna escrita, ninguna restricción creada.
- `assigned_presentation = 0` en todos los casos.
- La `quantity` original no cambia en ningún caso (FR-011-077).

## 6. Conversión de tipo — prueba independiente

| Caso | Comprobación |
|---|---|
| Valor exacto en `Float` | Se conserva idéntico en `NUMERIC` |
| Valor con error de representación (`0.30000000000000004`) | Se convierte con la precisión declarada y **se reporta** |
| Recuento de filas | Idéntico antes y después |
| Suma agregada | Comparada antes y después; toda diferencia se reporta, ninguna se oculta |

## 7. Regresión

`test_inventory.py`, `test_purchasing.py`, `test_sales.py`, `test_maestros.py`,
`test_process_flows.py`, `test_idempotency_concurrency.py`, `test_fiscal.py`,
`test_reporting.py` y `test_approvals*.py`, **sin cambio de expectativa** salvo
donde el contrato cambie de forma documentada.

Los tres dominios de alto riesgo —`inventory`, `purchasing`, `sales`— reciben
columnas en 6 tablas cada uno **y** conversión de tipo: su batería completa es
criterio de salida.

## 8. E2E previsto (§89)

1. Crear una unidad.
2. Producto con unidad base.
3. Crear una presentación.
4. Definir el factor.
5. Ver la vista previa.
6. Guardar.
7. Crear una versión nueva del factor.
8. Comprobar que el histórico conserva la versión anterior.
9. Desactivar la presentación.
10. Intentar borrarla y ver el rechazo con su alternativa.
11. Aislamiento multiempresa.

Añadido: un recorrido de **producto simple** que no configura ninguna
presentación y funciona igual.

## 9. Cross-browser

Chromium, Firefox y WebKit. **WebKit no se reporta como Safari.**

## 10. Accesibilidad y responsive

axe WCAG 2.2 AA y 6 viewports **solo sobre las pantallas que 011 crea o
modifica**. Los defectos preexistentes de otras Specs se escalan, no se corrigen
aquí.

## 11. Rendimiento

Documento de 1.000 líneas: número de consultas **constante**, verificado contando
consultas, no midiendo tiempo. `EXPLAIN` sobre la resolución de versión por fecha.

## 12. Criterio de salida

- Suite completa verde **sobre PostgreSQL 18.x**.
- Los 40 criterios de aceptación cubiertos.
- Los 6 casos de migración y los 4 de conversión de tipo, verdes.
- Regresión de los tres dominios de alto riesgo en verde.
- 0 columnas de cantidad o factor en `Float`.
- 0 literales de unidad o presentación en el código.
- Un solo lugar en el código donde se convierte.
