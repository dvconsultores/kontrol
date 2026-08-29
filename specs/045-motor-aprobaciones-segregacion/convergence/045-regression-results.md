# REGRESIÓN — SPEC 045 (§33, §34)

## Componentes compartidos modificados

La Spec 045 tocó cinco elementos globales. Cada uno exige regresión propia.

### `ConfirmationDialog` — slot `children` añadido

| Comprobación | Resultado |
|---|---|
| Usos existentes sin `children` | ✔ el slot es opcional; render idéntico |
| Acciones destructivas (`danger`) | ✔ sin cambio |
| Foco inicial en el botón de confirmar | ✔ sin cambio |
| Cierre con `Escape` y clic fuera | ✔ sin cambio |
| Responsive | ✔ 6 viewports |
| Sigue siendo confirmación breve | ✔ la configuración va en pantalla completa (ADR-015) |

### `apiFetch` — `ifMatch` añadido

| Comprobación | Resultado |
|---|---|
| Peticiones existentes sin `ifMatch` | ✔ la cabecera no se envía; 276 pruebas y 22 páginas verdes |
| Cabeceras, auth, JSON, errores | ✔ sin cambio |
| Refresh de sesión | ✔ sin cambio |
| `If-Match` válido | ✔ 200 |
| `If-Match` obsoleto | ✔ 409 `APPROVAL_STEP_VERSION_CONFLICT` |

### `DataTable` — cabecera a `text-600`

Solo color. `DataTable.test.tsx` (4 casos) verde; 22 páginas con axe verde en tres motores.

### `Sidebar` y `Topbar` — contraste

Solo color. Menú, colapso, permisos y navegación sin cambio; `audit-completeness`
(puertas G1-G4) verde.

## Dominios integrados (§34)

| Dominio | Suite | SQLite | PostgreSQL |
|---|---|---|---|
| Purchasing | `test_purchasing.py` | ✔ | ✔ |
| Inventory | `test_inventory.py` | ✔ | ✔ |
| Sales | `test_sales.py` | ✔ | ✔ |
| Regulatory | `test_regulatory.py` | ✔ | ✔ |
| Procesos E2E in-process | `test_process_flows.py` | ✔ | ✔ |
| Idempotencia y concurrencia | `test_idempotency_concurrency.py` | ✔ | ✔ |
| Auditoría | `test_audit_integration.py` | ✔ | ✔ |

**Sin cambio de expectativa en ninguna prueba existente** (AC-20): sin política
activa, los dominios se comportan exactamente igual que antes de 045.

## Calidad estática (§35)

| Comprobación | Resultado |
|---|---|
| `pytest` sobre PostgreSQL | **276 passed** |
| `pytest` sobre SQLite | **276 passed** |
| `ruff` (app, tests, alembic) | ✔ |
| `mypy` (75 archivos) | ✔ |
| `tsc` | ✔ |
| `eslint --max-warnings 0` | ✔ |
| `vitest` | **217 passed** (7 archivos) |
| `vite build` | ✔ 377,33 KB · gzip 115,26 KB |

## Verificación de no-duplicación (P22)

`test_no_domain_keeps_its_own_approval_logic` cubre **los cuatro dominios** y
además comprueba que ningún módulo declare modelo de política propio. No se
excluye ningún módulo para hacerla pasar.
