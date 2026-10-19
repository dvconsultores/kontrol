# SPEC 054 · Delta de diagnóstico — CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT

- **Dueña:** Spec 054. Apoyo: Spec 001 (versiones, CVE) y Spec 052 (imagen y despliegue).
- **Fecha:** 2026-10-19, rama `develop`, HEAD de partida `e11e8fe`.
- **Ruta B:** no hay evidencia Docker de OBS-09.
- **Evidencia:** `evidence/certification-environment-drift-diagnosis/`.
- **Alcance:** solo diagnóstico. No cambian producto, pruebas, QA, requirements, lock, Dockerfile ni `.venv`.
- **DeepSeek:** 0 llamadas.

## 1. Specify
Pregunta del ciclo: ¿certificamos el mismo entorno que desplegamos? (OD-CERT-01 ya está ratificada).

## 2. Clarify — definición del entorno de producción (`production-environment.json`)
| Elemento | Valor medido en las fuentes |
|---|---|
| Imagen base | `python:3.13-slim`, etiqueta flotante sin digest |
| Instalación | `pip install --no-cache-dir -r requirements.txt` (`Dockerfile.backend:20`), con el pip de la imagen |
| Lock consumido | **no** (`PRODUCTION_LOCK_ACTUALLY_CONSUMED = 0`); las transitivas se resuelven en el build |
| Paquetes de sistema | solo `curl`; **sin libmagic** |
| Etapa construida | **`dev`**: es la última del Dockerfile; ni `build-main.yml` ni `build-dev.yml` pasan `target`, `compose.yaml` usa la imagen del registro y `qa/compose_qa.py` construye sin `--target`. El contenedor corre `uvicorn --reload` con las pruebas copiadas |

## 3. Plan · 4. Constitution gate
| Entorno | Definición | Uso |
|---|---|---|
| V0 | `.venv` histórico, de solo lectura | control |
| V1 | CPython 3.13.15 (obtenido con uv en el scratchpad) + `python -m venv` + `pip install -r requirements.txt` | la semántica de instalación de la imagen |
| V2 | V1 + `python-magic==0.4.27` con el libmagic del host | aislar la deuda de libmagic |

- V3 no fue necesario: cada fallo se separó entre intérprete y paquete con una sonda específica.
- **Gate:** sin escrituras en rutas versionadas fuera de la documentación ✔ · sin paquetes de sistema ✔ · residuos
  confinados al scratchpad ✔.

## 5. Experimentos y resultados

**Dependencias** (`environment-v*.txt`, `dependency-classification.tsv`):
- V1 y V2: `pip check` limpio. Los 17 pines de `requirements.txt` se instalan exactos.
- **20 transitivas difieren del lock (LOCK_DRIFT).** La principal: un build de hoy instala **Starlette 1.9.0**, no la
  1.3.1 que declaran el lock y `dependency-matrix.md`. También cambian anyio 4.15.1, click 8.5.0 y uvloop 0.23.0, entre
  otras.
- Fuera del lock: pillow y charset-normalizer.
- `greenlet` está en el lock, pero no se instala en 3.13.

**Humo** (`smoke-gate.txt`): V0, V1 y V2 pasan las 7 comprobaciones:
- importación, creación de la app y `lifespan`;
- 85 módulos;
- Alembic, con 1 cabeza;
- OpenAPI 544/533/11.

MIME en V1: un PDF y un texto plano se detectan como `application/octet-stream`. En V2 se detectan bien.

**OpenAPI V0 frente a V2** (`openapi-diff.json`): mismos recuentos y 4 diferencias, todas FRAMEWORK_GENERATED_NONCONTRACTUAL.
- `file` pasa de `format: binary` a `contentMediaType: application/octet-stream`.
- El esquema por defecto `ValidationError` gana `ctx` e `input`.
- El 422 real del producto es su propio sobre `VALIDATION_ERROR` (`errors.py:122-131`), y el frontend no consume tipos
  generados.
- OPENAPI_CONTRACT_DRIFT = 0.

**Suites** (`suite-results.md`):
- V1, documentales: 79/31/28. **Las 31 son PRODUCTION_IMAGE_WITHOUT_LIBMAGIC.**
- V2, SQLite: 1881/4/1056.
- V2, PostgreSQL: 2913/2/26.
- Mismos totales que V0.

## 6. Atribución (`failure-attribution.json`)

