# SPEC 052 · Delta — PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE

- **Dueña:** Spec 052. Apoyo: Spec 054.
- **Fecha:** 2026-10-20, rama `develop`, HEAD de partida `f7e7e44`.
- **Ruta B:** no hay evidencia Docker de OBS-09.
- **DOCKER_AVAILABLE = 0.**
- **Decisiones:** OD-CERT-01 a 04 ratificadas. OD-CERT-04: el build por defecto es producción y `dev` exige selección
  explícita.
- **Evidencia:** `evidence/production-image-runtime-stage/`.
- **Directorio ajeno de la dueña:** `docs/Administracion Publica - Gobierno/`. Está presente, no es residuo y no se toca.
  Su huella de entrada es `4f1e6954208b…`.

## 1. Specify
Un `docker build` sin target y toda imagen que se publique deben ser el runtime de producción, sin `--reload` ni
`tests/`. La imagen de desarrollo solo debe obtenerse con selección explícita.

## 2. Clarify — reproducción e inventario de consumidores

**Reproducción previa, estructural, contra `f7e7e44`:**
- Etapas: `base` (`python:3.13-slim`) y `dev` (`FROM base`, la última).
- DEFAULT_BUILD_WITHOUT_TARGET_RESOLVES_TO = **dev**.
- DEV_STAGE_CONTAINS_TEST_SOURCE = 1 (`COPY resources/backend/tests ./tests`).
- DEV_STAGE_CONTAINS_RELOAD = 1 (`CMD … --reload`).
- Nadie en el repositorio usa `--target` ni `target:`.

**Consumidores:**

| Consumidor | Propósito real | Target hoy | Etapa efectiva | Necesita tests, pytest o reload | Publica | Despliega | Target tras el cambio |
|---|---|---|---|---|---|---|---|
| `.github/workflows/build-dev.yml` (push a `develop`) | **PRODUCCIÓN**: publica `kontrol-backend:latest`, la etiqueta que despliega `compose.yaml` por defecto (`${KONTROL_IMAGE_TAG:-latest}`) | ninguno | dev | no | sí | indirectamente | `runtime` explícito |
| `.github/workflows/build-main.yml` (push a `main`, rama de release aún inexistente) | PRODUCCIÓN: `kontrol-backend:main` | ninguno | dev | no | sí | — | `runtime` explícito |
| `compose.yaml` | PRODUCCIÓN: usa la imagen del registro; no construye ni sobrescribe el comando | — | la publicada | no | — | sí | (la publicada: runtime) |
| `qa/compose_qa.py` (evidencia de OBS-09) | QA de la imagen de producción: `docker build` sin target y `docker run --entrypoint sh` para comprobar que no hay clamscan ni firmas; pruebas por HTTP desde fuera | ninguno | dev | **no** | no | no | sin cambio (por defecto, runtime) |
| `docs/evidence/docker-validation-checklist.md` | QA manual: `docker build -f Dockerfile.backend` sin target | ninguno | dev | no | no | no | sin cambio (por defecto, runtime) |
| `qa/clamd_qa.py`, `test_clamav_qa`, `test_documents_clamd`, `test_backend_keepalive`, `test_imagen_backend_mime` | validación estática: leen el texto | — | — | — | — | — | se preservan |
| `scripts/reset.sh` | limpieza local de imágenes por nombre | — | — | no | no | no | sin cambio |

- **Consumidores reales de `dev`:** ninguno. Solo la intención documentada en la cabecera del Dockerfile («target
  "dev" para desarrollo con reload»).
- QA_NEEDS_DEV_STAGE = 0.

## 3. Plan — contrato de etapas (opción C)
- **`base`:** sin cambio. Capacidades del producto, libmagic, usuario `kontrol`, HEALTHCHECK, ENTRYPOINT, y
  `CMD uvicorn … --timeout-keep-alive 75` sin `--reload`.
- **`dev`:** sin cambio. `FROM base`, `tests/`, herramientas y `--reload`. Solo con `--target dev`.
- **`runtime`:** NUEVA y **ÚLTIMA** etapa, `FROM base` sin instrucciones propias. Hereda todo de `base`, así que el
  build sin target da producción. La cabecera del fichero se actualiza.
