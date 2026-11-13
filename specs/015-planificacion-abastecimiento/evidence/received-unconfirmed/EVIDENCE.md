# Recibido sin confirmar en la proyección: evidencia

- **Delta:** `../../spec015-received-unconfirmed-projection-delta.md`.
- **Autoridades y prueba de que no hay doble cuenta:** `RECEIVED_UNCONFIRMED_AUTHORITY.md`.
- **Intentos:** `ATTEMPT_LOG.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE: derivado sin migración. `purchasing/open_supply.py` es la autoridad única: `recibido_sin_confirmar` para un lote y `en_camino` para el suministro abierto y lo recibido en una sola sentencia |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE: la planificación cuenta lo aceptado y pendiente de confirmar en el almacén de la recepción, sin pedirlo de nuevo ni contarlo dos veces. Se ve en la necesidad y en el plan de la requisición |
| OWNER_READINESS_STATUS | Pasos 144 a 151 de la tarjeta. `OWNER_ACCEPTED`: NO |

## Puertas de completitud

| Puerta | Estado |
|---|---|
| BACKEND_COMPLETE | El mismo `compute_plan` calcula `projected_available = available + open_supply + received_unconfirmed` y añade `received_unconfirmed`. `condition_met`, la fórmula de la sugerida y `coverage_days` conservan su forma. La necesidad deriva `received_unconfirmed` (proyectado − disponible − suministro abierto) en `trigger` y en `current` |
| DATABASE_COMPLETE | No aplica: `MIGRATION_REQUIRED=0` y `DERIVATION_INSUFFICIENT=0`. Cabeza `0106`, sin cambios |
| API_COMPLETE | `GET /planning/plan` y `/planning/plans` añaden `received_unconfirmed`. La necesidad lo añade en `trigger` y `current`. Responden `dict`: OpenAPI y fixtures sin cambios |
| FRONTEND / SCREEN_COMPLETE | Necesidad: «En recepción (pendiente de confirmar)» en «Por qué se generó» y en «Situación actual». Requisición (plan en vivo): «En recepción (pendiente de confirmar)» y «Disponible proyectado». No se le llama stock y no hay UUID |
| MENU_COMPLETE | Compras → Necesidades de reposición, Compras → Requisiciones e Inventario → Confirmación de inventario (menús existentes) |
| PROCESS_COMPLETE | Necesidad → orden con destino (suministro abierto) → recepción aceptada (pasa a en recepción) → conteo independiente → confirmación (pasa a disponible). El proyectado y la sugerida no cambian y la necesidad no se duplica |
| FIELDS_COMPLETE | Disponible, suministro abierto, en recepción (pendiente de confirmar), disponible proyectado, punto de reorden y cantidad sugerida |
| ROLES_COMPLETE | Lectura con `compras:view`, como hasta ahora. No hay acciones nuevas |
| AUDIT_COMPLETE | Sin eventos nuevos: ni cálculos ni derivaciones se auditan. La recepción, la aceptación y la confirmación conservan su auditoría |
| SECURITY / ISOLATION_COMPLETE | La empresa sale del contexto. Una recepción de otra empresa sobre un almacén propio no suma (T7) |
| CONCURRENCY_COMPLETE | Sin bloqueos nuevos. El suministro abierto y lo recibido se leen en una sentencia (`UNION ALL`), así que una aceptación concurrente no se cuenta dos veces. Una confirmación concurrente puede faltar durante un tick, pero no se duplica (`RECEIVED_UNCONFIRMED_AUTHORITY.md`) |
| INVENTORY_SEMANTICS | `RECEIVED_UNCONFIRMED_CHANGES_STOCK=0`, `CREATES_INVENTORY_MOVEMENT=0`, `CHANGES_COST=0` y `CHANGES_PUTAWAY=0` (T9) |
| E2E_COMPLETE | `e2e/recibido-sin-confirmar.spec.ts`, 10 pasos sobre PostgreSQL efímero con ClamAV. Recorre necesidad, orden de 4, recepción aceptada de 3, conteo por otra persona, confirmación en la pantalla y aislamiento del segundo almacén, con la sugerida y el proyectado constantes |
| RESPONSIVE_COMPLETE | 1280, 390 y 320, sin desplazamiento horizontal |
| ACCESSIBILITY_COMPLETE | Axe (WCAG 2.0, 2.1 y 2.2, niveles A y AA) en el detalle de la necesidad, en tres momentos y a las tres anchuras: `AXE_NEW_SERIOUS=0` |

## Pruebas

| Prueba | Resultado |
|---|---|
| `tests/test_spec015_received_unconfirmed.py`, T1 a T10 | 10/10 en PostgreSQL. Cubre: secuencia 100 → 40 → 30 con confirmaciones, aceptación parcial, confirmación con rechazo, confirmación que no lo decide todo, estados que no cuentan, varios almacenes, aislamiento, que no se repone lo recibido, que no tiene efecto en el inventario y el detalle de la necesidad |
| Mutaciones (todas mueren; originales restaurados byte a byte) | Sin filtro de confirmación: 4 fallos. Sin filtro de almacén: 1. Proyección sin lo recibido: 3 |
| Pruebas existentes afectadas (planificación, suministro abierto, recepción, Specs 019, 021, 022 y 023, `n10`) | Solo la línea base: `spec019_receipt` ×2 y `n10` con las 6 diferencias de `import_*.created_by` |
| Vitest · typecheck · lint · build | Compras 141/141. Suite completa 1974/1974: la primera corrida tuvo 1 fallo que no quedó identificado, intermitente y sin atribuir; la segunda, todo en verde. Typecheck y lint limpios; build correcto |
| E2E `recibido-sin-confirmar`, `suministro-abierto` y `reposicion` | Verdes a 1280, 390 y 320 |
| Regresión E2E de Compras e Inventario (13 specs, incluida `inventory-confirmation`) | 51/51 a 1280 |
| ruff · mypy | Limpio · 157, igual que HEAD |
| OpenAPI | Sin cambios (fixtures regeneradas: 0 diferencias) |
| Suite completa de backend en PostgreSQL (una vez, con ClamAV) | 5436 PASS, 18 SKIP, 5 FAIL, de 14:52 a 16:50 (Caracas). Son 10 PASS más que en el ciclo anterior: las nuevas. Los 5 fallos son la línea base exacta: `gobierno_integridad_runner`, `n10` (solo las 6 diferencias de `import_*.created_by`), `naive_datetime` y `spec019_receipt` ×2. `NEW_BACKEND_FAILURES=0` |
| GOV-TEST-UTC-DATE | La suite corrió fuera de la franja de 20:00 a 24:00: `GOV_TEST_UTC_DATE=NOT_MEASURED_THIS_CYCLE`. No es puerta |

## Deudas (no absorbidas)

- **RECEIPT-CONFIRMATION-RESIDUE (Spec 021).** La confirmación es de una sola vez por recepción. Lo aceptado que no se libera ni se rechaza queda en `RECIBIDO` en una recepción CONFIRMADA y ya no puede confirmarse. La planificación no lo cuenta como pendiente.
- **E2E-INVCONF-ORDER-DEPENDENCY.** `inventory-confirmation.spec.ts` toma el primer almacén de la lista. Si se ejecuta la primera sobre una base efímera recién sembrada, todavía no hay almacenes y falla. En su orden habitual pasa (51/51). Es anterior a este ciclo.
- **REQUISITION-PLAN-SNAPSHOT.** La instantánea guardada del plan de una línea de requisición (`requisition_line_plans`) no guarda lo recibido sin confirmar ni el proyectado. La pantalla lo explica con el plan en vivo. Persistirlo exigiría migración y no se necesitaba.
- **Pendientes de ciclos anteriores:** ORDENES-UI-ETIQUETAS, AXE-BUTTON-BUSY-TRANSITION y las zonas A–E.
- **GOV-TEST-UTC-DATE.** Es externa a P2 y no es puerta de este producto.
