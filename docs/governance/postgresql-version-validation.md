# VALIDACIÓN DE VERSIÓN DE POSTGRESQL

**Control 3 del Gate pre-implementación de la Spec 008**
Fecha de ejecución: **2026-08-30** · Rama `develop` · Ejecutor: equipo de arquitectura

---

## 1. La divergencia que se resuelve

| Fuente | Versión | Estado antes de este documento |
|---|---|---|
| `ADR-D0-001` — PostgreSQL / production parity | **18.x** | Aprobado, referencia arquitectónica vigente |
| DOC-08 — Estándar de stack | **18** | Coherente con el ADR |
| Cierre real de la Spec 045 (`COMPLETE_100`) | **16.2** | Ejecutado sobre `pgserver`, único motor disponible entonces |

La Spec 045 alcanzó `COMPLETE_100` con evidencia sobre PostgreSQL **16.2**, no sobre
la versión que fija el ADR. La divergencia era real y no debía seguir acumulándose:
un ADR que dice 18 y una QA que corre 16 no es una arquitectura, son dos.

---

## 2. Qué se intentó primero

La opción preferida era Docker oficial de PostgreSQL 18.x. **No fue posible**, y la
causa se determinó en lugar de suponerse:

| Vía | Resultado | Causa verificada |
|---|---|---|
| Docker oficial | **No disponible** | No hay binario `docker` ni `podman` en el entorno |
| `apt install postgresql-18` | **No disponible** | `sudo` exige contraseña interactiva; no hay privilegio de root |
| Actualizar `pgserver` | **Insuficiente** | La última versión publicada es `0.1.4` y empaqueta PostgreSQL **16.2**. No existe una versión de `pgserver` con PostgreSQL 18 |

Ninguna de las tres es una limitación de KONTROL: son limitaciones del entorno de
ejecución. Esa distinción importa, porque determina si procede tocar el ADR.

## 3. Cómo se obtuvo PostgreSQL 18 real

Se instalaron los **paquetes oficiales del proyecto PostgreSQL** (repositorio PGDG,
`apt.postgresql.org`) extraídos con `dpkg-deb -x` en un prefijo sin privilegios. Son
los mismos binarios que instalaría `apt`, sin ejecutar sus scripts de sistema ni
tocar nada fuera del directorio de trabajo.

| Paquete | Versión | Origen |
|---|---|---|
| `postgresql-18` | `18.6-1.pgdg12+2` | `apt.postgresql.org/pub/repos/apt` (bookworm-pgdg) |
| `postgresql-client-18` | `18.6-1.pgdg12+2` | Ídem |
| `libpq5` | `18.6-1.pgdg12+2` | Ídem |
| `liburing2` | `2.3-3` | `deb.debian.org` (dependencia de sistema) |

Sin Docker, sin root, sin tocar infraestructura productiva y sin usar datos
productivos.

---

## 4. Entorno validado

| Parámetro | Valor obtenido | Exigido por `ADR-D0-001` | ¿Cumple? |
|---|---|---|---|
| Versión | **PostgreSQL 18.6** | 18.x | **Sí** |
| Encoding | `UTF8` | `UTF8` | Sí |
| Timezone del servidor | `UTC` | `UTC` | Sí |
| Base de datos | `kontrol` | `kontrol` | Sí |
| Rol de migración | `kontrol_migrator` (DDL) | Separado | Sí |
| Rol de aplicación | `kontrol_app` — `NOSUPERUSER`, `NOCREATEDB`, `NOCREATEROLE` | Sin `CREATE`, sin `SUPERUSER` | Sí |
| Extensiones | `pgcrypto` 1.4 (+ `plpgsql`) | Lista blanca: solo `pgcrypto` | Sí |

Arranque limpio, `pg_ctl start` con espera de disponibilidad, sin errores en el log.

---

## 5. Resultados de la validación

### 5.1 Cadena de migraciones

```
alembic upgrade head    →  0001 … 0016_approvals_backfill   APLICADA COMPLETA
alembic current         →  0016_approvals_backfill (head)
alembic heads           →  0016_approvals_backfill (head)
```

Las 16 migraciones existentes aplican sobre PostgreSQL 18.6 **sin ninguna
modificación**. Ninguna incompatibilidad de sintaxis, de tipo ni de catálogo.

### 5.2 Esquema resultante

| Métrica | Valor |
|---|---|
| Tablas en `public` | 153 |
| Columnas `timestamptz` | 362 |
| Columnas `timestamp` **sin** zona | **0** |
| Columnas `numeric` | 78 |
| Claves foráneas | 164 |
| Índices parciales | 1 (`uq_approval_requests_open_document`, Spec 045) |

