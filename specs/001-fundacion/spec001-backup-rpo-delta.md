# SPEC 001 · Delta — BACKUP-SCHEDULE-RPO (T052, con T053)

| Campo | Valor |
|---|---|
| Deudas | BACKUP-SCHEDULE-RPO (T052, HIGH) · BACKUP-PG-TOOLS-IN-OPS-IMAGE (T053, MEDIUM) |
| Dueña | 001 / 053. Línea: `SHARED_CORE`, por razón Enterprise (FR-001-083) |
| Estado | **IMPLEMENTADO EN LOCAL, SIN PUBLICAR; `T052_STATUS = BLOCKED_BY_EXTERNAL_CERTIFICATION_GATES`** (§22) |
| Alcance futuro | T052 + T053 (prerrequisito) + `T052_PREREQUISITE_AUDIT_TRUTHFULNESS`. No T054 ni T055 |
| Autorización de implement | Encargo T052-RPO-IMPLEMENTATION-02 |
| Evidencia | `evidence/backup-rpo/` |

Marcas: **MEASURED** (visto en el árbol en este ciclo), **RECORDED** (evidencia versionada), **DERIVED** (deducción), **NOT_MEASURED**.

## 1. Requisito

| Fuente | Texto | Estado |
|---|---|---|
| FR-001-083 (P0) | Scripts de backup y restauración verificados, «con RPO ≤15 min y RTO ≤4 h como objetivo» | Confirmado, sin `CONTRACT_CHANGED` |
| NFR-001-008 | Backups cifrados y verificados, restore probado, RPO ≤15 min, RTO ≤4 h, runbooks | Confirmado |
| `backup-restore-plan.md` | RPO objetivo inicial ≤15 min para datos transaccionales | Confirmado |
| DOC-05 §11 | RPO «ajustar por infraestructura»; backups «cifrados, retenidos y separados»; restore mensual y ejercicio trimestral | La fuente exige retención y separación; la cadencia de restore queda fuera (§15) |
| T052 | «planificación de copias o archivado continuo» | Admite la arquitectura elegida |
| RNF-GOV-010 | RTO/RPO por instalación | Solo compatibilidad (§14) |

`REQUIREMENT_RPO_MAX_MINUTES = 15`. El encargo fija el cumplimiento de ese máximo; el «como objetivo» del FR no se reescribe aquí.

## 2. Causa raíz (`ROOT_CAUSE_PROVEN = 1`, MEASURED)

KONTROL tiene `create`, `verify` y `restore`, pero ninguna garantía operacional de que exista una copia durable y válida dentro de la ventana contratada. No es «falta un cron»; faltan ocho capacidades:

| Dimensión | Hecho |
|---|---|
| Planificación | `registry.py` no tiene manejador de copia; solo se copia a mano |
| Herramientas | `Dockerfile.backend` no instala `pg_dump` ni `pg_restore` |
| Secreto | `cmd_scheduler_tick` no pasa `KONTROL_BACKUP_KEY`; `compose.yaml` no la declara en `backend` |
| Destino | `kontrol-backups` es un volumen del mismo anfitrión |
| Retención | OD-BK-09 prohíbe borrar: en programación el disco crece sin límite |
| Observabilidad | Diagnóstico no informa de copias ni de RPO |
| Detección de fallos | Ningún estado distingue copia vigente, atrasada o fallida |
| Verificabilidad | `create` registra «Copia verificada creada» antes de que corra `verify` |

Hallazgos colaterales: `backup_create.py:321` pasa todo `os.environ` a `pg_dump`, incluida la clave si está en el entorno; `create` escribe sin comprobar espacio.

## 3. Arquitectura

**Decisión: `BASELINE_RPO_ARCHITECTURE = SCHEDULED_KBK`,** condicionada a la puerta de capacidad (§4).

| Opción | Veredicto | Motivo |
|---|---|---|
| A · `.kbk` programado | **Elegida** | Reutiliza la restauración certificada; instantánea coherente de base y documentos |
| B · WAL/PITR | `FUTURE_ADVANCED_DEPLOYMENT_PROFILE` | No cubre el almacén documental, exige controlar la base externa y una segunda semántica de recuperación |
| C · Perfil por instalación | Evolución futura | Solo se evalúa si la capacidad lo exige |

### 3.1 Dónde corre: restricción de ADR-D0-015

R-D0-15-1 solo admite la cadena temporizador → orden canónica → **manejador registrado** → registro y auditoría. R-D0-15-2 prohíbe argumentos que elijan trabajo, R-D0-15-3 prohíbe workers o hilos de fondo y R-D0-15-4 impone un solo tick por instalación.

| Alternativa | Veredicto |
|---|---|
| Segundo temporizador con carril propio | Rechazada: exige enmendar R-D0-15-4 |
| Tick que lanza un proceso desacoplado | Rechazada: viola R-D0-15-3 |
| **Manejador en el tick existente** | **Elegida**: sin enmienda de ADR |

