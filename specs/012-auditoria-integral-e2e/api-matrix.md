# Spec 012 — Matriz de API (api-matrix.md)

Fuentes: `evidence/backend-endpoints.json` (285), `evidence/frontend-api-calls.json` (135), `evidence/api-coverage.json`, `evidence/backend-orphan-endpoints.json`.

## Dirección 1: Frontend → Backend (consumo real)
| Verificación | Resultado |
|---|---|
| Llamadas apiFetch del frontend | 135 |
| Resuelven a endpoint backend | **135 (100 %)** |
| Sin endpoint (rotas) | 0 |

## Dirección 2: Backend → Frontend (exposición)
| Verificación | Resultado |
|---|---|
| Endpoints backend (método+path) | 285 |
| Con consumidor frontend | 168 |
| **Sin consumidor frontend (huérfanos)** | **117** |

## Endpoints huérfanos relevantes (candidatos a interfaz faltante)
| Método | Ruta | Dominio | Nota |
|---|---|---|---|
| GET/POST | `/users` | Seguridad | Sin UI (F-01) |
| GET/POST | `/organization/establishments` | Org | Sin UI (F-05) |
| GET/POST | `/organization/locations` | Org | Sin UI |
| GET | `/inventory/balances` · `/movements` | Inventario | Sin UI de movimientos/balances |
| POST | `/inventory/movements/reverse` | Inventario | Sin UI |
| GET/POST | `/maestros/perfiles` | Fiscal | Sin UI de perfiles |
| GET/DELETE | `/auth/sessions` | Seguridad | Sin UI |
| POST | `/auth/password-reset/request`·`confirm` | Seguridad | Sin UI |

Clasificar cada uno como `DOCUMENTED_FUTURE_SCOPE` o brecha (T-07).
