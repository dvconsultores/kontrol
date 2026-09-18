# DEUDA TÉCNICA

| ID | Categoría | Deuda | Severidad | Spec | Riesgo si no se paga |
|---|---|---|---|---|---|
| DT-01 | Estructural | `SalesInvoice` sin FK a `sales_orders` | BLOCKER | 034 | Cada factura emitida sin vínculo es histórico irrecuperable |
| DT-02 | Estructural | Líneas de documento sin `uom_id`/`presentation_id` | CRITICAL | 011 | Todo documento histórico queda sin la dimensión; backfill imposible |
| DT-03 | Estructural | `location_id` nullable y nunca escrito | CRITICAL | 022, 023 | El Kardex histórico no tendrá ubicación; reconstrucción imposible |
| DT-04 | Estructural | `cost_center_id` como `String(36)` sin tabla ni FK | HIGH | 007 | Datos sucios que habrá que normalizar con migración de datos |
| DT-05 | Estructural | `price_list`/`zone`/`payment_term` como texto libre | HIGH | 012 | Idem; además viola P8 |
| DT-06 | Backend | `organization` y `master_data` sin auditoría | HIGH | 006, 051 | Vacío permanente en el rastro de auditoría; no reconstruible |
| DT-07 | DB | 2 tablas muertas (`outbox_events`, `feature_flags`) | LOW | 048, 001 | Confunden el inventario; decidir usar o retirar |
| DT-08 | DB | `alembic check` nunca ejecutado contra PostgreSQL | BLOCKER | 001, 052 | Drift silencioso descubierto en producción |
| DT-09 | DB | 36 columnas de cantidad en `Float` | LOW | ADR-012 | Aceptado por ADR; revisar si aparecen cantidades fraccionarias finas |
| DT-10 | Infra | `KONTROL_IMAGE_TAG` con default `latest` | MEDIUM | 052 | Viola P14; despliegue no reproducible |
| DT-11 | Infra | Backup/restore nunca ejecutado | BLOCKER | 053 | Sin garantía de recuperación; RPO/RTO indefinidos |
| DT-12 | Infra | `report_jobs` ejecutado en proceso, sin cola | MEDIUM | 048, 050 | Reportes grandes bloquean el worker web |
| DT-13 | QA | 0 pruebas de página frontend | HIGH | 054 | Las 77 pantallas solo están cubiertas por el crawler (200 OK), no por comportamiento |
| DT-14 | QA | Rendimiento medido sobre base vacía | MEDIUM | 054 | N+1 e índices faltantes invisibles |
| DT-15 | Seguridad | Sin SBOM | MEDIUM | 055 | Sin inventario de dependencias para respuesta a CVE |
| DT-16 | Seguridad | Sin rate limiting global (solo lockout de login) | MEDIUM | 055 | Superficie de abuso en el resto de la API |
| DT-17 | Frontend | Sin protección de cambios sin guardar | MEDIUM | 005 | Pérdida de trabajo del usuario; exigido por Vol. 2 §2 |
| DT-18 | Documental | 4 documentos de estado desfasados | MEDIUM | 054 | El expediente se contradice; riesgo en auditoría externa |

## Orden de pago recomendado

1. **DT-08, DT-11** (Ola 0) — sin PostgreSQL real ninguna otra evidencia es válida.
2. **DT-06, DT-18** (Ola 0) — cierran afirmaciones falsas ya publicadas.
3. **DT-01, DT-02, DT-03** (Olas 1-2) — **cuanto más tarde, más documentos históricos quedan sin la dimensión**. Es deuda que se encarece cada día de operación.
4. **DT-04, DT-05** (Ola 2) — normalizar antes de que crezca el volumen.
5. Resto según ola correspondiente.

## Nota sobre DT-01/02/03

Estas tres son las únicas deudas del listado cuyo coste **crece con el tiempo de operación**.
Una FK añadida hoy admite backfill; añadida tras un año de facturación deja un hueco histórico
permanente. Deben tratarse con prioridad superior a su severidad nominal.

---

## Deltas dirigidos posteriores al registro

