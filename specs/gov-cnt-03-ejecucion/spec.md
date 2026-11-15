# Spec · CNT-03 Ejecución del contrato (GOV-CNT-003 + GOV-CNT-007)

**Autorización:** encargo «KONTROL — PROGRAMADOR 1 · GOBIERNO · CNT-03 · EJECUCIÓN DEL CONTRATO» de la dueña (2026-11-15).
**Fuentes y decisiones:** `FUENTES.md` (OD-CNT03-01..04).

## Historia del sponsor

El supervisor del contrato y la unidad contratante recorren, sobre un contrato formalizado:

INICIO → HITOS → ENTREGABLES → VALUACIONES → RECEPCIONES (parciales en bienes y servicios; terminación y aceptación provisional en obras) → RECEPCIÓN DEFINITIVA → CIERRE OPERATIVO.

Además vinculan cada factura o cuenta de cobro a un hito y a una recepción conforme. Esto no crea causado, cuentas por pagar, asientos, pagos ni movimientos de almacén.

## Requisitos funcionales

| FR | Requisito | Contrato |
|---|---|---|
| FR-01 | Solo un contrato FORMALIZADO de CNT-01 admite ejecución; si no, 409 `GOV_CONTRACT_EXEC_NOT_FORMALIZED` | C03-01 |
| FR-02 | Los términos efectivos (monto, moneda, inicio, fin) salen de `terminos_efectivos(contrato, fecha)`. Hoy la fuente es el original de CNT-01; CNT-02 la ampliará (frontera) | C03-02, C03-18 |
| FR-03 | Toda conformidad resuelve `supervisor_en(contrato, fecha_del_hecho)` y exige que el actor sea el usuario vinculado a ese funcionario (OD-CNT03-03). Sin supervisor o con otro actor, se bloquea y se audita BLOCKED | C03-03 |
| FR-04 | Inicio único: fecha real entre la formalización y min(hoy, fin efectivo), con acta obligatoria y observación opcional. Lo registra el supervisor de esa fecha. Todo hecho posterior exige el inicio y una fecha ≥ inicio y ≤ hoy | C03-04 |
| FR-05 | Hitos HIT-NN: descripción, fecha prevista, monto y porcentaje previstos opcionales, obligatorio sí/no. La suma de montos previstos vigentes ≤ monto efectivo; el porcentaje está entre 0 y 100. Anulable con motivo si no tiene hechos asociados. «Cumplido» se deriva de una recepción conforme que lo incluye | C03-05 |
| FR-06 | Entregables ENT-NN, opcionalmente de un hito: descripción, vencimiento y obligatorio. Las entregas (fecha y evidencia) las revisa el supervisor: CONFORME o RECHAZADA, con observación obligatoria al rechazar. Solo una entrega abierta por entregable y solo una conforme. Una carga documental no acepta nada por sí sola | C03-06 |
| FR-07 | Valuaciones VAL-NN de un hito: período, fecha, monto (Decimal > 0, en la moneda del contrato) y soporte. Estados: PRESENTADA → CONFORMADA (supervisor, acumulado) o REPARADA (reparos obligatorios); también PRESENTADA → ANULADA (motivo) | C03-07 |
| FR-08 | Σ(PRESENTADA + CONFORMADA) + nueva ≤ monto efectivo al presentar, y Σ CONFORMADA + esta ≤ monto efectivo al conformar. Decimal, sin float ni redondeo; bajo FOR UPDATE del contrato | C03-08 |
| FR-09 | Recepción PARCIAL (solo bienes y servicios): acta, fecha, supervisor, observación y al menos un hito vigente no cumplido. Los entregables obligatorios de esos hitos deben estar CONFORME. Anulable con motivo si no hay facturas ni definitiva | C03-09 |
| FR-10 | Obras: acta de TERMINACIÓN (supervisor) → recepción PROVISIONAL (supervisor más representante del contratante con Aprobar × Contrataciones, fin de garantía ≥ fecha, hitos restantes y obligatorios completos) → DEFINITIVA solo con PROVISIONAL y fecha ≥ fin de garantía. Bienes y servicios: DEFINITIVA = certificación del cumplimiento, que completa los hitos restantes y exige obligatorios conformes. En ambos flujos: sin valuaciones PRESENTADA ni entregas abiertas, y una sola DEFINITIVA (índice único) | C03-10 |
| FR-11 | Factura FAC-NN: número del documento, fecha, monto (moneda del contrato), hito, recepción CONFORME del mismo contrato que incluye ese hito, soporte y conformidad del supervisor a la fecha de conformidad. Σ facturas del hito ≤ Σ valuaciones CONFORMADA del hito (OD-CNT03-04). Número único por contrato. Anulable con motivo | C03-11 |
| FR-12 | Ningún efecto contable, presupuestario, de pago ni de almacén | C03-12, C03-19 |
| FR-13 | Cierre operativo único: DEFINITIVA previa, fecha ≥ fecha de la DEFINITIVA, acta de aprobación del cierre y evaluación de desempeño (dos documentos distintos), aprobador derivado del expediente (Comisión si `committee_id`, si no la Unidad Contratante) y un supervisor válido a la fecha. Después del cierre no se admiten más hechos | C03-13 |
| FR-14 | Historia inmutable: los triggers PG solo permiten las transiciones listadas; sin DELETE ni TRUNCATE. Las correcciones se hacen por anulación con motivo | C03-14 |
| FR-15 | Concurrencia: FOR UPDATE del contrato en cada mutación. Dos valuaciones concurrentes no sobreejecutan; de dos definitivas, una gana y la otra recibe 409 | C03-15 |
| FR-16 | Aislamiento por `company_id`; un contrato de otro ente responde 404 | C03-16 |
| FR-17 | Auditoría CTL-02 de cada hecho y de los bloqueos, más la cronología del expediente | C03-17 |
| FR-18 | Pantalla «Ejecución del contrato» con resumen, inicio, hitos, entregables, valuaciones, recepciones, facturas, cronología y cierre; reporte CSV de la ejecución; E2E del sponsor con Axe a 1280/390/320 | C03-20 |

## Fuera de alcance

- CNT-02 (adendas), CNT-05 (tope de pagos), CNT-06 (anticipos, retenciones, penalidades y garantías), CNT-07 (rescisión y resolución), CNT-08 (expediente completo) y CNT-09 (alertas).
- BUD-09 (causado), TRE-04 (pago), contabilidad y almacén.
- La evaluación de desempeño solo se adjunta como documento, sin modelo de puntuación.

## Criterios de éxito

- SC-01: el recorrido del sponsor de 16 pasos (encargo §35) pasa en E2E.
- SC-02: ningún camino permite sobrevaluar el contrato ni facturar por encima de lo valuado del hito.
- SC-03: cero escrituras en tablas de presupuesto, tesorería, contabilidad o almacén.
