# CIERRE DE DEPENDENCIAS — SPEC 046

Fecha: 2026-08-30 · Origen: `SPEC 046 COMPLETE_100` (commit `51cbb5a`)

Este documento es la **autoridad** sobre qué desbloquea 046. Sustituye a
`document-consumer-contract-matrix.md` §2 y a cualquier afirmación previa.

Cada fila se verificó **contra el código**: el tipo está en el registro cerrado
de `app/modules/documents/resources.py`, su modelo resuelve, su columna de
empresa existe y hay prueba que lo ejercita. Lo que no se pudo comprobar así, no
se declara desbloqueado.

---

## 0. Corrección de numeración — cinco etiquetas erróneas

`document-consumer-contract-matrix.md`, escrita durante `/speckit.specify 046`,
usó nombres de Spec que **no coinciden** con la lista canónica de
`docs/roadmap/56-specs-gap-analysis.md`. No es un detalle cosmético: una Spec
mal numerada enruta trabajo futuro al equipo equivocado.

| Nº | La matriz decía | Nombre canónico | La necesidad documental pertenece en realidad a |
|---|---|---|---|
| 028 | «Cotizaciones de venta» | **Cuentas por pagar y pagos** | 028 — comprobante de pago (`ap_payments`) |
| 040 | «Tesorería / pagos» | **Retenciones IVA e ISLR** | 038 — Tesorería |
| 042 | «Auditoría» | **Documentos fiscales, controles y contingencia** | 051 — Auditoría empresarial avanzada |
| 051 | «Homologación» | **Auditoría empresarial avanzada** | 056 — Homologación fiscal y release |
| 056 | «Portal / integraciones» | **Homologación fiscal y release** | 048 — Integraciones |

Todas las filas de este documento usan la numeración canónica.

---

## 1. Vocabulario de estados

| Estado | Significado |
|---|---|
| `FULLY_UNLOCKED` | 046 era el único bloqueo y ya no queda ninguno |
| `PARTIALLY_UNLOCKED` | El bloqueo documental cayó y parte del dominio ya opera |
| `DOCUMENT_CAPABILITY_SATISFIED` | La capacidad documental está completa; el bloqueo restante **no es documental** |
| `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | El tipo está registrado y probado; el proceso de negocio sigue siendo suyo |
| `STILL_BLOCKED_BY_046` | 046 todavía no ofrece lo que esa Spec necesita |

---

## 2. Matriz

| Spec | Dependencia previa | Contrato 046 implementado | ¿Bloqueo documental resuelto? | Otros bloqueos | Estado |
|---|---|---|:--:|---|---|
| **019 · Recepción física** | Evidencia de recepción y fotografía | `GoodsReceipt` → `goods_receipts` (`company_id`, `compras:view`) | **Sí** | Su fase física: arribo, descarga, bultos, inspección (B-040) | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` |
| **027 · Factura proveedor y conciliación** | Expediente fiscal del documento recibido | `SupplierInvoice` → `supplier_invoices` (`company_id`, `compras:view`) | **Sí** | Conciliación y flujo fiscal | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` |
| **035 · Despacho, transporte y regulación** | Guía, documentos de vehículo y conductor, acuse | `Shipment`, `TransportVehicle`, `TransportDriver` — las tres registradas; `expiration_date` para licencias y seguros | **Sí** | Empaquetado físico y ruta | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` |
| **044 · SICA / SIGESAI / SACS** | Permisos, certificados, constancias con vencimiento | `PermitInstance`, `OfficialDocument` (`company_id`, `regulatorio:view`); metadata regulatoria declarable por tipo | **Sí** | Matrices oficiales por rubro no cargadas | `PARTIALLY_UNLOCKED` |
| **056 · Homologación fiscal y release** | Evidencia del acto formal | `HomologationRecord` — sin `company_id`: el acto es de la instalación, el control se apoya en `homologacion:view` | **Sí** | **`LEGAL_BLOCKER`**: acto formal no ejecutado | `PARTIALLY_UNLOCKED` |
| **018 · Importaciones** | Proforma, packing list, embarque, certificados | La capacidad está completa; **no hay entidad que vincular** | Sí, en capacidad | **Su expediente no existe**: INCOTERM, proforma, packing y embarque inexistentes (B-030, `NOT_STARTED`) | `DOCUMENT_CAPABILITY_SATISFIED` |
| **020 · Incidencias de recepción** | Foto del daño, soporte del reclamo | La capacidad está completa; **no hay entidad que vincular** | Sí, en capacidad | **No existe entidad de incidencia ni escalamiento** (B-041, `NOT_STARTED`) | `DOCUMENT_CAPABILITY_SATISFIED` |
| **040 · Retenciones IVA e ISLR** | Comprobante de retención | Se adjunta a `SupplierInvoice` / `SalesInvoice`, ambas registradas | **Sí** | **`LEGAL_BLOCKER`**: Decreto 1.808 sin conceptos cargados | `DOCUMENT_CAPABILITY_SATISFIED` |
| **028 · Cuentas por pagar y pagos** | Comprobante de pago | **Ninguno.** `Payment` → `ap_payments` **existe** con `company_id`, pero **no está registrado** | **No** | — | **`STILL_BLOCKED_BY_046`** |
| **038 · Tesorería** | Soporte de conciliación y de movimiento de caja | **Ninguno.** `bank_transactions`, `cash_sessions`, `reconciliations` existen; **ninguna registrada** | **No** | — | **`STILL_BLOCKED_BY_046`** |

