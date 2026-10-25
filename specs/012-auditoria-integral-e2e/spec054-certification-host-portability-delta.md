# SPEC 054 · Delta — CERTIFICATION-HOST-PORTABILITY

| Campo | Valor |
|---|---|
| Deuda | **CERTIFICATION-HOST-PORTABILITY** (G1–G4; dueña 054, apoyo 052), dentro de CANONICALIZE-CERTIFICATION-ENVIRONMENT |
| Decisiones | OD-CERT-27 = A (certificación oficial en un entorno dedicado; la OPTION B no está autorizada) · OD-CERT-28 = 28-B (delta de portabilidad antes de aprovisionar el anfitrión; la 28-A no está autorizada) |
| HEAD de entrada | `3300183` (sin confirmar: la implementación de CANONICALIZE-CERTIFICATION-ENVIRONMENT) |
| Evidencia | `evidence/certification-host-portability/` |
| Autorización de implement | Encargo de la dueña «OD-CERT-28 RATIFICADA + CERTIFICATION-HOST-PORTABILITY DELTA» (Constitución P2) |

## 1. Specify

**Objetivo.** La misma orden `python3 qa/certificar-release.py` produce el mismo perfil certificado en cualquier anfitrión
compatible (Debian 13 amd64), sin depender del número de CPU, de la variable `CI`, del `.venv` del backend, del HOME del
usuario ni del estado de la estación. El árbol certificado queda ligado criptográficamente a la identidad de la corrida.

**Requisitos.**
- **R1 (G1):** CANONICAL_E2E_WORKERS = 6 en la ruta canónica, sea cual sea el número de CPU. La corrida verifica en el
  `suite.log` que Playwright usó exactamente 6 workers y, si no, falla cerrado.
- **R2 (G2):** CANONICAL_E2E_RETRIES = 0 en la ruta canónica, esté o no definida `CI`. `CI` se canonicaliza (no llega a
  ningún sujeto). Un resultado `flaky` sigue siendo un fallo. No se tocan las rutas no canónicas.
- **R3 (§7):** una política de entorno versionada clasifica cada variable heredada (CANONICALIZED, ALLOWED_INHERITED,
  FORBIDDEN, SECRET, IRRELEVANT). Una variable FORBIDDEN hace fallar el preflight (RC 70). Las SECRET no llegan a los
  sujetos. El manifiesto registra solo nombres, nunca valores.
- **R4 (G3):** PostgreSQL de QA sale de una fuente fijada y verificada:
  - la rueda `pgserver` 0.1.4 cp311 (PostgreSQL 16.2);
  - `btree_gist` del `.deb` `postgresql-16_16.2-1.pgdg120+2`;
  - ambos con sha256 en `qa/postgres_qa.json`, instalados en un directorio propio bajo el HOME de certificación;
  - sin `.venv`, sin PATH, sin compilador, sin descarga flotante.

  El preflight ya no exige el `.venv`. El postmaster en marcha debe ser el binario fijado y la versión debe ser la fijada.
- **R5 (G4):** CERTIFICATION_INPUT_TREE_HASH es el objeto árbol de Git del árbol certificado, calculado con un índice y un
  almacén de objetos temporales, sin escribir en el repositorio y con una política de exclusión explícita y versionada.
  CANONICAL_RUN_INPUT_HASH v2 lo incorpora (además de la fuente de PostgreSQL de QA). Sin árbol no hay hash de entrada.
  El árbol se recalcula al cerrar la corrida y debe coincidir.
- **R6:** el uso queda documentado.

**Fuera de alcance.**
- Reducir workers, proyectos o casos (OPTION B).
- Cambiar umbrales.
- Ampliar el soporte de SO.
- E2E-RESULT-MANIFEST-POST-VALIDITY-SEMANTICS (deuda aparte).
- `qa/pg-migration-validation.sh` y las rutas de desarrollo no canónicas.

## 2. Clarify (medido)

