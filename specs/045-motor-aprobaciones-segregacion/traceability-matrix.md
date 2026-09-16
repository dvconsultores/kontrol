# MATRIZ DE TRAZABILIDAD — SPEC 045

Cadena exigida por P3: **Requisito → Spec → Plan → Tarea → Código → Prueba → Evidencia.**
Código y evidencia quedan pendientes: no hay autorización de implementación.

## Fuente documental → requisito

| Fuente | Requisitos derivados |
|---|---|
| `ADR-D0-002` R-D0-02-1 (no hardcodear) | FR-045-001, 006, NFR-045-07 |
| R-D0-02-2 (versionado) | FR-045-001, 004, 005 |
| R-D0-02-3 (snapshot) | FR-045-020, INV-07 |
| R-D0-02-4 (auditoría) | FR-045-064 |
| R-D0-02-5 (segregación) | FR-045-007, 040, INV-05 |
| R-D0-02-6 (cuórum) | FR-045-003, 028 |
| R-D0-02-7 (rechazo terminal) | FR-045-023 |
| R-D0-02-8 (delegación) | FR-045-042..046 |
| R-D0-02-9 (obsolescencia) | FR-045-050..052 |
| R-D0-02-10 (motor único) | FR-045-070..075 |
| `POL-D0-001` §4 | FR-045-011, 029, 005 |
| Constitución **P22** | FR-045-075, AC-21 |
| Constitución **P21** | NFR-045-06, test-plan §3 |
| Constitución **P23** | FR-045-020, 050 |
| Constitución P6 | FR-045-062, 063, AC-17 |
| Constitución P8 | NFR-045-07, AC-23 |
| Constitución P13 | FR-045-053..055 |
| `ADR-012` | FR-045-064 |
| `ADR-013` | FR-045-053, 054 |
| `ADR-015` / P18 | NFR-045-05, WF-045-03 |
| `ADR-D0-008` | FR-045-067 |
| `ADR-011` / `ADR-D0-013` | Alcance por empresa en todo endpoint |
| Vol. 1 §4 (módulo Aprobaciones) | Alcance §3 |
| Vol. 1 §5 («un usuario no crea y aprueba su propia excepción crítica») | FR-045-040, 041 |
| Vol. 2 §1 (rama Aprobaciones del menú) | WF-045-01..06 |
| Vol. 2 §2 (estándar de pantalla) | NFR-045-02, 05, WF §Estados |

## Requisito → historia → tarea → criterio → prueba

| Requisito | HU | Tarea | AC | Prueba |
|---|---|---|---|---|
| FR-045-001..005 | HU-01 | T-045-002, 003, 040 | AC-01, AC-02 | Unidad + integración |
| FR-045-006, 007 | HU-01 | T-045-007, 029 | AC-05 | Integración |
| FR-045-010, 013 | HU-02 | T-045-011, 014 | AC-04 | Unidad evaluador |
| FR-045-011 | HU-02 | T-045-012 | **AC-03** | Unidad moneda |
| FR-045-015 | HU-02 | T-045-013 | **AC-04** | Unidad |
| FR-045-014 | HU-08 | T-045-015, 021 | AC-05 | Integración |
| FR-045-020, 053 | HU-02 | T-045-020 | AC-10 | Idempotencia |
| FR-045-021, 022, 028 | HU-09, HU-10 | T-045-022 | AC-11, AC-12 | Unidad cuórum + integración |
| FR-045-023, 026 | HU-03 | T-045-023 | AC-13, AC-15 | Integración |
| FR-045-024, 030 | HU-05 | T-045-024 | AC-14 | E2E devolución |
| FR-045-025 | HU-03 | T-045-025 | — | Integración |
| FR-045-027 | HU-03 | T-045-031 | **AC-16** | Integración vencimiento |
| FR-045-029 | HU-02 | T-045-062..065 | **AC-17** | Integración por dominio |
| FR-045-040, 041 | HU-04 | T-045-029 | **AC-05** | Prueba negativa |
| FR-045-042..046 | HU-06 | T-045-030 | AC-06, AC-18 | Prueba negativa |
| FR-045-050..052 | HU-07 | T-045-016, 026 | AC-07, **AC-08** | Concurrencia |
| FR-045-054, 055 | — | T-045-027, 028 | **AC-09** | **Concurrencia PostgreSQL** |
| FR-045-060 | HU-03 | T-045-042, 052 | AC-19 | E2E bandeja |
| FR-045-061 | HU-08 | T-045-044, 053 | AC-14 | Integración |
| FR-045-062, 063 | HU-04 | T-045-046, 006 | AC-05 | Contrato |
| FR-045-064 | HU-08 | T-045-032 | — | Integración auditoría |
| FR-045-066 | — | T-045-033 | — | Unidad eventos |
| FR-045-067 | — | *(contrato; Spec 046)* | — | — |
| FR-045-070..075 | — | T-045-060..067 | AC-20, AC-21, AC-22 | Regresión 4 dominios |
| NFR-045-01 | — | T-045-042 | — | Rendimiento |
| NFR-045-03, 04 | — | T-045-078, 079 | AC-24 | axe + responsive |
| NFR-045-06 | — | Todas | Todas | PostgreSQL |
| NFR-045-07 | — | Todas | **AC-23** | Búsqueda de literales |

## Cobertura

| Métrica | Valor |
|---|---:|
| Requisitos funcionales | 40 |
| Requisitos no funcionales | 7 |
| Historias de usuario | 10 |
| Tareas | 65 |
| Criterios de aceptación | 24 |
| **Requisitos sin tarea** | **0** |
| **Requisitos sin criterio** | **1** — FR-045-067, contrato diferido a la Spec 046 y declarado |
| **Tareas sin requisito** | **0** |
| **Historias sin criterio** | **0** |

---

## Delta dirigido E2E-045 *(2026-09-16)*

Cobertura del delta, que no altera las cifras anteriores porque no toca producto:
añade cinco requisitos de verificación y cinco criterios.

| Requisito | Tarea | Criterio | Prueba | Mutación que lo mata |
|---|---|---|---|---|
| FR-045-076 | T-01, T-04 | AC-28 | `approvals.spec.ts` · regresión en `activarEmpresa` + «el localizador nunca alcanza Desactivar» | E2E-045-01 |
| FR-045-077 | T-01, T-03 | AC-25, AC-26, AC-27 | «el ayudante de empresa es idempotente» | E2E-045-02 |
| FR-045-078 | T-01 | AC-26 | fallo explícito con diagnóstico en `activarEmpresa` | E2E-045-02 |
| FR-045-079 | T-02 | AC-28 | aserción permanente dentro del ayudante | E2E-045-01 |
| FR-045-080 | T-05 | AC-29 | «la bandeja la delimita el contexto, no el parámetro» | E2E-045-03 |

| Métrica tras el delta | Valor |
|---|---:|
| Requisitos funcionales | 40 **+ 5** (FR-045-076..080, de verificación) |
| Criterios de aceptación | 24 **+ 5** (AC-25..29) |
| Requisitos del delta sin prueba | **0** |
| Criterios del delta sin prueba | **0** |
| Mutaciones supervivientes | **0** |
| Ficheros de producto modificados | **0** |
