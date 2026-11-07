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
