# `/speckit.converge 045` — CONVERGENCIA FINAL

Fecha: 2026-08-29 · Rama `develop` · Entorno: PostgreSQL 16.2 real, 3 navegadores.

Compara: CONSTITUCIÓN → ADR → SPEC → CLARIFICATIONS → PLAN → CONTRACTS → TASKS →
CODE → FRONTEND → BACKEND → POSTGRESQL → MIGRATIONS → SECURITY → AUDIT → TESTS →
E2E → CROSS-BROWSER → EVIDENCE.

| Eslabón | Verificación | Resultado |
|---|---|---|
| **Constitución v1.1** | 23 principios; P6, P8, P10, P11, P13, P18, P21, P22, P23 verificados con prueba | ✔ sin contradicción |
| **ADR (29 vigentes)** | ADR-001, 004, 011, 012, 013, 015, 016, D0-002, D0-008, D0-013 | ✔ sin contradicción |
| **Spec** | 40 FR + 7 NFR | ✔ 0 sin implementación |
| **Clarifications** | 15 decisiones | ✔ ninguna contradicha |
| **Plan** | 7 fases, orden F1→F2→F3→F4→F7→F5→F6 | ✔ ejecutado |
| **Contracts** | 22 endpoints, 10 códigos de error, `allowed_actions`, 6 eventos | ✔ verificados por API |
| **Tasks** | 65 | ✔ 65 `DONE` con evidencia |
| **Code** | Módulo `approvals` sin importar dominios | ✔ regla de acoplamiento intacta |
| **Frontend** | 4 rutas + panel; tsc, eslint, 217 vitest, build 377 KB | ✔ |
| **Backend** | 276 pruebas, ruff, mypy | ✔ |
| **PostgreSQL** | Suite completa sobre PG 16.2 | ✔ **276/276** |
| **Migrations** | Caso A limpio + Caso B pre-045; head único; drift de 045 = 0 | ✔ |
| **Security** | 401/403, aislamiento, IDOR, segregación, delegación, replay | ✔ |
| **Audit** | `AuditEvent` append-only con actor, motivo y delegación | ✔ |
| **Tests** | Unidad, integración, contrato, concurrencia, migración | ✔ |
| **E2E** | 11 escenarios contra stack real | ✔ **11/11** |
| **Cross-browser** | Chromium, Firefox, WebKit | ✔ **11/11 y 22/22 en los tres** |
| **Evidence** | 10 documentos de convergencia + scripts reproducibles | ✔ |

## Brechas internas de 045

**Ninguna.** Las 4 que pertenecían a 045 (CVG-045-01, 02, 03, 06) quedan
resueltas con evidencia. Las 3 restantes están formalmente diferidas a las Specs
046, 047 y 054, con contrato listo y sin dejar roto ningún requisito de 045.

## Autocorrecciones aplicadas durante esta convergencia

Todas dentro del alcance de 045 (§45), sin ampliar funcionalidad:

| # | Hallazgo | Corrección |
|---|---|---|
| 1 | `0015` colisionaba con los nombres de constraints al renombrar en PostgreSQL | Renombrado explícito de `pk_` e `ix_` por dialecto |
| 2 | `0016` abortaba con una fila legada de empresa inexistente | Omisión con traza; la fila se conserva |
| 3 | Idempotencia devolvía **500** ante dos solicitudes simultáneas | La colisión del índice parcial se traduce en respuesta idempotente |
| 4 | La simulación no funcionaba sobre un borrador, dejando inútil FR-045-008 | `evaluate` acepta `policy_id`; la UI simula la versión en edición |
| 5 | Los modelos no declaraban la restricción y el índice que crea `0015` | `__table_args__` en `ApprovalDecision` y `ApprovalRequest`; drift a 0 |

## Hallazgos ajenos a 045, escalados

No se corrigen aquí salvo los de accesibilidad, que son constitucionales (P11) y
de una línea. **Ninguno fue causado por 045; todos se hicieron visibles al medir
de verdad.**

| # | Hallazgo | Gravedad | Spec destino | ¿Corregido? |
|---|---|---|---|---|
| **A** | `0012` y `0014` referenciaban 7 columnas inexistentes: **la cadena de migraciones nunca pudo aplicarse sobre PostgreSQL** | **BLOCKER de producto** | **012** | **Sí** — sin ello 045 no podía cerrarse |
| **B** | 30 pruebas de dominio insertaban referencias inexistentes; pasaban solo porque SQLite no exige FK | **ALTA** | 002-009 | **Sí** — `seed_org_chain()` |
| **C** | `accessibility.spec.ts` y el crawler de rutas medían `/` en vez de la ruta | **ALTA** | 054 | **Sí** — navegación SPA + verificación de ruta |
| **D** | 6 defectos reales de accesibilidad (contraste y nombre accesible) en componentes compartidos y 2 páginas | **MEDIA** (P11) | 005 | **Sí** — 1 línea cada uno |
| **E** | **22 violaciones de scroll horizontal** en 15 rutas preexistentes a 320-412 px | **MEDIA** (P11) | 005 / 054 | **No** — es diseño de otras Specs |
| **F** | Drift real ORM↔BD: `license_states.license_id` sin UNIQUE y 2 columnas `NOT NULL` ausentes | **MEDIA** | **010** | **No** — ajeno al alcance |
| **G** | Las notificaciones son persistentes por diseño y, apiladas, tapan las acciones de cabecera | **BAJA** (UX) | 005 | **No** — decisión de diseño a revisar |

## Veredicto de convergencia

**Converge.** 0 brechas internas, 0 BLOCKER, 0 CRITICAL, 0 contradicciones,
trazabilidad completa y evidencia reproducible sobre el motor de producción.
