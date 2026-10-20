# SPEC 054 · Delta — DEPLOYMENT-PARITY-TEST-INCOMPATIBILITIES (normalización de pruebas)

- **Dueña:** Spec 054. Apoyo: Spec 001.
- **Fecha:** 2026-10-20, rama `develop`, HEAD de partida `41c90f3`.
- **Ruta B:** no hay evidencia Docker de OBS-09.
- **Diagnóstico de origen:** `spec054-certification-environment-drift-diagnosis-delta.md`.
- **Evidencia:** `evidence/deployment-parity-test-normalization/`.
- **Decisiones ratificadas:** OD-CERT-01, OD-CERT-02 y **OD-CERT-03** (PRODUCT_CHANGE = 0, vinculante).

## 1. Specify
OAS-14, ACS-08 y U03/U04 deben pasar en V0 (canónico vigente) y en V2 (paridad de despliegue) conservando exactamente su
intención. Solo cambian pruebas.

## 2. Clarify
**Reproducción previa** (`pre-fix-reproduction.txt`):
- V0: las 4 pasan en SQLite y PostgreSQL.
- V2: OAS-14 y ACS-08 fallan en los dos motores; U03 y U04 fallan en SQLite. Las firmas son las del diagnóstico.

**Ampliación demostrada, autorizada en el brief T3:** U01 (X3) y U02 (C1) llevan la misma aserción inmediata
`checkedout() == 0` tras uvicorn real. En V2 SQLite fallan de forma intermitente: U01 en 5 de 15 ejecuciones y U02 en 1 de
15 (`u01-u02-latent-race.txt`); en V0 nunca. Es la misma deuda, y T3 cubre U01 a U04.

**Búsqueda de patrones análogos:**
- `router.routes` en `test_spec038_float_a/b` recorre el `APIRouter` propio del módulo, no la app: no le afecta.
- `replace(__doc__)` solo aparece en ACS-08.
- Las aserciones `checkedout() == 0` de `test_document_upload_connection_boundary` van durante el análisis detenido o
  por TestClient en proceso, que espera a la app ASGI: no les afecta.

## 3. Design gate

**OAS-14** (`proto_oas` medido en V0 y V2):
- El recorrido genérico por `.routes` que sugería el encargo **no es viable**: `fastapi.routing._IncludedRouter` no
  expone `.routes`, y su `original_router` lleva las rutas **sin** el prefijo de inclusión.
- Diseño:
  - si existe la función **pública** `fastapi.routing.iter_route_contexts` (FastAPI 0.141), las rutas efectivas son
    `(rc.original_route, rc.path, rc.methods)`;
  - si no existe (FastAPI 0.115), `app.routes` plano;
  - sin nombrar clases privadas;
  - guarda contra (método, ruta) duplicados;
  - fallo explícito si una inclusión añade dependencias que la protección no mira.
- Prototipo: en V0 y V2, runtime 544 · duplicados 0 · faltan 0 · sobran 0 · desajustes de protección 0 · dependencias
  de inclusión 0.

**ACS-08:**
- `inspect.getsource` → `textwrap.dedent` → `ast.parse`.
- Si el primer nodo del cuerpo de la función es `Expr(Constant(str))`, se quitan del fuente exactamente sus líneas
  (`lineno`..`end_lineno`).
- La lista de prohibidos y las comprobaciones de `connect_args` y del resto del contrato no cambian.

**U01-U04:**
- SQLAlchemy 2.0.36 despacha el evento `checkin` **antes** de devolver la conexión (`pool/base.py:769-772`), y con
  desbordamiento la cierra y **después** llama a `_dec_overflow()` (`pool/impl.py:144-151`). No hay ningún evento
  posterior al último descuento de `checkedout()`.
- Una espera dirigida solo por eventos no puede observar la convergencia, así que se usa el respaldo autorizado: sondeo
  de la condición explícita «balance exacto **y** `checkedout() == 0`», con plazo de seguridad y diagnóstico completo al
  vencer.
- Producto sin cambio (OD-CERT-03).

