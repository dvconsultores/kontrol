# T052 · mediciones

## En este ciclo

| Métrica | Valor | Motivo |
|---|---|---|
| `QA_DATABASE_SIZE` | NOT_MEASURED | Sin `.venv`, PostgreSQL de QA ni `pg_dump` en este puesto |
| `QA_DOCUMENT_STORAGE_SIZE` | NOT_MEASURED | Igual |
| `BACKUP_PACKAGE_SIZE` | NOT_MEASURED | Igual |
| `BACKUP_CREATE_DURATION` | NOT_MEASURED | Igual |
| `BACKUP_VERIFY_DURATION` | NOT_MEASURED | Igual |

Aprovisionar ese entorno implica instalar dependencias y PostgreSQL. Este puesto solo dispone de Python 3.13, sin la rueda `pgserver` (cp311) ni compilador. No se ha hecho y no se fabrica ninguna cifra.

## Registrado (`specs/001-fundacion/evidence/backup-restore/certificacion.md`, 2026-10-28)

| Métrica | Valor | Alcance |
|---|---|---|
| Copia por CLI | 0,20 s | Conjunto sintético pequeño |
| Paquete | 768 000 bytes | Igual |
| Restauración por CLI | 1,30 s | Igual |
| RTO sin espera TOTP | 5,1 s | Igual |
| `BACKUP_VERIFY_DURATION` | No registrado | — |

Estas cifras no demuestran capacidad productiva. Tampoco muestran que `SCHEDULED_KBK` no pueda cumplir el RPO, así que la arquitectura se mantiene condicionada a la puerta de capacidad del delta §4.

## Medido sobre el árbol y fuentes públicas, 2026-11-06

| Hecho | Valor |
|---|---|
| Debian trixie | `postgresql-client-17` 17.11 |
| PGDG `trixie-pgdg` | `postgresql-client-18` 18.6-1.pgdg13+2 |
| Trixie sin PGDG | No alcanza a un servidor PostgreSQL 18 según `check_tool_compatible` |

## T053 · medido el 2026-11-07

| Campo | Valor |
|---|---|
| `BASE_IMAGE` | `python:3.13.16-slim-trixie@sha256:70729b46…`, sin cambio |
| `PACKAGE_SOURCE` | `https://apt.postgresql.org/pub/repos/apt`, `trixie-pgdg main` (Release del 2026-11-05) |
| `SELECTED_PG_CLIENT_PACKAGE` | `postgresql-client-18` y `libpq5` |
| `SELECTED_PG_CLIENT_VERSION` | `18.6-1.pgdg13+2`; el repositorio conserva 18.4 y 18.3 |
| `PG18_COMPATIBILITY_BASIS` | `check_tool_compatible` exige cliente >= servidor |
| `REPRODUCIBILITY_BASIS` | Versión exacta y comprobación en build. PGDG puede retirar versiones: la construcción falla, no deriva |
| `TRUST_BASIS` | Clave sha256 `01440685…8e76`, huella `B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8`, `signed-by` y prioridad 100 |
| `DOCKER_AVAILABLE` | 0 |
| `T053_RUNTIME_CERTIFIED` | NO |

## T052 · certificación local

SQLite con ClamAV: 4769 recogidas, 2974 aprobadas, 0 fallidas, 0 errores, 1795 omitidas. Vitest: 1332 aprobadas al cierre. mypy `app`: 154, sin errores nuevos. OpenAPI y catálogo: 689, con una sola alta autorizada. Migración 0076 subir, bajar y subir en SQLite aislada; el árbol Alembic completo no corre en SQLite por una migración anterior a este ciclo.

Mutaciones: 48 ejecuciones. Dos supervivientes equivalentes por defensa redundante (quitar la protección de última válida o última durable por separado); quitar las tres defensas a la vez muere.

`REAL_BACKUP_RESTORE`, `CAPACITY_MEASUREMENT_STATUS`, `OFF_HOST_OPERATIONAL_CERTIFICATION`, `SPEC047_NOTIFICATION_DELAY_IMPACT`: NOT_MEASURED. La exclusión por bloqueo consultivo y el índice parcial no se han probado con concurrencia real en PostgreSQL.
