# OWNER UAT CARD · GOV-0-06 · ORG-06 «Vincular usuario con identidad, cargo, unidad y alcance; separación de roles» (GOV-ORG-007, GOV-ORG-005)

```
MÓDULO: Gobierno · PROCESO: ORG-06 Identidad institucional
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Gobierno › Identidad institucional (/gobierno/identidad): qué cuenta corresponde a qué funcionario.
  - Desde esa pantalla: Nuevo vínculo, ficha de cada vínculo y Categorías y separación.
  - Gobierno › Mi contexto institucional (/gobierno/identidad/mi-contexto): su propia cuenta, funcionario,
    cargo y autoridad a una fecha.

ROLES A USAR:
  - Registro, edición y descarte; clasificar roles: gobierno_identidad:view y :manage.
  - Activación del vínculo y de la exigencia: gobierno_identidad:activate (pide MFA). Debe ser otra persona:
    quien registra no activa.
  - Cierre y revocación: gobierno_identidad:revoke (pide MFA).
  - Lector: solo gobierno_identidad:view.
  - Mi contexto: cualquier sesión con el módulo Gobierno; no necesita capacidad de identidad.
  - Negativas: un usuario solo con :view; un usuario de otro ente.
  En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) los tiene.

QUÉ ES Y QUÉ NO ES:
  Responde qué cuenta era qué funcionario, con qué cargo, unidad, ente y autoridad en cualquier fecha.
  Vincular NO concede autoridad: la autoridad sale de la ocupación vigente de ORG-04 y de las competencias
  del cargo de ORG-03. Un rol técnico tampoco concede autoridad de negocio.
  NO crea usuarios ni roles, y Atenea sigue siendo el sistema de nómina: no se crean usuarios desde Atenea.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno» y ente activo.
  - Una cuenta activa sin vínculo y un funcionario activo de ORG-04.
  - Para ver autoridad: ese funcionario con una asignación vigente en un cargo con competencias.
  - Dos personas: una registra y otra activa.

PASOS Y RESULTADO ESPERADO:
  1. REGISTRAR: en Identidad institucional pulse «Nuevo vínculo». Elija cuenta y funcionario de las listas,
     la fecha inicial y el motivo. Guarde: queda en Borrador. Vincular aún no da nada.
  2. ACTIVAR: entre con otra persona que tenga :activate, abra el vínculo y pulse «Activar». Pasa a Activo.
     Si intenta activarlo quien lo registró, o la cuenta del propio vínculo, el sistema lo rechaza.
  3. CONSULTAR: la ficha muestra funcionario, ente, ocupaciones, cargo, unidad, autoridad, roles, categorías
     y conflictos. Sin ocupación vigente la autoridad es ninguna, y lo explica.
  4. A UNA FECHA: cambie la fecha de consulta a una anterior a la ocupación y a otra posterior: la autoridad
     cambia con la fecha. Consultar el pasado no concede nada hoy.
  5. MI CONTEXTO: entre con la cuenta vinculada y abra Mi contexto institucional: ve lo mismo, solo de sí misma.
  6. CATEGORÍAS: en Categorías y separación clasifique un rol. En Segregación de funciones cree una regla del
     proceso ORG-06 entre dos categorías y actívela. Vea el conflicto cuando una cuenta reúna ambas.
  7. EXIGENCIA: en Categorías y separación active la exigencia de identidad (pide MFA y motivo). Desde ese
     momento, emitir un acto exige ejercer hoy ese cargo con esa competencia.
  8. CERRAR O REVOCAR: en la ficha pulse «Cerrar» o «Revocar» con fecha y motivo. La historia conserva todo.
  9. EXPORTAR: en la lista pulse «Exportar CSV». El archivo no trae el documento completo.

NEGATIVAS:
  - Dos cuentas para un mismo funcionario, o dos funcionarios para una cuenta, en la misma vigencia: se rechaza.
  - Dos cuentas de la misma persona no pueden registrar y activar: cuenta como el mismo actor.
  - Cuenta o funcionario inactivos: no se activa el vínculo, y una cuenta inhabilitada no tiene autoridad hoy.
  - Combinación de categorías incompatible según una regla activa: se bloquea y queda auditado.
  - Administrador técnico sin ocupación, con la exigencia activa: no puede emitir el acto.
  - Usuario de otro ente: el vínculo no existe para él.

LÍMITES CONOCIDOS:
  - En este ciclo la exigencia protege una sola operación: emitir un acto, la única con cargo y competencia
    explícitos. La guarda queda lista para los procesos que lleguen.
  - Los roles a una fecha pasada se reconstruyen de la auditoría de asignación y retiro de roles.
  - La certificación exhaustiva queda para FINAL_GOVERNMENT_CERTIFICATION, por directiva de la dueña.
```
