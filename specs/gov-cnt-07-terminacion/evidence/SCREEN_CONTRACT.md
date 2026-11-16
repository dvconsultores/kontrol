# CNT-07 · Ficha de pantalla

## Rutas

| Pantalla | Ruta | Cómo se llega | Permiso |
|---|---|---|---|
| Terminación, resolución o rescisión | `/gobierno/contratos/:contratoId/terminacion` | Gobierno · Contratos › **Contratos y órdenes** › contrato formalizado › enlace **Terminación / resolución / rescisión** (junto a «Ejecución del contrato») | Consultar: `gobierno_contratos:view`. Preparar, descartar y formalizar: `gobierno_contratos:terminate` (SENSITIVE, MFA) |

## Secciones (cada una con su `h2`)

| N.º | Sección | Contenido |
|---|---|---|
| 1 | Situación actual | Vigente o Extinguido (en texto), figura, «Eficaz desde», «Hechos de ejecución admitidos hasta», alerta `role="alert"` si el acto base se revocó o se declaró nulo, y la nota de cumplimiento por CNT-03 |
| 2 | Actuación formalizada | Código, figura, causal y cláusula, hechos, fundamento jurídico, acto decisorio (enlace), apertura, documento del acuerdo, conclusión autorizada, fecha del acto, fecha de eficacia, registro (instante con hora) y huella abreviada |
| 3 | Preparar la actuación | Selector «Figura jurídica» con el catálogo cerrado de la LCP art. 145 y botón «Preparar» |
| 4 | Actuación en preparación | Figura, causal (filtrada por figura), cláusula del contrato, hechos, fundamento jurídico, acto decisorio, acto de apertura (imputable), documento del acuerdo (mutuo acuerdo) y conclusión autorizada (rescisiones). Lista de requisitos «Cumplido / Pendiente». «Guardar borrador», «Descartar borrador» y «Formalizar» con confirmación fuerte |
| 5 | Notificaciones del acto | Tabla DOC-04 (contratista o garante, estado y fecha) con enlace a cada notificación |
| 6 | Consecuencias de ejecución y financieras | Monto vigente, valuado conformado y presentado, saldo no ejecutado, saldo por valuar (CNT-03), facturado conforme, recepciones, estado de la ejecución, indemnización (solo la regla, sin cálculo), compromisos BUD-08 y la nota de que no hay efectos |
| 7 | Garantías | PROC-10: referencia, tipo, emisor, monto, estado y vigencia, con enlace «Ir a PROC-10» |
| 8 | Obligaciones pendientes | LCP 51 (desempeño al SNC), LCP 8 (publicación en el SNC), revisar BUD-08 y revisar PROC-10 |
| 9 | Registro de terminaciones | Filtros por figura y fechas de eficacia, y «Descargar CSV» |

**Confirmación.** Muestra contrato, contratista, figura, causal, fecha de eficacia, acto y saldo contractual no ejecutado, con la advertencia: «Esta actuación modifica la situación jurídica del contrato y no se puede editar después de formalizarse.»

**Accesibilidad.** Las tablas son regiones desplazables enfocables con `aria-label`; el estado no depende del color. Sin desbordamiento horizontal a 1280, 390 y 320 px.

## Otras pantallas

- **Ficha del contrato (CNT-01):** enlace a la terminación y, en la cabecera, « · Extinguido (figura)» cuando corresponde.
- **Expediente contractual (CNT-08):** nueva sección 10 «Terminación / resolución / rescisión» (15 secciones en total), con la situación, la actuación y el enlace a la pantalla dueña. CNT-07 sale de «Otras fuentes del expediente» y entra en la cronología y en el paquete.
