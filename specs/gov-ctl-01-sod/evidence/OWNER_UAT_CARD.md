# OWNER UAT CARD · GOV-CTL-01 · CTL-01 «Matriz de segregación de funciones» (GOV-CTL-001)

```
MÓDULO: Gobierno · PROCESO: CTL-01 Segregación de funciones (SoD)
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Gobierno › Segregación de funciones (ruta /gobierno/sod): reglas, nueva regla y ficha de cada regla.
  - Gobierno › Segregación de funciones › «Ver conflictos» (/gobierno/sod/conflictos): intentos bloqueados.

ROLES A USAR:
  - Control Interno: gobierno_sod:view, :manage y :activate (este último pide MFA). En la base de QA, el administrador
    «con todo» (ADMIN + FUNCIONAL_COMPLETO) los tiene: la migración 0072 concede gobierno_sod a FUNCIONAL_COMPLETO.
  - Usuario A (registrador): permisos de actos (gobierno_actos:view, :edit) o de hallazgos (gobierno_hallazgos:view, :manage).
  - Usuario B (otro actor): los mismos permisos que A, otro usuario.
  - Negativas: un usuario solo con gobierno_sod:view; un usuario de otra empresa.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno», ente activo, estructura vigente y un cargo con competencia
    (lo mismo que ya usa DOC-02).

PASOS Y RESULTADO ESPERADO:
  1. NUEVA REGLA: en Segregación de funciones pulse «Nueva regla». Proceso «Actos administrativos»,
     Acción A «Registrar el acto», Acción B «Emitir el acto», nombre «Quien registra el acto no lo emite»,
     razón y vigente desde hoy. Pulse «Registrar regla»: se abre «Regla SOD-<año>-<nnnn>» en Borrador.
     Observe que como Acción B no se ofrece «Registrar el acto»: una acción que crea el objeto solo puede ser B
     si marca «En ambos sentidos».
  2. ACTIVAR: pulse «Activar regla» (MFA). Estado «Vigente · en vigor»; la ficha muestra quién y cuándo la activó,
     y la historia «Registrada» y «Activada».
  3. ACCIÓN A: con el usuario A registre un acto y complételo (con su documento firmado).
  4. BLOQUEO: con el mismo usuario A pulse «Emitir». Aparece la alerta «Operación bloqueada por segregación de
     funciones»: usted ya realizó «Registrar el acto»… y «Pida a otro usuario autorizado». El acto sigue en Borrador.
  5. OTRO ACTOR: con el usuario B emita el mismo acto: lo emite sin problema.
  6. EVIDENCIA: en «Ver conflictos» verá el intento: fecha, usuario A, la regla, «Emitir el acto», acción previa
     «Registrar el acto» y el enlace «Abrir acto». En la ficha de la regla, «Ver conflictos de esta regla (1)».
     Sistema › Auditoría registra «Operación bloqueada por segregación de funciones».
  7. LO MISMO EN HALLAZGOS (opcional): regla del proceso «Hallazgos y acciones correctivas», A «Registrar el hallazgo»,
     B «Añadir una recomendación»: quien registró el hallazgo no puede recomendar sobre él; otro usuario sí.

PRUEBA NEGATIVA:
  a) Cierre la regla («Cerrar regla» con un motivo de al menos 10 caracteres) y repita el paso 4 con otro acto:
     ya no bloquea. La regla cerrada no se puede reabrir ni editar: para cambiarla, registre otra.
  b) Una regla activada con «Vigente desde» mañana aparece «Vigente · aún no en vigor» y no bloquea hoy.
  c) Otra empresa: no ve sus reglas («Regla no encontrada») ni sus conflictos.
  d) Un usuario solo con gobierno_sod:view ve las reglas, pero no ve «Nueva regla» ni «Activar regla».
  e) Una segunda regla vigente con las mismas dos acciones no se puede activar: «Ya hay una regla vigente con esas dos
     acciones en este proceso».
  f) En hallazgos, la regla de CTL-06 «quien presentó no verifica» sigue mandando por sí sola, haya o no reglas de
     segregación: el mensaje es el de CTL-06, no el de esta pantalla.

AUDITORÍA:
  - Sistema › Auditoría: «Regla de segregación de funciones registrada / modificada / activada / cerrada» y
    «Operación bloqueada por segregación de funciones».
  - Gobierno › Auditoría institucional incluye el proceso «CTL-01 · Segregación de funciones».

LIMPIEZA: no hace falta. Las reglas no se borran (se cierran) y su historia es permanente por diseño.

DEUDAS CONOCIDAS NO BLOQUEANTES:
  - El alcance es «mismo objeto» y el modo «solo bloquear» (OD-CTL01-01/02): no hay excepciones autorizadas ni
    reglas entre objetos distintos.
  - Integradas DOC-02 y CTL-06 (OD-CTL01-03); otros procesos de Gobierno se añadirán a medida que existan.
```
