# Plan · GOV-DOC-08 Paquete de auditoría exportable (DOC-08, GOV-DOC-010)

## Decisiones de arquitectura

| Id | Decisión | Razón |
|---|---|---|
| AD-DOC08-01 | Servicio `service_paquetes.py`, esquemas `schemas_paquetes.py` y router `api_paquetes.py` (prefijo `/gobierno`, spec §7); guardas permiso → empresa → módulo | Patrón de Gobierno (CTL-04, CTL-06) |
| AD-DOC08-02 | El ZIP se guarda con el proveedor canónico de la Spec 046 (`get_storage().put/open/verify`, clave `generate_storage_key`). En la base solo hay metadatos, huellas y la copia del manifiesto | Sin segundo almacén ni copia de documentos en la base |
| AD-DOC08-03 | Generación síncrona y acotada (spec §4.8): ZIP en `SpooledTemporaryFile`, `put`, inserción y auditoría en una transacción. Si la inserción falla, se borra la clave del almacenamiento | Sin cola; nada a medias |
| AD-DOC08-04 | La legibilidad de un documento se decide con una función **pública** nueva de la Spec 046, `documents.service.puede_leer_archivo(db, document, company_id, permissions) -> bool`. `documents.api._assert_can_read_file` pasa a delegar en ella con el mismo comportamiento. La entrega usa `assert_deliverable` | Una sola regla de acceso documental; el paquete no la duplica ni la salta |
| AD-DOC08-05 | Las dos tablas (spec §6) son de solo inserción, con disparadores en PostgreSQL (UPDATE, DELETE y TRUNCATE rechazados) | Papel de trabajo inmutable |
| AD-DOC08-06 | El detalle seguro de un evento y el objeto de negocio se obtienen con las funciones de CTL-04 (`_detalle_de_evento_para_catalogo`, `_objeto_desde_evento`, `_resumenes`), importadas desde `service_auditoria` | La misma evidencia segura que ve el auditor |
| AD-DOC08-07 | CTL-04 incorpora el proceso DOC-08 (`owner_spec` `gov-doc-08`) y rastrea `GovernmentAuditPackage`. La ficha de la muestra ofrece «Generar paquete de auditoría» y «Paquetes de esta muestra» | Flujo contextual; historial descubrible |

## Decisiones de diseño (de Claude, dentro de las de la dueña)

- **PDD-DOC08-01:** el código es `PA-<año de Caracas>-<nnnn>` por empresa (como `MU-` y `HA-`). Si la unicidad choca por concurrencia, responde 409 `GOV_PACKAGE_CONFLICT` sin reintento silencioso.
- **PDD-DOC08-02:** los documentos van STORED (sin comprimir) y los JSON y textos DEFLATED, con orden y fecha fijos. Una alteración de los bytes de un documento se detecta por CRC y sha256.
- **PDD-DOC08-03:** el paquete no tiene estado. Si existe, está completo.
- **PDD-DOC08-04:** la descarga del paquete o del manifiesto exige poder leer **cada** documento incluido en ese momento (OD-DOC08-04). El detalle por API no muestra nombres de documento.
- **PDD-DOC08-05:** la verificación es de integridad, contra el registro de la empresa activa. Un código ajeno o inexistente da `PAQUETE_NO_REGISTRADO`, sin distinguir entre los dos casos.
- **PDD-DOC08-06:** límites de 500 eventos, 200 documentos y 250 MiB para generar. Para verificar: subida de 300 MiB, 1 000 entradas y razón de compresión de 200.
- **PDD-DOC08-07:** `gobierno_paquetes:view` es STANDARD y `:generate` es SENSITIVE.

## Puerta de la Constitución

| Compuerta | Valor |
|---|---|
| Rama / remotas / HEAD == origin | develop / 1 / 1 (`6afd8d0`) |
| DOC08_REQUIREMENTS_COMPLETE · DOC08_FULL_PROCESS_IMPLEMENTABLE | 1 · 1 |
| DOC01 · DOC05 · DOC06_DEPENDENCY_REQUIRED | 0 · 0 · 0 |
| PACKAGE_SOURCE · MANIFEST · HASH · DOCUMENT_INCLUSION · CROSS_REFERENCE · VERIFICATION | 1 · 1 · 1 · 1 · 1 · 1 |
| MENU_UX · SCREEN_FORM_MATRIX · ROLE_MATRIX · SECURITY_CONTRACT · OWNER_UAT_SCENARIO | 1 · 1 · 1 · 1 · 1 |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 · 0 · 0 · 0 |

**GATE = PASS.** Autorización de `implement`: el encargo GOV-DOC-FUNCTIONAL-03 de la dueña (§11), que nombra DOC-08.
