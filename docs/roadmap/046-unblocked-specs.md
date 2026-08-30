> **Superado por `docs/roadmap/046-dependency-closeout.md` (2026-08-30)**, que
> corrige cinco etiquetas de Spec erróneas y clasifica cada dependencia con el
> vocabulario formal. Este archivo se conserva como registro de lo que se
> afirmó al cerrar la implementación; **la autoridad es el otro**.

# SPECS DESBLOQUEADAS POR EL CIERRE DE LA SPEC 046

Fecha: 2026-08-30 · Origen: `SPEC 046 COMPLETE_100`

El desbloqueo se declara **por contrato verificado en código** —el tipo de
recurso está registrado, resuelve su modelo y su empresa, y tiene prueba— no
por lo que dijera el roadmap previo.

046 bloqueaba a 8 Specs. Ninguna queda `FULLY_UNLOCKED`: satisfacer la
dependencia documental no completa un dominio.

| Spec | Estado | Contrato entregado por 046 | Qué sigue bloqueando |
|---|---|---|---|
| **019 · Recepción física** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | `GoodsReceipt` registrada: adjuntar, versionar y descargar con autorización | Su proceso de recepción e incidencias |
| **027 · Factura de proveedor** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | `SupplierInvoice` registrada; la versión usada se congela al contabilizar | Conciliación y flujo fiscal |
| **035 · Despacho y transporte** | `DEPENDENCY_SATISFIED_BUT_OTHER_BLOCKERS_EXIST` | `Shipment`, `TransportVehicle` y `TransportDriver` registradas; `expiration_date` para licencias y seguros | Empaquetado y ruta |
| **044 · Regulatorio** | **`PARTIALLY_UNLOCKED`** | `PermitInstance` y `OfficialDocument` registradas; metadata regulatoria declarable por tipo | Matrices oficiales por rubro |
| **051 · Homologación** | **`PARTIALLY_UNLOCKED`** | `HomologationRecord` registrada: el acto puede tener por fin un archivo verificable | El acto formal y su ciclo |
| **018 · Importaciones** | `DOCUMENT_CAPABILITY_SATISFIED` | La capacidad está completa | **Su propio** expediente de importación: INCOTERM, proforma, packing y embarque no existen (B-030) |
| **020 · Incidencias de recepción** | `DOCUMENT_CAPABILITY_SATISFIED` | La capacidad está completa | **Su propia** entidad de incidencia y escalamiento (B-041) |
| **040 · Retenciones IVA e ISLR** | `DOCUMENT_CAPABILITY_SATISFIED` | El comprobante se adjunta a `SupplierInvoice` / `SalesInvoice`, registradas | **`LEGAL_BLOCKER`**: Decreto 1.808 sin conceptos cargados |
| **038 · Tesorería** | **`STILL_BLOCKED_BY_046`** | **Ninguno** | `ap_payments` existe y sería vinculable, pero **no está en el registro cerrado**. Remediación `REM-046-001`, no ejecutada |

Las tres `DOCUMENT_CAPABILITY_SATISFIED` **no están bloqueadas por 046**: lo que
les falta no es documental.

**038 sí lo está.** El registro de tipos es cerrado por diseño (`FR-046-022`) y
`Payment` no figura en él. Son dos líneas y una prueba; no se hicieron aquí
porque este cierre no autoriza tocar 046.

> Corrección de etiqueta (2026-08-30): la matriz de consumidoras llamaba «040» a
> Tesorería. El roadmap maestro manda: **038 es Tesorería**, **040 es Retenciones
> IVA e ISLR**. Autoridad: `docs/roadmap/046-dependency-closeout.md`.

## Lo que 046 deja explícitamente sin resolver

| Spec | Por qué no se tocó |
|---|---|
| **047 · Notificaciones** | 046 **no emite** eventos. Los contratos `document.expiring` y `document.scan_failed` quedan declarados para que 047 los consuma |
| **050 · Reportes** | `reporting` conserva su mecanismo propio de archivo. 046 no lo absorbe en el MVP |
| **042 · Auditoría** | Deliberado: adjuntar a un evento de auditoría lo volvería editable |

## El riesgo que 046 cierra

Doce columnas del sistema guardaban referencias documentales como **texto
suelto**: una URL, una ruta de otra máquina, un hash sin archivo. Ninguna era
verificable, y varias se leían como si lo fueran.

046 no las convirtió en documentos —eso habría llenado el repositorio de
expedientes que nadie puede abrir, con apariencia de completitud—. Las **anotó**
con su clasificación real, dejando el texto original intacto, y aportó la vía
para importar el binario cuando exista y su huella coincida.

Desde este cierre, un archivo solo está disponible si pasó por el analizador, se
escribió, se releyó y su huella coincidió. Y una evidencia usada en un proceso
resuelto devuelve **los bytes que existían entonces**, no los de la última
versión.
