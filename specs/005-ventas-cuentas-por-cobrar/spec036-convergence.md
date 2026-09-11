# SPEC 036 · CONVERGENCIA

`SPEC 036 — COMPLETE / CONVERGED` (técnica y funcionalmente)

> 2026-09-11, sobre `445ffde`. Ciclo completo desde `/speckit.specify`.

## La premisa de entrada era falsa

Este ciclo empezó con cuatro preguntas materiales abiertas y un motivo declarado
para no poder cerrarlas: «el proceso fuente termina en el ¶107 y no dice nada del
reingreso». Lo primero es cierto —el documento del pedido acaba en «PRODUCTO SALE
CON FACTURA» y su índice enumera siete fases que terminan en el despacho—. Lo
segundo **no**: ese documento describe *un* proceso, no todos.

La devolución tiene autoridad, y de nivel más alto que un documento de proceso:

| Fuente | Nivel | Qué aporta |
|---|---|---|
| `Leyes Venezolanas` §5, §6, §15 | **1 — normas oficiales** | Qué es una NC y una ND, sus causas, sus requisitos, y el flujo completo de la devolución de venta |
| Documento maestro de requerimientos | 3 | «La devolución física **no sustituye** una nota de crédito» |
| Arquitectura funcional §8 | 3 | «Devolución: **recepción, inspección y destino**» |
| Modelo de datos §8, §12, §13 | 3 | `Return` y `CreditDebitNote`; «no ajustar por encima de lo **pendiente** del original»; `CREDITED` como estado de la factura |
| `D0-10` | D0 | `DESPACHADO → DEVUELTO` y `DEVUELTO → DISPONIBLE · RECHAZADO`, dueña 036 |
| `D0-03` §H | D0 | «Re-reservar tras liberar = **nueva fila, nunca reactivación**» |

El `ManualAdministrativoSaint` menciona devoluciones treinta y nueve veces y **no
se usó**: la matriz de autoridad lo sitúa en el nivel 8, «no vinculante».

## Las cuatro preguntas, cerradas

| | Respuesta | Autoridad |
|---|---|---|
| **OQ-036-01** ¿cuándo vuelve al inventario? | En el **cuarto** acto, no en el primero: «Solicitud → Verificación física → Aprobación → **Entrada de inventario**» | Norma §15 |
| **OQ-036-02** ¿qué inspección precede? | «Verificación física», con **dos** destinos: `DISPONIBLE` y `RECHAZADO` | Norma §15 · `D0-10` |
| **OQ-036-03** ¿devolución y nota de crédito? | Actos distintos y vinculados: aceptar **no** emite; la nota puede existir sin devolución; el tope es lo pendiente | Maestro · norma §5 · regla de integridad |
| **OQ-036-04** ¿la reserva `FULFILLED`? | No se toca. La disponibilidad viene de la entrada de inventario | `D0-03` §H |

Ninguna hubo que decidirla. **Preguntas materiales nuevas: 0.**

## Lo que había

`create_return` insertaba una fila y no comprobaba nada: el origen era un texto
libre, sin factura, sin despacho, sin cliente y sin almacén, y no había forma de
saber cuánto quedaba por devolver. `create_credit_note` recibía **el número por
parámetro**: ningún correlativo fiscal, ningún número de control, ninguna línea,
ningún impuesto y ningún tope contra el original. Y ninguna de las dos tocaba el
inventario, así que la mercancía devuelta no volvía nunca.

## Puerta

| Criterio | Resultado |
|---|---|
| Una solicitud mueve inventario | **no** |
| Recibir la mercancía la hace vendible | **no** |
| Se reingresa sin verificar | **no** |
| Se reingresa sin aprobar | **no** |
| Destinos de la mercancía devuelta | **dos**, los que `D0-10` concede |
| Se inventa un estado de mercancía | **0** |
| La devolución es en cantidad base | sí — una caja de doce reingresa 12 |
| Se devuelve más de lo despachado | **no**, ni acumulando |
| La reserva `FULFILLED` se toca | **no** |
| El pedido revierte su historia | **no** |
| Aceptar la devolución emite la nota | **no** |
| El impuesto de la nota se recalcula con la regla de hoy | **no** — se reparte el de la factura |
| La nota lleva consecutivo y control propios | sí, de la 042 |
| Una nota gasta el correlativo de las facturas | **no** |
| Se acredita por encima de lo pendiente | **no** |
| `CREDITED` con una nota parcial | **no** |
| La nota de débito toca inventario | **no** |
| Backend | 1279 pruebas · **1271 pasan · 8 saltos · 0 fallos · 0 errores** |
| Saltos esperados / reales | **8 / 8**, todos S3 |
| Frontend | vitest 295/295 · `tsc`, ESLint, Ruff y build limpios |
| E2E de la 036 | **36/36** en Chromium, Firefox y WebKit |
| Cadena operativa e2e | **162/162** en los tres navegadores |
| Guardias de arquitectura 031→036 | **128/128**, sin saltos |
| Migración `0054` | ida y vuelta sobre base limpia |
| Trazabilidad | **100 %**, 42 requisitos, 0 huérfanos |
| Preguntas materiales nuevas | **0** |

