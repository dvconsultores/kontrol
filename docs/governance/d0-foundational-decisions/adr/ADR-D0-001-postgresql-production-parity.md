# ADR-D0-001 — PostgreSQL como motor obligatorio con paridad de producción

| Campo | Valor |
|---|---|
| ID | D0-01 |
| Estado | **APPROVED** |
| Fecha | 2026-08-29 |
| Responsable | Arquitecto de datos · DBA PostgreSQL · DevOps · QA Lead |
| Extiende | `ADR-003 — PostgreSQL como Fuente de Verdad` (PROPUESTO) |
| Specs afectadas | Todas (56) · críticamente 001, 023, 027, 030, 034, 042, 052, 053, 054 |

## Problema

`ADR-003` decidió que PostgreSQL es la fuente de verdad **en producción**, pero no dijo nada sobre
el motor usado para desarrollar y probar. El resultado, verificado en el GAP Analysis: las 223
pruebas de backend, los 20 flujos E2E in-process y las 3 pruebas de migración corren sobre **SQLite**.

## Por qué debe decidirse ahora

Cada Spec que se escriba a partir de aquí acumulará evidencia sobre un motor que no es el de
producción. El riesgo no es teórico: la migración `0012_numeric_money` introdujo una regresión
`Decimal + float` (`KQA-100`, CRITICAL) que SQLite no reveló y que rompió factura, pago, cobro,
notas y CxC/CxP. Se detectó por casualidad en una corrida funcional, no por la suite.

Diferencias que SQLite no expresa y que KONTROL usa de forma central:

| Área | SQLite | PostgreSQL | Riesgo en KONTROL |
|---|---|---|---|
| `Numeric` | almacena como float | decimal exacto | Importes fiscales |
| `timezone=True` | colapsa a naive | `timestamptz` | Períodos fiscales, vigencias de reglas |
| `SELECT … FOR UPDATE` | ignorado | bloqueo real | **Reserva de inventario, correlativos fiscales** |
| Nivel de aislamiento | serializado por archivo | MVCC configurable | Concurrencia de dos vendedores |
| Constraints diferibles | no | sí | Integridad transaccional |
| `ALTER COLUMN` | recrea tabla | nativo | Migraciones |
| JSON / índices parciales / UUID | limitado | nativo | Atributos, auditoría |

## Evidencia

- `qa/runs/KONTROL-QA-20260811-LOCAL/retest-results.md` — `KQA-100`.
- `specs/012-auditoria-integral-e2e/pending-validations.md` — `alembic upgrade`/`check` pendientes.
- `resources/backend/tests/test_migrations_offline.py` — la cadena solo **compila** en dialecto PG, no se aplica.
- `docs/roadmap/current-quality-baseline.md` — línea base medida.

## Alternativas

**A. Mantener SQLite para pruebas y validar en PG solo antes de release.**
Barata a corto plazo. Descartada: es exactamente la situación actual, y ya produjo un CRITICAL.
Descubrir el fallo al final del ciclo es el escenario más caro.

**B. PostgreSQL obligatorio en todo entorno, incluidas pruebas unitarias.**
Máxima fidelidad. Descartada como regla absoluta: penaliza la velocidad de las pruebas puras
(formato, cálculo, máquinas de estado en memoria) sin aportar fidelidad, porque esas pruebas no
tocan SQL.

**C. PostgreSQL obligatorio salvo excepción declarada y justificada.** ← **RECOMENDADA**
Paridad donde importa, velocidad donde no cuesta fidelidad, y la excepción es explícita y auditable
en vez de implícita.

## Regla definitiva

