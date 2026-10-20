# SPEC 052 · Delta — REPRODUCIBLE DEPLOYMENT DEPENDENCIES

| Campo | Valor |
|---|---|
| Deudas | PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES (dueña 052, apoyo 001) · LOCK-SIN-REPORTLAB-MAGIC (dueña 001/052) |
| Spec dueña | 052 (artefacto de release); apoyo 001 (ADR-014, `dependency-matrix.md`, `cve-review.md`) |
| Decisión aplicada | **OD-CERT-05**: `requirements.txt` es el manifiesto de dependencias directas y `requirements.lock` el conjunto completo, exacto y reproducible que instalan el despliegue y la certificación. Preservadas OD-CERT-01..04 |
| HEAD de entrada | `44e47b5` |
| Ruta | B (sin evidencia Docker externa de OBS-09) |
| Evidencia | `evidence/production-dependencies-reproducible/` |

## 1. Specify
- **Propiedad objetivo:** REPRODUCIBLE_DEPLOYMENT_DEPENDENCY_GRAPH. Un solo grafo completo, compatible, seguro y
  determinista que consumen tanto la imagen como la certificación.
- **Contrato:**
  - el lock contiene todas las directas con su pin exacto, más todas las transitivas;
  - se genera con un comando canónico declarado en su cabecera (Python 3.13, linux x86_64, corte de índice);
  - la imagen instala el lock sin volver a resolver (`--no-deps`) y verifica la coherencia del grafo (`pip check`).
- **Fuera de alcance:**
  - la separación runtime/dev/test (PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES);
  - la base flotante (PRODUCTION-BASE-IMAGE-FLOATING-TAG);
  - los hashes de artefacto;
  - las vulnerabilidades de los pines directos (BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES, nueva).

## 2. Clarify — descubrimiento, autoridad de versiones y número de raíces
**Lock histórico** (`lock-discovery.md`):
- formato `pip freeze` de 46 paquetes, sin cabecera ni hashes, sin comando de regeneración;
- intérprete **3.11** (contiene `greenlet`, que SQLAlchemy 2.0.36 solo exige por debajo de 3.13);
- **ningún consumidor**;
- no regenerado tras `reportlab` (`3cc89a7`) ni tras `python-magic` (`f7e7e44`).

**Imagen:** `pip install -r requirements.txt` resuelve las transitivas en cada build. Resolver hoy sin corte ya difiere
del grafo del 2026-10-20 (`certifi`).

**Autoridad de versiones** (`version-authority.tsv`, 50 paquetes): 26 HISTORICAL_LOCK_STALE, 1 MATRIX_STALE, 2
CVE_REVIEW_STALE, 0 VERSION_CONFLICT.
- **Starlette:**
  - FastAPI 0.141.1 exige `starlette>=0.46.0`;
  - `cve-review.md` fija un **suelo** (≥ 1.3.1, «versiones ≥ las corregidas»);
  - `dependency-matrix.md` **registra** la resolución del 2026-08-04 (1.3.1) y no es un requisito;
  - ADR-014 solo lleva a un ciclo propio las subidas de versión mayor (1.x → 1.x no lo es).
- Se adopta **1.9.0**, el único valor certificado con FastAPI 0.141.1 en 3.13 (V1': SQLite, PostgreSQL y E2E en
  verde). El conjunto del lock histórico (1.3.1 sobre 3.11) nunca se instaló en un entorno certificado.
- No se elige por ser la más nueva: el grafo propuesto es exactamente el certificado.
- VERSION_CONFLICT = 0 y MATERIAL_OQ = 0.

**CVE** (`cve-gate.md`):
- lock propuesto y lock histórico comparten los mismos avisos (`PyJWT 2.13.0` y `cryptography 46.0.6`, pines directos);
- CVE_REGRESSION = 0;
- la vulnerabilidad de los pines directos se registra como deuda nueva y no se absorbe.

