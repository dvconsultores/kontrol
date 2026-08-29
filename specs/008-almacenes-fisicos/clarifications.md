# CLARIFICACIONES — SPEC 008

Antes de escalar cualquier duda se revisaron D0, los 29 ADR y la baseline. Solo
se elevan decisiones de producto **no resueltas**; lo que es configuración de
cliente se resuelve por parametrización (§68 del encargo).

## Resueltas por la autoridad vigente — no se preguntan

| Pregunta | Ya decidida en | Resolución |
|---|---|---|
| ¿Puede una ubicación existir sin zona? | `ADR-D0-004` (jerarquía con hoja única) | **Sí.** Solo almacén y ubicación son obligatorios |
| ¿Zonas A–E como enum? | `ADR-D0-004` R-D0-04-1 | **No.** Catálogo por empresa |
| ¿La ubicación es obligatoria en todo movimiento? | `ADR-D0-004` R-D0-04-3 | Depende de `location_managed` **por almacén** |
| ¿Estado de ubicación = estado de mercancía? | `ADR-D0-010` R-D0-10-1 | **No**, son dimensiones independientes |
| ¿Qué motor de base de datos gobierna la evidencia? | `ADR-D0-001` · P21 | PostgreSQL |
| ¿Qué dimensiones lleva cada documento? | `ADR-D0-013` | Matriz cerrada; 008 la respeta |
| ¿Aprobación para crear almacenes? | Encargo §31 | No por defecto; si llegara a hacer falta, consume la 045 |
| ¿Concurrencia optimista? | `ADR-013` + 045 | `If-Match`, ya en la plataforma |
| ¿Auditoría propia? | `ADR-012` · P22 | No: `record_audit` común |

## Decisiones tomadas en esta Spec

| ID | Pregunta | Resolución | Fundamento |
|---|---|---|---|
| CL-008-01 | ¿Entidades separadas por tramo o una tabla auto-referenciada? | **Entidades separadas** para zona, pasillo, rack y nivel; `Location` como hoja con FK a cada tramo | Una tabla auto-referenciada obliga a recursión para ordenar físicamente (FR-008-031) y hace imposible un `ORDER BY` determinista en base de datos (NFR-008-03). El coste es cuatro tablas pequeñas; el beneficio, una consulta plana |
| CL-008-02 | ¿La hoja guarda la cadena completa o solo su padre inmediato? | **La cadena completa**, con FK a cada tramo declarado | Permite ordenar y filtrar sin joins recursivos y sobrevive a que un almacén use solo algunos tramos. La coherencia se impone por restricción (R-008-2) |
| CL-008-03 | ¿`ZoneType` es tabla o campo? | **Tabla, catálogo por empresa** | Distingue tipo conceptual de nombre (FR-008-012) y permite que la Spec 022 filtre por función sin conocer los nombres del cliente |
| CL-008-04 | ¿Ubicaciones especiales por tipo o por zona? | **Por `location_type`**, no duplicando el concepto en zona | Una zona de cuarentena puede contener ubicaciones de tipos distintos, y un almacén sin zonas necesita igualmente marcar su ubicación de cuarentena. El tipo va en la hoja, que es lo que la operación referencia |
| CL-008-05 | ¿`FULL` es estado persistente o derivado? | **Derivado** | Persistirlo obliga a mantenerlo sincronizado con el saldo, y el saldo es de la Spec 023. Guardar información derivable es la vía directa a la incoherencia |
| CL-008-06 | ¿Código de ubicación manual o generado? | **Ambos, por política del almacén; generado es el valor por defecto** | Un almacén grande no puede teclear 20.000 códigos; uno pequeño ya tiene los suyos rotulados en la pared |
| CL-008-07 | ¿El código debe revelar la jerarquía? | **No.** El código es identificador; la **etiqueta legible** es derivada y separada | Si el código codifica la jerarquía, mover una ubicación obliga a renumerar y rompe las referencias históricas |
| CL-008-08 | ¿Un endpoint de estructura o consultas separadas? | **Ambos**: `/{id}/structure` con profundidad controlada, y listados por tramo | Con decenas de miles de ubicaciones un árbol completo es inviable; con cinco, cinco llamadas son absurdas. La profundidad se pide, no se impone |
| CL-008-09 | ¿Se puede cambiar el padre de una ubicación con stock? | **No.** Se rechaza y se explica | Cambiarlo altera el significado de los movimientos históricos. Un traslado físico de mercancía es un movimiento de inventario (Spec 023/025), no una edición de metadatos |
| CL-008-10 | ¿Qué pasa con los movimientos si la ubicación cambia de nombre o código? | **La FK se conserva y basta**; ningún snapshot adicional | La FK apunta al identificador, no al código. El nombre es presentación. Si en el futuro se exigiera reconstruir la etiqueta histórica exacta, será un requisito de la Spec 023, no de 008 |
| CL-008-11 | ¿Desactivar un padre desactiva a los hijos? | **No en cascada silenciosa**: se rechaza si hay hijos activos | Una desactivación en cascada oculta trabajo real y es difícil de deshacer. El usuario decide qué desactivar |
| CL-008-12 | ¿Capacidad en el alcance actual? | **MVP**: unidades y peso máximo, opcionales. **Futuro**: volumen, dimensiones, pallets, temperatura | 022 necesita saber si cabe; no necesita un motor volumétrico |
| CL-008-13 | ¿Restricciones en el alcance actual? | **MVP**: producto o categoría permitidos. **Futuro**: peligrosidad, temperatura, compatibilidad | Es lo mínimo para que 022 no proponga un destino inválido |
| CL-008-14 | ¿Se sustituyen las páginas existentes? | **Sí**, `AlmacenesPage` y `UbicacionesPage` se reemplazan | Su modelo actual (zona/pasillo/rack como texto) desaparece; mantenerlas sería conservar el defecto |
| CL-008-15 | ¿Migración de las ubicaciones existentes? | Los textos de `zone`/`aisle`/`rack` se conservan en `legacy_path` y **no se convierten automáticamente** en entidades | Convertir texto libre en jerarquía adivinando es inventar datos. El cliente decide, y mientras tanto no se pierde nada |

