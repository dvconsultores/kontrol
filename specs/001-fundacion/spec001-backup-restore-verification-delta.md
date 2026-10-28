# SPEC 001 · Delta — BACKUP / RESTORE VERIFICATION (SHARED-CORE-P0-HARDENING-06)

| Campo | Valor |
|---|---|
| Spec dueña | **001**: FR-001-083, NFR-001-008, US-012, EDGE-21 y `backup-restore-plan.md` |
| Afectadas | **053**: DT-11 figura en el roadmap con dueña 053 y la carpeta de la Spec no existe en `specs/`, así que se registra como afectada sin duplicar el delta. También 004/010 (licencias), 002 (MFA), 046 (documentos), 009 (exportaciones) y 054 (QA) |
| Deudas en alcance | **DT-11** (BLOCKER) · LICENCIA-ESTADO-SIN-REVERIFICAR, en lo que toca a la restauración |
| Base | `f24e74e` (develop == origin/develop) |
| Evidencia | `evidence/backup-restore/` |
| Estado | **IMPLEMENTED — CERTIFIED (QA) — CONVERGED** (2026-10-28) |

## 0. Reconciliación previa

- **E2E-TOTP-PASO-COMPARTIDO** se reclasifica según el encargo (§4): MEDIUM · QA_RELIABILITY · BLOCKING_CURRENT_CYCLE = 0 · BLOCKING_FINAL_GOV_RELEASE_CERTIFICATION = 1.
- **Gobierno.** PDF releído (hash `8f86615f…`, sin cambio). Aplican:
  - RNF-GOV-010: RTO/RPO por instalación; validar backup/restore antes de producción;
  - RNF-GOV-011: cifrado y secretos fuera del código;
  - RNF-GOV-004 y RNF-GOV-005: inmutabilidad y auditabilidad tras la restauración;
  - RNF-GOV-017: logs sin secretos;
  - RNF-GOV-018: retención, que sigue como POLICY_NOT_RATIFIED, así que no se borra nada;
  - E2E-08 Restore;
  - §16 de convergencia: «backup/restore y DR probados».

  RNF-GOV-024 (contingencia offline) no aplica. No se implementa nada de Gobierno.
- **Objetivos de RPO y RTO.** FR-001-083 y NFR-001-008 (Spec 001, aprobada) fijan «RPO ≤15 min y RTO ≤4 h como objetivo». Hay fuente en el repositorio, así que se comparan contra esa fuente (OD-BK-08). No se marcan NOT_RATIFIED ni se inventan.

## 1. Discovery (medido)

| Pieza | Hoy |
|---|---|
| `scripts/backup.sh` | Solo `pg_dump` en SQL plano, vía `docker run postgres:18-alpine`. Almacén y estado de licencia **no** se copian (lo dice su propio comentario). Sin manifiesto. Cifrado `openssl -aes-256-cbc -pbkdf2`, **no autenticado**, con la clave como `pass:` en la línea de órdenes, **visible en `ps`**. Carga `.env` entero |
| `scripts/restore.sh` | Descifra y desempaqueta en un temporal y **solo imprime** pasos: no restaura nada |
| `kontrol.py backup` / `restore` | `backup` crea un directorio vacío; `restore` imprime el runbook |
| Imagen del backend | Sin `pg_dump` ni `pg_restore` (`Dockerfile.backend`); sí trae `cryptography` (fijada en `requirements.lock`) |
| Almacén documental | Solo sistema de archivos (S3 falla cerrado, OD-S3-01). Raíz `KONTROL_STORAGE_PATH/documents`, clave opaca generada por el servidor y escrita una vez (temporal + `os.replace`). `stored_files` guarda `storage_key`, `size`, `sha256` y `status` (AVAILABLE, QUARANTINED, PURGED) |
| Exportaciones | `KONTROL_STORAGE_PATH/exports/<file_ref>` (`report_exports.file_ref`), escritas una vez y sin hash en la base |
| Borrado de binarios | Solo huérfanos no confirmados, más la purga por retención (`purge_version`: borra el binario y deja la fila en PURGED) |
| Volumen de licencia | `KONTROL_INSTALLATION_VOLUME_PATH/installation_private_key.pem` (Ed25519): **secreto**. Artefactos y estado de licencia viven en la base |
| Reverificación de licencia | **Ya existe**: al arrancar (`reverificar_al_arrancar`) y en cada autorización de escritura (`reverificar_vigente`) |
| Anti-retroceso (EDGE-21) | `license.py`: `now = max(now, last_reliable_date)`. Importación: anti-retroceso de período (FR-010-200..209) |
| Sesiones | `sessions` (modelo `identity_access.models.Session`); el token lleva `sid` y se valida contra la fila (revocada o vencida da sesión inválida). Existe `revoke_user_sessions` |
| MFA | `KONTROL_MFA_KEYS` (anillo AES-256-GCM, AAD `tenant|user|factor`). Sin la clave, `_decrypt` → `_unavailable()`: falla cerrado |
| Modo de mantenimiento | No hay; solo el bloqueo de escritura por licencia (READ_ONLY) |
| Clientes PG de QA | `pg_dump`/`pg_restore` 16.2 (pgserver), del mismo servidor de QA |

