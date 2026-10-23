# SPEC 052 · Delta — PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES

| Campo | Valor |
|---|---|
| Deuda | **PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES** (dueña 052, apoyo 001) |
| Decisiones | OD-IMG-01..06 (frontera runtime/certificación, división de manifiesto y lock autorizada, igualdad del subconjunto runtime, modelo V6R/V6C, autoridad de certificación, validez del anfitrión) · OD-ORCH-01 · OD-CERT-16..18 (no se reabren) |
| Spec cruzada | Spec 054: el arnés E2E arranca el producto con `--python-de-producto` (V6R) y el arnés/ayudantes con V6C, sin tocar los contratos de intérprete cerrados (AIC-06/08, e2ecorrida_25/26) |
| HEAD de entrada | `31297a1` |
| Ruta | Q (sin Docker ni evidencia externa de OBS-09) |
| Evidencia | `evidence/production-image-test-dependencies/` |

## 1. Specify
- **Objetivo:**
  - la imagen de producción (etapa `runtime`, la publicada y por defecto) contiene solo el grafo necesario para ejecutar KONTROL;
  - la certificación usa ese **mismo** grafo, con las mismas versiones, más sus herramientas.
- **Fuera de alcance:**
  - `app/**`, el esquema, las migraciones y el comportamiento del producto;
  - los workflows, que ya publican `target: runtime`;
  - `Dockerfile.central`;
  - el material de Gobierno.

## 2. Clarify (medido; `dependency-inventory.json`)
- **Causa raíz:** `requirements.txt` declaraba pytest, httpx, ruff y mypy junto al runtime; el lock (49) los resolvía con él, la etapa `base` lo instalaba entero y `runtime` hereda de `base`. Además, `dev` hacía `pip install pytest httpx ruff mypy` sin fijar versiones.
- **Uso por el producto:** el AST de `app/`, `central_authority/`, `alembic/` y `scripts/` da **0** imports de las 4 herramientas y de sus 7 transitivas exclusivas. HTTPX_RUNTIME_REQUIRED = 0, y el producto tampoco usa `certifi` ni `ssl`.
- **Grafo de raíces** (`# via`):

  | Raíz | Transitivas exclusivas |
  |---|---|
  | pytest | iniconfig, packaging, pluggy, pygments |
  | httpx | httpcore, certifi |
  | mypy | mypy-extensions |
  | ruff | ninguna |

  Las compartidas (anyio, idna, h11, typing-extensions) se quedan porque tienen raíces de runtime.
- **Candidato compilado con el mismo corte:** runtime de **38** paquetes con **0 cambios de versión**; certificación con `--constraint` = **idéntica** al lock previo (49).
- **Gate de dependencias ocultas:** V6R, sin herramientas, importa los **119** módulos del producto. Pasan `create_app` + lifespan, OpenAPI 544/533/11, JWT, Ed25519, licencias, PDF y MIME, y contra PostgreSQL `alembic upgrade head` con health ready. UNDECLARED_RUNTIME_DEPENDENCIES = 0.
- **Hallazgo previo, no absorbido:** el producto importa `boto3` de forma perezosa y protegida por `ImportError` (proveedor S3 opcional de documentos). Nunca estuvo en el lock; deuda **PRODUCT-OPTIONAL-S3-PROVIDER-DEPENDENCY-UNDECLARED** (dueña 046).

## 3. Plan
| Tarea | Contenido | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | FILES |
|---|---|---|---|---|---|---|
| T1 | `requirements.txt` solo runtime; `requirements-test.txt` (`-r requirements.txt` + 4 herramientas); `dev` instala `requirements-test.lock` con `--no-deps` + `pip check`; README | DEEPSEEK | v4-flash | no | sí | `requirements.txt`, `requirements-test.txt`, `Dockerfile.backend`, `README.md` |
| L | Generar `requirements.lock` y `requirements-test.lock` con la orden canónica de uv; determinismo por `cmp` | CLAUDE (procedimiento mecánico; ficheros generados) | n-a | no | n-a | los dos locks |
| T2 → T2d + T2e | IDL-05 y SDV-08 adaptados a dos locks; `tests/test_dependencias_frontera.py` IDF-01..09 | DEEPSEEK | v4-pro | no | sí (sin las partes JWT) | 3 ficheros de prueba |
| T3 | Arnés E2E: `--python-de-producto`; backend y autoridad (uvicorn) con el intérprete de producto; sonda de producto (herramientas importables, paridad de versiones con el arnés); e2ecorrida_27..31 | DEEPSEEK | v4-pro | no | sí (sin `entorno_de_procesos`) | `qa/e2e_corrida.py`, `tests/test_e2e_corrida.py` |
| T4 | e2ecorrida_27 (herramientas vistas en un solo entorno) y e2ecorrida_32 (`main` pasa la opción) | DEEPSEEK | v4-flash | no | sí | `tests/test_e2e_corrida.py` |

RETRY_MAX: 2 por tarea. T2 agotó sus reintentos y se reclasificó dividiéndola (T2d y T2e).

