# OWNER UAT CARD · GOV-0-03 · ORG-03 «Cargos con competencias y límites de firma/aprobación»

```
MÓDULO: Gobierno · PROCESO: ORG-03 Cargos con competencias y límites de firma/aprobación · ESTADO: OWNER_UAT_READY
        (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
DÓNDE ENTRAR: Menú > Gobierno > Cargos y competencias  (ruta /gobierno/cargos; el ejercicio en /gobierno/cargos/AAAA;
              cada cargo en /gobierno/cargos/AAAA/<id>)
ROL A USAR: un usuario funcional de Gobierno con las capacidades gobierno_cargos (ver, editar, poner en vigor),
            gobierno_estructura:view y documentos. En la base de QA, el administrador «con todo» (ADMIN + FUNCIONAL_COMPLETO)
            las tiene (la migración 0065 se las concede a FUNCIONAL_COMPLETO). Para la auditoría: un usuario con audit:view.
            Para la prueba negativa b): un «preparador» con gobierno_cargos:view + gobierno_cargos:edit + gobierno_estructura:view.
PRECONDICIONES:
  - Licencia sintética de QA con el módulo «gobierno».
  - ORG-01: el ente configurado y ACTIVO (Gobierno > Configuración del ente).
  - ORG-02: la estructura del ejercicio en curso VIGENTE, con al menos la unidad DA-01 «Dirección de Administración»
    (Gobierno > Estructura organizativa).
  - Un tipo documental para PDF en ese contenedor (p. ej. «Acto de creación»).
DATOS DE PRUEBA (sintéticos):
  Cargo DIR-ADM «Director de Administración» en DA-01.
  Competencias: Aprobar · Contrataciones hasta 50.000 USD por operación (fundamento «Reglamento interno, art. 12»);
                Firmar · Tesorería sin límite.
  Acto: cualquier PDF pequeño de prueba (sin datos reales).
PASOS:
  1. Entre en Gobierno > Cargos y competencias y pulse «Cargos AAAA» (el año en curso). Llega a «Cargos y competencias AAAA».
  2. «Agregar cargo»: código DIR-ADM, denominación «Director de Administración», unidad «DA-01 — Dirección de
     Administración», «Guardar». Se abre la página del cargo, insignia «Borrador».
  3. Mire «Requisitos para poner en vigor»: faltan «Al menos una competencia» y «Acto del cargo»; «Poner en vigor» está
     deshabilitado.
  4. «Agregar competencia»: acción Aprobar, materia Contrataciones, «Hasta un monto por operación», monto 50000,
     moneda «Dólares (USD)», fundamento «Reglamento interno, art. 12», «Guardar». La tabla dice
     «Hasta 50.000,00 USD por operación».
  5. «Agregar competencia»: Firmar · Tesorería, «Sin límite». La tabla dice «Sin límite».
  6. En «Acto del cargo», elija el tipo documental, el PDF y pulse «Adjuntar». Verá «El cargo está completo y puede
     ponerse en vigor.».
  7. «Poner en vigor», lea la confirmación y confirme. La insignia pasa a «Vigente».
  8. «Cambiar el límite de Aprobar · Contrataciones»: monto 75000 e intente guardar sin motivo: el sistema lo pide.
     Escriba «Ajuste del límite aprobado» y guarde. La tabla dice «Hasta 75.000,00 USD por operación».
  9. «Historial»: aparecen las versiones del cargo, la última con el motivo.
 10. Vuelva a «Cargos AAAA» (miga de pan) y pulse «Exportar CSV»: se descarga cargos-AAAA.csv, una fila por competencia
     (cargo, unidad, estado, vigencia, acción, materia, límite, monto, moneda, fundamento).
 11. Abra otro cargo vigente (o cree uno y póngalo en vigor) y pulse «Desactivar»: fecha de fin (por defecto 31/12/AAAA)
     y motivo «Supresión del cargo». La insignia dice «Inactivo» y el aviso «su vigencia terminó el 31/12/AAAA». No se borra.
RESULTADO ESPERADO: DIR-ADM VIGENTE con dos competencias (Aprobar · Contrataciones hasta 75.000,00 USD; Firmar · Tesorería
                    sin límite), su acto vinculado y su historial; el otro cargo INACTIVO con fecha.
COMPETENCIAS A VERIFICAR: acción y materia en lenguaje de negocio; una misma acción × materia no se repite en un cargo.
LÍMITES A VERIFICAR: «Sin límite» o «Hasta <monto> <moneda> por operación»; el monto acepta coma o punto decimal, rechaza
                     cero y más de dos decimales.
DOCUMENTOS A VERIFICAR: el PDF aparece en «Acto del cargo» con su análisis y se descarga; sin acto no se pone en vigor.
REPORTES A VERIFICAR: la tabla «Cargos del ejercicio» (búsqueda y filtros por unidad y estado) y su CSV.
AUDITORÍA A VERIFICAR: Sistema > Auditoría, en ese contenedor: cargo creado, competencias otorgadas, cargo puesto en vigor,
                       límite cambiado (con antes, después y motivo), cargo desactivado, exportación.
HISTORIA A VERIFICAR: cada cambio deja una versión con fecha y motivo; un cargo vigente no cambia su código ni su inicio de
                      vigencia; un cargo inactivo es de solo lectura.
PRUEBA NEGATIVA:
  a) Con un usuario de solo consulta: ve la lista, el cargo y «Exportar CSV», pero no «Agregar cargo», «Editar» ni
     «Agregar competencia».
  b) Con el «preparador» (editar sin poner en vigor): puede registrar cargos y preparar borradores, pero en un cargo
     vigente no ve «Agregar competencia» ni «Cambiar el límite…», y la página dice «Solo quien puede poner cargos en
     vigor cambia sus competencias.».
  c) Repita Aprobar · Contrataciones en DIR-ADM: «El cargo ya tiene esa competencia». Escriba monto 0: «El monto debe ser
     mayor que cero».
  d) En la estructura (Gobierno > Estructura organizativa) intente desactivar DA-01: no se puede mientras tenga cargos.
LIMPIEZA: no hace falta; es una base de QA. (Un cargo vigente no se borra; se desactiva.)
DEUDAS CONOCIDAS NO BLOQUEANTES:
  - Notificaciones persistentes arriba a la derecha (GOV0-UI-02, LOW): ciérrelas con «Cerrar notificación» si tapan un botón.
  - El límite se registra y se versiona; su APLICACIÓN (denegar un compromiso o un pago por encima del límite) llega con
    los procesos de presupuesto y tesorería. Quién ocupa cada cargo llega con ORG-06; delegaciones y suplencias, con ORG-04.
  - La conversión entre monedas no la hace ORG-03 (OD-ORG03-03).
```