## 2. Inventarios

`BACKUP_SCOPE_INVENTORY.md` y `EXTERNAL_RECOVERY_SECRET_INVENTORY.md` están en la evidencia. Resumen:
- **Se incluye:** esquema, datos, secuencias, índices, restricciones, funciones y triggers (también los de inmutabilidad), `alembic_version`, binarios documentales referenciados, ficheros de exportación referenciados y la identidad de la instalación (en la base).
- **Excluido por diseño:** los secretos externos (OD-BK-04), la base de firmas de ClamAV (regenerable) y el propio volumen de copias.
- MISSING_REQUIRED_BACKUP_STATE = 0 tras el diseño.

## 3. Decisiones de la dueña aplicadas

| Decisión | Aplicación |
|---|---|
| OD-BK-01 | Cifrado obligatorio con clave propia (`KONTROL_BACKUP_KEY`), distinta de las demás |
| OD-BK-02 | El destino debe estar vacío, ser nuevo y estar aislado |
| OD-BK-03 | Identidad de la copia y de la instalación esperada |
| OD-BK-04 | Secretos externos, reprovisionados |
| OD-BK-05 | Alcance completo |
| OD-BK-06 | Consistencia |
| OD-BK-07 | Verificación independiente antes de restaurar |
| OD-BK-08 | RPO y RTO medidos y comparados con FR-001-083 |
| OD-BK-09 | Sin retención ni borrado |
| OD-BK-10 | Continuidad funcional |

**Decisión de diseño del proyecto (§35 del encargo), PDD-BK-11.** Tras restaurar se **revocan todas las sesiones** del destino con el mecanismo existente, y el runbook exige rotar `KONTROL_SECRET_KEY`, que solo firma JWT y se puede regenerar. Ninguna sesión anterior al desastre vuelve a valer. No requiere arquitectura nueva, así que MATERIAL_OQ = 0.

## 4. Arquitectura

**AD-B1 · Herramienta.** Paquete nuevo `app/ops/` dentro del backend, que trae la configuración, el ORM, el modelo de almacén y `cryptography`. Se invoca con `python -m app.ops.backup {create|verify|restore}`.
- Los binarios de PostgreSQL se toman de `KONTROL_PG_BIN_DIR` o del `PATH`. Si faltan, falla cerrado (`PG_TOOLS_MISSING`). La versión de `pg_dump`/`pg_restore` debe ser mayor o igual que la del servidor, y si no, falla cerrado.
- `scripts/backup.sh`, `scripts/restore.sh` y `kontrol.py backup|restore` pasan a ser envoltorios delgados.
- El empaquetado del cliente PG en la imagen operativa queda fuera: deuda BACKUP-PG-TOOLS-IN-OPS-IMAGE. No se toca `Dockerfile.backend`, porque la certifica la Spec 054.

**AD-B2 · Consistencia (OD-BK-06): DB_SNAPSHOT_WITH_IMMUTABLE_OBJECTS.** Se abre una transacción `REPEATABLE READ READ ONLY` y se exporta su instantánea (`pg_export_snapshot()`). Después:
- `pg_dump --snapshot=<id>`;
- en la **misma** transacción se leen los `stored_files` (todos), los `report_exports` con `file_ref`, los recuentos y huellas por tabla, la revisión de Alembic y la identidad.

