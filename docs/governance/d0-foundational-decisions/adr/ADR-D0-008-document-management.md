# ADR-D0-008 — Gestión documental transversal

| Campo | Valor | |
|---|---|---|
| ID | D0-08 · Estado **APPROVED** · 2026-08-29 | Extiende `ADR-008 — Estrategia de Archivos` |
| Responsable | Arquitecto backend · Arquitecto de seguridad · Auditor interno | |
| Specs afectadas | **046** (propietaria) · 018, 019, 020, 021, 027, 035, 036, 044, 050, 051 | |

## Problema

`file_metadata` existe con `sha256`, `storage_key`, `mime_type` y `size`. Pero **no hay endpoint de
subida** (`UploadFile`: cero coincidencias en el backend) y **no hay vínculo a entidad**: sin
`entity_type`/`entity_id`, un archivo no puede pertenecer a una factura, un permiso o una incidencia.

## Por qué debe decidirse ahora

Importación, incidencias de recepción, despacho, permisos regulatorios y auditoría **dependen de
evidencia documental**. Si cada una de esas Specs resuelve sus adjuntos por su cuenta, KONTROL
tendrá cinco sistemas de archivos incompatibles.

## Alternativas

**A. Adjuntos propios en cada módulo** — descartada: es exactamente lo que P17 prohíbe.
**B. Servicio transversal con vinculación polimórfica** ← **RECOMENDADA**.
**C. Binarios en PostgreSQL** — descartada: `ADR-008` ya decidió volúmenes; los binarios en la base
degradan respaldo y restauración, y no aportan integridad que el hash no dé ya.

## Modelo conceptual

```
DocumentType      (empresa · código · nombre · obligatorio · extensiones · tamaño máx. · retención)
Attachment        (tenant · empresa · nombre original · MIME · tamaño · sha256 · storage_key ·
                   subido_por · subido_en · estado)
 └── AttachmentVersion (n.º de versión · sha256 · storage_key · motivo del reemplazo)
AttachmentLink    (attachment_id · entity_type · entity_id · document_type_id · rol)
```

`AttachmentLink` separado del `Attachment` permite que **un archivo sirva a varias entidades**
(un packing list vale para el embarque y para la recepción) sin duplicar el binario.

## Reglas

| ID | Regla |
|---|---|
| R-D0-08-1 | Ningún módulo implementa su propio almacenamiento de archivos (P17). |
| R-D0-08-2 | `storage_key` es **opaca**. Está prohibido derivar lógica de negocio de rutas del host o de nombres de archivo. |
| R-D0-08-3 | No se guardan binarios en PostgreSQL salvo ADR explícito que lo justifique. |
| R-D0-08-4 | Todo adjunto tiene `sha256` calculado en el servidor. Un adjunto sin hash verificable no es evidencia. |
| R-D0-08-5 | Los adjuntos **no se sustituyen en sitio**: se versionan. La versión anterior se conserva con su hash (P5). |
| R-D0-08-6 | La descarga se autoriza por permiso sobre la **entidad vinculada**, no por conocer el identificador del archivo. |
| R-D0-08-7 | Toda subida, descarga, versión y eliminación lógica queda auditada. |
| R-D0-08-8 | Un adjunto vinculado a un documento inmutable (factura emitida, permiso usado) **no puede desvincularse ni eliminarse**. |
| R-D0-08-9 | La validación de tipo y tamaño se hace en el servidor, contra el `DocumentType`, no en el navegador (P6). |

## Impacto

Frontend: componente único de adjuntos reutilizable · Backend: módulo `documents` con subida,
descarga y versionado · DB: 4 tablas (`file_metadata` evoluciona a `Attachment`) · QA: hash,
autorización cruzada, límites, tipos peligrosos · Seguridad: **superficie nueva** — validación de
tipo real, límite de tamaño, sin ejecución, sin recorrido de rutas · Fiscal: soporte de evidencia
para expediente y auditoría.

## Migración

**`SAFE_MIGRATION`** — `file_metadata` está vacía de uso real (sin endpoint). Se extiende sin backfill.

## Criterios de aceptación

- [ ] Un archivo se adjunta a proveedor, importación, recepción, incidencia, pedido, despacho, permiso y evento de auditoría con el mismo componente y el mismo servicio.
- [ ] Reemplazar un adjunto crea versión y conserva la anterior.
- [ ] Sin permiso sobre la entidad, la descarga se deniega aunque se conozca el id.
- [ ] Un adjunto de factura emitida no puede eliminarse.
- [ ] No existe ninguna ruta del host en la lógica de negocio.

## Estado final

**APPROVED** — **CLOSED**.