| Hecho | Medida |
|---|---|
| G1 | `playwright.config.ts` no fija `workers`; `suite.log`: «Running 284 tests using 6 workers» con 12 CPU lógicas |
| G2 | `playwright.config.ts:19` `retries: process.env.CI ? 2 : 0`; `entorno_de_sujeto` solo quita variables de Python |
| Perfil E2E canónico | `qa/e2e_corrida.py` lanza `--project=chromium` y los 4 proyectos de licencia (Chrome): 280 + 4 pruebas en Chromium; Firefox y WebKit **no** forman parte de la E2E canónica |
| Paso de argumentos | `qa/e2e-run.py … -- <args>` llega a Playwright; `--workers` y `--retries` de la CLI prevalecen sobre la configuración |
| G3 | `qa/pg-provision.sh:12` y `PG_BIN` del módulo apuntan a `resources/backend/.venv/lib/python3.11/site-packages/pgserver`; `btree_gist` se compilaba con PGXS (gcc, make y `curl` de la fuente sin verificar) |
| Estado oculto | La estación **no tiene `gcc` ni `make`**: el `btree_gist.so` del `.venv` es un artefacto compilado en el pasado, no reproducible |
| Fuente fijada = certificada | La rueda `pgserver-0.1.4-cp311-…whl` (sha256 `d595789b…8813`, igual que en PyPI) contiene 1649 ficheros `pginstall/` y `pgserver.libs/` **idénticos** a los del `.venv`; los bits de ejecución vienen en la rueda |
| `btree_gist` sin compilador | `postgresql-16_16.2-1.pgdg120+2_amd64.deb` (sha256 `c9de1cc6…d699`, igual que en el índice `Packages` de PGDG): `btree_gist.so` solo enlaza libc; la extensión 1.7 funciona con los binarios fijados (restricción de exclusión GiST probada, solape rechazado) |
| `.deb` | `ar` con `debian-binary`, `control.tar.xz` y `data.tar.xz`: se desempaqueta con la biblioteca estándar |
| Bibliotecas | `psql` resuelve `libpq` por ruta relativa `../../../pgserver.libs`: hay que conservar `pgserver/pginstall/` y `pgserver.libs/` como hermanos |
| G4 | `hash_de_entrada` cubre HEAD, digests, locks, plataforma y referencia, pero no el contenido sin confirmar |
| Lecturas de docs por pruebas | Las pruebas leen `docs/governance/**`, `docs/evidence/cve-review.md` y `specs/001-fundacion/certified-deployment-base.json`; ninguna lee `specs/**/*.md`, `specs/**/evidence/**` ni `docs/roadmap/**` |

## 3. Diseño

**D1 — Perfil E2E (R1, R2).** Constantes `E2E_WORKERS_CANONICOS = 6` y `E2E_REINTENTOS_CANONICOS = 0`.
- `orden_de_e2e(py_c, py_r)` construye la orden con `"--", "--workers=6", "--retries=0"` al final. La usa `etapa_e2e`.
- `verificar_perfil_e2e(texto_del_suite_log)` extrae `using N worker(s)`. Lanza `FalloDeCertificacion` si falta o si N ≠ 6. Fija `CANONICAL_E2E_WORKERS` y `CANONICAL_E2E_RETRIES` en el manifiesto.

**D2 — Política de entorno v1 (R3).** `POLITICA_DE_ENTORNO_VERSION = 1`. Precedencia: CANONICALIZED → ALLOWED_INHERITED →
FORBIDDEN → SECRET → IRRELEVANT.

