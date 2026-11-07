# EXISTING_HISTORY_MATRIX

Evento de auditoría e historia completa no son lo mismo: el evento dice que algo cambió; la historia exigida dice de qué valor a qué valor. Medido en el código a `cca6b73`, no ejecutado.

| Campo | Cuentas bancarias | Bancos | Reglas SoD | Rubros de caja (fuera de alcance) |
|---|---|---|---|---|
| CREATE_AUDITED | 1 | 1 | 1 | 1 |
| UPDATE_AUDITED | 1 | 1 | 1 | 1 |
| DELETE_AUDITED | No aplica: BD impide borrar | Sin operación de borrar; BD no lo impide | No aplica: BD impide borrar | Sin operación de borrar |
| BEFORE_STATE | 0 | 0 | 0 | 0 |
| AFTER_STATE | Parcial: nombres de campos y número enmascarado | Parcial: nombres de campos | Parcial: nombres de campos | Parcial |
| ACTOR | 1 | 1 | 1 | 1 |
| EFFECTIVE_ACTOR | Según bitácora común | Igual | Igual | Igual |
| ROLE, UNIT | 0 en la historia | 0 | 0 | 0 |
| TIMESTAMP | 1 | 1 | 1 | 1 |
| CORRELATION | Evento de bitácora, no la historia | Igual | Igual | Igual |
| REASON | Solo inactivar, reactivar, cerrar | 0 | Solo cerrar | 0 |
| SOURCE | Bitácora | Bitácora | Bitácora | Bitácora |
| SUPPORT | Acto en las autorizaciones | 0 | 0 | 0 |
| IMMUTABLE_DB | 1 en `gov_bank_account_history` | 0 | 1 en `gov_sod_rule_history` | 0 |
| QUERYABLE | 1, en `CuentaPage` | Solo bitácora | 1, en `ReglaSodPage` | Solo bitácora |
| EXPORTABLE | 0 como historial | 0 | 0 | 0 |

## Contrato exigible

CTL08_HISTORY_CONTRACT = CHANGE_HISTORY_WITH_BEFORE_AFTER: qué cambió, cuándo, quién, en qué maestro y registro, de qué valor a qué valor, y por qué cuando el proceso lo exija.

Hoy ningún maestro lo cumple: tampoco las historias inmutables guardan valores anterior y nuevo en la edición.

## Arquitectura si se reabre

CTL08_ARCHITECTURE_MODE = C: historias por maestro con consulta unificada de Gobierno. Las que existen ampliarían su detalle y bancos tendría tabla propia. Sin motor genérico, sin tocar `record_audit` ni el núcleo de auditoría 006/051. Esto es una intención de diseño: no se ha construido nada.

Datos anteriores a esa ampliación no podrán reconstruir sus valores; el producto deberá decirlo y no inventarlos.

## Fronteras

- **CTL-04 y DOC-08:** muestran y empaquetan evidencia; no conservan historial de maestros. No se duplican.
- **CTL-01:** decide conflictos; CTL-08 solo mostraría cambios de sus reglas.
