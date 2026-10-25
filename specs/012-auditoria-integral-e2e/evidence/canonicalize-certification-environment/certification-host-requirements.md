# Anfitrión dedicado de certificación: descubrimiento y requisitos (v2, 2026-10-25, tras CERTIFICATION-HOST-PORTABILITY)

Decisiones aplicadas:
- **OD-CERT-27 = A**: la estación de desarrollo es multiproyecto; la certificación oficial exige un entorno dedicado. La OPTION B no está autorizada.
- **OD-CERT-28 = 28-B**: la delta de portabilidad (G1–G4) se cerró antes de aprovisionar el anfitrión. Ver `../certification-host-portability/`.

El perfil E2E, la concurrencia y los umbrales no cambian.

## 1. Descubrimiento (solo lectura; repetido tras la delta)

| Candidato | Medido | Resultado |
|---|---|---|
| Runners self-hosted del repositorio | `total_count = 0` (también tras la delta) | no existe |
| Runners de organización | HTTP 404 | no existe |
| Runners alojados de GitHub (`ubuntu-latest`) | usados solo para construir y subir imágenes | **sigue sin ser apto**, aunque G1 y G2 ya no lo bloquean (`CI=true` ya no cambia el perfil y los workers son fijos). Lo que queda: el SO es Ubuntu y la etapa 30 exige paquetes exactos de Debian 13; en un contenedor `debian:trixie` no hay systemd y `timedatectl` (comprobación de NTP del preflight) falla; la capacidad de un runner estándar no se ha verificado en esta sesión y está por debajo de los mínimos medidos; además, un workflow nuevo y subir el árbol no están autorizados |
| Hosts SSH, CLIs de nube, virtualización local | ninguno | ninguno |

`DEDICATED_CERTIFICATION_ENVIRONMENT_FOUND = 0` → `CERTIFICATION_INFRASTRUCTURE_REQUIRED = 1`.

**Formas viables, a decidir y aprovisionar por la dueña.** No se ha creado nada.
1. **VM o máquina Debian 13 dedicada**, operada por SSH. Recomendada: es la forma más simple.
2. La misma máquina registrada como **runner self-hosted** de GitHub. Requiere autorizar un workflow y un token de registro del runner. Al ser un repositorio privado, el runner solo ejecuta trabajos de este repositorio.

En los dos casos el coste depende del proveedor; aquí no se estima ningún precio.

## 2. Carga medida (MEASURED)

Referencia: Ryzen 5 7430U, 12 CPU lógicas, 15 390 MB de RAM y Debian 13, compartida con otras cargas.

| Medida | Valor | Fuente |
|---|---|---|
| Orden canónica completa | 3393 s (incluye 660 s de espera de salud); backend 2290 s; E2E 365 s | `cert_20261024T174958Z_ba4752` |
| Perfil E2E canónico | **Chromium**: 280 pruebas, más 4 de licencia, también en Chrome. Firefox y WebKit no forman parte de la E2E canónica | `qa/e2e_corrida.py`, `suite.log` |
| Workers / reintentos | 6 / 0, fijos en la orden (`--workers=6 --retries=0`) | delta G1/G2 |
| Huella E2E de KONTROL, 12 CPU | pico de **7557 MB** Pss+SwapPss (clamscan 3705, Node 2230, Chromium 1146, Python 275); mediana 3175; p95 5762 | `e2e-memory-footprint-diagnostic.json` |
| Huella E2E de KONTROL, 6 CPU, `CI=true` | pico de 8020 MB; 6 workers; 0 reintentos; **277 passed, 3 failed, 4 did not run** (los 3 fallos son cargas de documentos que esperan el análisis ClamAV ~30 s; los 4 son la cadena de licencias, que depende de ellos) | `../certification-host-portability/e2e-6cpu-ci-diagnostic.md` |
| PostgreSQL de QA fijado | 16.2 (`pgserver` 0.1.4 + `btree_gist` 1.7 de PGDG); instalación y descargas ≈ 62 MB | `g3-integration-clean-tree.md` |
| Navegadores necesarios | chromium, chromium-headless-shell y ffmpeg de Playwright 1.62.1: 656 MB | `du` |
| Dependencias | repositorio 319 MB; `node_modules` 295 MB; ClamAV 190 MB; cachés uv 1,7 GB y npm 523 MB. El `.venv` del backend **ya no** se necesita para certificar | `du` |
| Evidencia por corrida | < 2 MB (`qa/certificaciones`) + ≈ 6 MB (`qa/e2e-runs`) + ≈ 22 MB (`qa/backend-runs`) | `du` |

NOT MEASURED: el pico del espacio de trabajo V6R+V6C (se elimina al terminar) y el pico por proceso del backend.

## 3. Requisitos derivados

