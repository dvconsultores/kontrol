# Data Model: TRE-02

Todas las tablas son de alcance empresa. Importes `NUMERIC(18,2)`. Sin JSON de dinero. Sin FK compuestas con `company_id`, por norma del repositorio: la empresa cruzada se valida en el servicio y en los controles de integridad.

## gov_cash_items (Rubro)
`tenant_id`, `company_id`, `codigo` (hasta 20), `nombre` (3–120), `tipo` INGRESO|DESEMBOLSO, `estado` ACTIVO|INACTIVO, `version`, autoría. Único: empresa + código. El tipo no cambia tras crearse.

## gov_cash_programs (Programa)
`tenant_id`, `company_id`, `codigo` `PF-AAAA-MON`, `ejercicio`, `moneda` VES|USD|EUR, `mes_inicial` 1–12, `estado` BORRADOR|VIGENTE|CERRADO|DESCARTADO, `cerrado_por`, `cerrado_en`, `motivo_cierre`, `version` (control de concurrencia), autoría.

Índice único parcial: empresa + ejercicio + moneda donde estado ≠ DESCARTADO. Check de cierre completo. Sin borrado.

## gov_cash_program_versions (Versión)
`program_id`, `company_id`, `numero`, `estado` BORRADOR|VIGENTE|SUPERADA|DESCARTADA|CERRADA, `motivo` (nulo en la 1), `activada_por`, `activada_en`, autoría.

Único: programa + número. Índices únicos parciales: un BORRADOR por programa; una VIGENTE por programa. Sin borrado.

## gov_cash_program_declarations (Declaración)
`program_id`, `company_id`, `account_id` (FK `gov_bank_accounts`), `monto` ≥ 0, `fecha_corte`, `fundamento` (10–500), autoría. Único: programa + cuenta. Pertenece al programa, no a la versión (FR-005). Disparador: sin cambios si el programa no está en BORRADOR.

## gov_cash_program_lines (Línea)
`version_id`, `company_id`, `item_id` (FK), `mes` 1–12, `monto` > 0, autoría. Único: versión + rubro + mes. Disparador: sin alta, cambio ni baja si la versión no está en BORRADOR.

## gov_cash_program_history (Historia)
`program_id`, `company_id`, `version_numero`, `tipo` CREADO|DECLARACION|LINEA|ACTIVADO|REPROGRAMADO|DESCARTADO|CERRADO, `detalle`, autoría. Inmutable por disparador.

## Estados

| Desde | Acción | Capacidad | Condición | A | Motivo | Documento | Auditoría | MFA | Reversible |
|---|---|---|---|---|---|---|---|---|---|
| — | Crear | manage | sin programa no descartado para ejercicio y moneda | programa BORRADOR, versión 1 BORRADOR | — | — | GOV_CASH_PROGRAM_CREATED | no | descartar |
| versión BORRADOR | Declaración, línea | manage | FR-004, FR-006, FR-013 | igual | fundamento | — | GOV_CASH_PROGRAM_UPDATED | no | sí, en borrador |
| versión BORRADOR | Activar | activate | ≥1 declaración, ≥1 línea | VIGENTE; la anterior SUPERADA | — | — | GOV_CASH_PROGRAM_ACTIVATED | sí | por reprogramación |
| programa VIGENTE | Reprogramar | manage | sin borrador; ejercicio no terminado | versión nueva BORRADOR | 10–500 | — | GOV_CASH_PROGRAM_REVISED | no | descartar |
| versión BORRADOR | Descartar | manage | — | DESCARTADA; el programa solo pasa a DESCARTADO si era la versión 1 | — | — | GOV_CASH_PROGRAM_DISCARDED | no | no |
| programa VIGENTE | Cerrar | activate | sin borrador | programa CERRADO, versión CERRADA | 10–500 | — | GOV_CASH_PROGRAM_CLOSED | sí | no |

## Cálculo (al leer, por versión)
Para cada mes desde `mes_inicial` hasta 12: `inicial`, `ingresos`, `desembolsos`, `final`, `deficit` (final < 0). `inicial` del primer mes = suma de declaraciones. Exacto en `Decimal`.
