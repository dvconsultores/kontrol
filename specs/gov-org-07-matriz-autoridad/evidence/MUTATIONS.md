# GOV-ORG-07 · mutaciones de negocio (T010, herramienta de Claude `mutar07b.py`)

Método: un SEARCH único por mutante → REPLACE; purga de `__pycache__` y `PYTHONDONTWRITEBYTECODE=1`; restauración verificada por sha256
(42/42 restaurados). Backend: `pytest tests/test_gov_org07_autoridad.py` sobre PostgreSQL. Interfaz: `vitest run src/modules/gobierno/autoridad
src/layout/Sidebar.test.tsx src/app`.

## Backend · 27 mutantes · 25 muertos · 2 equivalentes · 0 supervivientes

| ID | Mutación | Resultado | Prueba que lo mata / justificación |
|---|---|---|---|
| BM-01 | ventana sin límite inferior (vigente_desde ignorado) | KILLED | GM-04 |
| BM-02 | vigente_hasta ignorado | KILLED | GM-06 |
| BM-03 | cargos BORRADOR incluidos en la proyección | EQUIVALENT | un cargo BORRADOR no tiene versiones VIGENTE/INACTIVO (BORRADOR → VIGENTE es irreversible), así que `_version_en_vigor` devuelve None y no aporta filas: doble guarda |
| BM-04 | corte de registro ignorado (última versión siempre) | KILLED | GM-04 |
| BM-05 | primera versión candidata en vez de la última | KILLED | GM-05 |
| BM-06 | sin respaldo de la primera VIGENTE (registro retroactivo excluido) | KILLED | GM-05 |
| BM-07 | subunidades fuera del filtro de unidad | KILLED | GM-09 |
| BM-08 | filtro de unidad ignorado | KILLED | GM-09 |
| BM-09 | filtro de acción ignorado | KILLED | GM-09 |
| BM-10 | filtro de materia ignorado | KILLED | GM-09 |
| BM-11 | filtro de cargo ignorado | KILLED | GM-09 |
| BM-12 | texto ignorado | KILLED | GM-10 |
| BM-13 | unidad ajena aceptada | KILLED | GM-09 |
| BM-14 | cargo ajeno aceptado | KILLED | GM-09 |
| BM-15 | fecha fuera del ejercicio aceptada | KILLED | GM-08 |
| BM-16 | ejercicio pasado por defecto al 1/1 | KILLED | GM-07 |
| BM-17 | documentos no activos como acto soporte (matriz) | KILLED | GM-11 |
| BM-18 | versiones sin filtro de empresa | EQUIVALENT | defensa en profundidad: las versiones se piden por `position_id` de cargos ya acotados a la estructura y a la empresa y por `structure_id`; la coherencia de empresa de las versiones la impone el servicio de ORG-03 y la vigila la integridad (C16) |
| BM-19 | detalle de cargo BORRADOR visible | SURVIVED → KILLED | GM-13 (detalle de BOR → 404, T001f) |
| BM-20 | paginación ignorada | KILLED | GM-12 |
| BM-21 | exportación sin el filtro de acción | KILLED | GM-14 |
| BM-22 | orden de acciones ignorado | SURVIVED → KILLED | GM-21 (T001f/T001g) |
| BM-23 | ruta de unidad invertida | KILLED | GM-03 |
| BM-24 | exportación sin auditoría | KILLED | GM-14 |
| BM-25 | denominación del cargo actual en vez de la de la versión | SURVIVED → KILLED | GM-21 |
| BM-26 | documentos no activos en el detalle | KILLED | GM-13 |
| BM-27 | estado del cargo de la versión en vez del actual | SURVIVED → KILLED | GM-21 |

## Interfaz · 15 mutantes · 14 muertos · 1 equivalente · 0 supervivientes

| ID | Mutación | Resultado | Prueba que lo mata / justificación |
|---|---|---|---|
| UM-01 | sin control de permiso de la matriz | KILLED | MTZ-01 |
| UM-02 | «Abrir el cargo» sin gobierno_cargos:view | KILLED | MTZ-07 |
| UM-03 | ejercicio por defecto = el primero de la lista | SURVIVED → KILLED | MTZ-18 (T008c) |
| UM-04 | acción de la URL sin validar | KILLED | MTZ-17 |
| UM-05 | cambiar filtro no reinicia la página | SURVIVED → KILLED | MTZ-19 (T008c) |
| UM-06 | marca «Inactivo» ausente | KILLED | MTZ-02 |
| UM-07 | acto vacío sin «Sin documento» | KILLED | MTZ-02 |
| UM-08 | paginación siempre oculta | KILLED | MTZ-09 |
| UM-09 | «Anterior» habilitado en la primera página | KILLED | MTZ-09 |
| UM-10 | búsqueda sin recortar | EQUIVALENT | `consultaDeMatriz` recorta `texto` antes de construir la consulta (CDM-02); el recorte de la pantalla es redundante |
| UM-11 | «Usada para esta fecha» en todas las versiones | KILLED | MTZ-07 |
| UM-12 | exportación sin filtros | KILLED | MTZ-10 |
| UM-13 | menú sin la entrada «Matriz de autoridad» | KILLED | GSB-12 |
| UM-14 | pantalla con la capacidad de cargos | KILLED | GSB-12 |
| UM-15 | consulta sin el texto | KILLED | CDM-02 |

Total: 42 mutantes · 39 muertos (6 tras añadir sus pruebas) · 3 equivalentes justificados · 0 supervivientes · 42/42 restaurados.
