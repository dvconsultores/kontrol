# Matriz de rutas documentales antes de la apertura

Rutas reales de `app/modules/documents/api.py` y consumidores internos. Estado esperado con sello activo.

| Ruta o punto | Clase | Comportamiento exigido |
|---|---|---|
| `GET /documentos` | DENIED_BEFORE_OPENING | No lista ni cuenta |
| `GET /documentos/{id}` | DENIED_BEFORE_OPENING | 404 |
| `PATCH /documentos/{id}`, `POST .../archive`, `DELETE /documentos/{id}` | DENIED_BEFORE_OPENING | 404 |
| `GET /documentos/{id}/versiones`, `POST /documentos/{id}/versiones` | DENIED_BEFORE_OPENING | 404: no hay versión nueva sobre lo recibido |
| `GET .../descargar`, `GET .../versiones/{v}/descargar`, `GET .../preview` | DENIED_BEFORE_OPENING | 404 |
| `POST /documentos/{id}/vinculos` | DENIED_BEFORE_OPENING | 404 |
| `DELETE /documentos/vinculos/{link}` | DENIED_BEFORE_OPENING | 404 |
| `GET /documentos/por-recurso/{tipo}/{id}` | DENIED_BEFORE_OPENING | **Hueco del candidato:** no filtraba |
| `/documentos/categorias`, `/tipos`, `/salud/almacenamiento` | NOT_RELEVANT | Sin datos de un documento |
| Paquete de auditoría: `documents_for`, `puede_leer_archivo`, `assert_deliverable` | DENIED_BEFORE_OPENING | Excluido y declarado |
| Actos, notificaciones, hallazgos, cargos, estructura, autoridad | NOT_RELEVANT | Exigen vínculo a su propio recurso; un sellado solo puede estar vinculado al expediente |
| Folio del expediente | DENIED_BEFORE_OPENING | 422 |
| Oferta: `GET .../ofertas`, `.../ofertas/{id}` | METADATA_ONLY | Huella, versión e integridad; sin título, nombre ni id si está sellada |
| Evento de cronología, bitácora de recepción | METADATA_ONLY | Sin título ni nombre de archivo |
| Copia de seguridad (`ops/backup_restore.py`) | NOT_RELEVANT | Operación de instalación, no ruta de producto |

**Límite declarado:** quien carga un archivo por el panel del expediente lo ve hasta que se recibe la oferta. El sello actúa desde la recepción. Un sobre físico cerrado no tiene archivo.
