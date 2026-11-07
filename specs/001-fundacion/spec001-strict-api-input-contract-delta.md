# SPEC 001 · Delta — STRICT API INPUT CONTRACT (SHARED-CORE-P0-HARDENING-05)

| Campo | Valor |
|---|---|
| Spec dueña | **001** (núcleo HTTP, contrato de errores, validación transversal de entradas, ADR-020) |
| Afectadas | 003 (Existencias, FR-003-012), 008 (organización: sucursales, almacenes), 013 (maestros y UoM), 006 (tesorería: tasas), 005 (compras: recepciones), 021 (aprobaciones), 041 (notificaciones y tareas) |
| Deudas en alcance | API-QUERY-SILENCIOSA · API-NAIVE-DATETIME-INPUT · UI-BUSQUEDA-MUERTA (Existencias) · API-COMPANY-ID-EN-CONSULTA · E2E-APPROVALS-LIMIT-NO-DECLARADO |
| Base | `49540a6` (develop == origin/develop) |
| Evidencia | `evidence/strict-api-input/` (reconcilia `evidence/undeclared-query-params/` de 2026-09-20) |
| Estado | **IMPLEMENTED — VERIFIED — CONVERGED** (§13–§16) |

## 0. Reconciliación previa

- `spec001-undeclared-query-params-analysis.md` (2026-09-20) se detuvo en CLARIFY: CASO D, sin política. **OD-API-01..07 resuelven aquella OQ.** Su medición, 27 de 224 E2E rotas con una sonda estricta, se vuelve a medir aquí sobre el código actual.
- `spec001-dead-search-analysis.md` dejó OQ-2 (Existencias) como material. Aquella lectura suponía `balances.product_id → products → catalog_items`, dos saltos. Hoy la FK es `catalog_items.id`, un solo salto. Con la regla del encargo (§35: la caja visible debe funcionar si el contrato define sus campos), OQ-2 se resuelve como **PDD-API-11** (§5).
- **Corrección del ciclo 04 (§6 del encargo).** AUDITORIA-PANTALLA-DUPLICADA no tiene decisión de la dueña. Estado correcto: **OPEN · CATEGORY = UX_PRODUCT_DECISION · SEVERITY = LOW · BLOCKING = 0**. Corregido en el delta de 04 y en el roadmap. Este ciclo no fusiona, no renombra ni retira ninguna de las dos pantallas.
- **Gobierno.** PDF releído antes de diseñar (hash `8f86615f…`, sin cambio). Aplican:
  - RNF-GOV-003: fecha civil y UTC conservando la zona;
  - RNF-GOV-006: validación en el backend, sin confiar en la UI;
  - RNF-GOV-015: APIs versionadas, contrato de esquema, **errores deterministas**;
  - GOV-DIG-004: API con contratos de datos.

  No se implementa nada de Gobierno.

## 1. Discovery (medido)

| Inventario | Resultado | Evidencia |
|---|---|---|
| Operaciones `/api/v1/**` | **555**: 227 GET y 328 de escritura, en 421 rutas | `QUERY_PARAMETER_INVENTORY.md` |
| Con parámetros de consulta declarados | 84 operaciones. Todos se declaran en la firma de la ruta: hoy ninguna dependencia declara parámetros de consulta | ídem |
| Lectores manuales (`request.query_params`, `request.url.query`, parseo propio) | **0** → UNCLASSIFIED_MANUAL_QUERY_READERS = 0 | `grep` en `app/` |
| Excepciones necesarias en `/api/v1/**` | **0** | — |
| Entradas `datetime` de petición | **16 INSTANT** (11 en cuerpo, 5 en consulta). Las fechas `date`, los `period` y el CSV de tasas quedan clasificados aparte | `INSTANT_INPUT_INVENTORY.md` |
| Parámetros no declarados que envía la UI | **8** (7 `company_id` y 1 `q`) | `UI_QUERY_PARAMETER_INVENTORY.md` |
| Clientes del repositorio no producto | 4 specs E2E y 2 guiones QA | ídem |

## 2. Reproducción y causa raíz

Detalle en `reproduccion-base.md`.

