# Trazabilidad hasta la ubicación final · registro de intentos

- **Modelo y modo:** todo con `deepseek-v4-pro` y `stream=true`.
- **Topes:** 8 llamadas por ciclo como máximo global y 2 reintentos por subproblema como máximo.
- **Llamada extra:** la novena la autorizó la dueña como `OWNER_EXCEPTION`.

| Llamada | Subproblema | Entrada/salida (tokens) | Coste | Resultado |
|---|---|---|---|---|
| DEEPSEEK_CALL_1 | A. Backend y pruebas | 10009/11186 | $0,014086 | AUDIT_REJECT completo, sin aplicar nada. Motivos: bloques encadenados (8 SEARCH sin coincidencia); `ReceiptConfirmation.product_id` e `InventoryMovement.receipt_id` inventados; código muerto; `Any`; índice duplicado; pruebas con fixtures inexistentes y un UPDATE en SQL que se saltaba el conteo |
| DEEPSEEK_CALL_2 | A·R1 | 11769/8192 | $0,012247 | Cortada por el límite de salida (8192 por defecto). AUDIT_PASS parcial con 5 bloques aplicados: servicio, rutas, `storage_flow` y `attributed_rows`. Rechazados: modelo insertado en mitad de `ReceiptConfirmation`, bloque de imports malformado, bloques encadenados y migración cortada |
| DEEPSEEK_CALL_3 | A·R2 (`max_tokens` 32000) | 4676/6179 | $0,007410 | AUDIT_PASS parcial con 19 bloques: imports, expediente, `_putaway_trace`, catálogo (487) y guardias. Rechazados: `Mapped[UUID]` sin import, `sa.func.now()` en `bulk_insert` y pruebas que leían una lista en lugar de `{"items"}`. A agotó RETRY_MAX y se reclasificó en A2 y A3 |
| DEEPSEEK_CALL_4 | A2 (modelo y migración) + A3 (pruebas) | 4067/3435 | $0,004758 | AUDIT_PASS. Migración `0103` con ida, vuelta e ida en PostgreSQL y paridad `n10` sin diferencias nuevas |
| DEEPSEEK_CALL_5 | B (preparación de la prueba de reubicación, mypy, prueba del backfill) | 2511/4186 | $0,004734 | AUDIT_PASS. Mypy vuelve a su línea base (51) y la prueba del backfill pasa con 1 caso válido y 5 de rechazo |
| DEEPSEEK_CALL_6 | C (pantallas y E2E) | 7266/5763 | $0,008175 | AUDIT_PASS de F1 a F4. Rechazado F5: endpoints inventados (`/organization/warehouses/{id}/locations` y `/maestros/catalogos/partners`) |
| DEEPSEEK_CALL_7 | C·R1 | 1953/1474 | $0,002132 | AUDIT_PASS |
| DEEPSEEK_CALL_8 | D (rutas de Compras a Inventario, frontera de la Spec 021) | 4445/3168 | $0,004690 | AUDIT_PASS de 14 bloques. Rechazado 1: SEARCH con un prefijo `/api` y una barra que no existen |
| DEEPSEEK_CALL_9 | D·R1 (`OWNER_EXCEPTION`) | 261/93 | $0,000194 | AUDIT_PASS. Una línea de `PutAwayPage.tsx` |
| DEEPSEEK_CALL_10 | C·R2 (`OWNER_EXCEPTION` 2) | 446/313 | $0,000466 | AUDIT_PASS. La E2E nueva de `putaway.spec.ts` omitía `confirm`, `quality`, `quality APPROVED` y `accept`, y el backend respondía con razón 409 `RECEIPT_NOT_ACCEPTED`. Se insertaron las cuatro llamadas, como en `conteo-independiente.spec.ts` |

| DEEPSEEK_CALL_11 | C·A11Y (`OWNER_EXCEPTION` 3) | 381/79 | $0,000234 | AUDIT_PASS. Axe a 390 y 320 encontró un nodo grave nuevo de este ciclo (`scrollable-region-focusable` en el contenedor de la tabla de trazabilidad). Se le aplicó el patrón del repositorio (`tabIndex={0} role="region" aria-label`). Tras el cambio quedan solo los nodos previos de A11Y-IMPORT-SCROLL-REGIONS |

| DEEPSEEK_CALL_12 | MERGE. Integración con REP-10 de P1 (frontera nueva: fusión; `OWNER_EXCEPTION` 4) | 212/90 | $0,000171 | AUDIT_PASS. Las dos ramas añadían una acción de auditoría y ponían el recuento en 487; fusionado, el catálogo tiene 488 (medido), y la prueba pasa a 488 |

```text
TOTAL_CALLS=12 (8 del tope + 4 OWNER_EXCEPTION)  TOTAL_RETRIES=6  SUBPROBLEMS=7 (A, A2, A3, B, C, D, MERGE)
MAX_RETRIES_SINGLE_SUBPROBLEM=3 (C, dos de ellos con OWNER_EXCEPTION)  GLOBAL_CAP_REACHED=1  OWNER_EXCEPTION=4
TOTAL_COST=$0,059297
```

**Causas raíz del proceso:**
- Defectos atribuidos a DeepSeek:
  - SEARCH encadenados sobre su propio parche;
  - columnas y endpoints inventados.
- Defectos de Claude:
  - el límite de salida por defecto de la herramienta (8192), que ahora se fija a mano;
  - el diseño inicial, que puso las rutas en Compras, contra una frontera aprobada de la Spec 021;
  - un brief que no fijaba el endpoint de las ubicaciones.

**Implementado por Claude:** ninguna línea de producto, prueba, E2E ni migración. Claude hizo:
- las decisiones y la arquitectura;
- los briefs y la auditoría;
- la aplicación literal de los bloques aprobados;
- las mutaciones de control, siempre restauradas byte a byte;
- las sondas de Axe, fuera del repositorio;
- la regeneración mecánica de las fixtures;
- los documentos.
