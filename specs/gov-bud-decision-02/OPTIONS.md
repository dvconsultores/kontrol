# OPTIONS · D-GOV-02

## 1. Qué significa «profundidad»

El IR §15 la define así: **formulación completa** frente a **presupuesto aprobado + ejecución**. Cada dimensión está clasificada con evidencia.

| Dimensión | Fuente | Clasificación |
|---|---|---|
| Ejercicio (estado, calendario, moneda funcional, versión normativa) | GOV-BUD-001; LOPPM 234-236, 250 | MANDATORY_FOR_V1 |
| Clasificación institucional (el ente) | ORG-01 | MANDATORY_FOR_V1 (ya existe) |
| Clasificación presupuestaria: **modelo** versionado por ejercicio | GOV-BUD-002; N04; LOPPM 239 | MANDATORY_FOR_V1 |
| Clasificación presupuestaria: **catálogo** del ejercicio (códigos ONAPRE) | N10 (C, no custodiado) | UNRESOLVED (sub-decisión D02-B) |
| Fuente de financiamiento | GOV-BUD-005; LOPPM 247 | MANDATORY_FOR_V1 |
| Sector, programa, subprograma, proyecto o categoría equivalente | LOPPM 239; GOV-BUD-003 | MANDATORY_FOR_V1 (niveles configurables por ente) |
| Plan, objetivo, metas físicas, indicadores y vínculo con el POA | GOV-BUD-003/004; LOPPM 233; N30, N31 | OPTIONAL_FOR_V1 (estructura sí; el bloqueo de créditos huérfanos solo «cuando la norma local lo exija», N37) |
| Unidad ejecutora o centro gestor | GOV-BUD-009; ORG-02 | MANDATORY_FOR_V1 (se reutiliza la unidad de ORG-02) |
| Partidas | LOPPM 239, 242 | MANDATORY_FOR_V1 (el código sale del catálogo) |
| Formulación: anteproyecto, proyecto, escenarios, supuestos, techos, presupuesto participativo | GOV-BUD-006/007; LOPPM 232-233; N08 (C) | **Lo que se decide**: MANDATORY en B, LATER_PHASE en A |
| Aprobado con su acto (la ordenanza o el reconducido) | GOV-BUD-007/008; LOPPM 229, 234-236 | MANDATORY_FOR_V1 |
| Modificaciones: traspaso, crédito adicional, rectificación (3 %) e insubsistencia | GOV-BUD-014/015; LOPPM 241, 242, 247 | MANDATORY_FOR_V1 (tipos LOPPM; límites como dato) |
| Otros tipos de modificación (instructivo N09) | N09 (C) | LATER_PHASE |
| Disponibilidad y certificación | GOV-BUD-009/010; LOPPM 242 | MANDATORY_FOR_V1 |
| Precompromiso o reserva | GOV-BUD-011 («cuando lo utilice») | OPTIONAL_FOR_V1 (activable por ente) |
| Compromiso | GOV-BUD-012; LOPPM 242, 248 | MANDATORY_FOR_V1 |
| Causado (momento presupuestario) | GOV-BUD-013; LOPPM 248-249 | MANDATORY_FOR_V1. El asiento contable va con D-GOV-04 |
| Pagado | GOV-BUD-016; TRE-04 | LATER_PHASE (depende de TRE-04 y del pagador) |
| Saldo y ledger reconstruible | GOV-BUD-016 | MANDATORY_FOR_V1 |
| Cierre y reconducción | GOV-BUD-017; LOPPM 234-236, 248-249 | MANDATORY_FOR_V1 |
| Formularios ONAPRE | GOV-BUD-018 (P1); N07-N10 (C) | LATER_PHASE |
| Contabilidad ONCOP | D-GOV-04 | NOT_IN_SCOPE de D-GOV-02 |

## 2. Opciones (realmente distintas)

### Opción A · Aprobado + ejecución completa; la formulación pasa a una fase posterior