> **R-D0-01-1.** PostgreSQL es el motor obligatorio para desarrollo integrado, pruebas de
> integración, pruebas de contrato, E2E, QA, staging y producción.
>
> **R-D0-01-2.** SQLite se admite **únicamente** en pruebas unitarias que no ejecuten SQL
> específico del dialecto ni dependan de transacciones, bloqueos, tipos numéricos o de fecha.
> Toda prueba que lo use debe declararlo explícitamente con un marcador; una prueba sin marcador
> que se ejecute sobre SQLite es un fallo de la suite, no una prueba válida.
>
> **R-D0-01-3.** Ninguna Spec puede alcanzar `COMPLETE_100` sin evidencia de ejecución sobre
> PostgreSQL. Esta regla es de aplicación inmediata y retroactiva: las 25 Specs hoy
> `SUBSTANTIALLY_COMPLETE` no cambian de estado, pero su techo queda fijado hasta que exista
> esa evidencia.
>
> **R-D0-01-4.** El aislamiento entre pruebas se logra por transacción con rollback, no por
> borrado de datos, y nunca compartiendo una base entre ejecuciones concurrentes.

## Parámetros del motor

| Parámetro | Valor decidido | Fundamento |
|---|---|---|
| Versión | **PostgreSQL 18.x** | `specs/001-fundacion/dependency-matrix.md`; ya declarada en `compose.yaml` |
| Encoding | `UTF8` | Razones sociales, RIF, direcciones |
| Timezone del servidor | **`UTC`** | P4/P5: los documentos fiscales se comparan en instante absoluto; la zona local es presentación |
| Base de datos | `kontrol` | — |
| Rol de aplicación | `kontrol_app` — sin `CREATE`, sin `SUPERUSER` | Mínimo privilegio (P6) |
| Rol de migración | `kontrol_migrator` — DDL, usado solo por el entrypoint | Separación de privilegios |
| Extensiones autorizadas | **`pgcrypto`** (generación de UUID y hash) | Lista blanca cerrada: cualquier otra extensión exige enmienda de este ADR |
| Pooling | Pool de la aplicación con tamaño configurable y `pool_pre_ping` | Instalación de un solo nodo (P9) |
| Base de pruebas | Base dedicada por ejecución, creada desde plantilla | Aislamiento |

Los valores concretos de tamaño de pool y recursos son configuración por instalación, no decisión de producto.

## Pruebas mínimas exigidas (a construir en Spec 054, no aquí)

1. Base vacía → `alembic upgrade head` → `seed` → arranque → suite completa.
2. `alembic check` sin drift entre ORM y esquema.
3. Verificación de que las 48 columnas declaradas `timezone=True` son `timestamptz`.
4. Backup → entorno limpio → restore → comparación de esquema, datos, licencia e `installation_id`.
5. Concurrencia: dos transacciones compitiendo por la misma unidad de stock (ver ADR-D0-003).

## Impacto

| Dimensión | Impacto |
|---|---|
| Frontend | Ninguno |
| Backend | Ninguno en código de negocio; sí en `conftest.py` y arranque de pruebas |
| Base de datos | Ninguno estructural; se ejercita lo ya declarado |
| Integraciones | Ninguno |
| QA | **Alto** — reconstrucción del arranque de la suite y del CI |
| Seguridad | Positivo — separación de roles y mínimo privilegio |
| Fiscal | Positivo — precisión decimal y timestamps reales bajo prueba |

## Migración / compatibilidad

**`NO_MIGRATION`** — no cambia el esquema ni los datos. Es infraestructura de pruebas y despliegue.
Riesgo esperado: al ejecutar por primera vez sobre PG aparecerán fallos hoy ocultos. **Eso es el
objetivo del cambio, no un efecto secundario.**

## Specs bloqueadas hasta aplicar esta decisión

Ninguna Spec queda bloqueada para **empezar**. Todas quedan bloqueadas para **cerrarse**.

## Criterios de aceptación

- [ ] `compose.dev` levanta PostgreSQL 18.x con healthcheck y volumen persistente.
- [ ] La suite de backend corre contra PG y pasa; las excepciones SQLite están marcadas y son ≤ 10 % de los casos.
- [ ] CI levanta PostgreSQL efímero y ejecuta `upgrade head` + `check`.
- [ ] Las cinco pruebas mínimas existen y pasan.
- [ ] Los roles `kontrol_app` y `kontrol_migrator` existen con privilegios separados.

## Preguntas pendientes

Ninguna que impida aprobar. El dimensionamiento de recursos es configuración por instalación.

## Estado final

**APPROVED** — decisión técnica con evidencia suficiente; no requiere validación empresarial ni legal.
