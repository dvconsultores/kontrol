# RESULTADOS DE PROCESOS, NAVEGADOR, RESPONSIVE, API, DB, SEGURIDAD Y FISCAL — RUN `KONTROL-QA-20260810-234937`

## process-results.md
| Proceso | Inicio | Fin esperado | Estado | Bloqueo | Evidencia |
|---|---|---|---|---|---|
| Configuración GLOBAL DV | Login | Empresa activa | BLOCKED | KQA-001 | — |
| Sucursales / Almacenes | — | — | BLOCKED | KQA-001 | — |
| Proveedor/Cliente/Producto | — | — | BLOCKED | KQA-001 | — |
| Compra completa / Recepción / Conciliación / CxP / Pago | — | — | BLOCKED | KQA-001 | — |
| Compra sin PO | — | — | BLOCKED | KQA-001 | — |
| Inventario / Transferencia | — | — | BLOCKED | KQA-001 | — |
| Cotización / Venta / Venta directa / Despacho / Facturación / CxC / Cobro / Devolución / NC / ND | — | — | BLOCKED | KQA-001 | — |
| Reportes / Auditoría | — | — | BLOCKED | KQA-001 | — |

**Procesos COMPLETE=TRUE: 0.** Todos dependen del login (KQA-001).

## browser-results.md
| Navegador | Resultado |
|---|---|
| Google Chrome / Chromium (real, integrado) | REAL_BROWSER_PASS (login renderiza; título y botón OK) |
| Microsoft Edge | NOT_EXECUTED (canal real no disponible en sandbox) |
| Mozilla Firefox | NOT_EXECUTED (binario Playwright no accesible en sandbox) |
| Opera | NOT_EXECUTED |
| Safari/WebKit | NOT_EXECUTED (WebKit es SIMULADO si se lanza; no se lanzó) |
| Chrome Android | NOT_EXECUTED |
| Safari iPhone/iPad | NOT_EXECUTED |
| Samsung Internet | NOT_EXECUTED |

Nota: en el sandbox los binarios de Playwright (firefox/webkit) no son accesibles, por lo que NO se presenta WebKit como "Safari real". Se requiere entorno con canales reales o BrowserStack/Sauce/LambdaTest.

## responsive-results.md
Login público, Chromium real, sin scroll horizontal:
| Viewport | Scroll horizontal |
|---|---|
| 320×568 | No |
| 375×667 | No |
| 768×1024 | No |
| 1366×900 | No |
| 1920×1080 | No |

Resto del sistema (dashboard, menús, tablas) **BLOCKED** por KQA-001.

## api-results.md
| Endpoint | Método | Resultado |
|---|---|---|
| /api/v1/setup/status | GET | **502** (KQA-001) |
| /api/v1/license/status | GET | **502** |
| /api/v1/auth/refresh | GET | **502** |
| /api/v1/auth/login | POST | **502** |
| /api/v1/organization/companies | GET | **502** |
| /health/live | GET | 200 pero HTML SPA (KQA-002) |
| /health/ready | GET | 200 pero HTML SPA (KQA-002) |

Sin datos sensibles en logs. Request IDs no disponibles (respuestas de nginx).

## db-results.md
`DB_DIRECT_VALIDATION_NOT_AVAILABLE` — no se dispone de acceso autorizado a PostgreSQL en esta sesión. La validación UI/API/DB queda bloqueada por KQA-001.

## security-results.md
- Ruta sin sesión: el SPA redirige a /login (comportamiento esperado).
- Ruta con sesión/permisos/IDOR: **NOT_EXECUTED** (requiere backend).
- KQA-001 impide validar seguridad funcional contra la instancia. La suite de seguridad automatizada del repo (pytest 204) sigue siendo la validación de referencia en ambiente controlado.

## fiscal-results.md
- `BLOCKED_FISCAL_PRODUCTION_SAFETY` por defecto: no se emitió ningún documento fiscal.
- La prueba quedó bloqueada antes del login (KQA-001); no se consumió ningún correlativo/número de control.
- Configuración fiscal de GLOBAL DV: no verificable (API 502).
- No se asumió ninguna clasificación tributaria; nada se marcó LEGAL_FISCAL_VALIDATION_REQUIRED porque no se llegó a configurar fiscal.

## reconciliaciones
- inventory-reconciliation.md / ar-reconciliation.md / ap-reconciliation.md: **N/A** (no se crearon documentos).