## 4. Constitution gate · 5. Tareas
| Tarea | EXECUTOR | MODEL | FILES | DONE_WHEN |
|---|---|---|---|---|
| N01 reproducción, diseño y briefs | CLAUDE | n-a | delta, evidencia | gate |
| T1 OAS-14 | DEEPSEEK | deepseek-v4-pro | `tests/test_openapi_security.py` | verde en V0 y V2 |
| T2 ACS-08 | DEEPSEEK | deepseek-v4-flash | `tests/test_motor_para_hilos.py` | verde en V0 y V2 |
| T3 U01-U04 | DEEPSEEK | deepseek-v4-pro | `tests/test_license_middleware_event_loop.py` | verde en V0 y V2 |
| N02 mutaciones, certificación V0 y V2, convergencia | CLAUDE | n-a | evidencia | gate de cierre |

## 6. Material gate
| Indicador | Valor |
|---|---|
| PRE_FIX_SIGNATURES_MATCH | 1 |
| PRODUCT_CHANGE_NEEDED | 0 |
| OWNER_DECISION_REQUIRED | 0 |
| MATERIAL_OQ | 0 |
| UNKNOWN | 0 |

**Implementación autorizada.**

## 7. Implementación (`orchestration.md`)
DeepSeek escribió los tres cambios: 3 llamadas, $0,003943, 0 reintentos, 0 rechazos. Se aplicaron tal cual.
- **T1:** `_matriz_runtime` usa la función pública `iter_route_contexts` si existe y, si no, `app.routes`. Prohíbe
  duplicados y falla cerrada si una inclusión añade dependencias.
- **T2:** `_codigo_sin_docstring` excluye el docstring por AST.
- **T3:** `_esperar_pool_en_reposo` sondea la condición doble (balance y `checkedout() == 0`) con plazo de seguridad y
  diagnóstico, en U01-U04, y mantiene después las mismas aserciones.

## 8. Pruebas y mutaciones (`directed-tests.txt`, `u01-u04-post-normalization.txt`, `mutations.json`)
- **Módulos completos (65 casos):** 65/0/0 en V0 y V2, SQLite y PostgreSQL, en orden normal e inverso.
- **Pruebas objetivo solas:** todas verdes.
- **U01-U04 tras la normalización, V2 SQLite:** 0 de 15 fallos cada una (antes U01 5/15, U02 1/15, U03 y U04 siempre).
- **Rojo contra HEAD:** las versiones de `41c90f3` fallan en V2 por las causas exactas (`pre-fix-reproduction.txt`).
- **Mutaciones:** 13 significativas · 12 KILLED · 0 SURVIVED · 1 EQUIVALENT (M10, justificada por el orden de eventos de
  SQLAlchemy y la aserción explícita posterior) · 100 % restaurado.

## 9. Certificación (`certification.md`)
| Entorno | SQLite | PostgreSQL | E2E | OpenAPI |
|---|---|---|---|---|
| V0 | 1885/0/1056 ×2 | 2915/0/26 | 284/0/0 | 544/533/11 |
| V2 | 1885/0/1056 | 2915/0/26 | 284/0/0 | 544/533/11, sin deriva de contrato |

## 10. Convergencia
**DEPLOYMENT-PARITY-TEST-INCOMPATIBILITIES = CLOSED / CONVERGED.**
- PRODUCT_CHANGE = 0.
- **RELEASE_DEPLOYMENT_PARITY_CERTIFIED = 0**: siguen abiertas las deudas de artefacto y las rutas fijas del arnés.

**Recomendación para la matriz:** FASTAPI-YIELD-TEARDOWN-AFTER-RESPONSE = **NOT_A_DEFECT / ACCEPTED_FRAMEWORK_SEMANTIC**.
Se cumplen todos los criterios:
- sin fugas, con convergencia medida;
- E2E en verde en V2;
- un cliente lento no prolonga la conexión;
- ninguna Spec ni ningún ADR exige cerrar la sesión antes de la respuesta: `get_db` solo hace `close()` y las
  escrituras se confirman explícitamente en cada endpoint.

No se cierra de forma incidental: queda como recomendación documentada.
