# Plan · GOV-ORG-07 Matriz auditable de autoridad

## Decisiones de arquitectura

| Id | Decisión | Razón |
|---|---|---|
| AD-ORG07-01 | **Proyección de lectura** en `service_autoridad.py` sobre `gov_positions`, `gov_position_competencies`, `gov_position_versions`, `gov_units`, `DocumentLink`/`Document`. Sin tablas ni caché | Fuente única de autoridad (ORG-03); no puede haber una matriz obsoleta que contradiga la fuente |
| AD-ORG07-02 | Regla de corte §4.2: la ventana del cargo usa el registro actual, como `_validar_autoridad` de DOC-02; las competencias, la versión en vigor en D. La comparación de instantes se hace en Python con `_utc` y `inicio_del_dia_de_negocio(D + 1 día)` | Coherencia con DOC-02 en la ventana; historia auditable; SQLite pierde la zona horaria (`DateTime(timezone=True)`), así que no se compara en SQL |
| AD-ORG07-03 | Se cargan una vez todos los cargos VIGENTE/INACTIVO de la estructura, sus versiones, las unidades y los vínculos documentales; después se filtra, ordena y pagina en memoria | El tamaño está acotado por la estructura de un ejercicio; evita N+1 y reglas en SQL difíciles de portar |
| AD-ORG07-04 | Router propio `api_autoridad.py` con prefijo `/gobierno/autoridad`; guardas permiso → empresa → módulo | Patrón de los routers de Gobierno |
| AD-ORG07-05 | Capacidad `gobierno_autoridad:view` (STANDARD); migración `0068_gov_org07_autoridad` solo de permisos, con el patrón `_conceder_permisos` de 0067 | OD-ORG07-03 |
| AD-ORG07-06 | Exportación con los mismos filtros y sin paginación; auditoría `GOV_AUTHORITY_MATRIX_EXPORTED` con el registro de `_auditar` de ORG-03 | Exportación auditada; el CSV es lo que se ve |
| AD-ORG07-07 | Interfaz: `MatrizAutoridadPage` con los filtros en la URL (`?ejercicio&fecha&unidad&cargo&accion&materia&texto&pagina`), tabla en `overflow-x-auto`, detalle en un panel de la página (sin modal) | Recargar y compartir conservan la consulta; regla de no modales; 320 px |
| AD-ORG07-08 | Detalle con su propia ruta de API bajo `gobierno_autoridad:view`: Control Interno ve el historial sin `gobierno_cargos` | IR §5 (solo lectura) |

## Decisiones de diseño (de Claude, dentro de las de la dueña)

- PDD-ORG07-01: el filtro de unidad incluye siempre sus subunidades (árbol por `parent_id` dentro de la estructura).
- PDD-ORG07-02: `texto` busca, sin distinguir mayúsculas, en código y denominación del cargo, código, denominación y ruta de la unidad, y fundamento.
- PDD-ORG07-03: filas sin competencias no existen; un cargo vigente sin competencias no puede darse (ORG-03 exige ≥ 1 para poner en vigor y no deja retirar la última).
- PDD-ORG07-04: el enlace «Abrir el cargo» (`/gobierno/cargos/:ejercicio/:cargoId`) se muestra solo con `gobierno_cargos:view`.
- PDD-ORG07-05: el CSV va en UTF-8 con cabecera en `snake_case` (como el de ORG-03); los montos en texto con punto decimal.
- FIND-ORG07-01 (LOW, informativo, fuera de alcance): DOC-02 valida la competencia de un acto con las competencias **actuales** del cargo, no con las de la fecha del acto. ORG-07 usa la versión en vigor (OD-ORG07-02). Se informa a la dueña y no se cambia DOC-02.

## Delta acotado QA-LIC-GOB-01 (OD-QA-LIC-02; tras la E2E dirigida de ORG-07)

- **QA-A · fidelidad de la licencia sintética** (`qa/licencia_firmada.py`): `payload_sintetico` lleva siempre `entitlements.modules`; por defecto, los de la siembra (`["gobierno"]`). Quitar Gobierno exige una opción explícita (`--modulos ""` o una lista) con el propósito dicho en la prueba.
- **QA-B · aislamiento del estado global** (`playwright.config.ts`): las specs que importan licencias aceptadas (`licencia-import`, `licencia-periodo`) pasan a un proyecto dependiente `licencia-estado` que espera a chromium, firefox y webkit. La cadena `licencia-revision → sync → rotacion → tasa` cuelga de él.
- **QA-C · contexto**: las specs no gubernamentales que hoy pasan solo porque Gobierno quedaba apagado afirman la terminología que corresponde al contexto (ente con Gobierno, empresa sin él). Los dos contextos quedan probados. Se identifican corriendo la canónica con QA-A + QA-B.
- Frontera: si el arreglo pide tocar algo más que esos ficheros y sus ayudantes directos, se para la expansión y QA-LIC-GOB-01 queda OPEN_RELEASE_BLOCKER.

## Puerta de la Constitución

| Compuerta | Valor |
|---|---|
| CURRENT_BRANCH / REMOTE_BRANCH_COUNT / HEAD_EQUALS_ORIGIN | develop / 1 / 1 (`b34f01a`) |
| ORG07_REQUIREMENTS_COMPLETE · FULL_PROCESS_IMPLEMENTABLE · WHO_SEMANTICS_RESOLVED | 1 · 1 · 1 (OD-ORG07-01) |
| ORG06_DEPENDENCY_REQUIRED · ORG04_DEPENDENCY_REQUIRED | 0 · 0 |
| AUTHORITY_SOURCE_OF_TRUTH_DEFINED · MATRIX / ACTION / MATTER / LIMIT / VALIDITY contracts | 1 · 1 / 1 / 1 / 1 / 1 |
| MENU · SCREEN_MATRIX · FIELD · ROLE · REPORT · AUDIT · OWNER_UAT_SCENARIO | 1 · 1 · 1 · 1 · 1 · 1 · 1 |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 · 0 · 0 · 0 |

**GATE = PASS.** Principios: Spec Kit (P1); autorización expresa de la iniciativa en el encargo de la dueña (P2); producto antes que campañas; solo `develop`.
