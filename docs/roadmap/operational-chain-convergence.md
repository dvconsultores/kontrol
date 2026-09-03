# CADENA OPERATIVA — CONVERGENCIA DEL CHECKPOINT

## Puerta

| Criterio | Exigido | Resultado |
|---|---|---|
| Specs auditadas | 6/6 | 6/6 — 019, 020, 021, 022, 031, 032 |
| Capacidades de proveedores medidas | sí | 9 proveedores: 008, 010, 011, 023, 024, 029, 030, 045, 046 |
| Estados desconocidos | 0 | 0 |
| Dependencias desconocidas | 0 | 0 |
| Bloqueos desconocidos | 0 | 0 |
| Dependencias sin respaldo | 0 | 0 — cada arista cita código o requisito |
| Dependencias circulares | 0 | 0 |
| Spec siguiente | exactamente 1 | `019 — Recepción física` |
| Cambios de código productivo | 0 | 0 |
| Trazabilidad | 100 % | 100 % (20 requisitos, 38 tareas, 6 Specs, 9 proveedores) |
| Constitution Gate | PASS | PASS |
| BLOCKER · CRITICAL · CONTRADICTIONS | 0 · 0 · 0 | 0 · 0 · 0 |

## Lo que cambió de verdad

Antes, la cadena de entrada se describía con una fila lineal de bloqueos heredados: 022 esperaba
ubicaciones que la Spec 008 ya había entregado, 031 y 032 esperaban a la 030 que acababa de cerrar,
y 021 esperaba a que la 020 «estuviera hecha» sin que nadie hubiera preguntado si una recepción sin
incidencias necesita registrar alguna.

Ahora cada arista dice qué capacidad exacta falta y quién la debe. Dos bloqueos se retiran porque
eran ciertos y dejaron de serlo. Dos se reformulan porque nombraban una Spec donde debían nombrar
una capacidad. Y dos aparecen, que nadie había escrito: **el motor de saldos solo sabe escribir
`DISPONIBLE`**, lo que impide a 021 confirmar mercancía a un estado no vendible; y **la línea de
recepción no captura presentación ni unidad**, con las columnas de la Spec 011 esperando desde hace
dos Specs a que alguien las escriba.

También queda escrito un invariante que hasta hoy solo existía como comportamiento: entre recibir y
ubicar, la existencia vive con almacén conocido y ubicación nula. No es un defecto de la recepción.
Recibir no es ubicar.

## Sobre la contradicción que no lo es

La mercancía se vuelve vendible al aceptar la recepción, y el contrato de `ADR-D0-010` dice que ese
paso exige liberación formal en la Spec 021. Parece una contradicción y no lo es: el propio ADR la
anticipó y le puso dueño y momento —«el cambio de comportamiento llega con la Spec 021, no con esta
decisión»—. Es un hueco conocido, atribuido y programado, y por eso este checkpoint cierra con cero
contradicciones y con un bloqueo nombrado en 021.

La Spec 030 no se toca: sigue reservando sobre saldo `DISPONIBLE`. Lo que cambiará cuando llegue 021
no es la regla de reserva, sino el conjunto de lo reservable.

## Veredicto

`OPERATIONAL CHAIN — DEPENDENCY MAP CONVERGED / NEXT SPEC SELECTED`

`NEXT SPEC = 019 — RECEPCIÓN FÍSICA`

`IMPLEMENTATION NOT STARTED`
