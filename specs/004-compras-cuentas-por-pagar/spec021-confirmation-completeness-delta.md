# Spec 021 · delta: confirmación completa, sin cantidades huérfanas

- **Encargo:** `RECEIPT_CONFIRMATION_RESIDUE`, del 2026-11-13.
- **Spec dueña:** 021, confirmación del inventario recibido (ciclo en `spec021-implementation-cycle.md`).
- **Consumidora:** Spec 015 (planificación). Solo lee el resultado.
- **Deuda que paga:** RECEIPT-CONFIRMATION-RESIDUE, abierta por `RECEIVED_UNCONFIRMED_PROJECTION`.
- **Evidencia:** `evidence/confirmation-completeness/`.

## Defecto

`confirmar_inventario` puede decidir menos de lo aceptado y aun así marcar la recepción CONFIRMADA. Lo que no se decidió queda en `RECIBIDO` para siempre, porque la confirmación es de una sola vez (`ALREADY_CONFIRMED`).

Reproducido sobre PostgreSQL antes de tocar nada: con 80 aceptadas y una decisión de 50 a DISPONIBLE más 10 a RECHAZADO, la recepción queda CONFIRMADA, quedan 20 en `RECIBIDO`, la segunda confirmación da `ALREADY_CONFIRMED` y la planificación ya no ve esas 20. Ver `evidence/confirmation-completeness/REPRODUCTION.md`.

**Causa raíz.** El servicio solo acota por arriba, y contra lo **recibido** (`_base_recibida`), no contra lo aceptado: no hay cota por abajo. Además, el tope se comprueba dentro del bucle, después de reclasificar las decisiones anteriores.

## Decisión de arquitectura (fijada por el encargo y coherente con la Spec)

- **`CONFIRMATION_MODE=ATOMIC_ONE_SHOT`.** La Spec 021 dice que la cabecera tiene «dos estados y no más» (PENDIENTE → CONFIRMADA) y una prueba fija `ALREADY_CONFIRMED`. No hay fuente que pida confirmaciones parciales: `MATERIAL_DECISION_REQUIRED=0`.
- **No se crean** segunda confirmación, confirmación parcial, estado intermedio ni reapertura.
- **Se repara:** la confirmación debe decidir el 100 % de lo aceptado por línea, o falla antes de mutar nada.

## Clarificaciones (resueltas con el código)

| Pregunta | Respuesta |
|---|---|
| ¿Qué es «lo aceptado» de una línea? | Lo que la aceptación asentó en `RECIBIDO`: `coalesce(base_quantity_accepted, quantity_accepted)` cuando la línea de orden tiene `needs_inventory`; 0 en otro caso (no asentó nada). Mismo patrón que `_base_recibida` |
| ¿Por qué no se calcula dentro de `confirmar_inventario`? | `GATE-021-09` prohíbe la subcadena `quantity_accepted` en su cuerpo. El cálculo vive en un helper propio, como `_base_recibida` |
| ¿Unidades y precisión? | Todo en unidad base, con `_dec` (6 decimales, `Decimal`). Sin `float` ni tolerancias |
| ¿Qué código para el exceso? | El canónico existente, `CONFIRMED_EXCEEDS_RECEIVED` (409). Ahora se mide contra lo aceptado, que es exactamente lo que está en `RECIBIDO`. El mensaje lo dice |
| ¿Y para lo que falta? | No hay equivalente canónico: `RECEIPT_CONFIRMATION_INCOMPLETE` (422, como `NO_DECISIONS`). El mensaje: «Debe decidirse la totalidad de la cantidad aceptada antes de confirmar el inventario.» |
| ¿Se audita el intento rechazado? | No. La política vigente no audita ningún rechazo de la confirmación (`ALREADY_CONFIRMED`, `INCIDENTS_UNRESOLVED`…): la transacción no se confirma. La confirmación exitosa conserva `RECEIPT_INVENTORY_CONFIRMED` |
| ¿Y las reglas del motor (motivo del rechazo, matriz de transiciones)? | Siguen siendo de la Spec 023. Si fallan, la API no hace `commit` y no persiste nada |
| ¿Hace falta migración? | No. Es un invariante de servicio: `MIGRATION_REQUIRED=0` |

## Contrato

- **CCR-01. Autoridad de lo aceptado.** Un único helper de la 021 devuelve lo aceptado de una línea en base, según la clarificación 1.
- **CCR-02. Una sola vez.** La confirmación sigue siendo atómica y de una sola vez. `ALREADY_CONFIRMED`, sin reapertura.
- **CCR-03. Reparto completo.** Para cada línea de la recepción, Σ decisiones (a DISPONIBLE y a RECHAZADO) = lo aceptado.
- **CCR-04. Faltante.** Si alguna línea con aceptado mayor que 0 suma menos (o se omite), 422 `RECEIPT_CONFIRMATION_INCOMPLETE`, con `details.lines[]` = {`receipt_line_id`, `product_code`, `base_accepted`, `base_decided`, `base_pending`}.
- **CCR-05. Exceso y valores inválidos.**
  - Una línea que suma más de lo aceptado da 409 `CONFIRMED_EXCEEDS_RECEIVED`, con {`receipt_line_id`, `base_accepted`, `base_decided`}. Incluye las líneas con aceptado 0.
  - Cantidad ≤ 0: 422 `INVALID_QUANTITY`.
  - Destino desconocido: 422 `CONFIRMATION_TARGET_UNKNOWN`.
  - Línea ajena: 404.
- **CCR-06. Atomicidad.** Una única función de validación, `validar_completitud_de_confirmacion`, corre antes de cualquier mutación:
  - ningún `reclassify` ni movimiento;
  - ninguna fila `receipt_confirmations`;
  - ningún cambio de `confirmation_status`;
  - ninguna auditoría.

  El tope que hoy está dentro del bucle desaparece: no se duplica la suma.
