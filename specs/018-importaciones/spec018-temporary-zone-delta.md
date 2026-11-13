# Spec 018 · delta: zona temporal de recepción o validación (§2)

- **Encargo:** `SPEC018_ZONA_TEMPORAL`, del 2026-11-12.
- **Spec dueña:** 018, dueña del proceso.
- **Autoridad del dato:** Spec 019 (Recepciones).
- **Decisión de producto:** la dueña, el 2026-11-11, eligió `REGISTRAR_UBICACION_TEMPORAL` (`evidence/SPEC018_REMAINING_DECISIONS.md`).
- **Evidencia:** `evidence/temporary-zone/`.

## Requisito

DOCX §2: «Colocar la mercancía temporalmente en zona de recepción o validación».

El sistema registra **dónde está** la mercancía de una recepción mientras se completa la recepción y su validación, y no mueve inventario. Responde a la pregunta «¿dónde está temporalmente esta mercancía?». El movimiento físico real sigue siendo el put-away (Spec 022).

## Modelo logístico existente (arqueología)

- `warehouse_locations` es la hoja de la jerarquía: tiene empresa, almacén, zona, pasillo, rack, nivel, tipo, código, nombre y estado. Las transacciones ya la referencian (put-away, validación física).
- `zone_types`, `warehouse_zones` y `location_types` (con `is_storable`) son configurables por empresa.
- Lo recibido queda hoy en estado RECIBIDO con ubicación nula. La confirmación (Spec 021) lo deja en DISPONIBLE, también sin ubicación, y el put-away lo coloca.

`TEMPORARY_ZONE_CAN_REUSE_LOCATION_MODEL=1`. No hace falta un catálogo nuevo: la zona temporal es una `warehouse_location` que la empresa configura (por ejemplo, «Muelle de recepción» o «Zona de validación»).

## Clarificaciones (resueltas con las fuentes, sin decisión material nueva)

| Pregunta | Respuesta y fuente |
|---|---|
| ¿Qué ubicaciones valen? | Cualquier ubicación ACTIVA del almacén de la recepción. El documento no fija un tipo, y fijarlo exigiría decidir la semántica de las zonas A a E, que están sin validar |
| ¿Cuándo se puede registrar o cambiar? | Desde el borrador hasta que se confirma el inventario: estado DRAFT, CONFIRMED, QUALITY_PENDING, ACCEPTED o PARTIALLY_ACCEPTED, con `confirmation_status = PENDIENTE`. Es la transición procedimental real que cierra la validación (Spec 021, etapa 9) |
| ¿Cuándo pasa a histórica? | Al confirmar el inventario, o si la recepción queda REJECTED, CLOSED o CANCELLED. Se conserva, no se borra y no se puede cambiar |
| ¿Se puede vaciar? | No. Solo se registra o se cambia, para no borrar la evidencia |
| ¿El put-away la borra? | No. La ubicación final queda en el ledger y en `receipt_putaways`, separada |
| ¿Hace falta un historial propio? | No. Cada cambio queda en `audit_events` (`RECEIPT_TEMPORARY_LOCATION_SET`, con el valor anterior y el nuevo). No se crea un ledger paralelo |
| ¿Quién puede? | Ver: `compras:view`. Registrar y cambiar: `compras:create`, el permiso de las acciones hermanas de la etapa (arribo y descarga programada) |

## Contrato

- **TZ-01. Autoridad.** Recepciones: `goods_receipts.temporary_location_id`, una FK nullable a `warehouse_locations.id`. Importaciones solo la proyecta.
- **TZ-02. Referencia estructurada.** La ubicación debe ser de la empresa del contexto, del mismo almacén que la recepción y estar ACTIVA. Errores:
  - 404 `LOCATION_NOT_FOUND`: ubicación inexistente o de otra empresa;
  - 409 `LOCATION_OTHER_WAREHOUSE`;
  - 409 `LOCATION_NOT_ELIGIBLE`.
- **TZ-03. Propiedad.** `purchasing.service.registrar_zona_temporal(db, *, company_id, receipt_id, location_id, actor)` es el único escritor.
- **TZ-04. Proyección.**
  - El detalle de la recepción añade `temporary_location {id, label}` y `can_set_temporary_location`.
  - La lista de recepciones añade `temporary_location_label`.
  - `logistics.receipts[]` del expediente añade `temporary_location_label` y `can_set_temporary_location`.
  - Para leerla hay una sola función de servicio. No se duplica lógica.
