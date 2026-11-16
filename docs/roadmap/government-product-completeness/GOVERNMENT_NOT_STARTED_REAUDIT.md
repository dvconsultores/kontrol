# Reauditoría de los 30 procesos NOT_STARTED (GOV-ROADMAP-REBASELINE-02)

> Generado desde `GOVERNMENT_NOT_STARTED_REAUDIT.csv` (autoridad legible por máquina). Autoridad del estado vigente de cada proceso: `GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX.csv`, columna `REBASELINE_02_STATUS`.

El bloqueo heredado de todos («entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0») estaba obsoleto: la línea Gobierno está autorizada y en desarrollo desde GOV-0-01. Se ordenan por nivel del DAG real (nivel 1 = todas sus dependencias internas ya son OWNER_UAT_READY).

## Recuentos

| Estado nuevo | De los 48 BLOCKED | De los 30 NOT_STARTED | Total de los 78 |
|---|---|---|---|
| BUILDABLE_NOW | 18 | 3 | 21 |
| WAITING_INTERNAL_DEPENDENCY | 17 | 26 | 43 |
| TENANT_CONFIGURATION_PENDING | 0 | 0 | 0 |
| NORMATIVE_VALIDATION_PENDING | 4 | 0 | 4 |
| EXTERNAL_INTEGRATION_PENDING | 9 | 1 | 10 |
| TRUE_BLOCKED | 0 | 0 | 0 |
| **Total** | **48** | **30** | **78** |

## Reauditoría (ordenada por nivel DAG)