| Caso | Hoy |
|---|---|
| Barrido GET | 189 aceptan el desconocido en silencio; 37 quedan tras la autorización; 1 no se puede sondear en SQLite (`bool_or`) |
| RQ-01..05: desconocido, vacío, parecido, en mayúsculas, varios, repetido | 200 |
| RQ-06: declarado | 200. Un valor inválido ya da 422 `VALIDATION_ERROR` |
| RQ-07: POST con desconocido en la consulta | El desconocido no se menciona |
| DT-02: consulta sin zona | 200, leído como UTC |
| DT-02d: `resolve` sin zona | Llega a la regla de negocio |
| UI-01: `balances?q=` | 200 con el conjunto entero |

**Causas (medidas):**
- FastAPI solo valida los parámetros que declara la ruta, y KONTROL no tiene mecanismo para los no declarados;
- Pydantic `datetime` acepta valores sin zona, y los ayudantes (`_momento`, `uom`, `approvals`, `identity`) les ponen `UTC` (ADR-020 (e));
- `list_balances` no declara `q`, y la UI lo envía (deriva del contrato UI/API).

## 3. Requisitos

| ID | Requisito | Fuente |
|---|---|---|
| **FR-001-268** | Toda operación `/api/v1/**`, sea cual sea su método, rechaza con **422 `UNKNOWN_QUERY_PARAMETER`** todo nombre de parámetro de consulta que su contrato resuelto (ruta y dependencias) no declare. Vale aunque el valor esté vacío, aunque aparezca una sola vez y aunque el resto de la petición sea válido. La coincidencia es exacta y distingue mayúsculas. Los nombres desconocidos van todos en **una** respuesta, únicos y en orden lexicográfico, sin eco de valores | OD-API-01..04, 06 · RNF-GOV-015 |
| **FR-001-269** | El conjunto admitido **se deriva** del contrato real de FastAPI (`get_flat_dependant` sobre la ruta, con sus dependencias y subdependencias), se precalcula al arrancar y se aplica en **un** mecanismo central:<ul><li>sin listas por ruta;</li><li>sin acceso a la base ni a la red por petición;</li><li>después de las dependencias de la ruta (autenticación, autorización, contexto de empresa) y antes de validar valores y de ejecutar el endpoint;</li><li>cabeceras, ruta, cookies y cuerpo no le afectan;</li><li>QUERY_PARAM_EXEMPTIONS = 0;</li><li>la repetición de un parámetro declarado conserva su semántica actual (OD-API-05)</li></ul> | OD-API-05, 07 · §15–§18, §21, §80 |
| **FR-001-270** | Toda entrada INSTANT (cuerpo, consulta, anidada, elemento de lista) exige un desfase explícito (`Z` o `±HH:MM`) y se normaliza a UTC. Sin zona responde **422 `NAIVE_DATETIME`** cuando todos los errores de la petición son de zona; si hay otros errores, 422 `VALIDATION_ERROR` con el mensaje de zona en su campo. El error nombra el campo, nunca el valor. BUSINESS_DATE (`date`), PERIOD y la regla CSV de tasas no cambian | OD-API-08..10 · ADR-020 · RNF-GOV-003 |
| **FR-001-271** | El frontend envía solo parámetros declarados. Una guarda de arquitectura compara cada consulta del frontend con la instantánea de rutas, que ahora incluye `query` por operación, generada con `qa/fixtures_de_frontend.py` | §34, §43 · RNF-GOV-006 |
| **FR-001-272** (afecta FR-003-012) | `GET /inventory/balances` declara `q`. Su comportamiento:<ul><li>busca por **código o nombre del producto**: subcadena, sin distinguir mayúsculas, en el catálogo de la empresa del contexto;</li><li>se compone por AND con los demás filtros y con la paginación;</li><li>`q` vacío no filtra;</li><li>cada fila publica `product_code` y `product_name`.</li></ul>La pantalla Existencias busca y pagina en el servidor, vuelve a la página 1 al buscar o cambiar el tamaño y muestra el producto por código y nombre | §35, §72 · PDD-API-11 |
| **FR-001-273** | Los errores `UNKNOWN_QUERY_PARAMETER` y `NAIVE_DATETIME` siguen el sobre canónico (`code`, `message`, `field_errors`, `request_id`, `details`), sin traza ni eco de valores, y nunca dan 500 | §32, §57 |

