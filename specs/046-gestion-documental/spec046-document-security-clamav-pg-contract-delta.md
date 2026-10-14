# SPEC 046 · Delta dirigida — OBS-08 + ENTORNO-SIN-CLAMSCAN (contrato de QA del analizador y de las carreras)

Dueña funcional: 046 (gestión documental; T-046-106, FR-046-115). Apoyo: 054 (arnés, runner E2E; enlace cruzado en
`specs/012-auditoria-integral-e2e/spec054-document-security-clamav-pg-contract-delta.md`). Fecha: 2026-10-14. HEAD de
partida `4fa9e7c`. Decisión de inicio ratificada por la dueña (solo autoriza investigar). Evidencia en
`evidence/document-security-clamav-pg-contract/`. Producto 0, migraciones 0, esquema 0, analizador no instalado, no simulado, no apagado.

**Veredicto: OBS-08 → CLOSED / CONVERGED (con autoridad existente) · ENTORNO-SIN-CLAMSCAN → BLOCKED BY OWNER DECISION.**
Son dos decisiones distintas y no se combinan.

## 1. Checkpoint — `checkpoint.md`
`4fa9e7c` = origin, limpio, 0/0/0, puertos libres; `clamscan`/`clamdscan`/`freshclam` ausentes; `KONTROL_CLAMSCAN_PATH` sin definir.

## 2. `/speckit.specify` — FR-DOCENV-001…028
Recogidos del encargo; los de investigación (001–011) se cumplen en §3; los de prohibición (004–006, 012–018, 021–024) se
verifican en §6–§8; los de no-cambio (025–028) en §8.

## 3. `/speckit.clarify` — descubrimiento (todo con autoridad física)

| Pregunta | Respuesta | Evidencia |
|---|---|---|
| Q1 ¿`clamscan` es REQUERIDO en el QA canónico? | **No hay autoridad que lo exija**: CL-046-09/FR-046-072 lo hacen «capacidad de despliegue configurable»; la certificación de 046 (ESC-046-01) **lo usó** (ClamAV 1.4.3 real), sin guion reproducible; el runner E2E y las pruebas EICAR tratan su ausencia como omisión declarada | `scanner-architecture.md`, `scanner-security-contract.md`, `environment-matrix.md` |
| Q2 ¿Qué capas lo necesitan? | toda subida con `scan_required` (defecto): backend SQLite y PostgreSQL (35 pruebas), n9 (2, entrega exige `CLEAN`), E2E (4); no hay capa «unidad» separada en 046 | `clamav-failure-inventory.md`, `e2e-skip-inventory.md` |
| Q3 ¿Hay doble ratificado? | existe `set_scanner()` «para pruebas» y `DisabledScanner` (declara `SKIPPED`), pero **ningún** doble que diga `CLEAN`, y §159/closeout rechazan dobles como evidencia | `scanner-architecture.md` |
| Q4 ¿Las carreras son PostgreSQL-only por contrato? | **sí**: FR-046-115 + `conc-046-concurrent-version-delta.md` («PostgreSQL decide», G-CONC-046-06) + `tests/concurrency.py` («carreras forzadas contra PostgreSQL», `pg_backend_pid`/`pg_stat_activity`) + P21; además `test_subidas_a_documentos_distintos_no_se_esperan` y `test_otro_tenant…` dependen del bloqueo de fila (SQLite bloquea toda la base) | `document-race-inventory.md`, `pg-backend-pid-analysis.md` |
| Q5 ¿Debe ser explícito? | sí, con el marcador canónico del repo (`skipif(not PG, reason=… (P21))`, precedentes de licencias, roles, picklist) | `pg-only-convention.md` |
| Q6 ¿Debe QA contener ClamAV? | decisión de la dueña: viable (paquete Debian 1.4.3, privilegios o prefijo de usuario, firmas ≈300 MB con red, minutos por suite), sin autoridad hoy | `clamav-qa-feasibility.md`, `virus-definition-requirements.md`, `option-matrix.md` |
| Q7/Q8 ¿Qué son los 42/35/4? | SQLite 42 = **35 del analizador** (S1 subida rechazada 17 + S2 consecuencias 18) + **7 que NO lo son** (`test_documents_legacy_import.py`: `StaleDataError` por la conexión compartida + petición HTTP en medio de la sesión; PostgreSQL los pasa con el mismo analizador ausente); PostgreSQL 37 = 35 + 2 n9 (`FILE_NOT_SCANNED`); E2E 4 = cargas de `documents.spec.ts` ×3 y teclado de `documents-a11y.spec.ts`, por `KONTROL_E2E_SCANNER_AVAILABLE=false` del runner; UNKNOWN 0 | `clamav-failure-inventory.md`, `failures-*-tbline.txt` |

