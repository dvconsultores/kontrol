# INVENTARIO — EVIDENCIA A/B

PostgreSQL 18.6 · **13 pruebas** · Veredicto: **PASS**

## Lo que se esperaba encontrar, y lo que se encontró

Los almacenes de la Spec 008 siempre tuvieron `company_id` con clave foránea
real. Eran la referencia positiva del Gate multiempresa: el único sitio donde la
empresa nunca se perdió.

El dato seguía siendo correcto. **La lectura no.**

`warehouse_api` resolvía el alcance con un ayudante que admitía cualquier
empresa del tenant, así que el almacén de B aparecía en el listado de A y se
dejaba leer y modificar desde ella. El comentario de `_get_warehouse` ya decía
la intención correcta —«un almacén de otra empresa se responde como
inexistente»—; la implementación se había quedado en el mundo de una empresa por
tenant.

Lo destapó la prueba de control, la que existía solo para confirmar que el
fixture funcionaba.

Veintinueve rutas pasan ahora por el contexto validado, y la creación toma la
empresa de ahí en vez del cuerpo.

## Cobertura

| Comprobación | Resultado |
|---|---|
| Almacenes con su empresa y listado acotado | PASS |
| El mismo artículo con existencias distintas en cada empresa | PASS |
| Mover existencias en el almacén ajeno | BLOCKED |
| El movimiento guarda su empresa y su almacén | PASS |
| Leer o revertir un movimiento ajeno | BLOCKED |
| Idempotencia de movimientos entre empresas | BLOCKED |
| Transferencia entre almacenes de A y B | BLOCKED |
| Transferencia entre almacenes de la misma empresa | PASS |
| Inventariar el almacén ajeno | BLOCKED |
| Anotar o transicionar el conteo ajeno | BLOCKED |
| Lotes sin mezcla; cuarentena de un lote ajeno | BLOCKED |
| Capas de costo sin mezcla | PASS |
| Ninguna fila hacia una empresa inexistente (9 tablas) | PASS |

## Existencias del mismo artículo

Es el caso que más se parece a un error de programa sin serlo: el producto puede
repetirse entre empresas, pero las unidades son de quien las compró. Cada
empresa ve su saldo y ninguna ve el de la otra.

## Transferencias entre empresas

Bloqueadas, no implementadas. Mover mercancía de una persona jurídica a otra es
una venta o una cesión, con su documento y su efecto fiscal; un traslado interno
la haría desaparecer de un balance y aparecer en otro sin que nada lo explique.

La transferencia **dentro** de la misma empresa se prueba aparte y funciona. Sin
eso, el bloqueo podría deberse a que nada funciona.

## Costos

Las capas de costo no se mezclan. Mezclarlas falsearía dos márgenes a la vez, y
en direcciones opuestas.
