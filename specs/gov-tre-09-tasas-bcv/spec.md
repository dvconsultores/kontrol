# Spec · TRE-09 · Procedencia de tasas oficiales BCV (GOV-TRE-011) y cierre de OBS-BUD08-VES-VED

**Requisito (literal):** GOV-TRE-011 · «Conservar provenance de tasas BCV cuando una operación autorizada requiera conversión monetaria.» (P1; N39, N03, N06).

**N39 (Biblioteca Normativa, clase A):** «Tasas y referencias oficiales del BCV · fuente oficial BCV vigente por fecha». Controles: guardar tasa, fecha y fuente BCV; no recalcular la historia con una tasa posterior; reglas por fecha, operación y fuente oficial.

**Decisión de la dueña (encargo TRE-09 §3–§8):** OBS_BUD08_VES_VED=CLOSED. El código canónico de Gobierno es VES (ISO 4217, Amendment 170: VED es de uso interno y no sustituye a VES). VED→VES es normalización de código con factor 1, no conversión. No se reescribe la historia. Enterprise no cambia. ORG-03 no admite VED.

## Historia del sponsor

1. Entra a Gobierno → Tesorería → Tasas oficiales.
2. Registra una tasa BCV en borrador: moneda, fecha efectiva (fecha valor BCV), valor «1 moneda = X VES», referencia oficial y fecha de publicación.
3. Adjunta la evidencia BCV (documento con sha256).
4. Otro usuario la aprueba con MFA.
5. Consulta la lista con filtros y la historia de versiones.
6. Corrige una tasa aprobada con una nueva versión y motivo; al aprobarla, la anterior queda SUSTITUIDA.
7. En Presupuesto → Compromisos, con una autoridad cuyo límite está en otra moneda, el sistema usa la tasa aprobada aplicable, muestra su procedencia y deja registrada la comparación.
8. Si falta la tasa o no está aprobada, la operación queda bloqueada.

## Contratos