| Requisito | Valor | Tipo y fundamento |
|---|---|---|
| CERTIFICATION_HOST_RAM_MIN | **16 GB** | DERIVED, sin cambios tras la delta (la huella no cambia: mismos 6 workers). Pico E2E 7,6–8,0 GB + PostgreSQL 0,6 + tmpfs 0,4 + sistema ~1 GB ≈ 9,6–10 GB; peor caso con 6 análisis simultáneos ≈ 11,9 GB; margen ≥ 25 % → 16 GB |
| CERTIFICATION_HOST_RAM_RECOMMENDED | **24 GB** | RECOMMENDED: el doble del peor caso |
| CERTIFICATION_HOST_SWAP_POLICY | swap habilitada (≥ 4 GiB), swappiness por defecto, **prohibido desactivarla** | sin swap, la medida de validez se vuelve trivial |
| CERTIFICATION_HOST_CPU_MIN (mínimo funcional) | **12 CPU lógicas** (ya no «exactas»: más CPU no cambia la concurrencia, workers fijos en 6) | MEASURED: con 12, 284 passed; con 6 (y `CI=true`), 3 cargas con análisis vencen su espera. Entre 7 y 11 no está medido, así que no se baja el mínimo |
| CERTIFICATION_HOST_CPU_RECOMMENDED (rendimiento) | 12 CPU lógicas x86-64-v3 o superior | MEASURED: referencia de ~57 min con Ryzen 5 7430U (6c/12t); por encima no hay medición, así que no se fija una cifra mayor |
| CERTIFICATION_HOST_DISK_MIN | **25 GB libres** (se conserva la base) | DERIVED: la delta solo reduce la huella ≈ 0,9 GB (sin `.venv`; navegadores solo Chromium 0,66 GB frente a 1,2 GB), un cambio no material; la base de v1 (dependencias + cachés + espacio V6R/V6C + evidencia + sistema, con margen × 2) se mantiene |
| CERTIFICATION_HOST_DISK_RECOMMENDED | 50 GB SSD | RECOMMENDED: historial de evidencia y actualizaciones |
| CERTIFICATION_HOST_OS_REQUIREMENT | **Debian 13 (trixie)** con `trixie` y `trixie-security` en APT; systemd (`timedatectl`) | MEASURED: la etapa 30 hace `apt-get download` de versiones exactas; el preflight usa `timedatectl` |
| CERTIFICATION_HOST_ARCH | **amd64** | MEASURED: digest `sha256:8fb4cfa1…` (linux/amd64) |
| CERTIFICATION_HOST_NETWORK_REQUIREMENT | salida HTTPS a Docker Hub (registro, autenticación y CDN), `deb.debian.org`/`security.debian.org`, PyPI (`pypi.org`, `files.pythonhosted.org`), `apt-archive.postgresql.org`, `api.osv.dev`, y npm y la CDN de Playwright solo al aprovisionar; sin entrada | MEASURED |
| CERTIFICATION_HOST_TIME_SYNC_REQUIREMENT | NTP sincronizado; sin suspensión (en una VM headless, el inhibidor OD-CERT-26 es NOT APPLICABLE) | MEASURED |
| CERTIFICATION_HOST_POSTGRES_REQUIREMENT | ninguno previo: la orden instala y verifica PostgreSQL 16.2 desde `qa/postgres_qa.json` en el HOME de certificación; no hace falta `.venv`, compilador ni PATH; el puerto 55432 debe estar libre o servido por ese mismo binario | MEASURED (G3) |
| CERTIFICATION_HOST_PLAYWRIGHT_REQUIREMENT | Node 24 (medido `v24.21.0`); `npm ci` en `resources/frontend`; `npx playwright install --with-deps chromium` (1.62.1); `CI` puede estar definida, porque ya no cambia el perfil | MEASURED |
| CERTIFICATION_HOST_CLAMAV_REQUIREMENT | `python3 qa/clamav_qa.py provisionar` (ClamAV 1.4 sin privilegios, ≈ 190 MB) y `eval "$(python3 qa/clamav_qa.py entorno)"` antes de la orden | MEASURED |
| Herramientas | `git`, `apt-get`, `dpkg-deb`, `node`, `uv`, `bash`, `timedatectl`, `python3` del sistema | preflight |
| Variables heredadas | ninguna FORBIDDEN de la política v1 (`PYTEST_*`, `PLAYWRIGHT_*` salvo `PLAYWRIGHT_BROWSERS_PATH`, `NODE_OPTIONS`, `KONTROL_*` salvo las tres permitidas, `UV_*`, `PIP_*`, `PG*`, `GIT_CONFIG*`, `GIT_DIR`…) | MEASURED (RC 70 si aparece alguna) |
| Aislamiento | un solo inquilino durante la corrida; puertos 8000, 5173, 8010 y 55432 libres; usuario sin sudo para la orden | DERIVED de OD-CERT-27 |
| Duración esperada | ~45–60 min (referencia: 57 min con 11 min de espera de salud) | MEASURED |

## 4. Procedencia de la certificación previa al commit

Implementada en la orden canónica (G4):
- `CERTIFICATION_INPUT_TREE_HASH` es el árbol Git del árbol de trabajo, calculado con un índice y unos objetos temporales y con la política de exclusiones v1;
- la configuración git del anfitrión está neutralizada;
- el árbol entra en `CANONICAL_RUN_INPUT_HASH` v2 y se recalcula al cierre.

Traspaso:
1. **En origen:** `python3 qa/certificar-release.py --solo-preflight` → RC 4 y el árbol en el manifiesto (medido: `a97220d6…`, RC 4, `TREE_HASH_BOUND_TO_RUN_INPUT = 1`).
2. **Transporte:**
   - un `git bundle` de `3300183`, o un clon con acceso de lectura;
   - un parche binario con sha256 de los ficheros del ciclo, sin el `.docx` SNAT, sin `.env` y sin secretos;
   - se borra al terminar.
3. **En destino:** aplicar, ejecutar `--solo-preflight` y comparar el árbol con el de origen (SOURCE_WORKTREE_CONTENT_MATCH). Después, una sola `python3 qa/certificar-release.py`.