## 4. Decisiones de la dueña aplicadas

OD-API-01..10, ratificadas en el encargo. Resumen:

| Decisión | Contenido |
|---|---|
| 01 | Un desconocido es inválido con valor vacío, de texto nulo, parecido o único |
| 02 | Coincidencia exacta y con mayúsculas |
| 03 | Un solo 422 con todos los nombres ordenados y sin valores |
| 04 | `UNKNOWN_QUERY_PARAMETER` con el sobre canónico (no había un código equivalente ratificado) |
| 05 | No se rediseña la repetición de lo declarado |
| 06 | Cualquier método |
| 07 | Sin ventana de compatibilidad |
| 08 | Un instante sin zona da 422 `NAIVE_DATETIME` (no había un código equivalente) |
| 09 | Ejemplos aceptados con zona; canónico UTC |
| 10 | La regla vale en cualquier ubicación |

## 5. Decisiones de diseño del proyecto (no de la dueña)

**PDD-API-11 · búsqueda de Existencias.**
- `q` busca en `catalog_items.code` y `catalog_items.name` del producto del saldo, con `ilike '%q%'`. Es la misma regla de `GET /maestros/catalogos/items` y de los buscadores de productos.
- Fuentes: el placeholder «Buscar por producto…»; FR-003-012, que pide el filtro por producto; FR-001-065, que pide búsqueda general; y la convención de `name | code`.
- Los comodines `%` y `_` se comportan como en los listados hermanos, sin escaparse; es coherente con ellos y queda anotado.
- Es reversible y no toca el esquema.

## 6. Arquitectura

**AD-1 · mecanismo central.** Fichero nuevo `app/core/query_contract.py`:
- `parametros_de_consulta_declarados(ruta: APIRoute) -> frozenset[str]` toma los alias de `get_flat_dependant(ruta.dependant, skip_repeats=True).query_params`.
- La clase `VerificadorDeConsulta`:
  - guarda `permitidos: frozenset[str]`;
  - su `async __call__(self, request: Request) -> None` calcula `desconocidos = sorted(set(request.query_params.keys()) - permitidos)`;
  - si hay alguno, lanza `KontrolError` con 422.
- `instalar_contrato_de_consulta(app, prefijo)` recorre las `APIRoute` cuya ruta es `prefijo` o empieza por `prefijo + "/"`:
  - calcula `permitidos` ANTES de instalar;
  - **añade al final** de `ruta.dependant.dependencies` la subdependencia `get_parameterless_sub_dependant(depends=Depends(VerificadorDeConsulta(permitidos)), path=ruta.path_format)`;
  - es idempotente: si la última dependencia ya es un verificador, no repite.
- `create_app()` la llama una vez, después del último `include_router`, con `settings.api_prefix`.
- Es asíncrono y no recibe parámetros: no cambia OpenAPI y no usa el pool de hilos.

**AD-2 · orden de validación.** El orden queda así:
1. enrutado (404/405);
2. middleware: request-id y licencia (423 en escrituras con licencia de solo consulta);
3. decodificación del cuerpo JSON (422 si está mal formado);
4. dependencias declaradas, en orden: autenticación, autorización y contexto de empresa (401/403);
5. **verificador** (422 `UNKNOWN_QUERY_PARAMETER`);
6. validación de valores de la consulta y del cuerpo (422 `VALIDATION_ERROR` / `NAIVE_DATETIME`);
7. endpoint (reglas de negocio).

Consecuencias:
- Quien no está autenticado recibe 401 antes que 422, así que el contrato de consulta no se convierte en un oráculo para anónimos.
- Si la autorización está dentro del cuerpo del endpoint, un autenticado recibe 422 antes que 403. Igual que ya pasa con `VALIDATION_ERROR`: el 422 solo dice que el nombre no está en el contrato publicado, nunca nada de un recurso.
- `UNKNOWN_QUERY_PARAMETER` va antes que los errores de valor, de forma determinista.

**AD-3 · sobre de `UNKNOWN_QUERY_PARAMETER`.**

```json
{"code": "UNKNOWN_QUERY_PARAMETER",
 "message": "La consulta incluye parámetros que esta operación no admite.",
 "field_errors": {"query.<nombre>": ["Parámetro no admitido por esta operación."]},
 "request_id": "…",
 "details": {"unknown_query_parameters": ["<nombre>", "…"]}}
```

