# SPEC 021 — CONFIRMACIÓN Y CONCILIACIÓN DEL INVENTARIO RECIBIDO · CICLO DE IMPLEMENTACIÓN

> 2026-09-04, sobre `289acee`. Ciclo completo desde `/speckit.specify`. La Spec estaba
> `READY_FOR_IMPLEMENTATION` y eso no autorizaba a empezar por el código.

## 1. Lo que esta Spec cierra, en una frase

**Recibir dejaba de significar tener disponible en el papel, pero no en el sistema.** Hasta este
ciclo, aceptar una recepción escribía el saldo en `DISPONIBLE` y la mercancía quedaba a la venta sin
que nadie la hubiera contado. `R-D0-10-4` lo prohíbe desde el 2026-08-29 y el propio `ADR-D0-010`
reservó el cambio de comportamiento para la Spec 021. Aquí ocurre.

## 2. Las etapas, extraídas de la fuente

`DOCX §3 «Confirmación del inventario recibido»`, párrafos 51 a 77, literales. **Catorce** etapas de
primer nivel, no once: el roadmap las contaba mal, igual que contaba diez las de recepción física
cuando eran doce.

| # | Etapa (literal) | Dueño | Antes | Ahora |
|---:|---|---|---|---|
| 1 | «Realizar conteo detallado por SKU o código» | **021** | ✗ | ✔ `counted_base_quantity` |
| 2 | «Comparar cantidades contra la orden de compra» | **021** | parcial | ✔ `matches_order` |
| 3 | «Comparar contra packing list» | 019 → **021** | ✔ capturado | ✔ transportado en la conciliación |
| 4 | «Comparar contra recepción física» | **021** | ✗ | ✔ `matches_physical` |
| 5 | «Validar descripción, referencia y presentación» | 019 | ✔ | ✔ (sin cambios) |
| 6 | «Identificar diferencias por cantidad, SKU, presentación, referencia, unidad de medida» | **021** | ✗ | ✔ conjunto cerrado de cinco |
| 7 | «Registrar el ingreso de mercancía en el sistema» | 019 | ✔ | ✔ |
| 8 | «Actualizar existencias» | 019 · 023 | ✔ | ✔ |
| 9 | «Diferenciar inventario: recibido; disponible; pendiente de validación; bloqueado por incidencia» | **021** · 023 | capacidad sin uso | ✔ resultado mixto por línea |
| 10 | «Confirmar si existen diferencias» | 020 | ✔ | ✔ |
| 11 | «Si existen diferencias, generar reporte formal» | 020 | ✔ | ✔ |
| 12 | «Determinar tratamiento» (cuatro) | 020 | ✔ | ✔ |
| 13 | «Una vez conciliado, confirmar inventario» | **021** | ✗ | ✔ |
| 14 | «Liberar el lote para almacenamiento» | **021** | ✗ | ✔ |

Nueve etapas eran de la 021 y ninguna estaba implementada salvo fragmentos. Tres son de la 020 y ya
lo estaban: las cuatro resoluciones de `INCIDENT_RESOLUTIONS` son literalmente los párrafos 72 a 75.

## 3. `/speckit.clarify` — lo que se resolvió con evidencia

**¿Existía entidad de confirmación?** No. La `Reconciliation` del repositorio es **bancaria**
(tesorería, Spec 038) y confundirla habría sido mezclar dominios. Lo único que había era la compuerta
`quality_status` y las cantidades aceptada y rechazada de la línea: las «2 de 11» que el roadmap
contaba.

**¿Confirmación por cabecera o por línea?** Por línea, y con varias decisiones por línea. La etapa 9
—«diferenciar inventario»— lo exige: noventa liberadas y diez rechazadas son dos filas, y un solo
campo por línea no podría representarlo. El ciclo de la cabecera es de dos estados y no más.

**¿Resultado mixto permitido?** Sí, y no por conveniencia: la etapa 9 lo nombra. La invariante que lo
acota es que la suma de lo confirmado nunca supere lo recibido en base.

**¿Hace falta `PENDIENTE_CONFIRMACION`?** No, y esto merecía cuidado porque la etapa 9 nombra
«pendiente de validación». El `ADR-D0-010` define `RECIBIDO` como «físicamente recibido, **aún no
conciliado**»: ya es el estado de lo que espera conteo. Abrir una arista
`RECIBIDO → PENDIENTE_CONFIRMACION` habría creado una distinción sin consecuencia operativa —los dos
son no vendibles y los dos salen a `DISPONIBLE` o `RECHAZADO`— y `R-D0-10-7` no admite aristas
decorativas. Si alguna vez hace falta separar «contándose» de «recibido», su dueña la declarará con
su evidencia. **No se activó ninguna arista nueva.**