Riesgo **por medir, no aceptado**: durante la copia el tick retiene su bloqueo, así que los ticks siguientes quedan `SKIPPED_OVERLAP` y las notificaciones de la 047 pueden retrasarse hasta la duración D. Se limita así:

- Los manejadores de copia van **al final** del registro, después de los de la 047.
- La copia corre como subproceso con tope duro `BACKUP_TIMEOUT`.
- La implementación registra `SCHEDULER_TICK_DURATION_BEFORE`, `BACKUP_HANDLER_DURATION`, `SCHEDULER_TICK_DURATION_AFTER` y `NOTIFICATION_DELAY_IMPACT`.
- Si el tick único no permite satisfacer a la vez el RPO y la latencia operacional: `ADR_CONFLICT = 1` y STOP. El ADR no se rompe en silencio.

### 3.2 Flujo

Manejadores nuevos, dueña `001`:

| Código | `catch_up` | Función |
|---|---|---|
| `installation_backup` | `LATEST_WINDOW` | Si toca, crea una copia. Tras una caída produce una sola, no una por tick perdido (R-D0-15-6) |
| `backup_retention` | `OWNER_IDEMPOTENT` | Aplica la política ratificada |
| `backup_rpo_evaluation` | `OWNER_IDEMPOTENT` | Registra transiciones de estado y las audita |

Secuencia, con clave lógica por franja (R-D0-15-5):

```
franja vencida → bloqueo propio → prechequeo (herramienta, clave, destino, espacio)
→ create en LOCAL_STAGING (`.part`, sin auditar) → verify → copia a destino (`.part`, fsync)
→ rename atómico + fsync del directorio → relectura y sha256 → ledger VERIFIED_DURABLE
→ auditoría de éxito → retención
```

**Ledger nuevo `backup_runs`** (`Scope.INSTALLATION`, migración): `slot` único, estado, `snapshot_at`, inicio y fin, tamaño, sha256, `protection` y `error_code`. Sin secretos, rutas ni contenido. No se copia a sí mismo como verdad: tras un `restore` el ledger se reinicia para no presumir de copias ajenas al destino.

## 4. Semántica del RPO y puerta de capacidad

La pérdida máxima **no** es el intervalo. Si el desastre ocurre justo antes de que la copia k+1 sea durable, lo último recuperable es k:

```
MAX_DATA_LOSS_WINDOW = I + D + J
I = intervalo entre instantáneas
D = instantánea → copia durable y verificada en destino
J = retraso de disparo (intervalo del temporizador + tick en curso)
```

- La edad se mide desde `snapshot_at`, nunca desde el fin de la copia.
- Una copia cuenta solo si está `VERIFIED_DURABLE`.
- `SCHEDULE_INTERVAL ≠ RPO`. Debe cumplirse `SCHEDULE_INTERVAL + BACKUP_EXECUTION_TIME + SCHEDULER_JITTER_OR_DURABILITY_MARGIN ≤ CONFIGURED_RPO`.
- Con `CONFIGURED_RPO` = 15, **I debe ser menor que 15 min**. No se fija ningún I como verdad universal: cada instalación lo valida por capacidad.

**Puerta de capacidad:** `CAPACITY_MEASUREMENT_STATUS = NOT_MEASURED`. Esto no bloquea publicar el diseño, pero sí bloquea `RPO_CAPACITY_CERTIFIED`. La implementación debe medir D en QA antes de habilitar la certificación. Si la fórmula no cabe con un I razonable, `BASELINE_RPO_ARCHITECTURE = BLOCKED_BY_MEASURED_DURATION`. Las cifras sintéticas registradas no demuestran capacidad productiva.

### Estados

`evaluate(now, ledger, config)` es una función pura sobre `LAST_VALID_DURABLE_SNAPSHOT_AT`, `CURRENT_TIME`, `CONFIGURED_RPO`, `IN_PROGRESS_BACKUP`, `LAST_FAILURE` y `DESTINATION_STATE`. La usan la API y el manejador, de modo que un temporizador muerto **también** se ve: el estado se calcula al leer. Una copia solo es válida para estado certificado con CREATE SUCCESS + VERIFY SUCCESS + OFF-HOST DURABILITY SUCCESS.

| Orden | Condición | Estado |
|---|---|---|
| 1 | Sin copia durable válida, o `age > R` | `RPO_BREACHED` |
| 2 | Último intento fallido, con `age ≤ R` | `BACKUP_FAILED` |
| 3 | `age + D_estimada > R`, copia en curso lenta o último tick atrasado | `RPO_AT_RISK` |
| 4 | Resto | `RPO_COMPLIANT` |

Por OD-RPO-03, una copia solo local es `LOCAL_STAGING` y nunca otorga `RPO_CERTIFIED`. Una configuración `CONFIGURED_RPO > 15` queda `NON_COMPLIANT_CONFIGURATION` y no alcanza nunca `RPO_COMPLIANT`.

## 5. T053 y cliente PostgreSQL (`PROJECT_DESIGN_DECISION`)

