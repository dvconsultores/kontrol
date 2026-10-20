# Certificación — PRODUCTION-IMAGE-WITHOUT-LIBMAGIC

**Árbol certificado:** HEAD `226e1c3` + `requirements.txt` (`python-magic==0.4.27`) + `Dockerfile.backend`
(`libmagic1t64` en la etapa `base`) + `tests/test_imagen_backend_mime.py` (7 pruebas).
- Producto (`app/**`) y lock sin cambio.
- Todo con el analizador real.

## V0 (canónico temporal, `.venv`, CPython 3.11.16)
| Puerta | Corrida | Resultado |
|---|---|---|
| SQLite #1 | `r20261020t023009p1797270n5191fe` | rc 0 · **1892/0/1056** (1885 + 7 nuevas) · 676,5 s · NORMAL |
| SQLite #2 | `r20261020t024140p1878605n6da2b7` | rc 0 · **1892/0/1056** · 679,2 s · NORMAL |
| PostgreSQL | `r20261020t025314p1960014n90afa5` | rc 0 · **2922/0/26** (2915 + 7) · 1484,1 s · NORMAL |
| E2E | `r20261020t035129p2569909nbbd596` | rc 0 · **284/0/0** · LIMPIA · protegidas sin cambio · 0 QueuePool · 0 errores no controlados · 0 respuestas 500 · 0 MIME |
| OpenAPI | — | 544/533/11; documento idéntico al del ciclo anterior (OPENAPI_CHANGE = 0) |

## Paridad de despliegue V1' (CPython 3.13.15 + `pip install --no-cache-dir -r requirements.txt` CORREGIDO; libmagic del host)
| Puerta | Corrida | Resultado |
|---|---|---|
| `pip check` / humo | — | limpio / PASS; `find_library('magic')` = `libmagic.so.1`; PDF → `application/pdf`; texto → `text/plain` |
| Documentales | — | SQLite **111/0/27** · PostgreSQL **129/0/9** (V1 con el requirements de HEAD: 79/31/28) |
| SQLite | `r20261020t031812p2229048n82aae4` | rc 0 · **1892/0/1056** · 617,9 s · NORMAL |
| PostgreSQL | `r20261020t032844p2308171nc01ef7` | rc 0 · **2922/0/26** · 1338,3 s · NORMAL |
| E2E | `r20261020t035622p2598927na9227b` | rc 0 · **284/0/0** · LIMPIA · 0 QueuePool · 0 errores no controlados · 0 respuestas 500 · 0 MIME |
| OpenAPI | — | 544/533/11; las mismas 4 diferencias generadas por el framework (no contractuales) |

**Prerrequisito de OBS-09** (`obs09-mime-prerequisite-probe.txt`). Con los ficheros de `qa/compose_qa.py`, leídos por
AST y sin modificarlo:

| Fichero | V1 | V1' |
|---|---|---|
| `PDF_LIMPIO` (F01/F03/F04) | `application/octet-stream` | `application/pdf` |
| EICAR (F02) | `application/octet-stream` | `text/plain` |

Los dos superan la fase MIME del tipo que usa OBS-09.

**Imagen:** DOCKER_AVAILABLE = 0 (no hay docker, podman ni buildah), así que IMAGE_RUNTIME_CERTIFICATION = **NOT
EXECUTED**. No se fabrica evidencia de imagen: la evidencia del host no sustituye a la del runtime de la imagen.

**Huecos que se mantienen:**
- MIGRATION_TESTS_EXECUTED_WITH_DEPLOYMENT_INTERPRETER = 0 (TEST-MIGRACIONES-VENV-FIJO).
- E2E_BACKEND_INTERPRETER = V1'.
- E2E_AUTHORITY_MIGRATION_INTERPRETER = V0 (E2E-HARNESS-INTERPRETER-FIXED).

**Equipo:**

| E2E | Precheck | Muestreo de 1 Hz |
|---|---|---|
| V0 | 6,0 GB disponibles | memoria mínima 696 MB, swap máxima 6,4 GB |
| V1' | 8,0 GB disponibles | memoria mínima 838 MB, swap máxima 6,1 GB |

Hasta 5 clamscan simultáneos en ambas.
