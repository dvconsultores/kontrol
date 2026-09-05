# SPEC 032 — PREPARACIÓN FÍSICA Y CONSOLIDACIÓN · CICLO DE IMPLEMENTACIÓN

> 2026-09-05, sobre `307f303`. Ciclo completo desde `/speckit.specify`.
> **`MATERIAL OQ = 0`**: las seis preguntas que el ciclo señalaba como material tenían autoridad,
> aunque repartida entre cinco documentos.

## 1. La fuente, leída entera

`requerimientos/Pedido - Organizar Pedido - Confirmar - Facturar - Despachar.docx`, Procesos 4 y 5.

**Proceso 4 · Preparación física del pedido**

| ¶ | Texto |
|---|---|
| 33 | El almacenista llega a la ubicación indicada. |
| 34-36 | Identifica el producto · Verifica referencia/SKU · Verifica cantidad requerida. |
| 37 | **Extrae la mercancía.** |
| 38 | Coloca la mercancía correspondiente al pedido. |
| 39 | Registra o marca la línea como preparada. |
| 40-41 | Continúa con la siguiente ubicación · Finaliza cuando se han recorrido todas las posiciones. |

**Punto de decisión — la discrepancia, literal**

| ¶ | Texto |
|---|---|
| 43 | ¿Se encontró toda la mercancía solicitada? |
| 44-45 | **Sí** → El pedido continúa al área de confirmación. |
| 46-47 | **No** → **Debe registrarse la diferencia:** |
| 48-52 | producto no localizado · cantidad física insuficiente · ubicación incorrecta · diferencia entre sistema y existencia física · mercancía dañada/no apta |
| 53 | «El pedido **no debería simplemente modificarse sin dejar evidencia de la diferencia**.» |

**Proceso 5 · Consolidación del pedido**

| ¶ | Texto |
|---|---|
| 55 | Los productos extraídos se concentran como un único pedido. |
| 56 | Se identifica físicamente el pedido. |
| 57 | Se separa de otros pedidos en preparación. |
| 58 | Se traslada al **Área de Confirmación de Pedido**. |
| 59 | Salida: **Pedido preparado pendiente de control**. |

El ¶59 fija dónde termina esta Spec. El ¶61 —«constituye un control **independiente** después del
picking»— fija que lo siguiente es de la 033.

**Los cinco motivos de diferencia no se inventan: están en el ¶48-52.**

## 2. La pregunta que parecía material y no lo era

El caso canónico: existencia 100, reservado 30, disponible 70. Se recogen las 30. ¿Qué queda?

Si la mercancía sale de `DISPONIBLE` hacia `PICKING` y el contador `qty_reserved` se queda en 30, el
disponible pasa a ser `70 − 30 = 40`: el mismo compromiso restado dos veces, y ventas dejaría de
poder vender 30 unidades que sí tiene. Ese es el riesgo real.

**Lo resuelve el vocabulario que `D0-03` fijó**, y que no estaba en la política de reservas sino en
el checkpoint:

| Término | Definición (`d0-03-reservation-decision.md` §0) |
|---|---|
| Stock reservado | «Unidades base comprometidas a líneas de pedido emitidas **y aún no extraídas**. Es un **contador** sobre `DISPONIBLE`, no un estado de custodia» |
| Stock en preparación | «Unidades cuyo estado de custodia pasó a `PICKING`/`PREPARADO` por 031/032. **Fuera de 030**» |
| Stock disponible | «`on_hand − reserved` de la fila en estado `DISPONIBLE`… porque los estados no vendibles **viven en otras filas**» |

Extraer **es** dejar de estar «aún no extraída». Las dos categorías son excluyentes por definición:
el contador vive sobre `DISPONIBLE`; lo recogido vive en otra fila. El caso canónico se resuelve solo:

| | `on_hand` `DISPONIBLE` | `qty_reserved` | disponible | `on_hand` `PICKING` | físico total |
|---|---:|---:|---:|---:|---:|
| Antes | 100 | 30 | 70 | 0 | 100 |
| Tras recoger 30 | 70 | **0** | **70** | 30 | **100** |

La `Reservation` **no se toca**: sigue `ACTIVE` hasta el despacho, que la consume → `FULFILLED`
(`POL-D0-002` §8, `FR-030-054`). Lo que baja es el **contador**, que es otra cosa y lo dice el
vocabulario. Y el físico total no cambia: nada ha salido del almacén todavía.

