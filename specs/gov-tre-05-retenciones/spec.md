# GOV-TRE-05 · Retenciones y comprobantes sobre el pago

- **Proceso:** TRE-05 (GOV-TRE-006, P0). Tesorería; consulta Contabilidad.
- **Depende de:** TRE-04 (pago, READY), TRE-09 (tasas oficiales, READY), ORG-03/04/07 (autoridad efectiva), CTL-01 (SoD), DOC (documentos).
- **Fuentes:** N11; N37 (Gaceta Municipal 512 Ext. de Naguanagua, custodiada); N38 (ninguna copia custodiada). Ver `evidence/N38_VALIDATION.md`.
- **Decisiones de la dueña (2026-11-20):** OD-TRE05-01..04 = A (ver §Decisiones).

## Historias

1. **Configurar (Tesorería).** Como responsable de tesorería defino el catálogo del ente (conceptos de retención y condiciones del beneficiario), la numeración de comprobantes y políticas de retención versionadas con reglas: concepto, base, alícuota, umbral, sustraendo, tope, condiciones exigidas, exclusiones, tipos de persona, redondeo, comprobante y fuente. Activo con fundamento y MFA; cierro; creo versión nueva.
2. **Calcular (preparador).** Sobre un pago TRE-04 no registrado elijo la política vigente a la fecha del pago, los conceptos y declaro los datos del beneficiario. El sistema muestra cada regla con base, alícuota, monto calculado y por qué aplica o no. El borrador no tiene efectos.
3. **Ajustar (si la política lo permite).** Cambio el monto aprobado de una línea con motivo; queda el calculado, el aprobado, el motivo y el actor.
4. **Aprobar (checker).** Otro usuario, con la competencia que fija la política en un cargo que ejerce, aprueba con MFA. Mismo usuario que calculó: rechazo. Se congela todo.
5. **Aplicar.** Al registrar el pago en TRE-04 la liquidación aprobada pasa a aplicada, se fijan bruto, total retenido y neto, y se emite un comprobante por cada concepto que lo exige, numerado según el patrón del ente, con PDF desde la instantánea.
6. **Consultar y exportar.** Lista de liquidaciones y comprobantes con filtros, CSV, historia y descarga del PDF.
7. **Corregir.** Antes del registro: anular la liquidación y recalcular. Después: los montos no cambian (TRE-07); el comprobante se anula con motivo y MFA y se sustituye por otro con los mismos montos y los datos declarados corregidos.

## Requisitos

- **FR-01** Catálogo del ente: `CONCEPTO` (con clase TRIBUTARIA, CONTRACTUAL u OTRA y serie opcional de comprobante) y `CONDICION`. Nada precargado.
- **FR-02** Política versionada BORRADOR → VIGENTE → CERRADA, con fuente (tipo, referencia, documento opcional), clasificación, vigencia, competencia del aprobador, permiso de ajuste y redondeo. `LEGAL_MANDATORY` se rechaza mientras N38 no tenga fuente verificada.
- **FR-03** Regla: concepto, base (`MONTO_BRUTO` o `PORCENTAJE_DEL_BRUTO`), alícuota, umbral (`NINGUNO`, `MONTO` o `MULTIPLO_TASA` con moneda TRE-09), sustraendo, tope, condiciones exigidas, exclusiones, tipos de persona y comprobante.
- **FR-04** Cálculo determinista en Decimal, con la política vigente a la **fecha del pago**. Las reglas son independientes entre sí: la base no descuenta otras retenciones. No aplican por umbral, exclusión, condición faltante o tipo de persona, y cada caso queda explicado en la línea.
- **FR-05** Autoridad única: bruto = monto del pago TRE-04; total retenido = suma de los montos aprobados de las líneas que aplican; neto = bruto − total. Siempre bruto = total + neto. El total nunca supera el bruto.
- **FR-06** Una liquidación activa por pago. Estados CALCULADA → APROBADA → APLICADA y ANULADA. Una CALCULADA bloquea el registro del pago. Editar, rechazar o anular el pago exige anular antes la liquidación, o la anula sola (rechazo y anulación del pago).
- **FR-07** Maker ≠ checker, competencia efectiva (ORG-03/04/07) y MFA para aprobar. CTL-01 con el proceso TRE-05.
- **FR-08** Comprobante por concepto con `exige_comprobante`. Lleva número, serie y patrón del ente, la instantánea completa (beneficiario declarado, pago, reglas, bases, alícuotas, montos, fecha, emisor y fuente), la huella y el PDF guardado en documentos. No se borra.
- **FR-09** Anular un comprobante (motivo, MFA) y sustituirlo con datos declarados corregidos y los mismos montos.
- **FR-10** Historia append-only y auditoría `GOV_WITHHOLDING_*`.
- **FR-11** Aislamiento por tenant y empresa en todas las rutas.
- **FR-12** UI: Gobierno · Tesorería › Retenciones y Políticas de retención; sección Retenciones en el detalle del pago, con bruto, retenciones y neto. Accesible a 1280, 390 y 320.

## Fuera de alcance

Declaración y enteramiento al fisco, libros fiscales, reverso de pagos (TRE-07), penalidades, anticipos y amortizaciones (CNT-06), maestro de terceros (ACC-06), unidad tributaria (PROC-09), bases dependientes entre retenciones, conversión de moneda del monto retenido.

## Decisiones

- **OD-TRE05-01 = A:** datos del beneficiario declarados por liquidación, más el catálogo del ente.
- **OD-TRE05-02 = A:** umbral en moneda o N × tasa oficial TRE-09, congelada.
- **OD-TRE05-03 = A:** liquidación propia, maker-checker, aplicada al registrar.
- **OD-TRE05-04 = A:** tras aplicar, solo se anula y sustituye el comprobante.