`T053_REQUIRED_FOR_T052 = 1`: el manejador corre en `backend` y `pg_tool` exige `pg_dump` en esa imagen.

| Campo | Decisión |
|---|---|
| Hecho de servidor | README fija PostgreSQL 18; QA usa 16.2 (desviación declarada) |
| Restricción | `check_tool_compatible` exige cliente ≥ versión mayor del servidor |
| Debian trixie | `postgresql-client-17` 17.11: **no sirve** contra un servidor 18 (MEASURED) |
| Contrato | `POSTGRES_CLIENT_MAJOR_COMPATIBILITY = PG18_COMPATIBLE`; sin servidor PostgreSQL en la imagen ni credenciales embebidas |
| Paquete | `postgresql-client-18` de PGDG `trixie-pgdg`. `OBSERVED_CANDIDATE_VERSION = 18.6-1.pgdg13+2` (2026-11-06), no contractual: la implementación determina el release exacto vigente |
| Imagen | Etapa `base` de `Dockerfile.backend` |
| Reproducibilidad | Clave de firma de PGDG verificada por huella; versión fijada, sin versiones flotantes |
| Verificación | Build: `pg_dump --version` y `pg_restore --version` con mayor 18. Runtime: prechequeo de cada copia (F01, F02) |

**Riesgo a certificar:** con cliente 18 contra servidor 16 la copia es válida, pero la restauración en 16 no está probada. La certificación debe correr contra **PostgreSQL 18**, además de QA 16.2. La parte de imagen sin Docker queda como puerta externa, igual que OBS-09.

## 6. Custodia de la clave

`KEY_CUSTODY_BLOCKER = 0`. Contrato: `SECRET_NOT_IN_GIT`, `SECRET_NOT_IN_IMAGE`, `SECRET_NOT_IN_LOGS`, `SECRET_NOT_IN_DEEPSEEK`, `SECRET_NOT_IN_BACKUP_METADATA` y `SECRET_ONLY_AVAILABLE_TO_REQUIRED_PROCESS`, todos a 1.

- La API residente no recibe la clave.
- El proceso autorizado del tick la obtiene del mecanismo canónico de secretos del anfitrión. Si falta, el tick sigue y la copia informa de F03.
- La clave llega solo al subproceso de copia; `pg_dump` deja de heredarla (corrige `backup_create.py:321`).

Dirección técnica, **no contractual** hasta revalidar el servicio real en el HEAD reconciliado: `EnvironmentFile` `root:root 0600` en la unidad del tick y paso por nombre con `docker compose exec -e`, como hace `cmd_backup`.

Riesgo residual: todos los manejadores comparten el entorno del tick, el mismo dominio de confianza que `KONTROL_MFA_KEYS`. Nunca va a logs, auditoría, ledger ni paquete.

## 7. Destino

| Concepto | Definición |
|---|---|
| `LOCAL_STAGING` | `/data/backups`. Zona de trabajo: nunca cuenta como protección contra pérdida del anfitrión |
| `OFF_HOST_DURABLE_DESTINATION` | Montaje de sistema de archivos declarado por la instalación, por ejemplo NFS o SMB. S3 sigue fuera |

| Señal | Verificación observable |
|---|---|
| `DESTINATION_AVAILABLE` | Montado, escribible y con marcador `.kontrol-destination` de esta instalación |
| `DESTINATION_DURABLE` | `st_dev` distinto de staging y almacén, y tipo de sistema de archivos de red en `/proc/self/mountinfo`; sonda de escritura con fsync. Un disco local cualquiera da `OFF_HOST_UNPROVEN` |
| `COPY_TRANSFERRED` | Copia a `.part`, fsync, rename atómico, fsync del directorio |
| `COPY_VERIFIED` | Relectura íntegra con sha256 igual al del paquete ya verificado |

Límite honesto: el producto observa un montaje de red, no la geografía real. La instalación declara el resto.

## 8. Retención (OD-RPO-01 ratificada)

`OD_RPO_01_RETENTION = B_CONFIGURABLE_PER_INSTALLATION`. **Modifica OD-BK-09 solo para las copias programadas.**

- Política administrada por instalación y **obligatoria para activar la planificación**; sin valor implícito.
- Las copias manuales no se borran automáticamente.
- Una copia no se invalida por edad sin conservar otra alternativa válida.
- Nunca se borra: la última copia válida, una copia en proceso, una necesaria para una recuperación activa, una manual, ni una cuyo sustituto no haya terminado de verificarse.
- El borrado es auditado, idempotente y seguro ante fallos.
- Si un borrado falla, la copia nueva sigue válida y queda el estado observable `RETENTION_DEGRADED`.

## 9. Observabilidad

Superficies existentes: `GET /system/diagnostics` (permiso `license:view`, global) y `DiagnosticoPage` (FR-001-084), en el menú. **Recomendación:** ampliar Diagnóstico con un bloque `backup`; no se crea pantalla nueva salvo que el HEAD reconciliado demuestre que no basta. El permiso es `PROJECT_DESIGN_DECISION`: reutilizar uno existente si corresponde.

