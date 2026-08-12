# T-221 · Reporte de Cobertura — Auditoría Integral E2E (Spec 012)

> AUDIT_RUN_ID: `KONTROL-AUDIT-20260812` · Fecha: 2026-08-12 · Rama: `develop`
> Alcance: cobertura por **módulo / proceso / requisito** (unit · integration · contract · E2E)
> conforme al criterio T-221 del plan de remediación. No incluye líneas de
> cobertura numérica (la herramienta `coverage`/`pytest-cov` no está instalada en
> el sandbox sin red); se documenta la cobertura **funcional** por archivo de prueba.

## 1. Resumen ejecutivo

| Capa | Cantidad | Estado |
|---|---|---|
| Backend unit/integration (pytest) | **223** tests · 21 archivos | ✅ |
| Frontend unit/contract (vitest) | **210** tests · 7 archivos | ✅ |
| E2E Playwright (chromium/firefox/webkit) | route-crawl 65/65 · smoke 2/2 · axe 13/13 · responsive 162/162 | ✅ |
| API in-process E2E (`functional-e2e-inprocess.py`) | 20/20 | ✅ |
| Lint/type | ruff · mypy · tsc · eslint | ✅ |

## 2. Cobertura por módulo backend

| Módulo | Test(s) | Unit | Integration | Contract |
|---|---|---|---|---|
| identity_access (auth/usuarios/roles/sesiones/reset) | `test_security.py`, `test_security_integration.py`, `test_password_reset.py`, `test_process_flows.py` | ✅ | ✅ | ✅ |
| organization | `test_process_flows.py`, `test_security_integration.py` | ✅ | ✅ | — |
| setup (instalación) | `conftest.py`, `test_process_flows.py`, `test_services.py` | ✅ | ✅ | — |
| master_data (terceros/catálogos/perfiles) | `test_maestros.py` | ✅ | ✅ | — |
| inventory (movs/seriales/reservas/lotes/valorización) | `test_inventory.py`, `test_qa_fixes.py`, `test_idempotency_concurrency.py` | ✅ | ✅ | — |
| purchasing (compras/CxP/retenciones) | `test_purchasing.py`, `test_qa_fixes.py`, `test_idempotency_concurrency.py` | ✅ | ✅ | — |
| sales (ventas/CxC) | `test_sales.py`, `test_qa_fixes.py`, `test_idempotency_concurrency.py` | ✅ | ✅ | — |
| treasury (caja/conciliación/IGTF) | `test_treasury.py` | ✅ | ✅ | — |
| fiscal (emisión/lotres/retenciones/declaraciones) | `test_fiscal.py`, `test_idempotency_concurrency.py` | ✅ | ✅ | — |
| regulatory (permisos/vehículos/aprobaciones) | `test_regulatory.py` | ✅ | ✅ | — |
| reporting (reportes/exportaciones/jobs) | `test_reporting.py`, `test_audit_integration.py` | ✅ | ✅ | — |
| audit (timeline/eventos) | `test_audit_integration.py` | ✅ | ✅ | — |
| licensing / licenciamiento | `test_license.py`, `test_licensing_central.py` | ✅ | ✅ | — |
| homologation | `test_homologation.py` | ✅ | ✅ | — |
| migraciones (Alembic offline) | `test_migrations_offline.py` | ✅ | — | ✅ |
| seguridad transversal (RBAC/tenant/IDOR/SQLi/XSS) | `test_security_integration.py` | ✅ | ✅ | — |
| idempotencia/concurrencia | `test_idempotency_concurrency.py` | ✅ | ✅ | — |

## 3. Cobertura por proceso (E2E)

| Proceso | Evidencia |
|---|---|
| Cadena de organización (empresa→sucursal→almacén→ubicación) | `test_process_flows.py` · E2E in-process 20/20 |
| Ventas: cotización→orden→factura→NC/ND→cobro | `test_sales.py`, `test_process_flows.py`, `qa/functional-e2e-inprocess.py` |
| Compras: requisición→orden→recepción→factura→NC→pago | `test_purchasing.py`, `test_process_flows.py` |
| Inventario: transferencias/conteos/ajustes/lotes/valorización | `test_inventory.py`, `test_qa_fixes.py` |
| Tesorería: caja/ingresos-egresos/conciliación/IGTF | `test_treasury.py` |
| Fiscal: emisión con correlativo/control/hash · lotes de declaración | `test_fiscal.py`, `test_idempotency_concurrency.py` |
| Regulatorio: permisos/vehículos/aprobaciones/traslados | `test_regulatory.py` |
| Seguridad: login/lockout/refresh/rotación/reset | `test_security.py`, `test_security_integration.py`, `test_password_reset.py` |
| Licenciamiento: importación/estados/entitlements | `test_license.py`, `test_licensing_central.py` |
| Exportación: CSV/PDF + descarga + aislamiento tenant | `test_reporting.py` |
| Auditoría: eventos por operación de negocio | `test_audit_integration.py` |
| Homologación: actos/versiones/timeline | `test_homologation.py` |

## 4. Cobertura por requisito (specs)

| Spec | Dominio | Cobertura |
|---|---|---|
| 001-fundacion | Fundación (auth, org, setup, seguridad) | ✅ unit/integration/E2E |
| 002-maestros | Maestros (terceros, catálogos, perfiles) | ✅ unit/integration |
| 003-inventario-logistica | Inventario y logística | ✅ unit/integration/E2E |
| 004-compras-cuentas-por-pagar | Compras y CxP | ✅ unit/integration/E2E |
| 005-ventas-cuentas-por-cobrar | Ventas y CxC | ✅ unit/integration/E2E |
| 006-tesoreria | Tesorería | ✅ unit/integration |
| 007-nucleo-fiscal | Núcleo fiscal | ✅ unit/integration |
| 008-regulacion-traslados | Regulación y traslados | ✅ unit/integration |
| 009-reportes-auditoria | Reportes y auditoría | ✅ unit/integration/E2E |
| 010-licenciamiento-central | Licenciamiento | ✅ unit/integration |
| 011-homologacion-liberacion | Homologación y liberación | ✅ unit/integration |
| 012-auditoria-integral-e2e | Auditoría integral | ✅ puertas G1-G4 + crawler + axe + responsive + cross-browser |

## 5. Cobertura frontend

| Tipo | Archivo | Resultado |
|---|---|---|
| Contract (G1-G4: menú→ruta→página→endpoint) | `src/tests/audit-completeness.test.ts` | ✅ 210 vitest |
| E2E route-crawl (sin 404/errores/H1) | `e2e/route-crawl.spec.ts` (chromium/firefox) | ✅ 65/65 |
| Smoke multi-browser | `e2e/smoke.spec.ts` (chromium/firefox/webkit) | ✅ 2/2 |
| Accesibilidad (axe-core WCAG 2.2 AA) | `e2e/accessibility.spec.ts` | ✅ 13/13 |
| Responsive (27 rutas × 6 viewports) | `e2e/audit-responsive-crawler.mjs` | ✅ 162/162 |

## 6. Limitaciones documentadas (ambiente autorizado)

- **Línea de cobertura numérica** (`pytest-cov`): no disponible sin red en el sandbox; se recomienda
  ejecutar `pytest --cov=app --cov-report=html` en CI con red para fijar un umbral (p. ej. ≥ 70 %).
- **PostgreSQL real**: migraciones validadas offline (dialecto PG) — falta `alembic upgrade/check` en PG.
- **SENIAT / normativa fiscal**: pendiente de homologación externa.
- **Edge/Opera**: chromium/firefox/webkit cubiertos; Edge/Opera pendientes de ambiente.
