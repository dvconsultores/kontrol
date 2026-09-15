# CONTRATOS DE API — SPEC 046

Prefijo `/api/v1/documentos`. Todo endpoint exige sesión, permiso y filtra por
empresa. **Ningún contrato expone `storage_key`, proveedor ni ruta**
(R-D0-08-2).

## 1. Catálogo

| Método | Ruta | Permiso |
|---|---|---|
| `GET` · `POST` | `/categorias` | `documentos:view` · `documentos:create` |
| `PATCH` | `/categorias/{id}` | `documentos:edit` |
| `GET` · `POST` | `/tipos` | `view` · `create` |
| `GET` · `PATCH` | `/tipos/{id}` | `view` · `edit` |

Ambos catálogos **nacen vacíos**.

## 2. Documentos

| Método | Ruta | Permiso | Notas |
|---|---|---|---|
| `GET` | `/` | `view` | Filtros: `q`, `type`, `category`, `status`, `expiring_before`, `resource_type`, `resource_id`; paginado |
| `POST` | `/` | `create` | Crea el documento **lógico**, sin archivo |
| `GET` | `/{id}` | `view` | Metadata, versión vigente, vínculos, `allowed_actions` |
| `PATCH` | `/{id}` | `edit` | `If-Match`; solo metadata |
| `POST` | `/{id}/archive` | `edit` | |
| `DELETE` | `/{id}` | `delete` | Solo si `can_delete` |

## 3. Subida y versiones

| Método | Ruta | Permiso | Notas |
|---|---|---|---|
| `POST` | `/{id}/versiones` | `upload` | `multipart/form-data`; crea versión y archivo |
| `GET` | `/{id}/versiones` | `view` | Historial completo |
| `GET` | `/{id}/versiones/{version_id}` | `view` | |

No existe `PATCH` de versión ni `PUT` de archivo: **reemplazar es crear una
versión** (R-D0-08-5).

### Petición

`multipart/form-data` con `file` y, opcionalmente, `replacement_reason`.
El cliente **no** envía hash, tamaño, `storage_key` ni número de versión: los
determina el servidor (§101, §127).

### Idempotencia

Cabecera `Idempotency-Key` con el mecanismo existente. Repetir la misma clave
devuelve la **misma versión**, no una nueva (§57).

> Delta CONC-046 (2026-09-15). «La misma versión» es la que creó esa clave en ese
> documento, aunque después se hayan subido otras. Si dos peticiones con la misma
> clave compiten, las dos reciben esa versión. Si compiten con claves distintas, o
> sin clave, una crea la versión y la otra recibe `409 VERSION_CONFLICT`: sin 500 y
> sin dejar archivo, análisis, auditoría ni binario.

### Respuesta

```json
{
  "id": "…", "document_id": "…", "version_number": 2,
  "file": {
    "original_name": "packing-list.pdf",
    "mime_type": "application/pdf",
    "declared_mime": "application/pdf",
    "detected_mime": "application/pdf",
    "size": 184320,
    "sha256": "9f2c…",
    "security_status": "SKIPPED"
  },
  "replacement_reason": "Corrección del proveedor",
  "created_at": "2026-08-30T12:00:00Z",
  "allowed_actions": ["download"]
}
```

`security_status` viaja siempre: si vale `SKIPPED`, el cliente sabe que **no se
analizó**. Nunca se omite para dar impresión de seguridad.

## 4. Descarga y previsualización

| Método | Ruta | Permiso | Notas |
|---|---|---|---|
| `GET` | `/{id}/descargar` | `download` | Versión vigente |
| `GET` | `/{id}/versiones/{version_id}/descargar` | `download` | Versión concreta |
| `GET` | `/{id}/preview` | `download` | **Mismo permiso**, no uno menor (§107) |

**Autorización:** por permiso sobre la **entidad vinculada**, no por conocer el
identificador (R-D0-08-6). Sin acceso se responde **404**, no 403: confirmar la
existencia ya sería una filtración (§128).

