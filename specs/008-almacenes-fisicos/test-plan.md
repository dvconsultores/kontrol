# PLAN DE PRUEBAS — SPEC 008

**Motor obligatorio: PostgreSQL 18.x** (P21; `ADR-D0-001` confirmado por ejecución sobre 18.6 el 2026-08-30 — ver `docs/governance/postgresql-version-validation.md`). PostgreSQL 16 es la mínima soportada, **no** el motor de aceptación.

## 1. Unidad

| Grupo | Casos |
|---|---|
| Coherencia de cadena | Cadena completa · con huecos · tramo de otro almacén · tramo no declarado por el almacén |
| Código | Generación por patrón · manual · colisión · unicidad por almacén |
| Etiqueta derivada | Con cadena completa · con tramos nulos · tras renombrar un tramo |
| Orden físico | Con y sin tramos nulos · empate por secuencia · estabilidad entre llamadas |
| Estados | Transiciones válidas · desactivación con hijos activos · `FULL` inexistente |
| `can_delete` | Sin historial · con movimientos · con saldo · con reservas |
| Reubicación | Sin historial permitida · con historial rechazada |

## 2. Integración sobre PostgreSQL (§47)

Los 12 casos exigidos: crear almacén, zona, pasillo, rack, nivel y ubicación;
jerarquía inválida; referencia entre empresas; código duplicado; desactivación;
borrado protegido; más búsqueda paginada y `/structure` con `depth`.

Añadidos por el alcance de esta Spec:

- Almacén **simple** de extremo a extremo (sin tramos).
- Almacén **complejo** de extremo a extremo.
- `location_managed=false`: operación a nivel de almacén.
- `allowed_actions` en tres estados de permiso.

## 3. Concurrencia — solo PostgreSQL (§55)

| Caso | Resultado esperado |
|---|---|
| Dos creaciones simultáneas del mismo código | Una prospera; la otra 409 |
| Dos ediciones simultáneas del mismo nodo | Una prospera; la otra 409 por `If-Match` |
| Desactivación mientras otra operación usa la ubicación | Estado final coherente, sin ubicación desactivada con operación en curso |
| Creación masiva concurrente con solapamiento de códigos | Sin duplicados |

## 4. Migraciones — los 6 casos del Control 1

Todos sobre **PostgreSQL real** con datos sembrados a propósito. **Nunca** en modo
`--sql`: el modo offline no lee datos y por tanto no puede clasificar.

| # | Escenario sembrado | Resultado exigido | Tarea | AC |
|---|---|---|---|---|
| 1 | Todas las referencias válidas | **PASS**; `valid = total`, `orphans = 0`; ninguna fila modificada | T-008-062 | AC-008-25 |
| 2 | Huérfana reconstruible por una **única** candidata | Reparada; `legacy_location_id` poblado; evidencia en el reporte. Con **dos** candidatas: degrada, no repara | T-008-063 | AC-008-26 |
| 3 | Huérfana no reconstruible, saldo cero, almacén sin gestión de ubicaciones | `NULL` + legacy preservado + incidencia con las tres condiciones evaluadas | T-008-064 | AC-008-27 |
| 4 | Huérfana crítica: saldo distinto de cero, irrecuperable | **MIGRACIÓN BLOQUEADA**; reporte emitido; **cero escrituras aplicadas** | T-008-065 | AC-008-28 |
| 5 | Base ya migrada, se reejecuta | Idempotente y no destructiva | T-008-066 | AC-008-29 |
| 6 | Base real pre-008 con datos de inventario, compras, ventas y conteos | Cadena completa aplica; recuentos intactos; `legacy_path` con el texto original; **ninguna zona creada automáticamente** | T-008-067 | AC-008-30 |

Comprobaciones transversales a los seis:

- Invariante `valid + reconstructed + nulled + critical = total_rows_checked`.
- El reporte permite responder, para toda fila modificada: qué valor tenía, qué
  valor tiene, por qué cambió y bajo qué clase.
- El reporte **no** contiene nombres de producto, cantidades, importes ni datos de
  tercero.
