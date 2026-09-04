# MATERIAL DECISION REQUIRED — SPEC 023 · SALDO MULTIESTADO

> Producido por el ciclo dirigido del 2026-09-03. **RESUELTO el mismo día** por el checkpoint
> `D0-10`, en `docs/governance/d0-foundational-decisions/d0-10-checkpoint/`. Se conserva por lo que
> documenta: la pregunta tal como se planteó y las opciones tal como se evaluaron.
>
> | Decisión | Resultado |
> |---|---|
> | 1 · grafo de transiciones | **cerrada** — nueve transiciones activas con evidencia, deny-by-default para el resto (`ADR-D0-010` v2 §Gobierno) |
> | 2 · reservado frente a reclasificación | **cerrada** — invariante `R-D0-10-9`; liberación automática y reasignación rechazadas por autoridad; la elección restante se traslada, por `R-D0-10-10`, al ciclo de la Spec que active la primera arista con origen `DISPONIBLE`. Ninguna arista activa puede producirla |
>
> La opción 3 que este documento señalaba como coherente —declarar solo el tramo de recepción y que
> cada Spec añada el suyo— es la que se adoptó.

## Por qué hay que decidir

El `ADR-D0-010` hizo bien la parte difícil: declaró los quince estados, fijó que vendible es
exclusivamente `DISPONIBLE` y ordenó que toda transición sea un movimiento. Con eso, la vendibilidad,
la reservabilidad y la fórmula de disponible quedan cerradas sin preguntar nada a nadie.

Lo que no declaró es **cuándo se puede pasar de un estado a otro** —aunque su regla R-D0-10-7 obliga
al motor a rechazar lo no declarado— ni **qué pasa con la mercancía ya comprometida a un cliente
cuando cambia de estado**. Sin lo primero no hay reclasificación legal; sin reclasificación, la Spec
021 no puede liberar formalmente lo recibido, que es justo lo que se le pide.

---

## DECISIÓN 1 — Grafo de transiciones de estado de mercancía

**Qué falta:** la tabla que R-D0-10-7 da por existente.

**Alcance mínimo para desbloquear la Spec 021** (el resto puede declararse cuando su Spec se
construya, porque el motor rechaza por defecto lo no declarado):

| Desde | Hacia | Por qué haría falta | Dueño del evento |
|---|---|---|---|
| *(entrada)* | `RECIBIDO` | La recepción física crea existencia no conciliada | 019 |
| `RECIBIDO` | `PENDIENTE_CONFIRMACION` | Empieza el conteo o la conciliación | 021 |
| `RECIBIDO` · `PENDIENTE_CONFIRMACION` | `BLOQUEADO` | Se abre una incidencia sobre esa mercancía | 020 |
| `BLOQUEADO` | estado previo o el que decida el tratamiento | R-D0-10-6: solo al cerrar la incidencia | 020 · 021 |
| `PENDIENTE_CONFIRMACION` | `DISPONIBLE` | **Liberación formal** (R-D0-10-4) | 021 |
| `PENDIENTE_CONFIRMACION` · `CUARENTENA` | `RECHAZADO` | No apto | 021 · 025 |
| `RECIBIDO` · `PENDIENTE_CONFIRMACION` | `CUARENTENA` | Retención por calidad | 021 |

**Preguntas concretas que la decisión debe responder:**

1. ¿La recepción de la Spec 019 pasa a escribir `RECIBIDO` en vez de `DISPONIBLE`? El ADR dice que
   ese cambio «llega con la Spec 021, no con esta decisión». Hay que confirmar que sigue siendo así.
2. ¿`BLOQUEADO` vuelve al estado del que salió, o el tratamiento de la incidencia decide el destino?
3. ¿Se declara ahora el grafo completo de los quince estados, o solo el tramo de recepción y cada
   Spec añade el suyo al construirse?

**Hacia dónde apunta la autoridad existente:** la opción 3 es la coherente con `SAFE_MIGRATION` del
ADR y con cómo KONTROL ha venido cerrando alcances. Declarar transiciones de `PICKING`, `PREPARADO`
o `DESPACHADO` hoy sería decidir por las Specs 031, 032 y 035 antes de auditarlas.

---

## DECISIÓN 2 — Reservado frente a reclasificación

**Qué falta:** qué ocurre cuando se reclasifica mercancía `DISPONIBLE` que tiene reserva viva.

**El problema, en números.** Fila `DISPONIBLE` con `qty_on_hand = 100` y `qty_reserved = 30`.
Calidad manda 80 unidades a `CUARENTENA`. Si la transición se ejecuta sin más:

`qty_on_hand = 20` · `qty_reserved = 30` · `disponible = −10`

Un disponible negativo que **no** viene de `allow_negative`. `POL-D0-002` §6 prohíbe la sobreventa
salvo por esa política explícita, así que este camino la contradice.

| Opción | Qué hace | Consecuencia |
|---|---|---|
| **A** | Bloquear la transición mientras haya reservado | La calidad no puede poner en cuarentena mercancía vendida. Protege al cliente y ata al almacén |
| **B** | Mover solo la cantidad no reservada | La transición se ejecuta parcialmente y en silencio: se pidieron 80 y se movieron 70. Físicamente falso si el daño afecta a las 80 |
| **C** | Liberar las reservas primero, y luego mover | Ventas pierde compromisos sin intervenir. Necesitaría notificación e incidencia, como el picking parcial de `POL-D0-002` §8 |

**Preguntas concretas:**

1. ¿Puede existir `qty_reserved` sobre una fila que no sea `DISPONIBLE`? Hoy la política dice que el
   contador vive en `DISPONIBLE`; si la respuesta es no, la opción B necesita definir qué pasa con la
   reserva de las unidades que sí se mueven.
2. ¿La reclasificación forzosa —daño, pérdida, decomiso— tiene un camino distinto de la voluntaria?
3. Si se elige C, ¿genera incidencia como el picking parcial, o basta con auditoría?

**Hacia dónde apunta la autoridad existente:** `POL-D0-002` §8 ya resolvió un caso gemelo. Ante un
picking parcial, la regla es «libera la diferencia y **genera incidencia**; nunca ajusta el pedido en
silencio». Esa frase descarta la opción B por construcción —el silencio está prohibido— y da forma a
la C. Pero aplicarla aquí es extenderla a otro hecho, y eso lo decide quien la escribió.

---

## Lo que este ciclo deja hecho y no hay que repetir

- Catálogo de quince estados extraído, con significado literal, vendibilidad y reservabilidad.
- Las ocho reglas del ADR clasificadas: tres implementables, una implementada, tres incompletas, una
  futura.
- Los diez puntos de escritura del motor localizados y atribuidos por dueño.
- Los cinco consumidores de saldo clasificados por lo que necesitan.
- Un defecto vivo documentado: la recepción de transferencia con diferencia declara `CUARENTENA` en
  `TransferLine.destination_state` y el motor la ignora.
- Un hueco estructural medido: `InventoryMovement` no lleva estado, y `recompute_balances`
  colapsaría cualquier saldo multiestado en `DISPONIBLE`.

Con las dos decisiones tomadas, el ciclo de implementación tiene todo lo demás listo.
