# OWNER UAT CARD · GOV-TRE-01 · TRE-01 «Cuentas bancarias públicas» (GOV-TRE-001)

```
MÓDULO: Gobierno · PROCESO: TRE-01 Cuentas bancarias públicas
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)

DÓNDE ENTRAR:
  - Gobierno · Tesorería › Cuentas bancarias (/gobierno/tesoreria/cuentas): lista, nueva cuenta y ficha.
  - Gobierno · Tesorería › Bancos (/gobierno/tesoreria/bancos): catálogo de bancos.

ROLES A USAR:
  - Tesorería: gobierno_cuentas:view y :manage. Para activar, inactivar, reactivar o cerrar, además :activate, que pide MFA.
    En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO) los tiene.
  - Negativas: un usuario solo con gobierno_cuentas:view; un usuario de otra empresa.

PRECONDICIONES:
  - Licencia de QA con el módulo «gobierno», ente activo, estructura vigente y al menos dos cargos vigentes.
  - Dos actos administrativos EMITIDOS o EFICACES del ente (DOC-02). Se registran en Gobierno › Actos administrativos.

PASOS Y RESULTADO ESPERADO:
  1. MENÚ: abra Gobierno · Tesorería. Ve «Cuentas bancarias» y «Bancos».
  2. BANCO: en Bancos registre un código de 4 dígitos y un nombre. Aparece en la tabla como «Activo».
     KONTROL no precarga bancos ni códigos oficiales: usted los registra.
  3. CUENTA: en Cuentas bancarias pulse «Nueva cuenta». Escriba denominación, banco, tipo, moneda y un número de
     20 dígitos que empiece por el código del banco. «Registrar cuenta» abre «Cuenta CB-<año>-<nnnn>» en Borrador.
     El número se ve enmascarado (••••NNNN).
  4. ACTO: en «Acto habilitante» elija un acto y pulse «Vincular acto».
  5. AUTORIZADO: pulse «Autorizar un cargo»; elija el cargo, el acto que lo autoriza y la fecha. Observe que solo se
     eligen cargos vigentes: no se escribe ninguna persona.
  6. ACTIVAR: pulse «Activar cuenta» (MFA). El estado pasa a Vigente y «Vigente · en vigor».
  7. NÚMERO: pulse «Ver número completo» y luego «Ocultar número». La consulta queda en la auditoría.
  8. CAMBIO DE AUTORIZACIÓN: autorice un segundo cargo con el otro acto y termine el primero, con acto, fecha y motivo.
     La tabla conserva los dos y la historia registra «Cargo autorizado» y «Autorización terminada».
  9. INACTIVAR Y REACTIVAR: inactive con motivo (Inactiva) y reactive con motivo (Vigente).
 10. CERRAR: pulse «Cerrar cuenta» con motivo y fecha. Queda Cerrada, sus autorizados terminan con
     «Cierre de la cuenta» y aparece «Una cuenta cerrada no se reabre.».

AUDITORÍA:
 11. Sistema › Auditoría muestra cada paso («Cuenta bancaria pública registrada / activada / inactivada / reactivada /
     cerrada», «Cargo autorizado en la cuenta bancaria», «Número completo de la cuenta bancaria consultado») y en
     ningún evento aparece el número completo.
 12. Gobierno › Auditoría institucional incluye el proceso «TRE-01 · Cuentas bancarias públicas» y abre la ficha.

PRUEBA NEGATIVA:
  a) OTRO ENTE: con un usuario de otra empresa, la cuenta responde «no encontrada» y no aparece en su lista.
  b) AUTORIZADO INVÁLIDO: el selector de cargo no admite texto libre ni ofrece cargos en borrador, de otro ejercicio o
     de otra empresa.
  c) NÚMERO: uno que no empieza por el código del banco se rechaza.
  d) ACTIVAR SIN PREPARAR: una cuenta sin acto o sin autorizados muestra qué le falta.
  e) ACTO REVOCADO: revoque en DOC-02 el acto vinculado. La cuenta conserva estado e historia, avisa «El acto habilitante
     fue revocado o anulado» y no admite nuevos autorizados ni reactivación hasta vincular un acto vigente.
  f) SOLO CONSULTA: un usuario con gobierno_cuentas:view no ve el número completo ni las acciones.

LIMPIEZA: no hace falta. Las cuentas no se borran (se cierran) y su historia es permanente por diseño.

DEUDAS CONOCIDAS NO BLOQUEANTES:
  - El autorizado es un cargo; la persona que lo ocupa y su firma registrada en el banco llegan con ORG-06 (OD-TRE01-01).
  - El número se guarda sin cifrado de campo, como las demás cuentas del repositorio; no hay contrato de cifrado de campo.
  - Sin combinaciones de firma, sin pagos, conciliación ni conversión de moneda: están fuera de TRE-01.
```
