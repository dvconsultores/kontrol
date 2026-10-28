# Orquestación Claude / DeepSeek — ciclo 06

Regla aplicada: Claude diseña, redacta cada encargo, audita, aplica tal cual, prueba y certifica; DeepSeek escribe todo
el código de producto, las pruebas, el guion de QA y la documentación de producto. **Código de producto escrito por
Claude: 0 líneas.** Claude escribió solo artefactos de diseño y evidencia (delta, inventarios, `catalogo.md`,
roadmap, esta evidencia), `.gitignore` y sus herramientas del scratchpad (aplicador, extractor, EGRESS, mutador,
validador del manifiesto). No se aplicó ningún retoque de formato (`ruff --fix` no se usó).

Cada llamada pasó EGRESS (`ENV_FILES=SECRETS=TOKENS=PRIVATE_KEYS=PROD_URLS=REAL_PII=0`); las alertas `ENV_FILES` de
`kontrol.py`, `instalar.md`, `scripts/backup.sh` y los encargos T05/T08 eran el nombre del fichero `.env` como ruta,
no su contenido (revisado a mano). Un encargo (T04) pedía generar la contraseña sintética con un prefijo literal; se reescribió para
que la genere `secrets.token_urlsafe` antes de enviarlo.

| Tarea | Modelo | Intentos | Resultado | Motivos de rechazo |
|---|---|---|---|---|
| T01 cifrado STREAM | pro | 3 | PASS (r2) | `seek` en descifrado; código de error ambiguo (Claude); `base64.binascii`; import en bucle · r1: tipado mypy de `readinto` y protocolos `ByteReader`/`ByteWriter` que la gemela necesitaba |
| T02 paquete | pro | 3 | PASS (r2) | `TarInfo.size` del texto en claro (grave); imports inexistentes; `type: ignore` · r1: F401, `__exit__ -> bool`, tipos de flujo, BB-08 mal estructurada, `except` silenciosos, recursos ante fallo · r2: bloque 1 omitido por estar contenido en el 2 |
| T02B referencias reales | flash | 2 | PASS | `REF_RE` del contrato de Claude rechazaba `report-…csv`; c0 inventó la importación (fallo del encargo, que no la incluía) |
| T02C truncado | flash | 2 | PASS | defecto de producto destapado por BR-08 (`tarfile.ReadError` en bruto); r1: el corte al 90 % caía en el relleno del tar (diseño de Claude) |
| T03 creación | pro | 3 + división | PASS (T03C) | `BundleError` sin importar; cabecera como dict; `Path` en vez de flujo; `except Exception`; volcado en claro a disco (cambio de diseño: `pg_dump` a stdout); base de prueba compartida (defecto del encargo) · r1: `psycopg2.connect(**libpq_env)` (contrato de Claude), DSN SQLAlchemy, sin `pg_bin_dir`, INSERT sin id, `int()` de uuid · r2: dos SEARCH duplicados → T03C |
| T03C | pro | 1 | PASS | `entity_id` = clave primaria de la instalación (decisión de Claude: `varchar(36)`); objetos ORM desligados |
| T04 restauración | pro | 3 + división | PASS (T04C) | c0: `seq` desde 0, staging con el nombre del fichero, sin comprobación de Alembic posterior, imports en funciones, pruebas que MIGRABAN el destino · encargo de Claude con `auth_sessions`, `StoredFile.tenant_id` y `Tenant` sin instalación (errores de Claude) · r1: conexión (contrato de Claude), `rowcount`, BR-01/07/08 mal construidas · r2 dividida en A (producto) y B (pruebas) porque el puente no admitía 49 KB; SEARCH no únicos → T04C |
| T04C | flash | 1 | PASS | restos mecánicos con anclas únicas dadas por Claude |
| T05 CLI | pro/flash | 3 | PASS (r2) | `load_key` fuera del `try`; `--key` aceptado como abreviatura de `--key-file` (defecto real, `allow_abbrev=False`); tipado · r1: `BackupResult` importado desde la CLI |
| T06 catálogo | flash | 1 | PASS | — |
| T07 certificación | pro/flash | 3 | PASS (r2) | **`alembic downgrade base` no pedido en el desastre (grave, rechazado)**; columna `event_type`; migración sin comprobar; limpieza fuera del veredicto · r1→ corrida real: C-08 usaba un parámetro `date` (diseño de Claude) |
| T07C | flash | 1 | PASS | lint estricto y veredicto que exige IDs y métricas |
| T08 runbook | pro | 1 | PASS | — |
| T09 pruebas de supervivientes | pro/flash | 3 | PASS (r2) | c0 inventó API (`BundleWriter` privado, `create_backup` posicional, fixture `pg_bin`, `match=` sobre el código) · r1: ancla de fin de fichero no única (fallo de Claude) |
| T09B prueba de punto de corte | flash | 1 | PASS | — (mata M06-26) |
| T050 manifiesto de licencia (convergencia F1) | flash | 1 | PASS | — (rojo medido antes de aplicar el producto) |
| T051 EDGE-21 en la certificación (convergencia F2) | pro/flash | 2 | PASS (r1) | el bloque de la suborden inventó el payload y `serialization.encode_rs256` (fallo del encargo, que no dio el payload literal); los otros 6 bloques se aplicaron |

Bloques omitidos al aplicar (siempre por no casar de forma única o por estar contenidos en otro bloque del mismo
parche; ninguno se editó): T02-r2 #1; T03-r2 #16–17; T04-r2a #3; T04-r2b #2, #5, #25, #26; T09-r1 #7; T051-c0 #2. Su contenido se
volvió a pedir en una tarea o reintento propio.

Incidencias del puente: dos respuestas largas quedaron en `tool-results` porque el subagente terminó con un error de la
API después de recibir la respuesta (T04-r1, T07-c0); se recuperaron del fichero literal. Un intento (T04-r2) no llegó a
enviarse (argumento demasiado grande) y no consumió reintento.

Coste DeepSeek del ciclo: **35 llamadas** (22 `deepseek-v4-pro`, 13 `deepseek-v4-flash`), **201 832** tokens de
entrada y **150 457** de salida, **≈ 0,19 USD**.
