# MUTATIONS · V4

Cada mutante altera el producto en un punto, corre `tests/test_v4_inventory_valuation.py` más
`test_importaciones_landed_cost.py::test_v4_transferencia_conserva_el_landed_cost_aplicado` sobre PostgreSQL 16.2
y restaura el fichero (comprobado con `cmp` contra la copia previa). Un mutante **muere** si alguna prueba falla.

Corrida final sobre el árbol integrado (`f6bce8e1`, tras fusionar TRE-05/BUD-02 de P1):

| Mutante | Resultado | Salida |
|---|---|---|
| M1 el destino recibe cantidad sin valor | MUERE | 1 failed in 16.05s |
| M2 el valor total de la empresa cambia en la transferencia | MUERE | 1 failed in 16.09s |
| M3 costo sustituido (no el de las capas consumidas) | MUERE | 1 failed in 16.21s |
| M4 se pierde el landed cost | MUERE | 1 failed, 2 passed in 16.15s |
| M5 la reversión vuelve a consumir capas | MUERE | 1 failed, 4 passed in 16.65s |
| M6 doble reversión permitida | MUERE | 1 failed, 7 passed in 16.67s |
| M7 recálculo sin permiso explícito | MUERE | 1 failed, 12 passed in 17.34s |
| M8 movimiento entre empresas | MUERE | 1 failed, 14 passed in 17.43s |
| M9 la concurrencia deja sacar dos veces | MUERE | 1 failed, 17 passed in 17.73s |
| M10 el ajuste cambia de estado sin efecto completo en el ledger | MUERE | 1 failed, 9 passed in 17.01s |
| M10b el ajuste aprobado no ofrece aplicar | MUERE | 1 failed, 9 passed in 17.15s |
| M11 valor separado de la cantidad (capa en otro almacén) | MUERE | 1 failed in 16.24s |
| M12 se omite la auditoría de la transferencia | MUERE | 1 failed, 19 passed in 17.89s |
| M13 conteo atascado en FROZEN | MUERE | 1 failed, 11 passed in 17.09s |
| M14 recepción parcial ignorada | MUERE | 1 failed, 3 passed in 16.28s |
| M15 recálculo reserva lo ya extraído | MUERE | 1 failed, 13 passed in 18.53s |

**Resultado: 16/16 mueren** (M1–M15 más M10b).

M11 del encargo («lote/valor separados») no es aplicable tal cual: el ledger no guarda lote (D-INV-LEDGER-LOT,
diferido). Se sustituyó por la separación equivalente que sí existe —el valor restaurado en otro almacén que la
cantidad— y muere.

Historia: en la primera corrida **M6 sobrevivió**. La prueba de doble reversión aceptaba cualquier
`ConflictError` y el segundo reverso chocaba igualmente con la regla de capa consumida. Clasificado como
TEST_DEFECT propio: la prueba ahora exige `ALREADY_REVERSED` también para una salida y comprueba que el valor no
cambia. Desde entonces M6 muere.
