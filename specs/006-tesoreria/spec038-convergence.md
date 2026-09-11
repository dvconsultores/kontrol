# SPEC 038 · CONVERGENCIA

`SPEC 038 — COMPLETE / CONVERGED` (técnica y funcionalmente)

> 2026-09-11. Ciclo completo desde `/speckit.specify`.

## 1. Las dos decisiones que desbloquearon la Spec, y lo que ya estaba escrito

La 038 entró con dos preguntas materiales que la 037 había dejado anotadas sin
autoridad: si un crédito a favor puede devolverse en dinero, y con qué política
se convierte entre monedas. El owner las respondió:

- **`OWNER-DECISION-038-01`** — el reembolso se soporta. No es automático:
  reserva el crédito, exige aprobación y no permite gastarlo dos veces.
- **`OWNER-DECISION-038-02`** — la política cambiaria es parametrizable y la
  conversión, explícita.

Ninguna fuente existente las contradice, así que no hubo `AUTHORITY_CONFLICT`.
La arquitectura funcional §9 dejaba el hueco **a propósito** —«según política»—
y lo que faltaba era precisamente la política, no una regla escondida.

## 2. El defecto más grave del ciclo

`_rate_snapshot` devolvía **`1.0`** cuando la moneda no estaba registrada o
cuando no había tasa del día.

Un pago en divisa quedaba valorado al cambio uno a uno, y nada en pantalla lo
decía. No era un caso raro: era lo que pasaba cada vez que faltaba la tasa, que
es justo cuando más importa.

| | |
|---|---|
| Clasificación | defecto de producto, P0 |
| Corrección | `None` cuando no hay tasa; `RATE_NOT_AVAILABLE` al capturar |
| Mutación | **M6** · devolver `1.0` hace fallar la prueba hostil |
| E2E | el caso está en las tres suites de navegador |

Y de la misma familia: la tasa se buscaba «la más reciente» sin mirar la fecha,
de modo que una tasa de hoy revaluaba una operación de ayer. Ahora la búsqueda
es con fecha y la instantánea queda **congelada**: guarda tasa, fuente, tipo,
día, origen, versión de política y la fila de la que salió.

## 3. El doble gasto

Un crédito a favor puede ahora irse por dos caminos —imputarse a una factura o
devolverse en dinero— y el riesgo es evidente: irse por los dos.

La reserva es lo que lo impide. Solicitar reserva; aprobar **no paga**; ejecutar
saca el dinero y convierte la reserva en devuelto; denegar la libera. Desde el
instante de la solicitud, ese importe deja de ser imputable.

Ejecutar es **idempotente a propósito**. Un reintento por corte de red no puede
convertirse en un segundo pago, y responder con un error a quien reintenta le
invita a insistir de otra forma. Por eso la prueba no exige un código de
rechazo: exige que el dinero no se mueva —mismo saldo, mismo movimiento, mismo
importe devuelto—.

## 4. Dos cifras donde antes había una · delta dirigido a la Spec 037

Al aparecer el reembolso, «crédito disponible» dejó de ser una sola cosa:

- lo **imputable** a documentos: `amount − applied − refund_reserved − refunded`;
- lo **debido** al cliente: `amount − applied − refunded`.

Una reserva sin ejecutar se sigue debiendo; solo cambió la forma en que se
pagará. Por eso reservar no mueve el saldo del cliente y ejecutar sí.

`customer_credits` ofrecía como disponible un crédito ya reservado —el mismo
dinero contado dos veces, y una imputación que el servicio rechazaba después— y
`customer_balance` calculaba el saldo con la resta equivocada. Ambas se
corrigieron **en su dueña**, la 037, no con una copia en tesorería.

Antes de la 038 las dos restas coincidían porque reservado y devuelto eran
siempre cero: **ninguna cifra ya certificada cambia de valor**.

## 5. El orden de las comprobaciones también es una respuesta

Pedir el reembolso de un crédito ajeno respondía «la política no admite
devolución» —y con eso confirmaba que el crédito existe—. La pertenencia se
comprueba **antes**: para quien no es su dueño, ese crédito no existe.

Es la misma lección que dejó `create_shipment` en la Spec 035, y ahora tiene su
prueba y su mutación (**M9**).

## 6. Puerta

| Criterio | Resultado |
|---|---|
| La tasa se inventa cuando falta | **no** — `RATE_NOT_AVAILABLE` |
| Una tasa de hoy valora una operación de ayer | **no** |
| Una tasa posterior revalúa lo ya hecho | **no** |
| La tasa manual se acepta sin política ni motivo | **no** |
| Se convierte sin política activa | **no** |
| Se convierte sin fondos | **no** |
| El mismo crédito se reserva y se imputa | **no** |
| Ejecutar sin aprobar | **no** |
| Aprobar mueve dinero | **no** |
| Ejecutar dos veces paga dos veces | **no** |
| Se devuelve más de lo que queda | **no** |
| Se paga desde una cuenta de otra moneda | **no** |
| Se ejecuta un reembolso sin fondos | **no** |
| El crédito de otra empresa se devuelve | **no** |
| La política tapa la comprobación de dueño | **no** |
| La posición de caja suma monedas distintas | **no** |
| Aritmética monetaria en `float` en lo nuevo | **0** |
| Reglas legales venezolanas escritas en el código | **0** |
| Consultas a servicios externos por la tasa | **0** |
| Permisos nuevos inventados | **0** |
| IGTF ampliado | **no** — su dueña es la 041 |

