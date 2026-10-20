# Certificación — PRODUCTION-IMAGE-BUILT-FROM-DEV-STAGE (2026-10-20)

**Entornos:**
- V0 = `.venv` histórico (CPython 3.11.16, FastAPI 0.115.6).
- V1' = CPython 3.13.15 + `pip install --no-cache-dir -r requirements.txt` (FastAPI 0.141.1, Starlette 1.9.0,
  python-magic 0.4.27).

Backend con `qa/suite_tiempos.py --con-analizador` (ClamAV real); E2E con `qa/e2e-run.py --con-analizador`.

| Corrida | Resultado | Duración | Anomalía |
|---|---|---|---|
| V0 SQLite 1 | 1900/0/1056 (rc 0) | 653,4 s | NORMAL |
| V0 SQLite 2 | 1900/0/1056 (rc 0) | 651,8 s | NORMAL |
| V0 PostgreSQL | 2930/0/26 (rc 0) | 1444,7 s | NORMAL |
| V1' SQLite | 1900/0/1056 (rc 0) | 590,2 s | NORMAL |
| V1' PostgreSQL | 2930/0/26 (rc 0) | 1357,6 s | NORMAL |
| V0 E2E | **284/0/0**, limpieza LIMPIA, `protegidas_sin_cambios` = true | 4,5 min | — |
| V1' E2E | **284/0/0**, limpieza LIMPIA, `protegidas_sin_cambios` = true | 4,4 min | — |

**Notas de la tabla:**
- Las suites crecen en +8 respecto de la línea base anterior (1892 / 2922): son las 8 IBE nuevas.
- El `backend.log` de ambas E2E da QueuePool 0, 500 0, Traceback 0 y rechazos MIME 0.
- Anfitrión durante las E2E: memoria disponible mínima de 674 MB, swap máxima de 6,4 GB, carga máxima de 15,9 y
  clamscan concurrentes máximo 5. Pasaron sin fallos.

**OpenAPI (sonda en proceso):**
- V0 y V1' dan 544 operaciones, 533 caminos y 11 esquemas de seguridad.
- El documento de V0 es idéntico al del ciclo anterior, y el de V1' también.
- No hay deriva de contrato, como corresponde a un cambio sin producto.
- Humo IMPORT, CREATE, LIFESPAN y OPENAPI en PASS; MIME: PDF → `application/pdf`, TXT → `text/plain`.

**Certificación de la imagen:**
- **NOT EXECUTED**: DOCKER_AVAILABLE = 0, sin instalar nada.
- La evidencia del contrato es estructural: grafo de etapas, `CMD` efectivo, `COPY` y `target` de los workflows, más 14
  mutaciones.
- Medir una imagen real (`docker build` sin target, inspección de `Cmd`, `User` y `Healthcheck`, ausencia de
  `/app/tests` y de `--reload`) queda pendiente de un entorno con Docker, por ejemplo la evidencia de OBS-09 o el CI.
