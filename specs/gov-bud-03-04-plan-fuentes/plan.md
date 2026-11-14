# Plan · BUD-03 + BUD-04

## Constitution gate

```text
BUD03_AUTHORITY_CLEAR=1 (GOV-BUD-003/004; LOPPM 233, 239; N31)   BUD04_AUTHORITY_CLEAR=1 (GOV-BUD-005; LOPPM 246, 247)
UNIT_RELATIONSHIP_CLEAR=1 (GovernmentUnit ACTIVA de la estructura ORG-02 VIGENTE con exercise = anio y misma empresa)
PROGRAM_PROJECT_SEMANTICS_CLEAR=1 (categorías BUD-02; sin segundo árbol)
FINANCING_SOURCE_SEMANTICS_CLEAR=1 (catálogo del ente por ejercicio, con procedencia; sin códigos oficiales)
VERSIONING_CLEAR=1 (por ejercicio; congelado y fotografía al fijar; historia append-only)
NORMATIVE_SOURCE_CLEAR=1   MATERIAL_DECISION_REQUIRED=0   SHARED_CORE_CHANGE_REQUIRED=0
CONSTITUTION_GATE=PASS
```

## Decisiones de diseño

| Id | Decisión |
|---|---|
| PDD-B34-01 | Responsable = unidad ORG-02. El cargo y la persona se derivan de ORG-03/04 |
| PDD-B34-02 | Fuentes por ejercicio (como el clasificador), con vigencia dentro del año |
| PDD-B34-03 | Restricción con partidas opcionales: lista de códigos EGRESO validada contra el clasificador del ejercicio (JSON ordenado y único) |
| PDD-B34-04 | El plan no se exige para aprobar (no altera la completitud de BUD-01), pero entra en la fotografía |

## Modelo (migración `0108_gov_bud03_04_plan_fuentes`, `down_revision = "0107_gov_bud01_ejercicio"`)

Todas las tablas llevan `id`, timestamps, `created_by`, `year_id` (FK `gov_budget_years`) y `company_id`.

| Tabla | Columnas propias |
|---|---|
| `gov_budget_plans` | `year_id` UNIQUE, `denominacion` String(300), `documento_id` FK documents null, `documento_sha256` String(64) null |
| `gov_budget_objectives` | `codigo` String(20), `descripcion` String(500); UNIQUE(`year_id`, `codigo`) |
| `gov_budget_categories` (columnas nuevas) | `unit_id` String(36) FK `gov_units` null, index; `objective_id` String(36) FK `gov_budget_objectives` null, index |
| `gov_budget_goals` | `category_id` FK `gov_budget_categories`, `descripcion` String(500), `unidad_medida` String(60), `cantidad` Numeric(18,4) (CHECK > 0), `indicador` String(200), `formula` String(500) null |
| `gov_budget_funding_sources` | `codigo` String(20), `denominacion` String(300), `procedencia` String(1000), `documento_id` FK documents null, `documento_sha256` null, `vigente_desde` Date, `vigente_hasta` Date null (CHECK); UNIQUE(`year_id`, `codigo`) |
| `gov_budget_funding_restrictions` | `source_id` FK `gov_budget_funding_sources`, `descripcion` String(500), `fundamento` String(500), `partidas` JSON (lista) |

**Triggers de congelado** (función existente `kontrol_gov_presupuesto_congelado_por_ejercicio`) en las 5 tablas nuevas. Las categorías ya lo tienen.

**Historia:** la CHECK de `gov_budget_year_history.tipo` se amplía con estos 13 tipos (se elimina y se recrea en la migración):

PLAN_REGISTRADO, OBJETIVO_CREADO, OBJETIVO_MODIFICADO, OBJETIVO_ELIMINADO, CATEGORIA_VINCULADA, META_CREADA, META_MODIFICADA, META_ELIMINADA, FUENTE_CREADA, FUENTE_MODIFICADA, FUENTE_ELIMINADA, RESTRICCION_AGREGADA, RESTRICCION_ELIMINADA.

## Auditoría (13 eventos; catálogo 510 → 523)

Entidad `GovernmentBudgetYear`, módulo `gov-bud-03`, clase FINANCIAL BUSINESS_COMMIT.

| Evento | Claves de `after` |
|---|---|
| GOV_BUDGET_PLAN_REGISTERED | anio, denominacion |
| GOV_BUDGET_OBJECTIVE_CREATED / _UPDATED / _DELETED | anio, codigo |
| GOV_BUDGET_CATEGORY_LINKED | anio, codigo_completo, objetivo, unidad |
| GOV_BUDGET_GOAL_CREATED / _UPDATED / _DELETED | anio, codigo_completo, indicador |
| GOV_BUDGET_FUNDING_SOURCE_CREATED / _UPDATED / _DELETED | anio, codigo |
| GOV_BUDGET_FUNDING_RESTRICTION_ADDED / _REMOVED | anio, codigo, partidas |

## API

Base `/gobierno/presupuesto/ejercicios/{id}`. `view` en los GET y `manage` en las mutaciones. Toda mutación lleva If-Match, exige BORRADOR, sube la versión y devuelve la vista del bloque.

- **GET `/plan`** devuelve:
  - `plan`: `denominacion`, `documento_id`, `documento_sha256`;
  - `objetivos`;
  - `vinculos`: por categoría, con unidad y objetivo;
  - `metas`;
  - `unidades_disponibles`: id, código y nombre;
  - `estructura_organizativa`: estado o null.
- **PUT `/plan`**.
- **POST / PATCH / DELETE `/plan/objetivos[/{oid}]`**.
- **PUT `/categorias/{cid}/vinculo`**: `{unidad_id, objetivo_id}`.
- **POST / PATCH / DELETE `/plan/metas[/{mid}]`**.
- **GET `/fuentes`**.
- **POST / PATCH / DELETE `/fuentes[/{fid}]`**.
- **POST / DELETE `/fuentes/{fid}/restricciones[/{rid}]`**.

## Frontend

Dentro del detalle del ejercicio, dos componentes nuevos:

- **PlanEjercicio:** plan, objetivos, tabla de responsables por categoría y metas.
- **FuentesEjercicio:** fuentes y restricciones.

Selectores con código y nombre.

## E2E

`gobierno-presupuesto-plan-fuentes.spec.ts`:

1. Se siembran por API un ejercicio con niveles y categorías, y una estructura ORG-02 VIGENTE del año.
2. Por el menú: plan, objetivos, vínculo, meta, fuente, restricción, negativas y recarga.
3. Historia y aislamiento.
4. 1280/390/320 con Axe.
