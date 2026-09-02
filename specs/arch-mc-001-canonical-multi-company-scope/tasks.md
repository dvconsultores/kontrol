# TAREAS — ARCH-MC-001

No existe una tarea «normalizar 82 tablas».

## N0 · Gobierno

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-001 | ADR de alcance canónico tenant/empresa/sucursal | FR-MC-001, FR-MC-002 | L |
| T-MC-002 | Enumeración `Scope` y declaración en el ORM | FR-MC-003 | M |
| T-MC-003 | Clasificar las 166 tablas; **0 sin clasificar** | FR-MC-004 | L |
| T-MC-004 | Criterio directa/derivada por entidad | FR-MC-005, FR-MC-006 | M |
| T-MC-005 | Regla constitucional para entidades nuevas | FR-MC-080 | S |
| T-MC-006 | Regla de QA: toda Spec con datos de empresa prueba con dos | FR-MC-081 | S |

## N1 · Contexto de empresa

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-010 | `CompanyContext` y su dependencia de FastAPI | FR-MC-010 | XL |
| T-MC-011 | Cabecera `X-Kontrol-Company` y su validación | FR-MC-011, AC-MC-10 | L |
| T-MC-012 | Resolución automática con una sola empresa | FR-MC-013, AC-MC-11 | M |
| T-MC-013 | Rechazo explícito con varias y sin cabecera | AC-MC-12, AC-MC-13, AC-MC-14 | M |
| T-MC-014 | Acceso usuario–empresa sobre `UserScope` y `user_roles` | FR-MC-030, FR-MC-031, AC-MC-42 | XL |
| T-MC-015 | Separar permiso de alcance | FR-MC-032, AC-MC-43 | L |
| T-MC-016 | Convivencia con el alcance por sucursal | FR-MC-033, AC-MC-44 | M |
| T-MC-017 | Revalidación por petición; contexto obsoleto | FR-MC-018, AC-MC-16 | M |
| T-MC-018 | Empresa desactivada | AC-MC-15 | S |
| T-MC-019 | Contexto explícito para trabajos sin petición | FR-MC-019, AC-MC-20 | L |
| T-MC-020 | Compatibilidad con la renovación de sesión ya remediada | FR-MC-016, R-MC-11 | M |
| T-MC-021 | Migración `00XX_mc_company_access` | FR-MC-031 | M |
| T-MC-022 | Imposición del límite de empresas por licencia | FR-MC-034, AC-MC-40, AC-MC-41 | L |
| T-MC-023 | El esquema es multiempresa aunque el plan sea de una | FR-MC-035 | S |

## N2 · Cortar la hemorragia

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-030 | Prueba de arquitectura que falla ante `company_id = actor.tenant_id` | FR-MC-025, AC-MC-04 | L |
| T-MC-031 | Prueba: modelo con `company_id` exige FK a `companies` | FR-MC-060, AC-MC-01 | M |
| T-MC-032 | Prueba: modelo con `tenant_id` exige FK a `tenants` | FR-MC-060 | M |
| T-MC-033 | Prueba: toda entidad declara alcance | FR-MC-003, AC-MC-02 | M |
| T-MC-034 | Prueba: ninguna derivada depende de FK anulable | FR-MC-005, AC-MC-03 | M |
| T-MC-035 | Prueba de rutas contra `endpoint-scope-matrix` | FR-MC-020 | L |

## N3 · Expandir

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-040 | Renombrar lo heredado a `legacy_scope_id`, sin destruir | FR-MC-054, AC-MC-74 | L |
| T-MC-041 | `company_id` nuevo, anulable, con FK | FR-MC-060 | L |
| T-MC-042 | Columna de clase de relleno | FR-MC-051 | S |
| T-MC-043 | Migraciones `00XX_mc_expand_<dominio>`, una por ola, con recuperación entre fases | FR-MC-050, NFR-MC-08 | XL |

