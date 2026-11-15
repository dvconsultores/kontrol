# CIERRE · CNT-02 Adendas, prórrogas, modificaciones y variaciones versionadas (GOV-CNT-002) · 2026-11-15

Incluye además el cierre de OBS-CNT01-BUD08-01 y OBS-CNT01-TRE09-01 (delta `specs/gov-cnt-01-contrato-orden/cnt01-moneda-cobertura-delta.md`).

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:** Gobierno · Contratos › Contratos y órdenes › (contrato formalizado) › enlace «Modificaciones (n)».
- **WHAT_CAN_USER_DO:**
  - ver las condiciones originales, que no cambian, junto a las vigentes en una fecha;
  - consultar el historial lineal;
  - preparar un borrador de adenda, prórroga, modificación o variación, con fechas, motivo, plazo, cambio de monto, condiciones, referencia y documento;
  - asignar cobertura CDP adicional;
  - formalizarlo con firmante (Firmar × Contrataciones, MFA), con el límite comprobado contra el monto efectivo nuevo y la conversión TRE-09;
  - descartar el borrador;
  - consultar la ficha sellada.
- **OWNER_UAT_READY:** YES. **OWNER_ACCEPTED:** NO (solo lo concede la dueña).
- **PRODUCT_STATUS:** OWNER_UAT_READY, con 10/10 compuertas aplicables (REPORTING NOT_APPLICABLE).
- **MISSING_GATES:** ninguna.

## Resultado (árbol final convergido con CNT-04 de P1)

| Comprobación | Resultado |
|---|---|
| PG dirigidas: CNT-02 (12) y delta CNT-01 (7) | 19/19 |
| PG completa, una vez sobre el árbol final `b3d3668` | 5610 en verde, 4 en rojo y 18 omitidas. Los 4 rojos son los de la línea base: n10 `import_*`, naive_datetime y spec019 ×2. NEW_BACKEND_FAILURES=0 |
| Mutaciones M1–M6 | 6/6 muertas |
| Vitest (Node 22) | 2083/2083. `AsyncButton` (FR-004) es intermitente bajo carga y anterior al ciclo: OBS-VITEST-ASYNCBUTTON-FLAKY |
| tsc, eslint y build | OK |
| E2E con `gobierno-contratos-modificaciones` y la regresión de `gobierno-contratos` (CNT-01 y CNT-04), a 1280, 390 y 320 px y con Axe | 2/2 sin reintentos (run `r20261115t192617p3824089n83f9d2`), AXE_NEW_SERIOUS=0 |
| ruff | limpio |
| mypy | 157 errores (línea base) |
| Alembic | up/down(0116)/up; cabeza única `0118_gov_cnt02_modificaciones`, reencadenada tras `0117_gov_cnt04_supervisor` de P1 |
| OpenAPI | 7 rutas nuevas; fixtures regeneradas solo con adiciones |

## Métricas tras la fusión (recuento desde la fuente)

- **Universo:** 1342 compuertas. PASS 409, N/A 74, aplicables 1268.
- **OWNER_UAT_READY:** 40/122 (CNT-01, CNT-02 y CNT-04). OWNER_ACCEPTED=0.

## Abierto

- **OQ-CNT02-01:** posibles topes del Reglamento (N12) sobre aumentos o plazos de solicitud. No hay copia local y no se inventan.
- **OQ-CNT02-02:** anular una modificación formalizada. No se construye ANULADA: se rectifica con otra modificación.
- **OQ-CNT02-03:** modificar un contrato con el plazo vencido. Se bloquea, por ser lo más conservador; la dueña puede relajarlo.
- **OBS-CNT02-LIBERACION-01:** una reducción no libera cobertura de la CDP. Liberarla exigiría una «liberación» versionada, y eso lo decide la dueña.
- **OBS-CNT01D-01/02:** no bloquean; detalle en el delta de CNT-01.
- **OBS-VITEST-ASYNCBUTTON-FLAKY:** la prueba usa un temporizador de 20 ms frente a dos clics y es anterior a este ciclo.

## DeepSeek

14 llamadas a deepseek-v4-pro, con 6 extra autorizadas por la dueña. 5 reintentos semánticos y un coste de $0,144272. Detalle en ATTEMPT_LOG.md.