**ROOT_COUNT = 2**, causalmente independientes:
1. **LOCK-SIN-REPORTLAB-MAGIC.** El lock es una instantánea manual, sin mecanismo de regeneración ni comprobación de
   coherencia. `requirements.txt` evolucionó sin él. Aun consumido por la imagen, le faltarían `reportlab` y
   `python-magic`.
2. **PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES.** La imagen no consume ningún lock e instala solo los pines de primer
   nivel. Aun con un lock completo, las transitivas derivarían en cada build.

Las dos se corrigen con **una implementación común**: lock completo y regenerable, más una imagen que lo consume.
Se mantiene la trazabilidad separada de cada DEBT_ID.

## 3. Plan
| Tarea | Contenido | EXECUTOR | MODEL | FILES |
|---|---|---|---|---|
| T1 | Regenerar el lock con el **comando canónico** (procedimiento mecánico; prohibido editarlo a mano) | CLAUDE (procedimiento) | n-a | `resources/backend/requirements.lock` |
| T2 | La etapa `base` copia `requirements.lock` e instala `pip install --no-cache-dir --no-deps -r /tmp/requirements.lock && pip check`; deja de instalar `requirements.txt` | DEEPSEEK | deepseek-v4-flash | `Dockerfile.backend` |
| T3 | Prueba nueva `test_dependencias_lock.py` (IDL) y adaptación de la última aserción de IMB-03 (la instalación de Python pasa por el lock) | DEEPSEEK | deepseek-v4-pro | `resources/backend/tests/test_dependencias_lock.py`, `resources/backend/tests/test_imagen_backend_mime.py` |

- T4 (generador versionado) **no hace falta**: el comando canónico queda en la cabecera del lock y una prueba lo exige.
- `requirements.txt` no cambia: sus pines ya coinciden con el lock.
- Su comentario «Se generará un lockfile … durante el build» queda como observación documental para el ciclo de
  separación de dependencias.

Contrato de V3, el entorno de certificación de despliegue:
- CPython 3.13.15 + `pip install --no-cache-dir --no-deps -r requirements.lock && pip check` (el mismo mecanismo que la
  imagen);
- su freeze debe ser igual al lock, sin contar el `pip` del venv.

## 4. Constitution gate
- **P14/P16 y ADR-014:** versiones fijas en lockfiles, sin rangos, con actualización controlada (el corte de índice).
- **P10/P16:** no hay regresión de CVE. La deuda nueva de los pines directos queda registrada y visible.
- **Producto, esquema, migraciones, compose, workflows y QA:** sin cambio.
- **Preservado:** etapa final `runtime`, libmagic, usuario no root, `HEALTHCHECK`, `ENTRYPOINT` y keep-alive 75.

## 5. Checklist y trazabilidad
| Requisito | Tarea | Prueba |
|---|---|---|
| Todas las directas en el lock con su pin exacto (`NO_DIRECT_PIN_CONTRADICTIONS`) | T1 | IDL-01 |
| `reportlab`, `python-magic`, `PyYAML` y los extras de `uvicorn[standard]` | T1 | IDL-02 |
| Cada línea `nombre==versión` exacta y nombres únicos | T1 | IDL-03 |
| Comando canónico en cabecera, con Python igual al de la base de la imagen | T1 | IDL-04 |
| Suelo de `cve-review.md` respetado | T1 | IDL-05 |
| La cadena efectiva de la imagen instala el lock con `--no-deps` y `pip check`, sin reinstalar `requirements.txt` | T2 | IDL-06 e IMB-03 |
| Los analizadores detectan una directa ausente, un pin contradictorio y una instalación desde `requirements.txt` | T3 | IDL-07 |

Trazabilidad: 7 de 7 requisitos con tarea y prueba.