Los objetos que se copian son **exactamente** los que referencia la instantánea:
- AVAILABLE y QUARANTINED: deben existir y su sha256 debe coincidir con `stored_files.sha256`;
- PURGED: se espera que falten y no se copian;
- exportaciones: deben existir; el hash se calcula al copiar.

Como los objetos se escriben una sola vez y nunca se modifican en el sitio, lo copiado es el estado de la instantánea. Un objeto creado después de la instantánea no está referenciado y no entra, sin estados a medias. Si una purga concurrente borró un objeto referenciado, o un hash no coincide, la copia falla con **BACKUP_INCONSISTENT** y no queda ningún paquete. No hace falta modo de mantenimiento.

**AD-B3 · Cifrado (OD-BK-01, §24).**
- `cryptography` (fijada), primitiva **AES-256-GCM** en la construcción **STREAM** (Hoang, Reyhanitabar, Rogaway y Vizár, 2015; la que usan age y Tink StreamingAEAD) con segmentos de 1 MiB.
- Nonce de 96 bits = prefijo aleatorio de 7 bytes + contador de 4 bytes + 1 byte de «último segmento».
- AAD = cabecera del paquete + nombre del miembro.

Así se detectan reordenamiento, truncado, intercambio de miembros y clave errónea. No es criptografía nueva: es la composición estándar sobre una primitiva AEAD de biblioteca.

La clave es de 32 bytes, en `base64url`, y llega por `KONTROL_BACKUP_KEY` o por `--key-file` (fichero 0600). **Nunca** por un argumento con el valor. No se escribe en ningún sitio.

**AD-B4 · Paquete y manifiesto (OD-BK-03, §22–§23, §30).**
- El paquete es un `.kbk`: un tar sin comprimir con miembros de nombre **fijo**:
  - `header.json` (en claro, autenticado como AAD);
  - `manifest.enc`;
  - `database.enc`;
  - `objects/000001.enc`, etc.
- Los nombres de miembro nunca llevan claves de almacenamiento.
- El manifiesto, cifrado y autenticado, contiene:
  - `format_version`, `backup_id`, `created_at_utc` y `product_version`;
  - `alembic_revision`, `installation_id` (uuid de instalación) y `tenants`;
  - `database` (miembro, sha256 y tamaño del texto en claro);
  - `objects` (secuencia, tipo `document|export`, referencia `storage_key`/`file_ref`, id de base, tamaño y sha256);
  - recuentos por tipo;
  - `tables` (recuento y huella por tabla), `audit` (recuento y último evento) y `license` (resumen sin material);
  - `required_external_secrets` (clases), `encryption` (alg y segmento) y `consistency_mode`.
- La autenticidad la da el AEAD con la clave externa. El sha256 se usa solo para comparar contenido.
- Al leer:
  - se usa `tarfile` sin `extract()`;
  - solo se aceptan miembros regulares cuyo nombre case con la lista blanca;
  - enlaces, dispositivos, rutas absolutas, `..` o duplicados → rechazo.

**AD-B5 · Verificación previa (OD-BK-07).** `verify` descifra todo hacia un temporal fuera de los destinos. Comprueba:
- el formato y el manifiesto;
- la presencia de cada miembro;
- el sha256 de la base y de cada objeto;
- la legibilidad del volcado (`pg_restore --list`).

`restore` ejecuta `verify` entero **antes** de tocar el destino.

**AD-B6 · Restauración (OD-BK-02/03/04, §44–§46).** Entradas obligatorias:
- `--bundle`, `--target-db-url` (en el entorno, nunca en un argumento) y `--target-storage-root`;
- `--target-installation-volume`;
- `--expected-installation-id`;
- la clave de copia;
- los secretos externos del destino: `KONTROL_MFA_KEYS` y la clave privada de la instalación ya reprovisionada en el volumen de destino.

