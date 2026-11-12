# Trazabilidad de la importación hasta la ubicación final: evidencia

- **Delta:** `../../spec018-putaway-trace-delta.md`.
- **Decisiones:** `../SPEC018_REMAINING_DECISIONS.md`.
- **Intentos:** `ATTEMPT_LOG.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE: vínculo estructurado `receipt_putaways`, migración `0103` con backfill exacto y sin texto en la atribución |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE: el expediente muestra la colocación y la reubicación con fecha y usuario; Inventario → Put-away admite la recepción de origen |
| OWNER_READINESS_STATUS | OWNER_UAT_READY: pasos 108 a 114 de la tarjeta. `OWNER_ACCEPTED`: NO |

## Puertas de completitud

| Puerta | Estado |
|---|---|
| BACKEND_COMPLETE | `vincular_putaway`, `pendiente_de_ubicar`, `recepciones_con_pendiente` y `ubicar_desde_recepcion`. Este último bloquea la recepción, da 404 si es ajena y 409 `PUTAWAY_EXCEEDS_RECEIPT_PENDING` si se excede, y usa el motor único |
| DATABASE_COMPLETE | `receipt_putaways`, con `movement_id` único. `0103` pasa ida, vuelta e ida en PostgreSQL y `n10` no muestra diferencias nuevas entre el ORM y la base |
| MIGRATION / BACKFILL | Autorizado por la dueña. Solo liga coincidencias exactas: UBICACION, POSTED, sin revertir, primera colocación, mismo almacén y código único en la empresa. `test_receipt_putaway_backfill` prueba 1 caso ligado y 5 rechazados (ambiguo, otro almacén, revertido, reubicación y texto libre), además de la vuelta. En la base local de UAT no había candidatos (0 movimientos UBICACION) |
| API_COMPLETE | `GET /inventory/putaway/recepciones` y `POST /inventory/putaway/desde-recepcion`, en Inventario (Spec 022). El expediente añade `logistics.putaway_trace`. Son adiciones compatibles. Compras no expone ninguna ruta de put-away, como exige la guardia de la Spec 021 |
| FRONTEND / SCREEN_COMPLETE | Expediente → Ubicación → «Trazabilidad hasta la ubicación final»: recepción, producto, almacén, desde («Sin ubicar»), hacia, cantidad, fecha legible y usuario. Inventario → Put-away → «Recepción de origen» (opcional, `<código> · pendiente <n>`). No muestra ISO ni UUID |
| MENU_COMPLETE | Compras → Importaciones → expediente; Inventario → Put-away. Son menús existentes; no hay entrada nueva |
| PROCESS_COMPLETE | Recibir → contar (otra persona) → confirmar → ubicar (expediente o Inventario con recepción) → reubicar por error → ver la cadena completa |
| ROLES_COMPLETE | Ver la trazabilidad: `compras:view`. Listar recepciones pendientes: `inventario:view`. Ubicar desde una recepción: `inventario:create`, el mismo permiso que el put-away |
| AUDIT_COMPLETE | `RECEIPT_PUTAWAY_ATTRIBUTED` (movimiento, producto, cantidad y destino), más `INVENTORY_PUTAWAY` del motor. Catálogo: 487 entradas |
| SECURITY_COMPLETE | El backend filtra por la empresa del contexto: una recepción ajena da 404 (T4). No se puede exceder lo pendiente (T3, E2E 409) |
| CONCURRENCY_COMPLETE | La fila de la recepción se bloquea antes de calcular lo pendiente, y `movement_id` es único |
| E2E_COMPLETE | `importaciones.spec.ts`: fila «Sin ubicar → ubicación» de 10 unidades con fecha legible, y fila de la reubicación A → B; en total 2 filas. `putaway.spec.ts`: la recepción de origen aparece con «pendiente 50»; tras ubicar 20, el pendiente baja a 30, los saldos quedan 20 ubicados y 30 sin ubicar, y 31 da 409 |
| RESPONSIVE_COMPLETE | `importaciones.spec.ts` pasa a 1280, 390 y 320. `putaway.spec.ts` pasa entera a 1280. A 390 y 320, sus pruebas de interfaz (también el camino feliz previo de la 022) no llegan a la pantalla porque `irAPutAway` pulsa el enlace del menú lateral plegado: deuda previa E2E-PUTAWAY-NAV-MOBILE. Entrando por URL (sonda), las 11 pruebas pasan a 390 y 320 |
| ACCESSIBILITY_COMPLETE | Axe (WCAG 2.0/2.1 A y AA): 0 faltas graves a 1280; en Put-away, 0 a 1280, 390 y 320. En el expediente, a 390 y 320, `AXE_NEW_SERIOUS=0`: el contenedor nuevo se hizo enfocable (`OWNER_EXCEPTION` 3). Quedan solo los nodos previos de A11Y-IMPORT-SCROLL-REGIONS (`#diferencias` y las tablas hermanas), que no se absorben |
| DOCUMENT / REPORTING | NOT_APPLICABLE: no genera documento; la trazabilidad se ve en pantalla y queda en la bitácora |

