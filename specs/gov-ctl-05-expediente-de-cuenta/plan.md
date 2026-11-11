# Plan · CTL-05

**Base:** develop `bb64b41`, Alembic `0097_fusion_gov_replenishment`; la migración nueva es `0100_gov_ctl05_rendicion` (renumerada dos veces tras las publicaciones de P2; ver evidence/CTL05_RECONCILIATION_REPORT.md).
**Pila:** FastAPI, SQLAlchemy y PostgreSQL. React con TanStack Query. ReportLab para el PDF.

## CONSTITUTION GATE

| Compuerta | Resultado |
|---|---|
| Fuente oficial leída (N21 art. 3–33) | PASS |
| `MATERIAL_BLOCKER_FOUND` | 0 |
| `MATERIAL_DECISION_REQUIRED` | 0 (DECISIONES = PDD) |
| Reutiliza CTL-02, CTL-04, DOC-08, ORG-04, ORG-06, storage y ReportLab, sin motor paralelo | PASS |
| No duplica DOC-08 ni DOC-01 ni crea dominios ausentes | PASS |
| Aislamiento por `company_id`, autoridad en PostgreSQL | PASS |
| Nombres OpenAPI únicos (prefijo `Rendicion`) | PASS (verificar con un diff antes de publicar) |
| DeepSeek escribe todo el código y las pruebas | PASS (C1 backend, C2 frontend, C3 E2E) |

## Modelo de datos (`app/modules/government/models.py`)

### `GovernmentRenditionFile` (tabla `gov_rendition_files`)

Mixins `UUIDMixin`, `TimestampMixin`, `CreatedByMixin` y `VersionMixin`; `__scope__ = Scope.COMPANY`.

**Campos:**
- **Identificación:** `company_id`, `codigo String(20)`, `numero_version Integer ≥1`, `anterior_id` (FK propia, nullable).
- **Cabecera:** `denominacion String(200)`, `ejercicio Integer?`, `periodo_desde Date`, `periodo_hasta Date`, `fecha_corte Date`, `observaciones String(1000)?`.
- **Responsable:** `assignment_id` (FK `gov_assignments`), `responsable JSON` (instantánea), `responsable_official_id String(36)`.
- **Estado:** `estado String(16)`, con CHECK en (EN_FORMACION, FORMADA, PARTICIPADA, CALIFICADA, FENECIDA, SUSTITUIDA).
- **Formación:** `formado_en`, `formado_por`, `snapshot JSON?`, `snapshot_sha256 String(64)?`, `informe_storage_key String(255)?`, `informe_sha256 String(64)?`, `informe_bytes Integer?`.
- **Participación:** `participacion_fecha Date?`, `participacion_oficio String(100)?`, `participacion_registrada_por`, `participacion_registrada_en`.
- **Calificación:** `calificacion String(10)?` (CONFORME u OBJETADA), `calificacion_organo String(200)?`, `calificacion_informe_numero String(50)?`, `calificacion_informe_fecha Date?`, `calificacion_fundamento String(1000)?`, `calificacion_registrada_por`, `calificacion_registrada_en`.
- **Fenecimiento:** `fenecimiento_auto_numero String(50)?`, `fenecimiento_auto_fecha Date?`, `fenecimiento_fundamento String(1000)?`, `fenecimiento_registrado_por`, `fenecimiento_registrado_en`.
- **Sustitución:** `sustitucion_motivo String(500)?`, que es el motivo de esta versión cuando `anterior_id` no es nulo.

**Unicidad:** (`company_id`, `codigo`, `numero_version`).

**CHECKs:**
- `periodo_desde <= periodo_hasta`;
- `fecha_corte` entre desde y hasta;
- estado distinto de EN_FORMACION ⇒ `snapshot_sha256` e `informe_sha256` no nulos;
- `calificacion` no nula ⇔ estado en (CALIFICADA, FENECIDA, o SUSTITUIDA nunca).

En la práctica basta: estado en (CALIFICADA, FENECIDA) ⇒ `calificacion IS NOT NULL`.

**Índices:** `company_id`, `estado`, `assignment_id`.

### `GovernmentRenditionPiece` (tabla `gov_rendition_pieces`)

**Campos:**
- **Vínculos:** `company_id`, `file_id` (FK), `audit_event_id String(36)`.
- **Orden:** `ordinal Integer?`, que se fija al formar.
- **Copia del evento:** `fecha DateTime(tz)`, `proceso String(16)`, `accion String(80)`, `entidad String(80)`, `entidad_id String(36)?`, `referencia String(300)`, `objeto JSON?`, `documentos JSON` (lista de `{documento_id, version_id, sha256}`).
- **Integridad:** `huella String(64)`.
- **Alta:** `incorporada_por`, `incorporada_en`.