| Fallo | Clasificación | Causa demostrada |
|---|---|---|
| OAS-14 (`test_openapi_security`) | DRIFT_TEST_INCOMPATIBILITY | FastAPI 0.141 guarda los routers incluidos como `_IncludedRouter` en `app.routes`. La prueba solo recorre el primer nivel; las 544 `APIRoute` siguen ahí. El producto no enumera rutas |
| ACS-08 (`test_motor_para_hilos`) | PYTHON_INTERPRETER_INCOMPATIBILITY | CPython 3.13 quita la sangría de `__doc__`, así que `.replace(__doc__, "")` ya no elimina el docstring y la prueba ve «timeout» en él |
| U03 y U04 (`test_license_middleware_event_loop`, SQLite) | PACKAGE_VERSION_INCOMPATIBILITY, sobre la ruta de producto `get_db` | FastAPI 0.141 ejecuta el código de salida de las dependencias con `yield` **después** de enviar la respuesta (0.115.6: antes), medido con una sonda aislada. Al llegar la última respuesta hay 10 conexiones aún prestadas y a los 50 ms ninguna; balance 15 = 15; sin fugas. `get_db` solo hace `db.close()` en su salida |
| 31 documentales en V1 | PRODUCTION_IMAGE_WITHOUT_LIBMAGIC | V2 = V1 + python-magic y en V2 pasan |

**Clasificación:**
- DRIFT_PRODUCT_INCOMPATIBILITIES = **0**: ningún fallo funcional del producto con las versiones de despliegue.
- Hay un cambio semántico del framework en la ruta de producto `get_db`: decisión técnica para la canonicalización.

**Hallazgos estructurales nuevos, registrados y no absorbidos:**
- **PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE:** la imagen publicada es la etapa `dev`, con `--reload` y las pruebas dentro.
- **PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES:** el lock no se consume; las transitivas derivan con la fecha del
  build, y la base `python:3.13-slim` no está fijada por digest.
- **E2E_HARNESS_INTERPRETER_FIXED (parcial):** `qa/e2e_corrida.py:393` migra la autoridad central con
  `.venv/bin/alembic`.

## 7. E2E y material gate (`e2e-result.md`, `material-gate.md`)
- **E2E con V2:** 284/0/0, LIMPIA, 0 QueuePool. El backend corrió con V2 por construcción; solo la migración de la
  autoridad central usa el alembic de V0.
- **Material gate: CASO D, mixto.**
  - DRIFT_PRODUCT_INCOMPATIBILITIES = 0.
  - DRIFT_TEST_INCOMPATIBILITIES = 1.
  - PYTHON_INTERPRETER_INCOMPATIBILITIES = 1.
  - PACKAGE_VERSION_INCOMPATIBILITIES = 1 (`get_db` tras la respuesta).
  - LIBMAGIC_FAILURES = 31.
  - OPENAPI_CONTRACT_DRIFT = 0.
  - OWNER_DECISION_REQUIRED = 0.

## 8. Convergencia diagnóstica
**DIAGNOSIS COMPLETE — MIXED: CERTIFICATION HARNESS DRIFT + FRAMEWORK SEMANTIC CHANGE ON get_db PROVEN; NO FUNCTIONAL
PRODUCT INCOMPATIBILITY.**

- CERTIFICATION-ENVIRONMENT-DEPENDENCY-DRIFT sigue OPEN, con el impacto medido.
- RELEASE_DEPLOYMENT_PARITY_CERTIFIED = 0: el entorno canónico no cambia hasta que V2 esté en verde y se canonicalice.

Deudas separadas y registradas, sin megacorrección:

| Deuda | Dueña | Qué cubre |
|---|---|---|
| FASTAPI-YIELD-TEARDOWN-AFTER-RESPONSE | 001, apoyo 054 | cambio semántico de `get_db` |
| DEPLOYMENT-PARITY-TEST-INCOMPATIBILITIES | 054 | OAS-14 y ACS-08 |
| PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE | 052 | — |
| PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES | 052, apoyo 001 | — |
| E2E-HARNESS-INTERPRETER-FIXED | 054 | parcial |

PRODUCTION-IMAGE-WITHOUT-LIBMAGIC queda reproducida (31 fallos en V1). Sigue siendo independiente y es prerequisito de
la evidencia de OBS-09 (OD-CERT-02).

## 9. Impacto medido del cambio de `get_db` (`get-db-teardown-impact.md`)
Con una respuesta de 20 MB leída despacio, la salida de la dependencia ocurre al entregarse el cuerpo al socket, en V0 y
en V2: un cliente lento **no** retiene la conexión. El efecto de FastAPI 0.141 es una ventana de milisegundos.
FASTAPI-YIELD-TEARDOWN-AFTER-RESPONSE queda registrada con impacto despreciable, y U03/U04 entran en la normalización del
arnés, sin ser deuda de producto prioritaria.
