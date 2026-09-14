# ADR-D0-015 — Planificador de plataforma: temporizador del sistema que invoca órdenes idempotentes de KONTROL

| Campo | Valor |
|---|---|
| ID | D0-15 |
| Versión | v1 (2026-09-14) |
| Estado | **APPROVED · ACTIVE** |
| Aprobación | Decisión expresa del owner que cierra **OQ-047-01** (opción A), 2026-09-14 — `specs/047-notificaciones-tareas/clarifications.md` §4 |
| Acota | `ADR-009 — Cola y workers (diferimiento)`: abre **una** excepción controlada; el resto de ADR-009 sigue vigente |
| Materializa | `ADR-D0-003` §G: «ejecución periódica = planificador de plataforma, propietaria Spec 047» |
| Relacionado | `ADR-002` (instalación independiente por cliente) · `ADR-012` (auditoría) · `ADR-013` (idempotencia y concurrencia) |
| Specs afectadas | **047** (propietaria del marco) · 045 · 030 · 048 · 052 |

## Contexto

KONTROL no ejecutaba nada sin una petición HTTP. Eso dejaba sin ejecutor
recordatorios y escaladas de la 047, el vencimiento de pasos de la 045
(`mark_expired` sin llamador), la caducidad de reservas de la 030, los reintentos
de correo de la 048 y la retención de la 052.

`ADR-D0-003` asignó a la 047 el «planificador de plataforma». `ADR-009` aplazó
cola y workers hasta que una Spec demostrara la necesidad —«reportes pesados,
correos, tareas programadas»—, con comparación de alternativas y evaluación en
instalaciones independientes. La 047 es esa Spec; este ADR es esa evaluación.

## Alternativas

| Opción | Resultado |
|---|---|
| **A · Temporizador del sistema → orden canónica idempotente** | **Elegida** |
| B · Proyección en lectura, sin ejecución | Descartada: sin canal externo posible, sin ejecutor para 030, 045, 048 ni 052 |
| C · Llamada síncrona de cada dueña a la 047 | Descartada como mecanismo temporal: contradice CL-045-11 |
| D · Bucle, hilo o worker residente dentro del proceso | Descartada: ADR-009 |
| E · Celery, Redis, RabbitMQ, Kafka | Descartada: ADR-009 y consumo en instalaciones por cliente |

## Decisión

> **R-D0-15-1.** KONTROL ejecuta trabajo sin petición de usuario **solo** por esta
> cadena: temporizador del sistema operativo → orden canónica de KONTROL →
> manejador registrado → ejecución transaccional e idempotente → PostgreSQL como
> autoridad → auditoría y registro de ejecución.

> **R-D0-15-2.** El temporizador decide **cuándo**. La orden decide **qué**. El
> temporizador no contiene reglas de negocio, SQL, llamadas HTTP a endpoints ni
> argumentos que elijan trabajo.

> **R-D0-15-3.** Sin cola, broker, worker residente, daemon, hilo ni bucle de
> espera como autoridad. Esta excepción no autoriza ningún otro proceso de fondo.

> **R-D0-15-4.** Un solo tick a la vez por instalación, garantizado por un
> bloqueo consultivo de PostgreSQL mantenido durante el tick. El tick solapado se
> registra como `SKIPPED_OVERLAP` y no ejecuta manejadores.

> **R-D0-15-5.** Todo efecto tiene una clave lógica única respaldada por una
> restricción de la base. Repetir un tick —una, dos o diez veces— no duplica
> efectos. Un UUID aleatorio nunca es la clave lógica.

> **R-D0-15-6.** Tras una caída, cada manejador recupera según su semántica
> declarada y produce como máximo el efecto lógico vigente, nunca uno por cada
> tick perdido.

> **R-D0-15-7.** Cada manejador declara su Spec dueña. El marco (047) no contiene
> reglas de dominio: un manejador de otra dueña invoca su contrato canónico.

> **R-D0-15-8.** Los efectos llevan actor de sistema explícito —nunca un usuario
> ficticio— y contexto explícito de tenant, empresa y correlación.

> **R-D0-15-9.** Cada instalación de cliente tiene su propio temporizador contra
> su propia pila y base. No existe planificador central entre clientes.

> **R-D0-15-10.** El intervalo del temporizador es operacional y se fija en el
> despliegue. Ningún manejador depende de un intervalo concreto.

## Implementación canónica

| Pieza | Artefacto |
|---|---|
| Orden en el contenedor | `python -m app.modules.scheduler tick` |
| Orden en el host | `python kontrol.py scheduler-tick` → `docker compose exec -T backend python -m app.modules.scheduler tick` |
| Temporizador | `scripts/scheduler/kontrol-scheduler.service` + `.timer`, instalados por `scripts/install-scheduler.sh` con `KONTROL_SCHEDULER_INTERVAL` obligatorio |
| Registro | `scheduler_runs`, `scheduler_handler_runs` |
| Códigos de salida | `0` completado u omitido por solapamiento · `2` completado con errores de manejador · `1` fallo operacional |

## Consecuencias

- La 047 posee el marco, el registro de ejecuciones, la protección de solapamiento
  y la recuperación genérica.
- La 045, la 030, la 048 y la 052 pueden registrar manejadores que llamen a su
  contrato canónico. **No** se implementa su backlog dentro de la 047.
- El manejador de vencimiento de la 045 queda **registrado y deshabilitado**: un
  paso `EXPIRED` sale de la bandeja y la 045 no tiene camino de reapertura.
  Habilitarlo es decisión de la 045.

## Verificación

Guardas de arquitectura en `tests/test_spec047_architecture.py`: sin librerías de
cola, sin hilos ni bucles de espera en el planificador, temporizador sin reglas,
referencia a este ADR en el módulo. Mutaciones M047-13 a M047-17.