- El caso 4 se verifica **por inspección de la base tras el aborto**: sin FK
  creadas, sin referencias anuladas, sin `legacy_path` poblado. No basta con que la
  migración devuelva error.

## 5. Regresión

`test_inventory.py`, `test_purchasing.py`, `test_sales.py`, `test_regulatory.py`,
`test_process_flows.py`, `test_idempotency_concurrency.py` y `test_approvals*.py`
**sin cambio de expectativa**. `inventory` es el de mayor riesgo: sus tres
referencias pasan a FK.

## 6. E2E (§48)

Crear almacén · zona · pasillo · rack · nivel · posición · consultar · editar ·
desactivar · intentar borrar con referencia · ver auditoría · multiempresa.

Adaptaciones por la arquitectura final:

- Un escenario paralelo con **almacén simple**: crear almacén y ubicación, sin
  tramos intermedios, y comprobar que la interfaz no los pide.
- Los pasos de rack y nivel solo se ejecutan en el almacén que los declara.

## 7. Cross-browser

Chromium, Firefox y WebKit. **WebKit no se reporta como Safari.**

## 8. Accesibilidad y responsive

axe WCAG 2.2 AA y 6 viewports **solo sobre las pantallas que 008 crea o
modifica** (§43). Las 22 violaciones preexistentes detectadas en el cierre de 045
**no se corrigen aquí**.

## 9. Rendimiento

Conjunto de 50.000 ubicaciones: búsqueda por código P95 ≤ 200 ms; consulta
ordenada resuelta por índice, verificada con `EXPLAIN`; `/structure` sin
ubicaciones por defecto.

## 10. Mutabilidad estructural — los 8 casos del Control 2

| # | Caso | Resultado exigido | Tarea | AC |
|---|---|---|---|---|
| A | Modificar `structure_levels` sin datos dependientes | **Permitido** y auditado | T-008-068a | AC-008-31 |
| B | Eliminar un tramo **utilizado** | **Bloqueado** `STRUCTURE_LEVEL_IN_USE` con `dependencies` | T-008-068a | AC-008-32 |
| C | Reordenar tramos utilizados | **Bloqueado** `STRUCTURE_REORDER_FORBIDDEN` | T-008-068a | AC-008-33 |
| D | Desactivar nodo sin dependencias | **Permitido**, reversible, auditado en ambos sentidos | T-008-068b | AC-008-34 |
| E | Eliminar nodo con histórico, propio o **heredado** | **Bloqueado** `NODE_HAS_HISTORY`; `allowed_actions` ofrece `deactivate` | T-008-068b | AC-008-35 |
| F | Cambiar el padre de una ubicación con histórico | **Bloqueado** `LOCATION_HAS_HISTORY`; sin histórico, permitido y auditado | T-008-068c | AC-008-36 |
| G | Almacén simple `Warehouse → Location` | **Funciona** completo sin exigir ni mostrar tramos | T-008-068d | AC-008-37 |
| H | Almacén complejo, jerarquía completa | **Funciona** completo, orden determinista | T-008-068d | AC-008-38 |

El caso E se prueba en los **seis** nodos, no solo en la ubicación. Se prueba
además el histórico **heredado**: una zona sin stock propio cuya ubicación tiene
movimientos tampoco se borra.

Adicional, no enumerado en el encargo pero necesario para que los ocho signifiquen
algo: cada bloqueo se invoca **directamente por API**, saltándose el frontend, y
debe rechazarse igual (T-008-068e, AC-008-39).

## 11. Criterio de salida

- Toda la suite verde **sobre PostgreSQL**.
- Los 24 criterios de aceptación cubiertos.
- Concurrencia y migraciones probadas, no razonadas.
- Regresión de los dominios consumidores en verde.
- Búsqueda de nombres de zona o estructura de cliente en el código: 0 coincidencias.
- Los 6 casos de migración del Control 1 y los 8 estructurales del Control 2, verdes.
- Ninguna referencia anulada sin justificación registrada.
- El caso crítico bloquea de verdad, verificado por inspección de la base tras el aborto.
