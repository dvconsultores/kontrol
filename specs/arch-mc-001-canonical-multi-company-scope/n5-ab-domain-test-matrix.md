# MATRIZ A/B POR DOMINIO — N5

Cada fila exige las ocho comprobaciones. Ninguna sustituye a otra: un listado
limpio no dice nada del `UPDATE`, y una base correcta no dice nada de la API.

Verificado sobre **PostgreSQL 18.6** en UTC, con dos empresas del mismo tenant.

| Dominio | Crear A/B | Listar | Detalle cruzado | Modificar cruzado | Relación cruzada | Base | Evento | Auditoría | Veredicto |
|---|---|---|---|---|---|---|---|---|---|
| **Tesorería** | PASS | PASS | PASS | PASS | BLOCKED | PASS | n/a | PASS | **PASS** |
| **Compras / CxP** | PASS | PASS | PASS | PASS | BLOCKED | PASS | n/a | PASS | **PASS** |
| **Ventas / CxC** | PASS | PASS | PASS | PASS | BLOCKED | PASS | n/a | PASS | **PASS** |
| **Inventario** | PASS | PASS | PASS | PASS | BLOCKED | PASS | n/a | PASS | **PASS** |
| **Regulatorio** | PASS | PASS | PASS | PASS | BLOCKED | PASS | n/a | PASS | **PASS** |
| **Fiscal P0** | PASS | PASS | PASS | PASS | BLOCKED | PASS | n/a | PASS | **PASS** |
| **Auditoría / eventos** | PASS | PASS | PASS | PASS | — | PASS | n/a | PASS | **PASS** |
| **Aprobaciones (045)** | PASS | PASS | PASS | PASS | BLOCKED | PASS | n/a | PASS | **PASS** |
| **Documental (046)** | PASS | PASS | PASS | PASS | BLOCKED | PASS | n/a | PASS | **PASS** |

## Sobre la columna «Evento»

Dice `n/a` y conviene ser explícito sobre por qué. `outbox_events` está
declarada y migrada, pero **ningún módulo escribe en ella**: no existe una sola
construcción de `OutboxEvent` fuera de su propio modelo.

No se inventa aquí el mecanismo que le falta —eso es una Spec futura, no deuda
de N5—. Lo que sí queda escrito es la regla que tendrá que cumplir cuando
exista, en una prueba que hoy pasa porque la tabla está vacía y que estará
esperando al primer productor que alguien añada.

El rastro que sí existe es la auditoría de negocio, y esa se verifica fila por
fila contra PostgreSQL.

## Bloqueos entre empresas comprobados

| Operación | Resultado |
|---|---|
| Transferencia de dinero entre cuentas de A y B | **BLOCKED** |
| Transferencia de existencias entre almacenes de A y B | **BLOCKED** |
| Pago de B aplicado a una deuda de A | **BLOCKED** |
| Cobro de B aplicado a una cuenta por cobrar de A | **BLOCKED** |
| Orden de compra de A recibida en el almacén de B | **BLOCKED** |
| Venta de A despachada desde el almacén de B | **BLOCKED** |
| Emisión fiscal de A con la serie o el rango de B | **BLOCKED** |
| Permiso de A amparando un vehículo de B | **BLOCKED** |
| Documento de B leído o descargado desde A | **BLOCKED** |
| Política de aprobación escrita en B desde A | **BLOCKED** |

Cada bloqueo va acompañado de su prueba positiva. Sin ella, un sistema
completamente roto pasaría la mitad de esta tabla.

## Recuento

| Suite | Pruebas |
|---|---:|
| Aislamiento base | 11 |
| Tesorería | 13 |
| Compras / CxP | 14 |
| Ventas / CxC | 17 |
| Inventario | 13 |
| Regulatorio | 10 |
| Fiscal P0 | 13 |
| Auditoría y eventos | 8 |
| Seguridad 045 / 046 | 13 |
| **Total** | **112** |

Las once del aislamiento base eran trece: dos **fijaban** las vulnerabilidades de
045 y 046 mientras esperaban corrección, y decían en su propio texto que
fallarían el día que se cerraran. Ese día llegó en esta fase. Las sustituye la
suite de seguridad, con aserciones más estrictas —descarga, previsualización,
versiones, cruce entre tenants y la escritura legítima que debe seguir
funcionando—, así que mantener aquí una versión más débil solo añadiría ruido.
