# Spec 018 · delta: programar la descarga desde la importación

Encargo `SPEC018_PROGRAMAR_DESCARGA`, del 2026-11-11. Spec dueña del proceso: 018. La autoridad del dato es la Spec 019 (Recepciones). Autoridad: `evidence/PROGRAMAR_DESCARGA_AUTHORITY.md`. Evidencia: `evidence/unloading-schedule/`.

## Contrato

- **UD-01. Fuente única.** `goods_receipts.unloading_scheduled_at`. Sin migración.
- **UD-02. Autoridad: Recepciones.**
  - `purchasing.service.programar_descarga(db, *, company_id, receipt_id, unloading_scheduled_at, actor)`.
  - Bloquea la fila con `with_for_update().execution_options(populate_existing=True)`.
  - Una recepción de otra empresa da 404 `RECEIPT_NOT_FOUND`.
  - Si el estado no es DRAFT ni CONFIRMED, da 409 `RECEIPT_NOT_OPEN`: «Solo una recepción abierta admite programar la descarga.»
  - Guarda el valor (un nulo borra la programación) y audita `RECEIPT_UNLOADING_SCHEDULED` con el valor anterior y el nuevo (ISO o nulo).
- **UD-03. API.** `POST /purchasing/receipts/{receipt_id}/unloading-schedule`, con body `{unloading_scheduled_at: InstanteDeEntrada | null}` y permiso `compras:create`. Responde con el dict de la recepción. Importaciones no duplica el endpoint: el expediente llama al de Recepciones, como ya hace con el arribo.
- **UD-04. Expediente.** `logistics.receipts[]` añade `unloading_scheduled_at` y `can_schedule_unloading`, que es verdadero cuando el estado es DRAFT o CONFIRMED.
- **UD-05. Pantalla.**
  - **Expediente:**
    - el alta de la recepción pide «Descarga programada» (hora de Caracas);
    - cada recepción muestra «Descarga programada: <fecha y hora legible>», o «Sin programar»;
    - la acción «Programar descarga de <código>» (fecha y hora, guardar) está disponible si se puede programar.
  - **Recepciones:** columna «Descarga programada».
- **UD-06. Concurrencia.** Cada guardado es atómico bajo el bloqueo de fila. Dos usuarios a la vez: gana el último, y la auditoría conserva los dos cambios con su antes y después.

## Estado

CONVERGED el 2026-11-11. Implementado por DeepSeek y auditado por Claude: 3 llamadas y 2 reintentos, $0,013. Sin migración. Evidencia en `evidence/unloading-schedule/`.

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T018-UD-A Backend y pruebas | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `purchasing/{service,api}.py`, `imports/service.py`, catálogo, `tests/test_spec019_unloading_schedule.py` | pytest en PostgreSQL | UD-01 a UD-04 y UD-06 en PASS |
| T018-UD-B Pantalla y E2E | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `ImportacionRecepcion.tsx`, `tipos.ts`, `RecepcionesPage.tsx`, `e2e/importaciones.spec.ts` (se extiende la E2E dueña del flujo para no duplicar su preparación) | E2E en Chrome sobre PostgreSQL | PASS a 1280, 390 y 320 |
| T018-UD-C Autoridad, delta, evidencia, matriz y tarjeta | CLAUDE | n-a | NO | n-a | n-a | documentos | — | matriz recontada |
