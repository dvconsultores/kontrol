# CTL08_MASTER_INVENTORY

Evidencia en `resources/backend/app/modules/government/` y `resources/frontend/src/modules/gobierno/`, a `cca6b73`.

| MASTER_ID | REQUIREMENT_NAME | GOVERNMENT_OWNER_PROCESS | MODEL | TABLE | API | UI | MUTATION | CURRENT_HISTORY | CURRENT_AUDIT | IMMUTABLE_HISTORY | STATUS | EVIDENCE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ACCOUNTS (bancarias) | cuentas | TRE-01 | 1 | `gov_bank_accounts` | 1 | 1 | 1 | Parcial: eventos, sin valores en la edición | 1 | 1 | EXISTS, significado sin fijar | `GovernmentBankAccountHistory`, `service_cuentas.py`, `CuentaPage.tsx` |
| ACCOUNTS (contables) | cuentas | ACC-01 | 0 | — | 0 | 0 | 0 | 0 | 0 | 0 | ABSENT, BLOCKED | GOV-ACC-002; D-GOV-04, N36 |
| SUPPLIERS | proveedores | PROC-01 / GOV-ACC-009 | 0 | — | 0 | 0 | 0 | 0 | 0 | 0 | ABSENT, BLOCKED | Sin modelo de terceros en Gobierno; PROC-01 bloqueado por N37. No se importa el maestro de Empresas |
| BANKS | bancos | TRE-01 | 1 | `gov_banks` | 1 | 1 | 1 | 0 | Parcial: solo nombres de campos | 0 | EXISTS | `GovernmentBank`, `editar_banco`, `BancosPage.tsx` sin historia |
| APPROVAL_RULES | reglas de aprobación | CTL-01, ORG-03, CTL-10 | Parcial | `gov_sod_rules`, competencias, políticas de cierre | 1 | 1 | 1 | Parcial | 1 | 1 en SoD y políticas | PARTIAL_EQUIVALENT | Sin maestro autónomo de niveles de aprobación |
| CLASSIFIERS | clasificadores | BUD-02 | 0 | — | 0 | 0 | 0 | 0 | 0 | 0 | ABSENT, BLOCKED | D-GOV-02, N10 |

No son clasificadores: `gov_cash_items` (rubros del ente, TRE-02).

## Cuentas

La IR no define «cuentas» en GOV-CTL-010. Existen dos lecturas con apoyo: **bancarias** (GOV-TRE-001; N23 las nombra) y **contables** (GOV-ACC-002, «Versionar plan de cuentas»). Que «bancos» figure aparte no descarta ninguna: una cuenta bancaria es un objeto distinto de su banco. Tampoco se descarta la lectura inclusiva. N20 y N23 no resuelven.

ACCOUNTS_MEANING = UNRESOLVED. **OQ-CTL08-01**, de la dueña, abierta y no resuelta en silencio. Solo la lectura «únicamente bancarias» dejaría este maestro satisfecho, y aun así proveedores y clasificadores seguirían ausentes.

## Proveedores

SUPPLIER_GOVERNMENT_MASTER_EXISTS = 0. Crear el maestro sería construir GOV-ACC-009/PROC-01, otro proceso, bloqueado. Importarlo de Empresas está prohibido.

## Bancos

BANK_MASTER_EXISTS = 1, MUTABLE = 1, HISTORY_EXISTS = 0, AUDIT_EXISTS = 1. `GOV_BANK_UPDATED` guarda el código y los nombres de los campos, no los valores.

## Reglas de aprobación

APPROVAL_RULE_MASTER_EXISTS = PARTIAL. La IR (línea 84) versiona «niveles de aprobacion», y GOV-ORG-003 asigna límites por cargo. Lo existente:

- `gov_sod_rules` prohíbe combinaciones; no fija quién aprueba.
- Competencias y límites por cargo (ORG-03), versionados con el cargo.
- Políticas de cierre (CTL-10) con historia propia.
- Matriz de autoridad (ORG-07): lectura a fecha.
- Motor de aprobaciones 045: compartido, no es maestro de Gobierno.

GENERIC_APPROVAL_ENGINE_REQUIRED = 0. Falta decidir cuáles de estos objetos cuentan como «regla de aprobación»; se fija al reabrir CTL-08.

## Clasificadores

CLASSIFIER_MASTER_EXISTS = 0. No se crea BUD-02/BUD-01 en este ciclo.