| Id | Prio. | Proceso | Nivel DAG | Dependencias | Parametrización / ente | Motor de procesos | Normativa | Integración externa | Estado nuevo | Motivo |
|---|---|---|---|---|---|---|---|---|---|---|
| BUD-11 | P0 | Ledger presupuestario inmutable y reconstruible | 1 | BUD-05, BUD-06, BUD-08 (READY) | momentos habilitados por ente | ledger reconstruible de los eventos existentes (aprobado, certificado, comprometido) con prueba de reconstrucción; reverso como evento | N03 (A) | — | BUILDABLE_NOW | Consolida los eventos presupuestarios ya publicados; base de BUD-09 y REP-01 |
| REP-04 | P1 | Contratos: comprometido, ejecutado, pagado, garantías y vencimientos | 1 | CNT-01..09 (READY); ampliación posterior: columna pagado con TRE-04 | cortes del ente | reporte sobre contratos existentes | — | — | BUILDABLE_NOW | Comprometido, ejecutado, garantías y vencimientos ya existen; la columna pagado se completa con TRE-04. No se construye en este ciclo |
| WH-02 | P0 | Inventario por almacén y movimientos sin negativo silencioso; consumo por programa | 1 | ORG-02 (READY) | almacenes, artículos y unidades del ente | modelo de almacén, artículo y movimiento sin negativo silencioso | N15 (C) para clasificar | — | BUILDABLE_NOW | Modelo genérico; la frontera con el almacén Enterprise ya está fijada en la línea base. Base de WH-01..05 y de ORG-05 |
| AST-03 | P0 | Ubicación y custodia con historial | 2 | AST-01, ORG-05 | ubicaciones del ente | ubicación y custodia con historia (ResponsibilityBinding) | N15 (C) | — | WAITING_INTERNAL_DEPENDENCY | Necesita el bien |
| AST-08 | P2 | Mantenimiento documental mínimo | 2 | AST-01 | tipos documentales | documentos del bien | — | — | WAITING_INTERNAL_DEPENDENCY | Necesita el bien |
| HR-03 | P1 | Reportes SISROE y de altos funcionarios | 2 | HR-01 | funcionarios alcanzados | reporte versionado | — | formato SISROE oficial | WAITING_INTERNAL_DEPENDENCY | Necesita HR-01; el formato SISROE es plantilla versionada |
| REP-09 | P1 | Rendición de cuentas por responsable y período | 2 | ORG-05, CTL-05 (READY) | períodos | rendición por responsable | N21 (A) | — | WAITING_INTERNAL_DEPENDENCY | Necesita los responsables (ORG-05) |
| REQ-02 | P0 | Verificación presupuestaria previa a la contratación | 2 | REQ-01, BUD-06 (READY) | tolerancias | ControlRule previa a la contratación | N03, N11 (A) | — | WAITING_INTERNAL_DEPENDENCY | Necesita la requisición |
| REQ-03 | P1 | Consolidar necesidades compatibles | 2 | REQ-01 | criterios de compatibilidad | regla de consolidación | N11 (A) | — | WAITING_INTERNAL_DEPENDENCY | Necesita la requisición |
| REQ-04 | P0 | Alertas de fraccionamiento | 2 | REQ-01, PROC-01 | ventanas y umbrales adoptados | ControlRule de fraccionamiento | N11, N12 (A) | — | WAITING_INTERNAL_DEPENDENCY | Necesita la requisición y los umbrales de modalidad |
| REQ-05 | P0 | Cerrar o cancelar requisición liberando reservas | 2 | REQ-01, BUD-07 | causas de cancelación | transiciones de cierre y liberación | N03 (A) | — | WAITING_INTERNAL_DEPENDENCY | Necesita la requisición y la reserva |
| TRE-03 | P0 | Orden de pago desde obligación causada | 2 | BUD-09 | documentos exigidos | orden de pago desde causado | N03 (A) | — | WAITING_INTERNAL_DEPENDENCY | Necesita el causado (BUD-09) |
| WH-03 | P0 | Salidas autorizadas con destino y beneficiario | 2 | WH-02 | destinos y aprobadores | salida con destino y aprobación | — | — | WAITING_INTERNAL_DEPENDENCY | Necesita WH-02 |
| WH-04 | P0 | Conteos físicos y conciliación con aprobación de ajustes | 2 | WH-02 | frecuencia y tolerancia | conteo y ajuste aprobado | — | — | WAITING_INTERNAL_DEPENDENCY | Necesita WH-02 |
| WH-05 | P0 | Kardex reproducible por artículo, almacén y período | 2 | WH-02 | método de valoración adoptado | kardex reconstruible | — | — | WAITING_INTERNAL_DEPENDENCY | Necesita WH-02 |
| ACC-03 | P0 | Cierres mensuales y anuales con checklist y reapertura excepcional | 3 | ACC-02 | checklist adoptado | ProcessDefinition del cierre contable | N36 (C) | — | WAITING_INTERNAL_DEPENDENCY | Necesita los asientos |
| ACC-07 | P1 | Multimoneda autorizada | 3 | ACC-02, TRE-09 (READY) | monedas autorizadas | moneda en asientos con tasa con procedencia | — | — | WAITING_INTERNAL_DEPENDENCY | Necesita los asientos |
| AST-04 | P0 | Transferencias internas e inter-ente con acta | 3 | AST-01, AST-03 | tipos de transferencia | transferencia con acta (DOC-02) | N17 (C) | — | WAITING_INTERNAL_DEPENDENCY | Necesita el bien y su custodia |
| AST-05 | P0 | Inventario físico patrimonial por campaña | 3 | AST-03 | calendario de campañas | campaña de inventario físico | N15 (C) | — | WAITING_INTERNAL_DEPENDENCY | Necesita la custodia |
| AST-11 | P0 | Actas de entrega de bienes por cambio de autoridad o custodio | 3 | AST-03, CTL-09 (READY) | — | acta de entrega reutilizando CTL-09 | N21 (A) | — | WAITING_INTERNAL_DEPENDENCY | Necesita la custodia |
| REP-05 | P1 | Obligaciones causadas pendientes de orden o pago | 3 | BUD-09, TRE-03 | — | reporte de obligaciones | — | — | WAITING_INTERNAL_DEPENDENCY | Necesita el causado y la orden de pago |
| ACC-05 | P0 | Conciliación presupuesto vs contabilidad vs tesorería vs cuentas por pagar | 4 | ACC-02, TRE-04, BUD-09 | tolerancias | conciliación entre ledgers | N36 (C) | — | WAITING_INTERNAL_DEPENDENCY | Necesita los tres ledgers |
| BUD-12 | P0 | Cierre y reconducción del ejercicio | 4 | BUD-09, TRE-04, CTL-10 (READY) | fechas y reglas de reconducción adoptadas | ProcessDefinition del cierre con checklist; ControlRule de CTL-10 | N03 (A); N09 (C) | — | WAITING_INTERNAL_DEPENDENCY | El cierre necesita causado y pagado |
| CNT-05 | P0 | Bloqueo de pagos por encima del monto contractual | 4 | TRE-03, TRE-04, CNT-01 (READY) | tolerancias adoptadas | ControlRule de bloqueo sobre la orden de pago | N11 (A) | — | WAITING_INTERNAL_DEPENDENCY | Necesita la orden de pago |
| INT-02 | P0 | Bancos: archivos/APIs con contrato del banco | 4 | TRE-01 (READY), TRE-04 | bancos y formatos | IntegrationContract por banco | — | contrato técnico de cada banco | EXTERNAL_INTEGRATION_PENDING | Conector externo por banco |
| PROC-12 | P0 | Trazabilidad completa de la compra pública (E2E-01) | 4 | REQ-01, PROC-01, PROC-04, BUD-09, TRE-03, TRE-04 | — | ProcessInstance/ProcessHistory transversal (E2E-01) | N11, N12 (A) | — | WAITING_INTERNAL_DEPENDENCY | Es la trazabilidad de toda la cadena; es la prueba de que la cadena existe |
| TRE-06 | P0 | Conciliación bancaria | 4 | TRE-01 (READY), TRE-04 | formato de extracto por banco | conciliación de movimientos | — | formato de extracto (manual primero) | WAITING_INTERNAL_DEPENDENCY | Necesita los pagos |
| TRE-07 | P0 | Anulación y reverso de pago | 4 | TRE-04 | causas y aprobaciones | reverso de pago como evento | N03 (A) | — | WAITING_INTERNAL_DEPENDENCY | Necesita el pago |
| TRE-10 | P0 | Trazabilidad del pago hasta presupuesto y contrato | 4 | TRE-04, BUD-09, CNT-01 (READY) | — | trazabilidad pago→causado→compromiso→contrato | — | — | WAITING_INTERNAL_DEPENDENCY | Necesita el pago |
| REP-06 | P1 | Tesorería: disponibilidad, pagos, conciliaciones y partidas en tránsito | 5 | TRE-04, TRE-06 | — | reporte de tesorería | — | — | WAITING_INTERNAL_DEPENDENCY | Necesita pagos y conciliación |
