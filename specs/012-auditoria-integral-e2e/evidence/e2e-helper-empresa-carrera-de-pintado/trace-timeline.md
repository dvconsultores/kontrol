# Línea de tiempo de las trazas · `r20261013t151632p464844n5ddc32` (3 fallos; `trace.zip` leídos con un guion de Claude)

Tiempos relativos al inicio de cada prueba (acciones del `.trace`) y peticiones del `.network` (hora absoluta → relativa
anclando el `POST /auth/login` a la acción «Iniciar sesión»). Sin direcciones ni cabeceras.

## `empresa-helper.spec.ts:28` («nunca alcanza Desactivar»)

| T | ms | Qué |
|---|---|---|
| T0 | 1722 → 2471 | clic en el menú «Empresas» → `waitForURL` cumplido (cambio de ruta SPA) |
| T1 | 2504 → **2626** | `waitForLoadState("networkidle")` **resuelto**: la última petición (`GET …companies?page=1&page_size=100`, la del contexto, ≈1620-1680) llevaba > 500 ms terminada |
| T2 | **≈ 2830** | `GET /organization/companies?page=1&page_size=10` (la tabla) **se emite**: ≈ 360 ms después del cambio de ruta y **después** de `networkidle` |
| T3 | ≈ 2886 | respuesta 200 (56 ms) |
| T8 | 2626 → 2825 | `activar.allInnerTexts()` (200 ms: hilo principal ocupado) → `[]` |
| T8 | 2856 → 2895 | `desactivar.count()` → **0** (la tabla aún no está; `activa.count()` ni se evalúa por cortocircuito) → `yaActiva = false` |
| T9 | 2909 / 2939 | `activar.count()` → 0 · `compuerta.count()` → 0 → rama «no determinable» |
| T10 | 2990 / 3034 | diagnóstico: `activa.count()` → **1**, `desactivar.count()` → **1**: la tabla se pintó entre T8 y T10 |
| Δ | ≈ 140 ms | entre el `count()` que decidió (0) y el que diagnosticó (1) |

## `empresa-helper.spec.ts:45` («idempotente»)

Misma secuencia: `networkidle` 2529 → 2612; `desactivar.count()` 2716-2739 → 0; `activar.count()` 2762 → 0; compuerta 2798
→ 0; diagnóstico `activa` 2839 → 1 (el `desactivar` del diagnóstico aún 0 → `activa=1 desactivar=0`, el único caso así: la
fila se estaba pintando en ese instante); petición de la tabla ≈ 2870 (15:17:50.639).

## `approvals.spec.ts:496` (copia local)

`networkidle` 2228 → 2303; `activar.allInnerTexts` 2303-2368; `desactivar.count()` 2391 → 0; login por API y `empresa()`
2423-2683 (la copia local resuelve el código); `activar.count()` 2687 → 0; `elegir-empresa-D1` 2721 → 0; diagnóstico
`activa` 2743 → 1, `desactivar` 2767 → 1. Petición de la tabla ≈ 2500 (15:17:17.174), emitida tras `networkidle`.

## Lectura

En las tres, `networkidle` se resolvió **antes** de que la página emitiera la petición de la tabla: `networkidle` solo
espera a peticiones ya en vuelo, y bajo carga (tres navegadores a la vez; `allInnerTexts` tardó 200 ms) la petición
salió ≈ 300-360 ms después del cambio de ruta. En una corrida sin carga (experimento A) sale **28 ms** después y
`networkidle` se resuelve 500 ms tras su respuesta, ya con la tabla pintada. Experimentos B y C (retrasar la RESPUESTA
con `page.route` 2,5-3 s): el ayudante actual **espera** y pasa, porque `networkidle` sí ve la petición en vuelo.

`RACE_TIMELINE = PROVEN`. Captura y `error-context.md` del fallo muestran la página ya pintada con «Activa»/«Desactivar».