## N4 · Rellenar y verificar

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-050 | Cálculo del instante en que un tenant deja de ser monoempresa | FR-MC-052, AC-MC-71 | L |
| T-MC-051 | Clasificador `MC-A`..`MC-E` | FR-MC-051 | XL |
| T-MC-052 | Rutas de reconstrucción admitidas | FR-MC-051 | L |
| T-MC-053 | Conflicto entre rutas ⇒ `MC-C`; nunca relleno automático | R-MC-3, AC-MC-72 | M |
| T-MC-054 | Informe previo **sin escribir** | FR-MC-058, AC-MC-70 | L |
| T-MC-055 | Aborto ante crítico no reconstruible | FR-MC-053, AC-MC-73 | L |
| T-MC-056 | Resolución manual auditable | FR-MC-055, AC-MC-75 | XL |
| T-MC-057 | Verificación de paridad de importes y números | FR-MC-056, AC-MC-76 | L |
| T-MC-058 | Migraciones `00XX_mc_backfill_<dominio>` | FR-MC-050 | XL |

## N5 · Dominios, por olas

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-060 | Ola 1 · organización y accesos (8 tablas) | FR-MC-020, FR-MC-021 | L |
| T-MC-061 | Ola 2 · maestros (24) | FR-MC-020 | XL |
| T-MC-062 | Ola 3 · **fiscal** (13) | FR-MC-063, AC-MC-50..55 | XL |
| T-MC-063 | Series y números de control por empresa | AC-MC-50, AC-MC-51 | XL |
| T-MC-064 | Libros por contribuyente | AC-MC-52, AC-MC-53 | L |
| T-MC-065 | Retenciones con su empresa agente | AC-MC-54 | L |
| T-MC-066 | Ola 4 · compras (21) | AC-MC-60, AC-MC-62 | XL |
| T-MC-067 | Coherencia orden ↔ almacén en recepción | AC-MC-61 | L |
| T-MC-068 | Ola 5 · inventario (13) | AC-MC-64, AC-MC-69 | XL |
| T-MC-069 | Transferencia entre empresas bloqueada | AC-MC-65 | M |
| T-MC-070 | Ola 6 · ventas (14) | AC-MC-66 | XL |
| T-MC-071 | Empresa emisora inmutable en la factura | AC-MC-55 | L |
| T-MC-072 | Ola 7 · tesorería (15) | AC-MC-67 | XL |
| T-MC-073 | Aplicación entre empresas bloqueada | AC-MC-63 | L |
| T-MC-074 | Ola 8 · regulatorio (11) | AC-MC-68 | L |
| T-MC-075 | Ola 9 · auditoría, eventos, informes | FR-MC-040, FR-MC-041 | L |
| T-MC-076 | Listados acotados en el backend | FR-MC-021, AC-MC-30 | XL |
| T-MC-077 | Detalle de otra empresa ⇒ 404 | FR-MC-022, AC-MC-31 | L |
| T-MC-078 | Escritura sin empresa del cliente | FR-MC-023, AC-MC-34 | L |
| T-MC-079 | `company_id` no asignable en masa | FR-MC-024 | M |
| T-MC-080 | Empresa en la clave de caché | NFR-MC-03, AC-MC-96 | M |
| T-MC-081 | Idempotencia sin colisión entre empresas | NFR-MC-04, AC-MC-97 | M |

## N6 · Frontend

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-090 | Interceptor que envía la cabecera | FR-MC-011 | M |
| T-MC-091 | Selector con solo las empresas autorizadas | FR-MC-014 | L |
| T-MC-092 | Una sola empresa: sin control de cambio | FR-MC-013 | S |
| T-MC-093 | Invalidación total al cambiar | AC-MC-35, R-MC-12 | L |
| T-MC-094 | Pestañas independientes | FR-MC-015, AC-MC-18 | L |
| T-MC-095 | Limpieza al cerrar sesión | FR-MC-017, AC-MC-19 | M |
| T-MC-096 | **No** añadir campo empresa a los formularios | FR-MC-023 | S |
| T-MC-097 | Accesible y responsive | NFR-MC-05, NFR-MC-06, AC-MC-92, AC-MC-93 | M |

