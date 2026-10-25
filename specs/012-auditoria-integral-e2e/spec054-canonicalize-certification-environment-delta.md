# SPEC 054 · Delta — CANONICALIZE-CERTIFICATION-ENVIRONMENT

| Campo | Valor |
|---|---|
| Deuda | **CANONICALIZE-CERTIFICATION-ENVIRONMENT** (dueña 054, apoyo 052) |
| Decisiones | OD-CERT-19 (V6R + V6C canónico; V0 = HISTORICAL_NON_BLOCKING_CONTROL) · OD-CERT-20 (canonicalización ≠ imagen exacta) · OD-CERT-21 (S3: decisión antes de Gobierno READY; no se absorbe) · OD-CERT-22 (ruff/mypy por ámbito y global) · OD-CERT-23 (SNAT/2026/00093 diferida, antes del 2027-04-19) · OD-CERT-24 (una orden canónica) · OD-CERT-25 (falla cerrado) · OD-ORCH-01 |
| Spec cruzada | Spec 052: V6R/V6C, `requirements.lock` / `requirements-test.lock`, `certified-deployment-base.json` |
| HEAD de entrada | `3300183` |
| Ruta | C (sin Docker ni evidencia externa de OBS-09) |
| Evidencia | `evidence/canonicalize-certification-environment/` |

## 1. Specify
- **Objetivo:** una única orden, en el repositorio, que reconstruya V6R y V6C desde el digest y los locks certificados, ejecute toda la certificación de release, dé el veredicto con un RC fiable y deje un manifiesto de evidencia saneado. Sin pasos manuales ni conocimiento de sesión.
- **V0:** no se ejecuta por defecto. Hay un modo opcional explícito de control histórico que nunca cambia el veredicto.
- **Fuera de alcance:**
  - `app/**`, los manifiestos, los locks, `Dockerfile.backend`, el esquema y las migraciones;
  - la imagen real (Docker: EXACT_RUNTIME_IMAGE_CONTENTS_CERTIFIED = 0, RELEASE_DEPLOYMENT_PARITY_CERTIFIED = 0);
  - S3, SNAT y Gobierno.

## 2. Clarify (medido; `certification-paths-before.json`)
- **16 puntos de entrada y 10 pasos manuales:**
  - V6R y V6C se construyen con herramientas que no están en el repositorio;
  - `mkdb ktest` hay que hacerlo a mano;
  - `pip check` / freeze, pip-audit, OpenAPI, residuos, la condición de salud, el muestreo de procedencia y el humo de V6R se ejecutan a mano.
- **Fallos de entorno ya ocurridos que la orden tiene que impedir:**
  - una PostgreSQL completa con `ktest` inexistente;
  - una descarga OCI colgada 10 h y errores 401 (token caducado y Bearer reenviado al CDN);
  - E2E sin condición de salud;
  - un criterio de validez con la swap residual en vez del incremento.
- **Reproducibilidad por piezas:** V6R se reconstruyó dos veces con el mismo freeze. **ROOT_CAUSE_PROVEN = 1**.

## 3. Diseño — `qa/certificar-release.py` (entrada) + `qa/certificacion_release.py` (módulo)
Sigue el patrón de `qa/e2e-run.py` / `qa/e2e_corrida.py`.
- **Orquestador:** usa solo la biblioteca estándar y no importa código del producto, así que puede correr con el `python3` del sistema. Todo proceso de certificación corre en V6R o en V6C, con rutas absolutas del espacio de la corrida y nunca con un Python del PATH.
- **Espacio de trabajo por corrida:** `${KONTROL_QA_CERT_HOME:-~/.cache/kontrol-qa/certificacion}/<run_id>/`, con una marca de propiedad.
- **Evidencia:** `qa/certificaciones/<run_id>/manifest.json`, fuera de Git (`.gitignore`).
- **Etapas** (cada una registra su resultado en el manifiesto; la primera que falla corta las siguientes y fija el RC):