Campos mínimos: `LAST_SUCCESSFUL_BACKUP`, `LAST_VALID_DURABLE_BACKUP`, `AGE`, `DURATION`, `PACKAGE_SIZE`, `DESTINATION` por etiqueta (nunca ruta), `NEXT_SCHEDULE`, `CONFIGURED_RPO`, `RPO_STATE` y `LAST_SANITIZED_ERROR`, más `RETENTION_DEGRADED`. Al ser producto visible, exige FRONTEND, MENU, FIELDS, ROLES, SCREEN, ACCESSIBILITY, RESPONSIVE y E2E.

## 10. Auditoría

Catálogo cerrado (`audit_catalog_entries.py`), dueña `ops`/`001`, clase `SECURITY`, emitido por tenant como `INSTALLATION_BACKUP_CREATED`. Política anti-tormenta: a 144 copias al día, lo rutinario va al ledger y a auditoría solo lo que un auditor necesita. Los nombres son **propuestas** a verificar contra la convención.

| Hecho | Destino | Código propuesto |
|---|---|---|
| Programada, iniciada | Ledger | Sin evento: sería ruido |
| Éxito | Auditoría, tras `VERIFIED_DURABLE` | `INSTALLATION_BACKUP_CREATED` existente; la copia programada usa `--no-audit` y emite al final |
| Fallida | Auditoría | `INSTALLATION_BACKUP_FAILED` |
| En riesgo o incumplido | Auditoría, solo en transición | `INSTALLATION_RPO_STATE_CHANGED` |
| Borrado por retención | Auditoría, uno por copia | `INSTALLATION_BACKUP_PURGED` |
| Destino no disponible | Auditoría, solo en transición | `INSTALLATION_BACKUP_DESTINATION_UNAVAILABLE` |
| Cambio de configuración | Auditoría | `INSTALLATION_BACKUP_CONFIG_CHANGED` |

**`T052_PREREQUISITE_AUDIT_TRUTHFULNESS = 1` (decisión de la dueña).** Es prerrequisito de T052, no deuda aplazable: `create` no puede declarar «verificada» antes de `verify`. El futuro diseño garantiza `CREATE_STARTED`, `CREATE_COMPLETED`, `VERIFY_STARTED`, `VERIFY_SUCCEEDED` y `VERIFY_FAILED`, o la convención equivalente del catálogo real, en ledger o auditoría según la política anterior. Nunca `VERIFIED` antes del resultado real. Aplica también a la copia manual.

Prohibido en cualquier evento: clave, contraseñas, dump, contenido documental, rutas y PII innecesaria. `FORBIDDEN_DETAIL_KEYS` lo refuerza. Actor de sistema explícito (R-D0-15-8), con `source` a fijar contra la convención.

## 11. Concurrencia

| Caso | Control |
|---|---|
| Dos ticks | Bloqueo consultivo del tick (R-D0-15-4): el segundo queda `SKIPPED_OVERLAP` |
| Scheduler duplicado | Mismo bloqueo, por base |
| Copia previa activa | Bloqueo consultivo propio en conexión dedicada; además protege de una copia manual si esta adopta el bloqueo |
| Doble efecto | `UNIQUE(slot)` en `backup_runs` (R-D0-15-5, Principio 25) |
| Reinicio durante la copia | El bloqueo cae con la conexión. La siguiente pasada marca `ABANDONED` y limpia `.part` propios |
| Lease expirado | No hay lease temporal: el dueño es la conexión. `BACKUP_TIMEOUT` mata el subproceso |
| Job huérfano | Solo se recupera con el bloqueo tomado; nunca por edad |

Contrato: `ONE_ACTIVE_BACKUP_JOB_PER_INSTALLATION`. Sin `sleep`, sin bloqueo solo en memoria y sin depender de una conexión que pueda volver al pool y perder la semántica. El bloqueo consultivo es **propuesta**: requiere validación con PostgreSQL real, pooling y límites transaccionales del scheduler. Con PgBouncer en modo transacción no sirve, y eso ya afecta al tick actual. El brief de implementación exige prueba real.

## 12. Modelo de fallos

