# Delta · Reporte formal de diferencias de importación

**Spec dueña:** 018. Consume, sin modificarlas, las autoridades de las Specs 019 (`GoodsReceipt`, `GoodsReceiptLine`), 020 (`ReceiptIncident`), 021 (conciliación) y 046 (`DocumentLink`, `get_storage`). **Autorización de implement:** encargo de la dueña del 2026-11-09, que nombra la iniciativa `SPEC018_REPORTE_FORMAL_DIFERENCIAS`. `MATERIAL_DECISION_REQUIRED = 0`: cada decisión de abajo es `SOURCE_BACKED_RULE` (SBR) o `DERIVED_TECHNICAL_DECISION` (DTD).

## Resultado para la dueña

En Compras → Importaciones → Expediente → Diferencias e inventario, por recepción, la usuaria puede:

- emitir el reporte formal de diferencias;
- consultarlo;
- descargar e imprimir el PDF;
- ver sus revisiones.

Desde Compras → Recepciones, en una recepción que pertenece a un expediente, puede ver los reportes de esa recepción, descargarlos y abrir el expediente.

## Requisitos

- **FR-DR-01:** se emite solo si la recepción tiene diferencias reales (DR-01). Si no las tiene, responde 422 `DIFFERENCE_REPORT_NO_DIFFERENCES` y no escribe nada.
- **FR-DR-02:** cada emisión es una instantánea inmutable. Las tablas de la instantánea no tienen ruta de edición, y la API no ofrece actualizar ni borrar.
- **FR-DR-03:** una revisión nueva se vincula a la anterior con `supersedes_id`, y la anterior se conserva.
- **FR-DR-04:** si nada cambió desde la última emisión, la API devuelve 409 `DIFFERENCE_REPORT_UNCHANGED`, con la referencia vigente. Esto evita la doble emisión.
- **FR-DR-05:** si la recepción cambió entre la consulta y la emisión, la API devuelve 409 `DIFFERENCE_REPORT_STALE`. Se detecta con `expected_snapshot_hash`.
- **FR-DR-06:** el PDF se genera una sola vez, al emitir. Se guarda con su sha256, y al descargarlo se verifica contra la huella.
- **FR-DR-07:** lectura y descarga exigen `compras:view`; emitir exige `compras:create`. Todo está aislado por empresa.
- **FR-DR-08:** se auditan la emisión, la reemisión y la descarga.
- **FR-DR-09:** la emisión no exige que las incidencias estén resueltas. Sin tratamiento, el reporte muestra «Pendiente».

## Decisiones

### Datos de origen

| ID | Decisión | Tipo | Motivo |
|---|---|---|---|
| DR-01 | Una recepción **tiene diferencias** si cumple al menos una de dos condiciones. **(a)** Tiene una `ReceiptIncident` con `status ≠ ANULADA`. **(b)** Tiene una línea que cumple alguna de estas: `count_difference_kinds` no vacío, `overage_base_quantity > 0` o `damaged_quantity > 0`. | SBR | La Spec 019 registra lo observado: conteo, sobrante y daño. La Spec 020 formaliza la excepción. Una incidencia anulada no es una diferencia vigente. |
| DR-02 | **Línea con diferencia:** la que tiene una incidencia no anulada o cumple la condición (b). La `DIFERENCIA_DOCUMENTAL` va en la sección de incidencias, sin línea y sin cantidad. | SBR | El `CHECK line_and_quantity_by_type` de la Spec 020 lo exige así. |
| DR-03 | La emisión exige recepción no anulada (`RECEIPT_CANCELLED`, 409), recepción del expediente (`IMPORT_RECEIPT_NOT_IN_FILE`, 404) y expediente no anulado (`IMPORT_CANCELLED`, 409). | DTD | Sobre una recepción anulada no hay hecho que reportar. Una recepción ajena se responde con 404, para no revelar su existencia. |
| DR-04 | **Cantidades**, siempre en unidad base y leídas tal como se guardaron: pedido (`PurchaseOrderLine.base_quantity_ordered`, o `quantity_ordered` si es nulo); recibido (`base_quantity_received`, o `quantity_received`); contado; aceptado; rechazado; dañado; sobrante. | SBR | Es la misma regla que `_base_recibida` de la Spec 021. No se recalcula con el maestro vigente. |
| DR-05 | **Presentación y unidad**: `Presentation.code`, unidad base `UnitOfMeasure.symbol` y el factor congelado de la línea. Si falta alguno, se muestra «—». | SBR | Es el snapshot de la Spec 019. |
| DR-06 | **Responsables** por su `User.username`, resuelto con el `tenant_id` del emisor. Si el usuario no se encuentra, se muestra «Usuario no disponible». Nunca un UUID. | SBR | Mismo patrón que `_usuarios_por_ids` de Government. KONTROL no tiene nombre completo de usuario. |
| DR-07 | **Autorización** de un tratamiento: estado de su `ApprovalRequest` si existe (`approval_request_id`); si no, «No requerida». | SBR | El motor único de aprobaciones es la autoridad (Spec 020, control 115). |
| DR-08 | **Evidencias:** cada `DocumentLink` de `resource_type` `ReceiptIncident` o `GoodsReceipt` de la recepción se copia como referencia legible: recurso, código, título del documento y versión vigente con su nombre de archivo y sha256. No se copia ningún binario. Sin evidencias, el PDF lo dice. | SBR | La Spec 046 es la autoridad del binario. |

