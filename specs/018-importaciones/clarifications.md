# Spec 018 · aclaraciones

Decisiones de diseño de Claude cuando la fuente no fija el detalle. Son reversibles y quedan para revisión de la dueña.

| Id | Pregunta | Decisión | Motivo |
|---|---|---|---|
| CL-018-01 | ¿Qué estados tiene el proceso? | Los de `IMPORT_STATE_MACHINE_CONTRACT` en `plan.md` | Ningún volumen los define; se derivan de los pasos del DOCX |
| CL-018-02 | ¿Dónde viven precio y cantidad negociados? | En la orden de compra | El Volumen 3 los ubica allí; evita dos fuentes de verdad |
| CL-018-03 | ¿Puede abrirse sin orden? | Sí | El DOCX negocia (paso 6) antes de emitir la orden (paso 7) |
| CL-018-04 | ¿Se exige proveedor aprobado para abrir? | No: rol y activo | La aprobación gobierna el pago, según el Volumen 4 pantalla 8, y una negociación es previa |
| CL-018-05 | ¿Qué documentos son obligatorios? | Proforma, packing list y embarque; certificados añadibles | El DOCX dice «certificados o soportes requeridos»: dependen de la mercancía |
| CL-018-06 | ¿Quién valida? | `compras:approve`, separado del alta `compras:create` | Control crítico «Control documental de importación» |
| CL-018-07 | ¿INCOTERM? | Lista cerrada Incoterms 2020 | Evita texto libre en una condición contractual |
| CL-018-08 | ¿La documentación precede al seguimiento? | No: conviven desde ORDERED | El DOCX los enumera, sin dependencia; el documento de embarque nace al embarcar. Corrige el ciclo 1 |
| CL-018-09 | ¿Qué es un agente? | Un `Party` activo, sin rol nuevo | La Spec 002 no define el rol y el DOCX solo lo nombra en IMP-12 |
| CL-018-10 | ¿Reutilizar `ReceiptIncident`? | No | Exige recepción; antes del arribo no existe |
| CL-018-11 | ¿Una corrección abierta bloquea? | Bloquea confirmar la documentación; tras el despacho no revierte | «Documentación completa» es falso con una corrección abierta; el despacho físico ya ocurrió |
| CL-018-12 | ¿El expediente crea pagos? | Sí, llamando a CxP, y vincula existentes; aprobar y ejecutar siguen en CxP | «Ejecutar anticipo o pago» sin segundo libro ni segunda puerta |
| CL-018-13 | ¿Qué órdenes se ofrecen? | Búsqueda en servidor de aprobadas, mismo proveedor y moneda, no usadas | Elimina el límite de 100 |
| CL-018-14 | ¿Cómo se liga la recepción al expediente? | Derivada de `GoodsReceipt.order_id`, sin clave nueva | La orden pertenece a un solo expediente |
| CL-018-15 | ¿Corrección o incidencia? | `PRE_DISPATCH_CORRECTION` en `import_corrections`; `POST_ARRIVAL_RECEIPT_INCIDENT` en `ReceiptIncident`. Un mismo hecho no va a las dos | Documental y de proceso frente a mercancía recibida. Una corrección sigue pudiendo abrirse tras despachar por un documento, sin revertir el estado |
| CL-018-16 | `PAYMENT_DRAFT_PERMISSION_CONTRACT` | `compras.create` crea el borrador; `compras.approve` hace la transición; sin ninguno de los dos, 403 | Crear no es aprobar ni ejecutar. Observar un borrador sin permiso de aprobación no es defecto. Protegido por prueba |