Orden, que falla antes de escribir donde se puede:
1. `verify`.
2. Identidad esperada = `manifest.installation_id`; si no, FOREIGN_BACKUP.
3. La revisión de Alembic es conocida por el código y es la cabeza. Si es desconocida o más nueva, ALEMBIC_INCOMPATIBLE. Si es anterior, RESTORE_REQUIRES_UPGRADE: no se migra (RESTORE ≠ UPGRADE).
4. Destino vacío: la base sin tablas en `public` y el almacén inexistente o vacío. Si no, TARGET_NOT_EMPTY y la marca queda intacta.
5. Secretos externos: la clave privada del volumen se corresponde con `installations.public_key` del manifiesto, y cada `key_id` de MFA en uso está en el anillo y descifra una muestra. Si no, EXTERNAL_SECRET_MISMATCH. Esto se comprueba antes de escribir, leyendo los factores del volcado restaurado en una base temporal, o después del paso 6 con limpieza si falla; ver AD-B7.
6. `pg_restore --no-owner --no-privileges --exit-on-error --single-transaction`.
7. Almacén: escritura en un staging hermano `<root>.restoring-<backup_id>` con la misma validación de clave que `FilesystemStorageProvider._resolve`; rehash de cada objeto; después `os.replace` a la raíz final.
8. Verificación posterior:
   - revisión de Alembic;
   - tablas, recuentos y huellas idénticos al manifiesto;
   - los 3 triggers de 0061;
   - catálogo de auditoría válido;
   - objetos con hash correcto.
9. Cierre: revocar todas las sesiones (PDD-BK-11) y un evento `INSTALLATION_RESTORED` por tenant.
10. Informe JSON con medidas.

**AD-B7 · Fallo a mitad (§46).** Cualquier fallo a partir del paso 6 deja el destino **como se encontró**, es decir vacío:
- `DROP SCHEMA public CASCADE; CREATE SCHEMA public`, solo porque el paso 4 probó que estaba vacía;
- se borran el staging y lo escrito en la raíz;
- el resultado es RESTORE_FAILED y nunca se informa éxito.

Los secretos se verifican en el paso 8, porque los factores se leen del destino. Si fallan, se aplica la misma limpieza.

**AD-B8 · Auditoría de la operación (§40).** Dos acciones nuevas en el catálogo (CATALOG_VERSION 2026-10-28.2):
- `INSTALLATION_BACKUP_CREATED` (`Installation`, TENANT, SECURITY, BUSINESS_COMMIT; detalle `backup_id`, `objects`, `consistency_mode`): una por tenant en el origen **después** de cerrar el paquete. No está dentro de ese mismo paquete, y queda documentado;
- `INSTALLATION_RESTORED` (`Installation`, TENANT, SECURITY, BUSINESS_COMMIT; detalle `backup_id`, `backup_created_at`, `sessions_revoked`): una por tenant en el destino, al final.

Sin rutas, claves ni secretos. Los rechazos se informan en el JSON de salida y con el código de salida. No se auditan en una base que no se toca.

**AD-B9 · Licencia (§36, EDGE-21).** No se confía en el estado cacheado: el arranque del destino ejecuta `reverificar_al_arrancar`, y la certificación registra el estado anterior, el restaurado sin procesar y el reverificado. EDGE-21 se comprueba en el destino:
- `period_end` y `last_reliable_date` iguales a los del punto de copia;
- el modo, calculado con el reloj actual, no es anterior;
- la importación de una licencia de período anterior se rechaza.

**AD-B10 · CLI y UX (§43–§45, §86).**
- Salida legible y un JSON final.
- Códigos de salida:

| Código | Significado |
|---|---|
| 0 | Correcto |
| 1 | Error operativo |
| 2 | Paquete inválido o corrupto |
| 3 | Clave errónea |
| 4 | Copia ajena |
| 5 | Destino no vacío |
| 6 | Alembic incompatible o se requiere actualización |
| 7 | Secreto externo ausente o erróneo |
| 8 | Restauración fallida y limpiada |
| 9 | Copia inconsistente |

- Nunca imprime la clave, la URL con credenciales ni contenidos.

**AD-B11 · Certificación real (§77–§83).** `qa/backup_restore_cert.py` sobre el PostgreSQL de QA:
1. Base origen `kbk_src_<run>` migrada a la cabeza y sembrada con el mundo sintético: 2 tenants, varias empresas, usuarios, roles y alcances, MFA, documentos con analizador, exportación, licencia y eventos.
2. Copia, verificación y **borrado de la base de origen y de su almacén** antes de restaurar (independencia de la fuente).
3. Restauración en `kbk_dst_<run>` y en una raíz nueva.
4. Arranque de la aplicación en un **proceso aparte** con solo el entorno del destino.
5. Pruebas funcionales:
   - inicio de sesión;
   - MFA con TOTP del anillo reprovisionado;
   - empresa;
   - lectura;
   - escritura y su auditoría;
   - intento de UPDATE y DELETE sobre auditoría, que debe ser rechazado;
   - descarga de un documento con su hash;
   - 422 de consulta y de instante sin zona;
   - una sesión previa al desastre rechazada.
