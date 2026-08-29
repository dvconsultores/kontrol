# EVIDENCIA — SPEC 045

Ejecutada el 2026-08-29 sobre `develop`. Entorno: SQLite en memoria (backend),
Chromium 1234 (frontend), stack local levantado con `qa/local-backend-bootstrap.py`.

## Compuertas automáticas

| Compuerta | Antes | Después | Comando |
|---|---|---|---|
| pytest | 223 | **276** | `pytest tests/ -q` |
| — de los cuales de la Spec 045 | — | 40 + 11 (API) + 2 (migración) | `test_approvals.py`, `test_approvals_api.py`, `test_migrations_offline.py` |
| vitest | 210 | **217** | `npm run test` |
| ruff | ✔ | ✔ | `ruff check app/ tests/ alembic/` |
| mypy | ✔ | ✔ (75 archivos) | `mypy app/` |
| tsc · eslint | ✔ | ✔ | `npm run build`, `npm run lint` |
| Bundle | 375 KB | **377 KB** (gzip 115 KB) | `npm run build` |
| axe WCAG 2.2 AA | 19/19 | **22/22** | `playwright test e2e/accessibility.spec.ts` |
| Responsive | 198/198 (33 rutas) | **216/216 (36 rutas)** · 0 scroll horizontal | `node e2e/audit-responsive-crawler.mjs` |
| Migración en dialecto PostgreSQL | — | ✔ 8 tablas + rename | `alembic upgrade 0014:0015 --sql` |
| Migración de datos idempotente | — | ✔ (2 ejecuciones) | `test_approvals_data_migration_is_idempotent` |

## Verificación directa de las pantallas nuevas

Navegación SPA autenticada, con espera de URL y de `h1` (no `page.goto`):

```
PASS /aprobaciones/bandeja       | h1="Mis aprobaciones"        | estado vacío correcto
PASS /aprobaciones/politicas     | h1="Políticas de aprobación" | estado vacío correcto
PASS /aprobaciones/delegaciones  | h1="Delegaciones"            | estado vacío correcto
menu: 3 enlaces de /aprobaciones presentes en el nav
```

## Regresión de los dominios migrados

`test_purchasing.py`, `test_sales.py`, `test_inventory.py`, `test_regulatory.py` y
`test_process_flows.py` pasan **sin cambio de expectativa** tras redirigir al motor (AC-20).

## Hallazgo sobre las herramientas de QA del proyecto

> **No es una regresión de la Spec 045.** Se detectó al intentar usar el crawler como evidencia.

`e2e/audit-route-crawler.mjs` y `e2e/accessibility.spec.ts` navegan con `page.goto(ruta)`. En una
carga completa el token de acceso vive en memoria (ADR-004) y se pierde; mientras la sesión se
restaura, el guard redirige a `/`. Resultado: **la navegación directa a cualquier ruta profunda
termina en `/`**.

Comprobado sobre rutas **preexistentes**, ajenas a esta Spec:

```
FAIL /maestros/terceros      -> url=/  h1="Inicio"
FAIL /inventario/existencias -> url=/  h1="Inicio"
FAIL /seguridad/usuarios     -> url=/  h1="Inicio"
```

Y en los resultados históricos del propio proyecto, las URLs registradas son sólo `/` y `/login`:

| Corrida | Filas | URLs distintas registradas |
|---|---:|---|
| `KONTROL-AUDIT-20260812/route-crawl-results-REAUDIT.json` | 65 | 2 (`/`, `/login`) |
| `KONTROL-AUDIT-20260812/crawl-ola5/route-crawl-results.json` | 71 | 3 |
| Esta corrida | 74 | 2 |

**Consecuencia:** las cifras «crawler 71/71 PASS» y «axe 19/19» que el expediente cita **no prueban
que cada ruta renderizó**: en su mayoría midieron la página de inicio repetidas veces. La cifra
«axe 22/22» de esta corrida tiene la misma limitación y **no se usa como evidencia de las pantallas
nuevas**; para éstas se usó la verificación directa por navegación SPA de la sección anterior.

Clasificación: **hallazgo de la Spec 054 (QA integral)**, fuera del alcance de 045. Registrado en
`convergence.md` §5 como `CVG-045-07` y elevado al backlog maestro.

## Limitación declarada

No hay servidor PostgreSQL en el entorno (BLK-D0-01): sin `psql`, sin Docker, sin binario del
servidor. Por tanto **no se ejecutaron** `alembic upgrade head`, `alembic check`, ni la prueba de
concurrencia real con `SELECT … FOR UPDATE`. Constitución v1.1 P21 lo convierte en condición de
`COMPLETE_100`.
