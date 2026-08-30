# SPECS DESBLOQUEADAS POR EL CIERRE DE LA SPEC 011

Fecha: 2026-08-30 · Origen: `SPEC 011 COMPLETE_100`

El desbloqueo se declara **por contrato verificado en código**, no por el
roadmap previo, y se distingue el grado: satisfacer la dependencia de unidad no
significa que la Spec quede lista.

| Spec | Estado | Contrato entregado por 011 | Qué sigue bloqueando |
|---|---|---|---|
| **015 · Requisiciones** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | `purchase_requisition_lines` con unidad, presentación, factor y cantidad base | Su propio flujo de aprobación y ciclo |
| **016 · RFQ y ofertas** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | `supplier_quote_lines` con semántica completa | Proceso de comparación de ofertas |
| **017 · Orden de compra** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Dos cantidades con su base; congelado al aprobar | Flujo de emisión y seguimiento |
| **019 · Recepción física** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Tres cantidades con base; comparación contra la orden en unidad base | Proceso de recepción e incidencias |
| **021 · Confirmación de inventario** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | `base_quantity` como magnitud de confirmación | Su propio ciclo |
| **023 · Inventario / Kardex** | **`PARTIALLY_UNLOCKED`** | `record_movement` ya convierte, congela y bloquea la unidad base | El ledger completo y la reconstrucción de saldos son suyos |
| **025 · Transferencias, conteos y ajustes** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Las tres tablas con unidad y base | Sus procesos |
| **026 · Costos** | **`PARTIALLY_UNLOCKED`** | Costeo FIFO y promedio ya operan íntegramente en `Decimal` sobre cantidad base | Política de costeo y capas avanzadas |
| **027 · Factura de proveedor** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Snapshot congelado al contabilizar; reimpresión sin consultar el maestro | Conciliación y flujo fiscal |
| **029 · Pedido comercial** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Presentación comercial conservada | Flujo de pedido |
| **031 · Cola y ruta de picking** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Cantidad pedida con su presentación; orden físico desde la Spec 008 | Algoritmo de ruta |
| **032 · Picking** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | `pick_list_lines` con unidad y base | Proceso de recolección |
| **034 · Facturación** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Símbolo y etiqueta congelados para reimpresión fiel | Motor fiscal completo |
| **035 · Despacho** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | `dispatchable` separa empaque de presentación comercial | Empaquetado físico |
| **036 · Devoluciones** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | Devolución hereda unidad y presentación del original | Su propio flujo |
| **043 · Regulatorio** | **`PARTIALLY_UNLOCKED`** | `permit_instances.uom_id` disponible | Matrices oficiales por rubro |

**Ninguna Spec queda `FULLY_UNLOCKED`.** 011 elimina una dependencia común; cada
Spec conserva las suyas.

## El riesgo que 011 cierra

`ADR-D0-009` lo llamó «la deuda que más rápido se encarece»: cada línea escrita
sin unidad era una línea que **nunca podría interpretarse con certeza**, porque
el dato no se perdía — nunca se capturaba.

Desde este cierre, las 17 líneas transaccionales del sistema capturan unidad,
presentación, factor congelado y cantidad base en el momento de escribir. La
hemorragia está detenida.

## Lo que 011 deliberadamente no desbloquea

- **Precios por presentación**: la línea conserva qué unidad sustentó el precio;
  la política es de la Spec 012.
- **Peso variable** y **alias de unidad**: `FUTURE_CAPABILITY`; el modelo no los
  bloquea, tampoco los construye.
- **Interpretación del `content` legado**: se conserva como evidencia; convertirlo
  en factor exigiría una decisión del cliente, no de una migración.
