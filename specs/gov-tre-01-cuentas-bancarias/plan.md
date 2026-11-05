# Plan · GOV-TRE-01 Cuentas bancarias públicas (TRE-01, GOV-TRE-001)

## Decisiones de arquitectura

| Id | Decisión | Razón |
|---|---|---|
| AD-TRE01-01 | `service_cuentas.py`, `schemas_cuentas.py` y `api_cuentas.py` bajo `/gobierno/tesoreria`, dentro de `app/modules/government`; guardas permiso → empresa → módulo | Mismo patrón que los procesos de Gobierno. El módulo privado `treasury` no se toca |
| AD-TRE01-02 | Cuatro tablas: `gov_banks`, `gov_bank_accounts`, `gov_bank_account_authorizations`, `gov_bank_account_history` | Tablas propias de Gobierno: la matriz de reutilización prohíbe las privadas |
| AD-TRE01-03 | Cuentas no borrables e historia inmutable por disparadores en PostgreSQL, como CTL-01 | La historia debe poder reconstruirse |
| AD-TRE01-04 | Índice único parcial `(account_id, position_id) WHERE vigente_hasta IS NULL` y único `(company_id, bank_id, numero)` | Una carrera no puede duplicar: la base lo garantiza |
| AD-TRE01-05 | `acto_sin_efecto` es derivado al leer, no una columna | Un cambio en DOC-02 no debe escribir en Tesorería; no hay dos fuentes de verdad |
| AD-TRE01-06 | El número solo sale por `GET /cuentas/{id}/numero`, auditado | Una sola salida, fácil de auditar y de probar |
| AD-TRE01-07 | La guarda SoD de CTL-01 se integra en las escrituras de TRE-01 y su catálogo gana el proceso `TRE-01` | Reutiliza la guarda única; no se crea ninguna regla |

## Decisiones de diseño (de Claude, dentro de las de la dueña)

- **PDD-TRE01-01:** código `CB-<año de Caracas>-<nnnn>` por empresa; si choca por concurrencia, 409.
- **PDD-TRE01-02:** moneda con el vocabulario `MONEDAS_LIMITE` de ORG-03.
- **PDD-TRE01-03:** activar y reactivar exigen ≥1 autorizado en vigor: una cuenta vigente sin autorizados no tiene sentido operativo.
- **PDD-TRE01-04:** el cierre termina los autorizados en vigor con motivo «Cierre de la cuenta» y sin acto de fin.
- **PDD-TRE01-05:** sin CSV en este ciclo: los filtros de S1 cubren la consulta por banco, moneda, cargo y estado, y el requisito no pide exportación.
- **PDD-TRE01-07:** alta y fin de una autorización llevan fecha ≤ hoy: se registra un hecho ocurrido. Así `en_vigor` equivale a `vigente_hasta` nulo y el índice único parcial basta.
- **PDD-TRE01-08:** número y código del banco se validan en el servicio, no en el esquema: un 422 del esquema repetiría el valor recibido.
- **PDD-TRE01-09:** se puede dejar una cuenta VIGENTE sin autorizados (reduce exposición) y la ficha lo avisa.
- **PDD-TRE01-06:** la autorización exige el cargo VIGENTE al darla de alta; si deja de estarlo, se avisa y no se termina sola.

## Puerta de la Constitución

| Compuerta | Valor |
|---|---|
| GOV_POST_E2E_INTEGRITY_RUNNER_VERSIONED · CURRENT_GOV_POST_E2E_INTEGRITY | 1 · PASS (`2b1dc6f`, 58 controles, 0 violaciones) |
| Rama / remotas / HEAD == origin | develop / 1 / 1 |
| TRE01_REQUIREMENTS_COMPLETE · FULL_PROCESS_IMPLEMENTABLE | 1 · 1 |
| AUTHORIZED_PARTY_SEMANTICS_RESOLVED · ORG06_DEPENDENCY_REQUIRED | 1 · 0 |
| BANK · ACCOUNT · ACCOUNT_TYPE · CURRENCY · ENABLING_ACT · AUTHORIZATION_HISTORY · STATE_MACHINE | 1 (todos) |
| PRIVATE_REUSE_MATRIX · MENU · ROLE_MATRIX · AUDIT · OWNER_UAT_SCENARIO | 1 (todos) |
| SCREEN_FORM_MATRIX · FIELD_CONTRACT | 1 · 1 (`evidence/TRE01_SCREEN_FORM_MATRIX.md`, `evidence/TRE01_FIELD_CONTRACT.md`) |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 · 0 · 0 · 0 |

**GATE = PASS.** Autorización de `implement`: el encargo GOV-TRE-FUNCTIONAL-01 de la dueña, que nombra TRE-01.
