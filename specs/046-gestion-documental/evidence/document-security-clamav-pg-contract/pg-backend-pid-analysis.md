# `carrera()` / `esperar_bloqueados()` (`tests/concurrency.py`)

Propósito (docstring): «Carreras forzadas contra PostgreSQL, sin depender de la suerte»: la primera transacción inserta y **no
confirma**; la segunda arranca en otra conexión, no ve esa fila (READ COMMITTED), pasa la comprobación previa y **queda bloqueada en
el índice único**; solo cuando `pg_stat_activity` muestra a esa conexión (`pid` de `pg_backend_pid()`) esperando un bloqueo
(`wait_event_type = 'Lock'`) se confirma la primera; la prueba falla si nunca hubo bloqueo («no se certifica una carrera que no ocurrió»).

| Registro | Valor |
|---|---|
| `RACE_HELPER_PURPOSE` | C: observar de forma determinista que la segunda transacción está bloqueada **y** apoyarse en la semántica de bloqueo de fila/índice de PostgreSQL (la segunda espera, no falla) |
| `PG_PRIMITIVE_REQUIRED_FOR_SEMANTICS` | sí: en SQLite no hay bloqueo de índice que haga esperar a la segunda transacción con la primera sin confirmar; la segunda recibiría `database is locked` o escribiría sobre una lectura obsoleta (demostrado en AUTH-ROTACION-SQLITE-HILOS) |
| `PG_PRIMITIVE_REQUIRED_ONLY_FOR_DETERMINISM` | no: también para el determinismo (`esperar_bloqueados` es la condición de la barrera), pero no solo |
| `SQLITE_EQUIVALENT_EXISTS` | no (`pg_backend_pid`, `pg_stat_activity` no existen; `motor_para_hilos` da conexiones propias pero no la espera en el índice) |
| `SQLITE_EQUIVALENT_WOULD_BE_SEMANTICALLY_FAITHFUL` | no: la garantía FR-046-115 la decide PostgreSQL (`conc-046-concurrent-version-delta.md`: «PostgreSQL decide», G-CONC-046-06 «PostgreSQL autoridad») |
| `SQLITE_EXECUTION_WITH_CURRENT_HELPER` | hoy no se llega (422 antes); con analizador presente fallaría con `OperationalError: no such function: pg_backend_pid` |

`DOCUMENT_RACE_CURRENTLY_PG_SPECIFIC = YES` · `PG_SPECIFIC_REASON = semántica de bloqueo + observabilidad`. No se diseña un
sustituto para SQLite: el contrato no lo pide.