## Pruebas

| Prueba | Resultado |
|---|---|
| `tests/test_receipt_putaway_link.py` (T1 a T6: pendiente, ubicar 60 de 100, 409 al exceder, aislamiento 404, put-away sin vínculo y auditoría) | PASS en PostgreSQL |
| `tests/test_receipt_putaway_backfill.py` (base efímera migrada a 0102 → semilla → 0103 → vuelta) | PASS en PostgreSQL |
| Mutaciones (quitar `source_location_id IS NULL` del backfill y quitar la comprobación de pendiente) | Las 2 mueren y el original se restauró byte a byte |
| Guardias de arquitectura 021 y 022, más el put-away de la 022 | 54 PASS |
| Regresión dirigida (Specs 018 a 022, Compras, catálogo, `n10` y guardias de cabeza) | 378 PASS con el diseño inicial. El único fallo nuevo, la frontera de la 021, se corrigió moviendo las rutas, y después dieron 54 PASS las guardias y las pruebas afectadas. Los 3 fallos restantes son de la línea base |
| E2E en Chrome sobre PostgreSQL con analizador real (`importaciones`, `putaway`, `receipts`, `conteo-independiente`, `inventory-confirmation`) | 24/24 a 1280. `importaciones` y `putaway`: 11/11 a 1280 tras el último cambio |
| Vitest · typecheck · lint · build | 1934/1934 · limpio · limpio · correcto |
| ruff · mypy | limpio · 51 (la línea base; ningún error nuevo) |
| OpenAPI | 2 rutas nuevas en Inventario (adición). Las fixtures del frontend se regeneraron |
| Suite completa de backend en PostgreSQL, con analizador real | 5343 PASS, 18 skip y 19 fallos. 14 de ellos son de Gobierno (`gov_proc08`, `gov_proc10`): «la fecha del acto no puede ser futura», porque `tests/proc08_ayudantes.py` usa `datetime.now(UTC).date()` y la suite pasó por las 20:00–24:00 de Caracas, cuando la fecha UTC ya es la del día siguiente. Al repetirlos a las 00:16 de Caracas: 14 PASS. Los 5 restantes son la línea base (`gobierno_integridad`, `n10`, `naive_datetime` y dos de `spec019_receipt`). NEW_FAILURES = 0 |

## Deudas que deja (no absorbidas)

- **E2E-PUTAWAY-NAV-MOBILE.** `e2e/putaway.spec.ts`, ayudante `irAPutAway`: navega pulsando el menú lateral, que está plegado a 390 y 320. Es previa a este ciclo y no es un fallo del producto: entrando por URL, la pantalla funciona y pasa Axe.
- **A11Y-IMPORT-SCROLL-REGIONS.** Previa; sin cambios.
- **Estados §3 y zona temporal.** Decididos por la dueña y sin construir.
- **Zonas A a E.** SPONSOR_VALIDATION_REQUIRED.
