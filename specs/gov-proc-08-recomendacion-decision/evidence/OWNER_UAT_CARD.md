# OWNER UAT CARD · PROC-08 «Recomendación y decisión» (GOV-PROC-010, GOV-PROC-011)

```
MÓDULO: Gobierno · PROCESO: PROC-08 Recomendación de la Comisión y decisión de la autoridad
ESTADO: OWNER_UAT_READY (pendiente de su prueba; OWNER_ACCEPTED solo lo da usted)
COMMIT: 570a033 (develop)

MENÚ: Gobierno · Contrataciones › Expedientes › (abrir un expediente) › sección «Recomendación y decisión»
      (debajo de «Apertura y evaluación»)

ROLES A USAR:
  - Capacidad gobierno_decision: view (ver), recommend (Comisión: emitir la recomendación),
    decide (autoridad: registrar la decisión; acción sensible con MFA).
  - En la base de QA, el administrador «con todo» las tiene. Con la exigencia de identidad de ORG-06
    activa, quien recomienda debe ser miembro de la Comisión y quien decide no puede haber firmado la
    recomendación.

QUÉ ES Y QUÉ NO ES:
  La Comisión emite su recomendación (acto separado) y la autoridad decide con un acto DOC-02.
  NO crea el contrato (eso es CNT-01). NO ordena ofertas por puntaje. NO afirma entrega electrónica de
  notificaciones: el registro se hace en el acto (DOC-04).

USE SOLO DATOS SINTÉTICOS.

PRECONDICIONES:
  - Expediente con la evaluación concluida (PROC-07) y al menos dos ofertas abiertas.
  - Un acto DOC-02 EMITIDO, de carácter PARTICULAR, con competencia APROBAR sobre CONTRATACIONES,
    dictado por un cargo con esa competencia vigente en la fecha del acto, y sin uso en otra decisión.

PASOS Y RESULTADO ESPERADO:
  1. Abra el expediente desde el menú y baje a «Recomendación y decisión».
     → Estado: Evaluación «Concluida»; siguiente acción «Preparar recomendación».
  2. Revise «Ofertas evaluadas» y los resultados técnico, económico y legal.
  3. Registre la motivación y los exámenes legal, financiero y técnico y el resultado de la matriz.
  4. Resultado «Adjudicar»: elija Opción 1 y, si quiere, Opción 2 y 3 (ninguna viene preseleccionada).
  5. Si corresponde, marque «Rechazar» en una oferta, elija la causal (LCP art. 76 / RLCP art. 102)
     y motive. → Si además la elige como opción, la emisión se rechaza: una oferta rechazada no puede ser opción.
  6. Marque los firmantes. → «Firmantes con voto: X de Y (mayoría requerida: Z)».
  7. «Emitir recomendación» → «Confirmar emisión». → REC-01 en solo lectura: «Emitida: no se puede editar.»
     Un suplente solo figura «con voto» si su principal no firmó.
  8. «Descargar informe (PDF)». → PDF del informe de recomendación.
  9. (Opcional) «Sustituir recomendación»: exige motivo; crea REC-02 y deja REC-01 «Sustituida».
  10. Como autoridad: en «Decisión de la autoridad» elija el acto DOC-02.
  11. Resultado «Adjudicada». → La oferta es la única admitida (Opción 1); no hay selector libre.
  12. Motive y «Registrar decisión» → «Confirmar decisión». → DEC-01 «Adjudicada», con enlace al acto.
  13. «Notificación a los oferentes»: cada oferente con «Sin notificación». Abra el acto y registre la
      notificación (DOC-04). → Al volver, ese oferente figura «Pendiente».
  14. «Historial»: recomendación y adjudicación con fecha.
  15. Compruebe que no se creó ningún contrato (CNT-01 es otro proceso).

RUTAS ALTERNATIVAS (en otros expedientes):
  A. Desierta: recomiende «Declarar desierta» con causal (LCP art. 113); decida «Declarada desierta».
  B. Terminación: con una adjudicación vigente, decida «Terminada» con otro acto. → La adjudicación queda
     «Sustituida».
  C. Nulidad por información falsa: anule DEC-01 con otro acto, causal «Información falsa». → DEC-01
     «Anulada»; ahora la oferta admitida es la Opción 2.
  D. Nulidad por violación legal: no habilita la opción siguiente.

QUÉ DEBE FALLAR (con mensaje claro):
  - Recomendar sin evaluación concluida, sin quórum o con un firmante ajeno a la Comisión.
  - Decidir con un acto interno, en borrador, sin competencia, de otro ente o ya usado.
  - Una segunda decisión final, o una recomendación nueva cuando ya hay decisión.

GAPS DECLARADOS:
  - Adjudicación parcial: no disponible (requiere pliego de PROC-04).
  - Límites de monto de la autoridad: no se validan (la oferta no registra monto).
```
