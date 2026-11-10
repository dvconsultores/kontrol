# OWNER UAT CARD · PROC-10 «Garantías y cauciones» (GOV-PROC-013)

```
MÓDULO: Gobierno · PROCESO: PROC-10 Garantías y cauciones del expediente
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
COMMIT: 1d45e49 (develop)

MENÚ: Gobierno · Contrataciones › Expedientes › (abrir un expediente) › sección «Garantías y cauciones»
      (debajo de «Recomendación y decisión»)

ROLES A USAR:
  - Capacidad gobierno_garantias: view (ver), manage (registrar emisores, requisitos, garantías,
    renovar y sustituir), release (liberar; acción sensible con MFA), execute (ejecutar; con MFA).
  - En la base de QA, el administrador «con todo» las tiene. El MFA es de sesión: se pide al iniciar
    sesión, no en cada botón.

QUÉ ES Y QUÉ NO ES:
  Registra lo que exige el pliego y cada garantía recibida, con su emisor, monto, moneda, vigencia y
  documento, y evalúa si es suficiente. NO calcula porcentajes sobre un monto que la plataforma no
  registra (presupuesto, oferta o contrato): en ese caso dice «No evaluable». NO crea el contrato (CNT-01).
  Renovar o sustituir NUNCA modifica la garantía anterior: crea una nueva encadenada.

USE SOLO DATOS SINTÉTICOS.

PRECONDICIONES:
  - Un expediente abierto con ofertas recibidas (PROC-06). Para todo tipo salvo mantenimiento de oferta
    (anticipo, fiel cumplimiento, laboral, responsabilidad civil y otra), además una adjudicación vigente (PROC-08).
  - Documentos del expediente con versión cargada (el pliego y cada fianza o póliza).
  - Para liberar o ejecutar: un acto DOC-02 EMITIDO o EFICAZ, de carácter PARTICULAR, con competencia
    APROBAR sobre CONTRATACIONES, dictado por un cargo con esa competencia vigente.

PASOS Y RESULTADO ESPERADO:
  1. Abra el expediente desde el menú y baje a «Garantías y cauciones».
     → Resumen textual (requisitos, garantías, por vencer, vencidas, liberadas, ejecutadas, sujetos sin
       garantía) y, si hay, «Adjudicación vigente: DEC-xx · O-xx (oferente)».
  2. «Nuevo emisor»: tipo Aseguradora, nombre y RIF → «Registrar emisor». → Aparece en la lista.
     (Un emisor Banco se elige de los bancos de TRE-01.)
  3. «Nuevo requisito»: regla «Mantenimiento de oferta · monto fijo en bolívares», monto, moneda VES,
     «Vigente al menos hasta», fundamento y documento del pliego → «Registrar requisito».
     → REQ-xx con su regla, fuente legal y forma de cálculo.
  4. «Registrar garantía»: requisito, oferta, emisor, número del instrumento, monto, moneda, fechas y
     documento → «Registrar». → GAR-xx con días restantes, estado de vigencia y «Suficiencia: …» con los
     seis criterios (documento, emisor, moneda, monto, vigencia mínima, vigente a la fecha).
  5. Suficiencia: si la garantía vence antes de la vigencia mínima → «Insuficiente» y «Vigencia mínima:
     No cumple»; si cubre monto y fecha → «Suficiente».
  6. NO_EVALUABLE: con una adjudicación vigente, registre un requisito «Fiel cumplimiento» por porcentaje
     (p. ej. 20 %) y su garantía. → «Suficiencia: No evaluable» y en el criterio Monto
     «BASE_MONETARIA_NO_DISPONIBLE: falta el …». Nunca muestra un cálculo con cero.
  7. «Renovar» en una garantía: nueva fecha hasta, documento del endoso y motivo → «Renovar garantía».
     → Una garantía nueva «Renueva o sustituye a GAR-xx»; la anterior queda «Renovada» con sus datos intactos.
  8. «Sustituir» (solo aparece en fiel cumplimiento y laboral): emisor, número, monto, moneda, fechas,
     documento y motivo → «Sustituir garantía». → Garantía nueva; la anterior «Sustituida» y conservada.
  9. «Liberar»: acto DOC-02 y motivo → «Liberar garantía» → «La liberación no se puede deshacer.» →
     «Confirmar liberación». → «Liberada»; en el historial, el acto y «Precondición: Verificada» (oferente no
     adjudicado o procedimiento desierto o terminado) o «Soportada por el acto».
  10. «Ejecutar»: acto DOC-02, motivo y monto ejecutado (no mayor que la garantía) → «Ejecutar garantía» →
      «La ejecución no se puede deshacer.» → «Confirmar ejecución». → «Ejecutada»; «Monto ejecutado: …».
  11. «Historial (N)» en cada tarjeta: Registro, Renovación, Sustitución, Liberación y Ejecución con fecha,
      actor, motivo, documento, acto y monto, incluida la cadena de la garantía anterior.
  12. Baje a «Cronología» del expediente: «Garantía GAR-xx liberada», «… sustituida por GAR-yy»,
      «… ejecutada por …».

QUÉ DEBE FALLAR (con mensaje claro):
  - Porcentaje fuera del rango legal de la regla, o monto fijo en otra moneda que VES cuando la regla lo exige.
  - Garantía de fiel cumplimiento sin adjudicación, o para una oferta que no es la adjudicada.
  - Emisor con RIF repetido en el ente, o la misma referencia del mismo emisor dos veces.
  - Fecha hasta anterior a la fecha desde.
  - Sustituir una garantía de mantenimiento de oferta.
  - Liberar o ejecutar con un acto en borrador, interno, sin competencia o de otro ente.
  - Ejecutar por más del monto de la garantía, o volver a actuar sobre una garantía ya liberada o ejecutada.

GAPS DECLARADOS:
  - Exigencias porcentuales: No evaluables mientras la plataforma no registre presupuesto, monto de oferta
    ni monto de contrato (OBS-PROC08-MONTO-01; PROC-04 y CNT-01).
  - Adjudicación parcial: no disponible (OBS-PROC08-PARCIAL-01).
```
