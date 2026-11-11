# OWNER UAT CARD · CTL-03 «Separación técnica y funcional» (GOV-CTL-004)

```
MÓDULO: Gobierno · PROCESO: CTL-03 Administrador técnico sin autoridad funcional
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
COMMIT: 011cf82 (producto) + 7db2ecc (humo UAT), develop

MENÚ: Gobierno › Separación técnica y funcional (debajo de «Bitácora institucional»)

ROLES A USAR:
  - Para ver la pantalla: capacidad gobierno_auditoria:view (Control Interno). En la base de QA el
    administrador «con todo» (admin) la tiene.
  - Para provocar un intento denegado: admintenant (administrador técnico) crea una cuenta nueva con
    SOLO el rol ADMIN y acotada a este ente; esa cuenta inicia sesión (alta MFA sintética la primera vez).

QUÉ ES Y QUÉ NO ES:
  Es una vista de SOLO LECTURA para Control Interno: muestra que el administrador técnico no tiene
  autoridad funcional, de dónde viene cada rol y qué intentos de ampliar autoridad fueron denegados.
  NO concede, quita ni corrige nada. NO crea otro sistema de roles: refleja el techo de delegación
  (Spec 003), la ocupación de cargos (ORG-04) y la identidad institucional (ORG-06).
  Compromiso y pago no existen todavía en Gobierno: el control es transversal y se aplicará cuando existan.

USE SOLO DATOS SINTÉTICOS.
```

## Pasos

1. Entre como **admin** y abra **Gobierno › Separación técnica y funcional**.
   Esperado: tres secciones, «Integridad de la separación», «Administradores técnicos» e «Intentos denegados».
2. **Integridad:** debe decir «Separación íntegra», con el rol ADMIN «todas técnicas» y FUNCIONAL_COMPLETO
   «ninguna técnica». Debajo verá el estado de la exigencia de identidad institucional (Inactiva por defecto) y su efecto.
3. **Administradores técnicos:** cada cuenta con capacidades técnicas tiene una ficha con:
   - sus roles separados en «Roles técnicos» y «Roles de negocio»;
   - el origen de cada rol: «Concedido en la instalación» o «Concedido por … el …»;
   - su identidad institucional: funcionario y vínculo, o «Sin vínculo institucional vigente»;
   - sus cargos y la autoridad que de ellos deriva.

   Fíjese en las etiquetas:
   - **«Solo técnico»**: un ADMIN puro.
   - **«Técnico y funcional, sin autoridad institucional»**: tiene permisos, pero no ejerce cargo. **Permiso no es autoridad.**
4. **Intento de autoescalada:**
   1. Como **admintenant**, en Seguridad › Usuarios, cree una cuenta sintética con solo el rol ADMIN para este ente.
   2. Entre con ella e intente asignarse FUNCIONAL_COMPLETO. Esperado: lo deniega «No puede ampliar su propia autoridad.».
   3. Si además intenta crear un rol con una capacidad de negocio (por ejemplo, decidir contrataciones), también se deniega y el rol no se guarda.
5. Vuelva como **admin** a la pantalla. En «Intentos denegados» debe aparecer el intento, con fecha, usuario, motivo en
   lenguaje humano y capacidades excedidas. Cuando el evento está en la bitácora, hay un enlace «Ver en la bitácora».
6. **Actor legítimo (opcional, más largo):** un usuario con vínculo institucional activo y ocupación vigente de un cargo con
   la competencia puede emitir un acto aunque la exigencia de identidad esté activa. Una cuenta con permisos pero sin
   vínculo recibe «Su cuenta no tiene un vínculo institucional vigente en este ente». Lo cubre la E2E automática (P4).
7. **Teléfono:** abra la pantalla en un móvil o a 390 px. Los intentos denegados se ven como lista, sin desplazamiento horizontal.

## Qué decirnos
- ¿Entiende, sin explicación técnica, por qué el administrador técnico no puede aprobar ni decidir?
- ¿Falta algún dato que Control Interno necesite en la ficha del administrador o en el intento denegado?
