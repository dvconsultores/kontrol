# SPEC 032 · CONTRATO DE ENTRADA TRAS LA SPEC 031

> Documenta qué recibe la Spec 032 y bajo qué condiciones. **No la implementa.**

## Lo que la Spec 032 puede consumir

Un plan de picking en estado `CONFIRMED` **que siga siendo válido al traspaso**
(`R-D0-15-17`). Nunca `DRAFT`, `CANCELLED`, `INVALIDATED` ni `CLOSED`.

`CONFIRMED` garantiza, y la Spec 031 lo comprueba antes de escribirlo:

- el 100 % de la cantidad base reservada está asignado, por línea de pedido;
- cada asignación apunta a una ubicación activa del almacén del pedido, con
  existencia vendible suficiente en el momento de confirmar;
- el recorrido está numerado según el orden físico de la Spec 008;
- el pedido está en `PREPARING`.

## Lo que la Spec 032 debe revalidar

Confirmar no congela la existencia física: entre el traspaso y la recogida la
mercancía puede moverse. La 032 revalida antes de su primer efecto físico.

## La frontera que la 031 dejó abierta a propósito

`CONFIRMED` puede cancelarse **solo antes del primer efecto físico irreversible**
(`R-D0-15-16`). Ese evento no existe todavía: mientras la 032 no lo defina, la
031 trata todo `CONFIRMED` como no ejecutado, y por eso permite cancelarlo.

Cuando la 032 introduzca ese momento deberá:

1. declarar cuál es el evento exacto que lo marca;
2. impedir la cancelación del plan a partir de él;
3. escribir `CLOSED` cuando la ejecución termine —la 031 no lo escribe nunca,
   porque `CONFIRMED` significa «terminó de planificar» y `CLOSED`, «terminó de
   ejecutarse».

## Lo que la Spec 032 no hereda

- **Selección de lote o serial.** La 031 preserva las dimensiones que la
  existencia ya tiene, y no elige entre varias (`R-D0-15-21`). Si la 032
  necesita elegir sin contrato que lo gobierne, es una parada material.
- **Liberación de la reserva comercial.** Es de la Spec 030.
- **Prioridad de cola.** Es temporal y de la 031; cliente, manual, SLA y ruta
  siguen `FUTURE` por `D0-03` §8.

## Estado

`SPEC 032 — BLOCKED UNTIL SPEC031 CONVERGES`. Este documento fija su entrada; no
adelanta ninguna de sus decisiones.
