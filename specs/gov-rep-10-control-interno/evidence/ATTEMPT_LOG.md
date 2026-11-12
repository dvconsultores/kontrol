# ATTEMPT_LOG · REP-10 (2026-11-12)

```text
DEEPSEEK_CALLS_TOTAL=10 (8 dentro del tope + 2 autorizadas por la dueña, C6 y C7)
BRIDGE_FAILURES_NOT_SENT=1 (primer R2: el puente no llegó a llamar; 0 llamadas, 0 coste)
MAX_RETRIES_SINGLE_SUBPROBLEM=2 (backend: R1 -> C1 -> C2; pantalla/E2E: R3 -> C4 -> C5)
GLOBAL_CAP_REACHED=1
COST_USD≈0.058
CLAUDE_SEMANTIC_CODE_WRITTEN=0  CLAUDE_SEMANTIC_TESTS_WRITTEN=0  CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0  CLAUDE_SEMANTIC_QA_WRITTEN=0
```

| # | Encargo | Modelo | in/out | USD | Resultado |
|---|---|---|---|---|---|
| 1 | R1 backend completo | v4-pro | 5166/8551 | 0,0097 | Servicio y API aplicados; pruebas con API inventada (`mundo.api.*`) e `int(entity_id)` sobre UUID |
| 2 | C1 (reintento 1) | v4-pro | 6868/5345 | 0,0076 | **AUDIT_REJECT**: formato incumplido, sin fichero de pruebas, desgloses contados dos veces |
| 3 | C2 (reintento 2) | v4-pro | 7246/7722 | 0,0099 | Aplicado. Defectos nuevos: `todos[-50:]` tomaba los 50 más antiguos, fechas en auditoría (500 al exportar), pruebas sin `gobierno` |
| 4 | R2 frontend (2 mensajes) | v4-pro | 7760/8825 | 0,0111 | Aplicado; `useState` sin importar, `.field_errors` en vez de `fieldErrors` |
| 5 | C3 combinada | v4-pro | 13501/6936 | 0,0118 | 19/21 aplicados (1 SEARCH sin coincidencia y 1 idéntico, rechazados) |
| 6 | R3 E2E + P1/P2 | v4-pro | 4398/3516 | 0,0050 | Aplicado; sin `gobierno_auditoria:view`, `acto.version` inexistente, `.codigo` inexistente |
| 7 | C4 (reintento 1 E2E/pantalla) | v4-pro | 1290/1063 | 0,0015 | 7/10 aplicados; **bloques 1-3 rechazados**: hooks tras los retornos tempranos (reglas de hooks) |
| 8 | C5 (reintento 2) | v4-pro | 1665/1090 | 0,0017 | 8/8 aplicados (rutas sin `resources/`, normalizadas y declaradas) |
| 9 | C6 (9/8, autorizada) | v4-flash | 317/97 | 0,00007 | Aplicado: rótulo «Acciones vencidas» buscado dentro de la región «Resumen» |
| 10 | C7 (10/8, autorizada) | v4-flash | 373/126 | 0,00009 | Aplicado: el paso responsive espera h1 y la sección antes de medir (carrera vista en la E2E canónica) |

## Lo que hizo Claude (mecánico, declarado)

- **Formato:** `ruff --fix --select I001` sobre `main.py` (orden de imports).
- **Normalización:** prefijo `resources/` en las 8 rutas de C5. El contenido de los bloques no se tocó.
- **Regeneración:** instantáneas `qa/fixtures_de_frontend.py`.
- **Diagnóstico fuera del producto, borrado tras cada corrida:**
  - pruebas `tests/test_zz_*`;
  - E2E `e2e/zz-*`;
  - una copia temporal de la pantalla con el import, restaurada byte a byte (`cmp`).

## Defectos de encargo atribuibles a Claude

1. RC1 no citó la ruta del CSV (`/reporte.csv`).
2. El diseño de rp10 en RC3 ignoraba que `audit_events` es append-only.
3. R3 pidió `acto.version`, que el ayudante no devuelve.
4. RC4 usó una ventana con líneas en blanco en los bordes y no fijó la posición de los hooks.
