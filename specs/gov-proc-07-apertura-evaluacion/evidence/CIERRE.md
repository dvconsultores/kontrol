# PROC-07 · Evidencia de cierre (2026-11-10)

Base pública: `de4773a` (merge ordinario por avance rápido desde `560fb07`). Migración reubicada:
`0092_gov_proc07_evaluacion` → `0091_location_validations` → `0090_import_difference_report`. Cabeza única.

| Comprobación | Resultado |
|---|---|
| E2E canónica `e2e/gobierno-evaluacion.spec.ts` (Chromium, PostgreSQL efímero, Alembic, analizador real) | 1/1 PASS (1,3 min) |
| Backend PROC-07 + guardas derivadas (PostgreSQL) | 54/54 |
| Backend PROC-02, PROC-03, PROC-06 (PostgreSQL) | 26/26 |
| Regresión del minuto (`test_apertura_mismo_minuto_que_recepcion`) | PASS con el servicio actual; FALLA con el anterior (422 en lugar de 201) |
| Alembic en PostgreSQL nuevo: upgrade, downgrade 0091_location_validations, upgrade, downgrade 0090_import_difference_report, upgrade | PASS |
| tsc, ESLint (0 avisos), build | PASS |
| Vitest Gobierno | 76 ficheros, 634 pruebas PASS |
| Vitest de contratos con instantáneas regeneradas | 5 ficheros, 375 pruebas PASS |
| ruff (ficheros tocados) | limpio |
| mypy `app` | 154 = línea base pública `de4773a`; 0 nuevos |
| OpenAPI frente a `de4773a` | solo añadidos: 9 rutas `/evaluacion…`, 5 esquemas; 0 cambiados, 0 quitados |
| Catálogo de auditoría | 433 (425 públicas + 8) |

## Lo que recorre la E2E en el navegador

Menú → expediente → «Apertura y evaluación»:
1. Recepción concluida; matriz técnica, económica y legal; bloqueo; criterio tardío rechazado (409).
2. Oferta sellada y documento inaccesible (404).
3. Quórum insuficiente rechazado; quórum válido; acta; apertura.
4. Oferta «Abierta», «Sello levantado en la apertura», «Registrada por», quórum 3 de 3 y acta; doble apertura 409.
5. Aporte con `matriz_version` vieja → 409 `GOV_EVAL_MATRIX_STALE`, sin aportes nuevos ni cambio de versión.
6. Documento liberado accesible.
7. Aportes técnico (45.00), económico (40.00) y legal (Cumple), cada uno con evaluador y «Vigente»; reemplazo 44.50 con historial «45.00 · fecha».
8. Resultados de la Comisión (44.00, 41.00, Cumple), registrados por la Secretaría, independientes de los aportes.
9. Conclusión; cronología; ausencia de Adjudicar o Declarar desierta.
10. Axe en 4 puntos con 0 violaciones; 390 y 320 px sin desborde en la apertura, la evaluación y la conclusión.

## Defecto de producto hallado por la E2E

El formulario envía la hora de apertura al minuto; el servidor comparaba con segundos contra la conclusión de la recepción.
Una apertura en el mismo minuto se rechazaba. Ahora se compara con el inicio de ese minuto.

## DeepSeek

5 llamadas a deepseek-v4-pro en los bloques G, H e I del 2026-11-10: G1, G2, H1, H2 e I1. Claude no escribió código del producto.
