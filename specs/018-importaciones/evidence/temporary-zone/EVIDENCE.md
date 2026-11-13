# Zona temporal de recepción o validación (§2): evidencia

- **Delta:** `../../spec018-temporary-zone-delta.md`.
- **Intentos:** `ATTEMPT_LOG.md`.
- **Decisión de la dueña:** `../SPEC018_REMAINING_DECISIONS.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE: `goods_receipts.temporary_location_id` (migración `0105`), una referencia estructurada a una `warehouse_location` existente |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE: se registra y cambia en el expediente y en Recepciones, se ve igual en las dos pantallas, se conserva al confirmar y no se confunde con la ubicación final |
| OWNER_READINESS_STATUS | Pasos 126 a 133 de la tarjeta. `OWNER_ACCEPTED`: NO |

## Puertas de completitud

| Puerta | Estado |
|---|---|
| BACKEND_COMPLETE | Una sola autoridad, en Recepciones: `registrar_zona_temporal`, `zonas_temporales`, `opciones_de_zona_temporal` y `zona_temporal_editable`. Bloqueo de fila; 404 si la recepción o la ubicación no son de la empresa; 409 `LOCATION_OTHER_WAREHOUSE`, `LOCATION_NOT_ELIGIBLE` y `RECEIPT_TEMPORARY_LOCATION_CLOSED` |
| DATABASE_COMPLETE | Una columna nullable con su FK `fk_goods_receipts_temporary_location_id_warehouse_locations`, sin backfill. `0105` pasa ida, vuelta e ida en PostgreSQL, y `n10` no muestra diferencias nuevas entre el ORM y la base. `0103` no se tocó |
| API_COMPLETE | `POST /purchasing/receipts/{id}/temporary-zone` (`compras:create`) y `GET …/temporary-zone/options` (`compras:view`). El detalle añade `temporary_location` y `can_set_temporary_location`, la lista añade `temporary_location_label` y el expediente los proyecta. Importaciones no tiene un endpoint de escritura propio. `REMOVED_ROUTES=0`, `BREAKING_SCHEMA_CHANGES=0` |
| FRONTEND / SCREEN_COMPLETE | El componente único `ZonaTemporal`, con su propia puerta de autoridad, aparece en el expediente (tarjeta de la recepción: «Zona temporal: …») y en Recepciones (columna «Zona temporal» y detalle). Muestra etiquetas legibles, sin UUID |
| MENU_COMPLETE | Compras → Importaciones → expediente y Compras → Recepciones, menús existentes |
| PROCESS_COMPLETE | Crear la recepción → registrar la zona → verla en Recepciones → cambiarla → verla en el expediente → contar y confirmar (la zona se vuelve histórica) → ubicar (la ubicación final, aparte) |
| FIELDS_COMPLETE | La ubicación temporal, elegida entre las ubicaciones activas del almacén de la recepción. No se pide más, porque la fuente no lo exige |
| ROLES_COMPLETE | Ver: `compras:view`. Registrar y cambiar: `compras:create`, el permiso de las acciones hermanas de la etapa (arribo y descarga). No se crea capacidad nueva |
| AUDIT_COMPLETE | `RECEIPT_TEMPORARY_LOCATION_SET`, con la zona anterior y la nueva (id y etiqueta), el actor y la empresa. Repetir la misma zona no audita. Catálogo: 494 entradas tras la fusión con PROC-11 (493 + 1). El historial completo está en la bitácora, sin un ledger paralelo |
| SECURITY / ISOLATION_COMPLETE | La empresa sale del contexto. Una recepción ajena da 404 (T6) y una ubicación de otra empresa, 404 (T5) |
| CONCURRENCY_COMPLETE | Bloqueo de la fila de la recepción. La confirmación bloquea la misma fila, de modo que un cambio que llega después de confirmar ve CONFIRMADA y da 409 (T4). El put-away no toca la recepción (T8) |
| INVENTORY_SEMANTICS | `TEMP_ZONE_CHANGES_STOCK=0`, `CREATES_INVENTORY_MOVEMENT=0`, `CHANGES_COST=0`, `CHANGES_PUTAWAY=0`. Lo prueban T3 en el backend (saldos y movimientos iguales) y la E2E (mismo número de movimientos antes y después) |
| E2E_COMPLETE | `importaciones.spec.ts`, pasos 2.6, 3 y 6: registrar «Muelle», verificar tras recargar con los movimientos sin cambio, verlo en Recepciones, cambiar a «Validación», y tras el put-away seguir viéndola, ya no editable y distinta de la ubicación final |
| RESPONSIVE_COMPLETE | La E2E pasa a 1280, 390 y 320 |
| ACCESSIBILITY_COMPLETE | Axe (WCAG 2.0/2.1 A y AA), con `AXE_NEW_SERIOUS=0` en reposo: expediente y Recepciones a 1280, 390 y 320. Un `color-contrast` intermitente a 390 (2 de 6 corridas) sobre el botón primario compartido, medido justo cuando vuelve de «ocupado» (`disabled:bg-brand-300` + `transition-colors` en `Button.tsx`): es un estado transitorio del componente compartido, previo a este ciclo, y no se absorbe |

## Pruebas

| Prueba | Resultado |
|---|---|
| `tests/test_spec018_temporary_zone.py`, de T1 a T8 (registrar, cambiar y auditar, sin efecto en inventario, cierre al confirmar, ubicaciones inválidas, aislamiento, opciones y put-away) | PASS en PostgreSQL |
| Mutaciones: siempre editable; sin la comprobación de almacén | Las 2 mueren y el original se restauró byte a byte |
| Pruebas dirigidas y guardias (019, 021, 022, `n10`, catálogo, cabezas, descarga, §3, importaciones) | 161 PASS; la única falla es la de línea base de `n10` |
| Regresión dirigida (Specs 018 a 023, Importaciones, Compras, catálogo, `n10` y cabezas) | 459 PASS; 3 fallos de línea base (`spec019_receipt` ×2, `n10`) |
| E2E en Chrome sobre PostgreSQL efímero con ClamAV (`importaciones`, `putaway`, `receipts`, `conteo-independiente`, `inventory-confirmation`, `condicion-recepcion`) | 25/25 a 1280; `importaciones` a 390 y 320 |
| Vitest · typecheck · lint · build | 1949/1949 (incluye `ZonaTemporal.test.tsx` y la guardia `gate-coverage`) · limpio · limpio · correcto |
| ruff · mypy | limpio · 51 (línea base; sin errores nuevos) |
| OpenAPI | 2 rutas nuevas (adición). Las fixtures se regeneraron |
| Fusión con PROC-11 de P1 (`279d6c8`) | Una sola cabeza, `0105_receipt_temporary_zone`, detrás de `0104_gov_proc11_sod_funciones`. La migración pasa ida, vuelta e ida en una base nueva. Guardias de cabeza, catálogo (494), zona temporal, arquitectura 019 y 021, `n10` y PROC-11: 100 PASS más la línea base de `n10`. ruff limpio. Vitest 1960/1960, typecheck, lint y build correctos |
| Suite completa de backend en PostgreSQL (una vez), con analizador real | 5382 PASS, 18 skip y 19 fallos. 14 son de Gobierno (`gov_proc08`, `gov_proc10`): «la fecha del acto no puede ser futura», porque `tests/proc08_ayudantes.py` usa `datetime.now(UTC).date()` y la suite terminó en la ventana de 20:00 a 24:00 de Caracas (GOV-TEST-UTC-DATE, la misma firma del cierre del put-away). Los 5 restantes son la línea base (`gobierno_integridad`, `n10`, `naive_datetime` y dos de `spec019_receipt`). `NEW_FAILURES=0` |

## Deudas (no absorbidas)

- **AXE-BUTTON-BUSY-TRANSITION.** El botón primario compartido puede medirse en mitad de la transición desde su estado deshabilitado.
- **Zonas A a E.** Siguen en SPONSOR_VALIDATION_REQUIRED. La zona temporal no depende de ellas.
- **Las demás deudas** siguen sin cambios: E2E-PUTAWAY-NAV-MOBILE, A11Y-IMPORT-SCROLL-REGIONS y las del encargo.
