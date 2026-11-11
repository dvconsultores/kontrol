# Spec 021 · delta: conteo independiente en la recepción

Encargo `SPEC018_CONTEO_INDEPENDIENTE`, del 2026-11-11. Spec dueña: 021, conteo y confirmación del inventario recibido. Autoridad y decisión de la dueña: `INDEPENDENT_COUNT_AUTHORITY.md`. Evidencia: `evidence/independent-count/`.

## Regla

**IC-01. Receptor ≠ contador.** Mientras el control esté activo en la empresa, cuentan como receptores de una recepción quien la registró (`goods_receipts.created_by`) y quien la aceptó (`goods_receipts.record_issued_by`). Ninguno de los dos puede registrar el conteo de sus líneas. La comparación se hace por el id persistido del usuario, nunca por nombres. Un actor nulo no coincide con nada.

**IC-02. Sin conteo no hay confirmación.** Con el control activo, cada línea que entra en `confirmar_inventario` tiene que estar contada (`counted_base_quantity` no nulo) y por alguien que no sea receptor. Si no, el control se saltaría con no contar. Es lo que pide la etapa 13 de la Spec 021: «una vez conciliado, confirmar inventario».

**IC-03. Configurable, activo por defecto.**
- Columna nueva: `companies.receipt_count_same_user_allowed`, booleana, `NOT NULL`, por defecto `false`. `false` significa que el control está activo.
- Endpoints: `GET /purchasing/settings/receipt-count` (permiso `compras:view`) y `PUT /purchasing/settings/receipt-count` (permiso `compras:approve`).
- Es el patrón hermano de `GET/PUT /sales/settings/reservation`.
- Cada cambio se audita como `COMPANY_RECEIPT_COUNT_POLICY_CHANGED`, con el valor anterior y el nuevo (`before`/`after`).
- No es retroactivo: las recepciones ya confirmadas no se revisan. Una recepción abierta se valida con la política vigente en el momento de confirmar.

**IC-04. Rechazo sin efectos.**
- Errores estables:
  - `409 INDEPENDENT_COUNT_REQUIRED`: «El conteo debe hacerlo una persona distinta de quien registró o aceptó la recepción.»
  - `409 COUNT_REQUIRED_BEFORE_CONFIRMATION`: «Cada línea debe contarse antes de confirmar el inventario.»
- Las comprobaciones de la confirmación se hacen **antes** de cualquier movimiento: no queda inventario confirmado, ni cantidades alteradas, ni movimientos.
- Las denegaciones no se auditan, porque el contrato de auditoría vigente audita hechos y no intentos de negocio rechazados. Lo que sí se audita: `RECEIPT_LINE_COUNTED` con el actor, `RECEIPT_INVENTORY_CONFIRMED` con el actor y el cambio de política.

**IC-05. Concurrencia.** `registrar_conteo` y `confirmar_inventario` bloquean la fila de la recepción con `select … with_for_update().execution_options(populate_existing=True)`, que es el patrón del módulo. Así, un conteo y una confirmación concurrentes sobre la misma recepción se serializan, y la confirmación valida el `counted_by` definitivo dentro de su transacción.

**IC-06. Interfaz.** En Inventario → Confirmación:
- un aviso visible cuando el control está activo;
- el mensaje de negocio del backend en el error;
- la sección «Política de conteo», con la casilla «Permitir que quien recibe cuente la mercancía», visible solo con el permiso de `PUT`.

**IC-07. Pruebas existentes.** No se debilita el control para mantenerlas en verde. Se adaptan para que cuente otro usuario real del arnés: `uab` en el backend y el verificador de escenario en la E2E.

## Estado

CONVERGED el 2026-11-11. Implementado por DeepSeek y auditado por Claude: 4 llamadas y 3 reintentos, $0,037. Backend PASS en PostgreSQL. E2E 14/14 en Chrome. El flujo nuevo pasa a 1280, 390 y 320 con Axe a 0. Evidencia en `evidence/independent-count/`.

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T021-IC-A Backend, migración y pruebas | DEEPSEEK | deepseek-v4-pro | SÍ (segregación) | YES | 2 | `organization/models.py`, `purchasing/{service,api}.py`, migración, catálogo, guardias, `tests/test_spec021_independent_count.py`, `tests/test_spec021_confirmation.py` | pytest en PostgreSQL | IC-01 a IC-05 en PASS; 021 sin regresión |
| T021-IC-B Pantalla y E2E | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `ConfirmacionPage.tsx`, tipos, `e2e/conteo-independiente.spec.ts`, E2E adaptadas | E2E en Chrome sobre PostgreSQL | PASS a 1280, 390 y 320 |
| T021-IC-C Autoridad, delta, evidencia, matriz y tarjeta | CLAUDE | n-a | NO | n-a | n-a | documentos | — | matriz recontada |

El control es de segregación (`SECURITY_SENSITIVE`). La dueña fijó la regla y Claude el contrato exacto. DeepSeek ejecuta un cambio local y cerrado, como asigna el encargo (precedencia 1).
