# Tarjeta de prueba de la dueña · PROC-08 con límite de autoridad en otra moneda (delta X08, 2026-11-15)

```text
MENÚ: Gobierno · Contrataciones › Expedientes › (abrir un expediente) › sección «Recomendación y decisión»
TASA: Gobierno · Tesorería › Tasas oficiales (TRE-09)
```

Preparación: un expediente con recomendación vigente cuya Opción 1 tenga monto declarado en USD (por ejemplo, 50.000,01 USD), y tres actos de
decisión emitidos con fecha de hoy: uno de un cargo con límite **en VES insuficiente**, uno con límite **en VES suficiente** y uno con límite **en EUR**.
Registre y apruebe (con otro usuario aprobador) una tasa USD con fecha efectiva de hoy o anterior. No registre ninguna tasa EUR.

| Paso | Qué hacer | Qué debe ver |
|---|---|---|
| 1 | En «Decisión», elija el acto del cargo con límite en EUR y «Adjudicada» | Panel «Control del límite de autoridad»: **Sin tasa oficial aprobada**, mensaje en rojo que pide registrar la tasa en Tesorería → Tasas oficiales; no aparece bloque de tasa |
| 2 | Registre y confirme | Aviso: «No hay tasa oficial BCV aprobada aplicable al …». No se registra nada |
| 3 | Cancele y elija el acto del cargo con límite en VES insuficiente | Bloque **Tasa oficial BCV utilizada**: «1 USD = … VES · vigente desde … · versión 1», la fuente BCV, el equivalente de la oferta y el del límite; resultado **Excede el límite** |
| 4 | Registre y confirme | Aviso «… equivale a … VES y excede el límite de aprobación …». No se registra nada |
| 5 | Cancele y elija el acto del cargo con límite en VES suficiente | «Dentro del límite», con la misma tasa y los equivalentes |
| 6 | Registre y confirme | DEC-01 Adjudicada. En su ficha aparece **Conversión de autoridad de DEC-01** con la tasa, la fuente y los equivalentes usados |
| 7 | Corrija o anule después la tasa USD en Tesorería y vuelva al expediente | La ficha de DEC-01 conserva la tasa con la que se decidió: la conversión guardada no se recalcula |
| 8 | Abra la bitácora del expediente | «Adjudicación bloqueada por el límite de la autoridad» con causal `GOV_OFFICIAL_RATE_REQUIRED` o de exceso, **sin importes**; «Decisión del procedimiento emitida» con la tasa usada (id y versión) |
| 9 | Pruebe en el móvil (390 o 320 px) | El panel y la ficha en una columna, sin desplazamiento horizontal |

Con la misma moneda en la oferta y el límite no se consulta ninguna tasa: el comportamiento del delta AAL no cambia.

## Límites declarados (no son fallos)

- La fecha de la tasa es la fecha del acto de decisión (la misma con la que se verifica la competencia).
- La tasa es la aprobada más reciente con fecha efectiva igual o anterior; no hay respaldo, tasa privada ni consulta externa.
- No hay reporte nuevo (REPORTING=NOT_APPLICABLE).
- CNT-01 (contratos) no se toca: es de P2.

`OWNER_ACCEPTED`: NO. Solo la dueña lo concede.
