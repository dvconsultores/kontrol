# N10 — RECONCILIACIÓN DE CIFRAS HISTÓRICAS

No se borra nada. Cada cifra queda como `vigente`, `superada` o `histórica
correcta`, con el motivo.

| Cifra | Histórica | Vigente | Estado | Motivo |
|---|---:|---:|---|---|
| Modelos ORM | 153 | **166** | superada | 153 fue el recuento de N0, antes de que N3–N8 añadieran y consolidaran. `pre-backfill-gate.md` la arrastraba junto al 166, contradiciéndose en la misma línea |
| Tablas | 166 | **166** | vigente | Coincide con los modelos: cada modelo es una tabla |
| Rutas derivadas | 35 / 36 | **41** | superada | 36 era el recuento de rutas de empresa. N10 añadió las cinco que faltaban por declarar: cuatro de tenant por `user_id → users` y una por `role_id → roles` |
| Uniques | 13 | 31 → **80** restricciones + 214 índices | superada | El 13 ya lo corrigió `clarifications.md`. El 31 contaba lo revisado en N7, no lo existente; N10 cuenta el catálogo entero |
| `ResourceKind` | 19 | **23** | superada en N9 | 19 registrados + 4 exigidos por `REM-046-001` |
| Rutas HTTP | 294 | **294** | vigente | Sin cambios: N10 no añadió ni retiró rutas |
| Operaciones HTTP | 404 | **404** | vigente | |
| Operaciones con cabecera de empresa | 332 | **342** | superada | Las diez rutas que N10 dotó de contexto ahora la declaran |
| Claves foráneas | 336 | **331** | superada | El 336 contaba **columnas** con clave foránea; 331 son **restricciones**. Las cinco compuestas de almacén cuentan una vez cada una, no dos |
| Columnas `company_id` | 107 | **107** | vigente | `0039` retiró `tenant_id`, no `company_id` |
| Columnas `tenant_id` | 10 | **5** | superada | `0039` retiró las cinco columnas abandonadas |
| Migraciones | 38 | **39** | superada | `0039_n10_scope_reconciliation` |
| `legacy_scope_id` en ejecución | 0 | **0** | vigente | |

## Sobre el 336 de claves foráneas

Es el caso en que N10 se equivocó primero y se corrigió después. La primera
medición contó las claves foráneas **por columna** y reportó cinco desviaciones
en las tablas de estructura de almacén: el ORM parecía declarar una clave simple
donde la base tenía una compuesta.

No había tal desviación. El ORM declara la compuesta correctamente en
`__table_args__`, y SQLAlchemy la refleja también en cada columna; lo que estaba
mal era la forma de contar. Se rehízo la medición sobre
`table.foreign_key_constraints` y la diferencia desapareció.

Queda escrito porque el error tiene la misma forma que los que esta remediación
persigue: un instrumento que informa de una diferencia que no existe es tan
inútil como uno que calla una que sí.

## Marcado

Los artefactos que conservan cifras superadas las mantienen como historia y no
las presentan como vigentes. La única baseline vigente es
`n10-final-authoritative-baseline.md`.
