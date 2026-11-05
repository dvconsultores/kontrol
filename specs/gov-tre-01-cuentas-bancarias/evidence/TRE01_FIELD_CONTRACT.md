# GOV-TRE-01 · contrato de campos

Comunes a todos los campos:
- **SOURCE_REQUIREMENT:** GOV-TRE-001, salvo que se indique otra fuente.
- **ROLE_VISIBILITY:** `gobierno_cuentas:view`.
- **Edición de datos de la cuenta:** `gobierno_cuentas:manage`, solo en BORRADOR.
- **Error de validación:** 422 `GOV_BANK_ACCOUNT_INVALID`.

| FIELD_ID | LABEL | BUSINESS_MEANING | TYPE | DB_TYPE | API_TYPE | REQUIRED | DEFAULT | CATALOG | VALIDATION | MASKING | ROLE_EDITABILITY | STATE_VISIBILITY | STATE_EDITABILITY | HISTORY | AUDIT | ERROR | HELP_TEXT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B01 | Código del banco | código de 4 dígitos que encabeza sus cuentas | texto | String(4) | string | sí | — | — | 4 dígitos; único por empresa | no | manage, solo al crear | todos | nunca | — | GOV_BANK_CREATED | GOV_BANK_CODE_DUPLICATE | «Los 4 primeros dígitos de las cuentas de este banco» |
| B02 | Nombre | nombre del banco | texto | String(120) | string | sí | — | — | 3–120 | no | manage | todos | siempre | — | GOV_BANK_UPDATED | 422 | — |
| B03 | Estado | si se ofrece para cuentas nuevas | enum | String(10) | enum | sí | ACTIVO | ACTIVO, INACTIVO | lista cerrada | no | manage | todos | siempre | — | GOV_BANK_UPDATED | 422 | «Las cuentas existentes no cambian» |
| C01 | Código | identificador interno | sistema | String(20) | string | sí | CB-AAAA-NNNN | — | único por empresa | no | nadie | todos | nunca | CREADA | GOV_BANK_ACCOUNT_CREATED | 409 | — |
| C02 | Denominación | para qué es la cuenta | texto | String(200) | string | sí | — | — | 3–200 | no | manage | todos | BORRADOR | EDITADA | _UPDATED | 422 | «Por ejemplo: Fondos de funcionamiento» |
| C03 | Banco | entidad bancaria | FK | String(36) FK gov_banks | uuid | sí | — | gov_banks ACTIVO | misma empresa | no | manage | todos | BORRADOR | EDITADA | _UPDATED | 422 | — |
| C04 | Tipo | tipo de cuenta | enum | String(10) | enum | sí | — | CORRIENTE, AHORRO (OD-TRE01-05) | lista cerrada | no | manage | todos | BORRADOR | EDITADA | _UPDATED | 422 | — |
| C05 | Número | número de 20 dígitos | texto | String(20) | string, solo en `/numero` y en la entrada | sí | — | — | 20 dígitos; empieza por B01; único por empresa y banco | `numero_enmascarado` ••••NNNN; completo con manage y auditado | manage | todos, enmascarado | BORRADOR | EDITADA, solo enmascarado | _UPDATED, _NUMBER_VIEWED, sin el completo | 422, 409 GOV_BANK_ACCOUNT_DUPLICATE | «20 dígitos, sin guiones» |
| C06 | Moneda | moneda de la cuenta | enum | String(3) | enum | sí | — | VES, USD, EUR (ORG-03) | lista cerrada | no | manage | todos | BORRADOR | EDITADA | _UPDATED | 422 | — |
| C07 | Vigente desde | inicio de la vigencia | fecha | Date | date | sí | — | — | fecha civil | no | manage | todos | BORRADOR | EDITADA | _UPDATED | 422 | — |
| C08 | Vigente hasta | fin de la vigencia | fecha | Date | date | no | — | — | ≥ C07 | no | manage | todos | BORRADOR; lo fija el cierre | EDITADA, CERRADA | _UPDATED, _CLOSED | 422 | «Déjelo vacío si no tiene fin previsto» |
| C09 | Estado | ciclo de vida | enum | String(10) | enum | sí | BORRADOR | BORRADOR, VIGENTE, INACTIVA, CERRADA | máquina de estados | no | activate (MFA) | todos | por acción | cada cambio | el de cada acción | 409 _INVALID_STATE | — |
| C10 | Acto habilitante | decisión que habilita la cuenta | FK | String(36) FK gov_acts | objeto | para activar | — | gov_acts EMITIDO, EFICAZ | misma empresa; fecha ≤ hoy | no | manage | todos | BORRADOR, VIGENTE, INACTIVA | ACTO_VINCULADO | _ACT_LINKED | 422, 409 _ACT_WITHOUT_EFFECT | «Debe estar emitido o eficaz» |
| C11 | Acto sin efecto | el acto fue revocado o anulado | derivado | — | bool | — | false | — | derivado al leer | no | nadie | todos | nunca | — | — | — | aviso en la ficha |
| C12 | Motivo | por qué se inactiva, reactiva o cierra | texto | historia; String(500) al cerrar | string | sí, en esas acciones | — | — | 10–500 | no | activate (MFA) | VIGENTE, INACTIVA, CERRADA | en la acción | INACTIVADA, REACTIVADA, CERRADA | el de la acción | 422 | — |
| C13 | Fecha de cierre | cuándo se cerró la cuenta | fecha | Date | date | sí, al cerrar | — | — | ≥ C07; ≤ hoy | no | activate (MFA) | CERRADA | en la acción | CERRADA | _CLOSED | 422 | — |
| A01 | Cargo autorizado | cargo institucional autorizado | FK | String(36) FK gov_positions + instantánea | uuid + textos | sí | — | gov_positions VIGENTE (OD-TRE01-01) | misma empresa; estructura vigente; sin otra en vigor | no | manage | todos | salvo CERRADA | AUTORIZADO_ALTA | GOV_BANK_AUTHORIZATION_ADDED | 422, 409 _AUTHORIZATION_DUPLICATE | «Un cargo, no una persona» |
| A02 | Acto de alta | acto que autoriza al cargo | FK | String(36) FK gov_acts | objeto | sí | — | gov_acts EMITIDO, EFICAZ | misma empresa; fecha ≤ hoy | no | manage | todos | en el alta | AUTORIZADO_ALTA | _ADDED | 422, 409 _ACT_WITHOUT_EFFECT | — |
| A03 | Autorizado desde | inicio de la autorización | fecha | Date | date | sí | — | — | ≥ C07; ≤ C08; ≤ hoy | no | manage | todos | en el alta | AUTORIZADO_ALTA | _ADDED | 422 | — |
| A04 | Autorizado hasta | fin de la autorización | fecha | Date | date | sí, al terminar | — | — | ≥ A03; ≤ hoy | no | manage | todos | al terminar | AUTORIZADO_FIN | _ENDED | 422 | — |
| A05 | Acto de fin | acto que termina la autorización | FK | String(36) FK gov_acts | objeto | sí, salvo en el cierre | — | gov_acts EMITIDO, EFICAZ | misma empresa; fecha ≤ hoy | no | manage | todos | al terminar | AUTORIZADO_FIN | _ENDED | 422 | — |
| A06 | Motivo de fin | por qué termina | texto | String(500) | string | sí, al terminar | — | — | 10–500 | no | manage | todos | al terminar | AUTORIZADO_FIN | _ENDED | 422 | — |

MISSING_REQUIRED_FIELDS = 0.