| # | Fallo | Detección | Estado | Auditoría | Visible | Recuperación | Seguridad | Efecto RPO |
|---|---|---|---|---|---|---|---|---|
| F01 | Herramienta ausente | Prechequeo `PG_TOOLS_MISSING` | FAILED | Sí | Sí | Instalar imagen correcta | Sin ruta en el mensaje | Edad crece |
| F02 | Cliente incompatible | `check_tool_compatible` | FAILED | Sí | Sí | Actualizar imagen | Saneado | Edad crece |
| F03 | Clave ausente | Salida 7 / `BACKUP_KEY_MISSING` | FAILED | Sí | Sí | Reponer `backup.env` | Nunca copia sin cifrar | Edad crece |
| F04 | Destino inaccesible | Prechequeo y sonda | FAILED; staging conservado | Transición | Sí | Reintento en franja siguiente | Etiqueta, no ruta | No cuenta si exige off-host |
| F05 | Volumen lleno | Prechequeo y `ENOSPC` | FAILED | Sí | Sí | Limpieza de `.part`; ampliar o retener | Sin parciales válidos | Edad crece |
| F06 | `pg_dump` falla | Código de salida | FAILED | Sí | Sí | Reintento en franja | stderr saneado | Edad crece |
| F07 | Documentos no copiables | Copia inconsistente, salida 9 | FAILED | Sí | Sí | Revisar almacén | Sin nombres de fichero | Edad crece |
| F08 | Paquete no verifica | `verify` ≠ 0 | FAILED; paquete descartado | Sí | Sí | Nueva copia | Nunca cuenta como válida | Edad crece |
| F09 | Transferencia falla | sha256 o E/S | FAILED | Sí | Sí | Reintento; `.part` eliminado | Nunca `rename` sin verificar | Edad crece |
| F10 | Tick perdido | Función pura al leer; `last_tick` | AT_RISK o BREACHED | En el siguiente tick | Sí, aunque el timer esté muerto | Reparar temporizador | n/a | Edad crece; se ve |
| F11 | Excede ventana | `BACKUP_TIMEOUT` | FAILED / AT_RISK | Sí | Sí | Revisar capacidad | Proceso terminado | Riesgo de incumplir |
| F12 | Proceso reinicia | RUNNING huérfano | `ABANDONED` | Sí | Sí | Limpieza y copia nueva | `.part` nunca es copia | Edad crece |
| F13 | Dos jobs compiten | Bloqueo no adquirido | Omitido, registrado | No | Sí | Automática | n/a | Nulo |
| F14 | Retención falla | Excepción del manejador | Copia sigue válida; aviso | Sí | Sí | Revisar destino | No borra nada más | Nulo inmediato; riesgo de F05 |
| F15 | Copia envejece > RPO | `evaluate` | BREACHED | Transición | Sí | Causa subyacente | Sin falso verde | Incumplido y declarado |

## 13. Revisión de amenazas (`THREAT_MODEL_COMPLETE = 1`)

| Amenaza | Control | Prueba |
|---|---|---|
| Fuga de clave por entorno, log o evidencia | §6 | N-CLAVE, M-10 |
| Copia sin cifrar por clave ausente | Fallo cerrado | T-07 |
| Lectura de copias en destino | AES-256-GCM existente | Certificación existente |
| Sustitución de un paquete en destino | Autenticado, sha256 y marcador de instalación | T-11 |
| Ruta maliciosa por configuración | Etiqueta validada; sin salir de la raíz | N-RUTA |
| Falso verde de RPO | Solo `VERIFIED_DURABLE`; función pura | T-16, M-03, M-07 |
| Staging tomado por off-host | §7 | M-04 |
| Borrado malicioso o erróneo | Solo ledger y ventana mínima | T-18, T-19, M-05 |
| Fuga entre empresas en la pantalla | Datos de instalación, sin negocio; permiso global | T-22 |
| Denegación por llenado de disco | Prechequeo y retención | T-10 |
| DeepSeek recibe un secreto | EGRESS previo a cada llamada | Registro por llamada |

Aislamiento: la copia es de instalación y preserva tenants; ningún dato de empresa sale por la superficie nueva.

## 14. Preservación

`SHARED_CORE_IMPACT_DETECTED = 1` · `GOVERNMENT_FUNCTIONAL_CHANGE = 0` · `GOVERNMENT_FILES_TOUCHED = 0`. La capacidad es de instalación: Gobierno puede reutilizarla después fijando su propio RPO, y su retención sigue `POLICY_NOT_RATIFIED`, por lo que allí no se borra sin decisión propia. El formato `.kbk`, `verify` y `restore` no cambian.

## 15. Fuera de alcance, sin absorber

T054 (RTO real: no es requisito de cierre de T052 y **RTO ≤4 h no queda certificado**), T055 (humo de navegador), SPEC054, OBS-09, SPEC057, S3, incrementales y WAL. Deuda nueva propuesta: **RESTORE-DRILL-PERIODIC** (DOC-05 §11, prueba mensual y ejercicio trimestral). `BACKUP-MANUAL-AUDIT-ANTES-DE-VERIFY` deja de ser deuda independiente: pasa a `T052_PREREQUISITE_AUDIT_TRUTHFULNESS`.

## 16. Decisiones

`OWNER_DECISIONS_PENDING = 0`. Ratificadas por la dueña; no se vuelven a elevar.

