# SPEC 052 · Delta — PRODUCTION-IMAGE-WITHOUT-LIBMAGIC

- **Dueña:** Spec 052. Apoyo: 001 (matriz de dependencias) y 046 (consumidora, §19 MIME por contenido).
- **Fecha:** 2026-10-20, rama `develop`, HEAD de partida `226e1c3`.
- **Ruta B:** no hay evidencia Docker de OBS-09.
- **DOCKER_AVAILABLE = 0:** no hay docker, podman ni buildah, y no se instalan.
- **Decisiones:** OD-CERT-01, 02 y 03 ratificadas.
- **Evidencia:** `evidence/production-image-libmagic/`.

## 1. Specify
La imagen del backend debe poder detectar el MIME por contenido: `python-magic` fijado en `requirements.txt` y la
biblioteca nativa con su base de firmas en la etapa que se despliega. No cambian el producto, `detect_mime`, su
fail-closed ni el lock.

## 2. Clarify — reproducción y arquitectura (`pre-fix-reproduction.txt`)

**Reproducción previa:**
- PYTHON_MAGIC_DECLARED = 0.
- SYSTEM_LIBMAGIC_DECLARED = 0.
- V1 (lo que construye la imagen): un PDF y un texto se detectan como `application/octet-stream`.
- Una carga real de PDF (`test_subida_idempotente`) da 422.

**Grafo de etapas de `Dockerfile.backend`:**

| Etapa | FROM | Padre | Paquetes de sistema | Instalación Python | CMD |
|---|---|---|---|---|---|
| `base` | `python:3.13-slim` | — | `curl` (apt, `--no-install-recommends`, limpieza de listas) | `pip install --no-cache-dir -r /tmp/requirements.txt` | `uvicorn app.main:app …` |
| `dev` | `base` | `base` | — | `pip install --no-cache-dir pytest httpx ruff mypy` | `uvicorn … --reload` |

- **FINAL_STAGE = EFFECTIVE_DEPLOYED_STAGE = `dev`.** Los workflows y `qa/compose_qa.py` no pasan `target`. Esto es la
  deuda PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE, que no se corrige aquí.
- `dev` hereda de `base`: lo que se instale en `base` llega al runtime efectivo.

**Base del sistema:** el registro público, con token anónimo y solo lectura, da el mismo digest a `python:3.13-slim` y a
`python:3.13-slim-trixie` (`sha256:70729b46c69b…`, frente a `…a1165e272e57…` de bookworm).
- BASE_OS = **Debian 13 (trixie)**.
- PACKAGE_MANAGER = apt.

**Paquete nativo** (medido en un host trixie desde `trixie/main amd64`):
- LIBMAGIC_SYSTEM_PACKAGE = **`libmagic1t64`** (1:5.46-5), que provee `/usr/lib/x86_64-linux-gnu/libmagic.so.1`.
- En trixie, `libmagic1` es solo un nombre virtual (`Provides: libmagic1`), resultado de la transición de `time_t`.
- LIBMAGIC_DATABASE_PACKAGE = **`libmagic-mgc`** (`/usr/lib/file/magic.mgc`), dependencia obligatoria
  (`Depends: libmagic-mgc (= 1:5.46-5)`). Por tanto, LIBMAGIC_TRANSITIVE_PACKAGE = `libmagic-mgc`, y apt la instala aunque
  se use `--no-install-recommends`.

**python-magic:**
- Última versión publicada en PyPI: **0.4.27** (2022-06-07).
- Sin vulnerabilidades en PyPI ni en OSV; no está retirada.
- Es un envoltorio `ctypes` en Python puro.
- PYTHON313_COMPATIBLE = 1, medido en V2: `pip check`, importación, detección real, SQLite 1885/0/1056, PostgreSQL
  2915/0/26 y E2E 284/0/0.

**Lock:**
- REQUIREMENTS_LOCK_CONSUMED_BY_PRODUCTION = 0.
- PYTHON_MAGIC_PRESENT_IN_REQUIREMENTS_LOCK = 0.
- LOCK_DRIFT_DELTA_CREATED_BY_THIS_CHANGE = +1: `python-magic` queda en `requirements.txt` y no en el lock.
- Se registra y no se reconcilia (LOCK-SIN-REPORTLAB-MAGIC y PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES).

## 3. Plan · 4. Constitution gate
| Tarea | Cambio |
|---|---|
| T1 | `requirements.txt`: añadir `python-magic==0.4.27` |
| T2 | `Dockerfile.backend`: `libmagic1t64` en la orden apt existente de la etapa `base`, junto a `curl` |
| T3 | prueba nueva `tests/test_imagen_backend_mime.py` |