**Nunca** se entrega un archivo cuyo `security_status` no sea `CLEAN` o
`SKIPPED`-con-política-que-lo-permita.

`Content-Disposition: attachment` salvo para los formatos que el tipo declare
seguros en línea. **SVG, HTML y comprimidos siempre `attachment`** (§47, §84).
Cabeceras `Cache-Control: private, no-store` (§82).

## 5. Vinculación

| Método | Ruta | Permiso | Notas |
|---|---|---|---|
| `POST` | `/{id}/vinculos` | `link` | Exige permiso sobre la **entidad de destino** |
| `DELETE` | `/vinculos/{link_id}` | `link` | Rechazado si `is_frozen` |
| `GET` | `/por-recurso` | `view` | `resource_type` + `resource_id` |

### Contrato interno para las Specs consumidoras (§94)

```
attach(document_id, resource_type, resource_id, role?) -> DocumentLink
detach(link_id)                                        -> respeta R-D0-08-8
documents_for(resource_type, resource_id)              -> [Document] con allowed_actions
freeze_links(resource_type, resource_id)               -> congela la versión usada
```

`freeze_links` es lo que invoca un consumidor cuando su entidad se vuelve
inmutable —una aprobación resuelta, una factura emitida—. A partir de ahí el
vínculo apunta a **esa** versión para siempre (§26, §123).

Ninguna firma expone almacenamiento.

## 6. Códigos de error

| Código | HTTP | Cuándo |
|---|---|---|
| `DOCUMENT_NOT_FOUND` | 404 | No existe **o** no hay acceso |
| `DOCUMENT_TYPE_NOT_FOUND` | 404 | |
| `FILE_TOO_LARGE` | 413 | Supera el máximo del tipo o el global |
| `MIME_NOT_ALLOWED` | 422 | Fuera de la lista blanca del tipo |
| `MIME_MISMATCH` | 422 | Declarado y detectado difieren |
| `FILENAME_UNSAFE` | 422 | Recorrido de rutas o nombre reservado |
| `FILE_INFECTED` | 422 | El análisis lo marcó |
| `FILE_NOT_SCANNED` | 409 | Descarga con análisis pendiente |
| `STORAGE_FAILURE` | 503 | El almacenamiento no responde |
| `STORAGE_OBJECT_MISSING` | 500 | Metadata sin binario (§74) |
| `DOCUMENT_IN_USE` | 409 | Borrar con vínculos o versiones |
| `LINK_FROZEN` | 409 | Desvincular de una entidad inmutable |
| `RESOURCE_TYPE_UNKNOWN` | 422 | Fuera del registro |
| `RESOURCE_ACCESS_DENIED` | 403 | Sin permiso sobre la entidad de destino |
| `VERSION_IMMUTABLE` | 409 | Editar una versión superada o congelada |
| `RETENTION_PROTECTED` | 409 | Borrar bajo política de retención |
| `VERSION_CONFLICT` | 409 | `If-Match` obsoleto; o, desde CONC-046, otra subida creó la versión a la vez |
| `EXTERNAL_DOCUMENT_NO_FILE` | 422 | Subir a un documento de referencia externa |

Todo bloqueo incluye `reason`, `dependencies` y `allowed_actions`, como fijaron
las Specs 008 y 011.

## 7. Contratos de evento (§66)

| Evento | Cuándo | Consumidor previsto |
|---|---|---|
| `document.uploaded` | Nueva versión con archivo | 042, 047 |
| `document.version_created` | Reemplazo | 042 |
| `document.expiring` | Consulta programada por el consumidor | 044, 047 |
| `document.scan_failed` | Análisis fallido o infectado | 047 |

**046 emite contratos; no notifica.** La Spec 047 será consumidora (§65, §163).
No se convierte cada operación en evento (§66).

## 8. Contratos declarados para Specs consumidoras

Detalle completo en `document-consumer-contract-matrix.md`. En resumen: toda Spec
adjunta con `attach`, consulta con `documents_for` y congela con `freeze_links`,
**sin conocer nunca dónde está el binario**.
