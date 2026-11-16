# ATTEMPT_LOG · CNT-09 Alertas de vencimientos (2026-11-16)

- Modelo: deepseek-v4-pro, sin session_id ni thinking.
- Llamadas: objetivo 3–5, tope duro 8, sin excepción heredada.
- **Resultado: 8 llamadas con respuesta. No hubo llamadas perdidas.** OWNER_EXCEPTION_USED=0.

| Llamada | Encargo | Entrada/salida | USD | Auditoría |
|---|---|---|---|---|
| D1 | Backend completo: modelo, migración 0120, servicio, API, esquemas, registro, catálogo 047, mensajes, auditoría y 5 fijaciones | 7.973 / 8.076 | 0,0105 | 17/17 bloques PASS. Rutas sin `resources/backend/`, prefijo añadido como normalización de formato; la ambigüedad estaba en el encargo. Observaciones menores: el `before`/`after` de auditoría omite las fuentes sin fila y los docstrings PDD van numerados distinto |
| D2 | Pruebas PG (8) | 5.056 / 6.037 | 0,0075 | Llegó con cerca de código, sin marcadores (normalizado). REJECT: import inexistente, F401, usuarios por id en lugar de nombre y `status=ALL` |
| D3 | Frontend y Vitest | 6.187 / 8.788 | 0,0103 | 11/12 PASS. REJECT de un bloque: retiraba `SupervisionContrato` de la ficha (regresión de CNT-04). Además: imports sin uso, un tipo, `htmlFor` de FormField y el texto de ForbiddenState |
| D2b | Reintento 1 de las pruebas PG | 6.762 / 12.103 | 0,0135 | Correcto en parte. Defectos: F821 (falta `GovernmentGuaranteeInstrument`), F841 y aislamiento entre pruebas (la base se comparte; el defecto venía del diseño del encargo de Claude) |
| D5 | Reintento 2 de las pruebas PG + reintento 1 del frontend | 8.118 / 7.002 | 0,0096 | Frontend PASS; un SEARCH repetido se aplicó a ambas apariciones de forma mecánica. Pruebas: 5/8; quedaban las aserciones sobre el valor de `_rec` y el 404 de otra empresa |
| D4 | E2E del sponsor (tramo CNT-09) | 2.503 / 1.771 | 0,0026 | Llegó sin marcadores: los SEARCH se reconstruyeron con las anclas exactas del encargo (formato). Defecto: `const` redeclarado (TS2451) |
| D6 | Tarea dividida, tras agotar los reintentos de las pruebas PG: líneas literales en las pruebas y renombrar en la E2E | 1.190 / 884 | 0,0013 | PASS. Rutas entre ángulos (formato). Cada bloque se aplicó a todas sus apariciones idénticas |
| D7 | Contraste de las etiquetas de severidad (tokens de color inexistentes) | 671 / 285 | 0,0005 | PASS. Se quitó una línea `<ruta>` literal (formato) |

**Total:** 38.460 tokens de entrada, 44.946 de salida, **USD 0,0558**.

## Reintentos y reclasificación

- Pruebas PG: intento, más 2 reintentos (D2b y D5). Al agotarse, **se dividió la tarea** (D6), como establece la política: líneas literales y locales.
- Frontend: 1 reintento (D5). E2E: 1 corrección (D6).
- Defectos de diseño de Claude hallados en la verificación:
  - rutas de los ficheros ambiguas (D1);
  - aserciones globales sobre una base compartida entre pruebas (D2);
  - suposición de que «ua» accede a company_b (D2);
  - no haber previsto que FormField reemplaza el id del hijo (D3).
- Defecto preexistente de la Spec 047 que CNT-09 dejó al descubierto: `EtiquetaSeveridad` usaba `text-warning-700` y `text-danger-700`, que no existen en el tema (contraste 4,27). Corregido en D7 con los tokens -600 (≥ 4,5:1).

## Integración mecánica de Claude (sin semántica)

- Normalizaciones de formato (FORMAT_ONLY_EDITS=6): prefijo de rutas en D1; cerca de código a bloque en D2; anclas a bloques en D4; ángulos en D6; `<ruta>` en D7; aplicación de un mismo bloque a varias apariciones idénticas (D5 y D6).
- Fixtures de OpenAPI regeneradas con `qa/fixtures_de_frontend.py`.
- Matrices de completitud actualizadas (documentación).

CLAUDE_SEMANTIC_CODE_WRITTEN=0, CLAUDE_SEMANTIC_TESTS_WRITTEN=0, CLAUDE_SEMANTIC_MIGRATION_WRITTEN=0, CLAUDE_SEMANTIC_QA_WRITTEN=0.
