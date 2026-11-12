# GOVERNMENT_PRODUCT_COMPLETENESS_MATRIX

> Generado desde el CSV homónimo (fuente de verdad legible por máquina). Medición: `develop` `0dbe632`; IR de Gobierno v1.0 SHA `8f86615f…`.

Compuertas en orden: backend · frontend · menú · proceso · campos · roles · documentos · reportes · auditoría · E2E · ficha de pantalla. `✗` = aplicable y en FAIL; `·` = no aplica (justificado: el proceso no produce ni exige documento/reporte).

En **todos** los procesos salvo ORG-01, ORG-02, ORG-03 y DOC-02: `OWNER_UAT_READY = NO`, `OWNER_ACCEPTED = NO`, evidencia = HEAD 0dbe632: 0 rutas, 0 modelos, 0 migraciones, 0 entradas de menú y 0 pantallas de Gobierno. **ORG-01** (GOV-0-01, 2026-10-30): 10/10 compuertas en PASS, `OWNER_UAT_READY = YES`, `OWNER_ACCEPTED = NO` (solo lo concede la dueña); evidencia en `specs/gov-0-01-configurar-ente/evidence/`. **ORG-02** (GOV-0-02, 2026-10-31): 11/11 compuertas en PASS, `OWNER_UAT_READY = YES`, `OWNER_ACCEPTED = NO`; evidencia en `specs/gov-0-02-estructura-organizativa/evidence/`.

## Government Core: ente, estructura y autoridad

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| ORG-01 | Configurar el ente y su tipo | P0 | Administración institucional | GOV-ORG-001 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | GOV-E2E-01..05 | — |
| ORG-02 | Estructura organizativa por ejercicio (órgano, unidad ejecutora, dependencia, sede, centro gestor) | P0 | Administración institucional | GOV-ORG-002 GOV-ORG-008 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | GOV2-E2E-01..07 | Organización privada (empresas, sucursales): otro contrato |
| ORG-03 | Cargos con competencias y límites de firma/aprobación | P0 | Máxima autoridad | GOV-ORG-003 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | GOV3-E2E-01..08 (×3 navegadores ×3 corridas) | — |
| ORG-04 | Delegaciones, suplencias, encargadurías y designaciones con acto | P0 | Máxima autoridad | GOV-ORG-004 GOV-ORG-009 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | OCU-E2E-01..03 (×3 navegadores) + HUMO-UAT-01 | Delegaciones del motor 045 (sin acto administrativo) |
| ORG-05 | Responsables por unidad, programa, cuenta, almacén, caja, contrato y bien, con historia | P0 | Administración institucional | GOV-ORG-006 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | DOMAIN_DEPENDENCY: 8 de 9 objetos sin modelo en Gobierno (BUD-03, ACC-01, WH-02, TRE-08, TRE-01, CNT-01, AST-01); MATERIAL_OQ OQ-ORG05-01..03 (specs/gov-0-04-responsables) | — | — |
| ORG-06 | Vincular usuario con identidad, cargo, unidad y alcance; separación de roles | P0 | Administración institucional | GOV-ORG-007 GOV-ORG-005 | ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | IDE-E2E-01..03 (×3 navegadores) + HUMO-UAT-01 | Usuarios, roles y alcance por empresa (003): otro contrato |
| ORG-07 | Matriz auditable de quién puede solicitar, comprometer, causar, pagar, custodiar, aprobar y auditar | P0 | Control Interno | GOV-ORG-010 | ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | ORG7-E2E-01..05 (×3 navegadores) + HUMO-UAT-01 | — |

