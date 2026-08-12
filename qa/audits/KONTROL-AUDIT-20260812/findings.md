# HALLAZGOS — Pasada 2 · Auditoría Integral E2E de KONTROL

> AUDIT_RUN_ID: `KONTROL-AUDIT-20260812` · Rama: `develop` @ 96c1f95 · Fecha: 2026-08-12
> Método: inspección de código + ejecución (pytest 207, vitest 193, E2E funcional in-process 20 pasos, crawler Playwright chromium 65 rutas) + validación de contratos.
> **No se modificó código productivo en esta pasada.**

Formato según Spec 012 §80 · Severidad según §79.

---

## KAUD-001 — Los módulos de negocio NO emiten eventos de auditoría (persistente KQA-102)

| Campo | Valor |
|---|---|
| Severidad | **CRITICAL** |
| Módulo | Todos (sales, purchasing, inventory, treasury, fiscal, regulatory, organization, master_data) |
| Requisito | FR-009-022 (P0, DOC-01 §4) — timeline de cambios/impresiones/exportaciones/accesos/incidentes |
| Spec | `specs/009-reportes-auditoria/spec.md` |
| Ruta/Pantalla | `/reportes/auditoria` · `ReportesAuditoriaPage` |
| API | `GET /reporting/audit/timeline`, `GET /audit/events` |
| Backend | `app/shared/audit.py` (`record_audit`) |
| Tabla | `audit_events` |

**Evidencia (reproducida esta pasada):**
- `grep -rn "record_audit" app --include=*.py` → único consumidor: `app/modules/identity_access/service.py:40`. Ningún servicio de negocio lo invoca.
- E2E funcional in-process (20 pasos: empresa→compra→CxP→pago→inventario→venta→CxC→cobro→devolución→NC→transferencia): al final solo **2** eventos en `audit_events` (identidad).
- `ReportesAuditoriaPage` muestra un timeline casi vacío para el flujo completo.

**Impacto:** la trazabilidad obligatoria (quién/qué/cuándo sobre operaciones de negocio) no existe. Imposible reconstruir la historia de emisiones, cobros, pagos, movimientos ni aprobaciones para auditoría interna/fiscal.

**Causa probable:** solo la fundación instrumentó `record_audit`; los módulos 002-011 no fueron instrumentados.

**Pruebas faltantes:** ninguna prueba verifica que una operación de negocio (emitir factura, aplicar cobro, mover inventario) cree un `AuditEvent`.

**Recomendación:** instrumentar `record_audit` en los servicios de negocio (emisión/anulación/reverso, transiciones, cobros/pagos, movimientos, retenciones, aprobaciones, exportaciones) + test por proceso.

---

## KAUD-002 — Exportación PDF/CSV: se registra metadata pero NO se genera ni almacena el archivo

| Campo | Valor |
|---|---|
| Severidad | **HIGH** |
| Módulo | Reportes (009) |
| Requisito | FR-009-020 (P0) — exportación auditada CSV/PDF con contenido |
| Spec | `specs/009-reportes-auditoria/spec.md` §6.3 |
| Ruta/Pantalla | `/reportes/exportaciones` · `ExportacionesPage`; `/reportes/centro` · `CentroReportesPage` (botón "Exportar CSV (auditado)") |
| API | `POST /reporting/exports` |
| Backend | `app/modules/reporting/service.py::create_export` |
| Tabla | `report_exports` |

**Evidencia (reproducida esta pasada):**
- `create_export`: para `fmt=="PDF"` solo construye `file_ref = "report-{key}-{ts}.pdf"` y guarda el registro `status="DONE"`. **No existe generación de PDF** (sin reportlab/weasyprint/fpdf en `requirements.txt`).
- Para CSV: `_to_csv(rows)` se ejecuta en memoria y **se descarta**; no se persiste contenido en `KONTROL_STORAGE_PATH`.
- **No existe endpoint de descarga** (ni `GET /reporting/exports/{id}/download`).
- `CentroReportesPage::exportCsv` notifica "Exportación auditada · Archivo …csv · DONE" — el usuario cree que exportó pero no puede obtener el archivo.

