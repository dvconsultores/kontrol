# Contrato de pantalla · CNT-04

**Ruta:** `/gobierno/contratos/{id}`. Es la ficha CNT-01: la sección solo aparece con el contrato FORMALIZADO y no añade entradas de menú.

| Elemento | Detalle |
|---|---|
| Sección | `<section aria-labelledby="supervision-titulo">`, h2 «Supervisor / responsable del contrato» |
| Vigente | h3 «Supervisor vigente» + `dl`: Funcionario (nombre · documento enmascarado), Cargo (código · nombre), Unidad, Figura, Desde, Acto de designación, Emitido por, Designación (SUP-NN · estado) |
| Sin vigente | EmptyState «Sin supervisor designado» |
| Programada | h3 «Designación programada»: funcionario · cargo · desde · referencia |
| Historial | región desplazable «Historial de supervisores» (tabla con caption): Designación, Funcionario, Cargo, Unidad, Acto, Desde, Hasta, Estado (situación · estado), Motivo |
| Acción | botón «Nueva designación» o «Sustituir supervisor»; solo con `gobierno_contratos:assign_supervisor` |
| Formulario | Fecha efectiva (date), Funcionario (select), Ocupación (select derivado; si hay una sola, se elige sola) + «Cargo: … · Unidad: …», Acto de designación (select), Motivo del cambio (solo al sustituir; máximo 500). Todos obligatorios |
| Confirmación | ConfirmationDialog «Formalizar la designación del supervisor» (MFA por la política SENSITIVE) |
| Mensajes | éxito con role="status" «Designación SUP-NN registrada.»; error con role="alert" y el mensaje de la API |
| Sin opciones | textos informativos cuando no hay funcionarios o actos elegibles |
| Responsive | 1280, 390 y 320 px sin desbordamiento horizontal; tabla en una región desplazable con tabIndex |
| Accesibilidad | Axe sin violaciones serias ni críticas (E2E a 1280 y, en el bucle común, a 390 y 320) |
