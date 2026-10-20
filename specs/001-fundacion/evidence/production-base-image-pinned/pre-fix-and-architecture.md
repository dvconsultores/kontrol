# Reproducción previa, consumidores y arquitectura (contra `6459fa0`, 2026-10-21)

## Reproducción
| Indicador | Valor | Clase de evidencia |
|---|---|---|
| BASE_REFERENCE_PRE | `FROM python:3.13-slim AS base` (`Dockerfile.backend:7`) | medido (repositorio) |
| PATCH_VERSION_PINNED_PRE · DISTRO_PINNED_PRE · DIGEST_PINNED_PRE · REFERENCE_IMMUTABLE_PRE | 0 · 0 · 0 · 0 | medido |
| `python:3.13-slim` hoy | índice `sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f` = `3.13-slim-trixie` = `3.13.16-slim-trixie`; config amd64 `PYTHON_VERSION=3.13.16`, creada el 2026-10-06 | VENDOR_METADATA (config OCI verificada) |
| `python:3.13.15-slim-trixie` | índice `sha256:7c61056e61ac89e852de05f3dc6fa51a6dd2181797bceed46aa725dd7cb2cd3b`, creada el 2026-09-19 | VENDOR_METADATA |
| Imagen publicada `dvconsultores/kontrol-backend:latest` | índice OCI con una sola plataforma `linux/amd64` (más la atestación de buildx); config `PYTHON_VERSION=3.13.16`, creada el 2026-10-20T20:21Z | VENDOR_METADATA del registro |

**Deriva demostrada sin esperar a que cambie la etiqueta:**
- El certificado de despliegue (V4) usa CPython 3.13.15.
- La misma referencia textual `python:3.13-slim` ya resolvió a 3.13.16 desde el 2026-10-06.
- Lo desplegable publicado hoy ejecuta 3.13.16.
- La deriva entre intérprete certificado y desplegado ya existe; la etiqueta flotante la produjo.

## Consumidores del `FROM`
| Consumidor | Qué lee | Efecto de un FROM `tag@sha256` |
|---|---|---|
| IDL-04 `_python_de_la_base` | `^python:(\d+\.\d+)` del FROM raíz | compatible (toma 3.13) |
| IBE (`_etapas_completas`) e IMB (`_etapas`) | `re.split(r"\s+AS\s+")`; el padre es la etapa declarada | compatibles (la imagen externa no es una etapa) |
| `test_backend_keepalive` | primer `CMD` | sin relación |
| Literales `python:3.13-slim` en IDL-07 e IBE-08 | Dockerfiles **sintéticos** | sin relación |
| build-main y build-dev | buildx con `target: runtime`, sin `platforms` | resuelven el índice en la plataforma del runner |
| compose y QA | imagen del registro / build por defecto | sin cambio |

## Arquitectura
| Campo | Valor | Fuente |
|---|---|---|
| CI_BUILD_ARCHITECTURE | linux/amd64: `ubuntu-latest` alojado en x86_64 con `setup-buildx-action`, sin `platforms` ni QEMU (build nativo) | workflows (repositorio) |
| REGISTRY_IMAGE_ARCHITECTURE | **linux/amd64**, la única plataforma del índice publicado | registro, medido |
| DEPLOYMENT_OS · DEPLOYMENT_ARCHITECTURE | linux · amd64. Lo desplegable solo existe para amd64; `compose.yaml` lo usa | derivado de lo medido |
| RUNTIME_ARCHITECTURE_IF_KNOWN | NOT MEASURED (el host de producción queda fuera de alcance) | — |
| DEPLOYMENT_ARCHITECTURE_CONFIRMED · TARGET_PLATFORM | 1 · linux/amd64 | — |

Con el digest de **índice** (`tag@sha256:<índice>`) la referencia es inmutable para todas las plataformas, y buildx
selecciona el manifiesto hijo `linux/amd64`. No hace falta fijar un manifiesto de plataforma.