## 6. Material gate (antes de implementar, sobre el lock candidato del scratchpad)
| Indicador | Valor |
|---|---|
| ROOT_COUNT · ROOT_CAUSE_PROVEN | 2 · 1 |
| LOCK_GENERATION_METHOD_CONFIRMED · LOCK_REGENERABLE · LOCK_GRAPH_DETERMINISTIC | 1 (histórico: freeze manual; nuevo: comando canónico) · 1 · 1 |
| LOCK_INSTALLABLE_PY313 | 1 (V3) |
| LOCK_CONTAINS_ALL_DIRECT_REQUIREMENTS · REPORTLAB · PYTHON_MAGIC · PYYAML | 1 · 1 · 1 · 1 |
| NO_DIRECT_PIN_CONTRADICTIONS · VERSION_CONFLICT · CVE_REGRESSION | 1 · 0 · 0 |
| IMAGE_INSTALLS_FROM_LOCK | diseñado (T2) |
| V3_PIP_CHECK · V3_SMOKE_PASS · V3_FREEZE_EQUALS_LOCK | PASS · 1 · 1 |
| PRODUCT · SCHEMA · MIGRATION change required | 0 · 0 · 0 |
| TEST_DEPENDENCY_SPLIT_REQUIRED_FOR_THIS_FIX | 0 |
| OWNER_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**V3_SMOKE_PASS:** humo en PASS en import, `create_app`, lifespan, 85 módulos (incluidas licencias), alembic, OpenAPI
544/533/11 (idéntico al de V1'), MIME del PDF, exportación con ReportLab, PyYAML, JWT HS256 y Ed25519.

**Implementación autorizada.**

## 7. Implementación
- **T1 — `resources/backend/requirements.lock`:** generado con el comando canónico, que queda declarado completo en su
  cabecera:

      uv pip compile requirements.txt --python-version 3.13 --python-platform x86_64-unknown-linux-gnu --exclude-newer 2026-10-20T00:00:00Z --upgrade -o requirements.lock

  Contiene 49 paquetes con anotaciones `# via`.
  - **Hallazgo de diseño:** sin `--upgrade`, `uv pip compile -o requirements.lock` toma como preferencia los pines que
    ya tenía el fichero de salida. En la prueba heredó 20 versiones del lock histórico, así que el resultado dependía
    del contenido previo. Con `--upgrade` el resultado depende solo del corte.
  - uv omite `--upgrade` en la cabecera que escribe, por eso la cabecera se fija con `--custom-compile-command`.
  - **Procedimiento de regeneración:** ejecutar el comando de la cabecera añadiendo
    `--custom-compile-command "<el mismo comando>"`.
  - Comprobado:
    - regenerar sobre sí mismo da un resultado idéntico (`cmp`);
    - regenerar desde el lock histórico da el mismo cuerpo;
    - el cuerpo coincide con el grafo de V3 y de V1'.
  - **Actualizar dependencias** es mover el corte `--exclude-newer` de forma deliberada (ADR-014).
- **T2 — `Dockerfile.backend`:** la etapa `base` copia `requirements.lock` y ejecuta
  `pip install --no-cache-dir --no-deps -r /tmp/requirements.lock && pip check`. Deja de instalar `requirements.txt`.
  `runtime` y `dev` lo heredan.
- **T3:**
  - `resources/backend/tests/test_dependencias_lock.py` (IDL-01..07) reutiliza los analizadores de etapas de las pruebas
    de imagen;
  - IMB-03 (`test_imagen_backend_mime.py`) pasa a exigir la instalación desde el lock (1 línea).
- Sin cambios en `requirements.txt`, el producto, el esquema, compose, los workflows ni QA.

## 8. Pruebas y mutaciones
- **Rojo contra `44e47b5`:** IDL-01 (faltan `python-magic` y `reportlab`), IDL-02 (las mismas), IDL-04 (sin cabecera
  canónica) e IDL-06 (la imagen copia e instala `requirements.txt`) fallan por la razón exacta.
  - IDL-03, 05 y 07 pasan, porque el lock histórico ya era de pines exactos y respetaba el suelo.
  - No falla nada por la base flotante, la etapa `dev`, libmagic, el intérprete de migraciones o E2E, ni por la
    separación de dependencias.
- **Mutaciones:** **16/16 KILLED**, todas restauradas idénticas (`cmp`). Detalle en `mutations.json`.
  - M01-M03: quitar reportlab, python-magic o PyYAML.
  - M04: pin directo contradictorio.
  - M05: volver a `requirements.txt`.
  - M06: instalar el lock solo en `dev`.
  - M07: transitiva sin pin.
  - M08: versión distinta en el manifiesto.
  - M09 y M09b: cabecera sin `--exclude-newer` o sin `--upgrade`.
  - M10: sin `pip check`. M10b: sin `--no-deps`.
  - M11: lock para 3.11.
  - M12: Starlette 1.2.0, regresión de CVE.
  - M13: `runtime` deja de heredar `base`.
  - M14: falta una directa.
- `ruff check` limpio y el fichero nuevo formateado.
  - `test_imagen_backend_mime.py` ya estaba sin formatear en HEAD; el ciclo solo cambia una línea y no absorbe ese formato.

## 9. Certificación
| Corrida | V0 (control) | V3 (lock de despliegue) |
|---|---|---|
| `pip check` · freeze = lock · humo | — | PASS · 1 · PASS |
| SQLite | 1907/0/1056 ×2 | 1907/0/1056 |
| PostgreSQL | 2937/0/26 | 2937/0/26 |
| E2E con analizador | 284/0/0, limpia, protegidas intactas | 284/0/0, limpia, protegidas intactas |
| OpenAPI | 544/533/11 (sin cambio) | 544/533/11; solo las 4 diferencias del framework frente a V0, deriva de contrato 0 |

La imagen no se midió (sin Docker). Detalle en `evidence/production-dependencies-reproducible/certification.md`.

## 10. Convergencia — cierre en dos niveles
| Indicador | Valor |
|---|---|
| LOCK_GRAPH_DETERMINISTIC · LOCK_INSTALLABLE_PY313 · LOCK_HAS_HASHES | 1 · 1 · 0 |
| LOCK_CONTAINS_ALL_DIRECT · REPORTLAB · PYTHON_MAGIC · PYYAML | 1 · 1 · 1 · 1 |
| TRANSITIVES_DRIFT_PRE → POST | 26 diferencias lock↔despliegue, además de la deriva en cada build → **0** (V3 freeze = lock) |
| VERSION_CONFLICT · CVE_REGRESSION | 0 · 0 |
| IMAGE_INSTALLS_FROM_LOCK | 1 (estructural, IDL-06; M05, M06, M10, M10b y M13) |
| PRODUCT · REQUIREMENTS · SCHEMA · MIGRATION changed | 0 · 0 · 0 · 0 |
| OTHER_DEBT_ABSORBED | 0 |

- **DEPENDENCY_SET_REPRODUCIBILITY = CLOSED / CONVERGED.**
  - **LOCK-SIN-REPORTLAB-MAGIC = CLOSED / CONVERGED:** lock completo, regenerable y protegido por IDL-01..05.
  - **PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES = CLOSED / CONVERGED:** la imagen y la certificación consumen el
    mismo grafo fijado, con `--no-deps` y `pip check`. V3 lo reproduce exactamente.
- **IMAGE_LOCK_RUNTIME_CERTIFICATION = BLOCKED BY ENVIRONMENT.**
  - Puerta externa: **IMAGE-INSTALLED-DEPENDENCY-SET-NOT-RUNTIME-CERTIFIED**.
  - Se cierra cuando un `pip freeze` dentro de la imagen construida sea semánticamente igual al lock.

**Deudas registradas, no absorbidas:**
- BACKEND-DIRECT-DEPENDENCIES-KNOWN-VULNERABILITIES (OPEN, dueña 001, apoyo 052; seguridad).
- LOCK-WITHOUT-ARTIFACT-HASHES (OPEN, menor, dueña 052; ADR-014 no exige hashes).