## 4. Constitution gate y trazabilidad
- P2: autorizado por el encargo (OD-IMG-02 autoriza la división de manifiesto y lock).
- Producto, esquema y migraciones: 0.

| Requisito | Tarea | Prueba |
|---|---|---|
| R1 El manifiesto runtime no declara herramientas de certificación | T1 | IDF-01 |
| R2 El manifiesto de certificación es `-r requirements.txt` + solo sus herramientas | T1 | IDF-02 |
| R3 El lock runtime no contiene nada exclusivo de certificación; el de certificación marca exactamente el runtime con `-c requirements.lock` | T1, L | IDF-03 |
| R4 Todo paquete del runtime tiene la misma versión en certificación (OD-IMG-03) | L | IDF-04; freeze V6R ⊂ V6C; paridad de la E2E V6 |
| R5 El grafo de certificación es reproducible y está anclado al corte y la plataforma del runtime | L | IDF-05; `cmp` al regenerar |
| R6 Cada lock en su etapa; nunca `pip install` de paquetes sueltos; `runtime` no menciona `requirements-test` | T1 | IDF-06, IDL-06 |
| R7 La cadena `runtime` no copia `tests/`, `qa/` ni `pyproject.toml` | — | IDF-07, IBE-03 |
| R8 Todo import de terceros del producto está en el grafo runtime (los opcionales, exactos y protegidos) | — | IDF-08; humo V6R |
| R9 Los suelos de seguridad se cumplen en el lock que corresponde | T2 | IDL-05, SDV-08; pip-audit 0/0 en los dos locks |
| R10 En la E2E, el producto corre en el runtime puro y el arnés en la certificación, con la paridad medida | T3, T4 | e2ecorrida_27..32; manifiesto `interprete_de_producto` |
| R11 Se conservan libmagic, el pin de CA, la base por digest, el usuario no root, HEALTHCHECK, keep-alive y la ausencia de `--reload` | — | IBB-01..06, IMB-01..07, IBE-01..08 |

Trazabilidad: 11 de 11.

## 5. Material gate
| Indicador | Valor |
|---|---|
| ROOT_CAUSE_PROVEN · RUNTIME_CURRENTLY_CONTAINS_TEST_TOOLING | 1 · 1 |
| RUNTIME_REQUIRED · CERTIFICATION_ONLY · QUALITY_ONLY · TRANSITIVE_TEST · UNKNOWN | 38 · 2 · 2 · 7 · 0 |
| HTTPX_RUNTIME_REQUIRED · UNDECLARED_RUNTIME_DEPENDENCIES | 0 · 0 |
| Diseño de manifiestos, locks y etapas listo · RUNTIME_SUBSET_EQUAL_DESIGN_PROVEN | 1 · 1 |
| PRODUCT · SCHEMA · MIGRATION change required | 0 · 0 · 0 |
| OWNER_DECISION_REQUIRED · MATERIAL_OQ · UNKNOWN | 0 · 0 · 0 |

**Implementación autorizada.**

## 6. Cierre (2026-10-24)
- **Rojo contra `31297a1`** (`red-against-head.txt`, árbol aislado con las pruebas nuevas): fallan IDF-01, IDF-03, IDF-06 e IDL-05, y solo por la frontera. Las otras 27 pasan.
- **Dirigidas:** dependencias, imagen y arquitectura 63/63; arnés E2E y AIC 62/62 sobre PostgreSQL (e2ecorrida 01–32, AIC 01–08); ruff y mypy limpios en los ficheros tocados (los 3 errores de mypy de `scanning.py` y de los stubs de `yaml` son previos).
- **Mutaciones:** **25/25** (`mutations.json`). En la primera pasada fueron 23/25: M23 y M25 eran huecos reales, que T4 cierra.
- **Certificación** (`certification.md`):
  - V6R: 38 paquetes, `pip check` PASS, freeze = lock, pip-audit 0/0, 0 herramientas, humo PASS;
  - V6C: 49 paquetes, subconjunto runtime igual (38/38);
  - SQLite V0 y V6C: 1965/0/1070;
  - PostgreSQL V6C: 3009/0/26;
  - E2E V0 **284/0/0**;
  - E2E V6 **284/0/0**, con el backend y la autoridad en V6R (sin herramientas) y el arnés y los ayudantes en V6C (113/113 en 3.13);
  - OpenAPI 544/533/11, con la misma huella en V0, V6R y V6C.
- **No absorbido:**
  - PRODUCT-OPTIONAL-S3-PROVIDER-DEPENDENCY-UNDECLARED (nueva, dueña 046);
  - la recurrencia de E2E-FLAKY-BAJO-CARGA en `route-crawl`, en una corrida V0 inválida por entorno;
  - EXACT_RUNTIME_IMAGE_CONTENTS_CERTIFIED = 0, a la espera de Docker.
- **Estado:** PRODUCTION-IMAGE-CONTAINS-TEST-QUALITY-DEPENDENCIES **CLOSED / CONVERGED**.