**Impacto:** funcionalidad que "aparenta existir" (UI + API + registro + DONE) sin efecto administrativo real: no hay documento. Incumple FR-009-020 e invariante de exportación auditada.

**Causa probable:** implementación de registro/metadata sin servicio de renderizado ni entrega.

**Recomendación:** renderizado real (CSV + PDF), almacenamiento en storage, endpoint de descarga autenticado, y evento de auditoría de la exportación. Test que verifique la descarga con contenido.

---

## KAUD-003 — ExportacionesPage: tabla "Jobs" simulada (mock vacío); no existe `GET /reporting/jobs`

| Campo | Valor |
|---|---|
| Severidad | **MEDIUM** |
| Módulo | Reportes (009) |
| Requisito | FR-009-023 (jobs asíncronos) |
| Ruta/Pantalla | `/reportes/exportaciones` · `ExportacionesPage` |
| Frontend | `ExportacionesPage.tsx` |
| Backend | `app/modules/reporting/api.py` |

**Evidencia:**
- `ExportacionesPage.tsx`: `queryFn: async () => ({ items: [] as ReportJobSummary[] })` — query de jobs **simulada** (mock), nunca llama al API.
- El backend **no expone** `GET /reporting/jobs` (lista); solo `GET /reporting/jobs/{job_id}`. El frontend "compensa" con un array estático → **viola la prohibición de datos simulados** (§13).
- Al pulsar "Ejecutar job" se notifica éxito, pero la tabla siempre queda vacía (la query simulada ignora la invalidación) → estado obsoleto persistente.

**Recomendación:** crear `GET /reporting/jobs` (lista por empresa) y consumirla; eliminar el mock.

---

## KAUD-004 — `PermissionGuard` es un stub que ignora permisos y no se usa

| Campo | Valor |
|---|---|
| Severidad | **MEDIUM** |
| Módulo | Seguridad / Fundación (001) |
| Requisito | FR-001-042, DOC-08 §15.2 |
| Frontend | `src/components/PermissionGuard.tsx` |
| Backend | `app/core/dependencies.py::require_permission` (autoridad real) |

**Evidencia:**
- `PermissionGuard` acepta `permission` y `hide` pero **no los usa**: siempre renderiza `children`.
- `grep -rln "PermissionGuard" src/modules` → **0 usos**.
- El backend sí aplica `require_permission` (403) y `allowed_actions` por registro se usa en varias pantallas.

**Impacto:** un rol no-ADMIN ve **todos los menús/pantallas** y solo recibe 403 al actuar. No es brecha de seguridad (el backend es la autoridad) pero es incompletitud funcional de permisos y mala UX.

**Recomendación:** implementar el guard (permisos del usuario) y aplicarlo a menú/rutas/acciones; o eliminar el stub.

---

## KAUD-005 — Nginx sin `Content-Security-Policy` ni `Strict-Transport-Security`

| Campo | Valor |
|---|---|
| Severidad | **MEDIUM** |
| Módulo | Infraestructura (NFR-001-001) |
| Archivo | `resources/nginx/nginx.conf` |

**Evidencia:** existen `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, `X-Frame-Options`; **faltan** `Content-Security-Policy` y `Strict-Transport-Security`.

**Recomendación:** CSP (`default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'`) y HSTS cuando TLS esté activo.

---

## KAUD-006 — Compose: default `latest` + watchtower auto-update

| Campo | Valor |
|---|---|
| Severidad | **MEDIUM** |
| Módulo | Infraestructura |
| Requisito | Principio 14 (no `latest` en producción) |
| Archivo | `compose.yaml` |

**Evidencia:** `KONTROL_IMAGE_TAG:-latest` por defecto y `watchtower` con `POLL_INTERVAL:-300` que recrea contenedores automáticamente. Despliegue sin fijar etiqueta → auto-actualización no verificada.