### Instantánea, referencia y PDF

| ID | Decisión | Tipo | Motivo |
|---|---|---|---|
| DR-09 | La instantánea es **relacional y tipada**, en cuatro tablas: cabecera, líneas, incidencias y evidencias. No hay JSON libre. | DTD | Lo pide el encargo. Además permite consultarla sin reabrir el PDF. |
| DR-10 | `snapshot_hash` es el sha256 del contenido canónico: cabecera de negocio, líneas, incidencias y evidencias, ordenadas, con decimales normalizados. Excluye la emisión: momento, emisor, referencia y revisión. | DTD | Así dos emisiones del mismo estado dan el mismo hash. Es la base de FR-DR-04 y FR-DR-05. |
| DR-11 | **Referencia interna**: `DIF-{n:06d}-R{revision}`, con `n` el número de la cadena dentro de la empresa. `n` se asigna en la revisión 1 y se conserva en las siguientes. No es un folio legal. Unicidad: `(company_id, reference)` y `(company_id, chain_number, revision)`. | DTD | El código de recepción no es único por empresa, así que no sirve como referencia. Un correlativo por empresa sí lo es, y se lee bien. |
| DR-12 | Concurrencia: la emisión bloquea con `FOR UPDATE` la empresa, el expediente y la recepción, en ese orden. Dos emisiones simultáneas se serializan. La segunda ve la primera y responde `DIFFERENCE_REPORT_UNCHANGED`. Si la base rechaza por unicidad, responde 409 `DIFFERENCE_REPORT_CONCURRENT`. | DTD | El bloqueo de la empresa serializa también el correlativo. La unicidad es la red de seguridad. |
| DR-13 | PDF con **ReportLab platypus**, el motor de `reporting/service.py`, en carta vertical y con plantilla propia. Se guarda con `documents.storage.get_storage()` y `generate_storage_key`, y se verifica después de escribir, igual que los paquetes de Government. La descarga verifica la huella antes de abrir (`STORAGE_HASH_MISMATCH`, 500) y responde con `StreamingResponse`. `?inline=true` sirve para imprimir. | SBR | Así no hay motor, almacenamiento ni descarga nuevos. |
| DR-14 | Sin flujo de aprobación (`APPROVAL_REQUIRED_FOR_DIFFERENCE_REPORT = 0`). Tampoco hay firma: el reporte identifica al emisor y el momento de emisión. | Encargo | — |
| DR-15 | **Estados de la pantalla**, calculados al consultar:<br>• `NO_DIFFERENCES`: no hay diferencias;<br>• `DIFFERENCES_WITHOUT_REPORT`: hay diferencias y ningún reporte;<br>• `REPORT_ISSUED`: el último reporte coincide con el hash actual;<br>• `NEW_REVISION_AVAILABLE`: el hash actual difiere del último reporte y sigue habiendo diferencias.<br>Si hubo reporte y las diferencias desaparecieron, el estado es `NO_DIFFERENCES` y el historial se conserva. | DTD | Son los cuatro estados del encargo. |
| DR-16 | El momento de emisión se guarda en UTC y se muestra en `America/Caracas` con `zona_de_negocio()`. | SBR | Es la zona de negocio de KONTROL. |

## Modelo de datos (una migración, id ≤ 32 caracteres)