- **CI:** `target: runtime` en el paso del backend de `build-main.yml` y de `build-dev.yml`. Es defensa en profundidad:
  una publicación no depende del orden de las etapas.
- **`qa/compose_qa.py`:** sin cambio.

## 4. Constitution gate
- Producto, requirements, lock y compose sin cambio.
- Sin «clam» en el Dockerfile.
- `CMD` de `base` intacto (el primero del fichero, que lee `test_backend_keepalive`).
- KA-03 sigue viendo el keep-alive 75 también en el `CMD` de `dev`.

## 5. Tareas
| Tarea | EXECUTOR | MODEL | FILES |
|---|---|---|---|
| T1 etapas | DEEPSEEK | deepseek-v4-flash | `Dockerfile.backend` |
| T2 prueba estructural | DEEPSEEK | deepseek-v4-pro | `resources/backend/tests/test_imagen_backend_etapas.py` |
| T3 CI | DEEPSEEK | deepseek-v4-flash | `.github/workflows/build-main.yml`, `.github/workflows/build-dev.yml` |

## 6. Material gate
| Indicador | Valor |
|---|---|
| ROOT_CAUSE_PROVEN · BUILD_CONSUMERS_INVENTORIED · PUBLISHED_IMAGE_CONTRACT_CONFIRMED | 1 · 1 · 1 |
| DEV_CONSUMERS_IDENTIFIED · QA_NEEDS_DEV_STAGE | 1 (ninguno real) · 0 |
| DEFAULT_RUNTIME_DESIGN_PROVEN | 1 (la última etapa es la de un build sin target; `runtime` hereda la configuración de `base`) |
| BUILD_MAIN_TARGET_DESIGNED · BUILD_DEV_TARGET_DESIGNED · QA_TARGET_DESIGNED | runtime · runtime · por defecto (runtime) |
| LIBMAGIC · NONROOT · HEALTHCHECK · ENTRYPOINT · KEEPALIVE preservables | 1 · 1 · 1 · 1 · 1 |
| PRODUCT · REQUIREMENTS · SCHEMA · MIGRATION change required | 0 · 0 · 0 · 0 |
| OWNER_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**Implementación autorizada.** Estado máximo: IMPLEMENTED — IMAGE RUNTIME CERTIFICATION BLOCKED BY ENVIRONMENT.

**Deuda separada que se registra y no se implementa:** PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES.
`requirements.txt` lleva pytest, httpx, ruff y mypy, y `base`, y por tanto `runtime`, los instala.

## 7. Implementación
- **T1 — `Dockerfile.backend`:** nueva etapa final `FROM base AS runtime`, sin instrucciones propias.
  - Hereda de `base` el usuario `kontrol`, `HEALTHCHECK` (`/api/v1/health/live`), `ENTRYPOINT ["/app/entrypoint.sh"]`,
    el `CMD` sin `--reload` con `--timeout-keep-alive 75` y `libmagic1t64`.
  - No copia `tests/` ni instala herramientas.
  - La cabecera documenta que `runtime` es lo que produce un build sin `--target` y que `dev` exige `--target dev`.
  - `base` y `dev` no cambian.
- **T3 — workflows:** `target: runtime` en el paso de build del backend de `build-main.yml` (`:main`) y de
  `build-dev.yml` (`:latest`, la que despliega `compose.yaml`). La elección queda explícita y no depende del orden de las
  etapas.
- **T2 — `resources/backend/tests/test_imagen_backend_etapas.py` (IBE-01..08):**
  - Analiza el grafo de etapas por herencia y reutiliza `_instrucciones` y `_cadena_efectiva` de
    `test_imagen_backend_mime.py`.
  - IBE-01: etapa final `runtime`, sin `dev` en su cadena.
  - IBE-02: `CMD` efectivo sin `--reload`, con `app.main:app` y keep-alive 75.
  - IBE-03: ningún `COPY` ni `ADD` de pruebas.
  - IBE-04: usuario no root.
  - IBE-05: `HEALTHCHECK` y `ENTRYPOINT`.
  - IBE-06: `dev` existe, hereda de `base`, no es la final y lleva `--reload`.
  - IBE-07: los dos workflows publican con `target: runtime`.
  - IBE-08: Dockerfiles sintéticos que validan el propio analizador (cadena de tres etapas e imagen externa).
