# Terceros · descubrimiento sobre el árbol local (`be05f92`)

**Backend existente:** `GET/POST /maestros/terceros`, `GET /terceros/{id}`, `POST /terceros/{id}/deactivate`, `POST /terceros/{id}/roles/{role}`. Sin PATCH, activar, quitar rol, hijos, extensiones, aprobación ni auditoría por tercero.

**Modelos existentes sin superficie:** `PartyAddress`, `PartyContact`, `PartyBankAccount`, `Customer`, `Supplier`, `Carrier`, `Driver`. `Customer`, `Supplier`, `Carrier` y `Driver` no se crean en ningún punto de la aplicación. `Supplier.approval_status` y `Customer.blocked` no los lee nadie: son decorativos. `CustomerCommercialTerms` cuelga de `Customer.id`, así que hoy no se puede alcanzar sin datos sembrados a mano.

**Frontend existente:** `TercerosPage`, listado de solo lectura sin filtro de estado ni paginación. «Ver» apunta a `/maestros/terceros/{id}`, sin ruta en `router.tsx`: `DETAIL_LINK_BROKEN_BEFORE = 1`.

**Sin versión:** ninguna tabla de terceros tiene `version`; requiere migración. El patrón del repositorio es `version` con `If-Match` (`organization/warehouse_api.py`), y 428 cuando la cabecera es obligatoria (`government/service_cuentas.py`).

**Auditoría:** catálogo cerrado en `app/shared/audit_catalog_entries.py`; `record_audit` falla cerrado ante una acción no catalogada. Ninguna operación de terceros audita hoy.

**Documentos:** guardan solo el id del tercero, sin instantánea de razón social ni RIF. Por tanto, editar un tercero no reescribe el documento, pero lo que se pinte en vivo sí cambia. Queda como deuda de la Spec 007 (`FISCAL-SIN-SNAPSHOT-DE-TERCERO`), no se absorbe.

**Government:** no usa estas rutas.
