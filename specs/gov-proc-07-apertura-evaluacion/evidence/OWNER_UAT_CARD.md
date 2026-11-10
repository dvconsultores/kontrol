# OWNER UAT CARD · PROC-07 «Apertura y evaluación de ofertas» (GOV-PROC-008, GOV-PROC-009)

```
MÓDULO: Gobierno · PROCESO: PROC-07 Apertura y evaluación
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
COMMIT: 4c4be3d (develop)

MENÚ: Gobierno · Contrataciones › Expedientes › (abrir un expediente) › sección «Apertura y evaluación»

ROLES A USAR:
  - Capacidad gobierno_evaluacion: view (ver), criteria (matriz), open (abrir ofertas), evaluate (aportes,
    resultados y conclusión). En la base de QA, el administrador «con todo» las tiene.
  - Con la exigencia de identidad de ORG-06 activa, quien abre o evalúa debe ser el funcionario miembro.

QUÉ ES Y QUÉ NO ES:
  La Comisión fija la matriz del pliego, abre en acto las ofertas recibidas (con quórum y acta), cada miembro
  registra su aporte por criterio y la Comisión registra su resultado por criterio y concluye.
  NO recomienda, NO adjudica, NO declara desierto (eso es PROC-08). El resultado de la Comisión NO es un promedio.

USE SOLO DATOS SINTÉTICOS.

PRECONDICIONES:
  - Expediente en curso, con comisión vigente vinculada (PROC-02): miembros principales con voto, suplentes y
    secretaría.
  - Un documento del pliego vinculado al expediente, y la matriz registrada ANTES de recibir la primera oferta.
  - Al menos una oferta recibida y sellada (PROC-06) y la recepción concluida.
  - Un documento para el acta de apertura, vinculado al expediente.

PASOS Y RESULTADO ESPERADO:
  1. Abra el expediente desde el menú.
  2. Baje a «Apertura y evaluación».
  3. En «Estado», «Recepción de ofertas» dice «Concluida · <fecha>».
  4. En «Matriz de evaluación» ve los grupos Técnico, Económico y Legal con sus criterios.
  5. Pulse «Bloquear matriz» y «Confirmar bloqueo»: ve «Matriz bloqueada»; ya no hay botones «Quitar».
  6. En «Ofertas», la oferta dice «Sellada hasta la apertura» y no tiene «Ver documentos».
  7. Pulse «Registrar apertura», marque la oferta y los asistentes.
  8. Con un solo miembro con voto ve «Sin quórum»; si confirma, el sistema lo rechaza. Marque la mayoría:
     ve «Hay quórum» (la secretaría asiste pero no vota).
  9. Elija el acta en «Acta de apertura».
 10. Pulse «Abrir ofertas» y «Confirmar apertura»: ve «Ofertas abiertas».
 11. La oferta dice «Abierta» y «Confidencialidad: Sello levantado en la apertura». La tarjeta A-01 muestra
     «Registrada por», el quórum («3 de 3 miembros con voto (requerido 2)»), los asistentes y el acta.
 12. Pulse «Ver documentos de O-01» y abra el documento: ahora se puede leer.
 13. En «Evaluación», criterio técnico: «Registrar aporte», elija el evaluador, escriba un puntaje
     (dos decimales, hasta el máximo) y «Guardar aporte».
 14. Haga lo mismo en el criterio económico.
 15. En el criterio legal elija «Cumple» o «No cumple».
 16. Cada aporte muestra el evaluador, el valor y «Vigente».
 17. Registre otro aporte del mismo evaluador en el mismo criterio: el nuevo queda «Vigente» y en
     «Historial (1)» se conserva el anterior con su valor y fecha. Nada se sobrescribe.
 18. En cada criterio: «Registrar resultado de la Comisión», valor y «Guardar resultado». Los aportes siguen
     visibles; el resultado no es su promedio. Ve «3 de 3 resultados de la Comisión registrados».
 19. Pulse «Concluir evaluación» y «Confirmar conclusión»: ve «Evaluación concluida · <fecha>» y desaparecen
     los botones de aporte y resultado.
 20. En «Cronología»: «Matriz de evaluación bloqueada», «Apertura A-01: 1 oferta(s)», «Evaluación concluida».
 21. No hay ningún botón «Adjudicar» ni «Declarar desierta»: la siguiente acción dice «pendiente de
     recomendación (PROC-08)».

NEGATIVAS:
  - Criterio nuevo tras el bloqueo: se rechaza.
  - Documento de una oferta antes de la apertura: «no encontrado».
  - Abrir dos veces la misma oferta: se rechaza.
  - Apertura con fecha anterior a la conclusión de la recepción o futura: se rechaza (se admite el mismo minuto).
  - Usuario de otro ente o sin la capacidad: no ve la evaluación.

LÍMITES CONOCIDOS:
  - Sin reporte propio de la evaluación: el informe es la recomendación de PROC-08.
  - Sin cambio motivado de criterios (decisión de la dueña; la vía legal es la reposición).
  - Teléfono: comprobado a 390 y 320 px.
```