## Lo que se midió, no se supuso

Tres mutaciones, y una destapó **una prueba débil mía**. El caso de
proporcionalidad usaba una alícuota del 16 %, que es justo la que la mutación
escribía a mano: el impuesto repartido y el recalculado daban el mismo número y
la prueba no distinguía las dos cosas. Corregida a una alícuota distinta, y
añadido el caso que ningún recálculo puede pasar —la regla cambia **después** de
emitir la factura y la nota tiene que seguir llevando el impuesto de la
operación—, la mutación falla como debía.

Las otras dos: hacer que la recepción reclasifique directo a `DISPONIBLE` rompe
cinco pruebas; quitar el tope acumulado de la devolución rompe dos.

## Dos defectos ajenos, medidos y arreglados en su dueña

| Hallazgo | Dueña | Cómo se descubrió |
|---|---|---|
| `emit_document` tenía el tipo de documento **escrito a mano** y rechazaba todo lo que no fuera `INVOICE:` | **042** | Al ir a emitir la primera nota de crédito. El modelo declaraba «INVOICE / CREDIT_NOTE / DEBIT_NOTE» desde el principio |
| `issue_invoice` **nunca creaba la cuenta por cobrar** | **034** | Al aplicar la nota y no encontrar documento que ajustar. «9. Emitir factura → **10. Crear CxC**» solo ocurría por el camino heredado `transition_invoice`; las facturas del proceso real nacían sin receivable |

El segundo es el más serio de los dos: llevaba desde la convergencia de la 034 y
ninguna prueba lo veía porque ninguna llegaba a cobrar una factura emitida por su
camino.

## Tres cosas que la regresión completa encontró y no las pruebas dirigidas

1. **El vocabulario de una serie fiscal.** El guardia nuevo —una nota no puede
   gastar el correlativo de las facturas— hizo fallar una prueba que creaba la
   serie como `"FACTURA"` y emitía un `INVOICE:`. No eran dos vocabularios en
   pugna: `"FACTURA"` aparecía en **un solo sitio** del repositorio y todos los
   demás usan `"INVOICE"`. Era una prueba desalineada, y el guardia la encontró.
2. **`updated_at` anulable en la migración y no en el ORM.** Las dos tablas
   nuevas heredan `TimestampMixin`, que la declara obligatoria. La paridad
   ORM/base de N10 lo vio.
3. **El catálogo de estados replicándose.** Al añadir `DEVUELTO`, el módulo de
   ventas llegaba a tres etiquetas exclusivas y el guardia de la Spec 023 avisó:
   «el catálogo vive en un módulo; copiarlo en otro es duplicar el motor». Los
   estados de la devolución pasaron a `states.py` y ventas se los pide.

Las tres eran reales. Ninguna se silenció.

## Las dos separaciones que hay que conservar

**Certificación técnica ≠ homologación legal.** `D0-07` sigue abierto y las Specs
039-043 siguen en `BLOCKED_BY_LEGAL_VALIDATION`. Este ciclo certifica la nota de
crédito y la de débito **técnica y funcionalmente** contra el motor fiscal
existente. **No** afirma homologación fiscal ni liberación legal para producción.

**Emitir ≠ cobrar.** La nota ajusta el documento por cobrar con el motor de la
004/037. Si la factura ya está cobrada no hay saldo que reducir y la nota queda
sin aplicar: qué hacer con ese crédito a favor es de CxC y de tesorería.

## Deuda anotada, no absorbida

| Hallazgo | Dueño |
|---|---|
| Qué hacer con la mercancía de una devolución **denegada**: se queda en `DEVUELTO` y devolvérsela al cliente sería una salida nueva que ninguna fuente declara | 036/038, requiere autoridad |
| Un crédito a favor sobre factura ya cobrada: imputación o reembolso | 037 · 038 |
| `FiscalNumberSeries.document_type` no tiene catálogo canónico ni restricción | 042 |
| `calculate_tax` opera en `float` | 039 |
| Selector de almacén truncado sin aviso en ocho pantallas | organización / 008 |

## Estado resultante

| | |
|---|---|
| Spec 036 | **COMPLETE / CONVERGED** (técnica y funcional) |
| Spec 034 | `COMPLETE / CONVERGED` · con un delta dirigido recibido (cuenta por cobrar al emitir) |
| Spec 042 | delta dirigido recibido: el motor emite los tres tipos de documento |