**Recomendación:** validar etiqueta fija en producción (rechazar `latest`), watchtower opt-in.

---

## KAUD-007 — 53 endpoints backend sin consumidor frontend (41 de negocio sin UI)

| Campo | Valor |
|---|---|
| Severidad | **LOW → MEDIUM** (según clasificación) |
| Evidencia | `evidence/backend-orphan-endpoints.json` (regenerado con extracción robusta: 279 llamadas crudas, 166 únicas) |

**Contexto:** de 294 rutas, 53 sin llamada frontend (extracción con parseo de genéricos `PagedResult<...>`):
- Sistema/infra (4): `/docs`, `/redoc`, `/openapi.json`, `/health/*`.
- Auth/licencia (8): `/auth/password-reset/request|confirm`, `/license/installation-request`, `/license/activate`, `/license/import`, `/licensing/sync-runs`, `/licensing/offline-status`, `/licensing/mode-transition`.
- **Negocio sin UI (41)**, p. ej.: `/purchasing/quotes` (solicitud de ofertas), `/inventory/reservations/*`, `/inventory/serials`, `/inventory/operations/receive|ship`, `/maestros/catalogos/atributos`, `/maestros/catalogos/unidades/*/conversiones`, `/purchasing/withholdings/*`, `/sales/withholdings-suffered/*`, `/fiscal/tax-return-batches`, `/fiscal/tax-profiles` (POST), `/reporting/jobs/{job_id}` (sin lista, ver KAUD-003), `/homologation/records/{id}`.

**Recomendación:** reclasificar cada uno (sistema / futuro / GAP). Los GAP de negocio sin UI (cotización de compras, reservas/seriales, atributos, retenciones sufridas, lotes de declaración) se consolidan en el plan de remediación.

---

## KAUD-008 — Tipos de datos (validación §23)

| Campo | Valor |
|---|---|
| Severidad | **LOW** |
| Evidencia | `evidence/database-schema-audit.json` (regenerado) |

- 144 tablas / 1.678 columnas. **0 FLOAT para dinero/tasas** (T-05 confirmado, `Numeric`). ✅
- 334 columnas `DATETIME` = **falso positivo de SQLite**; ORM usa `DateTime(timezone=True)` (48 usos; único "DateTime(" naive es docstring). Verificación final pendiente en PostgreSQL real.
- 1 `BIGINT`: `fiscal_number_series.next_number` (contador de correlativos) — adecuado.

---

## KAUD-009 — Bundle frontend 694 KB (174 KB gzip)

| Campo | Valor |
|---|---|
| Severidad | **LOW** |
| Evidencia | `vite build` (esta pasada) |

**Impacto:** carga inicial moderada; router con imports estáticos (sin `lazy`). Medir LCP/TTI con dataset real y considerar code-splitting.

---

## KAUD-010 — Test `e2e/route-crawl.spec.ts` frágil (race de login→sidebar)

| Campo | Valor |
|---|---|
| Severidad | **LOW** (calidad de test) |
| Archivo | `resources/frontend/e2e/route-crawl.spec.ts` |

**Evidencia:** falló con "debería haber rutas de menú para recorrer" (0 links) porque recolecta el nav inmediatamente tras el cambio de URL, sin esperar el render del Sidebar. El crawler de auditoría (con espera explícita) navega las rutas sin 404. El test debe esperar `nav a` visible antes de recolectar.

---

## KAUD-011 — Remediación de precisión monetaria INCOMPLETA: 54 columnas siguen en `Float`

| Campo | Valor |
|---|---|
| Severidad | **HIGH** |
| Módulo | Purchasing, Sales, Treasury, Fiscal, Master Data |
| Requisito | Principio 13 (integridad transaccional) · DOC-03 (precisión monetaria) · T-05 de la pasada 1 |
| Backend | `app/modules/purchasing/models.py`, `sales/models.py`, `treasury/models.py`, `fiscal/models.py`, `master_data/models.py` |
| Tablas | `ap_open_items`, `ap_payments`, `ap_advances`, `customers`, `withholding_rules`, `bank_transactions`, `cash_sessions`, `sales_credit_notes`, `supplier_credit_notes`, `sales_orders`, `triple_matches`, `purchase_order_lines`, `sales_order_lines`, `sales_quote_lines`, `supplier_quote_lines`, `tax_calculations` |

