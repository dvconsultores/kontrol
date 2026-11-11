# ATTEMPT_LOG · CTL-05 · 2026-11-11

Base: `bb64b41`. Worktree: `~/.cache/kontrol-qa/ctl05`. El candidato no está publicado.

| Llamada | Tarea | Carga | Salida | Coste | Resultado de la auditoría | Medido tras aplicar |
|---|---|---|---|---|---|---|
| C1 | T002 backend (intento) | 28,4k caracteres, idéntica al encargo | 26,6k tokens, 18 bloques | $0,027 | PARCIAL. Se aceptan modelos, migración 0098, esquemas y cableado. Se rechazan 5 bloques de pruebas transversales: copiaron el texto del encargo o traían el SEARCH vacío sobre ficheros existentes. | Importa. Alembic arriba/abajo/arriba en PG: PASS. Servicio y API con defectos de lógica: `null`, datetime dentro del JSON, informe sin guardar, candidatas paginadas en Python, firmas inventadas, Paragraph de ReportLab inválido. Además, comparación `json` en el disparador. |
| C2 | T002 (reintento 1) | 38,9k caracteres, idéntica | 23,1k tokens, 9 bloques | $0,025 | RECHAZO PARCIAL. Se aplican la reescritura de servicio y API, las pruebas PG y las 4 pruebas transversales. Se rechazan los 2 bloques del disparador, cuyo SEARCH unía líneas no contiguas. | La app no arranca: la API importa `_subficha`, que no existe. mypy: 49 errores en ficheros `_rendicion` (firmas de `_condiciones`, `_resumenes`, `_detalle_de_evento_para_catalogo` y `_objeto_desde_evento` cambiadas). |
| C3 | T002 (reintento 2, el último) | 22,1k caracteres, idéntica | 3,8k tokens, 37 bloques | $0,006 | RECHAZO PARCIAL. Se aplican 29 bloques. Se rechazan 8: 7 con SEARCH no único y 1 con SEARCH inexistente. | La app sigue sin arrancar (`_subficha`). mypy: 27 errores (`_CatalogSpec` sin definir, UUID/str, `GovernmentEntity.name`). La suite PG no puede ejecutarse. |

**Estado:**
- `RETRY_MAX = 2` agotado en T002, y van 3 de 5 llamadas.
- La política (CLAUDE.md, «Reintentos») exige parar y reclasificar.
- Claude no escribe código (regla de la dueña), así que dividir la tarea o ampliar el presupuesto es decisión de la dueña.

**Parche del candidato:** `~/.cache/kontrol-qa/herramientas/ctl05/ctl05-candidato.patch`, con 21 ficheros y 3.043 líneas.

**Lecciones:**
1. Los fragmentos de corrección deben construirse para que **cada línea con error** sea única, no solo el fragmento completo: DeepSeek recorta el SEARCH a una línea.
2. Hay que dar las firmas reales de **toda** función ajena que se cite, también las de módulos «conocidos». Sin ellas, v4-pro las inventa.
3. Un servicio de más de 800 líneas no sale bien en una sola llamada, como ya pasó en PROC-06. Debe dividirse por funciones con contrato de firma.

## Ciclo de reconciliación (orden autónoma de la dueña, 2026-11-11)

- **Reconciliación:**
  - Primero con `b73c171` (P2, la migración `0098_dispatch_cost_relief`); la de CTL-05 pasó a 0099.
  - Después, durante el ciclo, con `6e778a4` (P2, `0099_quote_award`); la de CTL-05 pasó a `0100_gov_ctl05_rendicion`.
  - Detalle en CTL05_RECONCILIATION_REPORT.md.
- **Canal:** el puente `deepseek-executor` volvió a funcionar en un subagente nuevo, con lectura y llamada explícitas. Ver DEEPSEEK_BRIDGE_INCIDENT_CTL05.md.
- **Llamadas C4R a C32** (29 llamadas):
  - **Backend:**
    - C4R: renumeración y mypy;
    - C5 a C9: pruebas y defectos de formación, PDF, integridad y paginación;
    - C16: paridad de la migración;
    - C18: documentos en tupla;
    - C23: huella;
    - C27 y C31: recuentos transversales;
    - C32: renumeración a 0100.
  - **Frontend:**
    - C10: pantallas, menú y rutas;
    - C11: tsc y Vitest;
    - C17: fechas civiles;
    - C19: doble incorporación;
    - C28 a C30: contratos estructurales, edición de cabecera y UUID visible.
  - **E2E:** C12 a C15, C20 a C22 y C24 a C26. Cada causa se midió en una corrida real; hubo 15 corridas hasta el verde.
- **Reintentos:** ningún subproblema pasó de 2. Cada llamada nueva respondió a una causa nueva medida, a una frontera técnica nueva (P2) o a un reintento declarado (C7, C9, C14, C29 y C30).
