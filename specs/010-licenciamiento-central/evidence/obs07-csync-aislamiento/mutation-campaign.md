# Mutaciones (GOOD→PASS · MUTATED→FAIL · RESTORED→PASS; copias GOOD; `PYTHONDONTWRITEBYTECODE=1`; juego: módulo + regresión)
| Id | Mutación | Detectada por |
|---|---|---|
| M-01 | `_mundo` vuelve a `scope="module"` | aisl_02 (orden inverso), aisl_01, aisl_03 |
| M-02 | csync_02 sin `_configura_autoridad` | aisl_03, csync_02 |
| M-03 | csync_06 sin `_importa_licencia` | aisl_03, csync_06 |
| M-04 | csync_04 sin `_sincronizacion_previa` | aisl_03, csync_04 |
| M-05 | `_importa_licencia` sin `POST SYNC` | csync_06/07/08/10 |
| M-06 | el override del cliente congela la factoría de la primera prueba | csync_11, csync_12, … |
| M-07 | `_sincronizacion_previa` no sincroniza | csync_04, aisl_02 |
| M-08 | aserción de csync_13 debilitada | aisl_03 |
| M-09 | la regresión inversa no invierte el orden | aisl_02 (**tras T07b**: superviviente en la primera pasada) |
| M-10 | `_aplicaciones` por prueba (caro) | aisl_03 |
| M-11 | csync_07 con la precondición después de otra sentencia | aisl_03 |
| M-12 | `sleep` en un ayudante | aisl_03 |
| M-13 | csync_01 llama a un ayudante de precondición | aisl_03 |
**13/13 detectadas** (12 en la primera pasada; M-09 tras T07b); restauración idéntica tras cada una.
