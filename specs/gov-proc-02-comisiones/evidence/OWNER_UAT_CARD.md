# OWNER UAT CARD · GOV-PROC-02 · PROC-02 «Comisión de contrataciones (miembros, suplentes, impedimentos)» (GOV-PROC-003)

```
MÓDULO: Gobierno · PROCESO: PROC-02 Comisiones de contrataciones
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Gobierno · Contrataciones › Comisiones (/gobierno/contrataciones/comisiones).
  - Desde la lista: Nueva comisión y la ficha de cada una.

ROLES A USAR:
  - Registro, edición, miembros, inhibiciones y notificación al SNC: gobierno_comisiones:view y :manage.
  - Activación y resolución de inhibiciones: gobierno_comisiones:activate (pide MFA). Otra persona: quien registra
    no activa, y quien declara una inhibición o el propio miembro no la resuelve.
  - Terminar un miembro y cerrar: gobierno_comisiones:close (pide MFA).
  - Lector: solo :view. Negativas: un usuario sin la capacidad; un usuario de otro ente.
  En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) las tiene.

QUÉ ES Y QUÉ NO ES:
  Registra quién integra cada comisión, por qué acto y durante qué período. Los miembros son funcionarios de
  Ocupación de cargos, no usuarios ni fichas de nómina. Todavía no hay procedimientos ni ofertas: se integrarán en
  los siguientes bloques de Contrataciones.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno» y ente activo.
  - Ocho funcionarios activos en Ocupación de cargos.
  - Un acto eficaz y publicado en gaceta en Actos administrativos (RLCP art. 15).

PASOS Y RESULTADO ESPERADO:
  1. CREAR: pulse «Nueva comisión». Nombre, tipo permanente o temporal, vigencia y acto. Queda en preparación.
     La ficha dice exactamente qué falta para activarla, citando la ley.
  2. EDITAR: pulse «Editar» y cambie el nombre.
  3. PRINCIPALES Y SUPLENTES: pulse «Añadir miembro». Tres principales, uno por área: jurídica, técnica y económico
     financiera, cada uno con su suplente. El selector muestra nombre, cargo y unidad. La lista de lo que falta se
     acorta con cada uno.
  4. SECRETARIO: añada el secretario y su suplente, con voz y sin voto. Ya no falta nada.
  5. ACTIVAR: entre con otra persona que tenga :activate y pulse «Activar». Pasa a Vigente.
  6. ACTO: en Datos pulse «Abrir el acto». Lleva al acto, sin duplicarlo.
  7. INHIBICIÓN: pulse «Declarar inhibición»: miembro, asunto, causal del art. 18, descripción y fecha. Queda
     Declarada y muestra el suplente que actúa. Otra persona la resuelve con «Resolver».
  8. SNC: pulse «Registrar notificación al SNC» con fecha y referencia. Es solo un registro: no hay integración.
  9. SUSTITUIR: pulse «Terminar» en un miembro, con fecha y causa. Pasa a «Miembros anteriores». Con «Designar miembro»
     incorpore otro, con su acto y fecha.
  10. A UNA FECHA: en Composición elija una fecha anterior. Se ve quién la integraba entonces.
  11. CERRAR: pulse «Cerrar comisión» con fecha y motivo. La historia conserva todo.
  12. LISTA Y CSV: busque, filtre por estado, tipo y vigencia, y pulse «Exportar CSV».
  13. BITÁCORA: en Bitácora institucional busque estos eventos: traen el funcionario y el cargo de quien actuó.

NEGATIVAS:
  - Activar con número par de principales, sin un área o sin suplentes: se rechaza y dice qué falta.
  - Acto no publicado en gaceta: se rechaza (RLCP art. 15).
  - Quien registró intenta activar: se rechaza.
  - Funcionario de otro ente: no se puede incorporar. Usuario de otro ente: la comisión no existe para él.
  - Dos personas editando a la vez: la segunda recibe aviso de que cambió.

LÍMITES CONOCIDOS:
  - La inhibición se registra sobre un asunto en texto, hasta que exista el procedimiento.
  - La falta temporal y la convocatoria del suplente llegan con las sesiones de la comisión.
  - El sistema no verifica que el emisor del acto sea la máxima autoridad: lo muestra.
  - Los cinco días de la notificación al SNC no se calculan: la ley no dice si son hábiles y el calendario está pendiente.
  - La certificación ante el SNC se registra como dato.
```