| Decisión | Valor | Estado |
|---|---|---|
| OD-RPO-01 | `B_CONFIGURABLE_PER_INSTALLATION` | RATIFIED |
| OD-RPO-02 | `B_CONFIGURABLE_MAX_15_MIN`: `CONFIGURED_RPO_MINUTES ≤ 15` | RATIFIED |
| OD-RPO-03 | `A_REQUIRED_FOR_CERTIFIED_STATE`: `OFF_HOST_REQUIRED_FOR_CERTIFIED_STATE = 1` | RATIFIED |
| OD-RPO-06 | `DEEPSEEK_WRITES_ALL_SEMANTIC_CODE_UNDER_CLAUDE_DESIGN_AND_AUDIT` | RATIFIED |
| Inclusión de la auditoría veraz | `INCLUDE_AS_T052_PREREQUISITE = 1` | RATIFIED |
| Arquitectura base | `SCHEDULED_KBK` | RATIFIED |
| `POSTGRES_CLIENT_VERSION_DECISION` | `PROJECT_DESIGN_DECISION` | Sin elevar |

## 17. Tareas futuras

Campos comunes a todas:

- `ROOT_CAUSE`: §2. `INVARIANTS`: I-01..I-08.
- `ROUTES_ALLOWED`: `resources/backend/app/ops/**`, `resources/backend/app/modules/scheduler/**`, `resources/backend/app/modules/system/**`, `resources/backend/app/shared/audit_catalog_entries.py`, `resources/backend/alembic/versions/**`, `resources/backend/tests/**`, `resources/frontend/src/pages/DiagnosticoPage*`, `resources/frontend/src/api/types.ts`, `resources/frontend/e2e/**`, `Dockerfile.backend`, `compose.yaml`, `kontrol.py`, `scripts/scheduler/**`, `scripts/install-scheduler.sh`, `.env.example`, `instalar.md`, `qa/backup_rpo_*`, este delta y su evidencia.
- `ROUTES_FORBIDDEN`: `specs/gov-*`, `resources/backend/app/modules/government/**`, `resources/frontend/src/modules/gobierno/**`, `requerimientos/**`, `.env*` reales, `scripts/install-deepseek-mcp.sh`, formato `.kbk` y `backup_restore.py`, producción.
- `EGRESS_CHECK`: completo antes de cada llamada. `EXECUTOR`: DeepSeek para código y pruebas; Claude audita y certifica.

Invariantes: **I-01** nada cuenta si no está `VERIFIED_DURABLE` · **I-02** edad desde `snapshot_at` · **I-03** sin copia sin cifrar · **I-04** nunca se borra la última válida · **I-05** una sola copia a la vez · **I-06** la clave no sale del proceso de copia · **I-07** un fallo se ve y nunca da verde · **I-08** `.kbk` y la restauración certificada no cambian.

| ID | Objetivo | Actual → esperado | Ficheros | Pruebas | Negativas | Mutantes | Aceptación |
|---|---|---|---|---|---|---|---|
| IMP-01 | Contrato del scheduler | Sin manejador → 3 registrados al final | `scheduler/registry.py`, `ops/` | T-01 | Tick sin copia vencida | M-01 | Notificaciones intactas; R-D0-15-5/6 probados |
| IMP-02 | Herramientas PG (T053) | Sin clientes → cliente 18 fijado | `Dockerfile.backend` | Versión en build y runtime | T-08 | — | Copia en composición, o puerta externa declarada |
| IMP-03 | Acceso al secreto | Tick sin clave → clave solo en el tick | `kontrol.py`, plantillas, `backup_create.py` | T-07 | N-CLAVE | M-10 | La clave no aparece en API, `pg_dump` ni logs |
| IMP-04 | Job y bloqueo | Manual → job con ledger y migración | `ops/`, modelo, alembic | T-03..T-05 | T-06 | M-01, M-03 | Una sola copia; `slot` único; upgrade y downgrade limpios |
| IMP-05 | Destino | Mismo anfitrión → staging y off-host | `ops/`, `compose.yaml` | T-09 | T-11 | M-04, M-06 | Señales §7 observables; staging no cuenta |
| IMP-06 | Retención | Prohibida → según OD-RPO-01 | `ops/` | T-18 | T-19 | M-05 | Nunca borra la última válida |
| IMP-07 | Evaluador | Sin estado → función pura | `ops/` | T-02, T-16 | T-15 | M-02, M-07 | Cuatro estados; `>15` no conforme |
| IMP-08 | Auditoría veraz (`T052_PREREQUISITE_AUDIT_TRUTHFULNESS`) | «Verificada» antes de `verify` → orden real de eventos | `audit_catalog_entries.py`, `ops/` | T-20, T-25 | Sin secretos; `verify` fallido sin `VERIFIED` | M-03, M-09 | Nunca `VERIFIED` antes del resultado real, también en manual |
| IMP-09 | Visibilidad | Nada → bloque en Diagnóstico | `system/api.py`, `DiagnosticoPage*`, `types.ts` | T-21, T-22 | Sin permiso 403 | M-07 | Ficha de pantalla, roles, axe y responsive |
| IMP-10 | Pruebas | — | `tests/` | Todas §18 | Todas | — | Rojo atribuible previo |
| IMP-11 | Mutaciones | — | evidencia | — | — | M-01..M-10 | `BEHAVIORALLY_SURVIVING_MUTANTS = 0` |
| IMP-12 | PostgreSQL | — | — | Suite completa, 16.2 y 18 | — | — | Sin regresión |
| IMP-13 | SQLite | — | — | Suite completa | — | — | Sin regresión; la copia sigue exigiendo PostgreSQL |
| IMP-14 | Copia y restauración | — | `qa/backup_rpo_*` | `backup_restore_cert` + copia programada | — | — | Restaura la última válida; base y documentos coherentes |
| IMP-15 | E2E | — | `e2e/` | E2E de operadora y canónica | Estado degradado | — | Sin reintentos |
| IMP-16 | Seguridad | — | — | Revisión §13 | — | — | Sin hallazgos abiertos |
| IMP-17 | OpenAPI | — | fixtures | Contraste | — | — | Solo el cambio declarado |
| IMP-18 | Residuos | — | — | `pg-test-residuos`, `scope_scan` | — | — | Cero residuos |
| IMP-19 | Convergencia | — | delta, roadmap | Puerta de capacidad | — | — | `UNRUN_REQUIRED_SUITES = 0` |

