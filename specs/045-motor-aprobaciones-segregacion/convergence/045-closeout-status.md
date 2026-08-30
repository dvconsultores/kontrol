# ESTADO REAL DE CONVERGENCIA — SPEC 045

Reconstruido con evidencia, no con el resumen anterior. Fecha: 2026-08-29.
Entorno: **PostgreSQL 16.2 real** (`qa/pg-provision.sh`), Chromium/Firefox/WebKit.

| ID | Hallazgo | Estado anterior | Evidencia actual | Acción necesaria | ¿Pertenece a 045? | Estado final |
|---|---|---|---|---|:--:|---|
| **CVG-045-01** | Concurrencia no verificada sobre PostgreSQL | Abierto | PostgreSQL 16.2 aprovisionado; suite **276/276**; E2E de concurrencia (dos decisiones simultáneas) **PASS** en 3 navegadores | Aprovisionar PG y ejecutar | **Sí** | **RESOLVED_IN_045** |
| **CVG-045-02** | `alembic upgrade head` / `check` nunca ejecutados | Abierto | Caso A (limpio) y Caso B (pre-045 con datos) **PASS**; `current`=`heads`=`0016`; drift de 045 = **0** | Ejecutar sobre PG real | **Sí** | **RESOLVED_IN_045** |
| **CVG-045-03** | E2E de flujo completo sin automatizar | Abierto | `e2e/approvals.spec.ts`: **11/11** contra frontend real → API real → backend real → PostgreSQL real | Construir y ejecutar | **Sí** | **RESOLVED_IN_045** |
| **CVG-045-04** | Evidencia adjunta a la solicitud | **Cerrado 2026-08-30** | Contrato `AttachmentLink(entity_type='ApprovalRequest')` **implementado** por 046 como `DocumentLink`, con congelación de la versión usada y prueba ejecutada | Ninguna en 045 — 0 cambios en su modelo | **No** | **`RESOLVED_BY_SPEC_046`** |
| **CVG-045-05** | Notificación activa al aprobador | Abierto | 8 tablas incluyen `approval_events`; 6 tipos de evento emitidos y verificados; 045 no importa nada de notificación | Ninguna en 045 | **No** | **DEFERRED_EXTERNAL_DEPENDENCY — SPEC 047** |
| **CVG-045-06** | Cross-browser sin ejecutar | Abierto | E2E **11/11** y axe **22/22** en Chromium, Firefox y WebKit | Ejecutar en 3 motores | **Sí** | **RESOLVED_IN_045** |
| **CVG-045-07** | Las herramientas de QA miden menos de lo que declaran | Abierto | Corregidas `accessibility.spec.ts` y `audit-responsive-crawler.mjs` para navegar por SPA y **verificar la ruta**; al medir de verdad afloraron defectos reales (ver §Hallazgos) | Parte en 045; plataforma general en 054 | **Parcial** | **RESOLVED_IN_045** (instrumentación) + **DEFERRED — SPEC 054** (plataforma) |

## Recuento

| Clasificación | Cantidad |
|---|---:|
| `RESOLVED_IN_045` | **4** (01, 02, 03, 06) + parte de 07 |
| `DEFERRED_EXTERNAL_DEPENDENCY` | **3** (04→046, 05→047, 07 parcial→054) |
| `BLOCKER` | **0** |
| `INVALID_FINDING` | **0** |