## 3. Lo que decide cada autoridad

| Pregunta | Autoridad | Respuesta |
|---|---|---|
| ¿Cambia el estado de mercancía? | `d0-10-merchandise-state-transition-matrix.md:60`: «`DISPONIBLE` \| `PICKING` → `PREPARADO` \| 031, 032 \| Specs no construidas» | Sí. Este ciclo activa las dos aristas; `R-D0-10-7` las tenía denegadas por no construidas |
| ¿Baja el físico del almacén? | `confirm_shipment` registra `SALIDA_DESPACHO`; `POL-D0-002` §8 «Despacho (salida física) → consume» | **No.** La salida es del despacho (035). El picking mueve dentro del almacén |
| ¿Qué pasa con la reserva? | `POL-D0-002` §8, tabla **cerrada** | Nada en el picking completo. En el parcial: «libera la diferencia y **genera incidencia**; nunca ajusta el pedido en silencio» |
| ¿Se puede copiar ese precedente? | `d0-10-reserved-stock-conflict-analysis.md`: «allí el que libera es el proceso de preparación, **dueño del pedido en ese momento**, y lo hace con incidencia» | Sí, aquí sí: el que libera **es** la preparación |
| ¿Y `R-D0-10-10`? | Exige elegir en el ciclo que active la primera salida de `DISPONIBLE` | Sus dos opciones —bloquear todo, o reclasificar solo lo no reservado— gobiernan la reclasificación **por un tercero** (calidad). Aquí quien extrae es el dueño de la reserva, y el análisis de `D0-10` distingue expresamente los dos casos |
| ¿Se puede replanificar tras una diferencia? | Ninguna autoridad lo permite; `POL-D0-002` §8 sí manda liberar la diferencia con incidencia | **No.** No se busca otra ubicación ni se reasigna |
| ¿Qué es consolidar? | DOCX ¶55-58 | Concentrar como un único pedido, identificarlo, separarlo y trasladarlo al Área de Confirmación |
| ¿Y una diferencia al consolidar? | DOCX ¶61: el control independiente es el Proceso 6 | Es de la 033. La 032 consolida lo recogido; no se autocertifica |
| ¿Sobre-recoger? | Sin autoridad; `R-D0-10-7` deny-by-default | **Bloqueado** |
| ¿Sustituir producto o lote? | `R-D0-15-21`; DOCX ¶72-73 del ciclo | **Prohibido**, nunca en silencio |

## 4. Lo que existe y no hay que construir

| Capacidad | Dueña | Estado |
|---|---|---|
| Plan `CONFIRMED` con asignaciones por ubicación y recorrido | Spec 031 | completa |
| Motor de movimientos con procedencia de estado y ubicación | Spec 023 | completo (`0046`, `0048`) |
| Reclasificación de estado con matriz y permisos | Spec 023 | `reclassify`, `assert_transition` |
| Traslado entre ubicaciones sin tocar la reserva | Spec 022 | `putaway` |
| Consumo de la reserva al despachar | Spec 030/005 | `confirm_shipment` → `fulfill_reservation` |
| Ubicaciones y tipos de zona | Spec 008 | `WarehouseLocation`, `ZoneType` |
| Área de Confirmación | Spec 008 | **es una ubicación**; se elige, no se inventa una entidad |

## 5. Deltas dirigidos que este ciclo necesita

| Delta | Dueño | Por qué |
|---|---|---|
| **A** · activar `DISPONIBLE → PICKING` y `PICKING → PREPARADO` en `ACTIVE_TRANSITIONS` | Spec 023 / `D0-10` | La matriz las declaró para 031/032 y las dejó denegadas «Specs no construidas». Este es el ciclo que las construye |
| **B** · el contador `qty_reserved` baja al extraer, y el despacho no vuelve a restar lo ya extraído | Spec 030 | El contador significa «comprometidas y aún no extraídas». Sin B, dos pedidos sobre el mismo producto se pisarían el contador al despachar el primero |

No se declara la Spec 030 ni la 023 reabiertas: son dos deltas con trazabilidad y convergencia
dirigidas, como los de la Spec 031.

## 6. Fuera de alcance

Confirmación independiente (033) · facturación (034) · despacho, transporte y permisos (035) ·
segunda verificación dentro de la 032 · FIFO/FEFO · sustitución de producto · replanificación.