- `compose.yaml`, `qa/compose_qa.py`, el producto, `requirements.txt` y el lock no cambian.

## 8. Pruebas y mutaciones
- **Rojo contra `f7e7e44`:** IBE-01, 02, 03, 06 y 07 fallan por la razón exacta: la final es `dev`, hay `--reload`, se
  copian las pruebas, `dev` es la final y no hay `target`. IBE-04, 05 y 08 pasan (preservación) y las pruebas MIME
  también (`evidence/production-image-runtime-stage/red-against-head.txt`).
- **Dirigidas:** en V0 y en V1', los módulos estructurales dan 78 passed y 2 skipped (los 2 de `test_clamav_qa`, sin el
  entorno del analizador; previos). El resultado es el mismo en orden normal e inverso, y las IBE solas dan 8/8. Los
  módulos son `test_imagen_backend_etapas`, `test_imagen_backend_mime`, `test_backend_keepalive`, `test_clamav_qa`,
  `test_documents_clamd` y `test_compose_qa`.
- **Mutaciones:** **14/14 KILLED**, todas restauradas idénticas (`cmp`).
  - M01 `dev` final · M02 `runtime` hereda de `dev` · M03 `--reload` · M04 copia de pruebas · M05 `target: dev`.
  - M06 sin `target` · M07 `dev` renombrada · M08 libmagic perdida · M09 USER root · M10 sin `HEALTHCHECK`.
  - M11 sin `ENTRYPOINT` · M12 keep-alive distinto · M13 el analizador toma una imagen externa como etapa · M14 el
    analizador solo mira la etapa final.
  - Detalle en `evidence/production-image-runtime-stage/mutations.json`.

## 9. Certificación
| Corrida | V0 | V1' |
|---|---|---|
| SQLite | 1900/0/1056 ×2 | 1900/0/1056 |
| PostgreSQL | 2930/0/26 | 2930/0/26 |
| E2E con analizador | 284/0/0, limpia, protegidas intactas | 284/0/0, limpia, protegidas intactas |
| OpenAPI | 544/533/11, idéntico al ciclo anterior | 544/533/11, idéntico al ciclo anterior |

- La imagen real no se midió (sin Docker).
- Detalle en `evidence/production-image-runtime-stage/certification.md`.

## 10. Convergencia
| Indicador | Valor |
|---|---|
| DEFAULT_NO_TARGET_BUILD_IS_PRODUCTION | 1 (estructural, IBE-01; M01 y M02) |
| PUBLISHED_REGISTRY_IMAGE_IS_PRODUCTION | 1 (`target: runtime` en `build-main` y `build-dev`; IBE-07; M05 y M06) |
| DEV_IMAGE_REQUIRES_EXPLICIT_SELECTION | 1 (IBE-06; M07) |
| PRODUCTION_IMAGE_CONTAINS_RELOAD · PRODUCTION_IMAGE_CONTAINS_TEST_SOURCE | 0 · 0 (IBE-02 e IBE-03; M03 y M04) |
| LIBMAGIC · NONROOT · HEALTHCHECK · ENTRYPOINT · KEEPALIVE preservados | 1 · 1 · 1 · 1 · 1 (M08–M12) |
| PRODUCT · REQUIREMENTS · LOCK · SCHEMA · MIGRATION changed | 0 · 0 · 0 · 0 · 0 |
| OPENAPI_DRIFT | 0 |
| DOCKER_AVAILABLE · IMAGE_RUNTIME_CERTIFIED | 0 · 0 |
| Deudas no absorbidas | PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES (nueva, OPEN) · PRODUCTION-DEPENDENCIES-UNPINNED-TRANSITIVES · PRODUCTION-BASE-IMAGE-FLOATING-TAG · LOCK-SIN-REPORTLAB-MAGIC · OBS-09 |

**Estado: IMPLEMENTED — IMAGE RUNTIME CERTIFICATION BLOCKED BY ENVIRONMENT.** Pasa a CLOSED / CONVERGED cuando una imagen
construida sin `--target` (y la publicada) demuestre:
- `Cmd` sin `--reload`;
- `User` = kontrol;
- `Healthcheck` presente;
- ausencia de `/app/tests` y libmagic operativa.