6. Medidas de RPO y RTO, y limpieza.

**Sin migración.** Alembic sigue en 0061.

## 5. Seguridad

| Amenaza | Control | Prueba |
|---|---|---|
| Clave en el paquete, en `ps` o en logs | AD-B3, AD-B10 | Barrido del paquete y de la evidencia en busca de la clave; ningún argumento con secreto |
| Paquete manipulado o truncado | AEAD STREAM | Negativas N-01..05 |
| Traversal o symlink en el tar | AD-B4 | N-06, N-07 |
| Escape de `storage_key` | `_resolve` | N-08 |
| Copia ajena | AD-B6.2 | N-09 |
| Sobrescritura | AD-B6.4 | N-10 |
| Restauración parcial que parece válida | AD-B7 | N-11 |
| Trigger de auditoría perdido | AD-B6.8 | N-12 |
| Clave MFA o de instalación errónea | AD-B6.5 | N-13, N-14 |
| Sesiones previas reutilizables | PDD-BK-11 | F-09 |
| Lectura accidental de la fuente | AD-B11 | El origen se borra antes de restaurar, con un centinela |

## 6. Tareas

Todas con RETRY_MAX = 2. DeepSeek redacta todo el código, las pruebas y los guiones. EGRESS sin claves ni volcados.

| Tarea | Modelo | Ficheros | Prueba |
|---|---|---|---|
| C06-T01 cifrado STREAM | pro | `app/ops/__init__.py`, `app/ops/backup_crypto.py`, `tests/test_backup_crypto.py` | Ida y vuelta, clave errónea, truncado, reordenamiento, cambio de cabecera |
| C06-T02 paquete y manifiesto | pro | `app/ops/backup_bundle.py`, `tests/test_backup_bundle.py` | Lista blanca, traversal, symlink, duplicados, miembro faltante, manifiesto corrupto |
| C06-T03 creación | pro | `app/ops/backup_create.py`, `tests/test_backup_create_pg.py` | Instantánea, objetos, inconsistencia, cifrado, auditoría |
| C06-T04 restauración | pro | `app/ops/backup_restore.py`, `tests/test_backup_restore_pg.py` | Restauración correcta y negativas N-01..14 |
| C06-T05 CLI y envoltorios | flash | `app/ops/backup.py` (`__main__`), `scripts/backup.sh`, `scripts/restore.sh`, `kontrol.py` | Códigos de salida y ausencia de secretos |
| C06-T06 catálogo | flash | `audit_catalog_entries.py`, `audit_catalog.py` (versión), pruebas de recuento | CAT-* |
| C06-T07 certificación real | pro | `qa/backup_restore_cert.py` | La corrida real |
| C06-T08 runbook | flash | `backup-restore-plan.md`, `instalar.md` | Revisión |

## 7. Puerta

| Condición | Valor |
|---|---|
| BACKUP_SCOPE_INVENTORY_COMPLETE · EXTERNAL_RECOVERY_SECRET_INVENTORY_COMPLETE | 1 · 1 |
| CONSISTENCY_MODEL_DEFINED · ENCRYPTION_MODEL_DEFINED · MANIFEST_CONTRACT_DEFINED | 1 · 1 · 1 |
| RESTORE_PRECONDITIONS_DEFINED · RESTORE_FAILURE_MODEL_DEFINED | 1 · 1 |
| LICENSE_REVERIFY_MODEL_DEFINED · RPO_MEASUREMENT_DEFINED · RTO_MEASUREMENT_DEFINED | 1 · 1 · 1 |
| ENGINEERING_REQUIREMENTS_REVIEWED | 1 |
| MATERIAL_OQ · UNKNOWN · CONTRADICTIONS · BLOCKER | 0 · 0 · 0 · 0 |

**GATE PASS.** El encargo autoriza `implement`.

## 8. Implementación (resultado)

Tareas añadidas durante la implementación (la tabla de §6 conserva la planificación original):

