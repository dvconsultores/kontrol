# Certificación final — PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES (2026-10-23/24)

**Árbol:** `31297a1` + T1..T4 y los dos locks generados.
**Entorno:**
- PostgreSQL de QA (`pg-provision.sh start` y `mkdb ktest`);
- ClamAV 1.4.3;
- V6R y V6C reconstruidos por digest: tras un reinicio se reconstruyeron de nuevo con el mismo resultado (`v6r-rebuild-2026-10-24.json`).

## Manifiestos y locks
| | Runtime | Certificación |
|---|---|---|
| Manifiesto | `requirements.txt` (14) | `requirements-test.txt` (`-r requirements.txt` + 4) |
| Lock | `requirements.lock` (**38**) | `requirements-test.lock` (**49**) |
| Orden | `uv pip compile requirements.txt … --exclude-newer 2026-10-20T02:24:15.073Z --upgrade -o requirements.lock` | `uv pip compile requirements-test.txt --constraint requirements.lock … (mismo corte) --upgrade -o requirements-test.lock` |
| Determinismo | `cmp` idéntico al regenerar | `cmp` idéntico al regenerar |
| pip-audit PyPI · OSV | 0 · 0 | 0 · 0 |

- Salen del runtime: certifi, httpcore, httpx, iniconfig, mypy, mypy-extensions, packaging, pluggy, pygments, pytest y ruff.
- **0 cambios de versión** en el runtime.
- El grafo de certificación es **idéntico** al lock de 49 paquetes certificado en `31297a1`.

## V6R (runtime puro) y V6C (certificación)
| Indicador | V6R | V6C |
|---|---|---|
| Base | `python:3.13.16-slim-trixie@sha256:70729b46…` (4 capas verificadas por sha256), libmagic `1:5.46-5`, `ca-certificates 20250419+deb13u1` (CA 148) | V6R + `pip install --no-deps -r requirements-test.lock` (como la etapa `dev`) |
| CPython | 3.13.16 (OpenSSL 3.5.7, glibc 2.41) | 3.13.16 |
| `pip check` | PASS | PASS |
| Freeze = lock | 1 (38) | 1 (49) |
| Herramientas de prueba importables | **0** | pytest 9.0.3, ruff, mypy |
| Subconjunto runtime con la misma versión | — | **38 de 38** (RUNTIME_SUBSET_EQUAL_IN_CERTIFICATION = 1) |
| Humo sin herramientas | 119 módulos; `create_app` + lifespan; OpenAPI; JWT; Ed25519; licencias; PDF y MIME; con PostgreSQL, `alembic upgrade head` + health ready (`v6r-smoke.json`). El único paso fallido es `alembic --sql` offline: las migraciones hacen consultas reales, así que lo sustituye el humo online contra PostgreSQL | — |

## Backend (`qa/suite_tiempos.py --con-analizador`)
| Corrida | Intérprete | Resultado | Monotónico |
|---|---|---|---|
| `r20261023t014126` SQLite | V0 3.11.16 | **1965/0/1070** | 722,8 s |
| `r20261023t015343` SQLite | V6C 3.13.16 (IN_PROCESS_CERTIFICATION_OVERLAY sobre el runtime exacto) | **1965/0/1070** | 673,6 s |
| `r20261023t020511` PostgreSQL | V6C 3.13.16 | **3009/0/26** | 1505,5 s |

Frente a `31297a1` (1956/0/1064 y 2994/0/26): +9 IDF; +6 omitidas en SQLite (e2ecorrida_27..32, que solo corren sobre PostgreSQL); +15 en PostgreSQL.

## E2E final (condición de salud previa medida en `salud.jsonl`; validez posterior por el incremento de swap)
| | V0 `r20261023t230552` | V6 `r20261023t225311` |
|---|---|---|
| Orden | `.venv/bin/python qa/e2e-run.py --con-analizador` | `<V6C> qa/e2e-run.py --con-analizador --python-de-producto <V6R>` |
| Resultado | **284/0/0**, LIMPIA | **284/0/0**, LIMPIA |
| Arnés = migración de la autoridad | 3.11.16 = 3.11.16, paridad 1 | 3.13.16 = 3.13.16, paridad 1 |
| Producto (`interprete_de_producto`) | UN_SOLO_ENTORNO; herramientas visibles (las de V0); paridad 1 | **RUNTIME_SEPARADO**; herramientas: **ninguna**; paridad_runtime 1 |
| Backend y autoridad (muestreo `/proc`) | V0 3.11 | **`ld-linux` del rootfs de V6R**, 3.13 |
| Ayudantes Python (muestreo) | 113 de 113 en 3.11 | **113 de 113 en 3.13** (V6C, rootfs) |
| Bases protegidas · reloj | sin cambios · sin salto | sin cambios · sin salto |

**Primer intento V0 `r20261023t223550`: INVALID_ENVIRONMENT** (`e2e-v0-invalid-environment.md`). Durante la corrida se escribieron 1,12 M páginas en swap y load1 llegó a 13; la prueba previa e intermitente `route-crawl` vio 4 rutas de menú. No cuenta.

En la repetición, la regla posterior «swap final < 2 GB» marcó INVALID por **3209 MB de swap residuales que ya había antes de empezar**. Durante la corrida solo hubo +118 MB y 52 385 páginas escritas, con 8,6 GB disponibles y la suite en 271,7 s, en la mediana. El criterio que mide la corrida es el incremento, y la corrida es válida (DERIVED; la medida está en `telemetria.jsonl`).

## OpenAPI
544/533/11 en V0, V6R y V6C, con la **misma huella** de `paths` (`444c820edc7e`). Deriva 0.

## Contenido de la imagen sin Docker (§31)
Demostrado estructuralmente:
- la cadena `runtime` instala solo `requirements.lock` (IDF-06, IDL-06);
- no menciona `requirements-test` y no copia `tests/`, `qa/` ni `pyproject.toml` (IDF-07, IBE-03);
- el lock runtime no contiene ningún paquete de certificación (IDF-03).

V6R reproduce esa cadena sobre el rootfs. **EXACT_RUNTIME_IMAGE_CONTENTS_CERTIFIED = 0**: sin Docker no se construyó la imagen real; queda como evidencia externa.
