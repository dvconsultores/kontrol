# CTL-07 · Alertas de operaciones atípicas (GOV-CTL-009)

- **Proceso:** CTL-07 · P1 · Control Interno.
- **Requisito literal (IR v1.0, GOV-CTL-009, N23/N20, P1):** «Emitir alertas de operaciones atipicas: duplicidad, fraccionamiento, autoaprobacion, proveedor relacionado u override frecuente, sin acusacion automatica.»
- **Fuentes:** `FUENTES.md`. **Decisiones:** `DECISIONES.md`. **Pantalla:** `SCREEN_CONTRACT.md`.
- **Selección:** la ruta B del encargo. CTL-03 ya está en OWNER_UAT_READY (cierre 2026-11-11, publicado en `011cf82`). Ningún P0 es elegible sin solapar BUD-05 (`plan.md` §1).

## Qué hace el usuario

Control Interno abre **Gobierno → Alertas de operaciones atípicas** y ve:
- las señales que KONTROL detecta sobre operaciones reales del ente;
- por qué se emitió cada una y sobre qué objetos;
- los tipos que el producto todavía no puede detectar, con el motivo y lo que haría falta.

Cada alerta se **revisa** («Sin observación» o «Requiere seguimiento», con observación). La revisión queda inmutable y auditada. Para seguimiento, la pantalla lleva a registrar un hallazgo (CTL-06, ya existente).

Una alerta **no es una acusación**: no cambia el estado de nada, no bloquea a nadie y no se presenta como conclusión.

## Requisitos funcionales

| ID | Requisito |
|---|---|
| CTL07-FR-01 | Detectar **duplicidad**: dos expedientes de contratación (PROC-03) no descartados, de la misma unidad y con el mismo objeto normalizado. Se emite una alerta por par |
| CTL07-FR-02 | Detectar **proveedor relacionado**: una oferta (PROC-06) cuyo documento de oferente coincide con el documento de un funcionario del mismo ente (ORG-04). El documento del funcionario se muestra enmascarado |
| CTL07-FR-03 | Detectar **autoaprobación**: los intentos bloqueados de autoaprobación o de funciones incompatibles, tal como la SoD los registró (`GOV_SOD_CONFLICT_BLOCKED` de CTL-01 y `GOV_SOD_ROLE_CONFLICT_BLOCKED` de PROC-11) |
| CTL07-FR-04 | **Fraccionamiento** y **override frecuente** figuran en el catálogo como «No disponible», con el motivo y el requisito habilitante. No se emite ninguna alerta inventada |
| CTL07-FR-05 | Cada alerta tiene clave estable, tipo, fecha, título, detalle, sujetos con etiquetas humanas (sin UUID) y estado `PENDIENTE` o `REVISADA` |
| CTL07-FR-06 | Revisar una alerta: resultado `SIN_OBSERVACION` o `REQUIERE_SEGUIMIENTO` y observación obligatoria (10 a 2000 caracteres). Una sola revisión por alerta, inmutable, con el resumen que se vio al revisar |
| CTL07-FR-07 | Nadie revisa una alerta de la que es sujeto: el funcionario vinculado al usuario en proveedor relacionado, o el usuario del intento en autoaprobación |
| CTL07-FR-08 | Filtros por tipo y por estado. Recuentos por tipo (total y pendientes) |
| CTL07-FR-09 | Aviso permanente: «Una alerta es una señal para revisar; no es una acusación ni una conclusión.» |

## Criterios de aceptación

| ID | Criterio |
|---|---|
| CTL07-AC-01 | Con dos expedientes «Adquisición de papelería» de la misma unidad aparece una alerta de duplicidad. Un tercero descartado, o uno de otra unidad, no la genera |
| CTL07-AC-02 | Una oferta con documento `v-12345678` (normalizado `V12345678`, con la regla de PROC-06: mayúsculas, sin espacios ni guiones) y un funcionario `V` `12345678` generan una alerta de proveedor relacionado, con el documento enmascarado (`V-******78`) |
| CTL07-AC-03 | Un conflicto SoD bloqueado aparece como alerta de autoaprobación, con usuario, regla o función y fecha |
| CTL07-AC-04 | Fraccionamiento y override frecuente: `disponible=false`, con el motivo y el requisito; ninguna alerta de esos tipos |
| CTL07-AC-05 | Revisar sin la capacidad da 403. Con una clave inexistente, 404 `GOV_ALERT_NOT_FOUND`. Revisar dos veces, 409 `GOV_ALERT_ALREADY_REVIEWED`. Revisarse a uno mismo, 409 `GOV_ALERT_SELF_REVIEW`. Con observación corta o resultado inválido, 422. Ningún rechazo escribe nada |
| CTL07-AC-06 | Una revisión válida emite `GOV_ATYPICAL_ALERT_REVIEWED` y la alerta pasa a `REVISADA` con quién, cuándo, resultado y observación |
| CTL07-AC-07 | Otra empresa no ve las alertas ni las revisiones de A, y revisar una clave de A desde B da 404 |
| CTL07-AC-08 | De dos revisiones simultáneas de la misma alerta queda una sola fila; la otra recibe 409 |
| CTL07-AC-09 | La revisión no se puede modificar ni borrar en PostgreSQL (disparador `GOV_ATYPICAL_ALERT_REVIEW_IMMUTABLE`) |
| CTL07-AC-10 | La pantalla funciona a 1280, 390 y 320 sin desplazamiento horizontal y con `AXE_NEW_SERIOUS=0` |

## Fuera de alcance

- Detección de fraccionamiento sin monto: sería una conjetura.
- Crear overrides para luego contarlos.
- Notificaciones push.
- Puntuación de riesgo o perfilado de personas.
- Cambiar CTL-01, PROC-11, PROC-03, PROC-06 o CTL-06.
- BUD-05 (P1).
