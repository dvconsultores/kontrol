# OWNER UAT CARD · GOV-TRE-02 · TRE-02 «Programación financiera y disponibilidad de caja» (GOV-TRE-002)

```
MÓDULO: Gobierno · PROCESO: TRE-02 Programación financiera
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Gobierno · Tesorería › Programación financiera (/gobierno/tesoreria/programacion): lista, nuevo programa y ficha.
  - Gobierno · Tesorería › Rubros de caja (/gobierno/tesoreria/rubros): catálogo de rubros del ente.

ROLES A USAR:
  - Tesorería: gobierno_caja:view y :manage. Para activar y cerrar, además :activate (pide MFA).
    En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) los tiene.
  - Presupuesto u otro lector: solo gobierno_caja:view.
  - Negativas: un usuario solo con gobierno_caja:view; un usuario de otra empresa.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno» y ente activo.
  - Al menos una cuenta bancaria VIGENTE de TRE-01 en la moneda del programa.

QUÉ ES Y QUÉ NO ES:
  La pantalla muestra disponibilidad de caja proyectada. No es disponibilidad presupuestaria ni saldo bancario.
  La disponibilidad inicial la declara Tesorería bajo su responsabilidad: el sistema no la infiere de ninguna parte.
  No hay conversión entre monedas ni totales entre ellas: cada programa va en una sola moneda.

PASOS Y RESULTADO ESPERADO:
  1. RUBROS: en Rubros de caja registre uno de Ingreso y otro de Desembolso. Aparecen en la tabla como Activo.
     El tipo y el código no se pueden cambiar después.
  2. NUEVO PROGRAMA: en Programación financiera pulse «Nuevo programa». Elija ejercicio, moneda y mes inicial.
     Se abre «Programa PF-<ejercicio>-<moneda>» en Borrador, con el aviso de semántica arriba.
  3. DECLARAR: pulse «Declarar», elija la cuenta, escriba monto, fecha de corte y fundamento (10 caracteres o más).
     Pulse «Registrar declaración». La tabla muestra la cuenta y el banco, nunca el número de cuenta.
  4. PROGRAMAR: pulse «Añadir línea», elija rubro, mes y monto. Repita con el desembolso.
     La tabla de disponibilidad mensual calcula inicial, ingresos, desembolsos y final de cada mes.
     Compruebe: final = inicial + ingresos − desembolsos, y el inicial del mes siguiente es el final anterior.
  5. DÉFICIT: añada un desembolso mayor que lo disponible. El mes muestra «Déficit proyectado»; el aviso indica que
     el programa puede activarse igualmente.
  6. ACTIVAR: pulse «Activar versión» (MFA). Estado Vigente, versión vigente 1. La historia muestra quién y cuándo.
  7. REPROGRAMAR: pulse «Reprogramar», escriba el motivo y confirme. Se abre el borrador de la versión 2 con las
     líneas copiadas. Añada una línea de un mes en curso o futuro y pulse «Activar versión».
     La versión 1 queda Superada y «Ver versión 1» conserva sus cifras originales.
  8. HISTORIA: la sección de historia muestra cada paso con su autor, fecha, versión y motivo.
  9. CIERRE: pulse «Cerrar programa», escriba el motivo y confirme (MFA). Estado Cerrado y sin acciones.

PRUEBA NEGATIVA:
  a) Otro ente: un usuario de otra empresa no ve el programa («Programa no encontrado») ni aparece en su lista.
  b) Cuenta cerrada: cierre una cuenta en TRE-01: ya no se ofrece al declarar. Una declaración ya hecha no cambia.
  c) Otra moneda: en un programa USD no se ofrecen cuentas VES.
  d) Sin preparar: activar sin declaración ni línea indica exactamente qué falta y el programa sigue en Borrador.
  e) Duplicado: un segundo programa del mismo ejercicio y moneda se rechaza.
  f) Mes pasado: en una reprogramación del ejercicio en curso no se puede añadir, cambiar ni quitar un mes pasado.
  g) Consulta: un usuario con solo gobierno_caja:view ve todo y no tiene botones de escritura.
  h) Cerrado: un programa cerrado no admite ningún cambio.

AUDITORÍA:
  - Sistema › Auditoría: registro y cambio de rubros; programa registrado, actualizado, activado, reprogramado,
    descartado y cerrado.
  - Gobierno › Auditoría institucional incluye el proceso «TRE-02 · Programación financiera» y enlaza al programa.
  - Segregación de funciones ofrece el proceso «Programación financiera» con cuatro acciones.

LIMPIEZA: no hace falta. Un borrador se descarta; un programa activado no se borra y su historia es permanente.

DEUDAS CONOCIDAS NO BLOQUEANTES:
  - Rubros y subperíodos de la ONT (Reglamento N.º 3, art. 63): el catálogo es del ente; no se precargan rubros.
  - Las cuotas y reprogramaciones que exige el art. 64 se registran aquí como decisión del ente: no hay aprobador
    externo ni envío a la ONT.
  - Presupuesto, compromiso, causado, pago y conciliación quedan fuera de este proceso.
```
