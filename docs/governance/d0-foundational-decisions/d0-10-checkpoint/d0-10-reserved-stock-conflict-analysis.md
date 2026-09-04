# D0-10 · CONFLICTO ENTRE RECLASIFICACIÓN Y STOCK RESERVADO

> Responde `OQ-D010-02`. Analiza el caso canónico, elimina dos opciones **por autoridad**, y
> concluye que la elección restante no hay que hacerla todavía —y por qué eso no es aplazar el
> problema, sino situarlo donde su dueño puede resolverlo.

## El caso canónico

Fila `DISPONIBLE`: `qty_on_hand = 100`, `qty_reserved = 30`. Un proceso pide reclasificar **80** a un
estado no vendible. Ejecutado a ciegas:

`qty_on_hand = 20` · `qty_reserved = 30` · `disponible = −10`

Un disponible negativo que **no** procede de `allow_negative`.

## La invariante, que sí se cierra

> **R-D0-10-9 (propuesta).** Ninguna reclasificación puede dejar `qty_reserved > qty_on_hand` en el
> saldo origen. `allow_negative` es la política de sobreventa de un almacén (`POL-D0-002` §6) y **no
> es la vía para admitir este resultado**: son problemas distintos y confundirlos convertiría una
> decisión de calidad en una autorización comercial que nadie dio.

Esta invariante no requiere decisión nueva: se deduce de `POL-D0-002` §6, que prohíbe la sobreventa
salvo por política explícita de almacén.

## Dos opciones quedan eliminadas por autoridad, no por preferencia

### Opción C — liberar reservas automáticamente · **RECHAZADA**

`POL-D0-002` §8 enumera los eventos que modifican una reserva: despacho, cancelación del pedido,
rechazo de crédito, reversión a borrador, expiración, picking parcial y liberación manual. **Es una
tabla cerrada y la reclasificación no está en ella.** Crear un octavo evento que libere compromisos
comerciales desde el motor de inventario duplicaría la autoridad que `D0-03` asignó a la Spec 030.

El precedente del picking parcial —«libera la diferencia y **genera incidencia**; nunca ajusta el
pedido en silencio»— se ha analizado y **no se copia**: allí el que libera es el proceso de
preparación, dueño del pedido en ese momento, y lo hace con incidencia. Aquí el que pediría liberar
es calidad, que no tiene relación con el cliente.

### Opción D — reasignar la reserva a otro stock elegible · **RECHAZADA POR AHORA (FUTURE)**

Exige elegir almacén alternativo, ubicación, lote y serial, y una política de fulfillment. Ninguna de
esas capacidades existe: `POL-D0-002` §7 fija hoy «un almacén por pedido; sin abastecimiento
cruzado». Reasignar sería construir abastecimiento cruzado dentro de una decisión sobre estados de
mercancía.

## Las dos que quedan

| Criterio | **A — bloquear toda la transición** | **B — reclasificar lo no reservado y devolver conflicto** |
|---|---|---|
| Disponible negativo | imposible | imposible |
| Compromiso con el cliente | intacto | intacto |
| Verdad del inventario | el saldo no refleja que 80 están dañadas | **10 unidades dañadas siguen etiquetadas `DISPONIBLE`** |
| Atomicidad | total | parcial, con resultado estructurado |
| Auditoría | un rechazo con cantidades | una aplicación parcial más un conflicto pendiente |
| Coherencia con `D0-03` | alta: `POL-D0-002` §3 ya eligió «todo o nada» en el dominio vecino | media: aplica en parte lo pedido |
| Usabilidad operativa | calidad no puede aislar **nada** hasta que ventas resuelva | calidad aísla lo que puede de inmediato |
| Complejidad aguas abajo | ninguna | necesita dueño del conflicto y su seguimiento |
| Efecto colateral oculto | ninguno | **puede despacharse mercancía dañada** al cliente de la reserva |

Ninguna de las dos se deduce de la autoridad existente. El argumento decisivo de A —que dejar diez
unidades dañadas en `DISPONIBLE` las pone en camino de un cliente— es fuerte, pero es un argumento
de ingeniería, no una regla escrita. El de B —que el conflicto queda registrado y su dueño lo
resuelve— también lo es.

**Recomendación técnica: opción A.** Es la única que no puede terminar entregando mercancía que se
sabe no apta, y es coherente con «todo o nada» que `POL-D0-002` §3 ya eligió para el dominio vecino.
Una recomendación no es una decisión.

## Por qué la elección no bloquea hoy

La matriz de transiciones activas de este mismo checkpoint tiene nueve aristas y **ninguna sale de
`DISPONIBLE`**. Las reservas viven exclusivamente en filas `DISPONIBLE` (`POL-D0-002` §1 y §7). Por
tanto:

> **Ninguna transición activa puede producir el conflicto.** El caso canónico no es alcanzable con la
> matriz vigente.

Y la respuesta contractual al caso canónico, hoy, es determinista y no dice «depende»:

```
can_transition(DISPONIBLE, CUARENTENA, ctx) → DENIED
```

Denegada porque **no está declarada**, por la regla `R-D0-10-7` que este checkpoint hace ejecutable.
No por el conflicto de reservas: el conflicto ni siquiera llega a evaluarse.

## Dónde queda la decisión

> **R-D0-10-10 (propuesta).** Activar la primera transición con origen `DISPONIBLE` hacia un estado
> no vendible exige, **en el ciclo de la Spec que la active**, elegir entre A y B con autoridad de
> negocio. C y D quedan rechazadas por este checkpoint con las razones de arriba. Mientras ninguna
> esté activa, la invariante R-D0-10-9 se cumple por construcción.

La dueña previsible es la **Spec 025** (ajustes de inventario), que ya tiene el evento —un ajuste por
daño, merma o decomiso— y la aprobación de la Spec 045 que ese evento exige. No es la 021: la 021
solo mueve mercancía *hacia* lo vendible.

**Consecuencia para la 021: ninguna.** Su capacidad queda completamente definida sin esta decisión.

## Si algún día gana A

Código de error, cantidad solicitada, cantidad máxima reclasificable (`qty_on_hand − qty_reserved`),
cantidad en conflicto, estado origen y destino. Sin efectos colaterales.

## Si algún día gana B

Además de lo anterior: cantidad aplicada, reservas afectadas, dueño del seguimiento y semántica
transaccional. El resultado no puede ser texto libre: `POL-D0-002` §8 ya estableció que una
diferencia se registra, no se comenta.