Las claves `query.<nombre>` siguen la forma de los errores de consulta existentes (`query.page_size`). No se devuelve ningún valor.

**AD-4 · instante de entrada.** En `app/shared/clock.py`, el núcleo temporal (ADR-020 (c)):
- se define `InstanteDeEntrada = Annotated[AwareDatetime, AfterValidator(<a UTC>)]`, primitiva canónica de Pydantic;
- se aplica a las 16 entradas INSTANT;
- su OpenAPI no cambia (`format: date-time`).

El manejador de `RequestValidationError` (`app/core/errors.py`):
- traduce los errores de tipo `timezone_aware` al mensaje «Indique la zona horaria (Z o ±HH:MM).»;
- usa `code = "NAIVE_DATETIME"` si TODOS los errores son de ese tipo, con el mensaje «La fecha y hora debe indicar su zona horaria.»;
- si hay de otros tipos, usa `VALIDATION_ERROR`;
- nunca usa `input` (el valor recibido).

Los ayudantes que ponían UTC a los valores sin zona se quedan: protegen las lecturas de SQLite y las llamadas internas. A la API ya no le llega ningún valor sin zona.

**AD-5 · ADR-020 (e), enmienda.** «En la API, un instante sin zona se rechaza con 422 `NAIVE_DATETIME`. La importación CSV de tasas conserva su regla de hora de pared de Caracas.» La enmienda queda registrada en el propio ADR con fecha y ciclo.

**AD-6 · Existencias.**
- Backend: si llega `q`, `list_balances` hace join con `CatalogItem` (`id == product_id`, `company_id == ctx.company_id`) y filtra `name ilike | code ilike`. Cada item añade `product_code` y `product_name`.
- `balance_dict` no cambia: los demás consumidores conservan su forma.
- La pantalla sigue el patrón de Empresas:
  - estado `pagina` (base 0) y `tamano`, enviados como `page`/`page_size` (base 1);
  - `Pagination` solo cuando `total` > 10;
  - `buscar` reinicia la página;
  - columna «Producto» = «código — nombre»;
  - error: el `message` de `ApiError` para un 4xx; si no, el texto genérico.

**AD-7 · guarda de frontend.**
- La instantánea `openapi-routes.json` añade `"query": [...]` a cada operación, desde la misma función `parametros_de_consulta_declarados`, y `test_frontend_fixtures.py` la mantiene fresca.
- Prueba vitest nueva `src/tests/query-contract.test.ts` con el compilador de TypeScript:
  - recorre todo `src` que no sea prueba;
  - resuelve el primer argumento de cada `apiFetch` (literal, plantilla, `+`, condicional, identificador `const` del fichero, `URLSearchParams` con `{...}`, `.set` o `.append`);
  - deduce la ruta y los nombres, y exige `nombres ⊆ query(ruta, método)`;
  - en los usos JSX `searchUrl="…"` de `AsyncCombobox`, exige `q`, `page_size` y, si hay `itemType`, `item_type`;
  - una llamada con consulta que no se pueda resolver hace fallar la prueba, salvo que esté en una lista cerrada con motivo; se prefiere una lista vacía.

**AD-8 · `company_id` obsoleto.** Las 7 llamadas dejan de enviarlo y construyen la consulta con `URLSearchParams` cuando quedan otros parámetros. La clave de caché conserva la empresa.

**AD-9 · clientes no producto.** Se corrigen las 4 specs E2E y los 2 guiones QA (quitar `company_id`; `limit` → `page_size`). Las pruebas del backend que fallen por enviar parámetros no declarados o instantes sin zona se corrigen en la petición.

**Base de datos:** sin migración. Alembic sigue en 0061.

**Auditoría:** el 422 de validación no se audita (§87, catálogo de 04). No hay acciones nuevas.

## 7. Seguridad (amenazas → control → prueba)

