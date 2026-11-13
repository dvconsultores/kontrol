# Plan · BUD-01 + BUD-02

## Constitution gate

```text
REQUIREMENTS=COMPLETE (BUD12-01..17, AC-01..10)
NORMATIVE_AUTHORITY=LOPPM 229, 234-236, 239, 248, 250 (A, en custodia); N04 (A); N08-N10 sin reglas (C)
CATALOG_READINESS=STRUCTURAL_MODEL; catálogo = dato del ente con procedencia (D02-B=1)
OWNER_DECISION=D-GOV-02 CLOSED A/1/1/1
ARCHITECTURE=módulo government, patrón PROC-11/TRE-02; DOC-08 por ResourceKind; CTL-02 record_audit
SECURITY=gobierno_presupuesto view/manage (STANDARD), approve/close (SENSITIVE, exige MFA); aislamiento 404
DATA_INTEGRITY=fundamentos e historia append-only; congelado por triggers; sin borrado de ejercicios
TESTABILITY=PG con fechas de negocio controlables (años pasados y futuros)
SHARED_CORE_CHANGE_REQUIRED=0 (solo registros declarativos: setup, mfa_policy, documents/resources, catálogo de auditoría)
MATERIAL_DECISION_REQUIRED=0
CONSTITUTION_GATE=PASS
```

## Contrato de estados (PDD-BUD12-01)

| Transición | Capacidad | Condición de fecha (`hoy` = `hoy_de_negocio()`) | Prerrequisitos | Fundamento |
|---|---|---|---|---|
| crear → BORRADOR | manage | — | año 2000–2100, único por empresa | — |
| BORRADOR → APROBADO | approve (MFA) | `fecha` (sanción) ≤ hoy y ≤ 31-dic del año | completitud | ORDENANZA: referencia, fecha, documento |
| BORRADOR → RECONDUCIDO | approve (MFA) | hoy > 15-dic del año −1 (si no, 409 `GOV_BUDGET_RECONDUCTION_PREMATURE`); `fecha` (publicación) ≥ 16-dic del año −1 y ≤ hoy | completitud | RECONDUCCION: referencia, fecha, documento |
| APROBADO \| RECONDUCIDO → CERRADO | close (MFA) | hoy > 31-dic del año (si no, 409 `GOV_BUDGET_YEAR_NOT_ENDED`) | — | `motivo` opcional (≤ 500) |

- **Completitud** (si falta algo, 422 `GOV_BUDGET_YEAR_INCOMPLETE` con la lista de faltas):
  - al menos 1 nivel y 1 categoría;
  - clasificador con procedencia y documento;
  - al menos 1 partida RECURSO y 1 partida EGRESO.
- **Documento válido:**
  - el `Document` está ACTIVE, es de la empresa y está vinculado (`DocumentLink`) a `resource_type="GovernmentBudgetYear"`, `resource_id=<id del ejercicio>`;
  - el sha256 sale de `DocumentVersion(current_version_id).sha256`;
  - si no, 422 `GOV_BUDGET_INVALID_DOCUMENT` con `field_errors` en el campo.
- **`reconduccion_definitiva`** (calculado, PDD-BUD12-02): estado RECONDUCIDO y hoy > 31-mar del año.

## Modelo (migración `0106_gov_bud01_ejercicio`, `down_revision = "0105_receipt_temporary_zone"`)

Todas las tablas llevan `id`, `created_at`, `updated_at` y `created_by`. Las que llevan `version` lo dicen. El dinero no aparece en este ciclo.

1. **`gov_budget_years` (`GovernmentBudgetYear`, con version):**
   - `tenant_id`, `company_id`;
   - `anio` SmallInteger;
   - `moneda_funcional` String(3);
   - `estado` String(12), por defecto BORRADOR;
   - `precompromiso_activo` Boolean, por defecto false; `precompromiso_desde` Date null;
   - `fijado_por`, `fijado_en`;
   - `cerrado_por`, `cerrado_en`; `motivo_cierre` String(500) null.
   - Restricciones:
     - UNIQUE(`company_id`, `anio`);
     - CHECK `anio BETWEEN 2000 AND 2100`;
     - CHECK `estado IN (BORRADOR, APROBADO, RECONDUCIDO, CERRADO)`;
     - CHECK `char_length(moneda_funcional) = 3`;
     - CHECK `estado = 'BORRADOR' OR (fijado_por, fijado_en NOT NULL)`;
     - CHECK `estado <> 'CERRADO' OR (cerrado_por, cerrado_en NOT NULL)`.
