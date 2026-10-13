# Analyze final · véase el delta §12

Todos los contadores exigidos en 0 y TRAZABILIDAD 100 %. Comprobaciones mecánicas: `git diff` solo en `e2e/helpers/empresa.ts`,
`e2e/empresa-helper.spec.ts`, `e2e/approvals.spec.ts`, `src/tests/e2e-harness-contract.test.ts` y documentación (producto 0);
inventario de `waitForTimeout` de `e2e/` sin cambio (6 preexistentes, vigilado por el contrato); `setTimeout` solo dentro de
la sonda `emitirLaTablaTarde`; `networkidle` fuera de las dos funciones de decisión; `ESPERA_DEL_AYUDANTE_MS = 15000` y ningún
otro `timeout:` distinto de 15000 en el ayudante; `exact: true` ×3; `retries` 0 fuera de CI y `expect.timeout` sin definir
(contrato del arnés); escaneo de secretos de la evidencia → 0.