## N7 · Restringir

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-100 | `NOT NULL` tras verificar | FR-MC-060 | L |
| T-MC-101 | FK reales, comprobadas **en PostgreSQL** | FR-MC-061, AC-MC-01 | L |
| T-MC-102 | Revisión de los 13 únicos con alcance | FR-MC-062 | L |
| T-MC-103 | Unicidad de las secuencias fiscales | FR-MC-063 | XL |
| T-MC-104 | Índices justificados con `EXPLAIN` | NFR-MC-02, AC-MC-95 | L |
| T-MC-105 | Renombrar a `tenant_id` las 7 del tenant | CL-MC-12 | M |
| T-MC-106 | `company_id` real en `user_roles`, `user_scopes`, `audit_events` | CL-MC-12 | M |
| T-MC-107 | Migraciones `00XX_mc_constrain_<dominio>` | FR-MC-050 | L |

## N8 · Contraer

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-110 | Retirar columnas heredadas y de clase | FR-MC-057, AC-MC-79 | L |
| T-MC-111 | Retirar ramas de compatibilidad | FR-MC-057 | M |
| T-MC-112 | Migraciones `00XX_mc_contract_<dominio>` | FR-MC-050 | M |

## N9 · Spec 046 y cierre

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-120 | `ResourceKind` con alcance y resolutor explícitos | FR-MC-072, AC-MC-80 | L |
| T-MC-121 | Registrar `Payment`, `BankTransaction`, `CashSession`, `Reconciliation` | AC-MC-82 | M |
| T-MC-122 | Probar los **19** tipos: propia ⇒ vínculo, ajena ⇒ 404 | FR-MC-073, AC-MC-81 | XL |
| T-MC-123 | `STILL_BLOCKED_BY_046` = 0; matriz actualizada | AC-MC-83 | M |
| T-MC-124 | Cerrar `REM-046-001` y converger 046 | FR-MC-073 | L |
| T-MC-125 | Regresión de 046 con **ClamAV real** | AC-MC-84 | L |
| T-MC-126 | Integración 045 → 046 con versión congelada | FR-MC-071, AC-MC-84 | M |

## N10 · Pruebas y regresión

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-130 | Fixture multiempresa: T1(A,B) · T2(C) · UA/UB/UAB/UC | AC-MC-* | L |
| T-MC-131 | Suite de amenazas `AMC-01`..`AMC-17` | R-MC-* | XL |
| T-MC-132 | Cruce entre empresas: leer, listar, modificar, borrar | AC-MC-30, AC-MC-31, AC-MC-32, AC-MC-33, AC-MC-34 | XL |
| T-MC-133 | Aislamiento entre tenants intacto | AC-MC-36 | M |
| T-MC-134 | Pruebas de migración: limpia, previa, monoempresa, multiempresa, ambigua, crítica | AC-MC-77, AC-MC-78 | XL |
| T-MC-135 | Aborto sin escrituras destructivas parciales | AC-MC-73 | L |
| T-MC-136 | E2E multiempresa de 20 pasos | AC-MC-* | XL |
| T-MC-137 | E2E fiscal A/B | AC-MC-50..53 | XL |
| T-MC-138 | E2E de empresa falsificada y almacenamiento manipulado | FR-MC-012, AC-MC-17 | L |
| T-MC-139 | Cross-browser en Chromium, Firefox y WebKit | NFR-MC-07, AC-MC-94 | M |
| T-MC-140 | Regresión de 008, 011, 045, 046 sin romper sus contratos | FR-MC-070, FR-MC-074, closed-spec-impact | XL |
| T-MC-141 | Regresión global con **0 fallos** | AC-MC-91 | XL |
| T-MC-142 | Reaprovisionar PostgreSQL 18.6 y ClamAV | NFR-MC-01, AC-MC-90 | M |

## N11 · Gobierno posterior

