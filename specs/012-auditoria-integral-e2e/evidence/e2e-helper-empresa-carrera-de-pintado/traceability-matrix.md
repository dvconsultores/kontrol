# Matriz de trazabilidad · E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO

| Eslabón | Artefacto | Prueba / evidencia |
|---|---|---|
| fallos observados | global `r20261013t151632…` (3) | `historical-frequency.md` |
| trazas | `trace.zip` ×3 leídos | `trace-timeline.md` |
| línea de tiempo petición/pintado | `networkidle` antes de la petición; `count()` 0 → 1 en 140 ms | `trace-timeline.md`, experimento A |
| firmas de estado | ACTIVA/INACTIVA/COMPUERTA/NO_LISTA/AMBIGUO | `state-signatures.md`, `render-state-model.md`; HE-05/06/07 |
| conteos instantáneos del ayudante | causa raíz | `root-cause.md`; HE-01 (fallo determinista del antiguo) |
| reproducción determinista | `emitirLaTablaTarde` (emisión diferida); `page.route` descartado con evidencia | `controlled-reproduction.md`; HE-02 |
| diseño de espera | `expect.poll` + lectura única, 15 s | `wait-design.md`; M-01/M-08/M-10/M-12 |
| cambio del ayudante | `e2e/helpers/empresa.ts` | HE-02…10; contrato estático |
| approvals | `LOCAL_SHARED_PRIMITIVE` | `approvals-strategy.md`; HE-11; M-09 |
| pruebas de arnés | `empresa-helper.spec.ts`, `approvals.spec.ts`, contrato Vitest | `harness-tests.md` (13/13 + 5/5) |
| mutaciones | M-01…M-12 | `mutation-campaign.md` (12/12) |
| gates estáticos | typecheck, lint, Vitest 482/482, build | `frontend-static-gates.md` |
| E2E global 1 / 2 | runner canónico | `global-e2e-1.md`, `global-e2e-2.md` |
| convergencia | delta §12 | `convergence.md` |

FR-HE-001…028 → T01–T06 y HE-01…16 (delta §4, §8, §11). Cobertura: **100 %**.
