# OWNER UAT CARD · GOV-ORG-07 · ORG-07 «Matriz auditable de autoridad: quién puede qué» (GOV-ORG-010)

```
MÓDULO: Gobierno · PROCESO: ORG-07 Matriz de autoridad · ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
DÓNDE ENTRAR: Menú > Gobierno > Matriz de autoridad  (ruta /gobierno/autoridad)
ROL A USAR: un usuario con gobierno_autoridad:view (en la base de QA, el administrador «con todo» ADMIN + FUNCIONAL_COMPLETO lo tiene:
            la migración 0068 se lo concede a FUNCIONAL_COMPLETO). Para la prueba negativa: un usuario con solo gobierno_autoridad:view y otro sin él.
PRECONDICIONES:
  - Licencia sintética de QA con el módulo «gobierno».
  - ORG-01 ente ACTIVO; ORG-02 estructura del ejercicio VIGENTE (p. ej. DESP «Despacho del Alcalde» con la subunidad DA-01).
  - ORG-03: al menos dos cargos VIGENTES con su acto, p. ej.:
      DIR-ADM en DA-01: Aprobar · Contrataciones hasta 50.000,00 USD; JEF-TES en DESP: Pagar · Tesorería sin límite.
EJERCICIO: el del año en curso (selector «Ejercicio»). FECHA: por defecto, hoy («A la fecha»).
PASOS Y RESULTADO ESPERADO:
  1. Abra Gobierno › Matriz de autoridad. Verá el aviso «La autoridad es la de cada cargo…» (personas: ORG-06; delegaciones: ORG-04) y el resumen
     «2 autorizaciones de 2 cargos al <hoy>».
  2. UNIDAD: en «Unidad» elija «DESP · Despacho del Alcalde»: siguen las dos filas (DA-01 es subunidad de DESP). Elija DA-01: solo DIR-ADM.
  3. CARGO / ACCIÓN / MATERIA: «Acción» = Pagar → solo JEF-TES; «Materia» = Contrataciones → solo DIR-ADM. «Limpiar filtros» vuelve a todo.
  4. LÍMITE: DIR-ADM muestra «Hasta 50.000,00 USD por operación» (con su fundamento si lo tiene); JEF-TES «Sin límite».
  5. ACTO SOPORTE: la columna muestra el título del documento del acto del cargo.
  6. HISTORIA: «Ver detalle» en DIR-ADM abre el panel con unidad y ruta, estado, vigencia, acto e «Historial» de versiones; la versión que usa la
     matriz dice «Usada para esta fecha»; «Abrir el cargo» lleva a su ficha en Cargos y competencias.
  7. A LA FECHA: desactive JEF-TES en Cargos y competencias con fecha 01/01 del ejercicio. En la matriz de hoy desaparece; con «A la fecha» =
     01/01 vuelve a aparecer marcado «Inactivo» con vigencia «01/01 – 01/01».
  8. EXPORTAR: con un filtro activo, «Exportar CSV» descarga autoridad-<ejercicio>-<fecha>.csv con solo las filas filtradas y la fecha de corte.
FILTROS A VERIFICAR: ejercicio, fecha, unidad (con subunidades), cargo, acción, materia, búsqueda (se aplica al pulsar «Buscar»), paginación (> 50 filas).
EXPORTACIÓN: el CSV respeta los filtros; Sistema > Auditoría registra «Matriz de autoridad exportada» con ejercicio, fecha, filtros y filas.
PRUEBA NEGATIVA:
  a) Con un usuario de solo gobierno_autoridad:view: ve la matriz y el detalle, pero no «Abrir el cargo» ni el menú «Cargos y competencias».
  b) Con un usuario sin gobierno_autoridad:view: el menú no muestra «Matriz de autoridad»; por URL directa, «Sin acceso».
  c) Escriba en «A la fecha» un día de otro año: error en el campo «La fecha debe estar dentro del ejercicio».
  d) Desde otro ente, el detalle de un cargo ajeno responde «no encontrado»; un cargo en BORRADOR nunca aparece.
LIMPIEZA: no hace falta; la matriz no escribe nada (solo la auditoría de la exportación).
DEUDAS CONOCIDAS NO BLOQUEANTES:
  - Personas que ocupan cada cargo: ORG-06 (BLOQUEADO). Delegaciones/suplencias: ORG-04 (BLOQUEADO). La matriz lo dice en pantalla.
  - FIND-ORG07-01 (LOW): DOC-02 valida la competencia de un acto con las competencias actuales del cargo, no con las de la fecha del acto.
```
