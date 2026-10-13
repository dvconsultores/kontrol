# Campaña de mutaciones · E2E-HELPER-EMPRESA-CARRERA-DE-PINTADO

Guion de Claude fuera del repositorio (`mutar_he.py`): sustitución exacta sobre copia, restauración byte a byte. Las
mutaciones de comportamiento se juzgan con el runner canónico (`qa/e2e-run.py -- e2e/empresa-helper.spec.ts
e2e/approvals.spec.ts --project=chromium -g …`: base PostgreSQL nueva por corrida, sin reintentos ni tiempos alterados);
las de contrato, con Vitest (`src/tests/e2e-harness-contract.test.ts`). GOOD → PASS · MUTATED → FAIL · RESTORED → PASS.
Sin mutaciones de producto.

| Mutante | Cambio | Juez | Lo mata |
|---|---|---|---|
| M-01 | la espera devuelve la primera lectura, sin repetir | runner | HE-02, HE-05, HE-06, HE-11 |
| M-02 | la decisión vuelve a contar por su cuenta (`yaActiva` con `count()`) | Vitest | invariante «la decisión no vuelve a contar» |
| M-03 | NO_LISTA tratado como AMBIGUO | runner | HE-06, HE-08 |
| M-04 | acepta firmas incompatibles (`desactivar ≥ 1 ∧ activa ≥ 1` = ACTIVA) | runner | HE-07, HE-10 |
| M-05 | «Activar» sin `exact` | runner | HE-02, HE-05, HE-07, HE-10 |
| M-06 | sin postcondición | Vitest | invariante «la postcondición sigue» |
| M-07 | `waitForTimeout` en el ayudante | Vitest | invariante «sin esperas fijas» + inventario de `waitForTimeout` |
| M-08 | `ESPERA_DEL_AYUDANTE_MS = 30000` | Vitest | invariante del tiempo |
| M-09 | approvals vuelve a decidir al instante (`networkidle` + lectura única) | runner | HE-11 |
| M-10 | relectura instantánea tras la espera (TOCTOU) | Vitest | invariante «devuelve la lectura que satisfizo la espera» |
| M-11 | la pareja «Activa»+«Desactivar» tratada como conflicto | runner | HE-02, HE-05, HE-06, approvals exact |
| M-12 | `networkidle` como única señal (sin espera) | runner | HE-02, HE-08, HE-10 |

## Salida