## 18. Plan de pruebas (`TEST_PLAN_COMPLETE = 1`)

| ID | Caso | ID | Caso |
|---|---|---|---|
| T-01 | Schedule correcto y franja única | T-13 | Tick perdido |
| T-02 | RPO configurable ≤15 y rechazo >15 | T-14 | Excede `BACKUP_TIMEOUT` |
| T-03 | Bloqueo | T-15 | Última copia vencida |
| T-04 | Solape | T-16 | Sin falso verde en cada estado |
| T-05 | Reinicio durante la copia | T-17 | Copia manual intacta |
| T-06 | Dos scheduler | T-18 | Retención correcta |
| T-07 | Clave ausente | T-19 | Nunca borra la última válida |
| T-08 | Cliente incompatible o ausente | T-20 | Auditoría, sin secretos |
| T-09 | Destino caído | T-21 | Estado de operadora |
| T-10 | Disco lleno | T-22 | Permisos y aislamiento multiempresa |
| T-11 | Paquete corrupto o ajeno | T-23 | Restaurar la última válida |
| T-12 | Verify fallido y transferencia fallida | T-24 | Base y documentos coherentes |

T-25: orden de eventos de auditoría y verificación en copia programada y manual. T-26: `RETENTION_DEGRADED` con copia nueva válida. T-27: medición del impacto del tick sobre la 047. T-28: bloqueo con PostgreSQL real y pooling.

`N-CLAVE`: la clave no aparece en logs, ledger, auditoría ni entorno de `pg_dump`. `N-RUTA`: destino fuera de la raíz permitida.

**Mutantes (`MUTATION_PLAN_COMPLETE = 1`):** M-01 omitir bloqueo · M-02 aceptar >15 · M-03 éxito antes de verify · M-04 staging como off-host · M-05 borrar la última válida · M-06 ignorar fallo de transferencia · M-07 ocultar BREACHED · M-08 usar copia corrupta · M-09 no auditar fallo · M-10 pasar la clave a `pg_dump`.

**Certificaciones futuras:** DB: 16.2 y 18, migración subir/bajar/subir, `alembic check`. Copia: `qa/backup_restore_cert.py` más copia programada. E2E: operadora, 3 navegadores si cambia Diagnóstico, y canónica. OpenAPI: contraste con cambio declarado. Accesibilidad y responsive: Diagnóstico.

## 19. Gate y trazabilidad

**Constitution Gate:**

| Principio | Resultado |
|---|---|
| P1 Spec antes que código · P2 Autorización | PASS: sin implementación |
| P3 Trazabilidad · P12 Decisiones | PASS: §20, §16 |
| P6 Seguridad en backend · P15 Datos protegidos | PASS en diseño |
| P7, P11 Frontend, accesibilidad | Planificado (IMP-09) |
| P9 Instalación independiente | PASS: R-D0-15-9 |
| P10, P27 Calidad y mutación | Planificado |
| P13 Integridad · P25 Altas concurrentes | PASS en diseño: `UNIQUE(slot)` |
| P14 Infraestructura reproducible | PASS en diseño: cliente fijado |
| P21 Paridad de motor · P26 Modelos y migraciones | Planificado |
| P22 Autoridad única | PASS: reutiliza scheduler y catálogo |
| P24 Instalación limpia | Planificado |

**Checklist:** requisito confirmado en local · causa raíz · RPO · T053 · clave · destino · estados · fallos · concurrencia · auditoría · visibilidad · pruebas · mutantes · OD-RPO-01..03: completos. **Pendiente:** reconciliación y revalidación contra el `origin/develop` real.

## 20. Trazabilidad

