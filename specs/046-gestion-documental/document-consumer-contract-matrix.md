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
| **038 · Tesorería** *(la fila decía «040», etiqueta errónea corregida el 2026-08-30: 040 es Retenciones IVA e ISLR)* | Comprobante de pago, referencia de transferencia, soporte de conciliación | Imagen o PDF por pago | `link(entity_type="Payment")`; hoy `license_renewal_requests.payment_proof_ref` es texto | **Sí** para el soporte de pago |
| **042 · Auditoría** | Evidencia adjunta a un evento de auditoría | Adjunto de solo lectura, inmutable | `link(entity_type="AuditEvent")`; sin desvinculación posible | No — la auditoría funciona sin adjuntos |
| **044 · Regulatorio (SICA/SIGESAI/SACS)** | Permisos, certificados, autorizaciones, constancias | Documento con emisor, número, emisión y **vencimiento** | `link` a `PermitInstance` y `OfficialDocument`; metadata regulatoria por `DocumentType` | **Sí** — hoy `permit_instances.file_ref` y `official_documents.file_ref` son texto suelto |
| **047 · Notificaciones** | Avisar de vencimiento de documento o de fallo de análisis | **Consumir eventos**, no producirlos | `document.expiring`, `document.scan_failed` como contratos de evento | No — 047 es consumidor |
| **050 · Reportes** | Exportaciones con archivo real | Ya existe un mecanismo propio en `reporting` | Convergencia futura opcional; 046 **no** absorbe 050 en el MVP | No |
| **051 · Homologación** | Evidencia del acto formal | Hoy `homologation_records.evidence_sha256` guarda **un hash sin archivo** | `link(entity_type="HomologationRecord")`; el hash pasa a ser el de un archivo real | **Sí** — un hash sin archivo no es evidencia verificable |
| **056 · Portal / integraciones** | Documentos intercambiados con terceros | Descarga autorizada por contrato | `link` + descarga con autorización sobre la entidad | No |

### Recuento

| ¿046 bloquea? | Specs |
|---|---|
| **Sí** | **018, 019, 020, 027, 035, 038, 044, 051** — 8 |
| No | 021, 028, 036, 042, 045, 047, 050, 056 — 8 |

> La fila de tesorería figuraba como «040». El roadmap maestro es la autoridad:
> **038 es Tesorería** y **040 es Retenciones IVA e ISLR**. Corregido el 2026-08-30;
> ver `docs/roadmap/046-dependency-closeout.md` §0.

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


---

## 5. Verificación tras la implementación — 2026-08-30

El registro de tipos vinculables es **cerrado**: solo admite entidades cuyo
modelo existe hoy. Esta es la fotografía real al cerrar 046, no la aspiracional.

| Spec | Entidad que necesita | ¿Registrada hoy? | Nota |
|---|---|---|---|
| 045 · Aprobaciones | `ApprovalRequest` | ✅ | Contrato verificado con congelación de versión |
| 018 · Importaciones | expediente de importación | ⛔ | El modelo no existe: lo crea 018. Cuando exista, se registra sin tocar 046 |
| 019 · Recepción física | `GoodsReceipt` | ✅ | — |
| 020 · Incidencias | `ReceiptIncident` | ⛔ | El modelo no existe: lo crea 020 |
| 021 · Confirmación | `InventoryConfirmation` | ⛔ | El modelo no existe |
| 027 · Factura de proveedor | `SupplierInvoice` | ✅ | — |
| 028 · Cotizaciones | `SalesQuote` | ⛔ | El modelo no existe |
| 035 · Despacho | `Shipment`, `TransportVehicle`, `TransportDriver` | ✅ | Las tres registradas |
| 036 · Devoluciones | `SalesReturn` | ✅ | — |
| 038 · Tesorería | `Payment` | ⛔ | El modelo **sí existe** (`ap_payments`, con `company_id`); lo que falta es su entrada en el registro cerrado — `REM-046-001` |
| 042 · Auditoría | `AuditEvent` | ⛔ | Deliberado: adjuntar a un evento de auditoría lo convertiría en editable |
| 044 · Regulatorio | `PermitInstance`, `OfficialDocument` | ✅ | Ambas registradas |
| 047 · Notificaciones | — | n/a | 046 **no** emite eventos; 047 los consumirá |
| 050 · Reportes | — | n/a | 046 no absorbe el mecanismo de `reporting` |
| 051 · Homologación | `HomologationRecord` | ✅ | Sin `company_id`: el acto es de la instalación; el control se apoya en el permiso |
| 056 · Portal | — | n/a | Usará `link` + descarga autorizada |

**19 tipos registrados**: los 16 previstos más `TransportVehicle`,
`TransportDriver` y `HomologationRecord`, añadidos al comprobar que sus modelos
ya existen y que sus Specs figuraban entre las bloqueadas.

### Estado de las 8 Specs bloqueadas

| Spec | ¿Desbloqueada por 046? | Qué le falta |
|---|---|---|
| 018 | **Parcial** | La capacidad está; le falta su propio modelo de expediente |
| 019 | **Sí** | `GoodsReceipt` registrada; puede adjuntar hoy |
| 020 | **Parcial** | Le falta su modelo de incidencia |
| 027 | **Sí** | `SupplierInvoice` registrada |
| 035 | **Sí** | Las tres entidades registradas; `transport_*.documents` queda anotado como legado, no convertido |
| 038 | **No** | `ap_payments` existe pero no está registrado: `STILL_BLOCKED_BY_046` — `REM-046-001` |
| 044 | **Sí** | `PermitInstance` y `OfficialDocument` registradas; `file_ref` anotado como legado sin verificar |
| 051 | **Sí** | `HomologationRecord` registrada; `evidence_sha256` queda `LEGACY_HASH_WITHOUT_FILE` — un hash sin binario sigue sin ser evidencia |

Ninguna de las cuatro «parciales» está bloqueada **por 046**: lo que les falta
es su propio modelo de dominio, que es suyo, no de esta Spec. Registrar un tipo
nuevo es una línea en `resources.py` y no toca ningún servicio.