| Tarea | Origen | Resultado |
|---|---|---|
| C06-T02B | El contrato de `REF_RE` (Claude) rechazaba el `file_ref` real de las exportaciones | `is_safe_ref` admite `report-…-….csv`; BB-15, BB-16 |
| C06-T02C | BR-08 destapó `tarfile.ReadError` en bruto con un paquete truncado | Todo error de `tarfile` sale como `BUNDLE_FORMAT_INVALID`; BB-17 por miembro |
| C06-T03C | División de T03 tras agotar sus reintentos | `entity_id` = clave primaria de la instalación (`varchar(36)`); BCP-02/03 con `pg_bin_dir` |
| C06-T04C | División de T04 tras agotar sus reintentos | Conexiones con `pg_connect_kwargs`, orden de imports, `str()` de identificadores |
| C06-T07C | Endurecer el guion | Lint estricto; el veredicto exige C-00..C-11, S-01 y las métricas (M-01) |
| C06-T09 | Supervivientes de la ronda 1 de mutaciones | BB-18, BB-19, BCP-09, BCP-10, BR-16..BR-21 |
| C06-T09B | M06-26, el sustituto válido de M06-25 según el Principio 27, sobrevivió | BR-22: escritura concurrente con la copia y restauración que verifica las huellas de la misma instantánea |
| C06-T050 (convergencia F1) | `license_states` se leía por `installations.id`, pero la columna guarda `installation_uuid`, así que el manifiesto nunca registraba la licencia | Consulta por `installation_uuid`; BCP-11 (rojo medido) |
| C06-T051 (convergencia F2) | AD-B9/EDGE-21 prometía comprobaciones en el destino que la certificación no hacía | C-12 (estado de licencia del punto de copia, sin retroceso de la fecha fiable) y C-13 (`LICENSE_PERIOD_DOWNGRADE`) |

Decisiones de diseño tomadas por Claude durante la implementación. Ninguna es material ni corresponde a la dueña:
- **AD-B2 (modo de volcado).** `pg_dump` escribe a stdout y el flujo se cifra directamente: el volcado nunca está en claro en disco al copiar. Al restaurar, el volcado se descifra en un directorio temporal 0700 que se borra siempre.
- **AD-B8 (`entity_id`).** Los eventos `INSTALLATION_*` llevan como `entity_id` la clave primaria de la instalación (`installations.id`). `installation_uuid` mide hasta 64 caracteres y no cabe en `audit_events.entity_id varchar(36)`.
- **Conexiones.** `backup_pg.pg_connect_kwargs` da los argumentos de `psycopg2.connect`. `libpq_env` queda solo para el entorno de `pg_dump` y `pg_restore`; nunca se construye una DSN con contraseña en argv.

Sin migración: Alembic sigue en 0061. OpenAPI sin deriva: 422 rutas y 0 operaciones o esquemas cambiados (la orden es de CLI).

## 9. Pruebas y certificación

| Verificación | Resultado |
|---|---|
| Pruebas dirigidas de copia (crypto, paquete, CLI, creación PG, restauración PG, catálogo) | 173/173 en PostgreSQL |
| Backend completo PostgreSQL (`qa/suite_tiempos.py --motor postgres --con-analizador`) | **3872/0** (18 omitidas) · r20261028t212344p8932n870a77 |
| Backend completo SQLite (ídem `--motor sqlite`) | **2761/0** (1129 omitidas) · r20261028t221023p394111ncee2fb |
| Frontend: vitest · tsc · eslint · build | 701/701 · 0 · 0 · OK |
| ruff · mypy `app` | limpio · 154 (MYPY_NEW_ERRORS = 0) |
| Certificación real `qa/backup_restore_cert.py` | **PASS** · cierre 20261028T230008Z-9657d0 (C-00..C-13, S-01, M-01) · validador externo VALIDO (`evidence/backup-restore/certificacion.md`) |
| Tras la convergencia (T050, T051, T09B) | pruebas de copia y licencia 190/190 en PostgreSQL, 108/0/31 en SQLite; `app/ops` solo lo importan las pruebas de copia, `backup_mundo` y el guion (medido) |
| Mutaciones 06 | 27 · 26 muertos · 0 equivalentes · 0 supervivientes · 1 inválido (M06-25, Principio 27) (`evidence/backup-restore/mutaciones.md`) |
| E2E canónica · base tras la E2E | Canónica con analizador: 1.ª corrida 377/1/4 (r20261028t222854p522164n8e257a: `accesibilidad: /inventario/existencias` agotó 30 s esperando `/auth/refresh` en `entrarComoUsuario`, familia de E2E-N6-ENTRAR-UAB-INTERMITENTE; sin relación con este ciclo, que no toca autenticación ni frontend); repetición diagnóstica única sin cambiar código **382/382** (r20261028t223815p549431nf18588), limpieza LIMPIA · base tras la E2E **PASS** (r20261028t224629p576649n1cb2e5: 23/23 Chromium; 188 eventos, 0 fuera de catálogo, 0 incoherencias de ámbito, triggers y 0061) |

