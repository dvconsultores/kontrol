# CTL-02 · Plan

**Núcleo compartido (SHARED_CORE_CHANGE_REQUIRED = 1).** WHY: GOV-CTL-003 exige sesión, IP y actor en el evento; hoy ningún servicio de Gobierno los pasa. FILES: `modules/audit/models.py`, `shared/audit.py`, `core/logging.py`, `core/middleware.py`, `core/dependencies.py`, `main.py`. ENTERPRISE_IMPACT: ninguno; sin proveedor aplicable, el evento se escribe igual. BACKWARD_COMPATIBILITY: columna nula, API de `record_audit` sin cambios. MIGRATION_IMPACT: una columna nula, sin reescritura de filas.

**Datos.** Migración sobre `0077_gov_org06_identidad`, cabeza única.

**API `/gobierno/bitacora`:** `GET /filtros`, `GET /`, `GET /{evento_id}`, con `gobierno_auditoria:view`.

**Servicios.** `government/contexto_auditoria.py` (instantánea, reutiliza `contexto_institucional` de ORG-06) y `government/service_bitacora.py`.

**Frontend.** `gobierno/bitacora` y `gobierno/bitacora/:eventoId`.

**Constitución.** Sin segunda fuente de verdad, append-only conservado, aislamiento por ente, sin secretos ni PII innecesaria. Gate superado: 0 decisiones materiales abiertas.
