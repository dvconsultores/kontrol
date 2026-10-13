# Gates estáticos de frontend y E2E (W23) · `resources/frontend/`

```
### typecheck ###
TSC_OK
### lint ###
LINT_OK
### vitest ###
 Test Files  36 passed (36)
      Tests  482 passed (482)
### build ###
dist/assets/DataTable-DmErvuzl.js                  52.53 kB │ gzip:  14.27 kB
dist/assets/index-BdmFHKzL.js                     416.72 kB │ gzip: 126.99 kB
✓ built in 2.93s
```

| Gate | Resultado |
|---|---|
| `tsc -b --noEmit` (src + herramientas + `e2e/` por `tsconfig.e2e.json`) | PASS |
| `eslint . --max-warnings 0` (recorre `e2e/`) | PASS |
| Vitest | **482/482** (481 + 1 invariante nuevo del contrato del arnés) |
| `vite build` | PASS |
| Producto (frontend `src/{modules,pages,api,app,components}`, backend `app/`) | **0 líneas de diff** |
| Ficheros del ciclo | `e2e/helpers/empresa.ts`, `e2e/empresa-helper.spec.ts`, `e2e/approvals.spec.ts`, `src/tests/e2e-harness-contract.test.ts` (solo arnés) |
