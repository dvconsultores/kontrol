# MATRIZ DE CONTRATOS CON SPECS CONSUMIDORAS — SPEC 046

**Obligatoria (§108, §154).** Existe para demostrar que 046 es realmente una
capacidad transversal y no un módulo de «subir archivos» con un consumidor.

Fecha: 2026-08-30. Construida leyendo las Specs y el código, no los nombres.

---

## 1. Qué gobierna cada parte (§142)

| 046 gobierna | El consumidor gobierna |
|---|---|
| El archivo, su binario y su integridad | Si el documento es **obligatorio** |
| Las versiones y su inmutabilidad | **Cuándo** lo es |
| La metadata genérica y la extensible por tipo | **Qué tipo** exige |
| El almacenamiento y su abstracción | Los **efectos de negocio** de tenerlo o no |
| El acceso, la autorización y la auditoría | Las validaciones regulatorias o fiscales propias |
| El vínculo con la entidad | El significado de ese vínculo |

046 **no** decide que una orden de compra necesita packing list. Provee la
capacidad para que la Spec 018 lo declare.

---

## 2. Matriz

| Spec | Caso | Necesidad documental | Contrato 046 | ¿046 bloquea a esa Spec hoy? |
|---|---|---|---|---|
| **045 · Aprobaciones** ✅cerrada | Evidencia de una solicitud, de su rechazo o de su modificación | Adjuntar y consultar sin cambiar el modelo de 045 | `link(entity_type="ApprovalRequest", entity_id=…)`; la versión usada queda congelada en la decisión | **No** — 045 está `COMPLETE_100` con evidencia interina en texto |
| **018 · Importaciones** | Proforma, packing list, factura del exterior, documentos de embarque, certificados, correcciones | Varios documentos por expediente, con tipo y número externo | `link` múltiple por expediente; `document_number` e `issuer` | **Sí** — sin 046 no hay expediente documental |
| **019 · Recepción física** | Documentos de recepción y evidencia fotográfica | Imágenes y PDF vinculados a la recepción | `link(entity_type="GoodsReceipt")`; tipos de imagen permitidos por `DocumentType` | **Sí** para la evidencia; el flujo puede existir sin ella |
| **020 · Incidencias de recepción** | Foto del daño, de la diferencia, soporte del reclamo | Evidencia fotográfica **obligatoria** en algunos casos | `link(entity_type="ReceiptIncident")`; la obligatoriedad la declara 020 | **Sí** — una incidencia sin evidencia no es reclamable |
| **021 · Confirmación de inventario** | Soporte de la confirmación | Adjunto opcional | `link(entity_type="InventoryConfirmation")` | No |
| **027 · Factura de proveedor** | PDF de la factura recibida, notas de crédito | Documento asociado a un documento fiscal recibido | `link(entity_type="SupplierInvoice")`; **inmutable** una vez contabilizada (R-D0-08-8) | **Sí** para el expediente fiscal |
| **028 · Cotizaciones de venta** | Cotización enviada al cliente | Adjunto generado o cargado | `link(entity_type="SalesQuote")` | No |
| **035 · Despacho y transporte** | Guía de despacho, documentos del vehículo y del conductor, acuse de entrega | Documentos con vigencia (licencia, seguro) | `link` a `Shipment`, `TransportVehicle`, `TransportDriver`; `expiration_date` | **Sí** — hoy `transport_vehicles.documents` es texto libre |
| **036 · Devoluciones** | Soporte de la devolución, evidencia del estado | Evidencia fotográfica | `link(entity_type="SalesReturn")` | No |
| **040 · Tesorería / pagos** | Comprobante de pago, referencia de transferencia, soporte de conciliación | Imagen o PDF por pago | `link(entity_type="Payment")`; hoy `license_renewal_requests.payment_proof_ref` es texto | **Sí** para el soporte de pago |
| **042 · Auditoría** | Evidencia adjunta a un evento de auditoría | Adjunto de solo lectura, inmutable | `link(entity_type="AuditEvent")`; sin desvinculación posible | No — la auditoría funciona sin adjuntos |
| **044 · Regulatorio (SICA/SIGESAI/SACS)** | Permisos, certificados, autorizaciones, constancias | Documento con emisor, número, emisión y **vencimiento** | `link` a `PermitInstance` y `OfficialDocument`; metadata regulatoria por `DocumentType` | **Sí** — hoy `permit_instances.file_ref` y `official_documents.file_ref` son texto suelto |
| **047 · Notificaciones** | Avisar de vencimiento de documento o de fallo de análisis | **Consumir eventos**, no producirlos | `document.expiring`, `document.scan_failed` como contratos de evento | No — 047 es consumidor |
| **050 · Reportes** | Exportaciones con archivo real | Ya existe un mecanismo propio en `reporting` | Convergencia futura opcional; 046 **no** absorbe 050 en el MVP | No |
| **051 · Homologación** | Evidencia del acto formal | Hoy `homologation_records.evidence_sha256` guarda **un hash sin archivo** | `link(entity_type="HomologationRecord")`; el hash pasa a ser el de un archivo real | **Sí** — un hash sin archivo no es evidencia verificable |
| **056 · Portal / integraciones** | Documentos intercambiados con terceros | Descarga autorizada por contrato | `link` + descarga con autorización sobre la entidad | No |

### Recuento

| ¿046 bloquea? | Specs |
|---|---|
| **Sí** | **018, 019, 020, 027, 035, 040, 044, 051** — 8 |
| No | 021, 028, 036, 042, 045, 047, 050, 056 — 8 |

Ocho Specs no pueden completarse sin esta capacidad. Ninguna de las ocho puede
resolverla por su cuenta sin violar P22 y R-D0-08-1.

---

## 3. Contrato de vinculación (§94)

Las Specs consumidoras adjuntan documentos **sin conocer el almacenamiento**:

```
attach(document_id, entity_type, entity_id, role?)   -> DocumentLink
detach(link_id)                                      -> respeta R-D0-08-8
documents_for(entity_type, entity_id)                -> lista con allowed_actions
required_types_for(entity_type)                      -> lo declara el consumidor, lo consulta 046
```

Ninguna firma expone `storage_key`, proveedor ni ruta (R-D0-08-2).

## 4. Contrato con la Spec 045 — verificación explícita (§27)

| Contrato que 045 publicó | Necesidad | Capacidad de 046 | Estado |
|---|---|---|---|
| `AttachmentLink(entity_type="ApprovalRequest", entity_id=<request_id>, document_type_id=<tipo>)` | Vincular evidencia a una solicitud | `DocumentLink` con `resource_type`/`resource_id` y `document_type_id` | **Satisfecho** |
| «Este contrato **no exige cambios en el modelo de 045**» (CL-045-10) | 045 no se toca | El vínculo vive en la tabla de 046; `approval_requests` no cambia | **Satisfecho — 0 cambios en 045** |
| La evidencia interina es `reason`/`observations` en texto | Coexistencia | El texto se conserva; el adjunto se **añade**, no lo sustituye | **Satisfecho** |
| CVG-045-04 · `DEFERRED_EXTERNAL_DEPENDENCY — 046` | Cerrar la dependencia | `link` + congelación de la versión usada en la decisión | **Satisfecho al implementar 046** |

> **046 no crea otro mecanismo de adjuntos.** El nombre de la entidad cambia de
> `AttachmentLink` (nomenclatura del ADR) a `DocumentLink` (nomenclatura de esta
> Spec); la semántica, las columnas y el contrato son los mismos. Se documenta la
> equivalencia para que no se lea como divergencia.