`RACE_PATH_REACHED_WITHOUT_SCANNER = NO` · `DOCUMENT_RACE_CURRENTLY_PG_SPECIFIC = YES` · `MATERIAL OQ`: 1 (solo para ENTORNO).

## 4. `/speckit.plan`, CONSTITUTION GATE (diagnóstico), checklist y tasks
W01–W29 del encargo; gate G01–G34 cumplidos para el diagnóstico (sin bypass, sin instalación, sin marcador antes de la
autoridad, producto 0, BLOCKER 0, UNKNOWN 0, trazabilidad 100 %) → diagnóstico ejecutado (§3). Tareas T01–T09 CLAUDE_ONLY;
`DEEPSEEK CALLS = 0`.

## 5. Compuerta de decisión
`CAN_EXISTING_CONTRACT_RESOLVE_POLICY_WITHOUT_OWNER`: **OBS-08 YES** (autoridad citada en Q4/Q5) → autorización de
implementación consumida solo para el marcador y su contrato · **ENTORNO-SIN-CLAMSCAN NO** → STOP, `owner-decision.md`.

## 6. `/speckit.implement` — `implementation.md`
Marcador canónico en las **siete** pruebas con mecanismo de carrera dependiente de PostgreSQL (seis de OBS-08 + una
descubierta por el contrato estático), con razón que cita FR-046-115/conc-046/P21; `tests/test_documents_carreras_contrato.py`
(DOCENV-05/12/13/14/15). Ninguna aserción cambia; el analizador no se toca.

## 7. Mutaciones — `mutation-campaign.md`
10/10 muertas (M-04 y M-07 tras reforzar el contrato; la campaña destapó la séptima carrera).

## 8. Certificación — `directed-tests.md`, `sqlite-full-1.md`, `sqlite-full-2.md`, `postgres-full.md`, `openapi.md`, `global-e2e.md`
Véase §9 (se completa con las corridas).

## 9. Resultados, `/speckit.analyze` final y veredicto

| Corrida | Resultado | Clasificación |
|---|---|---|
| Dirigidas | SQLite documentos 33 failed · 32 passed · 12 skipped (9 nodos de carrera con razón + 3 previas); PostgreSQL 37 failed · 39 passed · 4 skipped (sin cambio en los 37); regresiones UoM/almacenes/auth/ACS 78+1 / 79 | `directed-tests.md` |
| Mutaciones | 10/10 muertas | `mutation-campaign.md` |
| SQLite completa ×2 | 1637 / 33 / 1049 (26 analizador + 7 OBS-10; 0 nuevos) | `sqlite-full-1.md`, `sqlite-full-2.md` |
| PostgreSQL completa | 2653 / 37 / 29 (35 analizador + 2 n9; 0 nuevos) | `postgres-full.md` |
| OpenAPI · E2E | 544/533/11 sin cambio · 280/0/4 (analizador `None`) | `openapi.md`, `global-e2e.md` |

`final-analyze.md`: BLOCKER 0 y MATERIAL OQ 0 para OBS-08; 1 y 1 declarados para ENTORNO-SIN-CLAMSCAN. **Veredicto:
OBS-08 CLOSED / CONVERGED · ENTORNO-SIN-CLAMSCAN BLOCKED BY OWNER DECISION** (`convergence.md`). MASTER57 57; SPEC057 PLANNED /
NOT STARTED; NEXT MASTER SPEC NOT YET PRIORITIZED.

---

# Continuación · decisión A + A2 ratificada (2026-10-14): ClamAV real en el QA canónico, prefijo de usuario sin privilegios