## Escaladas — decisiones de producto pendientes

Ninguna bloquea la especificación ni la implementación.

| ID | Pregunta | Clase | Quién responde | ¿Bloquea? |
|---|---|---|---|---|
| OQ-008-01 | ¿La creación masiva por patrón entra en el MVP o en una fase posterior? | Producto | Product Owner | No — está como P1 |
| OQ-008-02 | ¿El código generado debe seguir un formato corporativo concreto? | Configuración | Cada empresa | No — la política es parametrizable |
| OQ-008-03 | ¿Qué tipos de zona y de ubicación se entregan como plantilla opcional de arranque? | Configuración | Implantación | No — el catálogo se crea vacío |

---

# DECISIONES DEL GATE PRE-IMPLEMENTACIÓN (Controles 1 y 2)

Estas decisiones **endurecen** la Spec. Ninguna amplía su alcance funcional.

| ID | Pregunta | Decisión | Autoridad |
|---|---|---|---|
| CL-008-16 | ¿Puede `0018` anular una referencia huérfana para poder terminar? | **No.** Se clasifica en A/B/C/D y la clase decide la acción (R-008-4) | P5, P23, Control 1 |
| CL-008-17 | ¿Qué hace la migración ante una huérfana crítica irrecuperable? | **Aborta de forma controlada** antes de escribir nada (R-008-5) | P5, Control 1 |
| CL-008-18 | ¿Cuándo es admisible reconstruir una referencia? | Solo si es determinista, **unívoca** y demostrable. Dos candidatas degradan la fila; nunca se elige «la más probable» | Control 1 |
| CL-008-19 | ¿Puede `legacy_path` usarse para reconstruir? | **No.** Es texto ambiguo; usarlo sería inventar jerarquía por la puerta de atrás | CL-008-15, Control 1 |
| CL-008-20 | ¿Se pierde el valor original al anular? | **Nunca.** Queda en `legacy_location_id` y en el detalle del reporte | P5, Control 1 |
| CL-008-21 | ¿Es `structure_levels` un campo editable? | **No.** Régimen `INITIAL` libre; `OPERATIONAL` con los tramos utilizados protegidos (R-008-6) | Control 2 |
| CL-008-22 | ¿Qué es «tramo utilizado»? | Aquel con al menos un nodo en el almacén, activo o inactivo. Un tramo declarado sin nodos sí puede retirarse | Control 2 |
| CL-008-23 | ¿Renombrar una zona es un cambio estructural? | **No.** Es metadata. La etiqueta derivada cambia y eso es correcto (AC-008-07) | Control 2 |
| CL-008-24 | ¿Reordenar `sequence` entre hermanos es estructural? | **No.** Altera el recorrido, no la jerarquía | Control 2 |
| CL-008-25 | ¿Puede borrarse un nodo cuyo hijo tiene histórico? | **No.** El histórico se hereda hacia arriba; la vía es desactivar | P5, Control 2 |
| CL-008-26 | ¿Implementa 008 la reestructuración? | **No.** 008 impide el cambio destructivo, conserva el histórico y deja la arquitectura preparada | Control 2 |
| CL-008-27 | ¿Se apoya el bloqueo en deshabilitar controles de la UI? | **No.** El backend es la autoridad; el frontend refleja (P6) | P6, Control 2 |

## Corrección de hecho detectada en este Gate

| Hallazgo | Antes | Verificado |
|---|---|---|
| Columnas `location_id` a convertir | Se documentaban **tres** (`InventoryBalance`, `AdjustmentLine`, `StockCountLine`) | Son **dos**. `inventory_adjustments` no tiene `location_id` y `adjustment_lines` **no existe**. Confirmado contra el esquema real: solo `inventory_movements` (ya FK), `inventory_balances` y `stock_count_lines` tienen la columna |

Corregido en `spec.md`, `research.md`, `plan.md`, `data-model.md`, `tasks.md`,
`checklist.md`, `acceptance-criteria.md`, `risk-register.md` y
`migration-0018-policy.md`.