## Presupuesto público (Budget Ledger)

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| BUD-01 | Ejercicio económico-financiero | P0 | Planificación/Presupuesto | GOV-BUD-001 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C); LEGAL_VALIDATION_REQUIRED N10 (clase C) | — | — |
| BUD-02 | Clasificador presupuestario versionado | P0 | Planificación/Presupuesto | GOV-BUD-002 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-02; LEGAL_VALIDATION_REQUIRED N10 (clase C) | — | — |
| BUD-03 | Plan, programas, proyectos, metas físicas e indicadores | P0 | Planificación/Presupuesto | GOV-BUD-003 GOV-BUD-004 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C) | — | — |
| BUD-04 | Fuentes de financiamiento y restricciones | P0 | Planificación/Presupuesto | GOV-BUD-005 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C) | — | — |
| BUD-05 | Formulación: anteproyecto, proyecto y presupuesto aprobado con su acto | P0 | Planificación/Presupuesto | GOV-BUD-006 GOV-BUD-007 GOV-BUD-008 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C); LEGAL_VALIDATION_REQUIRED N37 (clase C) | — | — |
| BUD-06 | Disponibilidad y certificación de disponibilidad | P0 | Planificación/Presupuesto | GOV-BUD-009 GOV-BUD-010 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| BUD-07 | Precompromiso / reserva | P0 | Planificación/Presupuesto | GOV-BUD-011 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N37 (clase C) | — | — |
| BUD-08 | Compromiso presupuestario | P0 | Planificación/Presupuesto | GOV-BUD-012 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| BUD-09 | Causado / devengado | P0 | Planificación/Presupuesto | GOV-BUD-013 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N36 (clase C) | E2E-01 | — |
| BUD-10 | Modificaciones presupuestarias con flujo de aprobación (E2E-02) | P0 | Planificación/Presupuesto | GOV-BUD-014 GOV-BUD-015 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-02; LEGAL_VALIDATION_REQUIRED N09 (clase C); LEGAL_VALIDATION_REQUIRED N37 (clase C) | E2E-02 | — |
| BUD-11 | Ledger presupuestario inmutable y reconstruible | P0 | Planificación/Presupuesto | GOV-BUD-016 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | E2E-02 | — |
| BUD-12 | Cierre y reconducción del ejercicio | P0 | Planificación/Presupuesto | GOV-BUD-017 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| BUD-13 | Formularios y reportes ONAPRE | P1 | Planificación/Presupuesto | GOV-BUD-018 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-02; LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C); LEGAL_VALIDATION_REQUIRED N09 (clase C); LEGAL_VALIDATION_REQUIRED N10 (clase C) | — | — |

## Requisiciones públicas

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| REQ-01 | Registrar necesidad/requisición (bienes, servicios u obras) con estimación y especificaciones | P0 | Unidad requirente | GOV-REQ-001 GOV-REQ-003 GOV-REQ-006 GOV-REQ-007 GOV-REQ-008 GOV-REQ-009 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N37 (clase C) | E2E-01 | Requisiciones de compras privadas (004): otro contrato |
| REQ-02 | Verificación presupuestaria previa a la contratación | P0 | Planificación/Presupuesto | GOV-REQ-002 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | E2E-01 | — |
| REQ-03 | Consolidar necesidades compatibles | P1 | Unidad contratante | GOV-REQ-004 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| REQ-04 | Alertas de fraccionamiento | P0 | Control Interno | GOV-REQ-005 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| REQ-05 | Cerrar o cancelar requisición liberando reservas | P0 | Unidad requirente | GOV-REQ-010 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |

## Contrataciones públicas / Licitaciones

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| PROC-01 | Determinar la modalidad de selección y conservar la regla y las excepciones | P0 | Unidad contratante | GOV-PROC-001 GOV-PROC-002 GOV-PROC-016 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N37 (clase C) | — | — |
| PROC-02 | Comisión de contrataciones (miembros, suplentes, impedimentos) | P0 | Máxima autoridad | GOV-PROC-003 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | COM-E2E-01, 02 + HUMO-UAT-01 | — |
| PROC-03 | Expediente único de contratación con cronología y lapsos | P0 | Unidad contratante | GOV-PROC-004 GOV-PROC-014 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| PROC-04 | Pliego, invitaciones, aclaratorias, prórrogas y avisos | P0 | Unidad contratante | GOV-PROC-005 GOV-PROC-015 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-03 | — | — |
| PROC-05 | Oferentes y contratistas (RNC/SNC) | P0 | Unidad contratante | GOV-PROC-006 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-03 | — | Terceros/proveedores privados: otro contrato |
| PROC-06 | Recepción y apertura de ofertas | P0 | Unidad contratante | GOV-PROC-007 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | gobierno-ofertas | Cotizaciones de compras privadas: otro contrato |
| PROC-07 | Evaluación técnica, económica y legal con matriz bloqueada | P0 | Comisión | GOV-PROC-008 GOV-PROC-009 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | gobierno-evaluacion | — |
| PROC-08 | Recomendación, decisión, adjudicación, desierta, anulación o rechazo | P0 | Máxima autoridad | GOV-PROC-010 GOV-PROC-011 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | gobierno-decision | — |
| PROC-09 | Compromiso de responsabilidad social | P1 | Unidad contratante | GOV-PROC-012 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ | 0/10 | BLOCKED | LEGAL_VALIDATION_REQUIRED (U.T. N38 clase C; 3 % LCP 31 frente a 1-5 % RLCP 35); MATERIAL_DECISION_REQUIRED (monto de la oferta, OBS-PROC08-MONTO-01); dependencias PROC-04 y CNT-01 | — | — |
| PROC-10 | Garantías y cauciones | P0 | Unidad contratante | GOV-PROC-013 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | gobierno-garantias | — |
| PROC-11 | Conflictos SoD en contratación | P0 | Control Interno | GOV-PROC-017 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | E2E-07 | Motor SoD 045 (las reglas por proceso son de Gobierno) |
| PROC-12 | Trazabilidad completa de la compra pública (E2E-01) | P0 | Control Interno | GOV-PROC-018 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | E2E-01 | — |

## Contratos públicos

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| CNT-01 | Crear contrato u orden desde la adjudicación | P0 | Unidad contratante | GOV-CNT-001 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Órdenes de compra privadas: otro contrato |
| CNT-02 | Adendas, prórrogas y variaciones versionadas | P0 | Unidad contratante | GOV-CNT-002 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| CNT-03 | Ejecución: hitos, entregables, valuaciones, recepciones y cierre; factura contra recepción | P0 | Administrador/Supervisor de contrato | GOV-CNT-003 GOV-CNT-007 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | E2E-01 | Recepciones y facturas de proveedor privadas: otro contrato |
| CNT-04 | Designación del supervisor del contrato | P0 | Máxima autoridad | GOV-CNT-004 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| CNT-05 | Bloqueo de pagos por encima del monto contractual | P0 | Tesorería | GOV-CNT-005 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| CNT-06 | Penalidades, retenciones, anticipos, amortizaciones y garantías del contrato | P0 | Administrador de contrato | GOV-CNT-006 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N38 (clase C) | — | — |
| CNT-07 | Terminación, resolución o rescisión | P0 | Máxima autoridad | GOV-CNT-008 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| CNT-08 | Expediente contractual completo | P0 | Administrador de contrato | GOV-CNT-009 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| CNT-09 | Alertas de vencimientos | P1 | Administrador de contrato | GOV-CNT-010 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Notificaciones 047 |

## Almacén de consumo público

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| WH-01 | Recepción física contra orden/contrato separando consumo, capitalizable y patrimonial | P0 | Almacén/Recepción | GOV-WH-001 GOV-WH-002 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N15 (clase C) | E2E-03 | Recepción privada (003/004): otro contrato |
| WH-02 | Inventario por almacén y movimientos sin negativo silencioso; consumo por programa | P0 | Almacén/Recepción | GOV-WH-003 GOV-WH-006 GOV-WH-007 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Inventario privado (003/008): otro contrato |
| WH-03 | Salidas autorizadas con destino y beneficiario | P0 | Almacén/Recepción | GOV-WH-004 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| WH-04 | Conteos físicos y conciliación con aprobación de ajustes | P0 | Almacén/Recepción | GOV-WH-005 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Conteos privados (003): otro contrato |
| WH-05 | Kardex reproducible por artículo, almacén y período | P0 | Almacén/Recepción | GOV-WH-008 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Kardex privado (003) |