**Evidencia (reproducida esta pasada):** escaneo de `database-schema-audit.json` → **54 columnas `Float`** aún en el ORM. La remediación T-05 migró los montos nombrados `amount/price/total/base/rate/...` pero **no** cubrió estos nombres:

**Dinero crítico en Float (18):**
- `ap_open_items.original`, `ap_open_items.applied` — **saldos abiertos** (fuente de CxC/CxP aging y reconstrucción de saldos). Confirmado en `purchasing/models.py:233-234`.
- `ap_payments.applied`, `ap_advances.available` (anticipos).
- `withholding_rules.minimum`, `withholding_rules.subtractor` — **bases de retención (fiscal)**. Confirmado `fiscal/models.py:205-206`.
- `customers.credit_limit` — confirmado `master_data/models.py:96`.
- `bank_transactions.commission`, `cash_sessions.difference`, `sales_credit_notes.applied`, `supplier_credit_notes.applied`, `sales_orders.margin`, `tax_calculations.rounding`, `triple_matches.variance_tax`, y `discount` en líneas de PO/sales/quote.

**Cantidades en Float (36):** `quantity*` en líneas, `inventory_balances.qty_*`, `cost_layers.quantity_*`, `goods_receipt_lines.quantity_*`, `permit_instances.quantity`, `locations/transport_vehicles.capacity`, `unit_conversions.factor`, `presentations.content`, `stock_count_lines.*`, `reconciliation_lines.match_score`, `withholding_rules` (tasas).

**Impacto:** los saldos abiertos y bases fiscales en punto flotante pueden producir diferencias de centavos en aging, aplicaciones parciales, retenciones y conciliaciones. Es el riesgo de precisión que la pasada 1 declaró "resuelto" y **no lo está** (faltan `original/applied/available/minimum/subtractor/credit_limit/commission/difference/margin/rounding/discount`).

**Causa probable:** la selección de columnas de la migración `0012_numeric_money` usó un conjunto de nombres de columna limitado.

**Pruebas faltantes:** test que compare `Numeric` vs `Float` para una operación de saldo parcial repetida (debe existir un test de precisión por módulo).

**Recomendación:** segunda ola de migración Float→Numeric para las 18 columnas de dinero (y evaluar las 36 de cantidad según la política del modelo de datos). Incluir en el plan de remediación (Ola 0/1).

## KAUD-012 — Recuperación de contraseña sin UI (endpoints sin consumidor)

| Campo | Valor |
|---|---|
| Severidad | **MEDIUM** (RESUELTO — Ola 3) |
| Módulo | Seguridad / Identity |
| Requisito | Recuperación de contraseña (autoservicio) |
| API | `POST /auth/password-reset/request`, `POST /auth/password-reset/confirm` (existen) |
| Frontend | `LoginPage` (sin enlace "olvidé contraseña") |

**Evidencia del hallazgo:** `grep -rln "password-reset" src --include=*.tsx` → **0 resultados**. No había página ni enlace de recuperación; `LoginPage` no lo referenciaba. `CambiarContrasenaPage` solo cubre cambio con sesión.

**Impacto:** un usuario que olvida su contraseña no podía recuperarla por autoservicio (solo el administrador vía UI de usuarios, o SQL manual).

**Remediación (Ola 3):**
- `src/pages/ResetPasswordPage.tsx` — flujo en dos pasos (solicitud → confirmación con token; en modo fundación el token se muestra en pantalla).
- Ruta `/reset-password` en `src/app/router.tsx` y enlace "¿Olvidó su contraseña?" en `LoginPage`.
- `tests/test_password_reset.py` — ciclo completo (solicitud → token → confirmación → login con nueva credencial) y no-revelación de existencia (401 uniforme).

