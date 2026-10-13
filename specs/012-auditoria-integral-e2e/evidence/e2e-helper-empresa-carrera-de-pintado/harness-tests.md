# Pruebas de arnés (HE) · corrida dirigida por el runner canónico `r20261013t183855…` (base nueva, chromium)

```
  ✓   6 [chromium] › e2e/approvals.spec.ts:506:3 › Spec 045 · motor de aprobaciones sobre PostgreSQL real › E2E-045 · el localizador de «Activar» nunca alcanza «Desactivar» (3.2s)
  ✓   1 [chromium] › e2e/empresa-helper.spec.ts:64:3 › Spec 054 · el ayudante de empresa › HE-05 · la pareja «Activa» + «Desactivar» es UN estado: ACTIVA, nunca ambiguo (3.7s)
  ✓   3 [chromium] › e2e/approvals.spec.ts:497:3 › Spec 045 · motor de aprobaciones sobre PostgreSQL real › E2E-045 · con la petición de la tabla emitida tarde, el ayudante espera a que se pinte (4.3s)
  ✓   5 [chromium] › e2e/approvals.spec.ts:522:3 › Spec 045 · motor de aprobaciones sobre PostgreSQL real › E2E-045 · el ayudante de empresa es idempotente (4.3s)
  ✓   4 [chromium] › e2e/empresa-helper.spec.ts:51:3 › Spec 054 · el ayudante de empresa › HE-06 · mientras no hay nada pintado la lectura es NO_LISTA, no un fallo, y la espera acaba en ACTIVA (4.7s)
  ✓   2 [chromium] › e2e/empresa-helper.spec.ts:41:3 › Spec 054 · el ayudante de empresa › HE-02 · con la petición de la tabla emitida tarde, el ayudante espera a que se pinte y acierta (4.8s)
  ✓  10 [chromium] › e2e/empresa-helper.spec.ts:111:3 › Spec 054 · el ayudante de empresa › el localizador de «Activar» nunca alcanza «Desactivar» (1.9s)
  ✓   7 [chromium] › e2e/empresa-helper.spec.ts:83:3 › Spec 054 · el ayudante de empresa › HE-07 · una lectura contradictoria es AMBIGUO y, si persiste, la espera falla con el diagnóstico (3.2s)
  ✓  11 [chromium] › e2e/empresa-helper.spec.ts:128:3 › Spec 054 · el ayudante de empresa › es idempotente: pedir la empresa que ya está activa no la apaga (2.0s)
  ✓  12 [chromium] › e2e/empresa-helper.spec.ts:146:3 › Spec 054 · el ayudante de empresa › desde el estado contrario converge y verifica la postcondición (2.1s)
  ✓  13 [chromium] › e2e/empresa-helper.spec.ts:163:3 › Spec 054 · el ayudante de empresa › la empresa activa es la que el contexto usa de verdad (1.1s)
  ✓   8 [chromium] › e2e/empresa-helper.spec.ts:95:3 › Spec 054 · el ayudante de empresa › HE-10 · más de una empresa activa no es una postcondición válida (16.5s)
  ✓   9 [chromium] › e2e/empresa-helper.spec.ts:103:3 › Spec 054 · el ayudante de empresa › HE-08 · si la tabla no llega nunca, el ayudante falla en su tiempo de siempre, con el diagnóstico (16.1s)
  13 passed (21.4s)
[e2e r20261013t183855p582932n1c98e1] suite: {'passed': 13} · limpieza: LIMPIA · salida: 0 · evidencia: <repo>/qa/e2e-runs/r20261013t183855p582932n1c98e1
```

| HE | Qué | Dónde | Resultado |
|---|---|---|---|
| HE-01 | fallo determinista del ayudante antiguo con la emisión diferida (`activar=0 compuerta=0 activa=0 desactivar=0`) | `controlled-reproduction.md` (corrida `r20261013t183318…`, antes del cambio) | PASS (falló como se esperaba) |
| HE-02 | emisión diferida 2 s: el ayudante espera y acierta | `empresa-helper.spec.ts` | PASS |
| HE-03 | ya activa: idempotente ×3, no pulsa nada destructivo | «es idempotente…» (existente) | PASS |
| HE-04 | sin empresa activa (compuerta): activa y verifica la postcondición | «desde el estado contrario…» (existente) | PASS |
| HE-05 | «Activa» + «Desactivar» = UN estado ACTIVA | `empresa-helper.spec.ts` | PASS |
| HE-06 | nada pintado = NO_LISTA, no fallo; la espera acaba en ACTIVA | `empresa-helper.spec.ts` | PASS |
| HE-07 | ambigüedad real (un «Desactivar» impostor inyectado en el DOM de la prueba): AMBIGUO y, persistente, falla con el diagnóstico `AMBIGUO: activar=0 compuerta=0 activa=1 desactivar=2` | `empresa-helper.spec.ts` | PASS |
| HE-08 | la tabla no llega nunca: falla en su tiempo de siempre (≈16 s) con `NO_LISTA: …` | `empresa-helper.spec.ts` | PASS |
| HE-09 | localizadores exactos: «Desactivar» no casa con «Activar» | «el localizador de Activar nunca alcanza Desactivar» (existente) + contrato estático | PASS |
| HE-10 | más de una activa (pareja impostora inyectada): `AMBIGUO: … activa=2 desactivar=2`, falla | `empresa-helper.spec.ts` | PASS |
| HE-11 | approvals con emisión diferida: espera y pasa; idempotencia y exact de approvals | `approvals.spec.ts` (3 pruebas) | PASS |
| HE-12/13/14 | sin `waitForTimeout`/`setTimeout` en la decisión; sin `waitForLoadState("networkidle")`; `ESPERA_DEL_AYUDANTE_MS = 15000` y ningún otro `timeout:` distinto de 15000; `expect.poll`; la espera devuelve la lectura que la satisfizo; tres localizadores exactos; postcondición presente | `src/tests/e2e-harness-contract.test.ts` (Vitest) | PASS |
| HE-15 | producto 0 | `git diff -- resources/frontend/src resources/backend/app` vacío (salvo `src/tests/`) | PASS |
| HE-16 | E2E-PANTALLA-SIN-PINTAR sigue OPEN | roadmap | PASS |

13/13 en el runner (21,4 s), base de corrida eliminada. HE-08 y HE-10 tardan ≈16 s cada una por diseño: agotan el tiempo del
ayudante (15 s) sin subirlo.
