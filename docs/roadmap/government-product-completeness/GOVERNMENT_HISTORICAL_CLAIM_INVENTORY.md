# GOVERNMENT_HISTORICAL_CLAIM_INVENTORY

> Generado desde el CSV homónimo (fuente de verdad legible por máquina). Medición: `develop` `0dbe632`; IR de Gobierno v1.0 SHA `8f86615f…`.

Búsqueda: todo `.md` versionado en `docs/`, `specs/`, `.specify/memory/`, `README.md` y `CLAUDE.md` en `HEAD`, con mención de Gobierno (gobierno, government, GOV-, RNF-GOV, D-GOV, ente) **y** palabra de estado (READY, DONE, IMPLEMENTED, CERTIFIED, CLOSED, COMPLETE, PASS, OWNER_ACCEPTED, CONVERGED, BLOCKED, GAP, 100 %, listo, terminado…): 44 líneas. Se añaden las filas de la tabla RNF de la readiness, los cierres técnicos de los fundamentos, dos afirmaciones del árbol del ciclo 07 (sin commit), los tres ejemplos del encargo y una frase de la memoria de Claude.

| Veredicto | N |
|---|---|
| CONFIRMED | 27 |
| TECHNICAL_FOUNDATION | 20 |
| PARTIAL | 9 |
| TECHNICAL_FOUNDATION_COMPLETE | 4 |
| CONFIRMED — PLANNING CLOSED, NOT PRODUCT | 3 |
| NOT_A_GOVERNMENT_CLAIM | 3 |
| CLAIM_NOT_FOUND_IN_REPOSITORY | 3 |
| PREMATURE | 2 |
| OUT_OF_SCOPE_PRIVATE_LINE | 1 |
| NOT_MEASURED | 1 |
| TECHNICALLY CLOSED BUT NOT PRODUCT COMPLETE | 1 |
| NOT_A_STATUS_CLAIM | 1 |

