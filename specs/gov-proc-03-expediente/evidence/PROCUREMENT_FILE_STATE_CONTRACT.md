# PROCUREMENT_FILE_STATE_CONTRACT · PROC-03

## SOURCE_BACKED_STATE

Ninguno. LCP arts. 19-20 y RLCP arts. 31-33 no definen estados del expediente. El único hecho con efecto citado, «culminada la selección» (art. 20),
pertenece a PROC-08, que no existe: este ciclo no lo representa.

## DERIVED_IMPLEMENTATION_STATE (sin efecto jurídico)

| Estado | Etiqueta | Por qué existe | Qué permite | Cómo se entra |
|---|---|---|---|---|
| `ABIERTO` | En curso | El expediente admite incorporaciones | Todo | Al crearlo |
| `CERRADO` | Cerrado | Dejar de admitir incorporaciones; no adjudica ni termina nada | Solo consulta | `close` con MFA, fecha y motivo |
| `DESCARTADO` | Descartado | Corregir uno creado por error sin borrar su rastro | Solo consulta | `manage`, con motivo, y solo sin folios, actuaciones ni hitos |

No hay borrador, aprobación ni adjudicación. El número sigue ocupado tras descartar. No hay reapertura en este ciclo.

## Hitos (derivado)

`PREVISTO` → `CUMPLIDO` (hay fecha real) | `NO_APLICA` (con motivo). `fecha_superada` no se guarda: compara la fecha prevista con hoy y no es un vencimiento legal.

## Backend = autoridad

Toda transición la decide el servicio bajo bloqueo de la fila y con If-Match. Pendientes y siguiente acción orientan: no bloquean ni deciden.
