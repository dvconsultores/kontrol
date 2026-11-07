# Contrato estricto de consulta en el runtime del lock

Medido el 2026-11-07 en `.venv` con Python 3.13.5 y `requirements-test.lock`: FastAPI 0.141.1, Starlette 1.9.0, Pydantic 2.10.4.

## RED
`hasattr(utils, "get_flat_dependant") = False`. `import app.main`: RC 1, `ImportError`.

## Causa
1. `REMOVED_FASTAPI_INTERNAL_DEPENDENCY_API`.
2. Inclusión perezosa: `app.routes` tiene 38 `_IncludedRouter`, 4 `Route` y 1 `APIRoute`. Cada ruta incluida se sirve desde un contexto efectivo reconstruido. Devolver el arranque sin más dejaba `GET /api/v1/health/live?zz=1` en 200.

## Corrección
`parametros_de_consulta_declarados` recorre el árbol `Dependant`. `instalar_contrato_de_consulta` usa `iter_route_contexts` (público, el mismo que usa el OpenAPI de FastAPI) y añade el verificador a `contexto.dependant`, último en dependencias. `route.dependencies` se descartó: correría antes de la autenticación.

API interna que permanece: `get_parameterless_sub_dependant`. WHY_REQUIRED: construye el Dependant del verificador. VERSION_CONTRACT: firma `(*, depends, path)` de FastAPI 0.141.1. FAILURE_MODE: `ImportError` o `TypeError` al arrancar, fallo cerrado. TEST_GUARD: `test_arranque_con_runtime_lock`, GUARD-Q-01.

## Verde
`import app.main` RC 0. `/api/v1/health/live` 200; `?zz=1` 422 `UNKNOWN_QUERY_PARAMETER`. `test_strict_query_contract.py` + `test_strict_query_runtime_lock.py`: 32/32, con GUARD-Q-01 (≥400 rutas) y GUARD-Q-02 (barrido).

Mutaciones: 9 ejecutadas, 9 muertas, 0 supervivientes (recorrido, primer nivel, alias, desconocidos, no instalar, solo raíz, duplicar, volver a `app.routes`, fuera del prefijo).

OpenAPI: 688 operaciones frente a 688 de `openapi-routes.json`, sin altas ni bajas.

# P0-B · consumidores de la inclusión perezosa

Medido el 2026-11-07, tras integrar `public-upstream/develop` hasta `cca6b73`.

## RED
`catalogo_de_operaciones(app)` = 1 operación. `iter_route_contexts` da 688 contextos de API y 688 operaciones únicas: POST 351, GET 286, PATCH 27, DELETE 19, PUT 5.

## Consumidores
| Fichero | Clase | Efecto antes del arreglo | Acción |
|---|---|---|---|
| `app/core/operaciones.py` | PRODUCT | Catálogo de 1 operación | Corregido |
| `app/core/query_contract.py` | PRODUCT | Ya correcto (P0-A) | Pasa por el ayudante común |
| `qa/fixtures_de_frontend.py` | QA | 1 ruta en la instantánea | Corregido |
| `test_mfa_session_authority.py`, `test_mfa_management.py`, `test_iso_guardas.py`, `test_naive_datetime_input.py` | TEST | Fallo | Corregido |
| `test_mfa_no_bypass.py` | TEST | Verde en vacío | Corregido |
| `test_iso_barridos.py` | TEST | Vacío en PostgreSQL; omitido en SQLite | Corregido |
| `test_gov0_ente.py`, `test_gov0_estructura.py`, `test_gov0_cargos.py`, `test_gov_doc02_actos.py` | TEST | Fallo en PostgreSQL; omitidos en SQLite | Corregido sin cambiar aserciones |
| `test_openapi_security.py` | FALSE_POSITIVE | Ya usa `iter_route_contexts` | Sin cambio |
| `test_spec038_float_a.py`, `test_spec038_float_b.py` | FALSE_POSITIVE | Leen `router.routes` de un router propio | Sin cambio |
| `test_strict_query_contract.py:335`, `test_strict_query_runtime_lock.py:114,148` | FALSE_POSITIVE | Mini app con rutas directas | Sin cambio |

## Verde
`import app.main` RC 0. Catálogo 688: COMPANY 613, GLOBAL 64, TENANT 11. Coincide con OpenAPI.

Instantáneas generadas en memoria: `openapi-routes.json` y `operaciones.json` **idénticas byte a byte** a las versionadas. No se regeneró ninguna, y el cambio de P1 en `6fa6d4f` queda intacto.

Suite SQLite completa, con ClamAV real (`qa/clamav_qa.py provisionar` RC 0; motor 1.4.3): **4621 recogidas, 2826 aprobadas, 0 fallidas, 0 errores, 1795 omitidas**, 1059 s. Los 27 fallos `SCAN_FAILED` anteriores desaparecen con el analizador. La corrida se hizo antes de integrar `cca6b73`, de Government, que cambia documentación y una especificación Playwright (`e2e/gobierno-cierres.spec.ts`), sin código de backend ni de frontend.

Mutaciones P0-B: 12 ejecutadas, 12 muertas. M3 (dependant original) sobrevivió en la primera pasada y murió tras añadir `test_dependencia_de_inclusion_aporta_capacidad`.

ruff: sin avisos. mypy `app`: 156 antes, 154 después, y las dos bajas son de ficheros tocados. OpenAPI: 688 = 688; ni altas ni bajas.

## No ejecutado
PostgreSQL: `NOT_EXECUTED_ENVIRONMENT_UNAVAILABLE`. Los guardas GS-25, GC-24 y GA-27 y el bucle de GE-11 se omiten en SQLite: su parte de rutas se ejecutó directamente y pasa; su parte HTTP no. Los barridos de `test_iso_barridos.py` no se han ejecutado sobre las 613 rutas de empresa: hasta ahora pasaban en vacío en este runtime y **son la primera prueba pendiente en PostgreSQL**.