| Id | Fuente | Estado original | Fecha | Veredicto actual | Motivo |
|---|---|---|---|---|---|
| HC-001 | docs/roadmap/government-architecture-baseline.md:20 | CLOSED,PLANNING_BASELINE | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED — PLANNING CLOSED, NOT PRODUCT | cierre de un documento de planificación; no es producto |
| HC-002 | docs/roadmap/government-architecture-baseline.md:23 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-003 | docs/roadmap/government-architecture-baseline.md:130 | REUSABLE_AFTER_SHARED_CORE_DELTA | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | clasificación técnica del núcleo; hoy F01; no concede estado de producto de Gobierno |
| HC-004 | docs/roadmap/government-architecture-baseline.md:133 | REUSABLE_AS_IS | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | clasificación técnica del núcleo; hoy F31; no concede estado de producto de Gobierno |
| HC-005 | docs/roadmap/government-architecture-baseline.md:134 | REUSABLE_AS_IS | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | clasificación técnica del núcleo; hoy F31; no concede estado de producto de Gobierno |
| HC-006 | docs/roadmap/government-architecture-baseline.md:136 | REUSABLE_AS_IS | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | clasificación técnica del núcleo; hoy F32; no concede estado de producto de Gobierno |
| HC-007 | docs/roadmap/government-architecture-baseline.md:138 | REUSABLE_AS_IS | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | clasificación técnica del núcleo; hoy F33; no concede estado de producto de Gobierno |
| HC-008 | docs/roadmap/government-architecture-baseline.md:139 | REUSABLE_AS_IS | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | clasificación técnica del núcleo; hoy F34; no concede estado de producto de Gobierno |
| HC-009 | docs/roadmap/government-architecture-baseline.md:281 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-010 | docs/roadmap/government-architecture-baseline.md:364 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-011 | docs/roadmap/government-architecture-baseline.md:367 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-012 | docs/roadmap/government-architecture-baseline.md:382 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-013 | docs/roadmap/government-architecture-baseline.md:469 | COMPLETE | ≤ 2026-10-28 (HEAD 0dbe632) | OUT_OF_SCOPE_PRIVATE_LINE | afirma COMPLETE de un módulo privado (008); técnicamente cerrado, no revalidado como producto con la norma nueva (retrospectiva privada pendiente: MOQ-RETRO-01) |
| HC-014 | docs/roadmap/government-architecture-baseline.md:639 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-015 | docs/roadmap/government-architecture-baseline.md:641 | CLOSED,PLANNING_BASELINE | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED — PLANNING CLOSED, NOT PRODUCT | cierre de un documento de planificación; no es producto |
| HC-016 | docs/roadmap/government-architecture-baseline.md:650 | SPONSOR REVIEW | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-017 | docs/roadmap/government-architecture-baseline.md:661 | BLOCKED,CLOSED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-018 | docs/roadmap/government-start-readiness.md:9 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-019 | docs/roadmap/government-start-readiness.md:11 | SPONSOR REVIEW | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-020 | docs/roadmap/government-start-readiness.md:36 | READY_WITH_GAPS | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | readiness técnica del núcleo; ver la fila RNF de la matriz de fundamentos |
| HC-021 | docs/roadmap/government-start-readiness.md:37 | READY | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | readiness técnica del núcleo; ver la fila RNF de la matriz de fundamentos |
| HC-022 | docs/roadmap/government-start-readiness.md:64 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-023 | docs/roadmap/government-start-readiness.md:65 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-024 | docs/roadmap/government-start-readiness.md:66 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-025 | docs/roadmap/government-start-readiness.md:68 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-026 | docs/roadmap/government-start-readiness.md:92 | GAP | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-027 | docs/roadmap/government-start-readiness.md:93 | GAP | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-028 | docs/roadmap/government-start-readiness.md:97 | GAP | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-029 | docs/roadmap/government-start-readiness.md:188 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-030 | docs/roadmap/government-start-readiness.md:193 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-031 | docs/roadmap/government-start-readiness.md:197 | SPONSOR REVIEW | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-032 | docs/roadmap/government-start-readiness.md:213 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-033 | docs/roadmap/kontrol-gobierno-source-register.md:16 | NOT_STARTED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-034 | docs/roadmap/master-56-specs-status.md:10 | SPONSOR REVIEW | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-035 | docs/roadmap/source-inventory.md:26 | SPONSOR REVIEW | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-036 | docs/roadmap/spec-equivalence-map.md:91 | GAP | ≤ 2026-10-28 (HEAD 0dbe632) | NOT_A_GOVERNMENT_CLAIM | la palabra es «gobierno» en sentido de gobernanza o decisión; no afirma estado de producto de Gobierno |
| HC-037 | docs/roadmap/technical-debt-matrix.md:2459 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-038 | docs/roadmap/technical-debt-matrix.md:2461 | SPONSOR REVIEW | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED | sigue siendo cierto: ninguna implementación de Gobierno en HEAD |
| HC-039 | docs/roadmap/technical-debt-matrix.md:2470 | CLOSED,PLANNING_BASELINE | ≤ 2026-10-28 (HEAD 0dbe632) | CONFIRMED — PLANNING CLOSED, NOT PRODUCT | cierre de un documento de planificación; no es producto |
| HC-040 | specs/001-fundacion/spec002-mfa-privileged-roles-delta.md:11 | COMPLETE,CONVERGED,IMPLEMENTED | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | clasificación técnica del núcleo; hoy F01; no concede estado de producto de Gobierno |
| HC-041 | specs/001-fundacion/spec002-mfa-privileged-roles-delta.md:662 | BLOCKED | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | clasificación técnica del núcleo; hoy F01; no concede estado de producto de Gobierno |
| HC-042 | specs/009-reportes-auditoria/spec009-report-export-download-delta.md:374 | GAP | ≤ 2026-10-28 (HEAD 0dbe632) | NOT_A_GOVERNMENT_CLAIM | la palabra es «gobierno» en sentido de gobernanza o decisión; no afirma estado de producto de Gobierno |
| HC-043 | specs/012-auditoria-integral-e2e/spec054-canonicalize-certification-environment-delta.md:6 | READY | ≤ 2026-10-28 (HEAD 0dbe632) | TECHNICAL_FOUNDATION | readiness técnica del núcleo; ver la fila RNF de la matriz de fundamentos |
| HC-044 | specs/arch-mc-001-canonical-multi-company-scope/pre-backfill-gate.md:9 | COMPLETE | ≤ 2026-10-28 (HEAD 0dbe632) | NOT_A_GOVERNMENT_CLAIM | la palabra es «gobierno» en sentido de gobernanza o decisión; no afirma estado de producto de Gobierno |
| HC-R01 | docs/roadmap/government-start-readiness.md:35-50 | READY_WITH_GAPS | 2026-10-25 | PARTIAL | medido hoy: F05 PARTIAL + F06 NOT_STARTED |
| HC-R02 | docs/roadmap/government-start-readiness.md:35-50 | READY | 2026-10-25 | PARTIAL | PARTIAL (las 4 columnas Float no se han reverificado) — medido hoy: F13 PARTIAL |
| HC-R03 | docs/roadmap/government-start-readiness.md:35-50 | GAP | 2026-10-25 | TECHNICAL_FOUNDATION_COMPLETE | TECHNICAL_FOUNDATION COMPLETE (b24b121) — medido hoy: F09 COMPLETE |
| HC-R04 | docs/roadmap/government-start-readiness.md:35-50 | NOT_MEASURED | 2026-10-25 | NOT_MEASURED | medido hoy: F14 NOT_MEASURED |
| HC-R05 | docs/roadmap/government-start-readiness.md:35-50 | GAP | 2026-10-25 | PARTIAL | PARTIAL (núcleo cerrado; dimensiones institucionales sin construir) — medido hoy: F07 COMPLETE + F08 NOT_STARTED |
| HC-R06 | docs/roadmap/government-start-readiness.md:35-50 | READY | 2026-10-25 | TECHNICAL_FOUNDATION_COMPLETE | TECHNICAL_FOUNDATION COMPLETE — medido hoy: F03 + F04 COMPLETE |
| HC-R07 | docs/roadmap/government-start-readiness.md:35-50 | NOT_MEASURED | 2026-10-25 | PARTIAL | medido hoy: F15 PARTIAL |
| HC-R08 | docs/roadmap/government-start-readiness.md:35-50 | GAP | 2026-10-25 | PARTIAL | PARTIAL (restauración verificada; RTO/RPO pendientes) — medido hoy: F11 COMPLETE + F12 NOT_STARTED |
| HC-R09 | docs/roadmap/government-start-readiness.md:35-50 | GAP | 2026-10-25 | PARTIAL | PARTIAL (MFA hecho; rotación no medida) — medido hoy: F01 COMPLETE + F18 PARTIAL |
| HC-R10 | docs/roadmap/government-start-readiness.md:35-50 | GAP | 2026-10-25 | TECHNICAL_FOUNDATION_COMPLETE | TECHNICAL_FOUNDATION COMPLETE (021c1c6) — medido hoy: F02 COMPLETE |
| HC-R11 | docs/roadmap/government-start-readiness.md:35-50 | READY_WITH_GAPS | 2026-10-25 | PARTIAL | medido hoy: F19 PARTIAL |
| HC-R12 | docs/roadmap/government-start-readiness.md:35-50 | READY_WITH_GAPS | 2026-10-25 | PARTIAL | medido hoy: F20 PARTIAL |
| HC-R13 | docs/roadmap/government-start-readiness.md:35-50 | GAP | 2026-10-25 | TECHNICAL_FOUNDATION_COMPLETE | TECHNICAL_FOUNDATION COMPLETE (f24e74e) — medido hoy: F10 COMPLETE |
| HC-R14 | docs/roadmap/government-start-readiness.md:35-50 | READY_WITH_GAPS | 2026-10-25 | PARTIAL | medido hoy: F22 PARTIAL |
| HC-D01 | specs/001-fundacion/spec002-mfa-privileged-roles-delta.md | IMPLEMENTED — CONVERGED | 2026-10-26 | TECHNICALLY CLOSED BUT NOT PRODUCT COMPLETE | TECHNICALLY CLOSED BUT NOT PRODUCT COMPLETE (fundamento F01; pantalla /seguridad/mfa existe para el usuario privilegiado, no es un proceso de Gobierno) |
| HC-D02 | specs/001-fundacion/spec002-password-reset-token-delta.md | IMPLEMENTED — CONVERGED | 2026-10-26 | TECHNICAL_FOUNDATION | TECHNICAL_FOUNDATION (F01) |
| HC-D03 | specs/001-fundacion/spec003-delegation-ceiling-delta.md | IMPLEMENTED — CONVERGED | 2026-10-26 | TECHNICAL_FOUNDATION | TECHNICAL_FOUNDATION (F02) |
| HC-D04 | specs/001-fundacion/spec003-company-scope-authorization-delta.md | IMPLEMENTED — CONVERGED | 2026-10-27 | TECHNICAL_FOUNDATION | TECHNICAL_FOUNDATION (F03) |
| HC-D05 | specs/001-fundacion/spec003-ui-company-aware-authorization-delta.md | IMPLEMENTED — CONVERGED | 2026-10-27 | TECHNICAL_FOUNDATION | TECHNICAL_FOUNDATION (F04) |
| HC-D06 | specs/001-fundacion/spec003-read-permission-enforcement-delta.md | IMPLEMENTED — CONVERGED | 2026-10-27 | TECHNICAL_FOUNDATION | TECHNICAL_FOUNDATION (F03) |
| HC-D07 | specs/001-fundacion/spec001-audit-catalog-delta.md | IMPLEMENTED — VERIFIED — CONVERGED | 2026-10-28 | TECHNICAL_FOUNDATION | TECHNICAL_FOUNDATION (F07) |
| HC-D08 | specs/001-fundacion/spec001-business-civil-date-delta.md | IMPLEMENTED — VERIFIED — CONVERGED | 2026-10-28 | TECHNICAL_FOUNDATION | TECHNICAL_FOUNDATION (F09) |
| HC-D09 | specs/001-fundacion/spec001-strict-api-input-contract-delta.md | IMPLEMENTED — VERIFIED — CONVERGED | 2026-10-28 | TECHNICAL_FOUNDATION | TECHNICAL_FOUNDATION (F10) |
| HC-D10 | specs/001-fundacion/spec001-backup-restore-verification-delta.md | IMPLEMENTED — CERTIFIED (QA) — CONVERGED | 2026-10-28 | TECHNICAL_FOUNDATION | TECHNICAL_FOUNDATION (F11); RTO/RPO siguen abiertos (F12) |
| HC-D11 | specs/012-auditoria-integral-e2e/ | IMPLEMENTED — CERTIFICATION PENDING | 2026-10-25 | CONFIRMED | CONFIRMED: BLOCKED (F30) por el anfitrión dedicado |
| HC-W01 | árbol de trabajo: docs/roadmap/government-start-readiness.md (fila 001) | PREREQUISITES_CERTIFIED (núcleo) | 2026-10-29, sin commit | PREMATURE | PREMATURE: el ciclo 07 está pausado sin E2E de aislamiento; F05 = PARTIAL. Se corrige en el árbol y no entra en esta retrospectiva |
| HC-W02 | árbol de trabajo: specs/001-fundacion/evidence/isolation-prerequisites/GOVERNMENT_REQUIREMENTS_RECONCILIATION.md | CORE_ISOLATION_PREREQUISITES = CERTIFIED | 2026-10-29, sin commit | PREMATURE | PREMATURE: mismo motivo; se marca pendiente de la E2E |
| HC-P01 | encargo GOV-PRODUCT-COMPLETENESS-RETRO-01 §50 (ejemplo) | «Activo Fijo listo» | — | CLAIM_NOT_FOUND_IN_REPOSITORY | CLAIM_NOT_FOUND_IN_REPOSITORY. Real: Gobierno AST-01..11 = BLOCKED/NOT_STARTED; Spec 057 privada = PLANNED / NOT_STARTED |
| HC-P02 | encargo §50 (ejemplo) | «Contrataciones 70 %» | — | CLAIM_NOT_FOUND_IN_REPOSITORY | CLAIM_NOT_FOUND_IN_REPOSITORY. Real: PROC-01..12 y CNT-01..09 = 0 % (0 compuertas) |
| HC-P03 | encargo §50 (ejemplo) | «Prefecturas listo» | — | CLAIM_NOT_FOUND_IN_REPOSITORY | CLAIM_NOT_FOUND_IN_REPOSITORY y NOT_IN_REQUIREMENTS: ni la IR v1.0 ni el repositorio contienen Prefecturas |
| HC-M01 | memoria de Claude certificacion-v6-y-snat-diferida (no versionada) | «SNAT/2026/00093 tras Gobierno 100 %» | 2026-10-24 | NOT_A_STATUS_CLAIM | NOT_A_STATUS_CLAIM: es una condición de secuencia; Gobierno hoy = 0 % funcional |
