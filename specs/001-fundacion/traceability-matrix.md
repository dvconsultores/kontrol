# MATRIZ DE TRAZABILIDAD — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Ruta | `specs/001-fundacion/traceability-matrix.md` |

Formato: | Requisito | Historia | Diseño | ADR | Contrato | Tarea | Prueba | Evidencia |

| Requisito | Historia | Diseño | ADR | Contrato | Tarea | Prueba | Evidencia |
|---|---|---|---|---|---|---|---|
| FR-001-001 | US-001 | plan.md §2 | ADR-002, ADR-014 | api-contracts (health) | T-004, T-005, T-007 | E2E instalación | `evidence/` (T-047) |
| FR-001-002 | US-002 | data-model §2.1 | ADR-002 | license-contract | T-011 | Test persistencia | evidence |
| FR-001-003 | US-002 | data-model §2.1 | ADR-002 | — | T-012 | E2E recreación | evidence |
| FR-001-004 | US-003, US-011 | license-foundation | ADR-005 | license-contract | T-015, T-016 | Test calendario/bloqueo | evidence |
| FR-001-005 | US-013 | security-baseline | — | — | T-006 | Test arranque | evidence |
| FR-001-010 | US-004 | WF-06 | — | api-contracts | T-024 | E2E setup | evidence |
| FR-001-011 | US-005 | data-model §2.2 | — | — | T-023 | E2E cambio contraseña | evidence |
| FR-001-012 | US-005 | security-baseline | ADR-004 | — | T-018 | Test contraseñas | evidence |
| FR-001-013 | US-015 | data-model §2.2 | ADR-004 | — | T-022 | Test recuperación | evidence |
| FR-001-020 | US-006 | data-model §2.2 | ADR-004 | api-contracts | T-019 | Test autenticación | evidence |
| FR-001-021 | US-006 | ADR-004 | ADR-004 | api-contracts | T-019 | Test cookies | evidence |
| FR-001-022 | US-016 | data-model §2.2 | ADR-004 | — | T-020 | Test sesiones | evidence |
| FR-001-023 | US-006 | security-baseline | — | — | T-021 | Test rate limit | evidence |
| FR-001-024 | US-006 | security-baseline | ADR-004 | — | (MFA) | Test MFA | evidence (fase) |
| FR-001-030 | US-017 | data-model §2.1 | ADR-011 | api-contracts | T-025 | Test multiempresa | evidence |
| FR-001-031 | US-017 | data-model §2.1 | ADR-011 | — | T-025 | Test límites licencia | evidence |
| FR-001-032 | US-007 | ADR-011 | ADR-011 | — | T-025, T-026 | Aislamiento negativo | evidence |
| FR-001-033 | US-008 | ADR-011 | ADR-011 | — | T-025 | Aislamiento negativo | evidence |
| FR-001-040 | US-007 | data-model §2.2 | ADR-011 | — | T-026 | Test permisos | evidence |
| FR-001-041 | US-007 | WF-01 | — | api-contracts | T-027 | Contract test | evidence |
| FR-001-042 | US-008 | frontend-foundation | ADR-006 | error-contract | T-028 | Component/E2E | evidence |
| FR-001-043 | US-007 | security-baseline | ADR-011 | — | T-026 | Test SoD | evidence |
| FR-001-050 | US-003 | license-foundation | ADR-005 | license-contract | T-013 | Test firma | evidence |
| FR-001-051 | US-010 | data-model §2.3 | ADR-005 | license-contract | T-014 | Test estado | evidence |
| FR-001-052 | US-011 | license-foundation | ADR-005 | license-contract | T-015 | Test calendario | evidence |
| FR-001-053 | US-011 | license-foundation | ADR-005 | error-contract | T-016 | Test bloqueo | evidence |
| FR-001-054 | US-010 | WF-09 | ADR-005 | api-contracts | T-017, T-039 | E2E | evidence |
| FR-001-055 | US-003 | license-foundation | ADR-005 | license-contract | T-013 | Test clave privada | evidence |
| FR-001-056 | US-011 | license-foundation | ADR-005 | license-contract | T-015 | Test fecha confiable | evidence |
| FR-001-060 | US-007 | frontend-foundation | ADR-006 | — | T-030, T-031 | Vitest | evidence |
| FR-001-061 | US-007 | frontend-foundation | ADR-006, ADR-015 | — | T-032 | E2E rutas | evidence |
| FR-001-062 | US-007 | WF-02 | ADR-015 | — | T-033 | Regresión visual | evidence |
| FR-001-063 | US-014 | frontend-foundation | ADR-006 | error-contract | T-034 | Vitest | evidence |
| FR-001-064 | US-014 | WF-02 | ADR-015 | — | T-035 | Component test | evidence |
| FR-001-065 | US-007 | WF-01 | ADR-006 | — | T-036 | Vitest + visual | evidence |
| FR-001-066 | US-007 | frontend-foundation | ADR-006 | — | T-037 | axe + Playwright | evidence |
| FR-001-067 | US-011 | WF-09 | ADR-005 | — | T-038 | Component test | evidence |
| FR-001-070 | US-018 | data-model §2.4 | ADR-012 | events | T-029 | Test auditoría | evidence |
| FR-001-071 | US-018 | data-model §2.4 | ADR-012 | — | T-029 | Test inmutabilidad | evidence |
| FR-001-072 | US-018 | data-model §2.4 | ADR-012 | events | T-029 | Test eventos | evidence |
| FR-001-080 | US-013 | infrastructure-plan | ADR-010 | api-contracts | T-008 | Test health | evidence |
| FR-001-081 | US-013 | ADR-010 | ADR-010 | — | T-009 | Test logs | evidence |
| FR-001-082 | US-012 | plan.md | ADR-014 | — | T-041, T-045 | Test migraciones/CI | evidence |
| FR-001-083 | US-012 | backup-restore-plan | — | — | T-042 | Test restore | evidence |
| FR-001-084 | US-013 | infrastructure-plan | — | — | T-043 | Test diagnóstico | evidence |
| FR-001-090 | — | plan.md §4 | ADR-001 | — | T-044 | Test modelo | evidence |
| FR-001-091 | — | research.md | — | — | T-044 | Test reglas | evidence |

## Reglas de integridad de la matriz

- No existe requisito sin prueba. ✔
- No existe tarea sin requisito. ✔ (T-003/CHK no funcional asociado a checklist)
- No existe código futuro sin tarea. ✔ (el plan no autoriza código)
- Cada historia US tiene al menos un requisito. ✔

## Estado

| Elemento | Estado |
|---|---|
| Requisito → Historia | ✔ |
| Requisito → Diseño | ✔ |
| Requisito → ADR | ✔ |
| Requisito → Contrato | ✔ |
| Requisito → Tarea | ✔ |
| Requisito → Prueba | ✔ |
| Requisito → Evidencia | Pendiente (implementación) |