| Clase | Contenido |
|---|---|
| CANONICALIZED | `CI`, las variables de Python ya excluidas (`PYTHONPATH`, `PYTHONHOME`…) y `PYTHONDONTWRITEBYTECODE` (fijada a 1) |
| ALLOWED_INHERITED | `PATH`, `HOME`, `USER`, `LOGNAME`, `SHELL`, `LANG`, `LANGUAGE`, `LC_*`, `TERM`, `TMPDIR`, `TZ`, `XDG_CACHE_HOME`, `XDG_RUNTIME_DIR`, `SSL_CERT_FILE`, `SSL_CERT_DIR`, `NODE_EXTRA_CA_CERTS`, `PLAYWRIGHT_BROWSERS_PATH`, `PYTHONIOENCODING`, `PYTHONUTF8`, `PYTHONUNBUFFERED`, `KONTROL_QA_CERT_HOME`, `KONTROL_CLAMSCAN_PATH`, `KONTROL_CLAMAV_DB` |
| FORBIDDEN, por prefijo | `PYTEST_`, `PWTEST_`, `PLAYWRIGHT_`, `PYTHON`, `KONTROL_`, `UV_`, `PIP_`, `NPM_CONFIG_`, `npm_config_`, `COVERAGE_`, `PG`, `GIT_CONFIG` |
| FORBIDDEN, por nombre | `PWDEBUG`, `NODE_OPTIONS`, `NODE_PATH`, `NODE_ENV`, `LD_PRELOAD`, `LD_LIBRARY_PATH`, `LD_AUDIT` y las variables git que cambian el repositorio, el índice o los objetos (`GIT_DIR`, `GIT_WORK_TREE`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`, `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_COMMON_DIR`, `GIT_NAMESPACE`, `GIT_CEILING_DIRECTORIES`, `GIT_DISCOVERY_ACROSS_FILESYSTEM`, `GIT_ATTR_SOURCE`, `GIT_GRAFT_FILE`, `GIT_REPLACE_REF_BASE`, `GIT_NO_REPLACE_OBJECTS`). `GIT_EDITOR`, `GIT_PAGER`, `GIT_ASKPASS`… son IRRELEVANT (medido: el preflight real rechazaba `GIT_EDITOR`, que hereda la sesión) |
| SECRET | Nombres que contienen `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `CREDENTIAL`, `PRIVATE_KEY`, `API_KEY` o `ACCESS_KEY` (sin distinguir mayúsculas) |
| IRRELEVANT | El resto: se hereda |

- `clasificar_entorno(entorno)` devuelve nombres por clase.
- `comprobar_politica_de_entorno(entorno)` lanza `FalloDePreflight` con los nombres prohibidos. Es lo primero que hace `etapa_preflight`, que fija `ENVIRONMENT_POLICY` con nombres, nunca valores; IRRELEVANT solo como recuento.
- `entorno_de_sujeto` elimina las CANONICALIZED y las SECRET antes de aplicar los extras.

**D3 — PostgreSQL de QA fijado (R4).** Fichero `qa/postgres_qa.json`, esquema 1:
- `postgres: "16.2"`;
- `rueda {fichero, url, sha256}`;
- `btree_gist {paquete, version, fichero, url, sha256}`.

Funciones:
- `descargar_verificado(url, sha256, destino, timeout_s)`: solo `https`, redirecciones solo a `https`, sha256 obligatorio. Si el sha256 no coincide, `FalloDeCertificacion` y no queda ningún fichero parcial.
- `extraer_postgres_de_la_rueda(rueda, destino)`: solo `pgserver/pginstall/**` y `pgserver.libs/**`, con los modos de la rueda, sin rutas fuera de `destino`. Verifica cada fichero extraído contra el `RECORD` de la rueda.
- `ficheros_de_btree_gist(deb)`: lee el `ar` y el `data.tar.xz` con la biblioteca estándar. Devuelve `btree_gist.so` y `btree_gist.control` / `btree_gist--*.sql`.
- `aprovisionar_postgres_qa(ctx)`:
  - directorio `<HOME de certificación>/postgres-qa/<sha256(postgres_qa.json)[:16]>/`, con descargas en `descargas/`, verificadas en cada corrida;
  - instalación inmutable: se marca `.completo` al final. Si ya existe completa, se reverifica (RECORD + sha256 de los ficheros de `btree_gist`) y se reutiliza;
  - una instalación incompleta se sustituye; si está alterada, `EntornoInvalido`;
  - fija `ctx.datos["postgres_qa"]` (`bin`, ids, sha256), `herramientas["psql"]` y `POSTGRES_QA_SOURCE` en el manifiesto;
  - el nombre `postgres-qa` queda reservado: `espacios_previos` no lo cuenta como espacio de corrida.

`etapa_postgres`:
1. aprovisiona;
2. ejecuta `status` / `start` con `KONTROL_PGBIN`, `KONTROL_PGDATA=/tmp/kontrol-pgdata-045` y `KONTROL_PG_SIN_COMPILAR=1`;
3. `ejecutable_del_postmaster(pgdata)` (PID de `postmaster.pid` → `/proc/PID/exe`) debe estar dentro del `bin` fijado. Si no, `EntornoInvalido` («detén el PostgreSQL de QA y relanza»);
4. `SHOW server_version` debe ser igual a la versión fijada;
5. sigue como hasta ahora.

`qa/pg-provision.sh`:
- `PGBIN="${KONTROL_PGBIN:-<ruta actual del .venv>}"`: el desarrollo no canónico no cambia, y con `KONTROL_PGBIN` no hay vuelta al `.venv`;
- con `KONTROL_PG_SIN_COMPILAR=1`, si falta `btree_gist.control`, termina con error antes de descargar o compilar nada.

El preflight retira `PG_BIN` y la exigencia del `psql` del `.venv`, y añade `qa/postgres_qa.json` a los requeridos.

**D4 — Árbol certificado (R5).** `POLITICA_DEL_ARBOL_VERSION = 1`. Exclusiones (pathspec de Git):
- `specs/**/evidence/**` y `specs/**/*.md`: documentación y evidencia que se escriben al cerrar y que ninguna etapa lee;
- `docs/roadmap/**`;
- `requerimientos/`: material de la dueña; queda tal como está en HEAD, nunca con cambios locales;
- `**/.env`, `**/.env.*`, `**/*.pem`, `**/*.key`, `**/id_rsa*`, `**/id_ed25519*`, `**/*.p12`, `**/*.pfx`.

`arbol_certificado(git, raiz, trabajo, entorno)`:
- usa `GIT_INDEX_FILE` y `GIT_OBJECT_DIRECTORY` en `trabajo`, con `GIT_ALTERNATE_OBJECT_DIRECTORIES` apuntando a los objetos del repositorio;
- neutraliza la configuración del anfitrión para que el árbol sea el mismo en cualquier máquina: `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null` y `-c core.autocrlf=false -c core.filemode=true -c core.symlinks=true` en cada orden git;
- secuencia: `read-tree HEAD` → `add -A -- . <exclusiones>` → `write-tree`;
- devuelve el árbol y los paths con cambios que quedaron fuera (diff contra el árbol sin exclusiones);
- nunca toca el índice ni los objetos del repositorio.

El preflight fija `CERTIFICATION_INPUT_TREE_HASH` y `ARBOL_POLITICA` (versión, exclusiones, excluidos con cambios).

`hash_de_entrada` v2 (`CANONICAL_RUN_INPUT_HASH_VERSION = 2`):
- semilla `{version, head, arbol, politica_del_arbol, digests, locks, plataforma, referencia, postgres_qa}`;
- sin árbol, `CANONICAL_RUN_INPUT_HASH = None`.

`etapa_manifiesto`:
- recalcula el árbol; si difiere, `FalloDeCertificacion` («el árbol certificado cambió durante la corrida»);
- fija `TREE_HASH_BOUND_TO_RUN_INPUT = 1` solo con hash v2 calculado.

**Procedencia remota.** En el anfitrión, la misma función produce `CERTIFICATION_INPUT_TREE_HASH`. `--solo-preflight` lo da
sin certificar en origen y en destino, y la igualdad es `SOURCE_WORKTREE_CONTENT_MATCH`.

## 4. Plan y tareas

| Tarea | Contenido | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| TP-A | Pruebas CRP (rojo) para G1–G4 y la política de entorno | DEEPSEEK | v4-pro | no | sí | 2 | `resources/backend/tests/test_certificacion_portabilidad.py` | rojo contra el árbol actual por las causas correctas | rojo atribuido |
| TP-1 | D1: perfil E2E canónico | DEEPSEEK | v4-pro | no | sí | 2 | `qa/certificacion_release.py` | CRP G1/G2 | verdes |
| TP-2 | D2: política de entorno | DEEPSEEK | v4-pro | no | sí | 2 | `qa/certificacion_release.py` | CRP entorno | verdes |
| TP-3a | D3: fuente fijada y funciones de descarga y extracción | DEEPSEEK | v4-pro | no | sí | 2 | `qa/postgres_qa.json`, `qa/certificacion_release.py` | CRP G3 | verdes |
| TP-3b | D3: `etapa_postgres`, preflight, `pg-provision.sh` | DEEPSEEK | v4-pro | no | sí | 2 | `qa/certificacion_release.py`, `qa/pg-provision.sh` | CRP G3 + CRE-26 | verdes |
| TP-4 | D4: árbol certificado y hash v2 | DEEPSEEK | v4-pro | no | sí | 2 | `qa/certificacion_release.py` | CRP G4 | verdes |
| TP-5 | Ajuste de CRE-10, CRE-26 y CRE-32 al contrato nuevo | DEEPSEEK | v4-flash | no | sí | 2 | `resources/backend/tests/test_certificacion_release.py` | CRE | verdes |
| TP-6 | Documentación de uso | DEEPSEEK | v4-flash | no | sí | 2 | `README.md`, `.claude/CLAUDE.md` | revisión | revisada |
| TP-7 | Evidencia, mutaciones, diagnósticos, requisitos del anfitrión | CLAUDE | n-a | no | n-a | — | `evidence/…` | — | evidencia completa |

## 5. Constitution gate, analyze y trazabilidad

- P2: autorizado por el encargo.
- Producto, dependencias de producción, Dockerfile, esquema y migraciones: 0.
- PostgreSQL de QA sigue siendo solo de QA, en localhost y fuera de producción.

| Requisito | Tareas | Pruebas |
|---|---|---|
| R1 | TP-1 | CRP G1 |
| R2 | TP-1, TP-2 | CRP G2 |
| R3 | TP-2 | CRP entorno |
| R4 | TP-3a, TP-3b | CRP G3, CRE-26, diagnóstico sin `.venv` |
| R5 | TP-4 | CRP G4, CRE-10, CRE-32 |
| R6 | TP-6 | revisión |

Trazabilidad 6/6. BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0; MATERIAL OQ = 0; UNKNOWN = 0.

## 6. Material gate

| Indicador | Valor |
|---|---|
| ROOT_CAUSE_PROVEN (G1–G4) | 1 |
| PORTABLE_POSTGRES_ARCHITECTURE_PROVEN | 1 (prueba manual de punta a punta, sin `.venv` ni compilador) |
| E2E profile reduced | 0 |
| Thresholds changed | 0 |
| PRODUCT · DEPENDENCY · DOCKER change | 0 · 0 · 0 |
| OWNER_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**Implementación autorizada.**

## 7. Estado (2026-10-25)
**PORTABILITY_DELTA = CLOSED / CONVERGED** (técnicamente). SPEC054 en conjunto sigue **IMPLEMENTED — BLOCKED BY
INFRASTRUCTURE**: falta la corrida oficial con RC 0 en un anfitrión dedicado. No se hace commit hasta entonces.

| Brecha | Estado | Prueba |
|---|---|---|
| G1 HOST-DEPENDENT-E2E-WORKERS | **CLOSED** | `orden_de_e2e` fija `--workers=6`; `verificar_perfil_e2e` exige «using 6 workers» en `suite.log`; con 6 CPU la E2E informó 6 workers (diagnóstico) |
| G2 CI-ENV-ENABLES-E2E-RETRIES | **CLOSED** | `--retries=0` en la ruta canónica; `CI` canonicalizada (no llega a los sujetos); con `CI=true`, 0 reintentos (diagnóstico) |
| Política de entorno v1 | **IMPLEMENTED** | preflight real: RC 4, 0 prohibidas, `CLAUDE_CODE_MESSAGING_TOKEN` como SECRET (eliminada de los sujetos; solo el nombre) |
| G3 PG-QA-FROM-PREEXISTING-VENV | **CLOSED** | `qa/postgres_qa.json` (rueda + `.deb`, sha256 contrastados con PyPI y PGDG); integración en un árbol limpio sin `.venv` ni compilador; procedencia del postmaster; suite PostgreSQL completa sobre los binarios fijados 3174/0/26 |
| G4 INPUT-HASH-EXCLUDES-WORKTREE | **CLOSED** | `CERTIFICATION_INPUT_TREE_HASH` ligado a `CANONICAL_RUN_INPUT_HASH` v2 y recalculado al cierre; configuración git del anfitrión neutralizada (CRP-11/12/13); preflight real con el árbol `a97220d6…` y `TREE_HASH_BOUND_TO_RUN_INPUT = 1` |

Medidas:
- **Pruebas:** CRE 78 + CRP 55 + CRQ 32 + O12 + AIC → 213 passed. ruff global 0; mypy del módulo 0; `bash -n` del script correcto.
- **Rojo previo:** `evidence/certification-host-portability/red-*.txt`; G1–G4 por la API ausente y el script volviendo al `.venv` señuelo.
- **Mutaciones:** 28 de 28 eliminadas, 0 supervivientes, restauración verificada por sha256 (`mutations.json`).
- **Base de datos (diagnóstico en la estación, árbol final):** SQLite 2130/0/1070; PostgreSQL sobre los binarios fijados 3174/0/26. Una primera corrida dio 3164/1/26: AIC-01 detectó literales `.venv` en CRQ, que se corrigieron con TP-5b.
- **E2E (diagnóstico):** con 12 CPU, 284 passed y pico de memoria de 7557 MB; con 6 CPU y `CI=true`, 6 workers y 0 reintentos, pero 3 cargas con análisis vencen su espera. De ahí `CPU_MIN = 12` lógicas, medido y ya no «exactas».
- **OpenAPI y seguridad:** sin cambios de producto ni de dependencias; se miden en la corrida oficial.
- **Orquestación:** 29 llamadas a DeepSeek; detalle en `orchestration.md`.

Requisitos re-derivados y formas viables de anfitrión: `evidence/canonicalize-certification-environment/certification-host-requirements.md` (v2).
- **OD-CERT-30 (dueña, 2026-10-25):** la VM local no cumple los requisitos (estación de 15 GB y 12 CPU compartidas) y no hay proveedor cloud conectado. Se confirma en develop el estado **IMPLEMENTED — CERTIFICATION PENDING** (no CLOSED) y se abre SPEC046 S3. La corrida oficial con RC 0 en un anfitrión dedicado cerrará SPEC054.
