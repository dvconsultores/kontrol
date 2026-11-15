# Plan · CNT-03 Ejecución del contrato

## Constitution Gate

```text
GOV_CNT_003_CLEAR=1   GOV_CNT_007_CLEAR=1
EXECUTION_START_RULE_CLEAR=1 (LCP 127, 137.1, 138.1)
MILESTONE_MODEL_CLEAR=1      DELIVERABLE_MODEL_CLEAR=1
VALUATION_RULE_CLEAR=1 (LCP 142, 143)
PARTIAL_RECEIPT_RULE_CLEAR=1 (bienes/servicios; OD-CNT03-01)
FINAL_RECEIPT_RULE_CLEAR=1 (LCP 146-150; OD-CNT03-01)
INVOICE_LINK_RULE_CLEAR=1 (LCP 141, RLCP 177; OD-CNT03-04)
CLOSURE_RULE_CLEAR=1 (LCP 151, RLCP; OD-CNT03-02)
CNT04_CONSUMER_CLEAR=1   CNT02_BOUNDARY_CLEAR=1 (terminos_efectivos + FOR UPDATE del contrato)
CNT06_NOT_ABSORBED=1   BUD09_NOT_ABSORBED=1   TRE04_NOT_ABSORBED=1
P1_P2_OVERLAP=0   MATERIAL_DECISION_REQUIRED=0 (OD-CNT03-01..04 cerradas por la dueña)
CONSTITUTION_GATE=PASS
```

Principios de la Constitución que aplican:
- Spec-driven.
- Decimal para dinero.
- Aislamiento por empresa.
- Auditoría.
- Sin escrituras fuera del dominio.
- DeepSeek escribe todo el código; Claude audita.

## Modelo de datos (migración `0118_gov_cnt03_ejecucion` sobre `0117_gov_cnt04_supervisor`)

Columnas comunes de instantánea:
- **Supervisor (SUP):** `supervisor_assignment_id` FK gov_contract_supervisors, `supervisor_official_id`, `supervisor_nombre`.
- **Documento (DOC):** `document_id` FK documents, `document_version_id` FK document_versions, `documento_sha256` (64), `documento_titulo` (300).

| Tabla | Columnas principales | Restricciones |
|---|---|---|
| `gov_contract_execution_acts` | company_id, contract_id, tipo INICIO/TERMINACION/CIERRE, fecha, observacion(1000), SUP (nullable solo en CIERRE), DOC; en CIERRE además `aprobacion_*` (DOC del acta de aprobación), `evaluacion_*` (DOC de la evaluación), `aprobador_tipo` COMISION/UNIDAD_CONTRATANTE, `aprobador_nombre`; registrado_en, registrado_por | UNIQUE(contract_id, tipo); CHECK tipo; CHECK de los campos de cierre. Trigger: sin UPDATE, DELETE ni TRUNCATE |
| `gov_contract_milestones` | contract_id, numero, descripcion(500), fecha_prevista, monto_previsto Numeric(18,2) NULL, porcentaje_previsto Numeric(5,2) NULL, obligatorio, estado VIGENTE/ANULADO, motivo_anulacion, anulado_en, anulado_por | UNIQUE(contract_id, numero); CHECK monto > 0; CHECK 0 < porcentaje ≤ 100. Trigger: solo VIGENTE→ANULADO con motivo |
| `gov_contract_deliverables` | contract_id, milestone_id NULL, numero, descripcion(500), fecha_vencimiento, obligatorio, estado VIGENTE/ANULADO, motivo_anulacion, anulado_en, anulado_por | Igual que los hitos |
| `gov_contract_deliverable_submissions` | deliverable_id, contract_id, numero, fecha_entrega, DOC, observacion_entrega, estado ENTREGADA/CONFORME/RECHAZADA, fecha_revision, observacion_revision, SUP (al revisar), revisado_en, revisado_por | UNIQUE(deliverable_id, numero); índice único parcial (deliverable_id) WHERE estado='ENTREGADA' y otro WHERE estado='CONFORME'. Trigger: solo ENTREGADA→CONFORME/RECHAZADA |
| `gov_contract_valuations` | contract_id, milestone_id, numero, periodo_desde, periodo_hasta, fecha, monto Numeric(18,2), moneda(3), DOC, estado PRESENTADA/CONFORMADA/REPARADA/ANULADA, fecha_conformidad, acumulado Numeric(18,2), reparos(1000), motivo_anulacion, SUP (al conformar o reparar), resuelto_en, resuelto_por | UNIQUE(contract_id, numero); CHECK monto > 0; CHECK periodo_desde ≤ periodo_hasta ≤ fecha. Trigger: solo PRESENTADA→CONFORMADA/REPARADA/ANULADA |
| `gov_contract_receipts` | contract_id, numero, tipo PARCIAL/PROVISIONAL/DEFINITIVA, fecha, DOC, observacion, SUP, `representante_cargo_id` FK gov_positions NULL, `representante_cargo_nombre`, `fin_garantia` NULL, estado CONFORME/ANULADA, motivo_anulacion, anulado_en, anulado_por | UNIQUE(contract_id, numero); índice único parcial (contract_id) WHERE tipo='DEFINITIVA' AND estado='CONFORME', y otro igual para PROVISIONAL. Trigger: solo CONFORME→ANULADA |
| `gov_contract_receipt_milestones` | receipt_id, milestone_id, contract_id | UNIQUE(receipt_id, milestone_id). Trigger: sin UPDATE ni DELETE |
| `gov_contract_invoices` | contract_id, numero, numero_documento(40), fecha, monto Numeric(18,2), moneda, milestone_id, receipt_id, DOC, fecha_conformidad, SUP, estado CONFORME/ANULADA, motivo_anulacion, anulado_en, anulado_por | UNIQUE(contract_id, numero); índice único parcial (contract_id, numero_documento) WHERE estado='CONFORME'. Trigger: solo CONFORME→ANULADA |

