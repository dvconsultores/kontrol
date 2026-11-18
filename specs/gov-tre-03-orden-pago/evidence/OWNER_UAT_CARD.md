# Tarjeta de prueba de la dueña · TRE-03 · Orden de pago

- **Dónde:** Gobierno · Tesorería › **Órdenes de pago** y **Políticas de órdenes de pago** (menú lateral; solo con el perfil KONTROL Gobierno o mixto).
- **Quién:**
  - **Consultar:** permiso de órdenes de pago «ver».
  - **Configurar políticas y numeración:** permiso «políticas». Activar y cerrar piden fundamento o motivo y MFA. El acto administrativo es opcional.
  - **Preparar borradores:** permiso «gestionar».
  - **Emitir:** permiso «emitir». Pide MFA.
  - **Anular:** permiso «anular». Pide MFA.
  - **Autoridad:** un cargo con la competencia **Ordenar pago × Tesorería** vigente en la fecha de la orden (ORG-03). Nunca un nombre de cargo fijo. El ente decide qué cargo la tiene.

## Preparación (datos sintéticos)

1. Un ejercicio **aprobado** con uno o más **causados formalizados** (BUD-09), del mismo beneficiario y moneda. Por ejemplo, A = 100.00, B = 200.00 y C = 300.00.
2. Un cargo activo con la competencia Ordenar pago × Tesorería.
3. Un tipo documental del ente y al menos un documento de ese tipo en el ejercicio. Es el que la política exigirá.
4. Para el recorrido G: acceso a **Segregación de funciones** (CTL-01).

## A · Política

| N.º | Acción | Resultado esperado |
|---|---|---|
| A1 | **Políticas de órdenes de pago** | Lista vacía: título «Aún no hay políticas de orden de pago» y debajo «El producto no trae ninguna precargada.» |
| A2 | **Nueva política**: código, nombre, «Vigente desde», tipo de regla, fundamento | La competencia aparece fija, en un campo deshabilitado: «ORDENAR_PAGO · TESORERIA» |
| A3 | **Añadir documento**: elige el tipo del ente y marca **Obligatorio**. Pulsa **Guardar** | Ficha de la política en **Borrador** |
| A4 | **Activar**, escribe un fundamento de al menos 20 caracteres y confirma (MFA) | Estado **Vigente**. Ya no se edita |
| A5 | Revisa **Historia** | Eventos de creación y activación, con fecha y actor |

## B · Numeración

| N.º | Acción | Resultado esperado |
|---|---|---|
| B1 | En **Políticas de órdenes de pago**, sección «Numeración de órdenes de pago», escribe un patrón, p. ej. `OP-{ANIO}-{NUMERO:4}` | Ayuda «Variables admitidas: {ANIO}, {NUMERO:n}» |
| B2 | **Guardar patrón** | «Ejemplo: OP-<año>-0001». Un patrón sin `{NUMERO:n}` se rechaza junto al campo |

## C · Orden simple, parcial

| N.º | Acción | Resultado esperado |
|---|---|---|
| C1 | **Órdenes de pago** (se abre en el ejercicio aprobado más reciente; con varios, elígelo) | Lista vacía: «Aún no hay órdenes de pago en este ejercicio» |
| C2 | **Nueva orden de pago** › marca el causado A | La tabla muestra causado, ordenado y pendiente. El monto se prellena con el pendiente (100.00) |
| C3 | Cambia el monto a 60.00 | «Pendiente tras esta orden»: 40.00. «TOTAL DE LA ORDEN»: 60.00 |
| C4 | Elige la política, escribe el concepto, elige el cargo que ordena el pago, **sin** marcar documento. Pulsa **Guardar borrador** | Detalle «Borrador de orden de pago» |
| C5 | Abre el causado A en **Presupuesto › Causados** | El borrador **no consume**: pendiente de orden de pago 100.00 |
| C6 | En el detalle de la orden, revisa **Controles** | «Documentos · Falta · Faltan documentos obligatorios: <tipo>». **Emitir orden de pago** deshabilitado. «Segregación de funciones — Se verifica al emitir (CTL-01)» |
| C7 | **Editar**, marca el documento de soporte y guarda | Todos los controles en **Cumple**. Emitir habilitado |
| C8 | **Emitir orden de pago** y confirma (MFA) | Código según el patrón (`OP-<año>-0001`), estado **Emitida**, «Siguiente paso: Pago (TRE-04)» |
| C9 | Revisa el causado A | «Pendiente de orden de pago: 40.00 <moneda>» (la emitida **consume** 60.00) |
| C10 | Revisa **Líneas** e **Historia** de la orden | Línea del causado A con 60.00. Eventos de borrador y emisión |
| C11 | En la lista, **Descargar CSV** con un filtro de estado | El CSV trae las órdenes con el filtro aplicado |

## D · Multicausado y varias órdenes

| N.º | Acción | Resultado esperado |
|---|---|---|
| D1 | **Nueva orden de pago** › marca B y C. Montos 80.00 y 120.00 | Pendiente tras la orden: 120.00 y 180.00. Total 200.00. Sin avisos de beneficiario ni moneda |
| D2 | Guarda, emite (MFA) y revisa las líneas | Una sola orden con dos líneas. B queda con 120.00 pendiente y C con 180.00 |
| D3 | Prepara y emite otra orden de 30.00 sobre el causado A | A queda con 10.00 pendiente (60.00 + 30.00 ordenado) |

## E · Sobreorden

| N.º | Acción | Resultado esperado |
|---|---|---|
| E1 | Nueva orden sobre A con 11.00 (pendiente 10.00) | «Supera el pendiente de la línea» y **Guardar borrador** deshabilitado |
| E2 | Prepara dos borradores de 10.00 sobre A y emite uno | El segundo muestra en Controles «Saldo disponible · Falta · Saldo insuficiente en: <causado> (pendiente 0.00)» y no se puede emitir. El sistema lo rechaza aunque se intente por otra vía |

## F · Documentos

| N.º | Acción | Resultado esperado |
|---|---|---|
| F1 | Sin el documento exigido (C6) | No se puede emitir |
| F2 | Con el documento exigido (C7) | Se puede emitir |

## G · Segregación de funciones (CTL-01)

| N.º | Acción | Resultado esperado |
|---|---|---|
| G1 | En **Segregación de funciones**, crea y activa una regla del proceso «Orden de pago»: «Formalizar el causado» frente a «Emitir una orden de pago del causado» | Regla vigente |
| G2 | Con el **mismo usuario que formalizó** un causado, intenta emitir una orden de ese causado | Rechazo. En Controles aparece «Bloqueado» con el motivo de la regla. La orden sigue en borrador. El bloqueo queda registrado en la bitácora |

## H · Anulación

| N.º | Acción | Resultado esperado |
|---|---|---|
| H1 | En una orden emitida, **Anular**, motivo de al menos 10 caracteres, cargo que anula, confirma (MFA) | Estado **Anulada**, con motivo y fecha. La orden no se borra |
| H2 | Revisa el causado | El pendiente vuelve al valor anterior a la orden (se **restaura**) |

## Fuera de alcance

- Pago, retenciones y contabilidad (TRE-04, TRE-05, ACC-*): la orden emitida solo muestra «Siguiente paso: Pago (TRE-04)».
- Vista previa de la segregación de funciones antes de emitir. La decide CTL-01 al emitir; no hay un evaluador paralelo.