## KAUD-013 — `POST /auth/refresh` devuelve 500 (comparación de datetimes naive/aware) — renovación de sesión rota

| Campo | Valor |
|---|---|
| Severidad | **HIGH** (CRITICAL en ambiente SQLite/dev) |
| Módulo | Identity / Autenticación |
| Requisito | Renovación de sesión (FR-001) · §56 (0 errores 500 en flujos normales) |
| API | `POST /api/v1/auth/refresh` |
| Backend | `app/modules/identity_access/service.py::rotate_session` (línea 165) |
| Tabla | `auth_sessions` |

**Evidencia (reproducida esta pasada, 2 vías):**
1. **Crawler chromium (65 rutas):** cada navegación dispara `POST /api/v1/auth/refresh` → **500** (65/65 requests fallidos). La UI sigue operando porque el frontend tolera el fallo y reutiliza el access token, pero **ningún refresh tiene éxito**.
2. **Reproducción directa (TestClient in-process):** login 200 (cookie de refresh presente) → `POST /auth/refresh` → **500** con:
   `TypeError: can't compare offset-naive and offset-aware datetimes` en `rotate_session` (`if session.expires_at < _now():`).

**Causa:** `session.expires_at` se lee naive desde la BD (SQLite; y es frágil en cualquier driver que no devuelva aware), mientras `_now()` devuelve aware UTC. La comparación lanza `TypeError` sin manejo → 500.

**Impacto:**
- El **flujo de renovación de sesión está roto**: cuando el access token expire, el refresh no puede renovar → pérdida de sesión / re-login forzado.
- **Todo el entorno QA/dev (SQLite) genera un 500 por cada navegación** — los logs se llenan de errores y ningún test detectó el fallo (el refresh no está cubierto por pruebas).
- En PostgreSQL con `DateTime(timezone=True)` puede quedar enmascarado, pero el defecto es real y sin test de regresión.

**Pruebas faltantes:** ningún test ejecuta login → refresh → expect 200 (rotación + nueva cookie + nuevo access token).

**Recomendación:** normalizar datetimes en la comparación (`session.expires_at.replace(tzinfo=UTC)` si naive, o helper `_as_utc`), añadir test de rotación de sesión (login → refresh 200 → refresh con token anterior → 401 SESSION_INVALID), y cubrir el refresh en `test_security_integration`.

## Positivos verificados (evidencia de integración real)

- Menú→Ruta→Página: 66 menús con ruta; 72 rutas con página (`menu-route-audit.json`, `route-audit.json`).
- Frontend→API: 234 llamadas → **0 sin endpoint** (`frontend-api-matrix.md`).
- E2E de proceso funcional: 19/20 PASS (compra→CxP→saldo 0; venta→CxC→saldo 0; inventario reconciliado; devolución; NC; transferencia).
- Seguridad: 401/403/RBAC, aislamiento multi-tenant, IDOR→404, SQLi/XSS (`test_security_integration.py` 8 PASS).
- Licencia: enforcement READ_ONLY (423) probado.
- Dinero: `Numeric` (T-05) + coerción `float()` en aritmética (bug decimal/float corregido).
- Migraciones: single head `0013`, cadena offline PostgreSQL OK.
- Suites: pytest 207 · vitest 193 · tsc · eslint · ruff · mypy — verdes.

---

# REMEDIACIÓN APLICADA (autorizada) — Re-auditoría 2026-08-12

Estado tras implementar el plan (`remediation-plan.md`): **pytest 221 · vitest 194 ·
tsc/eslint/ruff/mypy OK · E2E in-process 20/20 · crawler 65/65 PASS · axe 13/13 ·
responsive 162/162 · cross-browser chromium/firefox 65/65 + webkit 2/2 · idempotencia 6/6 · perf 12/12.**

