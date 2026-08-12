# PLAN DE REMEDIACIÓN — Pasada 2 · Auditoría Integral E2E de KONTROL

> AUDIT_RUN_ID: `KONTROL-AUDIT-20260812` · Fecha: 2026-08-12 · Rama: `develop` @ 96c1f95
> Regla: NO implementar sin autorización expresa. Cada hallazgo → tarea atómica.
> Autorización requerida: "Autorizo implementar el plan de remediación de la auditoría integral de KONTROL."

## Ola 0 — BLOCKERS
*(no se detectaron BLOCKER en esta pasada — ver criterio §92)*

## Ola 1 — Integridad estructural y precisión

| ID | Hallazgo | Tarea atómica | Severidad | Verificación |
|---|---|---|---|---|
| T-201 | KAUD-011 | Migrar Float→Numeric las **18 columnas de dinero** restantes (`ap_open_items.original/applied`, `ap_payments.applied`, `ap_advances.available`, `customers.credit_limit`, `withholding_rules.minimum/subtractor`, `bank_transactions.commission`, `cash_sessions.difference`, `sales_credit_notes.applied`, `supplier_credit_notes.applied`, `sales_orders.margin`, `tax_calculations.rounding`, `triple_matches.variance_tax`, `*_lines.discount`) + migración alembic `0014_numeric_money_2` | HIGH | migración offline PG + test de precisión (saldo parcial repetido) |
| T-202 | KAUD-011 | Evaluar/politizar las 36 columnas de cantidad (`quantity*`, `qty_*`, `capacity`, `factor`, etc.): `Numeric` vs `Float` según modelo de datos; documentar decisión (ADR) | MEDIUM | ADR + migración si aplica |
| T-203 | KAUD-002 | Implementar exportación real: renderizado CSV + PDF (biblioteca aprobada), persistir en `KONTROL_STORAGE_PATH`, **endpoint de descarga** autenticado, evento de auditoría | HIGH | test: crear exportación → descargar archivo con contenido esperado |

## Ola 1 — Auditoría y jobs

| ID | Hallazgo | Tarea atómica | Severidad | Verificación |
|---|---|---|---|---|
| T-204 | KAUD-001 | Instrumentar `record_audit` en servicios de negocio: emisión/anulación/reverso de documentos, transiciones de estado (orders/invoices/payments/collections/movements/permits/approvals), retenciones, exportaciones | CRITICAL | test por proceso: operación → `AuditEvent` creado |
| T-205 | KAUD-001 | Dashboard de auditoría con filtros (entity/action/user/fecha) y exportación del timeline | MEDIUM | E2E UI |
| T-206 | KAUD-003 | Crear `GET /reporting/jobs` (lista por empresa) y consumirla en `ExportacionesPage`; eliminar el mock `{items: []}` | MEDIUM | vitest G3/G4 + test de lista |

## Ola 1 — Permisos y frontend

| ID | Hallazgo | Tarea atómica | Severidad | Verificación |
|---|---|---|---|---|
| T-207 | KAUD-004 | Implementar `PermissionGuard` real (permisos del usuario vía `/auth/me`) y aplicarlo a menú/rutas/acciones; o eliminar el stub | MEDIUM | test: usuario sin permiso no ve acción |
| T-208 | KAUD-010 | Arreglar `e2e/route-crawl.spec.ts`: esperar `nav a` visible antes de recolectar enlaces | LOW | crawl verde en CI |

## Ola 1 — Seguridad e infraestructura

| ID | Hallazgo | Tarea atómica | Severidad | Verificación |
|---|---|---|---|---|
| T-209 | KAUD-005 | Añadir `Content-Security-Policy` y `Strict-Transport-Security` en `nginx.conf` | MEDIUM | curl headers + smoke |
| T-210 | KAUD-006 | Compose: rechazar `latest` en producción (validación de etiqueta) y watchtower opt-in | MEDIUM | compose config |
| T-211 | KAUD-007 | Reclasificar los 41 endpoints de negocio sin UI (sistema/futuro/GAP) y convertir GAPs aprobados en tareas | MEDIUM | clasificación en `orphan-endpoints-classification.md` |
| T-222 | KAUD-013 | Arreglar `rotate_session`: normalizar datetimes (helper `_as_utc` / `replace(tzinfo=UTC)` si naive) y añadir test login→refresh→200 + rotación (token anterior → 401 SESSION_INVALID) | HIGH | pytest nuevo + crawler sin 500 en refresh |

## Ola 2 — Procesos (validaciones pendientes de ambiente autorizado)

| ID | Tarea | Verificación |
|---|---|---|
| T-212 | E2E fiscal: emisión con correlativo + número de control + hash; NC/ND con límites; retenciones | `fiscal-audit-checklist.md` |
| T-213 | E2E regulatorio: SICA/SIGESAI/SACS (perfiles, traslados, bloqueo/liberación) | checklist regulatorio |
| T-214 | Concurrencia/idempotencia: doble click, doble request, dos usuarios, retry en emisión/pago/cobro/recepción | tests dedicados |
| T-215 | Backup/Restore real en PostgreSQL aislado + `alembic upgrade head` + `alembic check` | entorno aislado |

## Ola 3 — UX / Navegadores / Accesibilidad

| ID | Tarea | Verificación |
|---|---|---|
| T-216 | Ejecutar axe-core (WCAG 2.2 AA) sobre todas las pantallas (`e2e/accessibility.spec.ts`) | axe 0 violaciones críticas |
| T-217 | Responsive 320-1920px + zoom 125/150/200% sin scroll horizontal | suite Playwright viewports |
| T-218 | Cross-browser: Chrome (hecho), Firefox/WebKit (simulados disponibles), Edge/Opera reales si disponibles | clasificar REAL/SIMULATED |

## Ola 4 — Calidad / Rendimiento

| ID | Tarea | Verificación |
|---|---|---|
| T-219 | Code-splitting por ruta (router `lazy`) y medición LCP/TTI con dataset real | bundle < 500 KB objetivo |
| T-220 | Rendimiento backend P50/P95/P99, N+1, índices sobre dataset representativo | reporte |
| T-221 | Cobertura por módulo/proceso/requisito (unit/integration/contract/e2e) | reporte de cobertura |

## Criterio de cierre
- Ola 0: 0 BLOCKER.
- Ola 1: KAUD-001..011 cerrados con prueba (0 CRITICAL, 0 HIGH).
- Olas 2-4: checklists ejecutados en ambiente autorizado.
- Re-auditoría completa posterior a implementación (`/speckit.converge`).
