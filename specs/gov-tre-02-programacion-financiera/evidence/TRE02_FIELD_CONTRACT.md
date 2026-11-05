# GOV-TRE-02 · contrato de campos

Comunes: SOURCE_REQUIREMENT GOV-TRE-002; ROLE_VISIBILITY `gobierno_caja:view`; error de validación 422 `GOV_CASH_PROGRAM_INVALID`. Importes en la moneda del programa (CURRENCY).

| FIELD_ID | LABEL | BUSINESS_MEANING | TYPE | DB_TYPE | API_TYPE | REQUIRED | DEFAULT | CATALOG | CURRENCY | VALIDATION | ROLE_EDITABILITY | STATE_VISIBILITY | STATE_EDITABILITY | HISTORY | AUDIT | ERROR | HELP_TEXT |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| R01 | Código | identifica el rubro | texto | String(20) | string | sí | — | — | — | 1–20; único por ente | manage, al crear | todos | nunca | — | ITEM_CREATED | ITEM_DUPLICATE | — |
| R02 | Nombre | qué agrupa | texto | String(120) | string | sí | — | — | — | 3–120 | manage | todos | siempre | — | ITEM_UPDATED | 422 | — |
| R03 | Tipo | ingreso o desembolso | enum | String(12) | enum | sí | — | INGRESO, DESEMBOLSO | — | lista cerrada | manage, al crear | todos | nunca | — | ITEM_CREATED | 422 | «No se puede cambiar después» |
| R04 | Estado | si se ofrece en líneas nuevas | enum | String(10) | enum | sí | ACTIVO | ACTIVO, INACTIVO | — | lista cerrada | manage | todos | siempre | — | ITEM_UPDATED | 422 | «Las líneas existentes no cambian» |
| P01 | Código | identifica el programa | sistema | String(20) | string | sí | PF-AAAA-MON | — | — | único | nadie | todos | nunca | CREADO | PROGRAM_CREATED | — | — |
| P02 | Ejercicio | año programado | número | Integer | int | sí | año en curso | — | — | 2000–2100; ≥ año en curso − 1 | manage, al crear | todos | nunca | CREADO | PROGRAM_CREATED | _DUPLICATE | — |
| P03 | Moneda | moneda del programa | enum | String(3) | enum | sí | — | VES, USD, EUR | sí | lista cerrada | manage, al crear | todos | nunca | CREADO | PROGRAM_CREATED | 422 | «Cada moneda tiene su programa» |
| P04 | Mes inicial | primer mes programado | número | SmallInteger | int | sí | 1 | 1–12 | — | 1–12 | manage, al crear | todos | nunca | CREADO | PROGRAM_CREATED | 422 | — |
| P05 | Estado | ciclo de vida | enum | String(10) | enum | sí | BORRADOR | BORRADOR, VIGENTE, CERRADO, DESCARTADO | — | máquina | activate, manage | todos | por acción | cada cambio | el de la acción | _INVALID_STATE | — |
| V01 | Versión | número de versión | sistema | Integer | int | sí | 1 | — | — | único por programa | nadie | todos | nunca | REPROGRAMADO | PROGRAM_REVISED | — | — |
| V02 | Motivo | por qué se reprograma o cierra | texto | String(500) | string | sí, en esas acciones | — | — | — | 10–500 | manage, activate | todos | en la acción | REPROGRAMADO, CERRADO | PROGRAM_REVISED, CLOSED | 422 | — |
| D01 | Cuenta | cuenta de TRE-01 | FK | String(36) | uuid + textos | sí | — | cuentas VIGENTE de la moneda | sí | misma empresa y moneda | manage | todos | BORRADOR v1 | DECLARACION | PROGRAM_UPDATED | 422, _DECLARATION_DUPLICATE | — |
| D02 | Disponibilidad declarada | cuánto declara Tesorería | decimal | Numeric(18,2) | string | sí | — | — | sí | ≥ 0; 2 decimales | manage | todos | BORRADOR v1 | DECLARACION | PROGRAM_UPDATED | 422 | «Declarada por Tesorería bajo su responsabilidad» |
| D03 | Fecha de corte | a qué fecha | fecha | Date | date | sí | hoy | — | — | ≤ hoy | manage | todos | BORRADOR v1 | DECLARACION | PROGRAM_UPDATED | 422 | — |
| D04 | Fundamento | en qué se basa | texto | String(500) | string | sí | — | — | — | 10–500 | manage | todos | BORRADOR v1 | DECLARACION | PROGRAM_UPDATED | 422 | «Por ejemplo: estado de cuenta al corte» |
| L01 | Rubro | clase de ingreso o desembolso | FK | String(36) | uuid + textos | sí | — | rubros ACTIVO | — | misma empresa | manage | todos | BORRADOR | LINEA | PROGRAM_UPDATED | 422, _LINE_DUPLICATE | — |
| L02 | Mes | mes programado | número | SmallInteger | int | sí | — | meses del programa | — | ≥ mes inicial; en reprogramación ≥ mes en curso | manage | todos | BORRADOR | LINEA | PROGRAM_UPDATED | 422, _PAST_MONTH | — |
| L03 | Monto | importe programado | decimal | Numeric(18,2) | string | sí | — | — | sí | > 0; 2 decimales | manage | todos | BORRADOR | LINEA | PROGRAM_UPDATED | 422 | — |
| C01 | Disponibilidad inicial, ingresos, desembolsos, final | cálculo mensual | derivado | — | string | — | — | — | sí | fórmula FR-007 | nadie | todos | nunca | — | — | — | «Proyección de caja: no es disponibilidad presupuestaria ni saldo bancario» |

MISSING_REQUIRED_FIELDS = 0.