```
GOOD contrato 0 []
GOOD runner 0 ['13 passed (21.0s)', "[e2e r20261013t184146p590042n638bba] suite: {'passed': 13} · limpieza: LIMPIA · salida: 0 · evidencia: <repo>/qa/e2e-runs/r20261013t184146p590042n638bba"] []
M-01 sin auto-espera (la espera devuelve la primera lectura): KILLED rc=1 ['../../qa/e2e-runs/r20261013t184219p592059n0c8226/test-results/approvals-Spec-045-·-motor-01016-dante-espera-a-que-se-pinte-chromium/t
    ✘   1 [chromium] › e2e/empresa-helper.spec.ts:41:3 › Spec 054 · el ayudante de empresa › HE-02 · con la petición de la tabla emitida tarde, el ayudant
    ✘   4 [chromium] › e2e/empresa-helper.spec.ts:64:3 › Spec 054 · el ayudante de empresa › HE-05 · la pareja «Activa» + «Desactivar» es UN estado: ACTIV
    ✘   6 [chromium] › e2e/empresa-helper.spec.ts:51:3 › Spec 054 · el ayudante de empresa › HE-06 · mientras no hay nada pintado la lectura es NO_LISTA, 
    ✘   5 [chromium] › e2e/approvals.spec.ts:497:3 › Spec 045 · motor de aprobaciones sobre PostgreSQL real › E2E-045 · con la petición de la tabla emitid
M-02 la decisión vuelve a contar por su cuenta: KILLED rc=1 []
    × el arnés E2E no se relaja > el ayudante de empresa decide con una lectura esperada, no con una fotografía ni con networkidle 6ms
    → la decisión no vuelve a contar por su cuenta: expected 'async function activarEmpresa(page: P…' not to match /yaActiva|\(await desactivar\.count\(\…
M-03 NO_LISTA tratado como AMBIGUO: KILLED rc=1 ['../../qa/e2e-runs/r20261013t184240p594772n799295/test-results/empresa-helper-Spec-054-·--685bb-y-la-espera-acaba-en-ACTIVA-chromium/test-failed-1.png', '../../
    ✘   1 [chromium] › e2e/empresa-helper.spec.ts:51:3 › Spec 054 · el ayudante de empresa › HE-06 · mientras no hay nada pintado la lectura es NO_LISTA, 
    ✘   8 [chromium] › e2e/empresa-helper.spec.ts:103:3 › Spec 054 · el ayudante de empresa › HE-08 · si la tabla no llega nunca, el ayudante falla en su 
M-04 acepta firmas incompatibles (dos Desactivar): KILLED rc=1 ['../../qa/e2e-runs/r20261013t184313p596893nc7138f/test-results/empresa-helper-Spec-054-·--f6a32-ra-falla-con-el-diagnóstico-chromium/test-failed
    ✘   7 [chromium] › e2e/empresa-helper.spec.ts:83:3 › Spec 054 · el ayudante de empresa › HE-07 · una lectura contradictoria es AMBIGUO y, si persiste,
    ✘   8 [chromium] › e2e/empresa-helper.spec.ts:95:3 › Spec 054 · el ayudante de empresa › HE-10 · más de una empresa activa no es una postcondición vál
M-05 Activar sin exact: KILLED rc=1 ['../../qa/e2e-runs/r20261013t184345p598971nf55636/test-results/empresa-helper-Spec-054-·--e5e5a-ra-a-que-se-pinte-y-acierta-chromium/test-failed-1.png', '../../qa/e2e-runs/
    ✘   1 [chromium] › e2e/empresa-helper.spec.ts:64:3 › Spec 054 · el ayudante de empresa › HE-05 · la pareja «Activa» + «Desactivar» es UN estado: ACTIV
    ✘   7 [chromium] › e2e/empresa-helper.spec.ts:95:3 › Spec 054 · el ayudante de empresa › HE-10 · más de una empresa activa no es una postcondición vál
    ✘   4 [chromium] › e2e/empresa-helper.spec.ts:41:3 › Spec 054 · el ayudante de empresa › HE-02 · con la petición de la tabla emitida tarde, el ayudant
    ✘   8 [chromium] › e2e/empresa-helper.spec.ts:83:3 › Spec 054 · el ayudante de empresa › HE-07 · una lectura contradictoria es AMBIGUO y, si persiste,
M-06 sin postcondición: KILLED rc=1 []
    × el arnés E2E no se relaja > el ayudante de empresa decide con una lectura esperada, no con una fotografía ni con networkidle 5ms
    → la postcondición sigue: exactamente una empresa activa: expected 'async function activarEmpresa(page: P…' to match /await expect\(desactivar\)\.toHa
M-07 waitForTimeout en el ayudante: KILLED rc=1 []
    × el arnés E2E no se relaja > el ayudante de empresa decide con una lectura esperada, no con una fotografía ni con networkidle 5ms
    → sin esperas fijas: expected 'async function activarEmpresa(page: P…' not to match /waitForTimeout|setTimeout/
    × el arnés E2E no se relaja > no entran esperas fijas nuevas 9ms
    → expected { …(5) } to deeply equal { …(4) }
M-08 tiempo mayor: KILLED rc=1 []
    × el arnés E2E no se relaja > el ayudante de empresa decide con una lectura esperada, no con una fotografía ni con networkidle 5ms
    → expected '/**\n * El ayudante de empresa de los…' to match /export const ESPERA_DEL_AYUDANTE_MS =…/
M-09 approvals vuelve a decidir al instante: KILLED rc=1 ['../../qa/e2e-runs/r20261013t184422p602067na971b8/test-results/approvals-Spec-045-·-motor-01016-dante-espera-a-que-se-pinte-chromium/test-failed-1.png'
    ✘   1 [chromium] › e2e/approvals.spec.ts:492:3 › Spec 045 · motor de aprobaciones sobre PostgreSQL real › E2E-045 · con la petición de la tabla emitid
M-10 relectura instantánea tras la espera (TOCTOU): KILLED rc=1 []
    × el arnés E2E no se relaja > el ayudante de empresa decide con una lectura esperada, no con una fotografía ni con networkidle 9ms
    → expected 'export async function esperarEstadoDe…' to match /return lectura as LecturaDeEmpresa;/
M-11 la pareja Activa+Desactivar se trata como conflicto: KILLED rc=1 ['../../qa/e2e-runs/r20261013t184459p604553ne3134d/test-results/approvals-Spec-045-·-motor-01016-dante-espera-a-que-se-pinte-chromium/test-
    ✘   1 [chromium] › e2e/empresa-helper.spec.ts:41:3 › Spec 054 · el ayudante de empresa › HE-02 · con la petición de la tabla emitida tarde, el ayudant
    ✘   6 [chromium] › e2e/empresa-helper.spec.ts:64:3 › Spec 054 · el ayudante de empresa › HE-05 · la pareja «Activa» + «Desactivar» es UN estado: ACTIV
    ✘   3 [chromium] › e2e/approvals.spec.ts:506:3 › Spec 045 · motor de aprobaciones sobre PostgreSQL real › E2E-045 · el localizador de «Activar» nunca 
    ✘   2 [chromium] › e2e/empresa-helper.spec.ts:51:3 › Spec 054 · el ayudante de empresa › HE-06 · mientras no hay nada pintado la lectura es NO_LISTA, 
M-12 networkidle como única señal: KILLED rc=1 ['../../qa/e2e-runs/r20261013t184608p607132ned7839/test-results/empresa-helper-Spec-054-·--e5e5a-ra-a-que-se-pinte-y-acierta-chromium/test-failed-1.png', '../..
    ✘   4 [chromium] › e2e/empresa-helper.spec.ts:41:3 › Spec 054 · el ayudante de empresa › HE-02 · con la petición de la tabla emitida tarde, el ayudant
    ✘   8 [chromium] › e2e/empresa-helper.spec.ts:103:3 › Spec 054 · el ayudante de empresa › HE-08 · si la tabla no llega nunca, el ayudante falla en su 
    ✘   9 [chromium] › e2e/empresa-helper.spec.ts:95:3 › Spec 054 · el ayudante de empresa › HE-10 · más de una empresa activa no es una postcondición vál
RESTORED contrato 0 []
RESTORED runner 0 ['13 passed (21.3s)', "[e2e r20261013t184637p609589n3c7ad0] suite: {'passed': 13} · limpieza: LIMPIA · salida: 0 · evidencia: <repo>/qa/e2e-runs/r20261013t184637p609589n3c7ad0"] []
RESUMEN: 12 / 12 muertas
rc=0
copias .good residuales: 0
```

**12/12 muertas**; ninguna equivalente. GOOD y RESTORED: runner 13/13 y contrato 5/5. Tras la campaña, 0 copias `.good` y los tres ficheros con el cambio del ciclo intacto.
