# SPEC 033 — CONFIRMACIÓN INDEPENDIENTE DEL PEDIDO · CICLO DE IMPLEMENTACIÓN

> 2026-09-06, sobre `4b29eaf`. Ciclo completo desde `/speckit.specify`.
> **`MATERIAL OQ = 0`.** A diferencia de los ciclos anteriores, aquí la autoridad no estaba
> repartida: `ADR-D0-012` decide **las seis** preguntas materiales que el ciclo señalaba, y el
> proceso fuente enumera literalmente qué se compara.

## 1. La fuente

**Proceso 6 · Confirmación de pedido**

| ¶ | Texto |
|---|---|
| 61 | Esta etapa debe quedar muy bien definida porque constituye un **control independiente** después del picking. |
| 62 | El Área de Confirmación recibe el pedido preparado. |
| 63 | **Obtiene el pedido original.** |
| 64 | **Realiza un nuevo chequeo físico.** |
| 65 | Verifica producto por producto. |
| 66 | Confirma referencias/SKU. |
| 67 | Confirma cantidades. |
| 68 | Confirma **presentación o unidad correspondiente**. |
| 69 | Comprueba que la mercancía esté **en condiciones para despacho**. |
| 70-71 | **Compara: Pedido emitido vs. Mercancía físicamente preparada.** |

**Punto de decisión**

| ¶ | Texto |
|---|---|
| 73 | ¿Pedido conforme? |
| 74-79 | **No** → se identifica la diferencia · **se registra la incidencia** · el pedido **regresa a preparación/corrección** · se completa, sustituye o corrige · **regresa nuevamente a Confirmación**. |
| 80-81 | **Sí** → el pedido queda **formalmente confirmado**. |

**Proceso 7 · Liberación para facturación**

| ¶ | Texto |
|---|---|
| 83 | El Área de Confirmación **autoriza** que el pedido puede facturarse. |
| 86-90 | «Almacén prepara. Confirmación verifica. Facturación factura sobre un pedido previamente confirmado. Eso establece una **separación funcional adecuada**.» |

## 2. Lo que decide `ADR-D0-012`, y que no hay que decidir aquí

| Regla | Qué cierra |
|---|---|
| **R-D0-12-1** | La confirmación es «un **evento y una entidad distintos del picking**, con su propio actor, momento, resultado y evidencia. **No es un campo booleano** en el pedido ni un estado más de la lista de picking» |
| **R-D0-12-2** | Compara «el **pedido original** contra la **mercancía físicamente preparada**, verificando producto, SKU, cantidad, **presentación** y condición. La comparación es **contra el pedido, no contra la lista de picking**: comparar la preparación consigo misma no es un control» |
| **R-D0-12-3** | No conforme → incidencia con evidencia → el pedido vuelve a preparación → tras la corrección exige **nueva confirmación completa, no parcial** |
| **R-D0-12-4** | Conforme → `CONFIRMED` → habilita `READY_FOR_BILLING` |
| **R-D0-12-5** | **Segregación configurable**: `same_user_allowed` por empresa y por proceso, con **defecto `false`**, «porque un control cuyo valor por defecto lo anula no es un control» |
| **R-D0-12-6** | No se codifica la política de ningún cliente concreto |

### Qué significa «independiente»

El ¶90 lo dice: **separación funcional**. Almacén prepara, Confirmación verifica, Facturación
factura. `R-D0-12-5` lo traduce a producto sin inventar nada: la separación es **configurable por
empresa**, y su defecto es exigirla. Una empresa de tres personas puede desactivarla a conciencia y
queda auditado; lo que no puede es desactivarse sola.

En la implementación, «distinto» significa **distinto del que preparó**: ni de quien recogió ninguna
parada ni de quien consolidó. Eso es lo que hace del control un control.

### El conteo del verificador

El ¶64 dice «realiza un **nuevo chequeo físico**» y el ¶67 «confirma cantidades». No es aprobar la
evidencia ajena: es medir otra vez. Por eso el verificador **registra lo que cuenta**, y esa cifra se
guarda aparte de lo que la Spec 032 preparó. Tres cifras distintas y las tres se conservan:

| | De dónde sale |
|---|---|
| `required_base_quantity` | La línea del pedido, congelada |
| `prepared_base_quantity` | Lo que la Spec 032 consolidó |
| `checked_base_quantity` | Lo que el verificador cuenta ahora |

**No se implementa conteo ciego.** Ni el proceso ni el ADR lo piden, y `R-D0-12-6` prohíbe
codificar la política de un cliente concreto.

## 3. Lo que compara el control

Contra la **línea del pedido**, no contra el plan (`R-D0-12-2`):

| Dimensión | Autoridad | Cómo |
|---|---|---|
| Producto y SKU | ¶65-66 | identidad de la línea; sin sustitución silenciosa |
| Cantidad | ¶67 | en **unidad base**, `Decimal` exacto |
| Presentación o unidad | ¶68 | contra el snapshot congelado de la línea (`ADR-D0-009`), nunca contra el maestro actual |
| Condición para despacho | ¶69 | el verificador la declara |
| Línea faltante | — | no conforme; no se ignora por ausencia |
| Línea sobrante | — | no conforme |

## 4. Fronteras

La 033 **no** ejecuta picking, no escribe `InventoryBalance`, no crea `InventoryMovement`, no mueve
ni reclasifica mercancía, no toca la reserva, no replanifica, no factura y no despacha. Verifica y
deja constancia.

**Delta de inventario esperado: 0 en todo.**

## 5. Qué pasa al rechazar, y qué queda pendiente de otra Spec

`R-D0-12-3` y el ¶77 son claros: se registra la incidencia y **el pedido regresa a preparación**.
Eso es lo que hace la 033: `PREPARED → PREPARING`, con la incidencia y su evidencia.

Lo que ocurre después —«se completa, sustituye o corrige» (¶78)— es de la **Spec 032**, y hoy no
existe: su plan quedó `CLOSED` al consolidar y no tiene camino de reapertura, igual que no tiene la
arista `PICKING → DISPONIBLE` que este mismo tramo dejó anotada al cerrar la 032.

**Esto no bloquea a la 033**: rechazar no exige mover mercancía. El pedido queda registrado donde el
proceso dice que queda —en preparación, con su incidencia— y el sistema refleja exactamente eso. Lo
que todavía no puede es ejecutar la corrección, y esa deuda tiene dueña.

## 6. Deltas dirigidos

| Delta | Dueño | Qué |
|---|---|---|
| **A** | Spec 030 (`sales`) | `PREPARED → CONFIRMED` y `PREPARED → PREPARING`, declarados por `ADR-D0-012` |
| **B** | Spec 001 (`organization`) | `Company.confirmation_same_user_allowed`, defecto `false` (`R-D0-12-5`), con el precedente tipado de `reservation_ttl_days` |

`READY_FOR_BILLING` **no se añade**: lo escribirá la Spec 034, igual que la 032 dejó `CONFIRMED`
para esta.

## 7. Fuera de alcance

Facturación, número de control, impuestos, libro de IVA, cuentas por cobrar (034) · despacho,
transporte y permisos (035) · conteo ciego · aprobación de excepciones por supervisor —no existe
autoridad— · la corrección física tras un rechazo (032).
