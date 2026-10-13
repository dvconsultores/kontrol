# Estrategia para `approvals.spec.ts`

`APPROVALS_STRATEGY = LOCAL_SHARED_PRIMITIVE`. La copia local de `activarEmpresa` en approvals difiere del ayudante canónico
en la compuerta (resuelve el código de la empresa por API y usa `elegir-empresa-<código>` exacto) y en que con la empresa ya
activa **no cambia** de empresa (el canónico, con `codigo`, sí la cambia): no son el mismo contrato, así que no se sustituye
una por otra. Lo que sí se comparte es la sincronización: approvals importa `esperarEstadoDeEmpresa` (y la sonda
`emitirLaTablaTarde` para su prueba HE-11) de `e2e/helpers/empresa.ts`, decide con la lectura devuelta y conserva su
propia compuerta, su diagnóstico y su postcondición. Ficheros: `e2e/approvals.spec.ts` (función local `activarEmpresa` y una
prueba nueva). Sin refactor de suites. Las copias reducidas de `documents.spec.ts`/`documents-a11y.spec.ts` (pulsan «Activar»
solo si lo ven; no deciden por estado) quedan anotadas (delta §11), fuera de FR-HE-019.