2. **`gov_budget_year_foundations` (`GovernmentBudgetYearFoundation`), append-only:**
   - `year_id`, `company_id`;
   - `tipo` (ORDENANZA \| RECONDUCCION);
   - `referencia` String(300); `fecha` Date;
   - `documento_id` FK `documents.id`; `documento_sha256` String(64);
   - `huella` String(64); `fotografia` JSON.
3. **`gov_budget_program_levels` (`GovernmentBudgetProgramLevel`):**
   - `year_id`, `company_id`;
   - `orden` SmallInteger 1–8; `nombre` String(80);
   - UNIQUE(`year_id`, `orden`) y UNIQUE(`year_id`, `nombre`).
4. **`gov_budget_categories` (`GovernmentBudgetCategory`):**
   - `year_id`, `company_id`, `level_id`;
   - `parent_id` (FK a sí misma, null);
   - `codigo` String(20); `codigo_completo` String(200); `denominacion` String(300);
   - UNIQUE(`year_id`, `codigo_completo`).
5. **`gov_budget_classifiers` (`GovernmentBudgetClassifier`):**
   - `year_id` UNIQUE; `company_id`;
   - `edicion` String(200); `fecha_edicion` Date null; `procedencia` String(1000);
   - `documento_id` FK `documents.id` null; `documento_sha256` String(64) null.
6. **`gov_budget_classifier_items` (`GovernmentBudgetClassifierItem`):**
   - `classifier_id`, `company_id`;
   - `tipo` (RECURSO \| EGRESO); `codigo` String(40); `denominacion` String(300);
   - `nivel` SmallInteger 1–12; `parent_id` (FK a sí misma, null);
   - `vigente_desde` Date; `vigente_hasta` Date null;
   - UNIQUE(`classifier_id`, `tipo`, `codigo`);
   - CHECK de vigencia (`vigente_hasta` ≥ `vigente_desde`).
7. **`gov_budget_year_history` (`GovernmentBudgetYearHistory`), append-only:**
   - `year_id`, `company_id`;
   - `tipo` String(40); `detalle` JSON.

Triggers (patrón 0104):

- `gov_budget_years`: sin DELETE ni TRUNCATE.
- `foundations` e `history`: sin UPDATE, DELETE ni TRUNCATE.
- **Congelado** en levels, categories, classifiers e items: un trigger BEFORE INSERT/UPDATE/DELETE rechaza (`GOV_BUDGET_YEAR_FROZEN`) si el ejercicio dueño no está en BORRADOR. Las partidas llegan al ejercicio por `classifier_id`.

La migración también registra `gobierno_presupuesto` (view, manage, approve, close) y lo concede a `FUNCIONAL_COMPLETO` (patrón `_conceder_permisos` de 0074). El downgrade revierte todo.

## API (`/gobierno/presupuesto/ejercicios`)

Todas las rutas llevan `require_module("gobierno")`. Toda mutación lleva `If-Match` (si falta, 428 `GOV_BUDGET_IF_MATCH_REQUIRED`; si la versión no coincide, 409 `GOV_BUDGET_YEAR_STALE`), excepto la creación. Responde con el detalle del ejercicio y sube su versión.

