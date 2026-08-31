# TESORERÍA — EVIDENCIA A/B

PostgreSQL 18.6 · **15 pruebas** · Veredicto: **PASS**

## Por qué va primera

Es donde confundir la empresa se convierte en dinero mal aplicado. Un pago de A
que cancela una deuda de B no es un listado sucio: es un asiento falso en dos
contabilidades a la vez, y cuadra en ambas.

## Cobertura

| Comprobación | Resultado |
|---|---|
| Cuentas de A y B con su propia empresa, verificado en la base | PASS |
| Listado de cuentas sin intersección | PASS |
| Movimiento bancario sobre una cuenta ajena | BLOCKED (404) |
| El movimiento hereda la empresa de su cuenta | PASS |
| Movimientos sin mezcla entre empresas | PASS |
| Conciliar una cuenta ajena | BLOCKED |
| Leer, anotar o transicionar una conciliación ajena | BLOCKED |
| Operar la sesión de caja ajena: movimiento, arqueo, precierre, cierre, rechazo | BLOCKED |
| Abrir sesión sobre una caja ajena | BLOCKED |
| Transferencia entre cuentas de A y B | BLOCKED |
| Alcance desde el otro tenant | BLOCKED |
| Auditoría con la empresa real y con autor | PASS |
| Ninguna auditoría hacia una empresa inexistente | PASS |

## Transferencias entre empresas

Bloqueadas, no implementadas. Mover dinero entre dos personas jurídicas
distintas es un hecho contable con documentación propia, no un asiento interno.
Se registra como `FUTURE_INTERCOMPANY_CAPABILITY`; no es deuda de N5.

## Defecto encontrado

`arqueo_session` fijaba `actor=None` a mano y **ni siquiera aceptaba el
parámetro**, mientras `close_session` sí lo hacía. Un arqueo de caja con
diferencia quedaba registrado sin autor: el rastro sabía que hubo un descuadre y
no quién lo contó. Corregido pasando el actor desde la ruta.

## Sobre la forma de las pruebas

Los payloads son válidos a propósito. Un 422 por cuerpo mal formado no demuestra
bloqueo: significa que la petición murió en la validación de forma sin llegar a
preguntarse de quién era la caja. La primera versión de dos de estas pruebas
pasaba por ese motivo equivocado.

## Auditoría

Tesorería audita el arqueo, el cierre de caja y la transición de conciliación.
No audita la creación de catálogos, y aquí no se inventa el rastro que el
contrato no pide: se comprueba que el que existe lleva la empresa correcta.
