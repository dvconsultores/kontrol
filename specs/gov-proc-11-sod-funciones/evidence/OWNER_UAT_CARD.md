# OWNER UAT CARD · PROC-11 «Funciones incompatibles en contratación» (GOV-PROC-017)

```
MÓDULO: Gobierno · CONTRATACIONES: PROC-11 Funciones incompatibles
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
MENÚ:   Gobierno · Contrataciones › Funciones incompatibles
        (y el bloque «Funciones incompatibles» al final de la ficha de cada expediente)
FUENTE: Ingeniería de Requerimientos v1.0 §7.4 «GOV-PROC-017» y §13 «E2E-07 Hostil SoD»

ROLES:
  - Ver la matriz, los conflictos y exportarlos: gobierno_sod:view (Control Interno).
  - Declarar un borrador de regla: gobierno_sod:manage.
  - Activar o cerrar una regla: gobierno_sod:activate (sensible: pide su firma reforzada).

QUÉ ES Y QUÉ NO ES:
  Es el control que impide que una misma persona ejerza dos funciones del procedimiento de contratación que la
  institución declara incompatibles en el mismo expediente. La matriz la declara Control Interno: la ley exige
  segregar (N20) y prevenir el conflicto de interés (N23), pero no fija los pares.

  Funciones vigiladas hoy: Solicitante (quien registra el expediente y el requiriente), Receptor de ofertas,
  Evaluador (comisión, apertura, aportes y recomendación) y Adjudicador (quien decide).
  NO vigilada todavía: Pagador. El pago no existe en Gobierno (requisito GOV-TRE-004, TRE-04). La pantalla lo dice
  expresamente; no se simula.

  No sustituye a la segregación por acción de CTL-01 (Gobierno › Segregación de funciones): aquella impide que una
  persona haga dos acciones incompatibles sobre el mismo acto o hallazgo; esta mira las funciones que ocupa en el
  expediente de contratación.

USE SOLO DATOS SINTÉTICOS.
```

## Pasos

1. **Abrir.** Gobierno · Contrataciones › Funciones incompatibles.
   - Esperado: la lista de funciones vigiladas, la advertencia de que «Pagador» no está disponible y la matriz (vacía
     la primera vez).
2. **Declarar una regla.** Con una cuenta que tenga `gobierno_sod:manage`: escriba el nombre («Quien solicita no recibe
   ofertas»), elija «Función A» y «Función B», el riesgo y el fundamento; pulse «Registrar borrador».
   - Esperado: aparece como *Borrador* y la notificación confirma el código `RF-000n`.
   - Negativa: si elige la misma función dos veces, el formulario no deja registrarla.
3. **Activarla.** Con `gobierno_sod:activate`, pulse «Activar desde hoy».
   - Esperado: queda *Vigente · en vigor*. La activación es sensible: si su política exige firma reforzada, la
     aplicación se la pedirá.
4. **Ver un conflicto real.** Si el expediente ya tenía el conflicto antes de la regla (por ejemplo, usted registró el
   expediente y además recibió una oferta), el listado «Conflictos en el período» muestra el expediente, la fecha, la
   regla, las dos funciones, la persona y la evidencia de cada función.
   - Esperado: el número del expediente es un enlace que abre su ficha, y en la ficha el bloque «Funciones incompatibles»
     repite el conflicto.
5. **Comprobar el bloqueo.** Con la regla en vigor, intente que la misma persona asuma la función incompatible
   (por ejemplo, recibir una segunda oferta del expediente que esa persona registró).
   - Esperado: la operación se rechaza con un mensaje que nombra la regla, la función que ya ejercía y el registro que lo
     prueba. No se guarda nada y el intento queda en la bitácora como rechazo.
6. **Período y exportación.** Cambie «Desde», «Hasta» o «Función»; pulse «Exportar CSV».
   - Negativo: si «Desde» es posterior a «Hasta», el sistema responde que el período no es válido.
   - Esperado del CSV: se descarga con el período y la exportación queda registrada en la bitácora.
7. **Cerrar una regla.** Con `gobierno_sod:activate`, «Cerrar regla», escriba el motivo (mínimo 10 caracteres).
   - Esperado: queda *Cerrada*; su historia sigue visible y no se puede borrar.
8. **Teléfono y teclado.** A 390 y 320 px la pantalla se lee sin desplazamiento lateral (la tabla de conflictos se
   desplaza dentro de su caja). Todo se opera con teclado.

## Lo que queda fuera (no es un defecto de esta entrega)

- **Pagador:** requiere el pago de Gobierno (GOV-TRE-004, TRE-04). Mientras no exista, la matriz no puede referenciarlo.
- **Receptor de bienes:** es la recepción física de almacén (WH-01), distinta del receptor de ofertas que sí se vigila.
- **Inhabilidad del contratista (RNC/SNC):** es PROC-05, bloqueado por D-GOV-03.
- **Bloqueo por acción:** es CTL-01 y ya existe; no se duplica.
- Los conflictos anteriores a la regla no se borran ni se corrigen: se muestran con su evidencia para que Control Interno
  decida qué hacer por la vía que corresponda.