| ID | Tarea | Req. | Est. |
|---|---|---|---|
| T-MC-150 | Actualizar baseline, GAP, grafo y roadmap | — | M |
| T-MC-151 | Revalidación corta de la Spec 012 | future-spec-contracts | M |
| T-MC-152 | `/speckit.converge ARCH-MC-001` | — | M |

## Resumen

| Fase | Tareas | Carga |
|---|---:|---|
| N0 Gobierno | 6 | L |
| N1 Contexto | 14 | **XL** |
| N2 Cortar la hemorragia | 6 | L |
| N3 Expandir | 4 | L |
| N4 Rellenar | 9 | **XL** |
| N5 Dominios | 22 | **XL** |
| N6 Frontend | 8 | L |
| N7 Restringir | 8 | L |
| N8 Contraer | 3 | M |
| N9 Spec 046 | 7 | L |
| N10 Pruebas | 13 | **XL** |
| N11 Gobierno | 3 | M |
| **Total** | **103** | — |

---

# N7 — TAREAS

Cada una con su requisito, su código y su prueba.

| Tarea | Requisito | Código / migración | Prueba |
|---|---|---|---|
| T-N7-001 Inventario del catálogo | NFR-N7-004 | script de inventario | `n7-postgresql-catalog-evidence.md` |
| T-N7-002 Reconciliar ORM / migraciones / catálogo | NFR-N7-004 | — | `test_n7_structure.py::paridad` |
| T-N7-003 Declarar alcance en las 13 sin declarar | FR-N7-004 | `organization/models.py` | `test_architecture_scope.py` |
| T-N7-004 Claves foráneas de empresa | FR-N7-001, 006, 026 | `0033_n7_company_fk` | `test_n7_structure.py::fk_company` |
| T-N7-005 Claves foráneas de tenant | FR-N7-002 | `0034_n7_tenant_fk` | `test_n7_structure.py::fk_tenant` |
| T-N7-006 Obligatoriedad de empresa | FR-N7-029 | `0035_n7_not_null` | `test_n7_structure.py::not_null` |
| T-N7-007 Coherencia empresa/almacén | FR-N7-014 | `0036_n7_consistency` | `test_n7_corruption.py::almacen_ajeno` |
| T-N7-008 Índices justificados | NFR-N7-005 | `0037_n7_indexes` | `n7-performance-evidence.md` |
| T-N7-009 Unicidad: verificar, no cambiar | FR-N7-007→010 | — | `test_n7_corruption.py::unicidad` |
| T-N7-010 Corrupción por SQL directo | FR-N7-030, AC-001→006 | — | `test_n7_corruption.py` |
| T-N7-011 Rutas derivadas | FR-N7-004, 005, 027 | — | `test_n7_structure.py::derivadas` |
| T-N7-012 Fiscal P0 | FR-N7-016→022 | — | `test_n7_corruption.py::fiscal` |
| T-N7-013 Paridad de cálculo fiscal | FR-N7-023, AC-008 | — | suite fiscal existente |
| T-N7-014 Instalación limpia | NFR-N7-003 | — | `n7-migration-report.md` |
| T-N7-015 SQL sin conexión | NFR-N7-002 | — | `n7-migration-report.md` |
| T-N7-016 Fixture hostil y aborto | AC-N7-007 | — | `n7-migration-report.md` |
| T-N7-017 Regresión N5 | AC-N7-009 | — | suites `test_mc_*` |
| T-N7-018 Regresión N6 | AC-N7-009 | — | Vitest + Playwright |
| T-N7-019 Cierre y convergencia | — | `convergence.md` | `n7-final-checkpoint.md` |

---

# N8 — TAREAS