**¿Una incidencia abierta bloquea?** Sí. La etapa 13 dice «**una vez conciliado**, confirmar
inventario», y la 020 ya expone `ready_for_confirmation`. Confirmar con excepciones vivas sería
confirmar lo que aún se discute.

**¿Qué permiso confirma?** `inventario:confirm`, nuevo. Y aquí apareció un defecto del ciclo
anterior: la matriz de transiciones de `states.py` declaraba `compras:receive`,
`compras:incident`, `inventario:release` e `inventario:transfer`, y **ninguno de los cuatro existe**
en el catálogo de `setup/api.py`. Nada se rompía porque el motor no comprueba permisos —lo hace la
API—, pero eran cuatro contratos que nadie podía cumplir. Se corrigieron a los reales, y un guardia
estructural nuevo comprueba que cada permiso de la matriz exista en el catálogo.

## 4. Constitution Gate — PASS

| Gate | Resultado |
|---|---|
| GATE-021-02 · solo las cuatro transiciones autorizadas | La 021 solo puede pedir `DISPONIBLE` o `RECHAZADO`, y desde `RECIBIDO` o `CUARENTENA` |
| GATE-021-03/04 · sin duplicar el motor | `confirmar_inventario` no contiene `InventoryMovement(`, `InventoryBalance(` ni `qty_on_hand` |
| GATE-021-05 · sin duplicar la 020 | Consume `resultado_de_incidencias`; no resuelve, no escala, no registra |
| GATE-021-06/07 · sin put-away ni ubicación | `location_id=None`; guardia sobre `WarehouseLocation`, `put_away` y `zone_id` |
| GATE-021-08 · sin tocar reservas | Guardia sobre `SalesOrder`, `Reservation`, `reserve(` |
| GATE-021-09 · autoridad de la cantidad base | Guardia: ninguna función usa `quantity_accepted` para calcular |
| GATE-021-12/13 · conservación y paridad | Probadas: el mixto conserva 100; la reconstrucción de la 023 sigue verde |
| GATE-021-14 · sin decisión de transición nueva | Cero aristas añadidas a `ACTIVE_TRANSITIONS` |

## 5. Lo que se construyó

- **`GoodsReceipt.confirmation_status`** — dimensión distinta del `status`. Aceptada no es confirmada,
  y un guardia impide que `accept_receipt` toque el campo o que `confirmar_inventario` toque el
  `status`.
- **`GoodsReceiptLine`**: `counted_base_quantity`, `counted_at`, `counted_by`,
  `count_difference_kinds`.
- **`ReceiptConfirmation`** — una fila por decisión, con estado de origen, de destino, cantidad base,
  el movimiento que la materializó y la incidencia que la sostiene. No copia el asiento: lo referencia.
- **`registrar_conteo`**, **`resultado_de_conciliacion`**, **`confirmar_inventario`**.
- **Migración `0047`**, que además otorga `inventario:confirm` a quien ya podía aprobar inventario:
  un endpoint que nadie puede invocar no está entregado.
- **Frontend**: `/inventario/confirmacion`, con el conteo, la comparación y la decisión por línea. No
  ofrece put-away ni ubicación, y no deja confirmar mientras haya incidencias abiertas.

## 6. Lo que deliberadamente no se hizo

- **No se implementó nada de la 022.** Ni ubicación, ni zona, ni tarea de colocación. Tras confirmar,
  el almacén se conoce y la ubicación sigue nula: eso es lo correcto hasta que la 022 exista.
- **No se resolvió ninguna incidencia.** La 021 lee el resultado estructurado de la 020 y se detiene
  si algo sigue abierto.
- **No se creó un segundo veredicto de calidad.** `quality_status` sigue siendo el único.
- **No se recalculó ningún factor de conversión.** `P23`: cambiar el maestro no puede reinterpretar
  una recepción histórica, y un guardia comprueba que la confirmación no importe `uom_engine`.
- **No se reinterpretó el histórico.** Las recepciones ya aceptadas quedan `CONFIRMADA` porque su
  mercancía **ya está** en `DISPONIBLE` bajo la regla que regía entonces. Dejarlas pendientes
  afirmaría que hay stock a la venta sin confirmar, que es justo lo que esta Spec impide.