| Etapa | Contenido | Falla si… |
|---|---|---|
| 00 PREFLIGHT | Raíz del repo; HEAD y estado de suciedad clasificado (`DIRTY_STATE`: ficheros no versionados declarados aparte, p. ej. material de la dueña); ficheros requeridos; digest de `certified-deployment-base.json` = digest del `FROM` de `Dockerfile.backend`; cabeceras canónicas y corte de los dos locks; herramientas (`apt-get`, `dpkg-deb`, `node`, `uv`); espacio en disco; NTP; espacios de corridas anteriores incompletos (se listan, **nunca** se reutilizan) | falta cualquier cosa, o los digests y cortes no casan |
| 10 VALIDEZ DEL ENTORNO | Condición de salud (load1 < 3; MemAvailable > 5 GB; páginas leídas de swap < 2000/min; 3 muestras de 60 s), con espera acotada (`--espera-salud-min`, por defecto 30); suspensiones (`boottime − monotonic`) | no se cumple dentro del límite → **INVALID_ENVIRONMENT** (RC 3, no es un fallo de producto) |
| 20 DEPENDENCIAS | Regenerar los dos locks con la orden canónica de uv en el espacio de la corrida y comparar con `cmp` | difieren |
| 30 V6R | Índice → manifiesto amd64 → config → capas, verificados por sha256 (los digests vienen de `certified-deployment-base.json`); whiteouts; libmagic y `ca-certificates` con versión fijada (sha del `.deb` de CA de la fuente); retirada de los `.crt` que el `.deb` ya no trae; bundle; lanzador `ld-linux`; `pip install --no-deps -r requirements.lock`. Timeout finito por petición, token renovado ante 401, redirección al CDN sin Bearer, reintento acotado **solo de descargas** (la integridad la da el sha256) | cualquier digest, versión o paso |
| 40 CERTIFICACIÓN V6R | CPython 3.13.16; `pip check`; freeze = lock; 0 herramientas importables; humo sin pytest (todos los módulos de `app` y `central_authority`, `create_app` + lifespan, OpenAPI, JWT, Ed25519, licencias, PDF, MIME) | cualquiera |
| 50 V6C | Copia de V6R + `pip install --no-deps -r requirements-test.lock` (como la etapa `dev`); `pip check`; freeze = lock de certificación | cualquiera |
| 60 SUBCONJUNTO | Todo paquete de V6R está en V6C con la misma versión | ≠ 1 |
| 70 POSTGRESQL QA | `pg-provision.sh start` (idempotente); `ktest` **existe** (si falta, `mkdb ktest`, que solo se lanza cuando la base no existe); el servidor es el de QA (`localhost:55432`); `btree_gist` disponible; 0 bases de corrida y 0 esquemas `t_` antes de empezar | no queda listo |
| 80 BACKEND | `suite_tiempos.py --motor sqlite --con-analizador` y `--motor postgres --con-analizador` con V6C (IN_PROCESS_CERTIFICATION_OVERLAY); se usan su RC y su manifiesto | rc ≠ 0, fallos > 0 o errores > 0 |
| 90 E2E | `e2e-run.py --con-analizador --python-de-producto <V6R>` con V6C y muestreo `/proc` en paralelo (backend, autoridad y ayudantes); validez posterior por el **incremento** (páginas escritas en swap y swap añadida) | fallos o pruebas sin ejecutar > 0; paridad alembic ≠ 1; `paridad_runtime` ≠ 1; herramientas del producto ≠ ∅; modo ≠ RUNTIME_SEPARADO; algún ayudante fuera de V6C o algún proceso de producto fuera de V6R; degradación durante la corrida → INVALID_ENVIRONMENT |
| 100 OPENAPI | Recuentos y huella de `paths` en V6R y V6C, iguales entre sí y a la referencia versionada `qa/certificacion_referencia.json` | deriva |
| 110 SEGURIDAD | pip-audit con versión fijada (instalado con `--target` en el espacio de la corrida), PyPI y OSV, sobre los dos locks | algún hallazgo o fallo de la herramienta |
| 120 RESIDUOS | 0 bases de corrida; 0 esquemas `t_`; puertos 8000/5173/8010 libres; ningún PID de la corrida vivo; espacio de la corrida eliminado (salvo `--conservar-espacio`) | queda algo |
| 130 MANIFIESTO | Campos §18 del encargo + `CANONICAL_RUN_INPUT_HASH` = sha256(HEAD, digests, sha256 de los dos locks, plataforma, referencia); `SUBJECT_COMMAND` y `SUBJECT_RC` de cada subproceso; saneado (`<repo>`, `<tmp>`, `<home>`) y sin entorno | — |
| 140 VEREDICTO | RC 0 solo si todo pasa; 1 si falla la certificación; 3 si el entorno no es válido; 70 si falla el preflight | — |

