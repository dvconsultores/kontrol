# Spec 015 · Planificación de abastecimiento: evidencia del ciclo

Encargo `SPEC015_ROTACION_PROYECCION_REORDER`, 2026-11-10. Rama `develop`, P2.

## PRODUCT COMPLETENESS GATE

- **WHERE_IS_IT_IN_MENU:**
  - Maestros → Planificación de abastecimiento.
  - Compras → Requisiciones → «Nueva requisición» y «Ver» (detalle con el panel de planificación).
  - Maestros → Almacenamiento → Reglas de almacenamiento → «Banda de rotación».
- **WHAT_CAN_USER_DO:**
  - Configurar políticas versionadas por empresa o por almacén:
    - fuente de demanda, histórico, horizonte y plazo;
    - stock de seguridad: ninguno, cantidad fija o días;
    - métrica de rotación y vigencia.
  - Configurar bandas de rotación sin solape.
  - Crear una requisición con almacén.
  - Al elegir un producto, ver:
    - demanda neta, media, proyección, seguridad y punto de reorden;
    - existencia, reservado y disponible;
    - cobertura, banda y cantidad sugerida.
  - Usar la sugerencia o escribir otra cantidad. Cada línea guarda una instantánea inmutable, que un cambio de política no altera.
  - Usar la banda como criterio de una regla de almacenamiento.
- **OWNER_UAT_READY:** YES. Pasos 55 a 66 de `docs/roadmap/enterprise-application-completion/OWNER_UAT_CARD.md`.
- **PRODUCT_STATUS:** `FUNCTIONAL_SLICE_COMPLETE`, verificado en Chrome sobre PostgreSQL migrado. `OWNER_ACCEPTED` lo concede solo la dueña.
- **MISSING_GATES:**
  - Aceptación de la dueña.
  - Fuera de alcance, declarados en `spec.md`: suministro abierto por almacén (`OPEN_SUPPLY_NOT_AVAILABLE`), costo estimado y plazo por producto o proveedor.
  - Producto pendiente: editar y borrar líneas de requisición, y alerta automática de reposición.

## Pruebas

| Puerta | Resultado |
|---|---|
| Backend nuevo (configuración, motor, requisición, banda en almacenamiento) más regresiones de compras, aprobaciones, almacenamiento, importaciones y catálogo de auditoría | PostgreSQL 164/164 y 71/71; SQLite con 15 y 2 omitidas (solo PostgreSQL) |
| Suite backend completa, SQLite, con analizador real | 3298 pasan, 1974 omitidas, **1 falla previa de P1** (ver «Hallazgos») |
| Suite backend completa, PostgreSQL | ver «Suite PostgreSQL» |
| ruff (backend completo, ahora incluido `app/modules/storage`) | limpio |
| mypy | 154 errores, igual que la línea base: 0 nuevos |
| Migración `0094_supply_planning` | upgrade, downgrade -1 y upgrade sobre PostgreSQL nuevo; una sola cabeza |
| Frontend: lint (`--max-warnings 0`), typecheck, Vitest | limpio, limpio, 1892/1892 |
| E2E `e2e/planificacion.spec.ts`, Chrome, PostgreSQL efímero migrado por Alembic, un escenario, 0 reintentos | PASS a 1280, 390 y 320 px (corridas `r20261110t180535…`, `r20261110t180629…`, `r20261110t180723…`, evidencia fuera de Git en `qa/e2e-runs/`) |
| E2E de regresión: `importaciones.spec.ts` y `approvals.spec.ts` a 1280 | 15/15 |
| Axe (WCAG 2.0/2.1 A y AA) en 7 puntos del flujo, incluido el panel abierto | 0 graves o críticas a 1280 y a 320 |
| Teclado | «Usar cantidad sugerida» se activa con foco y Enter |
| Desbordamiento horizontal | ninguno en planificación, detalle de requisición y almacenamiento, a los tres anchos (medido tras cargar el encabezado de cada pantalla) |

### Mutaciones

Cada mutación se aplicó al fichero del repositorio y después se restauró, comprobándolo por md5.

| Mutación | Detectada por |
|---|---|
| Filtro de `/planning/plans` con EXISTS sobre COUNT (siempre verdadero) | `test_engine_o_api_lista` (3 en lugar de 2) |
| Sin comprobación de versión de política al crear la línea | `test_f_politica_vencida` (200 en lugar de 409) |
| Una regla con banda distinta coincide | `test_rotation_band_lenta_sin_regla` (CLASSIFIED en lugar de NO_RULE) |

## Vectores del motor (`AVG_CALENDAR_WINDOW_V1`)