La prueba T3 comprueba tres cosas:
- **Estática, que entiende las etapas:** cadena de herencia desde la etapa final; apt e instalación de requirements dentro
  de esa cadena.
- **Declaración:** `python-magic` declarado y fijado, igual a la versión instalada en el entorno certificado.
- **Runtime real, sin mocks:** biblioteca nativa cargada, base de firmas operativa, y `detect_mime` de contenido PDF y de
  texto sin extensión.

**Gate:**
- Sin cambio de producto ✔.
- Sin «clam» en el Dockerfile (invariante de `test_clam_14_15` y `test_o09_24`) ✔.
- Sin tocar la etapa `dev`, CI, compose ni el lock ✔.

## 5. Material gate
| Indicador | Valor |
|---|---|
| ROOT_CAUSE_PROVEN · OWNER_SPEC_CONFIRMED | 1 · 1 (052) |
| BASE_OS_CONFIRMED · LIBMAGIC_SYSTEM_PACKAGE_CONFIRMED · LIBMAGIC_SIGNATURE_DATABASE_AVAILABLE | 1 · 1 · 1 |
| PYTHON_MAGIC_VERSION_CONFIRMED · PYTHON313_COMPATIBILITY_CONFIRMED | 1 · 1 |
| EFFECTIVE_STAGE_RECEIVES_LIBMAGIC | 1 (`dev` hereda de `base`) |
| PRODUCT, SCHEMA, MIGRATION, LOCK_CHANGE_REQUIRED_FOR_THIS_FIX | 0 · 0 · 0 · 0 |
| OWNER_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**Implementación autorizada.** Estado máximo posible: IMPLEMENTED — IMAGE RUNTIME CERTIFICATION BLOCKED BY ENVIRONMENT,
porque DOCKER_AVAILABLE = 0.

## 6. Implementación (`orchestration.md`)
- **T1:** `python-magic==0.4.27` en `requirements.txt`.
- **T2:** `curl libmagic1t64` en la orden apt de la etapa `base`, más un comentario.
- **T3:** `tests/test_imagen_backend_mime.py`, IMB-01 a IMB-07. Necesitó dos correcciones; en la segunda Claude demostró
  el falso PASS de H4.
- DeepSeek: 5 llamadas, $0,010394, 2 reintentos. Se aplicaron tal cual.

## 7. Pruebas y mutaciones (`directed-tests.txt`, `red-against-head.txt`, `mutations.json`)
- **Dirigidas:** 7/7 en V0 y V1', con y sin PostgreSQL, en orden normal, en orden inverso y una a una. Los invariantes
  «sin clam» del Dockerfile siguen en verde.
- **Rojo contra `226e1c3`:** con V0 fallan IMB-01/02/03; con V1 fallan además IMB-04/05/06.
- **Mutaciones:** 12 significativas · 11 KILLED · 0 SURVIVED · 1 EQUIVALENT (M10: `import magic` ya exige la biblioteca
  nativa) · restauradas al 100 %.

## 8. Certificación (`certification.md`)
| Entorno | SQLite | PostgreSQL | E2E | Documentales |
|---|---|---|---|---|
| V0 | 1892/0/1056 ×2 | 2922/0/26 | 284/0/0 | — |
| V1' | 1892/0/1056 | 2922/0/26 | 284/0/0 | 111/0/27 · 129/0/9 |

- OpenAPI sin cambio.
- Prerrequisito MIME de OBS-09: F01, F02, F03 y F04 superan la fase MIME.
- **Imagen: NOT EXECUTED (sin Docker).**

## 9. Convergencia
**PRODUCTION-IMAGE-WITHOUT-LIBMAGIC = IMPLEMENTED — IMAGE RUNTIME CERTIFICATION BLOCKED BY ENVIRONMENT.**

- Todo lo verificable sin Docker está demostrado.
- Falta medir dentro de la imagen construida:
  - `import magic` y la carga de `libmagic.so.1`;
  - `magic.mgc`;
  - `detect_mime` de un PDF;
  - una carga real.
- Esa evidencia puede llegar junto con la evidencia Docker externa de OBS-09.
- RELEASE_DEPLOYMENT_PARITY_CERTIFIED = 0.
- Lock sin cambio: LOCK_DRIFT_DELTA = +1 (`python-magic` no está en el lock), registrado en LOCK-SIN-REPORTLAB-MAGIC.