| Hallazgo | Tarea | Estado post-remediación |
|---|---|---|
| KAUD-001 (CRITICAL) auditoría de negocio | T-204 instrumentar `record_audit` en sales/purchasing/inventory/fiscal/treasury/regulatory/reporting | **RESUELTO** — E2E "auditoría registra eventos" PASS; `tests/test_audit_integration.py` (2) |
| KAUD-002 (HIGH) exportación sin archivo | T-203 CSV/PDF reales (ReportLab) + `GET /reporting/exports/{id}/download` + auditoría | **RESUELTO** — `tests/test_reporting.py` (PDF `%PDF`, CSV, tenant isolation) |
| KAUD-003 (MEDIUM) jobs mock / sin lista | T-206 `GET /reporting/jobs` + frontend consume; sin mock | **RESUELTO** — `test_jobs_list` |
| KAUD-004 (MEDIUM) PermissionGuard stub | T-207 `GET /auth/me` + guard real + filtro de menú por permiso | **RESUELTO** — typecheck/lint/vitest OK |
| KAUD-005 (MEDIUM) nginx sin CSP/HSTS | T-209 CSP + HSTS en `nginx.conf` | **RESUELTO** |
| KAUD-006 (MEDIUM) compose latest + watchtower | T-210 entrypoint rechaza `latest` en prod; watchtower opt-in (profiles) | **RESUELTO** |
| KAUD-007 (LOW) 41 orphans | T-211 reclasificados en `orphan-endpoints-classification.md` (GAPs → Ola 2) | **DOCUMENTADO** |
| KAUD-010 (LOW) race route-crawl test | T-208 espera `nav a` visible | **RESUELTO** |
| KAUD-011 (HIGH) precisión monetaria incompleta | T-201 migración `0014_numeric_money_2` (18 cols dinero → Numeric) | **RESUELTO** — 0 columnas de dinero en Float |
| KAUD-012 (MEDIUM) reset sin UI | T-223 página `ResetPasswordPage` + ruta + enlace + `tests/test_password_reset.py` | **RESUELTO** — flujo completo 2/2 |
| KAUD-013 (HIGH) refresh 500 | T-222 `_as_utc` (naive/aware) + tests de rotación | **RESUELTO** — repro `refresh: 200`; 0× 500 en crawler |
| KAUD-205 (MEDIUM) dashboard auditoría | T-205 filtros entity_type/action en `ReportesAuditoriaPage` | **RESUELTO** |

**Olas 2-4 ejecutadas (2026-08-12):**
- **T-216 Accesibilidad (axe-core / WCAG 2.2 AA):** 13/13 PASS (login + 12 páginas autenticadas) — `e2e/accessibility.spec.ts`.
- **T-217 Responsive:** 162/162 PASS · 0 scroll horizontal (27 rutas × 6 viewports 320×568…1920×1080) — `resources/frontend/qa/audits/KONTROL-AUDIT-20260812-RESPONSIVE/` (`audit-responsive-crawler.mjs`).
- **T-218 Cross-browser:** chromium 65/65 · firefox 65/65 (route-crawl) · webkit 2/2 (smoke) — `playwright.config.ts` (proyecto webkit añadido).
- **T-214 Idempotencia/concurrencia:** `tests/test_idempotency_concurrency.py` 6/6 (pagos, facturas, inventario, doble transición 409, doble aplicación, emisión fiscal).
- **T-220 Rendimiento (smoke):** 12/12 rutas OK · P95 máx 8 ms (umbral 500 ms) — `qa/perf-smoke.py` + `perf-smoke-results.json`.
- **KAUD-012 (T-223):** resuelto (ver arriba).

**Pendientes de ambiente autorizado (fuera del sandbox):** PostgreSQL real (alembic check/
backup-restore/drift), validación normativa fiscal/regulatoria (SENIAT), browsers Edge/Opera,
rendimiento P50/P95/P99 sobre dataset representativo, y los GAPs de negocio sin UI (Ola 2, T-211).
