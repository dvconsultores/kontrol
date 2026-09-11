# SPEC 036 · DEVOLUCIONES, NOTAS DE CRÉDITO Y NOTAS DE DÉBITO

> Ciclo completo desde `/speckit.specify`. Estado de entrada:
> `DEPENDENCY UNBLOCKED · NOT READY_FOR_IMPLEMENTATION`, con **cuatro preguntas
> materiales abiertas**. Este documento es el trabajo de cerrarlas.

## 1. Lo que había que averiguar primero

Al converger la Spec 035 quedó escrito que el proceso fuente del pedido
—«Pedido - Organizar Pedido - Confirmar - Facturar - Despachar»— **termina en el
despacho**. Y es verdad: su última etapa es «PRODUCTO SALE CON FACTURA» y su
propio índice enumera siete fases que acaban en «7. Despacho».

De ahí se siguió que la 036 no tenía autoridad. **Era una conclusión precipitada,
y este ciclo la corrige.** Ese documento describe *un* proceso, no todos. La
devolución tiene autoridad, y de nivel más alto: está en las normas y en los
documentos maestros.

| Fuente | Nivel | Qué aporta |
|---|---|---|
| `Leyes Venezolanas` §5, §6, §15 | **1 — normas oficiales** | Qué es una NC y una ND, sus causas, sus requisitos, y el **flujo completo de la devolución de venta** |
| `01_Kontrol_Documento_Maestro_de_Requerimientos` | 3 | «La devolución física **no sustituye** una nota de crédito» |
| `02_Kontrol_Arquitectura_Funcional` §8 | 3 | «Devolución: **recepción, inspección y destino**» |
| `03_Kontrol_Modelo_de_Datos` §8, §11, §12, §13 | 3 | Entidades `Return` y `CreditDebitNote`; regla «no ajustar por encima de lo **pendiente** del original»; `CREDITED` como estado de la factura |
| `D0-10` matriz de transiciones | D0 | `DESPACHADO → DEVUELTO` y `DEVUELTO → DISPONIBLE · RECHAZADO`, **dueña 036** |
| `D0-03` §H | D0 | «Re-reservar tras liberar = **nueva fila, nunca reactivación**» |

El `ManualAdministrativoSaint` menciona devoluciones treinta y nueve veces y
**no se usa**: la matriz de autoridad lo sitúa en el nivel 8, «referencia
comparativa, no autoridad arquitectónica ni legal. No vinculante».

## 2. El flujo canónico

La norma lo escribe entero, y en este orden:

```
Devolución de venta
  Solicitud
  → Verificación física
  → Aprobación
  → Entrada de inventario
  → Nota de crédito vinculada
  → Ajuste de IVA
  → Ajuste de cuenta por cobrar
  → Registro en libro de ventas

Cargo posterior
  Identificación del concepto
  → Aprobación
  → Nota de débito vinculada
  → Ajuste de base e IVA
  → Cuenta por cobrar
  → Registro fiscal
```

Dos cosas saltan a la vista y las dos importan. La devolución tiene **cuatro
actos antes** de tocar el inventario. Y el cargo posterior **no tiene ninguna
etapa de inventario**: una nota de débito no mueve mercancía.

## 3. Las cuatro preguntas materiales, cerradas

### OQ-036-01 · ¿cuándo y con qué evento vuelve la mercancía al inventario?

**CERRADA.** El flujo lo ordena: `Solicitud → Verificación física → Aprobación →
**Entrada de inventario**`. La entrada es el cuarto acto, no el primero. Y la
arquitectura funcional nombra los tres momentos: «**recepción**, **inspección** y
**destino**».

Son actos distintos y no se fusionan:

| Acto | Qué cambia | Estado de mercancía |
|---|---|---|
| Solicitud | nada físico | — |
| Recepción física | la custodia vuelve a la empresa | `DESPACHADO → DEVUELTO` (`D0-10`, dueña 036) |
| Verificación + aprobación | nada físico | — |
| Entrada de inventario | la mercancía vuelve a existencia | `DEVUELTO → DISPONIBLE` o `RECHAZADO` |

Una solicitud **no** aumenta inventario. Una recepción **no** lo hace vendible.

### OQ-036-02 · ¿qué inspección precede al reingreso?

**CERRADA.** Existe —«Verificación física» en la norma, «inspección» en la
arquitectura funcional— y `D0-10` lo dice con todas las letras al declarar la
arista: «Requiere la **inspección previa al reingreso** que 036 define».