Medidas (corrida de cierre):
- RTO entre 5,1 s y 34,9 s según la espera determinista al paso TOTP siguiente; MET frente a ≤ 4 h.
- Restauración por CLI: 1,3–1,5 s.
- Ventana perdida: 1,3–1,5 s.
- RPO: `DEPENDS_ON_BACKUP_SCHEDULE`. El objetivo de ≤ 15 min no se cumple con copias manuales (deuda BACKUP-SCHEDULE-RPO).

Puertas: SCREEN_FORM_COMPLETENESS_GATE = NOT_APPLICABLE, porque no hay pantalla de copia (la operación es de administración por CLI). OPERATIONAL_UX_COMPLETENESS_GATE = PASS. La CLI cubre:
- precondiciones y entradas;
- clave solo por entorno o fichero 0600;
- progreso en líneas legibles y JSON final;
- códigos de salida 0..9;
- paquete corrupto → 2;
- guarda de destino → 5, sin `--force`;
- limpieza ante fallo → 8;
- verificación sin tocar el destino.

El runbook §4 indica la acción del operador para cada código.

Navegador: el humo de la aplicación restaurada se hizo por HTTP con la misma API del SPA. La cobertura de navegador de las pantallas que intervienen (inicio de sesión con MFA, empresa, documentos) la da la E2E canónica. Safari real: NOT_MEASURED. Queda la deuda BACKUP-RESTORED-UI-SMOKE (LOW).

## 10. Convergencia (`/speckit-converge`)

Se comprobaron FR-001-083, NFR-001-008, EDGE-21, T-010, T-042, AD-B1..B11, OD-BK-01..10, PDD-BK-11 y los 27 principios de la constitución. Hallazgos: 1 contradicts y 5 partial (3 HIGH, 2 MEDIUM, 1 LOW). Se añadieron a `tasks.md` como «Phase 1: Convergence»:
- **T050 (F1) y T051 (F2):** implementadas y certificadas en este ciclo.
- **T052..T055:** abiertas como deuda registrada; requieren infraestructura, imagen o datos reales fuera del alcance autorizado: T052 BACKUP-SCHEDULE-RPO, T053 BACKUP-PG-TOOLS-IN-OPS-IMAGE, T054 BACKUP-RTO-DATOS-REALES, T055 BACKUP-RESTORED-UI-SMOKE.

Ninguna violación de un MUST. El Principio 27 se aplicó a la propia evidencia: M06-25 se declaró inválido y se sustituyó.

## 11. Deudas

Cerrada en el núcleo: **DT-11**. Cubierta en la restauración: LICENCIA-ESTADO-SIN-REVERIFICAR (C-10, M06-21). Reclasificada: **E2E-TOTP-PASO-COMPARTIDO → MEDIUM** · QA_RELIABILITY · BLOCKING_CURRENT_CYCLE = 0 · BLOCKING_FINAL_GOV_RELEASE_CERTIFICATION = 1.

Nuevas (registradas en `docs/roadmap/technical-debt-roadmap.md`):
- **BACKUP-SCHEDULE-RPO** (HIGH · bloquea la certificación final de Gobierno, RNF-GOV-010);
- **BACKUP-PG-TOOLS-IN-OPS-IMAGE** (MEDIUM);
- **BACKUP-RTO-DATOS-REALES** (MEDIUM);
- **BACKUP-RESTORED-UI-SMOKE** (LOW).

Estado final: **IMPLEMENTED — CERTIFIED (QA) — CONVERGED** en el alcance del delta. Quedan abiertas en Spec 001 las tareas de convergencia T052..T055, que son deuda registrada y no bloquean este ciclo.