| Método y ruta | Capacidad | Cuerpo | Notas |
|---|---|---|---|
| GET `` | view | — | lista ordenada por año descendente |
| POST `` (201) | manage | `{anio}` | moneda de `Company.functional_currency` |
| GET `/{id}` | view | — | detalle |
| PUT `/{id}/niveles` | manage | `{niveles:[{nombre}]}` (1–8) | reemplaza la lista; 409 `GOV_BUDGET_LEVELS_IN_USE` si ya hay categorías |
| POST `/{id}/categorias` (201) | manage | `{nivel_orden, parent_id, codigo, denominacion}` | |
| PATCH `/{id}/categorias/{cid}` | manage | `{denominacion}` | |
| DELETE `/{id}/categorias/{cid}` | manage | — | 409 `GOV_BUDGET_CATEGORY_HAS_CHILDREN` |
| PUT `/{id}/clasificador` | manage | `{edicion, fecha_edicion, procedencia, documento_id}` | crea o actualiza; evento PROCEDENCIA_MODIFICADA al actualizar |
| GET `/{id}/clasificador/partidas` | view | `?tipo=&q=` | lista completa ordenada por tipo y código |
| POST `/{id}/clasificador/partidas` (201) | manage | `{tipo, codigo, denominacion, nivel, codigo_padre, vigente_desde, vigente_hasta}` | 409 `GOV_BUDGET_CLASSIFIER_MISSING` si no hay clasificador |
| DELETE `/{id}/clasificador/partidas/{pid}` | manage | — | 409 `GOV_BUDGET_ITEM_HAS_CHILDREN` |
| POST `/{id}/clasificador/importar` | manage | multipart `archivo` (CSV UTF-8) | todo o nada |
| POST `/{id}/aprobar` | approve | `{referencia, fecha, documento_id}` | |
| POST `/{id}/reconducir` | approve | `{referencia, fecha, documento_id}` | |
| POST `/{id}/cerrar` | close | `{motivo}` | |
| POST `/{id}/precompromiso` | approve | `{activo, vigente_desde, motivo}` | estados no CERRADO; `vigente_desde` dentro del año; cambio idéntico → 422 |

**Errores comunes:**

- 404 `GOV_BUDGET_YEAR_NOT_FOUND`, también en un hijo de otro ejercicio o de otra empresa;
- 409 `GOV_BUDGET_YEAR_FROZEN` si se modifica un ejercicio fuera de BORRADOR;
- 409 `GOV_BUDGET_YEAR_INVALID_STATE` en una transición inválida;
- 409 `GOV_BUDGET_YEAR_EXISTS`;
- 422 `GOV_BUDGET_INVALID` con `field_errors`.

**Validaciones de forma:**

- código de categoría `^[0-9A-Za-z-]{1,20}$`;
- código de partida `^[0-9A-Za-z.-]{1,40}$`;
- la vigencia de la partida cae dentro del año; `vigente_desde` vale por defecto el 1 de enero del año;
- CSV: cabecera exacta `tipo,codigo,denominacion,nivel,codigo_padre,vigente_desde,vigente_hasta`;
  - el padre puede ser una fila anterior o una partida existente;
  - errores en `field_errors={"archivo": ["Fila N: …", …]}` (máximo 50);
  - más de 5000 filas da 422.

**Detalle del ejercicio:**

- `id`, `anio`, `moneda_funcional`, `estado`, `version`, `congelado`, `reconduccion_definitiva`;
- `precompromiso_activo`, `precompromiso_desde`;
- `niveles` [`orden`, `nombre`];
- `categorias` [`id`, `nivel_orden`, `nivel_nombre`, `parent_id`, `codigo`, `codigo_completo`, `denominacion`], ordenadas por `codigo_completo`;
- `clasificador` (null, o `edicion`, `fecha_edicion`, `procedencia`, `documento_id`, `documento_sha256`, `partidas_recurso`, `partidas_egreso`);
- `fundamentos` [`tipo`, `referencia`, `fecha`, `documento_id`, `documento_sha256`, `huella`, `en`];
- `faltantes` [textos de completitud];
- `historia` [`tipo`, `detalle`, `en`];
- `fijado_en`, `cerrado_en`, `motivo_cierre`.

## Fotografía y huella (PDD-BUD12-03)

`fotografia` es un dict con:

- `anio`, `moneda_funcional`;
- `niveles` [`orden`, `nombre`];
- `categorias` [`codigo_completo`, `nivel_orden`, `denominacion`], ordenadas;
- `clasificador`: `edicion`, `fecha_edicion` (ISO o null), `procedencia`, `documento_sha256` y `partidas` [`tipo`, `codigo`, `denominacion`, `nivel`, `codigo_padre`, `vigente_desde`, `vigente_hasta`], ordenadas por (`tipo`, `codigo`).

