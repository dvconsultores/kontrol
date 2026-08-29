# TAREAS — 013 (tareas de AUDITORÍA, no de implementación)

| ID | Tarea | Estado | Evidencia |
|---|---|---|---|
| T-013-001 | Verificar estado Git y estructura del repositorio | [x] | `develop @ def2b52`, 3 untracked |
| T-013-002 | Extraer e inventariar los documentos de `requerimientos/` | [x] | `docs/roadmap/source-inventory.md` |
| T-013-003 | Leer íntegramente los 2 DOCX de proceso operativo | [x] | `research.md` §Entidades ausentes |
| T-013-004 | Inventariar las 12 Specs y su convergencia | [x] | `spec-equivalence-map.md` |
| T-013-005 | Extraer inventario de rutas del router | [x] | `evidence/frontend-routes.txt` (78) |
| T-013-006 | Extraer inventario de endpoints del backend | [x] | `evidence/backend-endpoints.txt` (275) |
| T-013-007 | Extraer inventario de tablas y migraciones | [x] | 144 tablas · head `0014` |
| T-013-008 | Auditar el menú contra rutas y páginas | [x] | 72/72 · 78/78 · 0 huérfanas |
| T-013-009 | Ejecutar pytest y vitest | [x] | 223 ✓ / 210 ✓ |
| T-013-010 | Auditar máquinas de estado por dominio | [x] | `research.md` |
| T-013-011 | Contrastar proceso de importación/recepción contra el código | [x] | `processes-to-specs-map.md` |
| T-013-012 | Contrastar proceso de pedido/picking/facturación/despacho | [x] | `processes-to-specs-map.md` |
| T-013-013 | Auditar cobertura de auditoría por módulo | [x] | 7 de 9 instrumentados |
| T-013-014 | Auditar integraciones reales | [x] | `current-quality-baseline.md` |
| T-013-015 | Clasificar las 56 Specs | [x] | `56-specs-gap-analysis.md` |
| T-013-016 | Construir grafo de dependencias | [x] | `spec-dependency-graph.md` |
| T-013-017 | Construir roadmap por olas | [x] | `roadmap-by-waves.md` |
| T-013-018 | Construir backlog maestro | [x] | `master-backlog.md` |
| T-013-019 | Documentar falsas terminaciones | [x] | `false-completion-findings.md` |
| T-013-020 | Documentar deuda técnica y funcional | [x] | `technical-debt-roadmap.md`, `functional-debt-roadmap.md` |
| T-013-021 | Emitir informe maestro | [x] | `KONTROL_GAP_ANALYSIS_ROADMAP_MAESTRO.md` |
| T-013-022 | `/speckit.analyze` de consistencia | [x] | `analysis-report.md` |
| T-013-023 | **DETENERSE y solicitar autorización** | [x] | Sin implementación ejecutada |

## No ejecutadas por falta de ambiente (registradas como bloqueo)

| ID | Tarea | Bloqueo |
|---|---|---|
| T-013-B01 | `alembic upgrade head` / `alembic check` en PostgreSQL real | Sin instancia PG |
| T-013-B02 | Backup → restore verificado | Sin instancia PG ni Docker |
| T-013-B03 | Rendimiento con dataset representativo | Sin dataset ni entorno |
| T-013-B04 | Validación normativa fiscal | Requiere equipo legal/contable |
| T-013-B05 | Navegadores reales (Edge/Opera/Safari en dispositivo) | Fuera de sandbox |
