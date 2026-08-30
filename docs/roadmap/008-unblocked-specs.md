# SPECS DESBLOQUEADAS POR EL CIERRE DE LA SPEC 008

Fecha: 2026-08-30 · Origen: `SPEC 008 COMPLETE_100`

El desbloqueo se declara **por contrato verificado**, no por el roadmap previo.
Cada fila cita el mecanismo concreto que 008 entrega y la prueba que lo respalda.

| Spec | Qué necesitaba de 008 | Contrato entregado | Prueba |
|---|---|---|---|
| **022 · Put-away** | Ubicaciones consultables con estado, tipo, jerarquía, capacidad y restricciones | `GET /organization/locations` con 7 filtros; `capacity_units`, `capacity_weight`, `restrictions`, `location_type_id` | `test_estructura_no_carga_ubicaciones_por_defecto` |
| **031 · Cola y ruta de picking** | Orden físico determinista y estable | `GET /organization/locations/ordered` con `physical_order`; orden total con `NULLS FIRST` y desempate por código | `test_orden_fisico_determinista_y_estable` + E2E |
| **032 · Picking y consolidación** | `location_id` con integridad real y búsqueda eficiente | FK real en las tres tablas; índice compuesto verificado por `EXPLAIN` | `test_las_dos_referencias_son_fk_reales`; P95 0,3 ms sobre 50.000 |
| **023 · Núcleo de inventario (parcial)** | La ubicación como dimensión, no como texto | `inventory_movements`, `inventory_balances` y `stock_count_lines` con FK a `warehouse_locations` | migración `0018` PASS |
| **025 · Transferencias, conteos y ajustes** | `source/destination/count_location` referenciables | `stock_count_lines.location_id` es FK real | ídem |
| **019 · Recepción física** | `destination_location_id` referenciable | Ubicación con identidad y FK | ídem |

## Lo que 008 deliberadamente **no** desbloquea

- **Reestructuración** de un almacén operativo (fusionar zonas, mover racks,
  cambiar profundidad). Fuera de alcance por FR-008-097; requiere su propia Spec.
- **Volumetría y slotting**: no se modelan. Capacidad y restricciones quedan al
  nivel de MVP acordado.
- **Etiquetado e impresión** de códigos de barras: el campo `barcode` existe y
  está reservado; la impresión pertenece a la Spec 025.

## Riesgo cerrado

El GAP Analysis registró `locations` como un maestro que **ninguna transacción
escribía**. Ese riesgo queda cerrado: la ubicación es ahora una dimensión con
integridad referencial impuesta por la base de datos, no una columna de texto
opcional que nadie rellena.