- Todas las tablas llevan company_id, created_at, updated_at, created_by y version (mixins).
- La migración concede `gobierno_contratos:execute` al rol FUNCIONAL_COMPLETO, igual que 0117.

## Servicio `service_contratos_ejecucion.py`

- `terminos_efectivos(contrato)` → `{monto, moneda, fecha_inicio, fecha_fin, fuente: "CNT01_ORIGINAL"}`. Es la frontera con CNT-02.
- `_conformante(db, ctx, contrato, fecha)` aplica OD-CNT03-03:
  1. `supervisor_en(fecha)`; si es None, BLOCKED `GOV_CONTRACT_EXEC_NO_SUPERVISOR`.
  2. `_funcionario_del_actor`; si difiere del supervisor, BLOCKED `GOV_CONTRACT_EXEC_NOT_SUPERVISOR`.
- `_documento` valida un documento del expediente sin sellar y lo sella (resource_type "GovernmentContract") después del flush.
- Toda mutación bloquea el contrato con FOR UPDATE, comprueba FORMALIZADO y que no haya CIERRE, y exige INICIO salvo en el propio inicio.
- Lecturas: `ejecucion()` (payload completo con resumen derivado), `opciones()` (documentos elegibles y cargos representantes) y `reporte_csv()`.
- Mutaciones: iniciar, crear_hito, anular_hito, crear_entregable, anular_entregable, entregar, revisar_entrega, presentar_valuacion, resolver_valuacion, anular_valuacion, terminar_obra, registrar_recepcion, anular_recepcion, vincular_factura, anular_factura, cerrar.

## API `/gobierno/contratos/{contrato_id}/ejecucion`

- GET `""`, `/opciones` y `/reporte.csv` → `gobierno_contratos:view`.
- 16 POST → `gobierno_contratos:execute` (SENSITIVE, MFA) + `require_write_allowed`.

## Cableado

| Pieza | Cambio |
|---|---|
| Permisos | `gobierno_contratos: [..., "execute"]` |
| MFA | `gobierno_contratos:execute` es SENSITIVE |
| SoD (PROC-03) | PROC03_EJEC_INICIAR, PROC03_EJEC_CONFORMAR, PROC03_EJEC_RECIBIR, PROC03_EJEC_FACTURA, PROC03_EJEC_CERRAR |
| Auditoría | 18 entradas `GOV_CONTRACT_EXEC_*` con `DETALLE_EJECUCION` |

Fijaciones:

| Fijación | Antes | Después |
|---|---|---|
| Catálogo de auditoría | 551 | 569 |
| SENSITIVE | 76 | 77 |
| Techo de delegación | 173 | 174 |
| Lista de CNT-01 | — | + "execute" |
| Cabeza | 0117 | 0118 (3 tests) |

## Frontend

- Ruta `gobierno/contratos/:contratoId/ejecucion` → `EjecucionContratoPage`.
- Desde la ficha del contrato FORMALIZADO, enlace «Ejecución del contrato».
- Secciones, cada una con `<section aria-labelledby>` y h2: Resumen · Inicio · Hitos · Entregables · Valuaciones · Recepciones · Facturas / cuentas vinculadas · Cronología · Cierre.
- Formularios con FormField y ConfirmationDialog en cada formalización.
- Botón «Descargar CSV».

## Concurrencia y frontera con CNT-02

- Cada mutación de CNT-03 toma FOR UPDATE de `gov_contracts`. CNT-02, al formalizar una adenda, debe tomar el mismo bloqueo, y así CNT-03 nunca confirma contra términos obsoletos.
- El guard de CNT-01 prohíbe UPDATE del contrato formalizado: CNT-03 solo lo bloquea y nunca lo escribe.

## Delegación (tope de 8 llamadas)

| Llamada | Contenido |
|---|---|
| C1 | Modelos, migración y cableado con fijaciones |
| C2 | Servicio, esquemas y API |
| C3 | Pruebas PG |
| C4 | Frontend: api, página y Vitest |
| C5 | E2E |
| C6–C8 | Reservadas para correcciones |
