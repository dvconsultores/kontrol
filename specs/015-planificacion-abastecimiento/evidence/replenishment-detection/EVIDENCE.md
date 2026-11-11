# Spec 015 · Detección automática de reposición: evidencia

Encargo `SPEC015_AUTOMATIC_REPLENISHMENT_DETECTION`, del 2026-11-10. Delta: `../../spec015-replenishment-detection-delta.md`.

## Estado

| Métrica | Estado |
|---|---|
| TECHNICAL_FOUNDATION_STATUS | COMPLETE: dominio, migración, planificador, alerta, API, permisos, aislamiento, auditoría y concurrencia |
| FUNCTIONAL_PRODUCT_STATUS | COMPLETE en Chrome sobre PostgreSQL migrado: alerta → necesidad → requisición → resolución → nuevo episodio |
| OWNER_READINESS_STATUS | OWNER_UAT_READY (pasos 67 a 76 de la tarjeta). `OWNER_ACCEPTED`: NO, solo lo concede la dueña |

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:**
  - Maestros → Planificación de abastecimiento: «Detección automática de reposición» en la política, columna «Detección» y botón Activar o Apagar.
  - Centro de alertas: alerta «… requiere reposición en el almacén …», con «Abrir origen».
  - Compras → Necesidades de reposición: lista y detalle.
  - Desde la necesidad, «Crear requisición», que abre Compras → Requisiciones → Nueva y después el detalle.
- **WHAT_CAN_USER_DO:**
  - Encender la detección por política.
  - Recibir una alerta cuando el disponible llega al punto de reorden con una sugerencia positiva.
  - Ver por qué se generó y la situación actual.
  - Crear una requisición precargada que queda enlazada a la necesidad.
  - Ver que la necesidad se resuelve sola cuando la situación cambia, y que si reaparece nace un episodio nuevo.
- **OWNER_UAT_READY:** YES.
- **PRODUCT_STATUS:** FUNCTIONAL_SLICE_COMPLETE, verificado en navegador.
- **MISSING_GATES:**
  - la aceptación de la dueña;
  - el suministro abierto por almacén, fuera de alcance (`OPEN_SUPPLY_NOT_AVAILABLE = 1`).

## Arquitectura (autoridades, sin reemplazos)

**Trabajo periódico:** temporizador del sistema → `python -m app.modules.scheduler tick` (Spec 047, ADR-D0-015) → manejador registrado `planning_replenishment_detection`.
- Spec dueña: 015.
- Recuperación: `OWNER_IDEMPOTENT`. Evalúa el estado actual, así que un tick perdido no exige repetir nada.
- El manejador solo llama a `planning/replenishment.py: evaluate_replenishment_needs`, que usa el motor existente `compute_plan`.

**Condición:** `AVAILABLE_AT_OR_BELOW_REORDER_POINT_V1`.
- Se cumple si el plan sale OK, disponible ≤ punto de reorden y sugerencia > 0.
- Sin política o sin historia, no hay necesidad. Con disponible 0, punto 0 y sugerencia 0, tampoco.

**Necesidad:** `replenishment_needs`.
- Instantánea de activación inmutable, más el estado actual.
- Estados ACTIVE y RESOLVED, con motivo.
- Una sola ACTIVE por empresa, almacén y producto, garantizada por un índice único parcial en la base.
- Una necesidad resuelta no se reabre: si la condición vuelve, se crea otra.

**Alerta:** de sistema, sin regla configurable.
- Contrato: `crear_alerta` de la Spec 047. La regla de la 047 está pensada para hechos de la 045 con destinatarios; una alerta no tiene destinatarios.
- Dedupe `replenishment-need:{id}`, origen `ReplenishmentNeed` (exige `compras:view`) y `route_key` `replenishment_need`.
- Se resuelve con el contrato nuevo `resolver_alerta_de_sistema`, sin borrar.
- Cuenta en `active_alerts` por el filtro de origen que ya existía.

**Universo por tick:**
- Primero las necesidades activas, para resolverlas.
- Después, los almacenes activos cuya política resuelta (respetando la precedencia publicada) tiene la detección encendida, con los productos que tienen movimientos en ellos.
- Tope de 500 evaluaciones por tick, con un cursor por empresa.
- Cada candidato va en su propia transacción y se cuentan vistos, procesados, omitidos y fallidos.

**Trazabilidad:** `requisition_line_plans.replenishment_need_id`. Crear la requisición no resuelve la necesidad.

## Pruebas