## Tesorería pública

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| TRE-01 | Cuentas bancarias públicas con autorizados y acto habilitante | P0 | Tesorería | GOV-TRE-001 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | TRE-E2E-01..03 (×3 navegadores) + HUMO-UAT-01 | Cuentas financieras privadas (006): solo como patrón |
| TRE-02 | Programación financiera y disponibilidad de caja | P0 | Tesorería | GOV-TRE-002 | ✓ ✓ ✓ ✓ ✓ ✓ · · ✓ ✓ ✓ | 9/9 | OWNER_UAT_READY | — | PF-E2E-01..03 y TRE-E2E-04 (×3 navegadores) + HUMO-UAT-01 | — |
| TRE-03 | Orden de pago desde obligación causada | P0 | Tesorería | GOV-TRE-003 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| TRE-04 | Pago con maker-checker, medios autorizados y bloqueo de duplicados | P0 | Tesorería | GOV-TRE-004 GOV-TRE-005 GOV-TRE-010 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N37 (clase C) | E2E-01 | Pagos privados (006): otro contrato |
| TRE-05 | Retenciones tributarias/contractuales y comprobantes | P0 | Tesorería | GOV-TRE-006 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N37 (clase C); LEGAL_VALIDATION_REQUIRED N38 (clase C) | — | Retenciones fiscales privadas (007): otro contrato |
| TRE-06 | Conciliación bancaria | P0 | Tesorería | GOV-TRE-007 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Conciliación privada (006): otro contrato |
| TRE-07 | Anulación y reverso de pago | P0 | Tesorería | GOV-TRE-008 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| TRE-08 | Fondos y cajas autorizadas: reposición, rendición y arqueo | P0 | Tesorería | GOV-TRE-009 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | DOMAIN_DEPENDENCY: TRE-03/TRE-04 (orden de pago), BUD (compromiso y causado), ORG-06 (funcionario responsable) | — | Cajas privadas (006): otro contrato |
| TRE-09 | Provenance de tasas BCV | P1 | Tesorería | GOV-TRE-011 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Tasas privadas (038/048) |
| TRE-10 | Trazabilidad del pago hasta presupuesto y contrato | P0 | Control Interno | GOV-TRE-012 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |

## Contabilidad pública

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| ACC-01 | Plan de cuentas, mapeos presupuesto-contabilidad e historial de reglas | P0 | Contabilidad | GOV-ACC-002 GOV-ACC-012 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) | — | — |
| ACC-02 | Asientos de doble partida automáticos y manuales; momentos contables; corrección por reverso | P0 | Contabilidad | GOV-ACC-001 GOV-ACC-003 GOV-ACC-004 GOV-ACC-005 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) | E2E-01 | — |
| ACC-03 | Cierres mensuales y anuales con checklist y reapertura excepcional | P0 | Contabilidad | GOV-ACC-006 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| ACC-04 | Balance de comprobación, estados y auxiliares | P0 | Contabilidad | GOV-ACC-007 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) | — | — |
| ACC-05 | Conciliación presupuesto vs contabilidad vs tesorería vs cuentas por pagar | P0 | Contabilidad | GOV-ACC-008 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| ACC-06 | Terceros y beneficiarios | P0 | Contabilidad | GOV-ACC-009 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N38 (clase C) | — | Terceros privados (009): otro contrato |
| ACC-07 | Multimoneda autorizada | P1 | Contabilidad | GOV-ACC-010 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| ACC-08 | Exportaciones a sistemas rectores | P1 | Contabilidad | GOV-ACC-011 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-04 | — | — |

