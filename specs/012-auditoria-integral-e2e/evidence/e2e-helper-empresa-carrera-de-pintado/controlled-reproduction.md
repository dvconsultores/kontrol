# Reproducción controlada (W08/W09)

## Por qué `page.route` no reproduce (experimentos B y C, corrida `r20261013t183033…`)

`networkidle` espera a que no haya peticiones en vuelo durante 500 ms: si la petición de la tabla **ya se emitió**,
retrasar su respuesta solo hace esperar al ayudante. El fallo real es que la petición se emite **tarde** (la página la
pide ≈ 360 ms después del cambio de ruta bajo carga) y `networkidle` se resuelve antes sin saber que llegará.

```
[A] +966ms URL · +994ms REQ ?page_size=10 · +1003ms RES · +1504ms NETWORKIDLE · desactivar=1 activa=1 (pintada)
[B] respuesta retardada 3 s con page.route → el ayudante actual terminó en 3827 ms (ESPERÓ) · ✓
[C] respuesta retardada 2,5 s → terminó en 3347 ms (ESPERÓ) · ✓
```

## Mecanismo determinista: diferir la EMISIÓN de la petición de la tabla

`emitirLaTablaTarde(page, ms)` (sonda de arnés, `page.addInitScript` instalada antes de cargar la aplicación): en la propia
página, el `fetch` de `GET /organization/companies?page=1&page_size=10` se difiere `ms` milisegundos (o no se emite nunca con
`null`) antes de salir. Ninguna petición en vuelo → `networkidle` se resuelve a los 500 ms → el ayudante actual cuenta sobre
la pantalla sin pintar. 2 000 ms ≫ 500 ms: el orden es determinista, no probabilístico. Sin tocar producto ni red.

## Resultado contra el ayudante ACTUAL (HEAD 0f4a5c3), corrida `r20261013t183318…`

```
  ✓  1 [chromium] › e2e/empresa-helper.spec.ts:117:3 › Spec 054 · el ayudante de empresa › la empresa activa es la que el contexto usa de verdad (2.3s)
  ✓  5 [chromium] › e2e/empresa-helper.spec.ts:65:3 › Spec 054 · el ayudante de empresa › el localizador de «Activar» nunca alcanza «Desactivar» (2.5s)
  ✓  2 [chromium] › e2e/empresa-helper.spec.ts:82:3 › Spec 054 · el ayudante de empresa › es idempotente: pedir la empresa que ya está activa no la apaga (2.6s)
  ✘  3 [chromium] › e2e/empresa-helper.spec.ts:55:3 › Spec 054 · el ayudante de empresa › HE-02 · con la petición de la tabla emitida tarde, el ayudante espera a que se pinte y acierta (2.6s)
  ✓  4 [chromium] › e2e/empresa-helper.spec.ts:100:3 › Spec 054 · el ayudante de empresa › desde el estado contrario converge y verifica la postcondición (2.8s)
    Error: estado de empresa no determinable: activar=0 compuerta=0 activa=0 desactivar=0 botones=["","Salir",""]
    Expected: 1
    Received: 0
    ../../qa/e2e-runs/r20261013t183318p580055n5819b3/test-results/empresa-helper-Spec-054-·--e5e5a-ra-a-que-se-pinte-y-acierta-chromium/test-failed-1.png
  1 failed
  4 passed (3.7s)
[e2e r20261013t183318p580055n5819b3] suite: {'failed': 1, 'passed': 4} · limpieza: LIMPIA · salida: 1 · evidencia: <repo>/qa/e2e-runs/r20261013t183318p580055n5819b3
```

HE-02 falla **determinísticamente** con la firma exacta (`activar=0 compuerta=0 activa=0 desactivar=0`: nada pintado) y las
cuatro pruebas previas pasan. `CURRENT_HELPER_RACE_REPRODUCED = YES`. Tras liberar la petición la página sí se pinta (la
captura del fallo original y el experimento A lo muestran): `PRODUCT_PAINT_EVENTUALLY = YES`.