| # | Amenaza | Control | Prueba |
|---|---|---|---|
| T1 | Una errata cambia el comportamiento en silencio | AD-1 | Q-04/05 |
| T2 | Se ignora un filtro de seguridad | AD-1 (cualquier nombre) | N-01 |
| T3 | El cliente cree que el filtro se aplicó | 422 explícito | Q-01 |
| T4 | Se ignora un selector de tenant o empresa desconocido (`tenant_id`, `company_id`) | AD-1 | N-02 |
| T5 | Contrabando por nombres repetidos | conjunto de nombres | Q-07 |
| T6 | Se esquiva el control con un lector manual | 0 lectores; guarda | GUARD-Q-03 |
| T7 | Se rechaza por error un parámetro de una dependencia | `get_flat_dependant` | Q-08 (app sintética con subdependencia anidada) |
| T8 | Una exención demasiado amplia | 0 exenciones; guarda estructural | GUARD-Q-01 |
| T9 | Un instante sin zona leído en otra zona | AD-4 | D-01..03 |
| T10 | Desplazamiento de borde de día | normalización a UTC | D-05/06 |
| T11 | Instante sin zona anidado o en una lista | tipo común | D-03/D-09 |
| T12 | Búsqueda muerta en la UI | AD-6 y la guarda | E-01..04, F-guard |
| T13 | El error devuelve los valores enviados | sin `input` ni valores | Q-06, D-07 |
| T14 | La validación acaba en 500 | KontrolError y manejador | N-08 |
| T15 | Saltarse la UI llamando a la API directamente | backend autoritativo | QUERY-422-E2E-01/04 |
| T16 | El contrato de consulta como oráculo para anónimos | AD-2 | Q-10 |

## 8. Pantallas y formularios (API_CONTRACT_SCREEN_MATRIX)

| SCREEN_ID | Pantalla | Cambio | Riesgo de 422 |
|---|---|---|---|
| SC-01 | Inventario › Existencias | `q` real, paginación y producto legible | Ninguno |
| SC-02 | Organización › Sucursales, Almacenes, Establecimientos | Sin `company_id` | Ninguno |
| SC-03 | Aprobaciones › Bandeja, Políticas, Delegaciones e Historial | Sin `company_id` | Ninguno |
| SC-04 | Tesorería › Tasas (`effective_at`, CSV) | Ninguno: envía `Z`; CSV sin cambios | NAIVE_DATETIME imposible desde la UI |
| SC-05 | Compras › Recepciones (`unloading_scheduled_at`) | Ninguno: envía `Z` | ídem |
| SC-06 | Aprobaciones › Delegaciones (`valid_to`) | Ninguno: `finDelDiaDeNegocio` → `Z` | ídem |
| SC-07 | Notificaciones y Tareas (filtros `created_*` y `due_*`) | La UI no envía esos filtros | — |

La puerta completa, los contratos de campo de filtro (§39) y de instante (§40), y el análisis de huecos (§85) están en `evidence/strict-api-input/screen-form-completeness.md`, que se rellena al verificar.

## 9. Tareas

Todas: RETRY_MAX = 2, EGRESS_SAFE = sí, DeepSeek redacta el código y Claude audita.

| Tarea | Modelo | SEC | Ficheros | Prueba | DONE_WHEN |
|---|---|---|---|---|---|
| C05-T01 rojo de consulta | pro | sí | `tests/test_strict_query_contract.py` | ella misma | Rojo atribuible: los 422 esperados no llegan; el control de lo declarado pasa |
| C05-T02 mecanismo | pro | sí | `app/core/query_contract.py`, `app/main.py`, `app/core/errors.py` (si hace falta) | T01 | T01 en verde; ruff y mypy sin errores nuevos |
| C05-T03 rojo de instantes | pro | sí | `tests/test_naive_datetime_input.py` | ella misma | Rojo atribuible; los controles con zona y de fecha de negocio pasan |
| C05-T04 instante | pro | sí | `app/shared/clock.py`, `app/core/errors.py`, los 7 módulos de API del inventario | T03 | T03 en verde |
| C05-T05 rojo y búsqueda de Existencias (backend) | flash/pro | no | `tests/test_inventory_balances_search.py`, `app/modules/inventory/api.py` | ella misma | Rojo → verde |
| C05-T06 pantalla de Existencias | pro | no | `ExistenciasPage.tsx` y su prueba vitest | vitest | Filtra, pagina, limpia y muestra el producto |
| C05-T07 `company_id` obsoleto en la UI | flash | no | 7 ficheros de producto y sus pruebas | vitest | Ninguna URL lleva `company_id` en esas rutas |
| C05-T08 instantánea con `query` | flash | no | `qa/fixtures_de_frontend.py` | `test_frontend_fixtures.py` | Fixtures regeneradas con el generador |
| C05-T09 guarda de frontend | pro | sí | `src/tests/query-contract.test.ts` | ella misma | Verde sobre el árbol corregido; roja si vuelve `q` o `company_id` |
| C05-T10 clientes E2E y QA | flash | no | 4 specs y 2 guiones | sintaxis y E2E | 0 parámetros no declarados |
| C05-T11 pruebas del backend afectadas | flash/pro | no | Según la medición | Suite completa | 0 fallos |
| C05-T12 QUERY-422-E2E y EXISTENCIAS-E2E | pro | no | `e2e/strict-api-input.spec.ts` | E2E ×3 | Verde en 3 navegadores |
| C05-T13 contratos | flash | no | `contracts/error-contract.md`, `contracts/api-contracts.md` | revisión | Códigos y reglas publicados |
| C05-ADR (Claude, diseño) | n-a | — | `adr/ADR-020.md` (e) | revisión | Enmienda registrada |

