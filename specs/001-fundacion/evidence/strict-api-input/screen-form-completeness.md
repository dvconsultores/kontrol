# STRICT API INPUT (05) · puerta de pantallas y formularios (2026-10-28)

## API_CONTRACT_SCREEN_MATRIX y puerta por pantalla (§37–§38)

| Campo | SC-01 Inventario › Existencias | SC-02 Organización › Sucursales · Almacenes · Establecimientos | SC-03 Aprobaciones › Bandeja · Políticas · Delegaciones · Historial | SC-04 Maestros › Producto nuevo (Rubro) | SC-05 Tesorería › Tasas · Compras › Recepciones · Delegaciones (instantes) |
|---|---|---|---|---|---|
| PROCESS_ID | Consulta de existencias (FR-003-012) | Estructura organizativa | Flujo de aprobaciones | Alta de producto (FR-002-043) | Registro de tasa, programación de descarga, vigencia de delegación |
| BUSINESS_PURPOSE | Saber cuánto hay de un producto | Mantener la estructura | Decidir y delegar | Clasificar el producto en su rubro | Fijar un momento absoluto |
| PRIMARY_USER_GOAL | Encontrar el saldo de un producto | Ver y editar sucursales y almacenes | Atender la bandeja | Elegir un rubro | Indicar el instante de vigencia o de descarga |
| ACTORS | `inventario:view` | `organization:*` | `aprobaciones:*` | `maestros:create` | `tesoreria:create`, `compras:*`, `aprobaciones:delegate` |
| FIELDS / FILTERS | Caja «Buscar por producto» (`q`), paginación | Sin filtros nuevos | Tipo de proceso y «vencidas» (bandeja) | Combo «Buscar rubro» (`q`, `page_size`) | `datetime-local` de Caracas y fecha «hasta» |
| QUERY_PARAMS | `q`, `page`, `page_size` (declarados) | Ninguno (se retiró `company_id`) | `process_type` y `only_overdue`; `document_type` y `document_id` (sin `company_id`) | `q`, `page_size` → `/catalogos/taxonomia/search` (nueva) | — |
| ACTIONS | Buscar, limpiar, paginar, cambiar el tamaño | Las existentes | Las existentes | Buscar y elegir | Guardar |
| STATES | Cargando, vacío (con texto según haya búsqueda o no), error 4xx con el mensaje seguro del servidor, error de red genérico | Sin cambios | Sin cambios | «Sin resultados», opciones | Sin cambios |
| VALIDATIONS | `page_size` ≤ 100 (servidor) | — | — | — | Instante con zona: la UI envía `Z` siempre (`instanteDesdeHoraDeCaracas`, `finDelDiaDeNegocio`) |
| PERMISSIONS / BACKEND_AUTHORIZATION | `require_permission("inventario","view")` y contexto | Sin cambios | Sin cambios | `require_permission("maestros","view")` | Sin cambios |
| API_CONTRACT | Sobre `{items,total,page,page_size}`; item con `product_code` y `product_name` | Sin cambios | Sin cambios | Sobre paginado `{items:[{id,code,name,level}],…}` | `format: date-time`; 422 `NAIVE_DATETIME` |
| ERROR_HANDLING | `ApiError` 4xx → `message` del servidor; otro → «No fue posible cargar las existencias.» | El existente | El existente | El existente del combo | `ApiError.message` del servidor |
| DB_API_UI_PARITY | `catalog_items.code` y `catalog_items.name` → `product_code` y `product_name` → «CÓDIGO — Nombre» | — | — | `taxonomy_nodes` ACTIVE → opción | Instante → UTC → presentación en Caracas |
| SECURITY | Join limitado a la empresa del contexto; sin eco de valores | Empresa por cabecera | Empresa por cabecera | Universo de la empresa y globales | Ambigüedad rechazada en el backend |
| RESPONSIVE | 320 px sin desbordamiento (EXISTENCIAS-E2E-01) | Sin cambios (deuda SHELL-SIDEBAR-NOT-RESPONSIVE aparte) | Sin cambios | Sin cambios | Sin cambios |
| ACCESSIBILITY | Etiqueta accesible «Buscar por producto», botón «Limpiar búsqueda», axe sin violaciones graves | — | — | `role=combobox` con nombre y `role=option` | — |
| E2E | EXISTENCIAS-E2E-01 (×3) | QUERY-422-E2E-04 (×3) | QUERY-422-E2E-04 (×3) y approvals.spec | RUBRO-E2E-01 (×3) | QUERY-422-E2E-03 (API) y regresiones rates/receipts |
| STATUS | **PASS** | **PASS** | **PASS** | **PASS** | **PASS** |

## Contratos de campo de filtro (§39)

