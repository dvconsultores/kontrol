# Plan · BUD-05 presupuesto aprobado

## Constitution gate

```text
BUD05_REQUIREMENT_CLEAR=1 (GOV-BUD-006/007/008 con D-GOV-02 A; OD-BUD05-01/02)
CREDIT_IDENTITY_CLEAR=1 (ejercicio × categoría hoja × partida EGRESO hoja × fuente; UNIQUE; unidad derivada de BUD-03)
CATEGORY_AUTHORITY_CLEAR=1 (BUD-01/03)   EXPENDITURE_ITEM_AUTHORITY_CLEAR=1 (BUD-02)   FUNDING_SOURCE_AUTHORITY_CLEAR=1 (BUD-04)
MONETARY_RULE_CLEAR=1 (NUMERIC(18,2) y Decimal como TRE-02 schemas_caja; gt 0, decimal_places 2; sin redondeo; D-GOV-02 ARCH §4)
BALANCE_RULE_CLEAR=1 (LOPPM 240 literal + OD-BUD05-02)   FREEZE_RULE_CLEAR=1 (trigger kontrol_gov_presupuesto_congelado_por_ejercicio)
INCOME_BUDGET_AUTHORITY_EXISTS=0 al entrar → 1 al cerrar (OD-BUD05-01)
MATERIAL_DECISION_REQUIRED=0 (resuelta por la dueña)   SHARED_CORE_CHANGE_REQUIRED=0
CONSTITUTION_GATE=PASS
```

## Decisiones de diseño (Claude, no materiales)

| Id | Decisión |
|---|---|
| PDD-B05-01 | Solo son imputables las **hojas**: categorías sin hijas y partidas sin hijas. Así no hay doble cómputo entre niveles. Se valida al registrar y otra vez al fijar (B05-07) |
| PDD-B05-02 | Restricciones: **unión** de las listas no vacías de la fuente (cada restricción es una afectación legal, LOPPM 246); un código cubre a sus descendientes. Sin restricciones con partidas, la fuente es libre |
| PDD-B05-03 | Un crédito solo cambia su monto. Para cambiar categoría, partida o fuente se elimina y se crea otro (la identidad no muta) |
| PDD-B05-04 | Aprobar no exige un mínimo de créditos ni de ingresos: se conserva el contrato de BUD-01 y basta el cuadre. Un aprobado sin créditos no podrá ejecutarse en BUD-06/08 |
| PDD-B05-05 | NUMERIC(18,2), el estándar del repositorio (TRE-02), en lugar de (20,2) de D-GOV-02 ARCH §4. Tope de 9.999.999.999.999.999,99 |
| PDD-B05-06 | Un rechazo por validación (422) no cambia el estado y no se audita: no hay requisito que pida registrar intentos. CTL-01 sí lo hace porque su norma lo exige |
| PDD-B05-07 | La vigencia de fuentes y partidas está dentro del año por construcción (BUD-02/04), así que un crédito del año siempre la cumple |

## Modelo (fichero `0111_gov_bud05_presupuesto_aprobado.py`, revisión `0111_gov_bud05_aprobado` (≤ 32 caracteres por `alembic_version`), `down_revision = "0110_gov_proc06_monto_oferta"`: reencadenada tras las migraciones 0109/0110 que P2 publicó durante el ciclo)

Todas las tablas llevan `id`, timestamps, `created_by`, `year_id` (FK gov_budget_years, índice) y `company_id` (FK companies, índice).

- **gov_budget_income_estimates**:
  - `item_id` FK gov_budget_classifier_items, con índice;
  - `monto` Numeric(18,2), CHECK monto > 0;
  - UNIQUE(year_id, item_id).
- **gov_budget_credits**:
  - `category_id` FK gov_budget_categories, con índice;
  - `item_id` FK gov_budget_classifier_items, con índice;
  - `source_id` FK gov_budget_funding_sources, con índice;
  - `monto` Numeric(18,2), CHECK > 0;
  - UNIQUE(year_id, category_id, item_id, source_id).
- **gov_budget_treasury_holdings**:
  - `year_id` UNIQUE;
  - `monto` Numeric(18,2), CHECK > 0;
  - `fecha_corte` Date;
  - `documento_id` FK documents, NOT NULL;
  - `documento_sha256` String(64), NOT NULL.
- **Triggers:** congelado en las 3 tablas, con la función existente.
- **Historia:** la CHECK suma 8 tipos: INGRESO_REGISTRADO, INGRESO_MODIFICADO, INGRESO_ELIMINADO, CREDITO_REGISTRADO, CREDITO_MODIFICADO, CREDITO_ELIMINADO, EXISTENCIAS_REGISTRADAS, EXISTENCIAS_ELIMINADAS.
- **Auditoría** (8 eventos, módulo gov-bud-05, catálogo 523 → 531):
  - GOV_BUDGET_INCOME_ESTIMATE_CREATED, _UPDATED y _DELETED, con (anio, codigo, monto);
  - GOV_BUDGET_CREDIT_CREATED, _UPDATED y _DELETED, con (anio, categoria, fuente, monto, partida);
  - GOV_BUDGET_TREASURY_HOLDINGS_REGISTERED, con (anio, fecha_corte, monto);
  - GOV_BUDGET_TREASURY_HOLDINGS_REMOVED, con (anio,).

## API

Base `/gobierno/presupuesto/ejercicios/{id}`. `view` en GET y `manage` en las mutaciones. Toda mutación lleva If-Match, exige BORRADOR, sube la versión y devuelve la vista.

- **GET `/presupuesto-aprobado`** devuelve:
  - `version`, `congelado`, `moneda`;
  - `ingresos`, `creditos`, `existencias_tesoro`;
  - `totales`: ingresos, creditos, existencias, holgura_tesoro, disponible, diferencia, cuadra;
  - `opciones`: categorías y partidas imputables, y fuentes con sus partidas permitidas.
- **POST / PATCH / DELETE `/presupuesto-aprobado/ingresos[/{iid}]`**.
- **POST / PATCH / DELETE `/presupuesto-aprobado/creditos[/{cid}]`**.
- **PUT / DELETE `/presupuesto-aprobado/existencias-tesoro`**.

## Frontend

Componente `PresupuestoAprobadoEjercicio.tsx` dentro del detalle del ejercicio, tras «Fuentes de financiamiento».

## Encargos a DeepSeek (deepseek-v4-pro; objetivo 3–5, tope 8)

1. **C1:** datos y contrato (modelos, migración, catálogo, esquemas, API, main y fijaciones).
2. **C2:** dominio (servicio nuevo y guardas en los servicios de BUD-01/02/04).
3. **C3:** pruebas PG.
4. **C4:** frontend y Vitest.
5. **C5:** E2E.
