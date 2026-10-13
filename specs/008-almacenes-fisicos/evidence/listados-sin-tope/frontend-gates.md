# Gates de frontend (W34) · `resources/frontend/`

```
### typecheck ###
TSC_OK
### lint ###
LINT_OK
### vitest ###
 Test Files  36 passed (36)
      Tests  481 passed (481)
### build ###
dist/assets/TasasPage-O5qEXUqg.js                  13.17 kB │ gzip:   3.83 kB
dist/assets/DataTable-DmErvuzl.js                  52.53 kB │ gzip:  14.27 kB
dist/assets/index-BdmFHKzL.js                     416.72 kB │ gzip: 126.99 kB
✓ built in 3.30s
rc=0
```

| Gate | Resultado |
|---|---|
| `tsc -b --noEmit` (src + herramientas + e2e) | PASS |
| `eslint . --max-warnings 0` | PASS |
| Vitest | **481/481** (ref. 477 + 4 pruebas nuevas de `listAllWarehouses`) |
| `vite build` | PASS |
