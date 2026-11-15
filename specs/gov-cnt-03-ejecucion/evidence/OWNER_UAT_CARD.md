# Tarjeta de prueba de la dueña · CNT-03 Ejecución del contrato

**Dónde está:** Menú › Gobierno · Contratos › Contratos y órdenes › (contrato **formalizado**) › enlace «Ejecución del contrato».

**Qué necesita antes de empezar:**
- un contrato formalizado (CNT-01) con supervisor designado (CNT-04);
- **una cuenta de usuario vinculada al funcionario supervisor**, en Gobierno › Identidad (vínculo activo). Solo esa cuenta conforma (OD-CNT03-03). Recuerde que nadie puede crear ni activar su propio vínculo;
- documentos adjuntos al expediente del contrato: uno distinto por cada acta o soporte;
- para obras, un cargo con la competencia Aprobar sobre Contrataciones como representante del contratante.

| # | Paso (con la cuenta del supervisor) | Resultado esperado |
|---|---|---|
| 1 | Abra el contrato y pulse «Ejecución del contrato» | Resumen con monto original y efectivo, saldo, supervisor y estado «Sin iniciar» |
| 2 | Registre el inicio con su acta | «Inicio de la ejecución registrado.» Estado «En ejecución» |
| 3 | Cree un hito con monto previsto | Aparece HIT-01 |
| 4 | Cree un entregable del hito y registre una entrega con su evidencia | ENT-01 con la entrega ENT-01/01 «Entregada». La carga **no** lo da por conforme |
| 5 | Pulse «Conformar» › «Confirmar revisión» | «Entrega conformada.» |
| 6 | Presente una valuación del hito (período, monto, soporte) y conforme | «Valuación conformada.» con el acumulado; el saldo baja |
| 7 | Intente presentar una valuación por encima del saldo | Rechazo con el saldo disponible |
| 8 | Registre una recepción parcial marcando el hito | REC-01; el hito queda «Cumplido» |
| 9 | Vincule una factura al hito y a REC-01 por un monto ≤ lo valuado | FAC-01. Nota visible: no genera causado, cuentas por pagar ni pagos |
| 10 | Intente una factura por encima de lo valuado del hito | Rechazo |
| 11 | Registre la recepción definitiva | «Recepción definitiva» |
| 12 | Cierre con el acta de aprobación del cierre y la evaluación de desempeño (documentos distintos) | Estado «Cerrada», con el aprobador (Comisión de Contrataciones o Unidad Contratante) |
| 13 | Revise la cronología y pulse «Descargar CSV» | Todos los hechos en orden y el CSV |
| 14 | Gobierno › Bitácora: filtre por GOV_CONTRACT_EXEC_* | Constan los hechos y los bloqueos |
| 15 | Entre con otra cuenta (no supervisora) e intente conformar | Rechazo: «Solo el supervisor del contrato en esa fecha puede conformar» |

**Obras:** inicio › acta de terminación › aceptación provisional (con representante y fin de garantía) › recepción definitiva, que solo se admite vencida la garantía.

**Qué no hace (a propósito):** retenciones, anticipos, penalidades (CNT-06), rescisión o resolución (CNT-07), causado (BUD-09), pagos (TRE-04) ni movimientos de almacén.

Credenciales: no se registran. Su aceptación (OWNER_ACCEPTED) solo la da usted.