| Tarea | Requisito | Código | Prueba |
|---|---|---|---|
| T-N8-001 Inventario de columnas transitorias | FR-001, 002 | — | `n8-legacy-removal-inventory.md` |
| T-N8-002 Inventario de lecturas y escrituras | FR-003, 004 | — | ídem |
| T-N8-003 Inventario de repliegues y ayudantes | FR-005, 006 | — | `n8-fallback-removal-report.md` |
| T-N8-004 Auditoría de cargas útiles | FR-024 | — | `n8-runtime-contract-inventory.md` |
| T-N8-005 Hueco de la cabecera en OpenAPI | FR-008 | — | `n8-openapi-contract-report.md` |
| T-N8-006 Fixture hostil reproducible | NFR-002, FR-015 | `qa/n4-legacy-hostile-seed.py` | `test_mc_preflight.py` |
| T-N8-007 Desacoplar `planes()` del ORM | FR-013, 014 | `app/core/mc/runner.py` | `test_mc_preflight.py` |
| T-N8-008 Retirar el repliegue | FR-005, 006 | `organization/service.py` + 4 llamantes | `test_n8_contract.py` |
| T-N8-009 Declarar la cabecera | FR-008, 009 | `app/core/company_context.py` | `test_n8_contract.py` |
| T-N8-010 Retirar columnas transitorias | FR-001, 002 | `0038_n8_drop_legacy` | catálogo |
| T-N8-011 Instalación limpia | AC-001 | — | `n8-regression-report.md` |
| T-N8-012 Preflight tras la retirada | FR-013, AC-003, 004 | — | `test_mc_preflight.py` |
| T-N8-013 Nulos globales | FR-019→021, AC-008 | — | `test_n8_contract.py` |
| T-N8-014 Auditoría de skips | FR-025, AC-009 | — | `n8-skipped-tests-audit.md` |
| T-N8-015 Documentación obsoleta | FR-023 | matrices | — |
| T-N8-016 Regresiones N5/N6/N7 | FR-026 | — | suites completas |
| T-N8-017 Cierre y convergencia | — | `convergence.md` | `n8-final-checkpoint.md` |

---

# N8 — SELLO FINAL DE EVIDENCIA

| Tarea | Requisito | Código | Prueba |
|---|---|---|---|
| N8-EVIDENCE-MC-D | FR-N8-016 | semilla en el fixture | `test_mc_preflight` |
| N8-EVIDENCE-INVALID | FR-N8-017 | semilla en el fixture | ídem |
| N8-EVIDENCE-CROSS-TENANT | FR-N8-018 | **`preflight.py`: emitir la clase** | ídem |
| N8-EVIDENCE-MASTER-RUN | FR-N8-016 | **`preflight.py` / `runner.py`: calcularlas** | ídem |
| N8-EVIDENCE-MASTER-DERIVE | FR-N8-016 | **`estrategia_de_maestro`: condición de disparo** | ídem |
| N8-EVIDENCE-ZERO-WRITE | NFR-N8-003 | — | por caso |
| N8-EVIDENCE-REPEATABLE | NFR-N8-003 | — | por caso |
| N8-EVIDENCE-SEED-ASSERT | NFR-N8-002 | aserciones en el fixture | ídem |

---

# N9 — TAREAS

| Tarea | Requisito | Código | Prueba |
|---|---|---|---|
| T-N9-001 Confirmar cardinalidad | FR-001 | — | `test_n9_registry` |
| T-N9-002 Enumerar el registro | FR-002 | — | ídem |
| T-N9-003 Matriz de alcance y autoridad | FR-005, 011–014 | — | `n9-resourcekind-authority-matrix.md` |
| T-N9-004 Matriz de permisos | FR-006 | — | ídem |
| T-N9-005…008 Auditar las cuatro entidades | FR-007–010 | — | ídem |
| T-N9-009…012 Registrarlas | FR-007–010 | `documents/resources.py` | `test_n9_registry` |
| T-N9-013 Registro cerrado | FR-017, 018 | — | `test_n9_registry::desconocido` |
| T-N9-014 Sembrar los 23 | AC-002 | fixture | `test_n9_resourcekinds` |
| T-N9-015 Alcance propio 23/23 | FR-011, AC-003 | — | ídem |
| T-N9-016 Entre empresas 23/23 | FR-015 | — | ídem |
| T-N9-017 Entre tenants 23/23 | FR-016 | — | ídem |
| T-N9-018 Vincular y desvincular | FR-020–023 | — | `test_n9_documentlink` |
| T-N9-019 Descarga y previsualización | FR-024–026 | — | ídem |
| T-N9-020 Congelado e invariancia | FR-027, 028 | — | `test_n9_frozen` |
| T-N9-021 Hash y objeto alterado | FR-029, 030 | — | `test_n9_integrity` |
| T-N9-022 ClamAV real | FR-031–033 | — | suite documental |
| T-N9-023 S3 y retención | FR-035, 036 | — | `n9-s3-status-report.md` |
| T-N9-024 Integración 045 | FR-037, 038 | — | `n9-spec045-integration-report.md` |
| T-N9-025 Matriz de consumidores | FR-041, 042 | — | `n9-consumer-dependency-matrix.md` |
| T-N9-026 Regresiones N5–N8 | FR-039 | — | suites completas |
| T-N9-027 Reconvergencia de 046 | FR-043 | — | `n9-spec046-reconvergence-report.md` |
| T-N9-028 Cerrar REM-046-001 | FR-044 | `docs/remediation/` | `n9-rem-046-001-closeout.md` |
| T-N9-029 Convergencia delta | — | `convergence.md` | `n9-final-checkpoint.md` |