- **Opciones:**
  - `--incluir-v0-historico`: SQLite y E2E en V0, marcadas HISTORICAL_CONTROL, que **no** cambian el veredicto;
  - `--espera-salud-min N`;
  - `--conservar-espacio`;
  - `--solo-preflight`: diagnóstico, que no certifica.
- **Prohibido:**
  - reintentar etapas de certificación;
  - `skip`;
  - volver a V0 o al Python del PATH;
  - usar etiquetas flotantes;
  - tuberías que oculten el RC;
  - registrar el entorno.

## 4. Plan
| Tarea | Contenido | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | FILES |
|---|---|---|---|---|---|---|
| T1 | Esqueleto del módulo: etapas, manifiesto, RC, espacio por corrida con marca de propiedad, opciones, entrada `qa/certificar-release.py`, `.gitignore` de `qa/certificaciones/` | DEEPSEEK | v4-pro | no | sí | `qa/certificacion_release.py`, `qa/certificar-release.py`, `.gitignore` |
| T2 | Reconstrucción V6R/V6C (descargas con timeout, token, CDN, sha256, whiteouts, CA, libmagic, lanzador) y certificación V6R (humo como programa embebido) y V6C | DEEPSEEK | v4-pro | no | sí | `qa/certificacion_release.py` |
| T3 | Preflight, validez del entorno y preparación de PostgreSQL de QA | DEEPSEEK | v4-pro | no | sí (sin URLs con credenciales) | `qa/certificacion_release.py` |
| T4 | Backend, E2E con muestreo y paridades, OpenAPI con referencia versionada, pip-audit fijado y residuos | DEEPSEEK | v4-pro | no | sí | `qa/certificacion_release.py`, `qa/certificacion_referencia.json` |
| T5 | Pruebas unitarias y estructurales (CRE-01..), con dobles de red y de subprocesos | DEEPSEEK | v4-pro | no | sí | `resources/backend/tests/test_certificacion_release.py` |
| T6 | Documentación de uso (CLAUDE.md, «Comandos canónicos», y README, «Certificación») | DEEPSEEK | v4-flash | no | sí | `.claude/CLAUDE.md`, `README.md` |

RETRY_MAX: 2 por tarea; agotados, se divide la tarea.

## 5. Constitution gate y trazabilidad
- P2: autorizado por el encargo.
- Producto, dependencias, Dockerfile, esquema y migraciones: 0.

| Requisito | Tarea | Prueba |
|---|---|---|
| R1 Una sola entrada canónica; por defecto certifica V6; V0 nunca por defecto | T1 | CRE estructurales |
| R2 V6R por digest de la fuente certificada, sin etiqueta flotante, con descargas acotadas y verificadas | T2 | CRE con dobles de registro |
| R3 freeze = lock, `pip check`, 0 herramientas y humo en V6R | T2 | CRE + corrida canónica |
| R4 V6C = V6R + lock de certificación; igualdad del subconjunto obligatoria | T2 | CRE + corrida |
| R5 Preflight, entorno y PostgreSQL fallan cerrado (`ktest` incluido) | T3 | CRE + corrida |
| R6 Suites, E2E, paridades, OpenAPI, seguridad y residuos obligatorios; INVALID_ENVIRONMENT distinto de un fallo | T4 | CRE + corrida |
| R7 Manifiesto saneado con hash de entrada; RC fiable; ningún reintento de certificación | T1, T4 | CRE |
| R8 Espacio por corrida; nunca reutilizar uno incompleto; solo se limpia lo propio | T1 | CRE |
| R9 Uso documentado | T6 | revisión |

Trazabilidad: 9 de 9.

## 6. Material gate
| Indicador | Valor |
|---|---|
| ROOT_CAUSE_PROVEN | 1 |
| CERTIFICATION_ENTRY_POINTS_PRE · MANUAL_STEPS_PRE | 16 · 10 |
| CANONICAL_COMMAND_DESIGN_READY | 1 |
| Automatizables: V6R · V6C · PostgreSQL QA · E2E · seguridad · manifiesto | 1 · 1 · 1 · 1 · 1 · 1 |
| V0_DEFAULT_REQUIRED | 0 |
| PRODUCT · DEPENDENCY · DOCKER change required | 0 · 0 · 0 |
| OWNER_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**Implementación autorizada**, pero bloqueada por el entorno: el MCP de DeepSeek no conectó en esta sesión (ver §7).