| Campo | Valor |
|---|---|
| SCOPE | Ejercicio, clasificador versionado (modelo), categorías programáticas, fuentes, **aprobado registrado desde su acto** (ordenanza sancionada o reconducido), disponibilidad y certificación, compromiso, causado, modificaciones LOPPM, ledger, cierre y reconducción |
| FUNCTIONAL_LEVEL | Presupuesto antes del gasto, con control legal completo de ejecución |
| BUD_PROCESSES_UNLOCKED | YES: BUD-01, 02, 04, 10. PARTIAL: BUD-03, 05. Construibles: BUD-06, 08, 11, 12 |
| DOWNSTREAM_UNLOCKED | REQ-02, REP-01 (completo) y REP-02 (parcial); prepara CNT-01, TRE-03 y TRE-10 |
| DATA_MODEL_IMPACT | Ejercicio, versión del clasificador y sus partidas, categoría programática, fuente, crédito (aprobado), modificación, movimiento del ledger (compromiso y causado), certificación. Dinero en `NUMERIC` / `Decimal` |
| UI_IMPACT | Menú Gobierno › Presupuesto, en unas 6 pantallas: ejercicio, clasificador, estructura, aprobado, modificaciones, disponibilidad y certificación |
| MIGRATION_IMPACT | Migraciones nuevas detrás de la cabeza vigente (una por ciclo BUD). No toca migraciones publicadas |
| LEGAL_RISK | **Bajo.** Las reglas salen de la LOPPM (clase A, en custodia). Lo clase C se trata como dato o se difiere |
| TENANT_CONFIGURABILITY | Niveles programáticos, límites de traspaso y rectificación, y precompromiso: activables por ente y ejercicio |
| FUTURE_EXPANSION_COST | Bajo. La formulación se añade después como versiones previas (ANTEPROYECTO → PROYECTO) del mismo modelo de presupuesto, sin migrar el aprobado |
| WHAT_IS_DEFERRED | GOV-BUD-006 (escenarios, techos, supuestos), anteproyecto y proyecto como flujo, presupuesto participativo (LOPPM 232), formularios ONAPRE (BUD-13), pagado (TRE-04) |

### Opción B · Formulación completa + ejecución en v1.0

| Campo | Valor |
|---|---|
| SCOPE | Todo lo de A, más el ciclo de formulación: escenarios, techos, anteproyecto, proyecto con POA ante el Concejo antes del 1.º de noviembre, presupuesto participativo y sanción |
| FUNCTIONAL_LEVEL | Ciclo presupuestario completo |
| BUD_PROCESSES_UNLOCKED | Los de A. BUD-05 completo **solo** cuando lleguen N08 y el calendario y manual locales (N37). Hoy sigue bloqueado por fuente externa |
| DOWNSTREAM_UNLOCKED | Los mismos que A; añade REP-02 completo si se construyen las metas |
| DATA_MODEL_IMPACT | A + escenarios, techos, supuestos, versiones de formulación, flujo con el Concejo y el CLPP |
| UI_IMPACT | A + unas 4 pantallas de formulación |
| MIGRATION_IMPACT | Mayor (unas 2 migraciones más) |
| LEGAL_RISK | **Medio-alto.** Los formularios y la mecánica de formulación dependen de N08 (C, no custodiado) y del manual local (N37) |
| TENANT_CONFIGURABILITY | Igual que A, más el calendario local de formulación |
| FUTURE_EXPANSION_COST | Bajo, pero con alto coste inmediato |
| WHAT_IS_DEFERRED | Formularios ONAPRE y pagado |

### Opción C · Control mínimo de disponibilidad (aprobado plano + compromiso)

| Campo | Valor |
|---|---|
| SCOPE | El aprobado por partida, sin estructura programática ni fuentes; disponibilidad y compromiso. Sin modificaciones, ledger completo ni cierre |
| FUNCTIONAL_LEVEL | Un candado de gasto |
| BUD_PROCESSES_UNLOCKED | BUD-01 y BUD-02 en parte; BUD-06 y BUD-08 en parte |
| DOWNSTREAM_UNLOCKED | REQ-02 (débil) |
| DATA_MODEL_IMPACT | Pequeño, pero habría que **migrar los datos** después para añadir las categorías |
| UI_IMPACT | Unas 3 pantallas |
| MIGRATION_IMPACT | Pequeño ahora; grande más adelante |
| LEGAL_RISK | **Alto.** Contradice LOPPM 239 (gastos por categorías programáticas) y deja sin cubrir los P0 GOV-BUD-014..017 |
| TENANT_CONFIGURABILITY | Baja |
| FUTURE_EXPANSION_COST | Alto |
| WHAT_IS_DEFERRED | Modificaciones, ledger, cierre, fuentes y categorías: casi toda la cadena P0 |
