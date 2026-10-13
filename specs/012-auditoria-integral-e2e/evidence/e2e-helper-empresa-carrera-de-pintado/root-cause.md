# Causa raíz

**Clasificación: `HELPER_INSTANT_COUNT_BEFORE_RENDER`** (con `networkidle` como señal de preparación equivocada: contribuye,
pero la decisión instantánea es lo que convierte una pantalla aún sin pintar en un fallo).

Evidencia: línea de tiempo de las tres trazas (`trace-timeline.md`: `networkidle` resuelto antes de emitirse la petición de
la tabla; `desactivar.count()` 0 → 1 en 140 ms), experimento A/B/C (la respuesta retrasada no reproduce; la emisión tardía
sí) y reproducción determinista HE-02 contra el ayudante actual (`controlled-reproduction.md`). Descartados:
`PRODUCT_NEVER_PAINTS` (la página se pinta: captura y diagnóstico con `activa=1 desactivar=1`), `NETWORK_MODULE_ABORT` (sin
`requestfailed`, backend sin errores), `AMBIGUOUS_LOCATOR_CONTRACT` (los tres nombres exactos funcionan: E2E-HELPER-EMPRESA-
AMBIGUO sigue cerrada), `PRODUCT_TRANSIENT_EMPTY_STATE` (el estado transitorio existe —`LoadingState`— y es legítimo; el
error es decidir sobre él). `ROOT_CAUSE = PROVEN` · `PRODUCT_CHANGE = 0`.