**Unicidad:**
- (`file_id`, `audit_event_id`) con el nombre `uq_gov_rendition_pieces_file_event`;
- (`file_id`, `ordinal`).

### Disparadores PostgreSQL (DDL en el modelo y en la migración, como PROC-10)

- **`gov_rendition_pieces`:**
  - UPDATE prohibido, salvo que solo cambie `ordinal` y el padre esté en EN_FORMACION en el momento de formar;
  - DELETE solo si el padre está en EN_FORMACION;
  - TRUNCATE prohibido.

  Implementación permitida: la función lee `gov_rendition_files.estado` del `file_id`.
- **`gov_rendition_files`:**
  - DELETE y TRUNCATE prohibidos;
  - una vez `snapshot_sha256` no es nulo, no cambian `snapshot`, `snapshot_sha256`, `informe_*`, cabecera, `responsable*` ni `codigo/numero_version`.

## Capacidades y cableado

- **Migración:** permisos `gobierno_rendicion` view, form y qualify con alcance COMPANY, concedidos a FUNCIONAL_COMPLETO, como en 0096.
- **`setup/api.py`:** `CATALOGO_DE_PERMISOS["gobierno_rendicion"] = ["view","form","qualify"]`.
- **`mfa_policy.py`:** `form` y `qualify` en SENSITIVE; `view` en STANDARD.
- **`audit_catalog_entries.py`:** 11 acciones con `owner_spec` `gov-ctl-05` y la entidad `GovernmentRenditionFile`:
  - CREATED, UPDATED, PIECE_ADDED, PIECE_REMOVED, FORMED;
  - PARTICIPATED, QUALIFIED, FENECIDA (código `GOV_RENDITION_FILE_DISCHARGED`), VERSIONED;
  - EXPORTED, que cubre la descarga de PDF y de CSV;
  - VERIFIED.
- **`service_auditoria.PROCESOS`:** se añade `("CTL-05", "Expedientes de cuenta", "gov-ctl-05")`.
- **`main.py`:** `include_router` del router nuevo.
- **Pruebas transversales:** CATB-03 (+11), los recuentos de MFA (+2/+1) y las cabezas Alembic (0098).

## API (`api_rendicion.py`, prefijo `/gobierno/rendicion`, `require_module("gobierno")`)

| Método | Ruta | Capacidad | Resultado |
|---|---|---|---|
| GET | `/opciones` | view | `{responsables:[{asignacion_id, codigo, funcionario, cargo, unidad, figura, desde, hasta}], procesos:[{codigo,nombre}], estados:[...]}` |
| GET | `/expedientes` | view | Filtros `estado, texto, desde, hasta, responsable (official_id), unidad (unit_id), pagina, por_pagina≤50`. Devuelve `{items, total, pagina, por_pagina}` |
| POST | `/expedientes` | form | 201, ficha |
| GET | `/expedientes/{id}` | view | Ficha |
| PUT | `/expedientes/{id}` | form + If-Match | Ficha (solo EN_FORMACION) |
| GET | `/expedientes/{id}/candidatas` | view | Filtros `proceso, accion, texto, pagina, por_pagina≤50`. Devuelve `{items:[{evento_id, fecha, proceso, proceso_nombre, accion, accion_etiqueta, usuario, referencia, objeto, incluida}], total, pagina, por_pagina}` |
| POST | `/expedientes/{id}/piezas` | form | `{evento_id}`; 201, pieza |
| DELETE | `/expedientes/{id}/piezas/{pieza_id}` | form | 204 |
| POST | `/expedientes/{id}/formar` | form | Ficha |
| GET | `/expedientes/{id}/reporte` | view | Reporte JSON |
| GET | `/expedientes/{id}/reporte.pdf` | view | application/pdf (409 si no está formado) |
| GET | `/expedientes/{id}/indice.csv` | view | text/csv (409 si no está formado) |
| GET | `/expedientes/{id}/integridad` | view | `{estado: VALIDO\|INCOMPLETO, snapshot_ok, informe_ok, piezas:[{ordinal, estado, detalle}]}` (409 si no está formado) |
| POST | `/expedientes/{id}/participacion` | form | `{fecha, oficio}`; ficha |
| POST | `/expedientes/{id}/calificacion` | qualify | `{resultado, organo, informe_numero, informe_fecha, fundamento}`; ficha |
| POST | `/expedientes/{id}/fenecimiento` | qualify | `{auto_numero, auto_fecha, fundamento?}`; ficha |
| POST | `/expedientes/{id}/nueva-version` | form | `{motivo}`; 201, ficha de la versión nueva |
| GET | `/expedientes/{id}/historial` | view | `{items:[{fecha, accion, accion_etiqueta, usuario, motivo, version}]}` de todas las versiones de la cadena |

### Ficha (`RendicionExpedienteOut`)