- **`import_difference_reports`**: `company_id`, `import_file_id`, `receipt_id`, `chain_number`, `revision`, `reference`, `supersedes_id` (FK a sí misma), `issued_at`, `issued_by` y `issued_by_name`. Copia de la cabecera: `company_name`, `file_code`, `order_code`, `supplier_name`, `receipt_code`, `warehouse_name`, `line_count`, `incident_count` y `evidence_count`. Integridad: `snapshot_hash`, `storage_key` (único), `file_sha256`, `file_size` y `file_name`. Timestamps con `now()` y `created_by`. `CHECK revision >= 1` y `CHECK chain_number >= 1`.
- **`import_difference_report_lines`**: `company_id`, `report_id`, `position`, `receipt_line_id`, `product_code`, `product_name`, `presentation_code`, `base_uom`, `conversion_factor`, `ordered_base`, `received_base`, `counted_base`, `accepted_base`, `rejected_base`, `damaged_base`, `overage_base`, `difference_kinds`, `physical_condition` y `observation`. Único por `(report_id, position)`.
- **`import_difference_report_incidents`**: `company_id`, `report_id`, `position`, `incident_id`, `code`, `incident_type`, `receipt_line_id`, `product_name`, `affected_base_quantity`, `description` y `status`. Escalamiento: `escalated_at`, `escalated_by_name` y `escalation_notes`. Tratamiento: `resolution` (nulo = «Pendiente»), `resolution_reason` y `authorization_status`. Resolución: `resolved_at` y `resolved_by_name`. Además, `registered_by_name`. Único por `(report_id, position)`.
- **`import_difference_report_evidence`**: `company_id`, `report_id`, `position`, `resource_type`, `resource_code`, `document_title`, `version_number`, `file_name` y `sha256`. Único por `(report_id, position)`.

## API (bajo `/importaciones/{file_id}`)

| Ruta | Permiso | Efecto |
|---|---|---|
| `GET /receipts/{receipt_id}/difference-report` | `compras:view` | Devuelve el estado (DR-15), `current_snapshot_hash`, las diferencias actuales y el historial de revisiones |
| `POST /receipts/{receipt_id}/difference-report` | `compras:create` | Emite. Cuerpo: `{expected_snapshot_hash}`, opcional |
| `GET /difference-reports/{report_id}` | `compras:view` | Devuelve la instantánea completa |
| `GET /difference-reports/{report_id}/pdf?inline=` | `compras:view` | Descarga el PDF, verifica su huella y lo audita |

Fuera del expediente:

| Ruta | Permiso | Efecto |
|---|---|---|
| `GET /importaciones/receipt-difference-reports/{receipt_id}` | `compras:view` | Desde Recepciones: devuelve el expediente de la recepción, si existe, y sus reportes |

Auditoría: `IMPORT_DIFFERENCE_REPORT_ISSUED` (revisión 1), `IMPORT_DIFFERENCE_REPORT_REISSUED` (revisión mayor que 1) e `IMPORT_DIFFERENCE_REPORT_DOWNLOADED`. Se registran con `service._audit` sobre la entidad `ImportFile`, que es el patrón de landed cost, para que el evento aparezca en el Historial del expediente. `after` lleva `report_id`, `reference`, `revision` y `receipt_code`. El catálogo pasa de 419 a 422 entradas.

## Tareas

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T-DR-A | Modelo, migración, instantánea, PDF, API, descarga y auditoría | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `imports/models.py`, `imports/difference_report.py`, `imports/api.py`, migración, catálogo, pruebas | `tests/test_importaciones_difference_report.py` sobre PostgreSQL | Emisión, revisión, negativas y PDF válido |
| T-DR-B | Sección del expediente y acceso desde Recepciones | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `ImportacionDiferencias.tsx`, `tipos.ts`, `RecepcionesPage.tsx`, pruebas Vitest | Vitest dirigido | Los cuatro estados, la descarga y el historial |
| T-DR-C | E2E de usuario en Chrome | DEEPSEEK | deepseek-v4-pro | NO | SÍ | 2 | `e2e/importaciones-diferencias.spec.ts` | E2E sobre PostgreSQL de Alembic | Flujo principal y revisión |
| T-DR-D | Certificación, documentos y publicación | CLAUDE | n-a | NO | SÍ | 0 | Evidencia, tarjeta y matrices | Cierre técnico | `HEAD == origin/develop` |

`LOCAL_RULE_CONFLICT = 1`: `CLAUDE.md` reserva las migraciones a Claude. Como en el ciclo 4B, la dueña decidió que DeepSeek escriba el código una vez fijado el contrato, que es lo que fija este documento.

## Fuera de alcance

- Folio legal y firma electrónica.
- Envío del reporte al proveedor.
- Reclamo formal.
- Reubicación y validación física: siguiente objetivo, `SPEC018_REUBICACION_ERROR_Y_VALIDACION_FISICA`.
- Cambios en las Specs 019 a 021.

## Cierre

`CONVERGED` en el commit de cierre del ciclo en `develop`. Evidencia: `evidence/difference-report/EVIDENCE.md`. Intentos: `evidence/difference-report/ATTEMPT_LOG.md`. La E2E se integró en `e2e/importaciones.spec.ts` (paso 4.5) y no en un fichero aparte. `OWNER_ACCEPTED` lo concede solo la dueña.