Sus destinos **no se eligen**: `D0-10` concede a la 036 exactamente dos,
`DISPONIBLE` y `RECHAZADO`. La fila «Devolución» de la arquitectura funcional
nombra cinco —disponible, cuarentena, reparación, rechazo, desecho— pero es una
fila genérica de todo el concepto y tres de esos destinos tienen **otro dueño**:
`CUARENTENA` entra por la resolución de incidencias de la 020, `DESECHO` es una
baja de inventario de la 025 (`RECHAZADO · CUARENTENA → DESECHO`), y
«reparación» **no es un estado de mercancía**: en la norma es un *motivo de
traslado* de una guía de despacho, no un destino de devolución.

Así que dos destinos, los dos declarados, ninguno inventado. Es la misma forma
que la Spec 021 usa al confirmar una recepción.

### OQ-036-03 · ¿qué relación hay entre la devolución y la nota de crédito?

**CERRADA**, y con tres piezas que se complementan.

1. **No son lo mismo.** El documento maestro es explícito: «La devolución física
   **no sustituye** una nota de crédito». Son dos actos, y la aceptación de la
   devolución **no emite** la nota: la emisión es un acto fiscal propio, con su
   consecutivo y su número de control. Es la misma separación que la 034 impuso
   entre generar la factura y emitir el documento fiscal.
2. **Una devolución aceptada lleva a una nota vinculada.** El flujo lo dice:
   `Entrada de inventario → **Nota de crédito vinculada**`.
3. **Pero una nota de crédito no necesita una devolución.** La norma enumera sus
   causas: «Devolución de mercancía. Anulación de una operación. Descuento
   posterior. Bonificación posterior. Corrección de un precio facturado en
   exceso. Disminución de cantidad. Devolución de envases o depósitos. Reversión
   total o parcial». Solo la primera y la séptima traen mercancía de vuelta.

La norma fija además **qué debe llevar** la nota: identificarse como tal,
consecutivo propio, número de control, referencia a la factura original con su
fecha, número y control, motivo, líneas, cantidades y montos, «**recalcular
proporcionalmente base imponible e IVA**» y «**mantener la misma clasificación
tributaria de la operación original**».

Y el tope lo pone la regla de integridad del modelo de datos: «**No ajustar por
encima de cantidades/base/IVA pendientes del original**». *Pendientes*, no
totales: el límite es acumulativo.

### OQ-036-04 · ¿qué pasa con una reserva ya `FULFILLED`?

**CERRADA.** No se toca. La autoridad es de la dueña de las reservas, `D0-03`:

> «Re-reservar tras liberar = **nueva fila, nunca reactivación**.»

Y `FULFILLED` no es siquiera una liberación: es un **consumo**. `D0-03` §H
enumera todos los disparadores que tocan una reserva —cancelación, rechazo de
crédito, reversión, expiración, picking parcial, despacho— y la devolución no
está entre ellos. El despacho «**consume**: `FULFILLED` — no `RELEASED`», y el
stock despachado «salió físicamente; la reserva quedó `FULFILLED`».

La devolución no resucita nada. Crea disponibilidad por el camino que la norma
nombra: «**Entrada de inventario**». Si esa mercancía se compromete después, será
una reserva nueva, con su propia fila.

## 4. Lo que este ciclo construye

1. **La devolución como proceso de cuatro actos**, no como un registro suelto.
2. **La elegibilidad**: qué se puede devolver, cuánto queda por devolver, y de
   qué despacho y factura viene.
3. **El reingreso físico correcto**: en cantidad base, con lote y serial, a una
   ubicación real, por el motor de inventario.
4. **La nota de crédito de verdad**: vinculada, proporcional, con su consecutivo
   y su número de control, y con tope acumulativo.
5. **La nota de débito**, que aumenta y **no toca inventario**.

## 5. Fronteras

La 036 **no** cobra, **no** devuelve dinero, **no** reabre reservas, **no**
inventa estados de mercancía, **no** numera por su cuenta y **no** reescribe la
factura original. Consume los motores de la 023 (inventario), 030 (reservas),
037/004 (CxC), 039-043 (fiscal), 045 (aprobaciones) y 046 (documentos).

## 6. La separación que hay que conservar

`D0-07` sigue abierto. Este ciclo certificará la nota de crédito y la de débito
**técnica y funcionalmente** contra el motor fiscal existente. **No** afirma
homologación fiscal ni liberación legal para producción.