| Campo | F-01 Existencias `q` | F-02 Existencias `page`/`page_size` | F-03 Rubro `q` |
|---|---|---|---|
| LABEL | «Buscar por producto» | Paginación («Registros por página», siguiente y anterior) | «Buscar rubro» |
| BUSINESS_MEANING | Código o nombre del producto del saldo | Página del listado | Nombre o código del nodo de taxonomía |
| API_PARAMETER | `q` (declarado) | `page`, `page_size` | `q`, `page_size` |
| TYPE | Texto | Entero | Texto |
| REQUIRED | No | No | No |
| EMPTY_BEHAVIOR | Vacío: sin filtro (no se envía) | — | Vacío: lista los primeros 20 activos |
| DEFAULT | «» | 1 / 10 | «» |
| VALIDATION | — | 1 ≤ `page_size` ≤ 100 | — |
| SEARCH_FIELDS | `catalog_items.code`, `catalog_items.name` (ilike, sin mayúsculas) | — | `taxonomy_nodes.code`, `taxonomy_nodes.name` |
| SERVER_SIDE | Sí | Sí | Sí |
| DEBOUNCE | No (como Empresas) | — | 300 ms (componente) |
| PAGINATION_INTERACTION | Buscar o cambiar el tamaño vuelve a la página 1 | — | `page_size=20` fijo |
| RESET_BEHAVIOR | «Limpiar búsqueda» restaura el conjunto | — | Borrar el texto |
| ERROR | Mensaje seguro del servidor | — | Estado del combo |
| HELP_TEXT | Placeholder «Buscar por producto…» | — | «Búsqueda asíncrona en el catálogo.» |

## Contratos de campo INSTANT (§40)

| FIELD_ID | Etiqueta | UI_INPUT_TYPE | API_TYPE / OPENAPI | TIMEZONE_EXPECTATION | USER_SEES_ZONE | NORMALIZATION | DB | TEST |
|---|---|---|---|---|---|---|---|---|
| I-01 tasa `effective_at` | Vigencia | `datetime-local` (hora de Caracas) | `InstanteDeEntrada` / `date-time` | Caracas → `toISOString()` (Z) | Sí: la pantalla dice «hora de Caracas» (ciclo 03) | UTC | `timestamptz` | DT-I, rates.spec |
| I-02 recepción `unloading_scheduled_at` | Descarga programada | `datetime-local` | ídem | ídem | ídem (03) | UTC | `timestamptz` | receipts.spec |
| I-03 delegación `valid_to` | Hasta | `type=date` → `finDelDiaDeNegocio` | ídem | Final del día de Caracas (Z) | Fecha de negocio | UTC | `timestamptz` | D-01, D-06 |
| I-04..16 resto de instantes de la API | — | La UI no los envía, o envía `null` | ídem | — | — | UTC | `timestamptz` | GUARD-D-01 |

Ninguna pantalla permite escribir una hora sin establecer su zona: los `datetime-local` se interpretan explícitamente como hora de Caracas y viajan con `Z`.

## Análisis de huecos (§85)

| Pantalla | Hueco | Clasificación |
|---|---|---|
| Existencias | Búsqueda muerta (`q` no declarado) | **FIXED** (FR-001-272) |
| Existencias | Sin paginación (solo los primeros 20) | **FIXED** |
| Existencias | El producto se mostraba como UUID | **FIXED** (código y nombre) |
| Existencias | Almacén y Lote siguen como identificador | DEUDA nueva EXISTENCIAS-IDENTIFICADORES-CRUDOS (LOW): enriquecer esas columnas es otra paridad DB/API/UI, fuera del contrato de consulta |
| Existencias | Filtros dedicados de FR-003-012 (almacén, ubicación, lote, serial, estado, vencimiento) sin control en pantalla, aunque la API los admite | FUTURE_SPEC (deuda EXISTENCIAS-FILTROS-DEDICADOS-UI, LOW) |
| Producto nuevo | Combo Rubro sin opciones nunca (array frente a sobre y `q` ignorado) | **FIXED** (PDD-API-12) |
| Producto nuevo | El combo no filtra por nivel (`RUBRO`) ni por `applies_to` | EXPLICITLY_OUT_OF_SCOPE: paridad con `list_taxonomy`, sin inventar reglas de clasificación |
| Organización y Aprobaciones | `company_id` obsoleto en la consulta | **FIXED** |
| Todas | `UNKNOWN_QUERY_PARAMETER` visible | Imposible desde la UI por la guarda (FR-001-271); si llegara, se mostraría el mensaje seguro del servidor |
| Instantes | `NAIVE_DATETIME` | Imposible desde la UI (siempre `Z`); mensaje seguro si llegara |

**UNEXPLAINED_UI_FUNCTIONAL_GAPS = 0 · SCREEN_FORM_COMPLETENESS_GATE = PASS · DB_API_UI_CONTRACT_PARITY = PASS.**