---

# TAREAS — N10

| Id | Tarea | Estado |
|---|---|---|
| T-N10-001 | Inventario actual de modelos ORM | Hecha — 166 |
| T-N10-002 | Inventario actual de tablas | Hecha — 166 |
| T-N10-003 | Inventario actual de alcances | Hecha — 0 indeterminados |
| T-N10-004 | Inventario de rutas derivadas | Hecha — 41, cinco nuevas |
| T-N10-005 | Inventario de unicidad | Hecha — 80 restricciones, 214 índices |
| T-N10-006 | Inventario de claves foráneas | Hecha — 331 |
| T-N10-007 | Inventario de alcance de la API | Hecha — 404 operaciones |
| T-N10-008 | Inventario de OpenAPI | Hecha — 294 rutas, 342 con empresa |
| T-N10-009 | Inventario de `ResourceKind` | Hecha — 23 |
| T-N10-010 | Inventario de migraciones | Hecha — 39 |
| T-N10-011 | Inventario de pruebas y saltos | Hecha |
| T-N10-012..022 | Reconciliar Constitución, ADR y N0–N9 | Hecha — `n10-n0-n9-decision-reconciliation.md` |
| T-N10-023 | Humo A/B global de dominio | Hecha — 9 defectos |
| T-N10-024 | Humo fiscal global | Hecha |
| T-N10-025 | Barrido de seguridad empresa/tenant | Hecha — 12 defectos |
| T-N10-026 | Regresión hostil de N4 | Hecha — 8 clases, 4 estrategias |
| T-N10-027 | Regresión de `ResourceKind` | Hecha |
| T-N10-028 | Regresión de Spec 045 y 046 | Hecha |
| T-N10-029 | Auditoría de cifras obsoletas | Hecha |
| T-N10-030 | Reconciliar el grafo de dependencias | Hecha |
| T-N10-031 | Clasificación de deuda | Hecha — 0 P0 |
| T-N10-032 | Regresión completa del backend | Hecha |
| T-N10-033 | Regresión completa del frontend | Hecha — 278/278, tsc, eslint |
| T-N10-034 | Playwright multiempresa | Hecha — sin cambios de frontend en N10 |
| T-N10-035 | Rutas, autenticación y OpenAPI | Hecha |
| T-N10-036 | Instalación limpia sobre PostgreSQL 18.6 | Hecha — `head` = `0039` |
| T-N10-037 | Trazabilidad global | Hecha — 100% |
| T-N10-038 | Reconciliación de artefactos | Hecha |
| T-N10-039 | `/speckit.converge ARCH-MC-001` | Hecha |
| T-N10-040 | Veredicto final de la arquitectura | Hecha |
| T-N10-041 | Revalidación documental de la Spec 012 | Hecha |
| T-N10-042 | Detenerse antes de implementar la 012 | Cumplida |