`[X] A — REAL CLAMAV IN CANONICAL QA` · `[X] A2 — NON-PRIVILEGED USER-PREFIX PROVISIONING`. OBS-08 sigue CLOSED. HEAD de
partida `d377db7` = origin, limpio, 0/0/0, puertos libres. No autoriza: cambiar `scanning.py` ni producto, dobles `CLEAN`,
`SCAN_FAILED` como éxito, firmas en Git, imágenes de producción, `sudo`.

## 10. `/speckit.specify` — FR-CLAM-A2-001…038
Recogidos del encargo: analizador real, sin root, reproducible, producto y `scanning.py` intactos, falso seguro intacto,
`KONTROL_CLAMSCAN_PATH`/`KONTROL_CLAMAV_DB` explícitos, binario y firmas en caché de usuario fuera de Git, versión del motor
y de la base registradas en cada certificación, sumas verificadas donde existan, CLEAN y EICAR probados en cada
certificación, solo EICAR, el QA canónico no se declara certificado si el preflight falla, las cuatro E2E se ejecutan, las
siete carreras siguen PostgreSQL-only, sin bypass ni skips amplios ni reintento a verde, MASTER57/SPEC057/NEXT sin cambio.

## 11. `/speckit.clarify`

| Registro | Valor |
|---|---|
| `QA_OS` · `QA_DISTRO` · `QA_ARCH` · `QA_PACKAGE_MANAGER` · `QA_HAS_SUDO` | Linux · Debian 13 (trixie), glibc 2.41 · x86_64 · apt (`apt-get download` no requiere root) · **NO** (contraseña requerida) |
| `QA_TOOL_CACHE_CONVENTION` · `QA_CACHE_WRITABLE` | no hay convención previa de caché de herramientas en `qa/`; `~/.cache` existe y es escribible; `XDG_CACHE_HOME` sin definir → el prefijo canónico será `${XDG_CACHE_HOME:-~/.cache}/kontrol-qa/clamav/<versión>` (configurable con `KONTROL_QA_CLAMAV_HOME`), fuera del repo y del CWD |
| `SYSTEM_CLAMSCAN_PRESENT` · `SYSTEM_FRESHCLAM_PRESENT` · `SYSTEM_CLAMAV_DB_PRESENT` · variables actuales | no · no · no · sin definir |
| `ENGINE_VERSION_AUTHORITY` · `REQUIRED_ENGINE_VERSION` · `COMPATIBLE_RANGE` | closeout 046 §7 certificó **ClamAV 1.4.3** (sin exigir exactitud); el paquete Debian trixie es `1.4.3+dfsg-1`: **misma versión semántica**, sin cambio de mayor/menor → aceptada 1.4.x |
| Mecanismo A2 elegido | **P1**: `apt-get download` (sin root; `.deb` firmados por el repositorio Debian, suma SHA256 contrastada con `apt-cache show`) + `dpkg-deb -x` al prefijo de usuario. Ni compilación ni binarios no oficiales |
| `PACKAGE_AVAILABLE` · `PACKAGE_VERSION` · `PACKAGE_ARCH` | sí · `clamav 1.4.3+dfsg-1`, `libclamav12`, `clamav-freshclam`, `clamav-base` · amd64 |
| `DEPENDENCY_CLOSURE` | `libclamav12` → libbz2, libjson-c5, libmspack0t64, libpcre2-8-0, libxml2, libssl3t64, libcurl4t64, zlib1g: **todas ya instaladas en el sistema** (dpkg); solo `libclamav.so.12` va en el prefijo → `LD_LIBRARY_PATH` por un **envoltorio** `bin/clamscan` (el producto ejecuta la ruta de `KONTROL_CLAMSCAN_PATH` sin tocar el entorno) |
| `DB_REQUIRED_FILES` · `FRESHCLAM_SUPPORTED` · `FRESHCLAM_NETWORK_REQUIRED` · `DB_CACHEABLE` · `DB_APPROX_SIZE` | `main.cvd`, `daily.cvd/cld`, `bytecode.cvd` · sí (`freshclam --config-file --datadir` sin root) · sí · sí (prefijo) · ≈ 200–300 MB |
| Política de firmas | reutilizar la caché si el preflight pasa (CLEAN + EICAR); refrescar con `freshclam` si falta o si se pide (`--refrescar`); registrar versión/fecha (`sigtool --info`) en cada certificación; fallar visible si no hay base usable; nunca en Git (`.gitignore` ya excluye nada de esto por estar fuera del repo) |
| `PROVISION_COMMAND` · `PREFLIGHT_COMMAND` · `PG_CERT_COMMAND` · `E2E_COMMAND` | `python qa/clamav-qa.py provisionar` · `python qa/clamav-qa.py preflight` (QAC-01…08, imprime versión y fecha, sale 1 si falla) · `eval "$(python qa/clamav-qa.py entorno)" && KONTROL_TEST_DB_URL=… pytest tests` · `python qa/e2e-run.py --con-analizador` (exige preflight y exporta las rutas al backend; sin la opción, comportamiento local de siempre) |
| Preflight QAC-01…08 | arranque del binario · versión 1.4.x · base carga (`clamscan --version` con base) · PDF sintético CLEAN · EICAR INFECTED · error de proceso ≠ CLEAN (base vacía → rc 2) · rutas exportadas · versión del motor y de la base en la evidencia |
| `MATERIAL OQ` | 0 (la decisión de política está tomada; lo que queda es viabilidad, medida en la POC) |

