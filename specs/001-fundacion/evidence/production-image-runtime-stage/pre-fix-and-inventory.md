# Reproducción previa e inventario de consumidores (contra `f7e7e44`)

**Grafo de etapas antes del cambio:** `base` (`python:3.13-slim`) → `dev` (`FROM base`, última).
- DEFAULT_BUILD_WITHOUT_TARGET_RESOLVES_TO = **dev**.
- DEV_STAGE_CONTAINS_TEST_SOURCE = 1 (`COPY resources/backend/tests ./tests`).
- DEV_STAGE_CONTAINS_RELOAD = 1 (`CMD [… "--reload" …]`).
- Uso de `--target` o `target:` en el repositorio: **0**.

| Consumidor | Propósito real | Target antes | Etapa antes | Target después | Etapa después |
|---|---|---|---|---|---|
| `.github/workflows/build-dev.yml` (push a `develop` → `kontrol-backend:latest`, la que `compose.yaml` despliega por defecto) | producción | — | dev | `runtime` | runtime |
| `.github/workflows/build-main.yml` (`kontrol-backend:main`) | producción | — | dev | `runtime` | runtime |
| `compose.yaml` (imagen del registro, sin `build` ni `command`) | producción (despliegue) | — | la publicada (dev) | — | la publicada (runtime) |
| `qa/compose_qa.py` (`docker build` + `docker run --entrypoint sh`; pruebas por HTTP) | QA de la imagen de producción; no usa `tests/` ni pytest dentro | — | dev | — (por defecto) | runtime |
| `docs/evidence/docker-validation-checklist.md` | QA manual | — | dev | — (por defecto) | runtime |
| `qa/clamd_qa.py` y pruebas estructurales | lectura estática | — | — | — | — |

- **Consumidores reales de `dev`:** 0.
- QA_NEEDS_DEV_STAGE = 0.
- BUILD_CONSUMERS_TOTAL = 7: 3 de producción (build-dev, build-main, compose), 2 de QA (compose_qa y la lista de
  validación), 2 estáticos y de limpieza (clamd_qa con las pruebas estructurales, reset.sh), 0 de desarrollo.