## Bienes públicos / Activo fijo patrimonial

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| AST-01 | Incorporación del bien: registro, categoría, origen y valor | P0 | Bienes/Patrimonio | GOV-AST-001 GOV-AST-003 GOV-AST-004 GOV-AST-005 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-05; LEGAL_VALIDATION_REQUIRED N15 (clase C); LEGAL_VALIDATION_REQUIRED N17 (clase C); LEGAL_VALIDATION_REQUIRED N36 (clase C) | E2E-03 | Spec 057 activos fijos privados (PLANNED / NOT_STARTED) |
| AST-02 | Codificación y etiquetado SUDEBIP | P0 | Bienes/Patrimonio | GOV-AST-002 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-05; LEGAL_VALIDATION_REQUIRED N15 (clase C) | E2E-03 | — |
| AST-03 | Ubicación y custodia con historial | P0 | Bienes/Patrimonio | GOV-AST-006 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | E2E-03 | — |
| AST-04 | Transferencias internas e inter-ente con acta | P0 | Bienes/Patrimonio | GOV-AST-007 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | E2E-03 | — |
| AST-05 | Inventario físico patrimonial por campaña | P0 | Bienes/Patrimonio | GOV-AST-008 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | E2E-03 | — |
| AST-06 | Revalorización con avalúo | P0 | Bienes/Patrimonio | GOV-AST-009 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N14 (clase C) | E2E-03 | — |
| AST-07 | Arrendamiento de bienes públicos | P1 | Bienes/Patrimonio | GOV-AST-010 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N16 (clase C) | — | — |
| AST-08 | Mantenimiento documental mínimo | P2 | Bienes/Patrimonio | GOV-AST-011 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| AST-09 | Desincorporación (baja, enajenación, pérdida, robo) sin borrado físico | P0 | Bienes/Patrimonio | GOV-AST-012 GOV-AST-013 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-05; LEGAL_VALIDATION_REQUIRED N17 (clase C) | E2E-03 | — |
| AST-10 | Relación con contabilidad y depreciación/valoración | P0 | Contabilidad | GOV-AST-014 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-04; LEGAL_VALIDATION_REQUIRED N36 (clase C) | — | — |
| AST-11 | Actas de entrega de bienes por cambio de autoridad o custodio | P0 | Bienes/Patrimonio | GOV-AST-015 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |

## Expedientes y actos administrativos

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| DOC-01 | Expediente electrónico único con índice, foliado y versiones | P0 | Unidad tramitadora | GOV-DOC-001 GOV-DOC-002 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | N40 acotada: verificación de firma (N40-02, N40-03) y clasificación solo APN (N40-01), en revisión profesional; el expediente base no depende de N40 | — | Gestión documental 046 (almacén y versiones; sin expediente) |
| DOC-02 | Actos administrativos con autoridad, motivación y eficacia | P0 | Máxima autoridad | GOV-DOC-003 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | DOC2-E2E-01..07 (×3 navegadores) + HUMO-UAT-01 | — |
| DOC-03 | Lapsos, suspensiones, subsanaciones y prórrogas | P0 | Unidad tramitadora | GOV-DOC-004 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | DOC-01 (expediente, N40 acotada); calendario oficial sin fuente ni responsable | E2E-05 | — |
| DOC-04 | Notificaciones administrativas con constancia de recepción | P0 | Unidad tramitadora | GOV-DOC-005 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | DOC4-E2E-01..05 (×3 navegadores) + HUMO-UAT-01 | — |
| DOC-05 | Firma electrónica | P1 | Máxima autoridad | GOV-DOC-006 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) | — | — |
| DOC-06 | Preservación y retención de evidencia sin borrado | P0 | Unidad tramitadora | GOV-DOC-007 GOV-DOC-009 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | LEGAL_VALIDATION_REQUIRED N37 (clase C) | — | — |
| DOC-07 | Búsqueda por expediente, acto, tercero, contrato, presupuesto, bien y fecha | P1 | Usuarios autorizados | GOV-DOC-008 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | DOMAIN_DEPENDENCY: objetos de búsqueda inexistentes en Gobierno (DOC-01, CNT-01, BUD-03, AST-01, terceros) | — | Búsqueda documental 046 |
| DOC-08 | Paquete de auditoría exportable | P1 | Control Interno | GOV-DOC-010 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | DOC8-E2E-01..03 (×3 navegadores) + HUMO-UAT-01 | — |