La huella es `sha256(json.dumps(fotografia, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode())`.

## Historia (`tipo`)

CREADO, NIVELES_CONFIGURADOS, CATEGORIA_CREADA, CATEGORIA_MODIFICADA, CATEGORIA_ELIMINADA, CLASIFICADOR_REGISTRADO, PROCEDENCIA_MODIFICADA, PARTIDA_CREADA, PARTIDA_ELIMINADA, PARTIDAS_IMPORTADAS, APROBADO, RECONDUCIDO, CERRADO, PRECOMPROMISO_CAMBIADO.

## Auditoría (14 entradas de catálogo, 495 → 509)

Todas con entidad `GovernmentBudgetYear`, módulo `government`, spec `gov-bud-01`, alcance COMPANY y clase FINANCIAL BUSINESS_COMMIT. Las claves de `after` coinciden exactamente con el detalle:

| Evento | Claves de `after` |
|---|---|
| GOV_BUDGET_YEAR_CREATED | anio, moneda_funcional |
| GOV_BUDGET_LEVELS_CONFIGURED | anio, niveles |
| GOV_BUDGET_CATEGORY_CREATED | anio, codigo_completo |
| GOV_BUDGET_CATEGORY_UPDATED | anio, codigo_completo |
| GOV_BUDGET_CATEGORY_DELETED | anio, codigo_completo |
| GOV_BUDGET_CLASSIFIER_REGISTERED | anio, edicion |
| GOV_BUDGET_CLASSIFIER_PROVENANCE_UPDATED | anio, documento_sha256, edicion |
| GOV_BUDGET_CLASSIFIER_ITEM_CREATED | anio, codigo, tipo |
| GOV_BUDGET_CLASSIFIER_ITEM_DELETED | anio, codigo, tipo |
| GOV_BUDGET_CLASSIFIER_ITEMS_IMPORTED | anio, filas |
| GOV_BUDGET_YEAR_APPROVED | anio, huella, referencia |
| GOV_BUDGET_YEAR_RECONDUCTED | anio, huella, referencia |
| GOV_BUDGET_YEAR_CLOSED | anio |
| GOV_BUDGET_PRECOMMITMENT_POLICY_CHANGED | activo, anio, vigente_desde |


## Registros declarativos (sin lógica de Shared Core)

- `setup/api.py`: `"gobierno_presupuesto": ["view", "manage", "approve", "close"]`.
- `mfa_policy`: `approve` y `close` en SENSITIVE (MFA); `view` y `manage` en STANDARD (patrón TRE-02).
- `documents/resources.py`: `ResourceKind("GovernmentBudgetYear", …, "gobierno_presupuesto:view", ("gov-bud-01",))`. La cardinalidad pasa de 34 a 35, con la semilla N9 correspondiente.
- `service_auditoria`: el objeto `GovernmentBudgetYear` lleva a la ruta `/gobierno/presupuesto/ejercicios/{id}`.

## Frontend

- **Menú:** Gobierno › «Presupuesto» › «Ejercicios presupuestarios» (`/gobierno/presupuesto/ejercicios`).
- **Pantallas:**
  - lista con alta;
  - detalle con secciones: Resumen, Niveles, Estructura programática, Clasificador (procedencia, partidas, importación), Fundamento (aprobar o reconducir), Precompromiso, Cierre, Documentos (`AdjuntosPanel` con `GovernmentBudgetYear`) e Historia.

## E2E

`gobierno-presupuesto.spec.ts`:

1. por el menú, crear un ejercicio y configurar 2 niveles con padre e hijo;
2. validar un error estructural;
3. adjuntar un PDF y registrar la procedencia;
4. importar un CSV;
5. aprobar;
6. comprobar el congelado (los controles de edición desaparecen y la API da 409);
7. revisar la historia;
8. comprobar el aislamiento por API;
9. 1280, 390 y 320 px con Axe.

La reconducción y el cierre dependen de la fecha y se prueban en PG.
