# SPEC 037 · CONVERGENCIA

`SPEC 037 — COMPLETE / CONVERGED` (técnica y funcionalmente)

> 2026-09-11, sobre `187d8f3`. Ciclo completo desde `/speckit.specify`.

## 1. La pregunta que bloqueaba, y por qué no hacía falta inventar nada

La 037 entró con una pregunta material: cuando una nota de crédito se emite
contra una factura **ya cobrada**, ¿qué representa el importe que queda a favor
del cliente?

La respuesta estaba escrita. La arquitectura funcional §9 dice:

> CxC — Saldo = documentos + débitos − cobros − retenciones − **créditos**.

y el modelo de datos declara que una aplicación puede tener por origen un
**`credit`**. Así que el importe a favor es **un crédito sin aplicar sobre su
propia nota**, que resta del saldo del cliente y puede imputarse a otros
documentos suyos. No hay entidad nueva, ni factura negativa, ni pago falso, ni
reapertura de la factura cobrada, ni reverso del cobro histórico.

Lo que **no** tiene autoridad queda declarado y sin construir: **el reembolso en
dinero** —ninguna fuente lo menciona— y **la aplicación entre monedas**, que
depende de una política de diferencia cambiaria que todavía no existe.

## 2. El defecto más grave del ciclo

`apply_credit_note` comprobaba la empresa y **nada más**. Dentro de una misma
empresa, el crédito del cliente X podía pagar la factura del cliente Y.

No era un caso raro: era el camino normal. Ninguna prueba lo veía porque ninguna
lo intentaba.

| | |
|---|---|
| Clasificación | defecto de producto, P0 |
| Corrección | `source.customer_id == target.customer_id`, comprobado en la transacción |
| Mutación | quitar la guardia hace fallar la prueba hostil |
| E2E | el caso está en las tres suites de navegador |

## 3. Los otros dos

**Ninguna aplicación dejaba rastro.** `apply_credit_note` mutaba los dos saldos
y no escribía nada, contra el §9: «cada aplicación relaciona origen, destino,
moneda, tasa, monto nominal, monto fiscal y fecha». Una aplicación sin fila no
se puede auditar ni revertir. Ahora cada una deja su `Application` canónica.

**No existía el reverso.** «Los reversos **no eliminan**; crean evento inverso y
reapertura controlada». Ahora la fila original se conserva marcada, se añade su
inverso por el importe contrario, y el documento vuelve a estar abierto porque
vuelve a tener saldo —no porque alguien le cambie el estado a mano—.

## 4. El delta monetario, y la identidad de su dueño

El cuarto defecto no era de esta Spec: `open_item_balance` calculaba el dinero
en coma flotante, y es el motor que comparten CxP, CxC, tesorería y conciliación.

**La identidad del dueño había que desambiguarla antes de tocar nada.** En el
Máster 56, `004` es **Licenciamiento**. La carpeta `004-compras-cuentas-por-pagar`
pertenece a otra numeración —la de iniciativas—, y el mapa de equivalencias dice
«**028 CxP y pagos ↔ `004-compras`**». Dueño canónico: **Spec 028**. Licenciamiento
no se tocó.

La autoridad tampoco hubo que buscarla lejos: `ADR-D0-001` ya registra
**`KQA-100`** —«`Decimal + float`… que rompió factura, pago, cobro»— como defecto
CRÍTICO, y el propio módulo tiene su helper `_dec` con la advertencia en el
docstring. El motor de saldos nunca lo recibió.

Y no hizo falta decidir ninguna política de redondeo, porque el cálculo no
depende de ninguna: los dos operandos vienen de columnas de escala 2 y su resta
es exacta. El `round(..., 6)` no era política de nadie sino el margen que la coma
flotante necesitaba, y su huella estaba a la vista: `<= 1e-6` para cerrar un
documento, que no cerraba en cero sino «suficientemente cerca de cero».

Convergido en su dueña: `spec028-monetary-balance-delta.md`.

## 5. Puerta

