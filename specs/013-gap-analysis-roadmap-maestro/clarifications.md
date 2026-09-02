# CLARIFICACIONES — 013

| ID | Pregunta | Resolución | Fuente |
|---|---|---|---|
| CL-013-01 | ¿El catálogo de 56 sustituye la numeración actual 001-012? | **No.** Las 12 Specs actuales se conservan; el catálogo de 56 es el *universo de control funcional*. Se produce mapa de equivalencias, no renombrado. | Prompt maestro §9 |
| CL-013-02 | ¿Puede una Spec actual cubrir varias maestras? | Sí. `001-fundacion` cubre 001/002/003/005/006; `002-maestros` cubre 009/010/011/014. Se documenta cobertura y recomendación KEEP/SPLIT. | `spec-equivalence-map.md` |
| CL-013-03 | ¿Los 2 DOCX sin track son fuente vinculante? | **Sí.** Son los procesos operativos de referencia y describen etapas que el modelo actual no tiene. Se tratan como requerimiento documentado. | `requerimientos/*.docx` (2026-08-25) |
| CL-013-04 | ¿`COMPLETE_100` es alcanzable hoy? | **No** para ninguna Spec: falta validación sobre PostgreSQL real, condición de "operativo E2E". | Prompt §56 · `012/pending-validations.md` |
| CL-013-05 | ¿Es defecto que SICA/SIGESAI/SACS no tengan integración en línea? | **No.** P20 prohíbe fabricar documentos oficiales; la integración exige convenio. Es FUTURE_SCOPE *dentro* de la Spec 044, no estado de la Spec. | Constitución P20 |
| CL-013-06 | ¿Cuándo debe reservarse el inventario? | **RESUELTA 2026-09-02 (`D0-03 — CLOSED`, `ADR-D0-003` v2):** `RESERVATION TRIGGER = ORDER_CONFIRMATION` — al emitir el pedido (`DRAFT→SUBMITTED`), como pedía el documento. El código reserva hoy al aprobar crédito; la Spec 030 lo corrige. | DOCX Pedido §1 · `sales/service.py:189` |
| CL-013-07 | ¿La confirmación de pedido es obligatoria? | El documento la define como control independiente con separación funcional (Almacén prepara / Confirmación controla). Se trata como requisito, no como opción. | DOCX Pedido §6-7 |
| CL-013-08 | ¿Se considera roto el despliegue de producción? | Incidencia **operativa**, no estado de Spec. Último registro: API 502 (2026-08-11), causa de infraestructura. No re-verificado aquí. | `qa/runs/KONTROL-QA-20260811-LOCAL` |
| CL-013-09 | ¿`file_metadata` sin endpoint cuenta como implementado? | No. Tabla sin acceso = `DATABASE_ONLY` (Spec 046). | `system/models.py:66` · sin `UploadFile` en todo el backend |
| CL-013-10 | ¿Las 36 columnas `Float` de cantidad son brecha? | No: ADR-012 las documenta y acepta como cantidad/medida. Sí lo sería una columna de dinero en Float — hoy quedan 0. | `specs/012/adr-012-numeric-precision.md` |