## 10. Mutaciones previstas (campaña 05)

1. Desactivar el verificador.
2. Aceptar un desconocido vacío.
3. Comparar sin mayúsculas.
4. Ignorar los parámetros de subdependencias.
5. Exención arbitraria.
6. Solo GET.
7. Saltarse POST/PATCH.
8. Eco de valores en `field_errors`.
9. Instante sin zona como UTC.
10. Validar solo cuerpo.
11. Validar solo consulta.
12. Saltarse los anidados.
13. Rechazar BUSINESS_DATE.
14. Romper la regla CSV de tasas.
15. Volver a enviar `q` no declarado.
16. Desactivar la guarda.

Más:
- `q` sin `company_id` en el join;
- `q` que no se compone con los filtros;
- página que no se reinicia;
- verificador antes de la autenticación;
- desconocidos sin ordenar.

## 11. Puerta de la Constitución

| Condición | Valor |
|---|---|
| QUERY_PARAMETER_INVENTORY_COMPLETE · INSTANT_INPUT_INVENTORY_COMPLETE · UI_QUERY_PARAMETER_INVENTORY_COMPLETE | 1 · 1 · 1 |
| OWNER_DECISIONS_APPLIED · ERROR_CONTRACT_DEFINED · ARCHITECTURE_DEFINED | 1 · 1 · 1 |
| SCREEN_FORM_INVENTORY_COMPLETE · TRACEABILITY_READY | 1 · 1 |
| MATERIAL_OQ · UNKNOWN · CONTRADICTIONS · CRITICAL · BLOCKER | 0 · 0 · 0 · 0 · 0 |

**GATE PASS.** El encargo autoriza `implement` para SHARED-CORE-P0-HARDENING-05.

## 12. Trazabilidad

| Requisito de ingeniería | Requisito del núcleo | Control | Prueba | Evidencia |
|---|---|---|---|---|
| RNF-GOV-015 (contrato de esquema, errores deterministas) | FR-001-268, 269, 273 | AD-1..3 | Q-*, GUARD-Q-*, N-* | `rojo.md`, `mutaciones.md` |
| RNF-GOV-003 (tiempo) | FR-001-270 | AD-4, AD-5 | D-* | ídem |
| RNF-GOV-006 (validación en el backend) | FR-001-268..271 | AD-1, AD-4, AD-7 | GUARD-Q-02, F-guard, QUERY-422-E2E | `e2e.md` |
| GOV-DIG-004 (contratos de datos) | FR-001-269, 271 | instantánea con `query` | `test_frontend_fixtures` | fixtures |
| FR-003-012 y FR-001-065 | FR-001-272 | AD-6 | E-*, EXISTENCIAS-E2E | ídem |

## 13. Hallazgo en ejecución: búsqueda muerta del Rubro (PDD-API-12)

La guarda de frontend (AD-7) encontró una deriva que el inventario manual no veía: el combo «Rubro» de Producto nuevo enviaba `q` y `page_size` a `/maestros/catalogos/taxonomia`, que no los declara y devuelve un array, no el sobre que espera `AsyncCombobox`. El combo nunca listó opciones.

