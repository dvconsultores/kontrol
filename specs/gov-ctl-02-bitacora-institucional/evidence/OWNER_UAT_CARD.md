# OWNER UAT CARD · GOV-CTL-02 · CTL-02 «Bitácora institucional append-only con actor, autoridad, unidad y correlación» (GOV-CTL-002, GOV-CTL-003)

```
MÓDULO: Gobierno · PROCESO: CTL-02 Bitácora institucional
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Gobierno › Bitácora institucional (/gobierno/bitacora). Cada fila abre el detalle del evento.

ROLES A USAR:
  - Consulta: gobierno_auditoria:view. Es de solo lectura.
  - Para generar eventos: una cuenta vinculada en Identidad institucional, con ocupación vigente y permisos
    de algún proceso, por ejemplo gobierno_ocupacion:manage.
  - Negativas: un usuario sin esa capacidad; un usuario de otro ente.
  En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) la tiene.

QUÉ ES Y QUÉ NO ES:
  Responde quién operó técnicamente, a qué funcionario representaba, qué cargo ejercía, en qué unidad y ente,
  con qué autoridad, desde qué sesión e IP, cuándo, bajo qué correlación, qué cambió y si fue éxito, rechazo o
  denegación. Lo muestra como era en ese momento: no se recalcula si después cambia la ocupación o el vínculo.
  NO es otra bitácora: es la misma auditoría inmutable del sistema, ahora con contexto institucional.
  Los eventos anteriores a CTL-02 no tienen contexto y se rotulan así; no se inventa.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno» y ente activo.
  - Una cuenta con vínculo ACTIVO y un funcionario con asignación vigente.

PASOS Y RESULTADO ESPERADO:
  1. GENERAR: con la cuenta vinculada registre un cambio, por ejemplo un funcionario en Ocupación de cargos.
  2. LOCALIZAR: entre con gobierno_auditoria:view a Bitácora institucional. Filtre por Funcionario o Usuario
     técnico y pulse «Filtrar». La fila muestra usuario técnico, actor efectivo, cargo y unidad.
  3. DETALLE: abra la fila. Ve Actor técnico (usuario, sesión, IP, correlación), Contexto institucional
     (actor efectivo, vínculo, ente, autoridad, roles, categorías, cargo, unidad, figura, competencias)
     y Qué cambió. Si tiene permiso sobre el objeto, aparece «Abrir el objeto».
  4. CORRELACIÓN: copie la correlación, vuelva a la lista, péguela en Correlación y filtre: aparece el evento.
  5. SIN IDENTIDAD: con una cuenta sin vínculo haga un cambio. La fila dice «Sin vínculo vigente» y el detalle
     no muestra funcionario, cargo ni autoridad.
  6. RECHAZO: active la exigencia de identidad e intente emitir un acto sin ejercer el cargo. La operación se
     rechaza, el acto sigue en borrador y la bitácora muestra el evento con resultado «Rechazo».
  7. HISTORIA: cierre el vínculo de la cuenta del paso 1 y vuelva a abrir aquel evento. Sigue mostrando el
     funcionario y el cargo de aquel momento.
  8. AUTENTICACIÓN: filtre la acción «Inicio de sesión»: aparecen los de cuentas vinculadas a este ente, con
     contexto «No aplica».

NEGATIVAS:
  - Usuario sin gobierno_auditoria:view: sin acceso.
  - Usuario de otro ente: no ve estos eventos y el detalle responde que no existe.
  - No hay botones para editar ni borrar: la base rechaza modificar o eliminar eventos.

LÍMITES CONOCIDOS:
  - Los 403 por falta de capacidad no generan evento, como en el resto de la plataforma (OBS-AUDIT-403-01).
  - El inicio de sesión de una persona vinculada a dos entes del mismo tenant se ve en ambos.
  - Las consultas sensibles auditadas son las 10 exportaciones y descargas de Gobierno; no se audita cada lectura.
  - Sin exportación de la bitácora en este ciclo.
```