- **CCR-07. Frontera del inventario.** Tras el fallo, saldos y movimientos quedan intactos. Tras el éxito, DISPONIBLE suma lo liberado, RECHAZADO suma lo rechazado y RECIBIDO de esa recepción queda en 0.
- **CCR-08. Estado.** Un fallo deja `confirmation_status = PENDIENTE` y el `status` de la recepción sin cambio.
- **CCR-09. Auditoría.** Sin eventos nuevos. El éxito emite `RECEIPT_INVENTORY_CONFIRMED`; el fallo no emite nada.
- **CCR-10. Aislamiento.** La recepción se resuelve por la empresa del contexto (404 si es ajena), y la línea, por la recepción (404 si es ajena).
- **CCR-11. Concurrencia.** El bloqueo de fila existente (`with_for_update`) hace que, de dos confirmaciones simultáneas, una gane y la otra reciba `ALREADY_CONFIRMED`. No hay doble movimiento, saldo ni registro.
- **CCR-12. Pantalla.** Inventario → Confirmación de inventario muestra por línea:
  - el producto por código y nombre, sin UUID;
  - «Cantidad aceptada»;
  - «A disponible» y «Rechazada», con un motivo obligatorio si es mayor que 0;
  - «Pendiente por decidir: X», calculado en vivo.

  El botón «Confirmar inventario» se deshabilita mientras alguna línea tenga pendiente distinto de 0 o exceda. Si excede, avisa al momento. El mensaje del backend se muestra tal cual. La conciliación expone `product_code`, `product_name`, `base_quantity_accepted` y `pending_decision_base`.
- **CCR-13. Compatibilidad con la planificación.**
  - La fórmula de la 015 no cambia.
  - Tras una confirmación válida, `received_unconfirmed` pasa a 0, el disponible sube en lo liberado y el proyectado conserva la consistencia.
  - La prueba de la 015 que fijaba el residuo (`test_confirmacion_que_no_decide_todo_no_queda_pendiente`) pasa a afirmar que la confirmación incompleta se rechaza y que lo recibido sigue contándose.
- **CCR-14. E2E.** Chrome sobre PostgreSQL, a 1280, 390 y 320, con Axe. Recorre: intento con residuo, rechazo, cero mutación, pendiente visible, reparto completo, confirmación, saldos y planificación.
- **CCR-15. UAT.** Pasos desde el 152 de la tarjeta.

**API:**
- `POST /purchasing/receipts/{id}/confirmacion-inventario`: mismo cuerpo, con el código nuevo de error.
- `GET …/conciliacion`: 4 campos más por ítem.
- Las dos responden `dict`: OpenAPI no cambia.

**Base de datos:** `MIGRATION_REQUIRED=0`.

## Constitution gate

```text
ONE_SHOT_CONFIRMATION_PROVEN=1 (Spec 021 §3 «dos estados y no más»; test_confirmar_dos_veces_no_duplica_nada)
ACCEPTED_QUANTITY_AUTHORITY_CLEAR=1  DECISION_QUANTITIES_CLEAR=1 (receipt_confirmations.base_quantity)
BASE_UNIT_CONVERSION_CLEAR=1 (base_quantity_accepted, congelada en la aceptación; _dec a 6 decimales)
ATOMICITY_CLEAR=1  ERROR_CONTRACT_CLEAR=1  MATERIAL_DECISION_REQUIRED=0  CONSTITUTION_GATE=PASS
```

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T021-CCR-0 Reproducción, arqueología, delta y diseño | CLAUDE | n-a | NO | n-a | n-a | documentos | sonda fuera del repo | gate PASS |
| T021-CCR-A Servicio, conciliación y pruebas (021 y 015) | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `purchasing/service.py`, `tests/test_spec021_confirmation_completeness.py`, `tests/test_spec015_received_unconfirmed.py` | pytest en PostgreSQL | CCR-01 a CCR-11 y CCR-13 |
| T021-CCR-B Pantalla, tipos, Vitest y E2E (y la dependencia de orden de `inventory-confirmation`) | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `ConfirmacionPage.tsx`, `api/types.ts`, `confirmacion.test.tsx`, `e2e/confirmacion-completa.spec.ts`, `e2e/inventory-confirmation.spec.ts`, `e2e/conteo-independiente.spec.ts` | Vitest y E2E | CCR-12, CCR-14 |
| T021-CCR-C Evidencia, tarjeta y cierre | CLAUDE | n-a | NO | n-a | n-a | documentos | — | — |

## Trazabilidad

| Requisito del encargo | Contrato | Prueba |
|---|---|---|
| §8 reproducción | — | `REPRODUCTION.md` |
| §10 y §11 invariante y validación por línea | CCR-03, CCR-04, CCR-05 | backend: faltante, exceso, negativo, línea omitida, aceptado 0, presentación (caja de 12) |
| §12 atomicidad | CCR-06, CCR-07, CCR-08 | backend: cero filas, movimientos, saldos y auditoría tras el fallo |
| §13 error | CCR-04, CCR-05 | backend (códigos y detalles) y Vitest (mensaje) |
| §14 idempotencia | CCR-02 | backend: segunda confirmación |
| §21 y §22 planificación y caso fundamental | CCR-13 | backend: 100/80/20 → 50+10 rechazado → 60+20 confirmado, con `received_unconfirmed` 80 → 0 |
| §23 línea ajena y empresa ajena | CCR-10 | backend |
| §24 concurrencia | CCR-11 | backend con `tests/concurrency.carrera` |
| §19 y §20 pantalla | CCR-12 | Vitest y E2E |
| §28 E2E | CCR-14 | `e2e/confirmacion-completa.spec.ts` |
