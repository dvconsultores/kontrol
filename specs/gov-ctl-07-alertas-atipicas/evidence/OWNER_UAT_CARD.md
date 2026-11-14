# Tarjeta de prueba de la dueña · CTL-07 · Alertas de operaciones atípicas

- **Dónde:** Menú › Gobierno › **Alertas de operaciones atípicas**.
- **Quién:** un usuario de Control Interno con «Alertas de operaciones atípicas: ver» y «revisar». Revisar pide MFA.
- **Qué demuestra:** KONTROL señala operaciones atípicas reales sin acusar a nadie, y Control Interno deja una revisión inmutable y auditada.

## Preparación (una vez)

1. Con un usuario de contrataciones, registra dos expedientes de la **misma unidad** con el **mismo objeto**; por ejemplo, «Adquisición de papelería» y « adquisicion de PAPELERÍA ».
2. Registra un funcionario y, en un expediente, recibe una oferta cuyo documento de oferente sea **el mismo** que el del funcionario (por ejemplo, `V-12345678` para el funcionario V 12345678).
3. En **Gobierno › Funciones incompatibles**, activa la regla «Solicitante ≠ Receptor de ofertas». Después, con el usuario que registró el expediente, intenta recibir otra oferta en él: el sistema lo bloquea.

## Pasos

| N.º | Acción | Resultado esperado |
|---|---|---|
| 1 | Abre la pantalla | Aviso: «Una alerta es una señal para revisar; no es una acusación ni una conclusión.» |
| 2 | Mira la tabla «Tipos de alerta» | Duplicidad, Proveedor relacionado y Autoaprobación aparecen como **Disponible**. Fraccionamiento y Override frecuente aparecen como **No disponible**, con el motivo y lo que haría falta |
| 3 | Busca la alerta de duplicidad | Título «Expedientes X y Y con el mismo objeto», con la unidad y el objeto. No hay códigos internos |
| 4 | Busca la de proveedor relacionado | Muestra el oferente, el expediente y la oferta. El documento del funcionario aparece **enmascarado** (`V-******78`), nunca completo |
| 5 | Busca la de autoaprobación | «Intento bloqueado por funciones incompatibles», con el usuario, la regla y el expediente |
| 6 | Entra como el usuario que provocó el intento | En su alerta dice «No puede revisar esta alerta porque es sujeto de ella.» y no hay botón «Revisar» |
| 7 | Con otro usuario de Control Interno, pulsa «Revisar» en la duplicidad | Formulario con Resultado (Sin observación / Requiere seguimiento) y Observación. El botón «Registrar revisión» se activa a partir de 10 caracteres |
| 8 | Registra «Sin observación» con una observación | «Revisión registrada». La alerta pasa a **Revisada**, con quién, cuándo y la observación |
| 9 | Revisa la autoaprobación con «Requiere seguimiento» | Aparece el enlace **Registrar hallazgo**, que lleva al alta de hallazgos (CTL-06) |
| 10 | Filtra por Estado = Revisadas | Solo quedan las revisadas |
| 11 | Descarta uno de los dos expedientes duplicados (PROC-03) y vuelve | La revisión sigue visible como «Revisada · Ya no se detecta.» |
| 12 | Abre la bitácora institucional o la auditoría | Aparece el evento «Alerta de operación atípica revisada». Como proceso se ve el código técnico «gov-ctl-07», no un nombre: es la deuda declarada GOV-AUDIT-PROCESS-LABELS, que comparte con BUD-01..04 |
| 13 | Prueba en el móvil (390 o 320 px) | Sin desplazamiento horizontal; la tabla se desplaza dentro de su recuadro |

## Límites declarados (no son fallos)

- **Fraccionamiento:** no está disponible porque las ofertas y las adjudicaciones no registran monto (OBS-PROC08-MONTO-01), y los umbrales en U.T. dependen de N38, de clase C.
- **Override frecuente:** no está disponible porque Gobierno no admite excepciones a la SoD ni al techo de autoridad.
- **Proveedor relacionado:** solo detecta la coincidencia de documento de identidad. El parentesco y la participación societaria requieren el maestro de proveedores (D-GOV-03).
- **La revisión es única e inmutable.** El seguimiento real se hace como hallazgo (CTL-06).

`OWNER_ACCEPTED`: NO. Solo la dueña lo concede.