El índice parcial de idempotencia de la Spec 045 se crea correctamente y con el
predicado esperado.

### 5.3 Drift ORM ↔ esquema — la comprobación decisiva

`alembic check` se ejecutó sobre **ambas** versiones, con la misma cadena aplicada
sobre base limpia:

| Motor | Líneas de drift |
|---|---:|
| PostgreSQL 16.2 (`pgserver`, base `kontrol_clean`) | **18** |
| PostgreSQL 18.6 (PGDG, base `kontrol`) | **18** |

**Los dos conjuntos son idénticos.** El drift es el ya conocido y escalado en el
cierre de la Spec 045 —`license_states.license_id`, dos columnas `NOT NULL` de
licenciamiento (Spec 010) y diferencias de reflexión de índices y constraints— y
**no** hay una sola diferencia atribuible a la versión del motor.

### 5.4 Suite de backend

```
276 passed in 268.53s
```

La suite **completa**, sin exclusiones, sobre PostgreSQL 18.6. Mismo resultado que
sobre 16.2 en el cierre de la Spec 045: 276 pruebas, 276 pasadas.

---

## 6. Compatibilidad 16 / 17 / 18

| | PostgreSQL 16 | PostgreSQL 17 | PostgreSQL 18 |
|---|---|---|---|
| Cadena de migraciones de KONTROL | Aplica (probado, 16.2) | No probado | **Aplica (probado, 18.6)** |
| Suite de backend | 276/276 (Spec 045) | No probado | **276/276** |
| Drift ORM ↔ esquema | 18 líneas | No probado | **18 líneas, idénticas** |
| Índices parciales, `timestamptz`, `numeric` | Correctos | — | **Correctos** |
| Soporte upstream a 2026-08-30 | Sí (fin nov. 2028) | Sí | **Sí — versión objetivo** |

No se detectó ninguna funcionalidad de KONTROL que dependa de una versión concreta.
La compatibilidad observada 16↔18 es total, lo que era esperable: el esquema no usa
características específicas de versión.

---

## 7. Decisión

> **`ADR-D0-001` continúa VIGENTE y SIN MODIFICACIÓN. Queda
> `CONFIRMED_BY_EXECUTION`.**

No procede supersesión ni enmienda: el ADR fijaba PostgreSQL 18.x y PostgreSQL 18.x
funciona. Lo que estaba desalineado no era la decisión, era la evidencia.

### Consecuencias vinculantes

1. **PostgreSQL 18.x es obligatorio** para la aceptación final de toda Spec nueva a
   partir de esta fecha, empezando por la Spec 008.
2. **SQLite** mantiene el ámbito que ya le fija `ADR-D0-001` R-D0-01-2: pruebas
   unitarias sin SQL de dialecto, transacciones, bloqueos ni tipos numéricos o de
   fecha. Sin cambios.
3. La **Spec 045** conserva su `COMPLETE_100`. Su evidencia se ejecutó sobre 16.2,
   y esta validación demuestra que su comportamiento sobre 18.6 es idéntico:
   misma suite, mismo resultado, mismo drift. No se reabre.
4. **Versión mínima soportada: 16.** Verificada por ejecución. **Versión objetivo y
   de aceptación: 18.x.** PostgreSQL 17 no está probado y por tanto no se declara
   soportado.
5. La infraestructura de QA debe converger a PostgreSQL 18.x. `pgserver` (16.2)
   queda como recurso auxiliar, **no** como motor de aceptación.

---

## 8. Reproducibilidad

El aprovisionamiento de PostgreSQL 18.6 usado aquí es reproducible sin Docker y sin
root: descarga de los `.deb` oficiales de PGDG, extracción con `dpkg-deb -x`,
`initdb -E UTF8`, `timezone = 'UTC'`, y los dos roles del ADR.

**Pendiente para la Spec 054 (QA/CI), no para 008:** integrar este aprovisionamiento
en `qa/pg-provision.sh` junto al camino con Docker, de modo que CI levante
PostgreSQL 18.x efímero. Queda registrado como tarea de 054; no bloquea la
implementación de 008, que se valida contra la instancia 18.6 aquí verificada.

---

## 9. Estado final

| Control | Resultado |
|---|---|
| Versión que fija el ADR | PostgreSQL 18.x |
| Versión realmente validada | **PostgreSQL 18.6** |
| Migraciones 0001→0016 | **Aplican** |
| Suite de backend | **276/276** |
| Drift respecto a 16.2 | **Ninguno** |
| `ADR-D0-001` | **VIGENTE · CONFIRMED_BY_EXECUTION** |
| Divergencia 16.2 vs 18.x | **RESUELTA** |

Una sola verdad arquitectónica: **PostgreSQL 18.x**, ahora con evidencia de
ejecución detrás.