## Control interno, auditoría y rendición

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| CTL-01 | Matriz SoD por proceso y detección previa | P0 | Control Interno | GOV-CTL-001 | ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | SOD-E2E-01..03 (×3 navegadores) + HUMO-UAT-01 | Motor SoD 045 reutilizado solo como patrón |
| CTL-02 | Bitácora institucional append-only con actor, autoridad, unidad y correlación | P0 | Control Interno | GOV-CTL-002 GOV-CTL-003 | ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | BIT-E2E-01 + HUMO-UAT-01 | Bitácora 006/051 (sin autoridad ni unidad) |
| CTL-03 | Administrador técnico sin autoridad funcional | P0 | Control Interno | GOV-CTL-004 | ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | gobierno-separacion | Separación ADMIN de 003 (reutilizada, no duplicada) |
| CTL-04 | Consulta y muestreo read-only del auditor | P0 | Auditor interno/externo | GOV-CTL-005 | ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | CTL4-E2E-01..06 (×3 navegadores) + HUMO-UAT-01 | Pantalla de auditoría privada (no cuenta) |
| CTL-05 | Expediente de cuenta y reportes de rendición | P0 | Control Interno | GOV-CTL-006 GOV-CTL-007 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | gobierno-rendicion + HUMO-UAT-01 | — |
| CTL-06 | Hallazgos y planes de acción correctiva | P1 | Control Interno | GOV-CTL-008 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | CTL6-E2E-01..04 (×3 navegadores) + HUMO-UAT-01 | — |
| CTL-07 | Alertas de operaciones atípicas | P1 | Control Interno | GOV-CTL-009 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| CTL-08 | Historial de cambios de maestros sensibles | P0 | Control Interno | GOV-CTL-010 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | DOMAIN_DEPENDENCY: maestros de proveedores (PROC-01/GOV-ACC-009, N37) y clasificadores (BUD-02, D-GOV-02, N10) inexistentes en Gobierno; significado de «cuentas» sin fijar (OQ-CTL08-01) | — | Auditoría de cambios privada |
| CTL-09 | Actas de entrega por cambio de responsable o autoridad | P0 | Máxima autoridad | GOV-CTL-011 | ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ ✓ | 11/11 | OWNER_UAT_READY | — | gobierno-actas-entrega + HUMO-UAT-01 | — |
| CTL-10 | Controles materiales que impiden cerrar ejercicio o proceso | P0 | Control Interno | GOV-CTL-012 | ✓ ✓ ✓ ✓ ✓ ✓ · · ✓ ✓ ✓ | 9/9 | OWNER_UAT_READY | — | CIE-E2E-01..03 (×3 navegadores) + HUMO-UAT-01 | — |

## Gobierno Digital: trámites e interoperabilidad

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| DIG-01 | Catálogo de trámites con requisitos versionados y captura única | P0 | Unidad de trámites | GOV-DIG-001 GOV-DIG-002 GOV-DIG-008 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-06 | — | — |
| DIG-02 | Solicitud, subsanación y seguimiento del trámite con estado visible (E2E-05) | P0 | Ciudadano / Unidad de trámites | GOV-DIG-006 GOV-DIG-007 GOV-DIG-009 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-06; N40 acotada: clasificación previa a publicar, solo APN (N40-01) | E2E-05 | — |
| DIG-03 | Interoperabilidad: datos del Estado, API, provenance, base de intercambio e inventario | P0 | Integración | GOV-DIG-003 GOV-DIG-004 GOV-DIG-005 GOV-DIG-011 GOV-DIG-012 | ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ ✗ | 0/11 | BLOCKED | D-GOV-08; LEGAL_VALIDATION_REQUIRED N40 (clase C) | E2E-05 | — |

## Gasto de personal e interfaz Atenea

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| HR-01 | Estructura de cargos y plantillas presupuestarias de personal | P0 | Planificación/Presupuesto | GOV-HR-001 GOV-HR-003 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-07_TECHNICAL_CONTRACT (ENGINEERING_PENDING); LEGAL_VALIDATION_REQUIRED N07 (clase C); LEGAL_VALIDATION_REQUIRED N08 (clase C) | — | — |
| HR-02 | Interfaz de nómina Atenea con maker-checker y sin duplicados (E2E-04) | P0 | Contabilidad | GOV-HR-002 GOV-HR-004 GOV-HR-005 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-07_TECHNICAL_CONTRACT (ENGINEERING_PENDING); N40 acotada: clasificación de datos de personal, solo APN (N40-01); transporte sin norma localizada | E2E-04 | — |
| HR-03 | Reportes SISROE y de altos funcionarios | P1 | Recursos humanos | GOV-HR-006 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |

## Integraciones institucionales

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| INT-01 | Atenea: lotes de nómina idempotentes | P0 | Integración | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · · ✗ ✗ ✗ | 0/9 | BLOCKED | D-GOV-07_TECHNICAL_CONTRACT (ENGINEERING_PENDING) | E2E-04 | — |
| INT-02 | Bancos: archivos/APIs con contrato del banco | P0 | Integración | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · · ✗ ✗ ✗ | 0/9 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| INT-03 | SNC/RNC: consulta de contratistas con provenance | P1 | Integración | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · · ✗ ✗ ✗ | 0/9 | BLOCKED | D-GOV-03 | — | — |
| INT-04 | SUDEBIP: reportes y codificación por mecanismo oficial | P1 | Integración | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · · ✗ ✗ ✗ | 0/9 | BLOCKED | D-GOV-05 | — | — |
| INT-05 | ONAPRE/ONCOP: formatos oficiales versionados | P1 | Integración | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · · ✗ ✗ ✗ | 0/9 | BLOCKED | D-GOV-02; D-GOV-04 | — | — |
| INT-06 | Interoperabilidad del Estado (N26/N28) | P0 | Integración | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · · ✗ ✗ ✗ | 0/9 | BLOCKED | D-GOV-08 | — | — |
| INT-07 | Firma electrónica: proveedor o certificado homologado | P1 | Integración | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · · ✗ ✗ ✗ | 0/9 | BLOCKED | D-GOV-08 | — | — |

## Reportes y tableros institucionales

| Id | Proceso | Prio. | Actor principal | Requisitos | Compuertas | PASS | Estado real | Bloqueos | E2E | Equivalente privado (no cuenta) |
|---|---|---|---|---|---|---|---|---|---|---|
| REP-01 | Ejecución presupuestaria (aprobado, modificado, comprometido, causado, pagado, disponible) | P1 | Planificación/Presupuesto | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-02 | E2E-02 | Motor de reportes 050 |
| REP-02 | Plan vs presupuesto vs ejecución físico-financiera | P1 | Planificación/Presupuesto | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-02 | — | Motor de reportes 050 |
| REP-03 | Contrataciones por modalidad, estado, unidad, proveedor, monto y tiempos | P1 | Unidad contratante | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Motor de reportes 050 |
| REP-04 | Contratos: comprometido, ejecutado, pagado, garantías y vencimientos | P1 | Administrador de contrato | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Motor de reportes 050 |
| REP-05 | Obligaciones causadas pendientes de orden o pago | P1 | Tesorería | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | CxP privadas (004): otro contrato |
| REP-06 | Tesorería: disponibilidad, pagos, conciliaciones y partidas en tránsito | P1 | Tesorería | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | Reportes de tesorería privados (006) |
| REP-07 | Contabilidad: balance, diario, mayor, auxiliares y cierres | P1 | Contabilidad | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-04 | — | — |
| REP-08 | Bienes públicos: inventario, custodios, ubicaciones, diferencias y desincorporaciones | P1 | Bienes/Patrimonio | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-05 | — | — |
| REP-09 | Rendición de cuentas por responsable y período | P1 | Control Interno | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | NOT_STARTED | entrada general: GOVERNMENT_IMPLEMENTATION_AUTHORIZED = 0 | — | — |
| REP-10 | Control interno: overrides, conflictos SoD, duplicados, hallazgos | P1 | Control Interno | IR §11/§12 | ✓ ✓ ✓ ✓ ✓ ✓ · ✓ ✓ ✓ ✓ | 10/10 | OWNER_UAT_READY | — | gobierno-control-interno + HUMO-UAT-01 | — |
| REP-11 | Trámites: volumen, tiempos, subsanaciones y cuellos de botella | P1 | Unidad de trámites | IR §11/§12 | ✗ ✗ ✗ ✗ ✗ ✗ · ✗ ✗ ✗ ✗ | 0/10 | BLOCKED | D-GOV-06 | — | — |

## Matriz E2E de producto (§65)

Para los 122 procesos: HAPPY_PATH, WRONG_ROLE, WRONG_SCOPE, INVALID_STATE, INVALID_DATA, DOCUMENT_FLOW, REPORT_FLOW y AUDIT_FLOW = **NOT_RUN** (no existe pantalla ni API que recorrer); navegadores: ninguno; estado: FAIL. La columna «E2E» de arriba enlaza cada proceso con los casos E2E-01..08 de la IR §13.
