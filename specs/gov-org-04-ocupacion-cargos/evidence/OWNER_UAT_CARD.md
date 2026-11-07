# OWNER UAT CARD · GOV-ORG-04 · ORG-04 «Delegaciones, suplencias, encargadurías y designaciones con acto» (GOV-ORG-004, GOV-ORG-009)

```
MÓDULO: Gobierno · PROCESO: ORG-04 Ocupación de cargos
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Gobierno › Ocupación de cargos (/gobierno/ocupacion): quién ocupa cada cargo a una fecha.
  - Desde esa pantalla: Asignaciones (lista, exportación CSV, ficha) y Funcionarios (registro y ficha).

ROLES A USAR:
  - Registro: gobierno_ocupacion:view y :manage.
  - Activación: gobierno_ocupacion:activate (pide MFA). Debe ser otra persona: quien registra no activa.
  - Revocación, finalización y avocación: gobierno_ocupacion:revoke (pide MFA).
  - Lector: solo gobierno_ocupacion:view.
  - Negativas: un usuario solo con :view; un usuario de otro ente.
  En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) los tiene.

QUÉ ES Y QUÉ NO ES:
  Responde quién ejerce qué cargo, bajo qué figura, por qué acto, emitido por quién, desde cuándo, hasta
  cuándo, con qué estado y qué autoridad tiene en una fecha. Figuras: titular, encargaduría, suplencia,
  comisión de servicio, delegación de atribuciones y delegación de firma.
  El funcionario NO es un usuario del sistema ni una ficha de nómina: Atenea sigue siendo el sistema de
  nómina y su integración técnica es otro trabajo. Vincular usuarios y funcionarios es ORG-06.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno» y ente activo.
  - Estructura VIGENTE del ejercicio con dos cargos activos.
  - Un acto EFICAZ emitido por un cargo distinto del que se va a ocupar. Para una delegación, emitido por
    el cargo delegante y publicado en gaceta.

PASOS Y RESULTADO ESPERADO:
  1. FUNCIONARIO: Ocupación de cargos › Funcionarios. Registre nombre, tipo y número de documento.
     La lista muestra el documento enmascarado.
  2. DESIGNAR: pulse «Nueva asignación». Elija Titular, el funcionario, el cargo, el acto, la fecha inicial
     y el fundamento. Guarde: queda en Borrador.
  3. ACTIVAR: entre con otra persona que tenga :activate, abra la asignación y pulse «Activar». Pasa a Vigente.
     Si intenta activarla quien la registró, el sistema lo rechaza.
  4. CONSULTAR: en Ocupación de cargos el cargo aparece Cubierto con su titular y quién lo ejerce. Abra el
     cargo: ve el acto, su autoridad a la fecha, delegaciones e historia.
  5. REVOCAR: en la asignación pulse «Revocar», elija el acto, la fecha y el motivo. La historia muestra
     registro, activación y revocación.
  6. HISTÓRICO: abra el cargo y elija una fecha posterior a la revocación: aparece vacante y la fila queda
     Revocada. En una fecha anterior o igual sigue Vigente: la fecha final cuenta completa.
  7. EXPORTAR: en Asignaciones pulse «Exportar CSV». El archivo no trae el documento completo.

NEGATIVAS:
  - Dos titulares simultáneos en un cargo: el segundo se rechaza.
  - Acto no eficaz, acto del propio cargo o delegación sin gaceta: se rechaza con el motivo.
  - Competencia que el cargo no tiene, o firma por delegación de atribuciones: se rechaza.
  - Suplencia de la máxima autoridad municipal: más de 15 días exige autorización del Concejo; más de 90 no
    procede (LOPPM art. 87).
  - Usuario de otro ente: la asignación no existe para él.

LÍMITES CONOCIDOS:
  - La clasificación jurídica de «designación temporal» dentro de encargaduría va al paquete profesional;
    no cambia el modelo.
  - El art. 35 LOAP: 35.3 lo aplica el sistema; 35.1, 35.2 y 35.4 son una declaración de quien registra.
  - El registro de usuario-funcionario llega con ORG-06.
```