| Criterio | Resultado |
|---|---|
| Un crédito se aplica al documento de otro cliente | **no** |
| La misma empresa se considera suficiente | **no** |
| Una aplicación no deja rastro | **no** |
| El reverso borra o muta la original | **no** |
| Se revierte dos veces | **no** |
| Se aplica más de lo que queda | **no** |
| Se aplica entre monedas distintas | **no** — error de dominio, sin conversión |
| El crédito se resta dos veces | **no** |
| Aplicar un crédito crea un cobro | **no** |
| Aplicar un crédito mueve tesorería | **no** |
| La factura pagada se reabre | **no** |
| El cobro histórico se revierte por una nota | **no** |
| Existe reembolso en API o interfaz | **0** |
| Aritmética monetaria en `float` en el motor | **0** |
| `1e-6` como cero monetario | **0** |
| Backend | 1311 pruebas · **1303 pasan · 8 saltos · 0 fallos · 0 errores** |
| Saltos esperados / reales | **8 / 8**, todos S3 |
| Frontend | vitest 297/297 · `tsc`, ESLint, Ruff y build limpios |
| E2E de la 037 | **27/27** en Chromium, Firefox y WebKit |
| Cadena operativa e2e | **189/189** en los tres navegadores |
| Guardias de arquitectura 028→036 | **134/134** |
| Trazabilidad | **100 %**, 28 requisitos, 0 huérfanos |
| Preguntas materiales nuevas | **0** |

## 6. Lo que se midió, no se supuso

Cuatro mutaciones permanentes, cada una falla donde debe:

| | Mutación | Qué rompe |
|---|---|---|
| M1 | quitar la guardia de cliente | la prueba hostil del P0 |
| M2 | no crear la fila de aplicación | cuatro pruebas de rastro y reverso |
| M3 | borrar la original al revertir | las dos de historia del reverso |
| M4 | restar el crédito dos veces | el saldo y el estado de cuenta |

Y en el delta monetario, devolver `float` al saldo hace fallar **5 de 7**. Sus
cifras están elegidas entre las que **no son representables en binario**: tres
aplicaciones de `33.33` sobre `99.99`, y `0.10 + 0.20` sobre `0.30`.

## 7. Un fallo intermitente, clasificado con evidencia

La primera corrida de la cadena operativa dejó en rojo la prueba de interfaz del
despacho, en Firefox. Aislada, pasa. Repetida la cadena entera, pasa: **189/189**.
Clasificación: `EXTERNAL_ENVIRONMENT` —contención al correr ocho suites en
paralelo—, no regresión. No se dio por buena diciendo «ya pasó antes»: se aisló,
se reprodujo y se comparó.

## 8. Un defecto de superficie, de la misma familia que uno anterior

El selector de clientes pedía `?limit=200` a un endpoint que **no acepta
`limit`**: pagina con `page`/`page_size` y su máximo es 100. El parámetro
inventado se ignoraba en silencio y el desplegable se quedaba con los veinte por
defecto. Es la misma clase de defecto que el selector de almacén de la Spec 031,
y se corrigió igual: pedir hasta agotar `total`, sin confiar en un tope.

## 9. Las dos separaciones que hay que conservar

**Certificación técnica ≠ homologación legal.** `D0-07` sigue abierto y las Specs
039-043 en `BLOCKED_BY_LEGAL_VALIDATION`. Este ciclo certifica las cuentas por
cobrar **técnica y funcionalmente**. **No** afirma homologación fiscal.

**Derecho de cobro ≠ movimiento de dinero.** La 037 gobierna el saldo, sus
aplicaciones y su trazabilidad. Mover dinero es de la 038, y por eso aplicar un
crédito no crea ningún cobro ni toca tesorería.

## 10. Deuda anotada, no absorbida

| Hallazgo | Dueño |
|---|---|
| Reembolso de un crédito a favor: sin autoridad en ninguna fuente | requiere decisión · 037/038 |
| Política de diferencia cambiaria para aplicar entre monedas | 013 · 038 |
| `FiscalNumberSeries.document_type` sin catálogo canónico | 042 |
| Qué impuesto espera la conciliación triple de la orden de compra | 027 |
| Selector de almacén truncado en ocho pantallas | organización / 008 |

## 11. Estado resultante

| | |
|---|---|
| Spec 037 | **COMPLETE / CONVERGED** (técnica y funcional) |
| Spec 028 | `PARTIALLY_IMPLEMENTED` · con su delta monetario convergido |
| Spec 034 · 042 | con sus deltas dirigidos convergidos y verificados |