**PDD-API-12:** ruta hermana `GET /maestros/catalogos/taxonomia/search`, con el mismo contrato que `/catalogos/items/search` (FR-002-043):
- `q` busca por nombre o código;
- solo nodos ACTIVE de la empresa o globales;
- devuelve el sobre paginado.

`list_taxonomy` no cambia, porque la pantalla Catálogos consume su array. OpenAPI pasa de 421 a 422 rutas.

**Ajuste del inventario de §1:** UI_UNDECLARED_PARAMS_SENT_BEFORE = 9 (7 `company_id`, el `q` de Existencias y `q`/`page_size` del Rubro). AFTER = 0.

## 14. Resultados

| Verificación | Resultado | Corrida |
|---|---|---|
| Dirigidas (consulta, instantes, Existencias, taxonomía) | 18 + 13 + 8 + 7 PASS | — |
| PostgreSQL completo con analizador | **3731/0** (18 omitidas, igual que la línea base) | `r20261028t163130p343337n0da7ba` |
| SQLite completo con analizador | **2649/0** (1100 omitidas) | `r20261028t163130p343339n5036a7` |
| vitest · tsc · eslint · build | **701/701** · 0 · 0 · OK | — |
| ruff · mypy | Limpio · 154 = 154 (0 nuevos) | — |
| Alembic | 0061 (sin migración) | — |
| OpenAPI | 421 → 422; solo cambia `GET /inventory/balances` (`q`); deriva sin explicar 0 | — |
| Mutaciones 05 | **23/23** muertas, 0 equivalentes, 0 supervivientes | `mutaciones.md` |
| QUERY-422 · EXISTENCIAS · RUBRO-E2E (×3 navegadores) | **18/18** | `r20261028t170855p835687n94b04d` |
| Regresiones (22 specs; Firefox, WebKit y también Chromium) | 469/471. Las 2 de Chromium no son atribuibles y dan 16/16 en la repetición | `r20261028t171009p840212n1d80ae`, `r20261028t171857p896287n0a4e1f` |
| Canónica | **382/382** en la tercera corrida (ver §15) | `r20261028t173918p966491n36d340` |
| Base tras la E2E | **PASS** | `r20261028t174637p992699n9dff53` |

## 15. Corridas E2E no verdes, con causa

1. **T12 r1:** EXISTENCIAS-E2E-01 esperaba una petición al limpiar, pero `staleTime: 30 000` la sirve de caché. Error del encargo de Claude, corregido en T12 r2. No es una repetición del mismo código.
2. **Regresiones:**
   - colisión TOTP conocida en auditoria-sobre (E2E-TOTP-PASO-COMPARTIDO);
   - mfa 08: la fila del usuario no aparece bajo la carga de 3 proyectos. Usa `GET /users`, sin parámetros, y pasó en Firefox y WebKit.

   Las dos dieron 16/16 en una repetición aislada sin cambios.
3. **Canónica 1:** `n6-multicompany` (caché) se quedó esperando `/auth/refresh` al entrar como `uab`, y con ella no corrieron las 4 dependientes de licencias. Diagnóstico:
   - pasa aislada en los 3 navegadores;
   - en la misma spec, «cada pestaña conserva su empresa» falla en Firefox y WebKit **también en HEAD 49540a6**, medido en un worktree desacoplado que ya se retiró. Es preexistente: deuda E2E-N6-PESTANAS-FF-WK.

   El paso de inicio de sesión con dos empresas es intermitente: deuda E2E-N6-ENTRAR-UAB-INTERMITENTE. Hubo una repetición, registrada.
4. **Canónica 2:** n6 pasa. Falla la colisión TOTP exacta (admin_w2) y no corren las 4 dependientes. Se usó la única repetición que permite §75.
5. **Canónica 3:** 382/382.

## 16. Trazabilidad final y convergencia