## 7. Estado (2026-10-24)
**IMPLEMENTED — FINAL CERTIFICATION BLOCKED BY ENVIRONMENT — CERTIFICATION_HOST_CAPACITY_INSUFFICIENT = 1** (memoria del anfitrión durante la E2E, repetida en cuatro corridas). OD-CERT-27 = **A** (dueña, 2026-10-24): certificación oficial en un entorno dedicado; **BLOCKED_BY_INFRASTRUCTURE = 1** (no existe ninguno).

- **MCP:** recuperado (`/mcp → Reconnect` de la dueña; llamada real `MCP_OK`); `MCP_TIMEOUT=120000` en los ajustes locales de Claude Code (no versionado). Detalle: `evidence/…/mcp-recovery.md`.
- **T1–T6 implementadas por DeepSeek** y auditadas por Claude (registro completo en `evidence/…/orchestration.md`). Reintentos agotados en T1, T2 y T5a → las tareas se dividieron en microtareas (T2b, T2c, T4c, T5c–T5l); ninguna línea de producto ni de pruebas la escribió Claude.
- **Ficheros:** `qa/certificar-release.py`, `qa/certificacion_release.py` (15 etapas), `qa/certificacion_referencia.json`, `.gitignore` (`qa/certificaciones/`), `resources/backend/tests/test_certificacion_release.py` (77 pruebas CRE), `resources/backend/tests/test_suite_tiempos_qa.py` (O12-04 independiente de dónde viva el intérprete), `.claude/CLAUDE.md` y `README.md` (uso).
- **Pruebas:** 125 passed (CRE + O12 + AIC); ruff tocado y global limpio; mypy tocado 0 (mypy global `app`: 154 errores en 18 ficheros, preexistentes, `app/` sin cambios). Rojo contra `3300183`: `ModuleNotFoundError: certificacion_release` (única causa). Mutaciones M01–M24: **24/24 matadas**, original restaurado (`evidence/…/mutations.json`).
- **Medido con el módulo real:** V6R por digest (CPython 3.13.16, freeze = lock 38, humo PASS), V6C 49, subconjunto 38/38, locks regenerados idénticos, PostgreSQL QA listo, backend SQLite 2041/0/1070 y PostgreSQL 3085/0/26, E2E 284/0/0 con procedencia correcta (0 fuera de lugar), OpenAPI deriva 0, pip-audit 0/0.
- **Corridas canónicas** (`evidence/…/canonical-runs.md`): dos con RC 1 por pruebas preexistentes dependientes del entorno (O12-04 y AIC-01 frente a las pruebas nuevas), corregidas; dos con **RC 3 INVALID_ENVIRONMENT** por la validez posterior de la E2E (incremento de páginas escritas en swap 577 068 y 363 778, umbral 200 000) con la E2E en 284/0/0. La orden se comportó según el contrato en las cuatro (primer fallo manda, cierre siempre, residuos CLEAN, manifiesto saneado).
- **Quinta corrida (`cert_20261024T104651Z_370530`, RC 3):** backend SQLite 2042/0/1070 en verde, pero la suite midió un salto de reloj (713,7 s monotónicos frente a 4128,6 s de pared): suspensión del equipo durante la corrida. Detectó además que `ENVIRONMENT_VALIDITY` no reflejaba un INVALID_ENVIRONMENT fuera de las etapas 10 y 90 → corregido en T1b (CRE-41; 78 pruebas CRE; 126 passed; mutaciones 24/24).
- **Sexta corrida (`cert_20261024T140249Z_078af5`, RC 3), con inhibidor de suspensión propio (OD-CERT-26):** sin suspensión ni salto de reloj; 0–80 PASS (SQLite 2043/0/1070, PostgreSQL 3087/0/26); E2E 284/0/0 con procedencia correcta, pero +1 092 373 páginas escritas en swap y +2,95 GB de swap durante la E2E → MEMORY_PRESSURE. Tres de seis corridas invalidadas por memoria durante la E2E, siempre con Opera abierto (~2,8–3,7 GB).
- **Séptima corrida (`cert_20261024T161414Z_09f664`, RC 70 INTERRUPTED):** fin de sesión de GNOME y reinicio del anfitrión a los 207,7 s de la E2E (`journalctl -b -1`: `endSessionDialog` 17:14:56Z). 0–80 PASS (SQLite 2043/0/1070, PostgreSQL 3087/0/26). Sin residuos: el clúster QA en tmpfs desapareció con el reinicio.
- **Octava corrida (`cert_20261024T174958Z_ba4752`, RC 3), bajo la política multiproyecto:** inhibidor propio (PID 15860) activo y retirado por su PID (0 inhibidores KONTROL), suspensión 0 s, NTP sincronizado; 0–80 PASS (SQLite 2043/0/1070, PostgreSQL 3087/0/26); la suite E2E dio **284 passed**, pero la validez posterior midió +1 037 103 páginas escritas en swap y +2,6 GB de swap (umbrales 200 000 y 1 GiB) → INVALID_ENVIRONMENT; 100/110 NOT_RUN; 120 CLEAN. OTHER_WORKLOAD_PRESENT = 1 (aplicaciones de escritorio y una suite de otro proyecto), solo observadas.
- **Clasificación:** MEMORY_PRESSURE / SWAP_ACTIVITY repetida (corridas 3, 4, 6 y 8) con el producto en verde → **CERTIFICATION_HOST_CAPACITY_INSUFFICIENT = 1**. Los umbrales y el perfil E2E no se cambian. Decisión de la dueña (OD-CERT-27): **A** equipo de certificación dedicado o CI con el perfil E2E sin cambios (recomendada) · **B** delta del perfil de QA que reduzca la concurrencia de navegadores.
- **Desbloqueo (superado por la política multiproyecto):** ya no se exige cerrar aplicaciones ni otros proyectos; el desbloqueo depende de OD-CERT-27.
- **Historial (bloqueo MCP previo):** CONNECT_TIMEOUT al arrancar la sesión; causa SESSION_TRANSPORT_NOT_RECONNECTED; recuperado por la dueña.
- **OD-CERT-27 = A (dueña, 2026-10-24):** la estación es MULTI_PROJECT_ALLOWED; la certificación oficial exige DEDICATED_ENVIRONMENT_REQUIRED; la OPTION B no está autorizada. Descubrimiento de solo lectura: 0 runners self-hosted, sin hosts SSH, CLIs de nube ni virtualización; los runners alojados de GitHub no son aptos (Ubuntu frente a Debian 13, `CI=true` → `retries: 2`, y un workflow nuevo no está autorizado) → **CERTIFICATION_INFRASTRUCTURE_REQUIRED = 1**. Huella E2E medida (diagnóstico, no certifica): pico de 7557 MB Pss+SwapPss (clamscan 3705 MB). Requisitos derivados (16 GB mín. / 24 GB recomendados, 12 CPU lógicas exactas, Debian 13 amd64, swap habilitado), diseño de procedencia previa al commit y brechas G1–G4: `evidence/…/certification-host-requirements.md`.
- **OD-CERT-28 = 28-B (dueña, 2026-10-25):** la delta `spec054-certification-host-portability-delta.md` cerró G1–G4 (CLOSED / CONVERGED; 213 pruebas, 28/28 mutaciones, SQLite 2130/0/1070, PostgreSQL fijado 3174/0/26). Los requisitos del anfitrión se re-derivaron: RAM 16/24 GB, **12 CPU lógicas (mínimo funcional y recomendado medidos; ya no exactas)**, disco 25/50 GB, Debian 13 amd64, sin `.venv`. Estado: **IMPLEMENTED — BLOCKED BY INFRASTRUCTURE** hasta la corrida oficial con RC 0 en un anfitrión dedicado aprovisionado por la dueña.
- **OD-CERT-30 (dueña, 2026-10-25):** la VM local no cumple los requisitos (estación de 15 GB y 12 CPU compartidas) y no hay proveedor cloud conectado. Se confirma en develop el estado **IMPLEMENTED — CERTIFICATION PENDING** (no CLOSED) y se abre SPEC046 S3. La corrida oficial con RC 0 en un anfitrión dedicado cerrará SPEC054.
