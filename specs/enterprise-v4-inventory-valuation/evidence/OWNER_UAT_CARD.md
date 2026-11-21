# Tarjeta de prueba de la dueña · V4 Transferencias con valor y reversión

**Qué demuestra:** una mercancía se transfiere entre almacenes sin perder cantidad ni valor, se puede recibir
por partes y se puede revertir devolviendo todo a su sitio. **Duración:** unos 10 minutos.

## Antes de empezar

- Usuario con permisos de inventario (crear, transicionar y aprobar).
- Dos almacenes de la misma empresa: **A** (origen) y **B** (destino).
- Un producto con existencia valorada en **A**, por ejemplo 10 unidades a 10,00 (valor 100,00). Si no lo tiene,
  regístrelo en **Inventario → Movimientos** con tipo «Entrada por recepción», cantidad 10 y costo 10.

## Recorrido

| Paso | Dónde | Qué hacer | Qué debe ver |
|---|---|---|---|
| 1 | Inventario → Valorización | Anote el valor del producto en A y el total | A = 100,00; total = 100,00 |
| 2 | Inventario → Transferencias | «Nueva transferencia»: código, almacén origen A, destino B, el producto y cantidad 4; **Crear** | La fila muestra A y B por su nombre y el estado «Borrador» |
| 3 | La misma fila | **Enviar a aprobación**, **Aprobar**, **Confirmar envío** | Estado «En tránsito»; **Valor enviado 40,00** y **En tránsito 40,00** |
| 4 | Inventario → Valorización | Mire A | A = 60,00 (el valor en tránsito está en la transferencia) |
| 5 | Transferencias → «Registrar recepción» | Elija la transferencia; en «Recibir ahora» escriba **3**; **Registrar recepción** | Estado «Recibida parcialmente»; En tránsito 10,00 |
| 6 | La misma sección | Elija otra vez la transferencia; el campo propone **1**; **Registrar recepción** | Estado «Recibida»; En tránsito 0,00 |
| 7 | Inventario → Valorización | Mire A, B y el total | A = 60,00; B = 40,00; **total = 100,00** |
| 8 | Inventario → Movimientos | Busque el producto | Salida de A y entradas en B con el mismo documento; nombres, no códigos internos |
| 9 | Transferencias → «Revertir transferencia» | Elija la transferencia y pulse **Revertir** sin motivo | Aviso «Falta el motivo»; no se revierte |
| 10 | La misma sección | Escriba un motivo («Destino equivocado») y **Revertir** | Estado «Revertida»; la transferencia ya no aparece para revertir |
| 11 | Inventario → Valorización | Mire A, B y el total | A = 100,00; B = 0,00; total = 100,00 |

## Comprobaciones extra (opcionales)

- **Ajustes:** cree un ajuste de +2 del producto, envíelo y apruébelo; debe aparecer **Aplicar**; al aplicarlo la
  existencia sube a 12 y el valor sube al costo vigente (12 × 10,00 = 120,00).
- **Conteos:** cree un conteo, **Congelar**, **Iniciar conteo**, agregue una línea dejando «Esperado» vacío (lo
  calcula el sistema) y **Enviar**.
- **Móvil:** repita los pasos 2 a 6 en un teléfono: la tabla no debe desplazarse a lo ancho.

## Resultado

Marque **ACEPTADO** solo si todos los pasos muestran lo indicado. `OWNER_ACCEPTED` lo concede únicamente la dueña.