| ID | Contrato |
|---|---|
| T09-01 | **Autoridad propia de Gobierno:** tabla `gov_official_exchange_rates`. No se lee el maestro privado `treasury.ExchangeRate`. |
| T09-02 | **VES canónico:** `canonical_currency(c)`: VED→VES; cualquier otro código, en mayúsculas sin cambios. Monedas cotizables: USD y EUR (MONEDAS_LIMITE sin VES). VES y VED no se cotizan (422). |
| T09-03 | **VED heredado:** los registros de Gobierno con VED (todos posteriores al 2021-10-01) se comparan como VES con factor 1. Las escrituras nuevas normalizan a VES: el ejercicio que crea BUD-01 desde `functional_currency`, la moneda de las certificaciones de BUD-06 y la de los compromisos de BUD-08. Sin UPDATE masivo. Un límite VED en ORG-03 sigue rechazado por el CHECK y el esquema vigentes. |
| T09-04 | **Procedencia:** fuente = BCV (fija). Fecha efectiva y referencia oficial obligatorias (10–300 caracteres). Fecha de publicación opcional y ≤ fecha efectiva. Se guardan quién captura y quién aprueba, con fecha y hora. |
| T09-05 | **Convención:** 1 MONEDA = valor VES. `rate_to_ves(VES) = 1` y no se guarda una observación VES/VES. |
| T09-06 | **Decimal exacto:** valor Numeric(28,12), mayor que 0, con hasta 12 decimales (el BCV publica 8). Nunca float. |
| T09-07 | **Ciclo de vida:** BORRADOR → APROBADA → SUSTITUIDA. BORRADOR → ANULADA y APROBADA → ANULADA, con motivo. Nada se borra y una APROBADA no se edita. La corrección crea una nueva versión (supersedes_id, version+1, motivo); al aprobarla, la anterior pasa a SUSTITUIDA en la misma transacción. Triggers PG de inmutabilidad y contra DELETE y TRUNCATE. |
| T09-08 | **Maker-checker:** el aprobador no puede ser quien capturó; se compara contra los actores equivalentes, como en CTL-01 (409 GOV_OFFICIAL_RATE_MAKER_CHECKER). La aprobación y la anulación exigen `gobierno_tasas:approve`, SENSITIVE (MFA). |
| T09-09 | **Evidencia:** para aprobar se exige un documento ACTIVO con sha256 vinculado a la tasa (ResourceKind GovernmentOfficialExchangeRate). Al aprobar se guarda una copia con el id y el sha256 (422 GOV_OFFICIAL_RATE_EVIDENCE_REQUIRED). |
| T09-10 | **Selección por fecha:** para una operación de fecha D se usa la tasa APROBADA de la moneda con la mayor fecha efectiva ≤ D: la «vigente por fecha» de N39, que cubre fines de semana y feriados. BORRADOR, ANULADA y SUSTITUIDA nunca se seleccionan. Por (empresa, moneda, fecha) hay como máximo una APROBADA y como máximo un BORRADOR (índices únicos parciales). |
| T09-11 | **Copia inmutable:** la operación guarda id, moneda, fecha efectiva, valor, fuente, referencia, versión y sha256 de la evidencia de cada tasa usada. No se relee el maestro. |
| T09-12 | **Comparación:** con monedas canónicas iguales, `total ≤ límite`. Si difieren, `total × rate_to_ves(op) ≤ límite × rate_to_ves(lím)` con Decimal exacto y sin redondear. El formato solo se aplica en la presentación. |
| T09-13 | **Sin tasa no hay operación:** si falta alguna tasa, 422 GOV_OFFICIAL_RATE_REQUIRED con details {moneda_operacion, moneda_limite, fecha, monedas_sin_tasa}. Sin mutación y sin respaldo. |
| T09-14 | **Consumidor BUD-08:** la verificación del límite usa T09-10..13. La copia va en `snapshot.autoridad.conversion` (huella y PDF). El importe y la moneda del compromiso no cambian. Una vista previa de solo lectura (`GET .../compromisos/verificacion-limite`) muestra lo que el backend usará; el usuario no elige la tasa. Desaparece el código GOV_BUDGET_COMMITMENT_AUTHORITY_CURRENCY_MISMATCH. |
| T09-15 | **Concurrencia:** la aprobación bloquea FOR UPDATE la tasa y la sustituida; el compromiso lee las tasas con FOR SHARE. Dos aprobaciones de la misma clave: una pasa y la otra recibe 409 GOV_OFFICIAL_RATE_CONFLICT (índice único). El compromiso queda ligado a la versión que leyó. |
| T09-16 | **Aislamiento:** con una empresa ajena o inexistente, 404 COMPANY_NOT_FOUND. `require_module` va como último parámetro y la familia de rutas entra en test_iso_barridos. |
| T09-17 | **Auditoría (CTL-02):** GOV_OFFICIAL_RATE_CREATED, _APPROVED, _SUPERSEDED, _ANNULLED, con moneda, fecha, valor, referencia y sha256. Sin secretos. |
| T09-18 | **E2E y UAT:** recorrido del sponsor por el menú a 1280, 390 y 320 px con Axe; humo UAT con la pantalla nueva. |

## Vectores

| ID | Caso | Resultado esperado |
|---|---|---|
| A | Tasa USD 900, operación 450000 VES, límite 500 USD | 450000 ≤ 450000: PASA, con copia |
| B | Igual que A pero con 450000,01 VES | AMOUNT_EXCEEDED |
| C | EUR 1000 y USD 900; operación 90000 USD (81.000.000 VES), límite 81000 EUR (81.000.000 VES) | PASA. Con 90000,01 USD: EXCEDE |
| D | Límite USD sin tasa USD aprobada (solo BORRADOR) | GOV_OFFICIAL_RATE_REQUIRED |
| E | Tasa de fecha D+1 aprobada, operación en D, sin otra tasa ≤ D | GOV_OFFICIAL_RATE_REQUIRED |
| F | Ejercicio heredado VED y límite VES | sin tasa; compara 1:1 |
| G | Ejercicio nuevo con empresa en VED | moneda_funcional = VES |
| H | Límite ORG-03 en VED | 422, rechazado |
| I | Corrección aprobada | la anterior queda SUSTITUIDA; el compromiso previo conserva el valor viejo en su copia; uno nuevo usa el valor nuevo |
| J | Anulación de la única tasa aprobada | el compromiso nuevo da GOV_OFFICIAL_RATE_REQUIRED |

**Fuera de alcance:** integración con PROC-08 y CNT-01 (DEFERRED); scraping del BCV; tasas entre monedas extranjeras; reportes (REPORTING=NOT_APPLICABLE).
