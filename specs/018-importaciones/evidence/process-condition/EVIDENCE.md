# Condición del proceso de recepción (§3): evidencia

- **Delta:** `../../spec018-process-condition-delta.md`.
- **Decisiones:** `../SPEC018_REMAINING_DECISIONS.md`.
- **Intentos:** `ATTEMPT_LOG.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE: condición derivada (`purchasing/process_condition.py`), sin columna ni tabla nueva, sin motor paralelo |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE: «Recibido», «Pendiente de validación» y «Bloqueado por incidencia» en Recepciones y en el expediente, con la misma fuente |
| OWNER_READINESS_STATUS | OWNER_UAT_READY: pasos 115 a 125 de la tarjeta. `OWNER_ACCEPTED`: NO |

## Puertas de completitud

| Puerta | Estado |
|---|---|
| BACKEND_COMPLETE | `condiciones_por_recepcion` / `condicion_de_recepcion` derivan la condición del estado real: incidencia viva (020), confirmación de inventario (021) y estado de la recepción. Una consulta por lote; precedencia `BLOQUEADO > PENDIENTE > RECIBIDO` |
| DATABASE_COMPLETE | Sin cambios de esquema: `MIGRATION_REQUIRED=0`. `ALEMBIC_HEAD_COUNT=1` (`0103_receipt_putaway_link`) |
| API_COMPLETE | Adiciones compatibles: `process_condition` en `GET /purchasing/receipts`, `GET /purchasing/receipts/{id}` y `logistics.receipts[]` de `GET /importaciones/{id}`. `REMOVED_ROUTES=0`, `BREAKING_SCHEMA_CHANGES=0` |
| FRONTEND / SCREEN_COMPLETE | Columna «Condición» en Recepciones, bloque «Condición del proceso» en la ficha y en la sección «Recepción» del expediente. Texto humano del backend, sin códigos internos, UUID ni JSON; el bloqueo explica el motivo y enlaza a las incidencias existentes |
| MENU_COMPLETE | Sin entradas nuevas: Compras → Recepciones y Compras → Importaciones → expediente |
| PROCESS_COMPLETE | Recepción creada → pendiente; contada sin confirmar → pendiente; incidencia abierta → bloqueada y confirmación impedida; resolución → recalculada; confirmación → recibida |
| FIELDS_COMPLETE | `code`, `label`, `blocking_incidents`, `incidents[]` e `reason`; nulo para anulada y rechazada |
| ROLES_COMPLETE | `compras:view`, el mismo permiso que ya abre ambas pantallas; ninguna capacidad nueva |
| AUDIT_COMPLETE | Sin evento nuevo: la condición es derivada y las acciones materiales ya las auditan las Specs 020 y 021 |
| SECURITY_COMPLETE | Filtro por empresa del contexto y por `company_id`; otra empresa recibe 404 y no la ve en el listado |
| CONCURRENCY_COMPLETE | La condición se calcula con el estado transaccional de la lectura; no introduce locks ni duplica los de las Specs dueñas |
| E2E_COMPLETE | `condicion-recepcion.spec.ts` (nueva, verde): pendiente al crear y al contar, bloqueo visible con motivo y enlace, confirmación impedida 409, recalculación al resolver, «Recibido» al confirmar, recarga y 1280/390/320. En `importaciones.spec.ts`, el expediente muestra el bloqueo con su enlace y se recalcula a pendiente: esas aserciones pasaron en la corrida canónica antes de un bloqueo de entorno ajeno a esta fila (ver «Deudas y límites») |
| RESPONSIVE_COMPLETE | `condicion-recepcion.spec.ts` verifica la condición a 1280 (ancho del proyecto), 390 y 320 sin desplazamiento lateral. El bloque responsive final de `importaciones.spec.ts` no llegó a ejecutarse por el bloqueo de entorno de la pestaña de impresión |
| ACCESSIBILITY_COMPLETE | Axe (WCAG 2.0/2.1/2.2 A y AA) sobre la pantalla de Recepciones con el bloqueo visible: `AXE_NEW_SERIOUS=0`. La condición es texto con tokens del sistema, no depende solo del color, y el enlace es un control existente y enfocable |
| DOCUMENT / REPORTING | NOT_APPLICABLE: no genera documento; la condición es una vista del proceso |

## Pruebas

| Prueba | Resultado |
|---|---|
| `tests/test_spec018_process_condition.py` (11 escenarios: pendiente inicial, contada sin confirmar, bloqueo y confirmación impedida 409, recalculación, proceso completo, precedencia sobre recibido, una sola condición, stock intacto, expediente, listado, aislamiento 404, anulada sin condición) | 11/11 PASS en PostgreSQL |
| `tests/test_spec018_process_condition_architecture.py` (tres condiciones y precedencia, sin persistencia, sin escritura de inventario, sin estados nuevos, sin segundo motor, superficies y una sola consulta por lote) | 10/10 PASS |
| Guardias 019, 020, 021 y 022, incidencias, confirmación, conteo independiente, put-away y vínculo del put-away (sin contar las 21 nuevas) | 125/125 PASS en PostgreSQL |
| Suites de importaciones (flujo, seguimiento, reubicación, almacenamiento y costos) | 56/56 PASS en PostgreSQL |
| `test_frontend_fixtures` (sin rutas nuevas) | 2/2 PASS |
| Vitest completo del frontend, incluido `CondicionDelProceso.test.tsx` | 1946/1946 PASS (174 archivos) |
| typecheck · lint · build · typecheck de la E2E · lint de la E2E | limpio · limpio · correcto · limpio · limpio |
| ruff · mypy sobre los archivos nuevos | limpio · limpio |
| E2E `condicion-recepcion.spec.ts` en Chrome sobre PostgreSQL efímero, con ClamAV real, incluido el barrido Axe | 1/1 PASS (11,7 s), limpieza LIMPIA |
| E2E `importaciones.spec.ts` (superficie del expediente) | Las aserciones de la condición pasaron; la corrida se detuvo después en la pestaña de impresión, bloqueada por el navegador de este entorno |

## Cierre

- **Publicación.** `3f7d00e` en `develop`, con `HEAD_EQUALS_ORIGIN_DEVELOP=1`. Entrada `7fcb491`; sin fusión necesaria.
- **Sin migración.** `ALEMBIC_HEAD_COUNT=1` (`0103_receipt_putaway_link`), sin cambios de esquema.
- **Superficies.** Recepciones (fila y ficha) y expediente consumen el mismo cálculo del backend; React muestra el texto humano que publica la API.
- **Stock intacto.** Las pruebas comprueban que abrir y resolver la incidencia no cambia los saldos ni crea estados de mercancía nuevos.

## Deudas y límites (no absorbidos)

- **E2E-PRINT-BLOB-BLOQUEADO (entorno).** En `importaciones.spec.ts`, la comprobación de la pestaña de impresión (`window.open` de un `blob:`) no puede pasar con el Chromium de este equipo: se reprodujo con una sonda independiente del producto —abrir una ventana y navegarla a un `blob:`, o hacerlo con un ancla— y en todos los casos la pestaña queda en `about:blank`. Es una limitación del navegador del entorno, no de esta fila: las aserciones de la condición del expediente pasaron antes de ese punto. La verificación de la fila se completa con `condicion-recepcion.spec.ts`, en verde.
- **Analizador.** La primera corrida sin ClamAV falló donde debe (`SCAN_FAILED` en cargas con análisis obligatorio); con el ClamAV real aprovisionado sin privilegios, el flujo documental pasó.
- **Suite completa de backend en PostgreSQL (una corrida).** Llegó al 100 % y su resumen corto reportó **74 fallos y 72 errores**, todos atribuidos a este entorno y ninguno a esta fila:
  - 36 de `documents` (`documents`, `documents_security`, frontera de carga): sin `clamscan` el producto falla cerrado (`SCAN_FAILED`/`FILE_NOT_SCANNED`). **Con el ClamAV real aprovisionado: 71/71 PASS.**
  - 30 de `backup_create_pg`/`backup_restore_pg`: `pg_dump`/`pg_restore` fuera del `PATH`. **Con los binarios de QA en el `PATH`: 30/31 PASS**; el restante es un límite del rol (`permission denied to terminate process`).
  - 72 errores de `test_iso_relaciones_inv_md`: carrera al crear `btree_gist` en la base de prueba cuando la corrida completa crea esquemas en paralelo. **Aislado: 72/72 PASS.**
  - 2 de `n9_integrity`: dependen del analizador. **Con ClamAV: 3/3 PASS.**
  - 2 de `pg_harness_lifecycle`: el rol de prueba no puede leer `data_directory` (`InsufficientPrivilege`), parámetro de superusuario.
  - 4 de línea base ya conocida: `n10_convergence` (1), `naive_datetime_input` (1) y `spec019_receipt` (2, discrepancia previa entre prueba y producto sobre una recepción sin líneas).
  - La corrida no escribió su línea final porque el desmontaje de fixtures no terminó; el resumen corto con los 146 casos es el que se atribuye arriba.
- **Zona temporal (§2)** y **Zonas A a E**: fuera de este ciclo, sin cambios.
