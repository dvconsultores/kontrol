# §2 Programar descarga desde la importación: evidencia

Autoridad: `../PROGRAMAR_DESCARGA_AUTHORITY.md`. Delta: `../../spec018-unloading-schedule-delta.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE. Reutiliza `unloading_scheduled_at`; sin migración |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE: desde Compras → Importaciones → expediente se programa y se reprograma la descarga, y Recepciones muestra el mismo valor |
| OWNER_READINESS_STATUS | OWNER_UAT_READY: pasos 102 a 107 de la tarjeta. `OWNER_ACCEPTED`: NO |

## Puertas de completitud

| Puerta | Estado |
|---|---|
| BACKEND_COMPLETE | `purchasing.service.programar_descarga`: bloquea la fila; 404 si es de otra empresa; 409 `RECEIPT_NOT_OPEN` fuera de DRAFT y CONFIRMED; un nulo borra la programación |
| DATABASE_COMPLETE | La fuente única es `goods_receipts.unloading_scheduled_at`. `MIGRATION_REQUIRED = 0`. No hay columna ni motor duplicado |
| API_COMPLETE | `POST /purchasing/receipts/{id}/unloading-schedule`, en Recepciones, que es la autoridad. Importaciones no duplica el endpoint. El detalle del expediente añade `unloading_scheduled_at` y `can_schedule_unloading` (adiciones compatibles) |
| FRONTEND / SCREEN_COMPLETE | Expediente, sección Arribo: «Descarga programada: <fecha y hora legibles>» o «Sin programar»; la acción «Programar descarga de <código>», con aviso si falta la fecha. El alta de la recepción pide «Descarga programada (hora de Caracas)». Recepciones tiene la columna «Descarga programada». No muestra ISO crudo, UUID ni códigos |
| MENU_COMPLETE | Compras → Importaciones → expediente (menú existente). Sin entrada nueva |
| PROCESS_COMPLETE | Crear la recepción con su programación → confirmar el arribo → reprogramar la descarga → verla en Recepciones → seguir con la recepción física |
| FIELDS_COMPLETE | Fecha y hora: lo único que pide la fuente. Ventana, muelle, responsable y observaciones no se añadieron porque la fuente no los exige |
| ROLES_COMPLETE | Ver: `compras:view`. Programar, editar y borrar: `compras:create`, el permiso de las acciones hermanas de la etapa (arribo y confirmación). No se usa `compras:approve`, porque no es una aprobación |
| AUDIT_COMPLETE | `RECEIPT_UNLOADING_SCHEDULED`, con el valor anterior y el nuevo, el actor y la empresa. El alta sigue en `RECEIPT_CREATED` e `IMPORT_RECEIPT_CREATED` |
| SECURITY_COMPLETE | El backend filtra por la empresa del contexto; una recepción ajena da 404 (probado) |
| CONCURRENCY_COMPLETE | Cada guardado se hace bajo el bloqueo de fila. Con dos usuarios a la vez gana el último, y los dos cambios quedan auditados con su antes y después |
| TIMEZONE | La entrada es hora de Caracas (`instanteDesdeHoraDeCaracas`); el backend la recibe con zona (`InstanteDeEntrada`) y la guarda en UTC; se muestra con `formatearInstante`. Medido en la E2E: 08:15 en Caracas se guarda como `2026-12-16T12:15:00Z`, y Recepciones y el expediente muestran el mismo texto. Una hora sin zona da 422. `TIMEZONE_REGRESSION = 0` |
| E2E_COMPLETE | `e2e/importaciones.spec.ts`, pasos 1 a 3: programación al crear, reprogramación, comprobación del instante en UTC, persistencia tras recargar y el mismo valor en Recepciones |
| RESPONSIVE_COMPLETE | La E2E pasa a 1280, 390 y 320, sin desbordamiento |
| ACCESSIBILITY_COMPLETE | Axe (WCAG 2.0/2.1 A y AA): 0 faltas graves o críticas en el expediente (paso de programar) y en Recepciones, a 1280, 390 y 320. Campos nativos con su `label` |
| DOCUMENT / REPORTING | NOT_APPLICABLE: programar no genera documento; el rastro está en la bitácora |

## Pruebas

| Prueba | Resultado |
|---|---|
| `tests/test_spec019_unloading_schedule.py`: programar y consultar; reprogramar con antes y después en la auditoría; borrar; una hora sin zona da 422; una recepción aceptada da 409; aislamiento por empresa (404) | PASS en PostgreSQL |
| Regresión dirigida de las Specs 018 y 019 (19 ficheros) | 116 PASS. Los 2 fallos son de la línea base de `spec019_receipt` |
| E2E en Chrome sobre PostgreSQL con analizador real: `importaciones`, `receipts`, `conteo-independiente`, `inventory-confirmation` | 14/14 a 1280; `importaciones` también a 390 y 320 |
| Vitest completo · typecheck · lint · build | 1922/1922 · limpio · limpio · correcto |
| OpenAPI | Una ruta nueva (adición); las fixtures del frontend se regeneraron |
| Suite completa de backend en PostgreSQL, con analizador real | 5340 PASS y los 5 fallos de la línea base (`gobierno_integridad`, `n10`, `naive_datetime`, dos de `spec019_receipt`). NEW_FAILURES = 0 |

## Cierre

- **Fusión con CTL-09 de P1:** este ciclo no tiene migración, así que la cabeza es la de P1 (`0102_gov_ctl09_actas`, una sola). El catálogo queda en 486.
- **Después de la fusión:** 96 PASS en las pruebas backend afectadas (catálogo, guardias de cabeza, descarga, conteo independiente, compras) y 443 PASS en Vitest de contratos.