**Identificación y cabecera:** `id`, `codigo`, `numero_version`, `version` (VersionMixin), `estado`, `anterior_id`, `sustituido_por_id`, `sustitucion_motivo`, `denominacion`, `ejercicio`, `periodo_desde`, `periodo_hasta`, `fecha_corte`, `observaciones`, `ente` (denominación), `responsable` (`{funcionario, funcionario_codigo, cargo, cargo_codigo, unidad, unidad_codigo, figura, asignacion_codigo}`).

**Contenido y formación:**
- `piezas`, en orden de índice; antes de formar, el ordinal provisional se calcula con la misma regla;
- `formado_en`, `formado_por` (username), `snapshot_sha256`, `informe` (`{sha256, bytes}` o null).

**Rendición:**
- `participacion`: `{fecha, oficio, vence, en_plazo, registrada_por, registrada_en}` o null;
- `plazo_participacion`: `periodo_hasta` más 90 días;
- `calificacion`: `{resultado, organo, informe_numero, informe_fecha, fundamento, registrada_por, registrada_en}` o null;
- `fenecimiento`: `{auto_numero, auto_fecha, fundamento, registrado_por, registrado_en}` o null;
- `hallazgos`: lista de `{ordinal, referencia, objeto}` de las piezas con `entidad == "GovernmentFinding"`.

### Pieza (`RendicionPiezaOut`)

`id, ordinal, evento_id, fecha, proceso, proceso_nombre, accion, accion_etiqueta, entidad, entidad_id, usuario, referencia, objeto ({tipo,id,ruta,capacidad}|null), documentos ([{documento_id, version_id, sha256}]), huella, ruta_evento ("/gobierno/bitacora/{evento_id}")`.

### Reporte (`RendicionReporteOut`)

`{provisional: bool, generado_en, expediente: {...cabecera, estado, codigo, version}, ente, responsable, piezas: [...], resumen: [{concepto, fuente, filtro, periodo, conjunto, regla, resultado}], hallazgos, snapshot_sha256|null}`.

Para una cuenta formada es exactamente el snapshot congelado. El resumen tiene estas filas:
1. hechos de Gobierno del período en la bitácora (consulta guardada; conteo hasta `formado_en`);
2. piezas incluidas;
3. una fila por proceso con piezas;
4. soportes documentales;
5. hallazgos asociados.

### Errores (KontrolError, sin envoltorio de módulo)

**404:** `GOV_RENDITION_NOT_FOUND`, `GOV_RENDITION_EVENT_NOT_FOUND`.

**422:**
- `GOV_RENDITION_INVALID_PERIOD`;
- `GOV_RENDITION_RESPONSIBLE_INVALID`;
- `GOV_RENDITION_EVENT_OUT_OF_PERIOD`;
- `GOV_RENDITION_EMPTY`;
- `GOV_RENDITION_REASON_REQUIRED`.

**409:**
- `GOV_RENDITION_STATE` (transición o edición no permitida);
- `GOV_RENDITION_PIECE_DUPLICATE`;
- `GOV_RENDITION_NOT_FORMED`;
- `VERSION_CONFLICT` (por el `_version` de `api.py`).

**403:** `GOV_RENDITION_SAME_ACTOR` (calificación o fenecimiento registrados por quien formó la cuenta o por el cuentadante).

## Concurrencia

- **Escrituras sobre el expediente:** `SELECT … FOR UPDATE` sobre la fila del expediente. El estado se comprueba después del bloqueo.
- **Pieza duplicada:** el `IntegrityError` de `uq_gov_rendition_pieces_file_event` se traduce a 409.
- **Doble formación:** el segundo intento recibe 409 `GOV_RENDITION_STATE`.

## Frontend (C2)

Módulo `src/modules/gobierno/rendicion/`:
- `ExpedientesCuentaPage` (listado con filtros y paginación);
- `NuevoExpedienteCuentaPage`;
- `ExpedienteCuentaPage` (ficha con secciones: cabecera y responsable; piezas e índice con candidatas paginadas; reporte; rendición; integridad; historial).

Entrada de menú «Expedientes de cuenta» en Gobierno, junto a Control Interno. Las rutas se registran en `pantallas.ts` con la capacidad `gobierno_rendicion:view`. Móvil con listas, sin tablas anchas.

## E2E (C3)

`e2e/gobierno-rendicion.spec.ts`:
1. datos reales: acto DOC-02, eventos CTL-02, muestra CTL-04 y hallazgo CTL-06;
2. crear, incorporar, revisar el índice, generar el reporte, formar, reabrir y verificar el snapshot tras un evento posterior;
3. tres negativas: otro ente, cuenta formada inmutable y pieza inexistente;
4. Axe y responsive.

Además, la pantalla nueva se añade a HUMO-UAT-01.
