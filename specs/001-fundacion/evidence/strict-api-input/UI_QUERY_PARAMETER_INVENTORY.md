# UI_QUERY_PARAMETER_INVENTORY — línea base en 49540a6 (2026-10-28)

## Método

Claude cruzó cada construcción de consulta del frontend con los parámetros declarados de la ruta, sacados de `create_app()` y `get_flat_dependant`. Las construcciones son de cuatro formas:
- plantilla `` `/ruta?x=${…}` ``;
- concatenación con `+`;
- `new URLSearchParams({...})`, `.set()` y `.append()`;
- la ruta dinámica `searchUrl` de `AsyncCombobox`.

Se recorrieron las mismas búsquedas en `e2e/` y en `qa/`. Hay 84 sitios de producto. La mayoría solo envía parámetros declarados (`q`, `status`, `page`, `page_size`, `warehouse_id`, `period`, `limit`, `offset`…).

## Parámetros no declarados que envía el producto

| UI_SURFACE | API_ROUTE | PARAMETER | DECLARED_IN_OPENAPI | PURPOSE | CURRENT_EFFECT | Clase (§36) | ACTION |
|---|---|---|---|---|---|---|---|
| Inventario › Existencias (`ExistenciasPage.tsx`) | `GET /inventory/balances` | `q` | **No** | Caja «Buscar por producto…» | Ignorado: la caja no filtra (UI-BUSQUEDA-MUERTA) | **INTENDED_FILTER** | Declarar `q` e implementarlo en el servidor (PDD-API-11) |
| Organización › Sucursales | `GET /organization/branches` | `company_id` | No | Empresa activa | Ignorado: decide `X-Kontrol-Company` | STALE_CLIENT_PARAMETER | Dejar de enviarlo |
| Organización › Almacenes | `GET /organization/branches` | `company_id` | No | ídem | ídem | STALE_CLIENT_PARAMETER | Dejar de enviarlo |
| Organización › Establecimientos | `GET /organization/branches` | `company_id` | No | ídem | ídem | STALE_CLIENT_PARAMETER | Dejar de enviarlo |
| Aprobaciones › Bandeja | `GET /approvals/inbox` | `company_id` | No | ídem | ídem | STALE_CLIENT_PARAMETER | Dejar de enviarlo |
| Aprobaciones › Políticas | `GET /approvals/policies` | `company_id` | No | ídem | ídem | STALE_CLIENT_PARAMETER | Dejar de enviarlo |
| Aprobaciones › Delegaciones | `GET /approvals/delegations` | `company_id` | No | ídem | ídem | STALE_CLIENT_PARAMETER | Dejar de enviarlo |
| Historial de aprobaciones (componente de documento) | `GET /approvals/requests/by-document` | `company_id` | No | ídem | ídem | STALE_CLIENT_PARAMETER | Dejar de enviarlo |

**UI_UNDECLARED_PARAMS_SENT_BEFORE = 8**: 7 sitios con `company_id` y 1 con `q`. Ninguno es DEPRECATED_CONTRACT: ningún contrato publicó esos parámetros. Los siete `company_id` son API-COMPANY-ID-EN-CONSULTA. La empresa ya llega por la cabecera validada, así que dejar de enviarlos no cambia el resultado.

### Ya declarados (no cambian)

- `/organization/warehouses?company_id=` **sí** lo declara: filtro propio del endpoint.
- `/organization/companies?q=` lo declara: Empresas, ciclo anterior.
- `/audit/events` declara los 11 parámetros que envía `api/audit.ts` (ciclo 04).
- `AsyncCombobox` envía `q`, `page_size` e `item_type` a un `searchUrl` que recibe por propiedad. La guarda de frontend (AD-7) lo comprueba en cada uso literal.

## Clientes del repositorio que no son producto

| Cliente | Llamada | Parámetro | Acción |
|---|---|---|---|
| `e2e/approvals.spec.ts` | `/approvals/requests/by-document`, `/approvals/policies`, `/approvals/inbox` | `company_id` | Quitarlo |
| `e2e/approvals.spec.ts` | `/audit/events` | `limit` (E2E-APPROVALS-LIMIT-NO-DECLARADO) | Usar `page_size`, que sí está declarado |
| `e2e/sales-orders.spec.ts`, `e2e/incidents.spec.ts`, `e2e/receipts.spec.ts` | `/organization/branches` | `company_id` | Quitarlo |
| `qa/functional-e2e-inprocess.py`, `qa/functional-e2e-local.py` | `/organization/branches` | `company_id` | Quitarlo |
| Pruebas del backend | Se miden con la suite completa tras el cambio | — | Corregir la petición, nunca la regla (§56) |

No hay integraciones externas documentadas que dependan de parámetros no declarados. El contrato público (`api-contracts.md`) solo publica los declarados.