## 12. `/speckit.plan`, CONSTITUTION GATE (diagnóstico), checklist y tasks
W01–W30 del encargo. Gate G01–G39 cumplidos para el diagnóstico (sin sudo, sin producto, sin `scanning.py`, sin doble, sin
firmas en Git, acciones acotadas a un prefijo temporal). Tareas T01–T09 CLAUDE_ONLY; `DEEPSEEK CALLS = 0`.

## 13. A2-POC (etapa 1) y compuerta material
Véase `a2-feasibility-poc.md` (se completa con la corrida).

`a2-feasibility-poc.md`: **PASS** (paquetes oficiales sin root con sumas verificadas; 1.4.3; una sola biblioteca en el prefijo;
firmas por `freshclam` en directorio de usuario; CLEAN rc 0, EICAR rc 1, sin firmas rc 2; nada fuera del prefijo temporal).
Compuerta material A2: PASS → autorización etapa 2 consumida.

## 14. `/speckit.implement` — `implementation-a2.md`, `signature-policy.md`, `provisioning-run.txt`
Provisionado real en la caché del usuario: 3 min 54 s con red (15 MB de paquetes + 108 MB de firmas); preflight 14,6 s;
segunda provisión idempotente 14,4 s sin descargas; `entorno` exporta las dos variables.

## 15. Certificación con analizador real

| Corrida | Resultado | Evidencia |
|---|---|---|
| Dirigidas | SQLite documentos + CLAM 7 failed (OBS-10) · 75 passed · 9 skipped; PostgreSQL documentos + n9 + CLAM **93 passed · 1 skipped** (35 del analizador, 2 n9 y las siete carreras pasan) | `directed-tests-a2.md` |
| Mutaciones | 14/14 muertas | `mutation-campaign-a2.md` |
| SQLite completa ×2 | 1679 / 8 / 1046 (7 OBS-10 + 1 intermitente de reloj conocido, OBS-11); analizador 0 | `sqlite-full-a2.md` |
| PostgreSQL completa | 2706 / 1 / 26 (solo el intermitente de reloj); analizador 0; carreras ejecutadas | `postgres-full-a2.md` |
| E2E ×2 `--con-analizador` | 284 / 0 / 0 ambas (las cuatro cargas se ejecutan; manifiesto con motor y firmas) | `global-e2e-a2.md` |
| OpenAPI | 544/533/11 sin cambio | `openapi.md` |

## 16. `/speckit.analyze` final y veredicto
`final-analyze-a2.md`: todo a 0; trazabilidad 100 % (`traceability-matrix-a2.md`). **Veredicto: ENTORNO-SIN-CLAMSCAN →
CLOSED / CONVERGED** (`convergence-a2.md`). OBS-08 sigue CLOSED. OBS-09, OBS-10 y la nueva OBS-11 registradas, no absorbidas.
Orden canónica: `python qa/clamav_qa.py provisionar` · `eval "$(python qa/clamav_qa.py entorno)"` · suite PostgreSQL ·
`qa/e2e-run.py --con-analizador`. MASTER57 57; SPEC057 PLANNED / NOT STARTED; NEXT MASTER SPEC NOT YET PRIORITIZED.