`test_planning_engine.py` comprueba en `Decimal`, cuantizado a 6 decimales:
- la ventana de días de negocio de Caracas;
- el neteo de devoluciones (`DESPACHADO → DEVUELTO`) y de reversos;
- la exclusión de ajustes, transferencias y movimientos internos;
- la media, la proyección y el stock de seguridad (ninguno, cantidad fija y días);
- el punto de reorden, el reservado y el disponible;
- la cobertura, la historia insuficiente y la historia parcial;
- la demanda cero, el turnover con existencia media reconstruida desde el ledger, la banda y la sugerencia `max(0, …)`.

La E2E comprueba en pantalla la cuenta de punta a punta: 12 recibidas, 10 salidas, 10 días, horizonte 5 y sin seguridad dan una sugerencia de 3,000000 y la banda «Rápida».

## Hallazgos

1. **Falso verde de un ciclo anterior (corregido).** ruff respeta `.gitignore`, y la regla `storage/` (datos locales) le ocultaba `app/modules/storage`, aunque Git lo versiona por una negación. La puerta «ruff limpio» del ciclo de clasificación de almacenamiento (`b40bbdc`) no examinó ese módulo, que tenía 10 errores. Corrección:
   - `respect-gitignore = false` en `pyproject.toml`; medido: así ruff examina exactamente esos 5 ficheros más;
   - los 10 errores, corregidos.
2. **Deuda previa de P1, no corregida (P2 no desarrolla Gobierno).** `test_naive_datetime_input.py::test_guard_d01_ningun_datetime_desnudo` falla en `HEAD`: `POST /gobierno/contrataciones/expedientes/{id}/evaluacion/aperturas` recibe `abierta_en` como `datetime` sin zona. Viene de `4c4be3d` (PROC-07). Este ciclo no toca ese módulo.
3. **Prueba inestable previa.** `AsyncButton.test.tsx` («previene doble envío») falló una vez con la suite completa y pasa 3 de 3 sola. Sin cambios de este ciclo en ese componente.
4. **Defecto de aislamiento del ciclo anterior (corregido).** `GET /storage/profiles/{item_id}` no validaba que el artículo fuera de la empresa activa y respondía 200 con un perfil vacío. No devolvía datos ajenos, pero la puerta `test_iso_barridos` fallaba, y ya fallaba en `b40bbdc`. Corrección:
   - la llamada 25 valida con `_item`, como ya hacía `save_profile`;
   - prueba nueva `test_storage_profile_isolation.py`.
5. **Deudas previas, no de esta Spec:** convergencia ORM y base (6 tablas de importaciones), `test_spec019_receipt`, `test_spec047_scheduler` y el corredor de integridad de Gobierno. Se informan y no se tocan en este ciclo.
6. **Carrera de sesión en E2E.** Dos `page.goto` seguidos tras `entrar` cancelan el refresco de sesión en vuelo y el siguiente refresco responde 401. La nueva E2E espera la carga; las existentes no lo sufren porque intercalan acciones. Es una propiedad del arnés, no del producto, pero cualquier E2E nueva debe esperarla.

## Suite PostgreSQL

Ejecutada sobre el PostgreSQL de QA con el analizador real, en dos tramos: la primera corrida agotó su límite de 90 minutos al 80 %, y el resto se corrió aparte. Total: 5233 pasan y 38 fallan. Cada falla se reprodujo sola y se comparó con una exportación limpia de `HEAD` (`b40bbdc`, por `git archive`, fuera de Git).

| Falla | Causa | Estado |
|---|---|---|
| 30 de `test_backup_create_pg` y `test_backup_restore_pg` | Entorno de la corrida: `pg_dump` y `pg_restore` no estaban en el PATH | Pasan con el PATH correcto |
| `test_iso_barridos::test_barrido_cabecera_manipulada` | Contaminación: Claude lanzó a la vez otra corrida contra la misma base | Pasa sola |
| `test_iso_barridos::test_barrido_ids_ajenos` | `GET /storage/profiles/{item_id}` respondía 200 con un artículo de otra empresa. Defecto del ciclo `b40bbdc`: también falla en `HEAD` | Corregido en la llamada 25. Pasa en PostgreSQL |
| `test_n10_convergence::test_el_orm_y_la_base_no_difieren_en_nada` | `created_by` anulable en el ORM y no en la base, en 6 tablas de importaciones | Previa: falla igual en `HEAD` |
| `test_spec019_receipt` (2) | `RECEIPT_EMPTY` antes de calidad | Previa: falla igual en `HEAD` |
| `test_gobierno_integridad_runner` | Gobierno (P1) | Previa: falla igual en `HEAD` |
| `test_naive_datetime_input::test_guard_d01…` | Gobierno PROC-07 (P1) | Previa: falla igual en `HEAD` |
| `test_spec047_scheduler::test_el_tick…` | Manejadores de respaldo registrados por el entorno | Previa: falla igual en `HEAD` |

**Ninguna falla de la suite PostgreSQL viene de la Spec 015.**