## 7. Evidencia

| Puerta | Resultado |
|---|---|
| Backend | 1344 pruebas · **1336 pasan · 8 saltos · 0 fallos · 0 errores** |
| Saltos esperados / reales | **8 / 8**, todos S3 |
| `test_spec038_treasury.py` | 33 |
| Frontend | vitest **303/303** · `tsc`, ESLint, Ruff y build limpios |
| Puertas de completitud | **235** (6 nuevas por las tres pantallas) |
| E2E de la 038 | **30/30** en Chromium, Firefox y WebKit |
| Cadena operativa e2e | **183/183** en los tres navegadores |
| E2E de la 033, tras su delta | **21/21** en los tres navegadores |
| Migración `0055` | sube y baja limpia, en `kmc` y en `ke2e` |
| Trazabilidad | **100 %**, 35 requisitos + 2 del delta, 0 huérfanos |
| Preguntas materiales nuevas | **0** |

## 8. Lo que se midió, no se supuso

| | Mutación | Qué rompe |
|---|---|---|
| M5 | el crédito reservado vuelve a ser imputable | la prueba de la reserva |
| M6 | la tasa vuelve a inventarse como `1.0` | la prueba hostil de la tasa |
| M7 | ejecutar no consume la reserva | dos pruebas del consumo |
| M8 | no se comprueba el saldo de la cuenta | dos de fondos |
| M9 | la política se mira antes que el dueño | las tres de pertenencia |

## 9. Tres defectos en las propias pruebas, y uno en la matriz

No todo lo que falló era del producto:

1. **Moneda no única.** `marca().slice(0, 2)` parecía aleatorio y no lo era:
   `Date.now()` en base 36 no cambia sus primeros caracteres en años. Todas las
   pruebas compartían código de moneda.
2. **Mundo contaminado.** Una prueba creaba una segunda empresa para comprobar
   el aislamiento; con dos empresas el shell pasa a pedir «Seleccione una
   empresa» y eso cambiaba el arranque de **todas** las demás suites. Se retiró
   de e2e y se borró la fila que había quedado.
3. **Fila ajena.** La tabla lista los reembolsos de toda la empresa; quedarse
   con la primera «Solicitado» operaba sobre el reembolso de otra prueba.
4. **Dos requisitos sin prueba.** Al levantar la trazabilidad aparecieron dos
   filas que apuntaban a pruebas inexistentes. En vez de retirar los requisitos
   se escribieron las pruebas, con sus mutaciones **M8** y **M9**.

## 10. Un defecto ajeno que bloqueaba la puerta

`npm run build` llevaba roto desde `fe92cf3` (Spec 033): `ConfirmacionPedidoPage`
repetía cuatro claves antes de un spread que las pisaba, y `tsc -b` lo rechaza
con `TS2783`. No lo veía nadie porque `tsc --noEmit` y `npm test` usan otra
configuración y pasan.

Esto obliga a corregir una evidencia anterior: la puerta «build limpia» que la
convergencia de la 037 da por buena **no lo estaba** en ese momento. El defecto
es de la pantalla de confirmación, no de la 037 ni de la 038.

Corregido en su dueña con el mismo comportamiento —valores en blanco, encima lo
ya verificado, encima el campo que cambia— y comprobado con las 21 pruebas e2e
de la Spec 033 en los tres navegadores.

## 11. Las dos separaciones que hay que conservar

**Certificación técnica ≠ homologación legal.** `D0-07` sigue **abierto**. Este
ciclo certifica la tesorería **técnica y funcionalmente**. **No** afirma
homologación fiscal ni liberación legal. Ninguna regla legal venezolana se
escribe en el código: se configura, se versiona y se deja con su referencia de
autoridad.

**Registrar dinero ≠ decidir cuánto se debe.** La 038 ejecuta y registra. No
decide qué se debe (028), ni qué se cobra (037), ni cuánto impuesto corresponde
(041 y fiscales), ni aprueba por su cuenta (045).

## 12. Deuda anotada, no absorbida

| Hallazgo | Dueño |
|---|---|
| `BankTransactionCreate.amount` declarado `float` en el borde de la API | 019 |
| El arqueo de caja resta en coma flotante (`round(float(a) - float(b), 6)`) | 019 |
| El IGTF vive en `treasury` por historia | 041 |
| Proyección de liquidez: lectura pendiente de su ciclo | 038 · fase posterior |

Los dos primeros son de la familia de `KQA-100`. No están corregidos aquí
porque su dueña es otra Spec y el delta corresponde a su ciclo.

## 13. Estado resultante

| | |
|---|---|
| Spec 038 | **COMPLETE / CONVERGED** (técnica y funcional) |
| Spec 037 | con su delta de crédito imputable convergido y verificado |
| Spec 033 | con su delta de build convergido y verificado |
