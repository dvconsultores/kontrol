# Recepción · modelo de proceso final

Estados y operaciones reales del árbol local.

| # | Pregunta | Respuesta | Autoridad |
|---|---|---|---|
| 1 | ¿Qué orden es recibible? | `APPROVED`, `PARTIALLY_RECEIVED`, `RECEIVED`. Las demás responden 409 `ORDER_NOT_RECEIVABLE` | `RECEIVABLE_ORDER_STATUSES` |
| 2 | ¿Quién selecciona el almacén? | Quien crea la recepción, entre los activos de la empresa | `RECEIPT_WAREHOUSE_ALLOWED_STATUSES` |
| 3 | ¿Qué ocurre al arribo? | Se registra momento y responsable; no mueve inventario | `confirmar_arribo` |
| 4 | ¿Qué se inspecciona? | Cuatro comparaciones, cada una coincide, no coincide o no comparado; bultos contados y observaciones | `registrar_inspeccion` |
| 5 | ¿Qué línea se recibe? | Una línea de la orden de la recepción | `add_receipt_line` |
| 6 | ¿Qué producto corresponde? | El de esa línea. Se deriva y se exige al guardar y al aceptar | `RECEIPT_LINE_PRODUCT_MISMATCH`, `RECEIPT_LINE_INTEGRITY` |
| 7 | ¿Cómo se captura la presentación? | Entre las del producto derivado, o unidad base | `to_base` |
| 8 | ¿Cómo se declara el daño? | Estado físico, cantidad dañada y detalle; sin valor por omisión | FR-019-007 |
| 9 | ¿Identificación y referencia? | Correcta, incorrecta o no observada | FR-019-007 |
| 10 | ¿Cómo se registra el exceso? | Se calcula `overage_base_quantity`; no se impide | FR-019-012 |
| 11 | ¿Cuándo puede aceptarse? | `CONFIRMED`, calidad `APPROVED`, al menos una línea, almacén activo y todas las líneas íntegras | `accept_receipt` |
| 12 | ¿Cuándo entra inventario? | Al aceptar, en estado `RECIBIDO`, en unidad base y al costo de la línea | `accept_receipt` |
| 13 | ¿Cuándo pasa a confirmación? | Con la recepción `ACCEPTED`, en Inventario → Confirmación (Spec 021) | `ConfirmacionPage` |
| 14 | ¿Qué deriva a la Spec 020? | Faltante, sobrante, daño, referencia incorrecta y diferencia documental, abiertos a mano en Compras → Incidencias | Spec 020 |

## Máquina de estados real

`DRAFT → CONFIRMED → ACCEPTED → CLOSED`, y `CONFIRMED → REJECTED → CLOSED`.

Declarados en la máquina y **hoy no alcanzables**, sin operación que lleve a ellos: `QUALITY_PENDING`, `PARTIALLY_ACCEPTED`, `CANCELLED`. `CLOSED` tampoco tiene operación. Una aceptación con cantidades parciales queda `ACCEPTED`, con sus cantidades por línea.

`accept_receipt` no exige arribo ni inspección previos: no hay requisito que lo pida.

## Observación e incidencia

`OBSERVATION_TO_INCIDENT_CONTRACT = MANUAL_SEPARATE`. El hecho observado vive en la línea y sobrevive solo (FR-019-011). La incidencia lo referencia y se abre aparte (FR-020-005). Una observación negativa no crea incidencia ni bloquea aceptar, porque ningún requisito lo pide.

## Contratos de observación

`IDENTIFICATION_OBSERVATION_CONTRACT` y `REFERENCE_OBSERVATION_CONTRACT`: `true` correcta, `false` incorrecta, `null` no observada. La columna admite nulo, la API lo tiene por defecto, y las filas anteriores a la Spec 019 lo conservan; convertirlo en booleano inventaría una observación que nadie hizo.

## Estado del almacén

`RECEIPT_WAREHOUSE_ALLOWED_STATUSES = ACTIVE`. `MATERIAL_OWNER_DECISION_REQUIRED = 0`.

- Un almacén solo alcanza `ACTIVE` e `INACTIVE` por la API; `BLOCKED` y `MAINTENANCE` son estados válidos de nodo (FR-008-040) y quedan rechazados igual.
- La operación hermana ya decide lo mismo: lo que no está activo no recibe mercancía (`LOCATION_NOT_ELIGIBLE`), y se revalida al enviar, no solo al listar.
- Los almacenes son maestros con ciclo de activación (FR-003-004), y la desactivación es reversible (FR-008-006). Ninguna fuente describe un caso legítimo de entrada en uno inactivo.
- Se revalida al crear y al aceptar. Si un almacén se desactiva con una recepción en curso, la aceptación se rechaza hasta reactivarlo.

## Orden en estado RECEIVED

`create_receipt` la admitía, `allowed_actions.receive` no, y ambas vienen del mismo commit. Se conserva el comportamiento efectivo: un sobrante que llega tarde se registra, no se impide (FR-019-012). `allowed_actions.receive` no tenía consumidores. Ahora hay una sola autoridad.