| Requisito | Diseño | Tareas | Pruebas |
|---|---|---|---|
| FR-001-083 RPO | §3, §4 | IMP-01, 04, 07 | T-01..T-06, T-13..T-16 |
| FR-001-083 verificación | §3.2, §7 | IMP-04, 05, 14 | T-11, T-12, T-23, T-24 |
| NFR-001-008 cifrado | §6 | IMP-03 | T-07, N-CLAVE |
| NFR-001-008 runbooks | §11, §17 | IMP-19 | Revisión |
| FR-001-084 Diagnóstico | §9 | IMP-09 | T-21, T-22 |
| T052 | Todo | IMP-01..19 | Todas |
| T053 | §5 | IMP-02 | T-08 |
| ADR-D0-015 | §3.1 | IMP-01 | T-01, T-06 |
| OD-BK-09 enmendada por OD-RPO-01 | §8 | IMP-06 | T-18, T-19, T-26 |
| OD-RPO-02 | §4 | IMP-07 | T-02 |
| OD-RPO-03 | §4, §7 | IMP-05 | T-09, M-04 |
| `T052_PREREQUISITE_AUDIT_TRUTHFULNESS` | §10 | IMP-08 | T-25, M-03 |
| DOC-05 §11 | §7, §8 | IMP-05, 06 | T-09, T-18 |

Requisitos sin diseño: 0. Tareas sin requisito: 0. `TRACEABILITY = 100 %`.

## 21. Contrato de producto completo

`PRODUCT_BEFORE_TESTS = 1` · `TESTS_VALIDATE_PRODUCT = 1` · `TESTS_ARE_NOT_PRODUCT = 1` · `QA_ARTIFACTS_ARE_NOT_PRODUCT = 1` · `MOCKS_ARE_NOT_PRODUCT = 1` · `FIXTURES_ARE_NOT_PRODUCT = 1` · `FUNCTIONAL_PRODUCT_COMPLETENESS_REQUIRED = 1`.

Una persona autorizada debe poder, desde el producto real: consultar y configurar el RPO (≤15 min), la retención y el destino soportado; habilitar o deshabilitar la planificación; y observar `CONFIGURED_RPO`, `LAST_SUCCESSFUL_BACKUP`, `LAST_VALID_BACKUP`, `LAST_VALID_DURABLE_OFF_HOST_BACKUP`, `BACKUP_AGE`, `BACKUP_DURATION`, `PACKAGE_SIZE`, `DESTINATION`, `NEXT_SCHEDULE`, `RPO_STATE` y `LAST_SANITIZED_ERROR`. Test, fixture, mock, fila de base, guion QA, API aislada o E2E que inyecte el resultado no sustituyen esa superficie.

## 22. Implementación local (T052-RPO-IMPLEMENTATION-02, 2026-11-07)

Diferencias con el diseño, todas de proyecto:

- **Estados.** El orden de §4 se sustituye por `DISABLED`, `MISCONFIGURED`, `NO_VALID_BACKUP`, `LOCAL_ONLY`, `RPO_BREACHED`, `DEGRADED`, `RPO_AT_RISK`, `RPO_CERTIFIED` y `RPO_MET`, en `app/ops/backup_rpo.py`, conforme al encargo.
- **Exclusión.** Además del bloqueo consultivo, un índice único parcial impide dos filas `RUNNING`, también con PgBouncer.
- **`CREATED`.** Estado nuevo de copia manual creada y sin verificar: nunca cuenta como válida.
- **Eventos.** `INSTALLATION_BACKUP_CREATED` significa «creada, pendiente de verificación». Se añaden `VERIFIED`, `VERIFY_FAILED`, `FAILED`, `PURGED`, `DESTINATION_UNAVAILABLE`, `CONFIG_CHANGED` y `RPO_STATE_CHANGED`.
- **Retención en recuperación.** `python -m app.ops.backup hold BACKUP_ID` retiene una copia antes de restaurar; `release` la suelta. La operadora debe usarlo: no hay marca automática de recuperación activa.

| Frontera | Estado |
|---|---|
| `T052_TECHNICAL_FOUNDATION` | LOCAL_COMPLETE |
| `T052_LOCAL_PRODUCT_IMPLEMENTATION` | LOCAL_COMPLETE |
| `T052_LOCAL_NON_PG_CERTIFICATION` | PASS |
| `T052_POSTGRES_CERTIFICATION` | NOT_EXECUTED_ENVIRONMENT_UNAVAILABLE. T061 va primero |
| `T052_OFF_HOST_CERTIFICATION` | NOT_MEASURED |
| `T052_CAPACITY_CERTIFICATION` | NOT_MEASURED |
| `T052_E2E_CERTIFICATION` | NOT_EXECUTED_ENVIRONMENT_UNAVAILABLE |
| `T052_PUBLICATION` | Bloqueada: `GIT_AUTH_ONLY` |
| `T052_OWNER_UAT` | NO |

Sin resolver, por rutas prohibidas: tras un `restore` el ledger no se reinicia (§3.2), porque `backup_restore.py` no se toca. Una fila `RUNNING` restaurada se abandona sola, pero las copias anteriores siguen listadas: RESTORE-LEDGER-RESET.