### Recuento

| Estado | Specs | Nº |
|---|---|---:|
| `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | 019, 027, 035 | 3 |
| `PARTIALLY_UNLOCKED` | 044, 056 | 2 |
| `DOCUMENT_CAPABILITY_SATISFIED` | 018, 020, 040 | 3 |
| **`STILL_BLOCKED_BY_046`** | **028, 038** | **2** |
| `FULLY_UNLOCKED` | — | **0** |

**Ninguna Spec queda `FULLY_UNLOCKED`.** Satisfacer la dependencia documental no
completa un dominio, y decir lo contrario sería el mismo error que 046 vino a
corregir en el legado: confundir una referencia con una evidencia.

---

## 3. El hallazgo: 028 y 038 siguen bloqueadas por 046

El registro de tipos vinculables es **cerrado por diseño** (`FR-046-022`): un
tipo ausente se rechaza con `RESOURCE_TYPE_UNKNOWN`. Es lo que impide vínculos
polimórficos inseguros, y no se negocia.

Cuatro entidades que ya existen, con su `company_id`, **no figuran** en él:

| Entidad | Tabla | Spec | Permiso que le correspondería |
|---|---|---|---|
| `Payment` | `ap_payments` | 028 | `compras:view` |
| `BankTransaction` | `bank_transactions` | 038 | `tesoreria:view` |
| `CashSession` | `cash_sessions` | 038 | `tesoreria:view` |
| `Reconciliation` | `reconciliations` | 038 | `tesoreria:view` |

**No se registran aquí.** Este prompt autoriza un único cambio de código —la
remediación de `route-crawl`/`auth refresh`— y no es este.

Queda identificada como **`REM-046-001`**: cuatro entradas en `resources.py` y
sus pruebas, a ejecutar con autorización expresa o al implementar 028/038.

Que un pendiente sea pequeño no lo convierte en hecho.

---

## 4. Lo que 046 deja fuera a propósito

| Spec | Motivo |
|---|---|
| **047 · Notificaciones y tareas** | 046 **no emite** eventos. `document.expiring` y `document.scan_failed` quedan como contratos declarados para que 047 los consuma |
| **050 · Reportes empresariales** | `reporting` conserva su mecanismo propio de archivo; 046 no lo absorbe en el MVP |
| **051 · Auditoría empresarial avanzada** | Deliberado: adjuntar a un evento de auditoría lo volvería editable |
| **048 · Integraciones** | Usará `link` + descarga autorizada; no necesita nada nuevo de 046 |

---

## 5. Deudas de 046 — clasificación formal

| Id | Deuda | Clasificación | Spec propietaria del cierre |
|---|---|---|---|
| **DEUDA-046-1** | Adaptador compatible con S3 | **`IMPLEMENTED_NOT_VERIFIED`** | 046 · reverificar cuando exista un servicio real |
| **DEUDA-046-2** | Purga por retención sin planificador | **`DEFERRED_EXTERNAL_DEPENDENCY`** | **052 · Instalador, actualización y migración** — es la Spec de infraestructura de ejecución. Si al implementarla se decide otra ubicación, se reasigna |
| **DEUDA-046-3** | E2E regulatorio por interfaz | `DEFERRED_EXTERNAL_DEPENDENCY` | 044 · cuando tenga pantallas de permiso con carga |
| **DEUDA-046-4** | `UnsavedChangesGuard` no aplicado | **Observación** | Ninguna: los formularios de 046 son de una línea |
| **REM-046-001** | 4 entidades de 028/038 sin registrar | `PENDING_MINOR_REMEDIATION` | 046 · con autorización expresa, o al implementar 028/038 |

### DEUDA-046-1 · Estado del almacenamiento por proveedor

| Proveedor | Estado | Base de la afirmación |
|---|---|---|
| `FilesystemStorageProvider` | **`VERIFIED`** | 10 pruebas de conformidad sobre disco real, más toda la suite documental |
| `S3CompatibleStorageProvider` | **`IMPLEMENTED_NOT_VERIFIED`** | 8 pruebas de conformidad escritas y **omitidas**, por no haber servicio compatible con S3 en el entorno |

**No se declara** `production-ready`, `supported` ni `validated` para S3. El
proveedor de producción validado hoy es **filesystem**.

### DEUDA-046-2 · Por qué no hay planificador

`FR-046-066` exige que la purga física la ejecute el trabajador común de la
plataforma, **nunca un planificador propio de 046**. Ese trabajador **no existe
todavía**: se buscó `worker`, `scheduler`, `cron` y `APScheduler` en todo
`app/` y no hay ninguno.

046 aporta la operación —`purge_version`, idempotente, que se niega a purgar una
versión referenciada y dice por qué— y **no** aporta el calendario. Crear uno
aquí habría violado el propio requisito.

### Deuda responsive preexistente

Las 22 violaciones responsive conocidas **permanecen en sus Specs propietarias**
(005 / 054). No se cargan a 046 ni se corrigen desde este cierre.
