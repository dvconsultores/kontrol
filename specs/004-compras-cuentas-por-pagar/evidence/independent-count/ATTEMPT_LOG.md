# Conteo independiente · registro de intentos por subproblema

Todo con `deepseek-v4-pro` y `stream=true`. **Presupuesto:** objetivo 2 llamadas, máximo 4, y 2 reintentos por subproblema. **Usado:** 4 llamadas y 3 reintentos, en 7 envíos. Las llamadas 3 y 4 se justifican aparte: la 3 es una frontera técnica nueva (otras E2E) y la 4 una causa raíz nueva medida en Chrome.

| Subproblema | Envío | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| A. Backend, migración y pruebas (llamada 1) | 1 | 13388/5393 | $0,010516 | Producto, migración (entonces `0100`; ver E), catálogo, guardias y endpoints: AUDIT_PASS y aplicados. Rechazado: dos bloques que no cambiaban nada, la adaptación IC-08 que faltaba, y pruebas con tablas o columnas adivinadas y un `skip` incondicional |
| A | 1·R1 | 9384/8224 | $0,011237 | IC-08 (los conteos pasan a `uab`) y la prueba nueva: AUDIT_PASS. 88 PASS en PostgreSQL. Quedaba un E402 de ruff |
| A | 1·R2 (dentro del envío 2·R1) | — | — | E402 corregido. Ruff limpio |
| B. Pantalla y E2E nueva (llamada 2) | 2 | 7174/4349 | $0,006904 | Aplicados el tipo, los imports, el aviso y la sección de política. Rechazado: `useQuery.onSuccess` (no existe en TanStack v5), una E2E con `any`, un endpoint inventado `GET /orders/{id}/lines`, `await marca()`, una aserción más débil y el desbordamiento sin `expect.poll` |
| B | 2·R1 | 4006/3098 | $0,004438 | AUDIT_PASS. typecheck y lint limpios |
| C. Adaptar las E2E existentes (llamada 3, NEW_TECHNICAL_BOUNDARY) | 3 | 3602/1694 | $0,003041 | AUDIT_PASS. `receipts`, `inventory-confirmation` e `importaciones` cuentan con un segundo usuario real (`verificadorDeEscenario`) |
| D. Arnés de sesión (llamada 4, NEW_ROOT_CAUSE) | 4 | 723/161 | $0,000455 | Medido: la E2E nueva entra con dos usuarios. `_cadenaDeSesion` guardaba la única cookie del navegador en el estado de todos, y `importaciones` siguiente actuaba como el segundo usuario (`Emitido por ic-…`). Corrección: `enElNavegador.clear()` antes de registrar al usuario que entra. AUDIT_PASS; 14/14 E2E |
| E. Topología Alembic (llamada extra autorizada por la dueña) | 5 | 797/489 | $0,000772 | P1 publicó `0100_gov_ctl05_rendicion` desde `0099`. La migración de este ciclo, sin publicar, se reencadena como `0101_receipt_count_independence` detrás de la de P1, y el catálogo pasa a 476 (475 de P1 + 1). AUDIT_PASS |

**Total:** 8 envíos, $0,037363. Hubo 5 llamadas: la 5.ª, extra, la autorizó la dueña por AskUserQuestion después de agotar el presupuesto de 4. Ningún subproblema superó 2 reintentos (A: 2; B: 1; C: 0; D: 0).

**Implementado por Claude:** ninguna línea de producto, prueba, migración ni QA. Claude hizo:
- la lectura de autoridad y la pregunta a la dueña;
- el contrato y la auditoría;
- la regeneración mecánica de las fixtures con `qa/fixtures_de_frontend.py`;
- las mediciones con sondas fuera del repositorio;
- los documentos.

**Incidencia de proceso:** en varios envíos el puente avisó de que no pudo garantizar una copia byte a byte. En el envío 1 hubo una desviación real en un fragmento de ejemplo de Ventas, que no afectó a la propuesta.
