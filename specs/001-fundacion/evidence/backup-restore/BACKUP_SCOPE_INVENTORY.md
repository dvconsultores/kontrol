# BACKUP_SCOPE_INVENTORY (06)

Columnas comunes:
- REQUIRED_FOR_RESTORE: sí en todas las filas, salvo B12 y B13.
- ENCRYPTION_REQUIRED: sí, AEAD en el paquete; no aplica a lo excluido.
- EXTERNAL_SECRET_DEPENDENCY: ninguna, salvo B8, B9 y B11 (indicada en su motivo).

| ITEM_ID | STATE_TYPE | OWNER_SPEC | LOCATION | PERSISTENCE_TECH | BACKUP_STATUS | CONSISTENCY_REQUIREMENT | VERIFY_METHOD | RESTORE_METHOD | RATIONALE |
|---|---|---|---|---|---|---|---|---|---|
| B1 | Esquema (tablas, columnas) | 001 | PostgreSQL `public` | PG | INCLUDED | Instantánea exportada | Lista de tablas, recuentos y huellas | `pg_restore --single-transaction` | Volcado en formato custom |
| B2 | Datos | Todas | PG | PG | INCLUDED | ídem | Recuento y huella por tabla | ídem | — |
| B3 | Secuencias, índices, restricciones | 001 | PG | PG | INCLUDED | ídem | Catálogo `pg_indexes`/`pg_constraint`; secuencias | ídem | — |
| B4 | Funciones y triggers de inmutabilidad (0061) | 001 | PG | PG | INCLUDED | ídem | Los 3 triggers en `pg_trigger` y UPDATE/DELETE/TRUNCATE rechazados | ídem | Sin ellos no hay RNF-GOV-004 |
| B5 | Revisión de Alembic | 001 | `alembic_version` | PG | INCLUDED | ídem | = manifiesto = cabeza del código | ídem (sin migrar) | RESTORE ≠ UPGRADE |
| B6 | Identidad de la instalación (`installations`, tenants, empresas) | 004/010 | PG | PG | INCLUDED | ídem | `installation_uuid` = esperado | ídem | OD-BK-03 |
| B7 | Estado y artefactos de licencia | 004/010 | PG | PG | INCLUDED | ídem | Reverificación al arrancar | ídem + arranque | No se confía en el estado cacheado |
| B8 | Factores MFA (cifrados) | 002 | `mfa_factors` | PG | INCLUDED | ídem | Muestra descifrada con el anillo reprovisionado | ídem | Depende de `KONTROL_MFA_KEYS`, que no viaja |
| B9 | Sesiones | 001/002 | `auth_sessions` | PG | INCLUDED (se revocan al restaurar) | ídem | 0 sesiones vigentes tras restaurar | ídem + revocación | PDD-BK-11. Depende de `KONTROL_SECRET_KEY`, que se regenera |
| B10 | Binarios documentales | 046 | `STORAGE/documents/<storage_key>` | FS | INCLUDED (referenciados por la instantánea; PURGED, ausentes por diseño) | Escritos una vez, atados a la instantánea | sha256 = `stored_files.sha256` | Staging, rehash y renombrado | No se copia lo no referenciado: los huérfanos son basura recuperable (046) |
| B11 | Ficheros de exportación | 009 | `STORAGE/exports/<file_ref>` | FS | INCLUDED (referenciados) | ídem | sha256 al copiar = al restaurar | ídem | — |
| B12 | Clave privada de la instalación | 004/010 | `INSTALLATION_VOLUME/installation_private_key.pem` | FS | **EXCLUDED_BY_DESIGN** (secreto externo) | — | Se corresponde con `installations.public_key` | Reprovisión externa | OD-BK-04 |
| B13 | Base de firmas de ClamAV | 046 | `kontrol-clamav-db` | Volumen | EXCLUDED_BY_DESIGN (regenerable) | — | — | `freshclam` o provisión | No es estado del cliente |
| B14 | Volumen de copias | 001 | `kontrol-backups` | Volumen | NOT_APPLICABLE | — | — | — | Es el destino, no el estado |
| B15 | Configuración y secretos (`.env`) | 001 | Anfitrión | Fichero | EXCLUDED_BY_DESIGN | — | — | Reprovisión | OD-BK-04 |

**MISSING_REQUIRED_BACKUP_STATE = 0 · BACKUP_SCOPE_INVENTORY_COMPLETE = 1.**
