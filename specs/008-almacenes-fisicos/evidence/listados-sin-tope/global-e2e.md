# E2E globales canónicas (W36) · `resources/backend/.venv/bin/python qa/e2e-run.py` · base PostgreSQL efímera por corrida

Fuente E2E y frontend cambiaron (T04/T05): **dos globales limpias** obligatorias. La primera cayó por un intermitente ajeno,
clasificado con evidencia independiente antes de correr dos más (no es reintento hasta verde: la clasificación precede).

## Corrida 1

```
[e2e r20261013t151632p464844n5ddc32] crear base
  3 failed
  4 skipped
  4 did not run
  266 passed (4.4m)
[e2e r20261013t151632p464844n5ddc32] entorno: túnel (VPN) presente
[e2e r20261013t151632p464844n5ddc32] suite: {'failed': 3, 'skipped': 4, 'did not run': 4, 'passed': 266} · limpieza: LIMPIA · salida: 1 · evidencia: <repo>/qa/e2e-runs/r20261013t151632p464844n5ddc3
rc=1
```

## Corrida 2

```
[e2e r20261013t152120p495303n800604] crear base
  4 skipped
  273 passed (4.4m)
[e2e r20261013t152120p495303n800604] entorno: túnel (VPN) presente
[e2e r20261013t152120p495303n800604] suite: {'skipped': 4, 'passed': 273} · limpieza: LIMPIA · salida: 0 · evidencia: <repo>/qa/e2e-runs/r20261013t152120p495303n800604
rc=0
```

## Corrida 3

```
[e2e r20261013t152645p529338n5eef74] crear base
  4 skipped
  273 passed (4.0m)
[e2e r20261013t152645p529338n5eef74] entorno: túnel (VPN) presente
[e2e r20261013t152645p529338n5eef74] suite: {'skipped': 4, 'passed': 273} · limpieza: LIMPIA · salida: 0 · evidencia: <repo>/qa/e2e-runs/r20261013t152645p529338n5eef74
rc=0
```

| Corrida | Resultado | Clasificación |
|---|---|---|
| 1 · `r20261013t151632…` | 266 / **3** / 4 (+4 sin correr) | `approvals.spec.ts:496`, `empresa-helper.spec.ts:28` y `:45`: «estado de empresa no determinable: activar=0 compuerta=0 activa=1 desactivar=1»; el ayudante `activarEmpresa` decide con `count()` instantáneos tras `networkidle` y la tabla se pinta entre la decisión y el diagnóstico (la captura del error muestra la página ya pintada con «Activa»/«Desactivar»); backend.log sin errores; ninguna de las tres toca almacenes ni pick-lists; túnel VPN presente. **Intermitente de arnés independiente** (familia E2E-PANTALLA-SIN-PINTAR; candidata `E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO`, dueña 054). No absorbido. Trazas y capturas en `qa/e2e-runs/r20261013t151632…/test-results/` |
| 2 · `r20261013t152120…` | **273 / 0 / 4** (4.4 min) | limpia |
| 3 · `r20261013t152645…` | **273 / 0 / 4** (4.0 min) | limpia |

Las 4 omitidas de cada corrida son las de `ENTORNO-SIN-CLAMSCAN`. Las suites que consumen los dos listados corregidos
(`putaway.spec.ts` con `todasLasListasDePreparacion` y `limit=100`, `picking.spec.ts`, `order-confirmation`, `sales-orders`,
`receipts`, `inventory-confirmation`, `warehouse-structure`, `warehouse-a11y`) pasan en las tres corridas. Bases de corrida
residuales 0 · puertos libres · directorios temporales del arnés 0 · schemas `t_` 0.
