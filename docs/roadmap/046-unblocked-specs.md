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
| **018 · Importaciones** | `BLOCKED_BY_OWN_MODEL` | La capacidad está completa | **Su propio** modelo de expediente de importación |
| **020 · Incidencias de recepción** | `BLOCKED_BY_OWN_MODEL` | La capacidad está completa | **Su propio** modelo de incidencia |
| **040 · Tesorería / pagos** | `BLOCKED_BY_OWN_MODEL` | La capacidad está completa | **Su propio** modelo de pago |

Las tres marcadas `BLOCKED_BY_OWN_MODEL` **no están bloqueadas por 046**: lo que
les falta es su entidad de dominio, que es suya. Registrarla después es una
línea en `resources.py` y no toca ningún servicio.

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