- **TZ-05. Sin movimiento.** No crea `inventory_movements`.
- **TZ-06. Sin efecto en saldos ni costo.** No toca `inventory_balances`, capas, valoración ni landed cost.
- **TZ-07. Ciclo de vida.** Como en las clarificaciones. Fuera de él: 409 `RECEIPT_TEMPORARY_LOCATION_CLOSED`.
- **TZ-08. Editabilidad.** Se puede cambiar cuantas veces haga falta dentro del ciclo de vida. Si el valor es el mismo, no hace nada y no audita.
- **TZ-09. Historial y auditoría.** `RECEIPT_TEMPORARY_LOCATION_SET`, con `before` y `after` = `{temporary_location_id, temporary_location_label}`, más actor, empresa y entidad (la recepción).
- **TZ-10. Permisos.** Ver: `compras:view`. Escribir: `compras:create` + `require_write_allowed`.
- **TZ-11. Aislamiento.** Una recepción de otra empresa da 404 `RECEIPT_NOT_FOUND`. La empresa sale del contexto, nunca del cliente.
- **TZ-12. Concurrencia.** Bloqueo de fila de la recepción (`with_for_update().execution_options(populate_existing=True)`). La confirmación de inventario bloquea la misma fila, de modo que un cambio que llega después de confirmar ve CONFIRMADA y da 409. Dos cambios a la vez: gana el último y ambos quedan auditados. El put-away no toca la recepción.
- **TZ-13. Separación de la ubicación final.** Ni el put-away ni la reubicación leen ni escriben la zona temporal. El expediente muestra «Zona temporal» en la tarjeta de la recepción y la ubicación final en «Ubicación».
- **TZ-14. Fronteras.**
  - Rutas `POST /purchasing/receipts/{receipt_id}/temporary-zone` y `GET /purchasing/receipts/{receipt_id}/temporary-zone/options` (ubicaciones elegibles, con `compras:view`).
  - `purchasing/api.py` no contiene `put-away`, `putaway`, `ubicacion` ni `/locations` (guardia de la Spec 021).
  - `create_receipt` no cambia (guardia de la Spec 019).
  - No se crea ninguna constante ZONA_A a ZONA_E.
- **TZ-15. Aceptación de UAT.** Pasos desde el 126 de la tarjeta de la dueña.

```text
ROUTES_ALLOWED=POST /purchasing/receipts/{receipt_id}/temporary-zone; GET /purchasing/receipts/{receipt_id}/temporary-zone/options
ROUTES_FORBIDDEN=cualquier escritura de la zona temporal bajo /importaciones; cualquier ruta con put-away|putaway|ubicacion|/locations en purchasing/api.py
MIGRATION_REQUIRED=1 (0105_receipt_temporary_zone: una columna nullable y su FK; sin backfill)
ALEMBIC=0105_receipt_temporary_zone detrás de 0104_gov_proc11_sod_funciones (P1, publicada); nació como 0104 y se reencadenó en la fusión, sin cambiar su cuerpo
```

## Constitution gate

```text
REQUIREMENT_COMPLETE=1  AUTHORITY_CLEAR=1  LOCATION_MODEL_REUSABLE=1  NO_ZONES_A_E_DEPENDENCY=1
NO_STOCK_SIDE_EFFECT=1  SECURITY_PASS=1  DATA_INTEGRITY_PASS=1  ARCHITECTURE_PASS=1  TESTABILITY_PASS=1
MATERIAL_DECISION_REQUIRED=0  CONSTITUTION_GATE=PASS
```

## Tareas

| Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|
| T018-TZ-0 Autoridad, delta y diseño | CLAUDE | n-a | NO | n-a | n-a | este documento | — | gate PASS |
| T018-TZ-A Backend: migración 0105, modelo, servicio, API, proyección, catálogo, guardias y pruebas | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `alembic/versions/0105_receipt_temporary_zone.py`, `purchasing/{models,service,api}.py`, `imports/service.py`, catálogo, guardias de cabeza, `tests/test_spec018_temporary_zone.py` | pytest en PostgreSQL | TZ-01 a TZ-14 |
| T018-TZ-B Pantallas y E2E | DEEPSEEK | deepseek-v4-pro | NO | YES | 2 | `RecepcionesPage.tsx`, `ImportacionRecepcion.tsx`, tipos, `e2e/importaciones.spec.ts` | E2E en Chrome sobre PostgreSQL | 1280, 390 y 320; Axe sin faltas graves nuevas |
| T018-TZ-C Evidencia, matriz y tarjeta de UAT | CLAUDE | n-a | NO | n-a | n-a | documentos | — | matriz recontada |

## Trazabilidad

| Requisito | Contratos | Pruebas |
|---|---|---|
| DOCX §2 «colocar temporalmente en zona de recepción o validación» | TZ-01 a TZ-04, TZ-07, TZ-13 | backend T1, T2 y T9; E2E pasos de la zona temporal |
| Sin efecto en inventario (decisión de la dueña) | TZ-05, TZ-06 | backend T3 y T8 |
| Integridad y seguridad | TZ-02, TZ-10, TZ-11, TZ-12 | backend T4 a T7 |
| Historial | TZ-09 | backend T2 |
