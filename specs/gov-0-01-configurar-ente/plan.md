# Plan · GOV-0-01 Configurar el ente

## Decisiones

| Tipo | Id | Decisión |
|---|---|---|
| OWNER | OD-METHOD-01..06 | Producto primero con calidad; la dueña gobierna la prioridad; corte vertical; progreso visible; el prompt siguiente es propuesto |
| OWNER | OD-GOV0-01 | Tipo de ente en dos campos: nivel político-territorial y forma organizativa |
| OWNER | OD-GOV0-02 | Acto de creación (F09–F12) y documento (F13) obligatorios para activar; borrador sin ellos; tras activar, cambios con motivo y versionados |
| OWNER | OD-GOV0-03 | Ente = contenedor «empresa» 1:1; el tenant agrupa los entes del organismo; la UI dice «ente» |
| OWNER (ratificada) | OQ-GAB-1 = A | Perfil de instalación de Gobierno separado |
| ARCHITECTURE | AD-GOV0-01 | Módulo backend `app/modules/government/` (GOVERNMENT_ONLY). No reutiliza modelos privados (057, organización privada) |
| ARCHITECTURE | AD-GOV0-02 | Se habilita por el entitlement de licencia `gobierno`, denegado por defecto: `require_module("gobierno")` en el backend y `GET /gobierno/modulo` para el menú. `gobierno` se añade a `ENTITLED_MODULES` |
| ARCHITECTURE | AD-GOV0-03 | Concurrencia optimista por `version` en el cuerpo; historia en `gov_entity_versions`, solo inserción |
| ARCHITECTURE | AD-GOV0-04 | El documento del acto usa el módulo 046 (`ResourceKind("GovernmentEntity", …, company_attr="company_id", permission="gobierno_ente:view")`) y `AdjuntosPanel` en la UI |
| PROJECT_DESIGN | PDD-GOV0-01 | Capacidades `gobierno_ente:view/create/edit/activate`: son funcionales, así que FUNCIONAL_COMPLETO las recibe y ADMIN no (GOV-CTL-004) |
| PROJECT_DESIGN | PDD-GOV0-02 | En una instalación de Gobierno el selector de contexto se rotula «Ente» |
| PROJECT_DESIGN | PDD-GOV0-03 | El motivo (F14) admite de 5 a 255 caracteres: es el ancho de `audit_events.reason`, que lo recibe íntegro; un límite mayor truncaría o fallaría en PostgreSQL |

## Clasificación de capacidades usadas

| Capacidad | Clase |
|---|---|
| Identidad, sesión, MFA, RBAC por capacidad × empresa, contexto de empresa (ahora «ente»), aislamiento del 07, auditoría y catálogo (04), documentos y análisis (046), tiempo de Caracas (05), API estricta (05) | SHARED_CORE |
| Licencia y entitlements | SHARED_CORE (se añade el módulo `gobierno`) |
| `GovernmentEntity`, `GovernmentEntityVersion`, la pantalla y el menú Gobierno | GOVERNMENT_ONLY |
| Organización privada (empresas, sucursales), Spec 057 | PRIVATE_ONLY. **No se usa** |

## Puntos de contacto (ficheros)

| Capa | Ficheros |
|---|---|
| Backend | `app/modules/government/{__init__,models,schemas,service,api}.py`; registro del router y de los modelos; `app/modules/licensing/service.py` (`ENTITLED_MODULES`); `app/core/dependencies.py` (`require_module`); `app/modules/setup/api.py` (`CATALOGO_DE_PERMISOS`); `app/shared/audit_catalog_entries.py` y su espejo `specs/001-fundacion/evidence/audit-catalog/catalogo.md`; `app/modules/documents/resources.py` |
| Migración | `alembic/versions/0063_gov0_entes.py` (+ permisos en las instalaciones existentes, si el mecanismo lo exige) |
| QA | `qa/pg-e2e-seed.py` (entitlement `gobierno` en la licencia sintética) |
| Frontend | `src/modules/gobierno/ente/GobiernoEntePage.tsx` (+ formulario e historial), `src/app/router.tsx`, `src/layout/Sidebar.tsx`, `src/app/autoridad/pantallas.ts`, el selector de contexto; el contrato de la API del módulo en `src/modules/gobierno/api.ts` (patrón por módulo de la Spec 047, como `src/modules/notificaciones/api.ts`; no `src/api/types.ts`) |
| Pruebas | `tests/test_gov0_ente.py` (dominio, API, permisos, aislamiento, concurrencia, documento, auditoría); guardas (`test_iso_guardas.py`, cabeza de Alembic); vitest de la pantalla y del menú; `e2e/gobierno-ente.spec.ts` |

## Pruebas (resumen; detalle en tasks y RS)

- **Primero en rojo:** la suite de backend del proceso se escribe antes que el código y falla sin él.
- **Mutaciones de negocio:** quitar el permiso; saltar la máquina de estados; no exigir el documento ni el acto; aceptar otro ente u otro tenant; quitar la auditoría; aceptar una versión vieja; no exigir el motivo; quitar el control del módulo; que la UI ofrezca «Activar» sin autoridad.
- **E2E:** login → menú → pantalla → alta → documento → activación → modificación con motivo → historial → auditoría, en tres navegadores, más los negativos (sin capacidad, otro ente, faltantes, versión vieja).
