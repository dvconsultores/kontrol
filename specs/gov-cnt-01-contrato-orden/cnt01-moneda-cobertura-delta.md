# Delta CNT-01 · moneda canónica, firmante multimoneda y cobertura frente a compromisos (2026-11-15)

Spec dueña: `specs/gov-cnt-01-contrato-orden`. El delta cierra dos decisiones de la dueña recogidas en el encargo de CNT-02 (§4–§14):
- **OBS-CNT01-BUD08-01** queda CERRADA: la cobertura de CNT-01 es documental. CNT-01 no crea compromiso ni consume disponibilidad, y BUD-08 sigue siendo la única autoridad del compromiso.
- **OBS-CNT01-TRE09-01** queda CERRADA: CNT-01 usa `canonical_currency` (VED → VES, factor 1, no es FX) y el límite del firmante se compara con TRE-09.

No crea fila de proceso (`PROCESS_ROW_COUNT_CHANGE=0`). Lo ejecuta P2 dentro del ciclo CNT-02, antes de CNT-02, porque CNT-02 reutiliza estas reglas.

## Contrato (H01–H10)

| Id | Regla |
|---|---|
| H01 | Al crear el borrador, `moneda = canonical_currency(oferta.moneda)`. Ningún contrato nuevo se escribe en VED (`NEW_GOVERNMENT_VED_WRITES=0`). El monto no cambia. Si un borrador antiguo guarda `VED`, la columna no se reescribe (la guarda PG la protege), pero toda comparación y toda salida usan el código canónico. |
| H02 | La fotografía de la formalización guarda `moneda` (canónica) y `moneda_oferta` (el código tal como lo declaró la oferta). La ficha expone `moneda_oferta`, tomada de la fila de monto de la oferta (`amount_id`). |
| H03 | La comprobación «el monto de la oferta cambió» compara monedas canónicas. Una oferta en VED frente a un contrato en VES no es un cambio. |
| H04 | Las CDP se comparan por moneda canónica, tanto en la validación como en la lista de elegibles. Las asignaciones nuevas guardan la moneda canónica. |
| H05 | Límite del firmante (FIRMAR × CONTRATACIONES) con `service_tasas.verificar_limite`, evaluado a la fecha de formalización (`hoy_de_negocio()`):<br>• misma moneda canónica: comparación directa, sin consultar tasas;<br>• moneda distinta: tasa BCV APROBADA aplicable, en VES, con Decimal exacto;<br>• sin tasa: 422 `GOV_OFFICIAL_RATE_REQUIRED`, con `moneda_operacion`, `moneda_limite`, `fecha` y `monedas_sin_tasa`;<br>• exceso: 409 `GOV_CONTRACT_SIGNER_AMOUNT_EXCEEDED`, con la conversión en `details`.<br>Desaparece `GOV_CONTRACT_SIGNER_CURRENCY_MISMATCH`. La lista de firmantes muestra el estado `SIN_TASA` («Sin tasa oficial aprobada») con su mensaje. |
| H06 | La fotografía guarda `firmante.conversion`: monedas, fecha y, por cada tasa, id, moneda, valor, versión, fecha efectiva, fuente y referencia; además `total_ves`, `limite_ves` y el resultado. Es `null` si no hubo conversión. No se recalcula: la ficha formalizada la lee de la fotografía. |
| H07 | Saldo libre de una CDP para el contrato C, del expediente E:<br>`cdp.monto − Σ reclamos formalizados de otros contratos (asignaciones CNT-01 y asignaciones CNT-02) − Σ compromisos VIGENTES imputados a la CDP cuyo expediente es distinto de E o nulo`.<br>Un compromiso del mismo expediente E es compatible con la cobertura y no se descuenta (no hay doble descuento). Un compromiso sin expediente no demuestra que pertenezca a E y sí se descuenta. |
| H08 | Se mantiene `Σ reclamos formalizados sobre la CDP ≤ cdp.monto`. `cdp.monto` no cambia. |
| H09 | Al formalizar, si los compromisos VIGENTES del expediente E (suma de sus líneas, en moneda canónica) superan el monto del contrato, se responde 409 `GOV_CONTRACT_COMMITMENT_EXCEEDS_AMOUNT`. Si hay compromisos de E en otra moneda canónica, se responde 409 `GOV_CONTRACT_COMMITMENT_NOT_COMPARABLE`, porque no se convierten importes presupuestarios. El borrador lo anuncia en `pendientes`. BUD-08 no se modifica. |
| H10 | BUD-08 no exige contrato (`BUD08_REQUIRES_CONTRACT=0`) y no cambia: ni su servicio ni sus reglas. |

## Constitution Gate

```text
BLOCKER=0 CRITICAL=0 CONTRADICTIONS=0 OWNER_CONFLICT=0 MATERIAL_OQ=0 UNKNOWN=0
OBS_CNT01_BUD08_01=CLOSED  OBS_CNT01_TRE09_01=CLOSED
AUTOMATIC_CURRENCY_CONVERSION=0 (solo límites de autoridad, con TRE-09)  SECOND_FX_ENGINE=0
CONSTITUTION_GATE=PASS
```

## Observaciones

- **OBS-CNT01D-01 (no bloquea).** BUD-08 puede emitir un compromiso del expediente E por encima del monto de un contrato ya formalizado, porque H10 deja BUD-08 intacto. La guarda H09 y la de reducción de CNT-02 impiden *agravar* desde contratos, pero no desde BUD-08. Si se quiere la guarda en BUD-08, es un delta de BUD-08 y decide la dueña.
- **OBS-CNT01D-02 (no bloquea).** Para una CDP sin expediente, un compromiso sin expediente y la asignación de otro contrato pueden ser la misma cuantía. El descuento es conservador por mandato del encargo (§6): puede haber doble descuento, pero nunca sobrefinanciación.

## Tareas

Las tareas H forman parte de la llamada T002 de CNT-02: ver `specs/gov-cnt-02-adendas-variaciones/tasks.md`. La evidencia está en `specs/gov-cnt-02-adendas-variaciones/evidence/`.
