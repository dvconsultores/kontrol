# Confirmación completa: evidencia

- **Delta:** `../../spec021-confirmation-completeness-delta.md`.
- **Reproducción previa:** `REPRODUCTION.md`.
- **Intentos:** `ATTEMPT_LOG.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE: una sola validación de servicio de la Spec 021 (`validar_completitud_de_confirmacion`) antes de cualquier mutación, con la autoridad de lo aceptado en `_base_aceptada`. Sin migración |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE: la confirmación decide el 100 % de lo aceptado o no hace nada. La pantalla reparte cada línea entre disponible y rechazada y muestra lo pendiente por decidir |
| OWNER_READINESS_STATUS | Pasos 152 a 159 de la tarjeta. La UAT local (`kuat`) se migró a `0108` (la cabeza de P1 tras la fusión con BUD-03/04) y tiene el backend y el frontend arriba. Humo autenticado: `confirmacion-completa.spec.ts` contra la UAT, 1/1 (23:12, Caracas), con el residuo rechazado y el reparto completo confirmado. `OWNER_ACCEPTED`: NO |

## Puertas de completitud

| Puerta | Estado |
|---|---|
| BACKEND_COMPLETE | `confirmar_inventario` sigue siendo atómica y de una sola vez. Primero valida, sin mutar nada: línea de la recepción, destino, cantidad mayor que 0, exceso sobre lo aceptado y faltante en cualquier línea con aceptado mayor que 0. Después reclasifica. El tope antiguo contra lo recibido, que se comprobaba dentro del bucle, desaparece: la suma ya no se duplica |
| DATABASE_COMPLETE | No aplica: `MIGRATION_REQUIRED=0`. Sigue habiendo una sola cabeza |
| API_COMPLETE | `POST …/confirmacion-inventario` añade el error 422 `RECEIPT_CONFIRMATION_INCOMPLETE`, con `details.lines[]` (`receipt_line_id`, `product_code`, aceptado, decidido y pendiente). El exceso conserva el código canónico `CONFIRMED_EXCEEDS_RECEIVED` (409), ahora medido contra lo aceptado. `GET …/conciliacion` añade `product_code`, `product_name`, `base_quantity_accepted` y `pending_decision_base`. Las respuestas son `dict`: OpenAPI y fixtures sin cambios |
| FRONTEND / SCREEN_COMPLETE | Inventario → Confirmación de inventario:<br>• producto por código y nombre (antes, un trozo de UUID);<br>• columnas «Aceptado (base)» y «Pendiente por decidir»;<br>• por línea, «Cantidad aceptada», «A disponible», «Rechazada» y «Motivo del rechazo», con «Pendiente por decidir: X» y «Excede lo aceptado en X.» en vivo.<br>El botón se deshabilita mientras el reparto no está completo, y el mensaje del backend se muestra tal cual |
| MENU_COMPLETE | Inventario → Confirmación de inventario (menú existente) |
| PROCESS_COMPLETE | Recepción → aceptación → conteo independiente → reparto completo → confirmación → disponible y rechazado. Con un residuo, la confirmación se rechaza sin tocar nada |
| FIELDS_COMPLETE | Aceptado, a disponible, rechazada, motivo y pendiente por decidir |
| ROLES_COMPLETE | `inventario:confirm` para confirmar e `inventario:view` para conciliar, como hasta ahora. No hay acciones nuevas |
| AUDIT_COMPLETE | Sin eventos nuevos. El éxito emite `RECEIPT_INVENTORY_CONFIRMED`; un intento rechazado no audita nada, como los demás rechazos de la confirmación (probado) |
| SECURITY / ISOLATION_COMPLETE | Una recepción de otra empresa da 404 y una línea de otra recepción, 404. En ambos casos no se muta nada (probado) |
| CONCURRENCY_COMPLETE | Con el bloqueo de fila existente, de dos confirmaciones simultáneas solo una completa y la otra recibe `ALREADY_CONFIRMED`: un solo registro, un solo movimiento y el saldo una sola vez. Probado con `tests/concurrency.carrera`, que fuerza el choque en PostgreSQL |
| PLANNING_COMPATIBILITY | La fórmula de la Spec 015 no cambia. Tras una confirmación válida, `received_unconfirmed` pasa a 0 y el disponible sube en lo liberado. Con un residuo, `received_unconfirmed` se conserva |
| E2E_COMPLETE | `e2e/confirmacion-completa.spec.ts`: residuo bloqueado en la pantalla y en la API, cero mutación, exceso, reparto completo, saldos, planificación sin doble cuenta y segunda confirmación imposible |
| RESPONSIVE_COMPLETE | 1280, 390 y 320, sin desplazamiento horizontal |
| ACCESSIBILITY_COMPLETE | Axe (WCAG 2.0, 2.1 y 2.2, niveles A y AA) en tres momentos (inicio, residuo y confirmada) y a las tres anchuras: `AXE_NEW_SERIOUS=0` |

## Pruebas

| Prueba | Resultado |
|---|---|
| `tests/test_spec021_confirmation_completeness.py`, 12 pruebas:<br>• caso fundamental 100/80/20 (50+10 rechazado y después 60+20);<br>• exceso, negativo y cero, línea omitida;<br>• línea con aceptado 0, caja de 12 en unidad base;<br>• línea ajena, empresa ajena;<br>• segunda confirmación, recepción no aceptada;<br>• conciliación y concurrencia | 12/12 en PostgreSQL |
| `tests/test_spec015_received_unconfirmed.py`: la prueba que fijaba el residuo pasa a afirmar el rechazo y que lo recibido se sigue contando | 10/10 |
| Suites de la 021 (confirmación, arquitectura y conteo independiente) | Verdes, sin cambios. Las guardias de arquitectura (`GATE-021-09` y las demás) se cumplen |
| Suites afectadas (put-away, 018, 019, 022, 023, 033, suministro abierto, catálogo de lectura) | 133 PASS. Solo fallan los 2 de la línea base de `spec019_receipt` |
| Mutaciones (todas mueren; original restaurado byte a byte) | Sin validación: 6 fallos. Sin el rechazo del faltante: 4. Recibido en lugar de aceptado: 4 |
| Vitest (Node 22) · typecheck · lint · build | `ConfirmacionPage.test.tsx` 5/5. Suite completa 1992/1992 a la primera, sin repetir el fallo intermitente del ciclo anterior (`OBS_FRONTEND_FLAKE_REPRODUCED=0`). Typecheck y lint limpios; build correcto |
| E2E `confirmacion-completa`, `conteo-independiente` e `inventory-confirmation` | 5/5 a 1280. A 390 y 320, `confirmacion-completa` y `conteo-independiente` pasan; `inventory-confirmation` no (ver deudas) |
| Regresión E2E de Compras e Inventario (15 specs) | 53/53 a 1280, con las 2 specs corregidas en B·R2 |
| ruff · mypy | Limpio · 157, igual que HEAD |
| OpenAPI | Sin cambios: fixtures regeneradas, 0 diferencias |
| Reconciliación con P1 (`f100c34`, BUD-03/04 con la migración `0108`) | Fusión ordinaria sin conflictos; P1 no toca ningún fichero del ciclo. Una sola cabeza (`0108`); fixtures regeneradas con 0 diferencias. Sobre el árbol fusionado: confirmación completa, arquitectura de la 021, recibido sin confirmar, `gov_bud03_04`, el runner de Gobierno, `n10` y las marcas de tiempo de las migraciones de la 018 dan 54 PASS. El único fallo es `n10`, con las 6 diferencias de la línea base. Ruff limpio, typecheck limpio y `ConfirmacionPage` 5/5 |
| Suite completa de backend en PostgreSQL (una vez, con ClamAV) | **Entrada** (`5b7e1b9`, base `ktestbase`, de 18:52 a 20:56 en Caracas): 5453 PASS, 19 SKIP, 4 FAIL (`n10` y `naive_datetime`, con `spec019_receipt` ×2) → `ENTRY_PG_FAILURES=4`. **Final** (árbol del ciclo, `ktest`, de 20:56 a 22:56): 5465 PASS, 18 SKIP, 5 FAIL. Son 12 PASS más, las 12 pruebas nuevas. Los 4 fallos de la entrada se repiten y el quinto es `gobierno_integridad_runner` (OC20 = −15). Atribución: el código de entrada falla sobre `ktest` y el del ciclo pasa sobre `ktestbase`. La causa eran 5 esquemas `t_*` huérfanos del arnés en `ktest`, de corridas interrumpidas: OC20 cuenta disparadores en toda la base, 5 × 3 = 15 de más. Se soltaron en la base de QA y la prueba pasó 3/3 a las 23:03, dentro de la franja. `FINAL_PG_FAILURES=4` (efectivos, el mismo conjunto que la entrada) · `NEW_BACKEND_FAILURES=0` · `OBS_PG_HARNESS_ORPHAN_SCHEMAS=5` |
| GOV-TEST-UTC-DATE | La suite final y la repetición de Gobierno corrieron dentro de la franja de 20:00 a 24:00. Gobierno no tuvo ningún fallo atribuible a la fecha: `GOV_TEST_UTC_DATE=PASS_IN_WINDOW`. No es puerta |

## Dependencia de orden de `inventory-confirmation` (E2E-INVCONF-ORDER-DEPENDENCY)

- Reproducida antes de la reparación: ejecutada sola sobre una base recién sembrada, 3/3 fallos.
- Se corrigió solo el arnés: si no hay almacén, crea sucursal y almacén.
- Después: 3/3 a 1280 sobre una base recién sembrada. **Pagada.**

## Deudas (no absorbidas)

- **E2E-INVCONF-DESKTOP-NAV.** `inventory-confirmation.spec.ts` llega a la pantalla con un clic en el enlace del menú lateral. A 390 y 320 el menú está plegado y el clic agota el tiempo. Es previa y solo del arnés; la cobertura responsive del flujo la da `confirmacion-completa`, que entra por ruta.
- **REQUISITION-PLAN-SNAPSHOT.** Sigue abierta.
- **Pendientes de ciclos anteriores:** ORDENES-UI-ETIQUETAS, AXE-BUTTON-BUSY-TRANSITION, E2E-PRINT-BLOB-BLOQUEADO, las zonas A–E y las deudas de Gobierno.