| ID | Deuda | Estado | Evidencia |
|---|---|---|---|
| **MIGR-0033-FK-HUERFANA** | Actualizar una instalación con histórico abortaba en la migración `0033`: exigía una clave foránea de empresa que la fila preservada a propósito por `0016` violaba | **CLOSED / CONVERGED** (2026-09-16) | `specs/001-fundacion/spec052-migr-0033-legacy-fk-delta.md` · `evidence/migr-0033/` |
| **AUTH-MC-INTERMITENTE** | El arnés `conftest_multicompany` pide un token nuevo en cada llamada; en tandas completas largas alguna petición recibe `401` y tumba una prueba de la Spec 030 que pasa aislada | **OPEN** — dueña sugerida 054 | Tandas 2 y 3 de `evidence/migr-0033/` |

**DT-08** (`alembic check` nunca ejecutado) quedó cerrada al ejecutarse en la auditoría
maestra; las demás del registro conservan el estado que allí se midió.

| **SEIS FRONTERAS `float` DE TESORERÍA** | `SessionOpen.opened_amount`, `SessionMovementCreate.amount`, `TransferCreate.amount`, `ReconciliationCreate.opening_balance` y `closing_balance`, `IgftEvaluateBody.amount` | **CLOSED / CONVERGED** (2026-09-16) | `specs/006-tesoreria/spec038-remaining-float-boundaries-delta.md` · `evidence/float-038-c/` |

Con FLOAT-038-A, FLOAT-038-B y FLOAT-038-C, **el borde monetario público de Tesorería
queda sin un solo `float`**. Lo que sigue en `Float` en ese módulo es `match_score`,
que es una puntuación de coincidencia y no dinero.

| **CLOCK-013** | Las pruebas de maestros financieros construían sus fechas con `date.today()` —el día civil del proceso— mientras el producto mide en UTC; el resultado dependía de la zona horaria y la suite exigía `TZ=UTC` para ser verde | **CLOSED / CONVERGED** (2026-09-17) | `specs/006-tesoreria/spec013-clock-determinism-delta.md` · `evidence/clock-013/` |
| **POLICY-CLOCK-LOCAL** | `active_policy` usa el día civil del servidor mientras la resolución de tasas usa el instante UTC. Coherente sobre el despliegue documentado (servidor en UTC, `ADR-D0-001`); divergiría sobre un servidor en otra zona | **OPEN** — observación, dueña 013/052 | `spec013-clock-determinism-delta.md` §6 |

| **POLICY-CLOCK-LOCAL** | El día civil de negocio salía del reloj del proceso: con el despliegue en UTC, KONTROL aplicaba la política de cambio, la regla IGTF y la versión de la regla fiscal del día siguiente durante cuatro horas diarias. 26 usos en 7 módulos y 2 pantallas, sin una sola conversión de zona en todo el producto | **CLOSED / CONVERGED** (2026-09-17) | `specs/001-fundacion/spec001-business-timezone-delta.md` · `evidence/policy-clock-local/` |