| Puerta | Resultado |
|---|---|
| `test_planning_replenishment.py` (15 escenarios: apagada, por encima del punto, detección, dedupe, resolución, reaparición, sin política o historia, política apagada, producto inactivo, API y permisos y aislamiento, trazabilidad, visibilidad de la alerta, tope y cursor, registro, concurrencia en PostgreSQL) | PostgreSQL 15/15; SQLite 14 + 1 omitida |
| Regresión dirigida: Spec 015 (configuración, motor, requisición), banda de rotación de la Spec 018, Spec 047 (notificaciones y planificador), compras, catálogo de auditoría y guardas de cabeza | PostgreSQL 210/210; SQLite 133 + 77 omitidas |
| ruff | limpio |
| mypy | 154, igual que la línea base: 0 nuevos |
| Migración `0096_replenishment_detection` sobre PostgreSQL nuevo | upgrade, downgrade a `0095_fusion_gov_planning`, upgrade; una cabeza; `alembic check` sin deriva en las tablas nuevas |
| Frontend: lint, typecheck, Vitest | limpio, limpio, 1903/1903 |
| E2E `e2e/reposicion.spec.ts` (Chrome, PostgreSQL efímero migrado por Alembic, tick canónico del planificador) | PASS a 1280, 390 y 320 |
| E2E de regresión `planificacion.spec.ts` + `notifications.spec.ts` | 8/8 |
| Axe (WCAG 2.0/2.1 A y AA) en planificación, centro de alertas, detalle de la necesidad, nueva requisición precargada y lista | 0 graves o críticas introducidas, a 1280 y a 320. Una previa en el centro de alertas: ver «Hallazgos» |
| Teclado | «Abrir origen» de la alerta y «Crear requisición» se activan con foco y Enter |

**Recorrido de la E2E:**
1. Política creada en la UI con la detección encendida.
2. Tick: disponible 20 frente a punto 3, así que no hay necesidad.
3. Salida de 18, tick: 1 necesidad y 1 alerta. Otro tick: siguen 1 y 1, con el mismo id.
4. Centro de alertas → «Abrir origen» → detalle con la frase de activación (disponible 2, punto 8,4, política v1) y la sugerencia de 12.
5. «Crear requisición»: almacén precargado, código, alta; producto y cantidad precargados; la línea queda con «Ver necesidad» y la política v1; al reabrirla, la instantánea persiste.
6. La necesidad lista su requisición y sigue activa.
7. Entrada de 50, tick: necesidad RESOLVED y alerta RESOLVED.
8. Salida de 50, tick: nueva necesidad ACTIVE con otro id y nueva alerta; la anterior sigue RESOLVED.

### Mutaciones

Cada una se aplicó al fichero del repositorio y se restauró, comprobándolo por md5.

| Mutación | Detectada por |
|---|---|
| Clave de dedupe de la alerta distinta en cada evaluación | c, d, e, f |
| Condición invertida (disponible > punto) | c, d, e, f |
| No resolver la alerta al resolver la necesidad | e, h |

## Hallazgos

1. **Migración que no coincidía con el modelo (corregida antes de publicar).** La primera 0096 creaba `created_by` NOT NULL sin default y `version` en las dos tablas nuevas. Las pruebas no lo veían porque construyen el esquema desde los modelos. En una base migrada (E2E, UAT o producción) toda necesidad habría fallado al guardarse. Lo detectó `alembic check`.
2. **Contraste de la etiqueta «Advertencia» en el Centro de alertas, deuda previa de la Spec 047.** Axe marca `color-contrast` grave en `EtiquetaSeveridad` (`bg-warning-100` con `text-warning-700`). El componente no se tocó en este ciclo. Se ve porque esta es la primera alerta `WARNING` que recorre la E2E. No se corrige aquí porque el encargo pide no cambiar la Spec 047.
3. **Prueba previa reparada al pasar.** `test_spec047_scheduler::test_el_tick_deja_registro_de_cada_manejador…` fallaba desde que se registraron los manejadores de copias de seguridad. Había que añadir el manejador nuevo a esa misma aserción, así que ahora refleja el registro completo y pasa.
4. **UAT sin temporizador.** En la UAT local el paso del planificador se lanza a mano (`kontrol.py scheduler-tick`). La tarjeta lo dice.

## Suite completa (cierre)

Una corrida de cada motor con el analizador real. Comparación con la línea base de la cabeza `e22a394`:

| Motor | Resultado | Fallos | Nuevos |
|---|---|---|---|
| SQLite | 3313 pasan, 1988 omitidas | `test_naive_datetime_input` (previo) y `test_backup_job_retencion::test_registro_termina_con_las_tres_copias` | 1, corregido por la llamada 5 |
| PostgreSQL | 6 fallos | `test_n10_convergence` (deuda previa de `created_by`; no menciona las tablas nuevas), `test_spec019_receipt` ×2, `test_gobierno_integridad_runner`, `test_naive_datetime_input` (los cinco previos), y el mismo `test_backup_job_retencion`, que se lanzó antes de aplicar la llamada 5 | 0 tras la llamada 5 |

**Después de la llamada 5**, en PostgreSQL: `test_backup_job_retencion.py` + `test_spec047_scheduler.py` + `test_planning_replenishment.py` dan 56/56. En SQLite, 40 pasan y 16 se omiten.

**NEW_FAILURES = 0.**
