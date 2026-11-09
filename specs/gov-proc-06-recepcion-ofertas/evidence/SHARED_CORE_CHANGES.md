# Cambios de núcleo compartido (documentados antes de tocar el código)

`SHARED_CORE_CHANGE_REQUIRED = 1` en este ciclo, por dos causas distintas.

## SC-1 · Armazón responsive (OBS-UI-320-01)

- **WHY:** con carga directa a 320 px el menú ocupa 255 px y deja 64 px al contenido en Expedientes, Comisiones y Documentos. Es `GLOBAL_APPLICATION_SHELL_DEFECT`: el menú tiene ancho fijo y siempre arranca abierto, para todos los módulos.
- **FILES:** `resources/frontend/src/layout/PageLayout.tsx`, `Sidebar.tsx`, `Topbar.tsx`, `Sidebar.test.tsx`.
- **BACKWARD_COMPATIBILITY:** de 768 px en adelante el armazón no cambia. Por debajo, el menú pasa a panel que se abre con un botón.
- **ENTERPRISE_IMPACT:** Enterprise usa el mismo armazón: gana el mismo comportamiento en teléfono y ningún cambio en escritorio. Sin cambio de rutas, permisos ni datos.
- **ALTERNATIVE_GOV_ONLY:** rechazada: la dueña prohíbe un arreglo solo de Gobierno para un defecto del armazón.
- **REGRESSION_REQUIRED:** pruebas de `Sidebar`, `documents-a11y.spec.ts` y una pantalla de escritorio.

## SC-2 · Documento sellado (confidencialidad de ofertas, GOV-PROC-007)

**Estado 2026-11-09: sin publicar. `/documentos` en `develop` no tiene sello.**

- **WHY:** `/documentos` entrega metadatos y bytes a quien pueda ver una entidad vinculada. Ocultar un botón no protege la oferta: hace falta una regla en la capa documental.
- **FILES:** `resources/backend/app/modules/documents/models.py`, `service.py`, `api.py`, y una tabla nueva `document_seals`.
- **BACKWARD_COMPATIBILITY:** un documento sin sello se comporta exactamente igual. La tabla nace vacía.
- **ENTERPRISE_IMPACT:** Enterprise no sella documentos: su comportamiento no cambia. Coste: una comprobación adicional por documento y un filtro en el listado.
- **ALTERNATIVE_GOV_ONLY:** rechazada: un guardián solo en la API de Gobierno dejaría abierta la descarga directa por `/documentos`.
- **REGRESSION_REQUIRED:** pruebas de documentos del núcleo y de paquetes de auditoría.
