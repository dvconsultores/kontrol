# Tarjeta de prueba de la dueña · TRE-04 · Pago con maker-checker

- **Dónde:** Gobierno · Tesorería › **Pagos** y **Políticas de pago** (menú lateral; perfil KONTROL Gobierno o mixto).
- **Quién:**
  - **Consultar:** permiso de pagos «ver».
  - **Configurar medios, políticas y numeración:** permiso «políticas». Activar y cerrar una política piden fundamento o motivo y MFA.
  - **Preparar y enviar (maker):** permiso «gestionar».
  - **Autorizar o rechazar (checker):** permiso «autorizar». Pide MFA. El checker es **otra persona**: quien preparó o envió el pago nunca lo autoriza.
  - **Registrar el pago ejecutado:** permiso «ejecutar». Pide MFA.
  - **Anular antes de ejecutar:** permiso «anular». Pide MFA.
- **Autoridad del checker:** un cargo con la competencia que pida la banda (por ejemplo **Pagar × Tesorería**) vigente hoy (ORG-03), con su ocupación, encargaduría o suplencia (ORG-04/ORG-06). Nunca un nombre de cargo fijo.
- **Qué significa «registrar»:** KONTROL **no envía nada al banco**. Registra un pago que la Tesorería ya ejecutó por el medio indicado: fecha valor, referencia y soportes.

## Preparación (datos sintéticos)

1. Una **orden de pago emitida** (TRE-03), por ejemplo de 100.00, y otra de 300.00 para el recorrido G.
2. Una **cuenta bancaria vigente** (TRE-01) en la moneda de la orden.
3. Dos usuarios checker con permiso «autorizar» y un cargo cada uno con Pagar × Tesorería. Para G, un tercer cargo con Firmar × Tesorería.

## A · Política y medios

| N.º | Acción | Resultado esperado |
|---|---|---|
| A1 | **Políticas de pago** | Secciones Políticas, Medios de pago y Numeración. Texto: «KONTROL no trae medios precargados: cada ente registra los que tiene autorizados.» |
| A2 | Crea un **medio de pago**: código, nombre, vigente desde, «exige referencia», «referencia única» y fundamento | Aparece en la tabla de medios como Activo |
| A3 | **Nueva política**: código, nombre, moneda, medio permitido, pago parcial sí o no, control de duplicado, fundamento. Revisa la **banda**: desde 0, sin tope, requisito Pagar × Tesorería × 1 | Guardada en **Borrador** |
| A4 | **Añadir banda** | La nueva banda empieza donde termina la anterior. La ayuda explica que las cifras las define el ente |
| A5 | Añade un **documento** exigido en la etapa Preparar (opcional) | Queda en la lista de documentos de la política |
| A6 | **Activar** con un fundamento de al menos 20 caracteres (MFA) | Estado **Vigente**. Ya no se edita |

## B · Pago parcial

| N.º | Acción | Resultado esperado |
|---|---|---|
| B1 | **Pagos › Nuevo pago**: elige la orden de 100 | Ves Ordenado 100.00, Pagado 0.00, En trámite 0.00, Pendiente 100.00 y Disponible 100.00 |
| B2 | Política, cuenta, medio y monto 40.00 → **Guardar borrador** | Detalle en **Borrador**. «La regla se congela al enviar.» El saldo de la orden no cambia: el borrador no consume |
| B3 | **Enviar a autorización** | **Pendiente de autorización**, con código asignado. En trámite 40.00; Disponible 60.00. La regla queda congelada (banda y requisitos) |
| B4 | Con el **checker**: **Aprobar**, elige el cargo y el requisito, y confirma (MFA) | **Autorizado**, «1 de 1» |
| B5 | Con el maker: **Registrar pago ejecutado**, con fecha valor y referencia, y confirma (MFA) | **Pago registrado**. La orden queda con Pagado 40.00 y Pendiente 60.00 |
| B6 | Revisa **Historia** y **Qué sigue** | Eventos CREADO, ENVIADO, AUTORIZADO y REGISTRADO. Fronteras TRE-05, TRE-06, TRE-07 y ACC |

## C · Maker-checker

| N.º | Acción | Resultado esperado |
|---|---|---|
| C1 | Un usuario con «gestionar» y «autorizar» prepara y envía un pago, e intenta **Aprobar**lo él mismo | Rechazo: «Quien preparó o envió el pago no puede autorizarlo». El pago sigue pendiente |

## D · Varios pagos

| N.º | Acción | Resultado esperado |
|---|---|---|
| D1 | Sobre una orden de 100, con una política con control de duplicado «Advertir»: pagos de 40, 30 y 30 | El segundo de 30 pide **confirmar con motivo** (mismo importe). Al registrar los tres: Pagado 100.00 y Pendiente 0.00 |

## E · Sobrepago

| N.º | Acción | Resultado esperado |
|---|---|---|
| E1 | Con 70 registrados sobre 100, prepara un pago de 31 y envíalo | Rechazo: el monto supera el disponible (30.00). Con 30 sí se envía |

## F · Referencia duplicada

| N.º | Acción | Resultado esperado |
|---|---|---|
| F1 | Con un medio de referencia única, registra un pago con la referencia «REF-1» | Pago registrado |
| F2 | En otro pago con el mismo medio, registra «ref-1» | Rechazo: la referencia ya fue registrada |

## G · Banda según el monto

| N.º | Acción | Resultado esperado |
|---|---|---|
| G1 | Política con dos bandas: de 0 a 100 con Pagar × 1, y de 100 sin tope con Pagar × 1 + Firmar × 1 | — |
| G2 | Pago de 50 enviado | Exige **1** autorización (banda 1) |
| G3 | Pago de 150 enviado | Exige **2** autorizaciones (banda 2). Un cargo con Pagar no cubre el requisito Firmar. Con el cargo Firmar de otro checker: **Autorizado** |

## H · Versión de la política

| N.º | Acción | Resultado esperado |
|---|---|---|
| H1 | Envía un pago A con la política v1 | Regla congelada v1 |
| H2 | **Nueva versión** de la política, cambia la fecha de vigencia a hoy y **Activar** | v2 Vigente; v1 Cerrada («Sustituida por la versión 2») |
| H3 | Aprueba y registra el pago A | Sigue con la regla v1 |
| H4 | Prepara y envía un pago B | Usa la regla v2 |

## Qué no hace TRE-04 (fronteras)

- **Banco:** no envía el pago al banco ni se conecta con él.
- **Reverso:** no reversa pagos ejecutados (TRE-07).
- **Otros procesos:** no calcula retenciones (TRE-05), no concilia (TRE-06) y no contabiliza (ACC).

`OWNER_ACCEPTED`: lo concede solo la dueña.