| **E2E-HELPER-EMPRESA-AMBIGUO** | Cuatro suites E2E buscaban «Activar» por subcadena, casaban con «Desactivar» y apagaban la empresa que necesitaban activa: 12 fallos y 6 pruebas sin llegar a correr, con la señal de la suite completa inservible | **CLOSED / CONVERGED** (2026-09-17) | `specs/012-auditoria-integral-e2e/spec054-company-helper-delta.md` · `evidence/e2e-helper-empresa/` |
| **E2E-SEED-EMPRESA-UNICA** | `qa/pg-e2e-seed.py` deja una empresa y `qa/spec047-e2e-seed.py` añade una segunda. Con la segunda activa, las suites cuyos usuarios no están acotados caen en la compuerta «Seleccione una empresa» y no llegan a su pantalla. Causa raíz medida: `create_user` no escribe ninguna fila en `user_scopes` y sin alcance declarado el servidor admite todas las empresas del tenant (`company_context.py:82`), así que el conjunto de empresas de un usuario de prueba depende de lo que haya sembrado otro. Radio medido: de las seis suites que crean usuarios por API **solo `order-confirmation` entra por la interfaz con uno**, de ahí un único fallo. Causalidad en dos sentidos: con `D2` activa 6/7, con `D2` inactiva 7/7. Clasificada `INDEPENDENT_ROOT_CAUSE` frente al arranque de N6. **Causa exacta**: el fixture declaraba la empresa en `user_roles` —el alcance del permiso— creyendo que limitaba el acceso, cuando la autoridad de acceso es `user_scopes`, que no tiene ni API ni interfaz. El alcance se declara ahora con `qa/alcance_de_usuario.py`, autoridad única del repositorio, invocada desde el ayudante canónico `e2e/helpers/usuario.ts` | **CLOSED / CONVERGED** (2026-09-17) | `specs/012-auditoria-integral-e2e/spec054-user-scope-fixture-delta.md` · `evidence/user-scope-fixture/` |
| **E2E-N6-ARRANQUE** | `n6-multicompany` y `n6-a11y-responsive` (25 pruebas) usaban los usuarios `ua`/`ub`/`uab` que su propio arranque creaba en **otra base** —un fichero SQLite que además borraba al empezar—, así que contra la base del E2E la sesión no abría. El mundo pasa a definirse una sola vez en `qa/n6_world.py`, se siembra en la base que sea con `qa/n6-e2e-seed.py` y la cadena entera la ejecuta `e2e/global-setup.ts` antes de la suite. 25/25 en Chromium, Firefox y WebKit | **CLOSED / CONVERGED** (2026-09-17) | `specs/012-auditoria-integral-e2e/spec054-n6-seed-orchestration-delta.md` · `evidence/n6-multicompany-startup/` |
| **E2E-031-RESERVAS** | `putaway.spec.ts:341` y `picking.spec.ts:314` afirmaban sobre el **recuento global** de reservas de la empresa —un conjunto compartido que crece mientras la suite corre: medido, de 330 a 369 en un mismo ciclo— cuando lo que querían decir era «mi reserva sigue siendo la que era». `picking` además enviaba `?source_order_id=`, que el servidor no declara y por tanto ignora en silencio. El endpoint cumple su contrato («reservas activas/históricas», sin filtro por pedido). Corregido en las pruebas con un ayudante canónico de identidad | **CLOSED / CONVERGED** (2026-09-17) | `specs/012-auditoria-integral-e2e/spec054-reservation-identity-delta.md` · `evidence/reservation-identity/` |
| **API-QUERY-SILENCIOSA** | `GET /inventory/reservations` acepta sin protestar un parámetro de consulta que no declara: `?source_order_id=<inexistente>` devuelve la lista entera. Un cliente puede creer que filtró cuando no filtró. Cambiarlo es semántica pública | **OPEN** — dueña 023 | `spec054-reservation-identity-delta.md` §19 |
| **E2E-SIN-TYPECHECK** | `tsc -p tsconfig.json` solo cubre `src`: el directorio `e2e/` no se comprueba de tipos en el flujo del proyecto y un error de tipos solo aparece como fallo en ejecución | **OPEN** — dueña 054 | `spec054-reservation-identity-delta.md` §19 |
| **INV-MOVTYPE-CARRERA** | `create_movement_type` consultaba y luego insertaba sin nada entre medias: dos altas simultáneas del mismo código pasaban ambas la consulta y la segunda subía como **500** en vez del `409 MOVEMENT_TYPE_DUPLICATE` que el camino secuencial ya contestaba. Medido con carrera forzada sobre PostgreSQL: `IntegrityError` crudo, `pgcode=23505`, restricción `uq_movement_types_company_code`. La creación baja al servicio con el patrón que el propio módulo ya usaba —savepoint, captura de esa restricción, conflicto de dominio—; la ruta se queda con confirmar | **CLOSED / CONVERGED** (2026-09-18) | `specs/003-inventario-logistica/spec023-movement-type-create-race-delta.md` · `evidence/movement-type-race/` |
| **MOVTYPE-GLOBAL-SIN-UNICIDAD** | Un tipo de movimiento de toda la instalación lleva `company_id` nulo, y en PostgreSQL los nulos no colisionan entre sí: `UNIQUE (company_id, code)` no garantiza nada ahí. Medido: dos altas concurrentes dejan **dos filas**. Protegerlo exige un índice único parcial y, por tanto, migración; pero la Spec **no declara** unicidad del código —su modelo de datos solo dice «company_id/global»—, así que decidir si dos tipos globales pueden compartir código es una decisión de identidad de negocio | **OPEN** — `MATERIAL_DECISION_REQUIRED`, dueña 023 | `spec023-movement-type-create-race-delta.md` §7 |
| **SEED-EMPRESA-CODIGO-NO-UNICO** | `companies` no tiene índice único sobre `(tenant_id, code)`: una mutación creó tres `D2` en el mismo tenant sin que la base se quejara. La identidad de empresa descansa en la disciplina de cada guion, no en el motor. Corregirlo es una migración | **OPEN** — dueña por decidir | `spec054-n6-seed-orchestration-delta.md` §20 |