| Requisito | Control | Prueba | Mutante | Evidencia |
|---|---|---|---|---|
| FR-001-268 | AD-1, AD-3 | Q-01..12, N-01/02, GUARD-Q-02, QUERY-422-E2E-01/02 | Q01, Q02, Q03, Q06, Q07, Q08, Q10 | `rojo.md`, `mutaciones.md` |
| FR-001-269 | AD-1, AD-2 | Q-13, GUARD-Q-01, GUARD-Q-03, Q-10 | Q04, Q05, Q09 | ídem |
| FR-001-270 | AD-4, AD-5 | D-01..12, GUARD-D-01, QUERY-422-E2E-03 | D01..D07 | ídem |
| FR-001-271 | AD-7, AD-8 | QC-01..10, EXS-F-07, QUERY-422-E2E-04 | U01, U03 | ídem |
| FR-001-272 | AD-6, PDD-API-11 | E-01..08, EXS-F-01..07, EXISTENCIAS-E2E-01 | E01, E02, U02 | ídem |
| PDD-API-12 | §13 | T-01..07, RUBRO-E2E-01 | T01 | ídem |
| FR-001-273 | AD-3, AD-4 | Q-06, D-07, N-08 (sin 500 en el barrido) | Q08 | ídem |

**Convergencia (equivalente explícito):**
- Los 6 FR y las 2 PDD tienen control, prueba en rojo y en verde, mutante muerto y evidencia.
- Ninguna tarea sin cumplir, ninguna contradicción con la Constitución y ningún trabajo no pedido sin justificar: la ruta de taxonomía queda justificada en §13.
- **CONVERGED.**

## 17. Compatibilidad con el runtime del lock (2026-11-07)

Ciclos P0-RUNTIME-LOCK-API-BOOT-FAILURE-16 y P0-RUNTIME-LOCK-OPERATIONS-CATALOG-17. FastAPI 0.141.1, Starlette 1.9.0, Pydantic 2.10.4. Evidencia: `evidence/strict-api-runtime-compatibility/`.

| Fase | P0-A `REMOVED_FASTAPI_INTERNAL_DEPENDENCY_API` | P0-B `LAZY_INCLUDED_ROUTER_CONSUMERS` |
|---|---|---|
| DISCOVER | `query_contract.py` importaba `get_flat_dependant` | 1 consumidor de producto, 1 de QA y 10 ficheros de prueba recorrían `app.routes` |
| REQUIREMENTS | FR-001-268 y FR-001-269: 422 ante parámetros no declarados en toda ruta | Catálogo de operaciones completo: capacidades, alcance y métodos reales (Spec 003, ADR-018) |
| REPRODUCTION | `import app.main`: RC 1, `ImportError` | `catalogo_de_operaciones(app)` = 1 operación; 688 esperadas |
| ROOT_CAUSE | FastAPI eliminó el ayudante interno | `app.routes` = 38 `_IncludedRouter`, 4 `Route`, 1 `APIRoute`; cada ruta incluida se sirve desde su contexto efectivo |
| DESIGN | Recorrer el árbol `Dependant` y añadir el verificador a `contexto.dependant` | `app/core/route_contexts.py::contextos_de_api`: una sola visión de las rutas efectivas |
| CONSTITUTION GATE | Sin cambio de contrato, esquema ni dependencias | Igual: sin migración, sin cambio de OpenAPI |
| CHECKLIST | Arranque, 422, autorización antes del verificador, sin eco | Catálogo, capacidades, alcances, métodos, anidados, Government, fixtures |
| TASKS | P0_ATTEMPT_1, P0_RETRY_1 | P0-B1, P0-B2, P0-B3 |
| ANALYZE | Sin contradicciones | Sin contradicciones. `MATERIAL OQ = 0` |
| TRACEABILITY | `test_strict_query_runtime_lock.py`, GUARD-Q-01/02 | `test_operations_catalog_runtime_lock.py`, `test_frontend_fixtures.py`, `test_ui_authority_api.py` |
| AUTHORIZATION | Encargo 16 | Encargo 17 |
| IMPLEMENT | Aplicado | Aplicado |

**`ROUTE_CONTEXT_HELPER_OWNER = app/core/route_contexts.py` (opción B).** Hay dos consumidores de producto (`query_contract`, `operaciones`) y uno de QA. `operaciones` no debe depender del contrato de consulta para recorrer rutas. Una guarda estática impide volver a recorrer `app.routes` en `app/` o `qa/`.

**Excepción declarada:** `get_parameterless_sub_dependant` sigue siendo API interna de FastAPI. Se usa para construir el Dependant del verificador; la versión está fijada por el lock.
