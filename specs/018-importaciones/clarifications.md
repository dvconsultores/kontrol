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
