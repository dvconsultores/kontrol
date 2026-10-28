# SPEC 001 · Delta — SHARED-CORE-P0-HARDENING-03 · AMERICA/CARACAS BUSINESS CIVIL DATE + TEMPORAL SEMANTICS HARDENING

| Campo | Valor |
|---|---|
| Spec dueña | **001 — Fundación**. Es la dueña del núcleo temporal compartido: `app/shared/clock.py` y `src/lib/fecha-de-negocio.ts`, que creó POLICY-CLOCK-LOCAL en `0c47f61` (2026-09-17), y de `ADR-D0-001` |
| Specs afectadas | **009** (período de reportes, FR-009-015) · **046** (vencimiento documental) · **037/004** (estado de cuenta) · **038/048** (tasas) · **045** (delegaciones) · **012/054** (QA, clasificador de suites) · las pantallas con instantes de 002, 005, 008, 010, 019, 027–036 y 044 (solo presentación) |
| Delta anterior que se endurece | `spec001-business-timezone-delta.md` (POLICY-CLOCK-LOCAL, CLOSED). Este delta no lo reabre: cubre lo que aquel no midió |
| HEAD de entrada | `4c94906` (develop = origin/develop) |
| Evidencia | `evidence/business-civil-date/` |
| Decisiones de la dueña | OD-TIME-01..10 (encargo 03, ratificadas). **PDD-TIME-11** no es una decisión de la dueña: es una decisión de diseño del proyecto que implementa FR-009-015 con el bloqueo legal de los libros (reclasificada el 2026-10-28 por el encargo 04, §6, porque el repositorio no contiene ratificación explícita). Fija que el período se aplica al reporte gerencial y que los libros fiscales quedan bloqueados por norma |
| GOVERNMENT_IMPLEMENTATION_AUTHORIZED | 0 |
| NORMATIVE_RESEARCH | REQUIRED · COMPLETE (§4) |
| Estado | **IMPLEMENTED — VERIFIED — CONVERGED** (autorizado por el encargo «SHARED-CORE-P0-HARDENING-03»; §13–§18) |

## 1. OBS-TIME-01 (lectura del anfitrión, sin cambiar nada)

| Medida | Valor |
|---|---|
| Zona del anfitrión | `Europe/Amsterdam` (CET, UTC+1; CEST desde el 25-10-2026 ya no rige) · `TZ` sin definir · NTP sincronizado |
| `date` / `date -u` | 2026-10-28 00:55:39 CET / 2026-10-27 23:55:39 |
| Python | `datetime.now(UTC)` correcto; `ZoneInfo("America/Caracas")` → −04:00; tzdata del sistema 2026e; sin paquete `tzdata` |
| Generador de run_id (`qa/e2e_nombres.nuevo_run_id`) | **UTC** por diseño |
| PostgreSQL de QA | `-c timezone=UTC` en el arranque; `SHOW TimeZone` = UTC |
| Motor de la aplicación (`app/core/database.py`) | **no fija la zona de sesión**: hereda la del servidor |

### 1.1 Clasificación de las observaciones

| Observación | Causa medida | Clase |
|---|---|---|
| 02E: run_id «≈22:00» frente a `date` «22:52» | El run_id está en UTC y `date`/vitest, en CET: 1 h exacta. Por ejemplo, la corrida SQLite `r20261027t214607` arrancó a las 21:46 UTC = 22:46 CET | **EXPLAINED** |
| 02B: desvío de 1359,9 s con anomalía «NORMAL» (`r20261027t003429…`) | Pared 3431 s y monotónico 2071 s. El muestreador, que mide cada 30 s, tomó **70** muestras: ≈ 2100 s monotónicos. El proceso no corrió durante 1360 s, así que fue una **suspensión** del equipo: CLOCK_MONOTONIC no cuenta el tiempo suspendido. Histórico: 25 917 s, 9399 s, 3415 s, 2572 s y 1551 s, todos con `salto=true` | **HOST_ONLY** |
| La línea de resumen de `qa/suite_tiempos.py` imprime «desvío … · anomalía: NORMAL» **sin decir que hubo salto**, aunque `salto=true` consta en el manifiesto. Quien la lee entiende que todo fue normal | El indicador de anomalía mide la duración, no el reloj, y el resumen no muestra el salto | **QA_CLASSIFIER_DEFECT** → T07 |

**OBS_TIME_01_STATUS = QA_CLASSIFIER_DEFECT (corregido en T07) · causas: EXPLAINED + HOST_ONLY.** Ninguna tiene impacto de producto. Prohibido y no hecho: sudo, cambiar el reloj o la zona del sistema, tocar NTP.

## 2. tzdata (§85)

| Entorno | `America/Caracas` | Versión | Evidencia |
|---|---|---|---|
| Estación / QA | sí (sistema) | 2026e | `ZoneInfo` |
| **V6R** (`python:3.13.16-slim-trixie`, configuración `sha256:ce3ff952…`, digest verificado) | **sí**, en la capa 0 (`debian.sh trixie`), paquete dpkg `tzdata` | 2026c | Capa descargada del registro con token anónimo y verificada por SHA-256 |

Las transiciones (1900–2040) del fichero de V6R y del de la estación son **idénticas**:
- 1912-02-12T04:30Z → −04:30;
- 1965-01-01T04:30Z → −04:00;
- **2007-12-09T07:00Z → −04:30**;
- **2016-05-01T07:00Z → −04:00**.

Resultado: **TZDATA_AVAILABLE_TEST = 1 · TZDATA_AVAILABLE_V6R = 1 · LOCK_CHANGED = 0.** No hace falta el paquete `tzdata`.

## 3. Inventario temporal

### 3.1 Backend, medido en `4c94906`

| Fuente | Nº | Clase |
|---|---:|---|
| Columnas ORM `DateTime(timezone=True)` | 123 (+2 del mixin) | INSTANT |
| Columnas ORM `DateTime` sin zona | **0** | — |
| Columnas ORM `Date` | 50 | BUSINESS_DATE. Algunas se llaman `*_at` (`CashSession.opened_at`, `IgftEvent.evaluated_at`…): es un olor de nombre, sin cambio (OD-TIME-09) |
| `datetime.now(UTC)` | 154 | INSTANT / TECHNICAL_STAMP |
| `date.today()`, `datetime.now()` sin zona, `datetime.utcnow()` en lógica | 0 (guarda de POLICY-CLOCK-LOCAL) | — |
| `CURRENT_DATE`, `::date`, `date_trunc`, `AT TIME ZONE` en lógica | 0 (solo el literal `'infinity'::date` de `commercial/models.py:183`) | — |
| `.date()` sobre un instante | **2 defectuosos** (§3.3, B1) y `clock.py` | — |
| `strftime` | 2: el sello del nombre de exportación (02E) y la clave diaria de idempotencia de licencias (`licensing/service.py:760`) | TECHNICAL_STAMP (OD-TIME-06) |

El inventario completo de campos (FIELD_ID, módulo, tabla.columna, tipos, clase, decisión) está en `evidence/business-civil-date/inventario-temporal.md`.

### 3.2 Frontend, medido en `4c94906`

`evidence/business-civil-date/inventario-frontend.md`:
- 61 apariciones en producción;
- 14 inputs de fecha o período;
- los helpers de E2E.

### 3.3 Hallazgos

| ID | Dónde | Defecto medido | Clase | Riesgo en la ventana 20:00–23:59 de Caracas | Decisión |
|---|---|---|---|---|---|
| **B1** | `treasury/rates.py:412` y `:612` | `rate_date=momento.date()` y `active_policy(…, momento.date())`. Sin fecha, o con un instante en Z, `momento` es UTC | UTC_DATE_USED_AS_BUSINESS_DATE | Elige la política y la `rate_date` del día siguiente | **FIX** (T02) |
| **B2** | `treasury/rates.py:_fecha` (importación CSV) | «AAAA-MM-DD» → `datetime` sin zona, que `_momento` lee como UTC: rige desde las 20:00 del día anterior en Caracas. Una hora sin zona también se lee como UTC | Interpretación implícita | La tasa del día D rige desde D−1 20:00 | **FIX** (T02). Fecha → 00:00 de Caracas, igual que `_momento(date)`; hora sin zona → hora de Caracas (contrato documentado); con desfase → tal cual |
| **B3** | `documents/service.py:440` `is_expired` | `datetime.now(UTC).date()` | UTC_DATE_USED_AS_BUSINESS_DATE | Un documento que vence hoy sale vencido desde las 20:00 | **FIX** (T03) |
| **B4** | `core/config.py` `business_timezone` | Configurable por `KONTROL_BUSINESS_TIMEZONE`, contra OD-TIME-01; `license_timezone` es una constante muerta | Contradice OD-TIME-01 | Una instalación podía cambiar el calendario en silencio | **FIX** (T01): cualquier valor distinto de `America/Caracas` impide arrancar. `license_timezone` queda registrada como deuda (Spec 004) |
| **B5** | `sales/service.py:2894` y `:2907` (estado de cuenta) | `date` mezcla `Date` (aplicaciones) e instantes ISO (`created_at`, `issued_at`); la UI corta `slice(0,10)` y muestra el día UTC | Contrato ambiguo | Día UTC | **FIX** (T04): `date` es siempre la fecha de negocio |
| **B6** | `core/database.py` | Sin zona de sesión: con un servidor en `Asia/Tokyo`, los instantes llegan con `+09:00` y los `slice(0,10)` de la UI dan el día de Tokio | DB_SESSION_TZ_DEPENDENCE | Día de otra zona | **FIX** (T05): sesión fijada en UTC solo para PostgreSQL, más una prueba de invariancia con la sesión en otras zonas |
| **B7** | `reporting/service.py` y `fiscal/service.py:books` | **`period` se recibe y se ignora**: todo reporte devuelve todas las filas. Contradice FR-009-015 (P0) | Requisito incumplido | — | **FIX parcial** (T06, PDD-TIME-11): contrato PERIOD; `executive_ventas` filtra; libros fiscales `period_applied=false` |
| B8 | Entradas `datetime` sin zona en la API (`_momento`, `uom`, `approvals`, `identity`) | Un `datetime` sin zona se lee como UTC | Contrato implícito | Solo si un cliente envía hora local sin zona; el frontend siempre envía Z | **DOCUMENTADO** en ADR-020; el 422 se difiere al ciclo UNDECLARED QUERY PARAMETERS → 422 (deuda API-NAIVE-DATETIME-INPUT) |
| **F1** | Unas 20 pantallas: `toLocaleString`, `toLocaleDateString("es-VE")` e `i18n.formatearFecha` sin `timeZone` | Instantes en la zona del navegador | BROWSER_TZ_DEPENDENCE | Hora y día del navegador | **FIX** (T08–T12) |
| **F2** | 10 `slice(0,10)` sobre instantes | Día UTC (o de la sesión de la base) | UTC_DATE_USED_AS_BUSINESS_DATE | Muestra mañana | **FIX** (T09–T12) |
| **F3** | Unos 10 `slice(0,16\|19).replace("T"," ")` y 3 ISO crudos | La hora tal como llega (UTC) presentada como local | DISPLAY implícito | Hora UTC | **FIX** (T09–T12) |
| **F4** | `DelegacionesPage:64` | `new Date("AAAA-MM-DD").toISOString()` = 00:00 UTC = 20:00 de Caracas del día anterior | Fecha civil convertida con `Date` | La delegación vence ≈ 28 h antes de lo elegido | **FIX** (T13): vigente hasta el final del día D en Caracas |
| **F5** | `TasasPage:62-64/152`, `RecepcionesPage:142` (`datetime-local`) | La hora tecleada se lee en la zona del navegador y el valor por defecto es «ahora» del navegador | BROWSER_TZ_DEPENDENCE | Instante desplazado | **FIX** (T13): hora de Caracas, convertida con la base de zonas (sin −04:00 fijo) |
| **F6** | `MiLicenciaPage:88-96` | Límites de licencia (definidos en Caracas) en el día del navegador | BROWSER_TZ_DEPENDENCE | Fuera de Caracas, 31-mar → 1-abr | **FIX** (T10) |
| F7 | `format.ts::formatDate` y `DateInput.tsx` | Sin usos; `formatDate("AAAA-MM-DD")` desplazaría el día | Código latente | — | `formatDate` delega en el módulo central (T08); `DateInput` no se toca |
| F8 | Período como texto libre (Centro, Libros, Lotes) | Sin validar; vacío → «0» | Contrato sin formato | — | **FIX** en Centro (T14); Libros con aviso de bloqueo normativo (T14); Lotes de declaración sin cambios (fiscal, D0-07) |
| **Q1** | E2E | Ningún proyecto fija `timezoneId`; `auditoria-fecha.spec` consagra la zona del navegador como esperada | Prueba dependiente del anfitrión | — | **FIX** (T16): E2E nueva bajo UTC, `Asia/Tokyo` y `America/Caracas`; la expectativa de `auditoria-fecha` pasa a Caracas (T16) |

**Ya correcto y probado (POLICY-CLOCK-LOCAL), sin cambio:**
- los 26 «hoy» de negocio;
- la ventana de consulta de tasas por fecha;
- la antigüedad de saldos (`hoy_de_negocio` sobre `due_date`);
- las columnas `Date` de caja, IGTF y conciliación;
- las fronteras de licencia (instantes con desfase de Caracas);
- seguridad (sesiones, MFA y reset son INSTANT/DURATION);
- los inputs `type="date"` que se envían tal cual (9).

## 4. Investigación normativa (fuentes primarias)

Registro completo en `evidence/business-civil-date/normativa.md`.

| SOURCE_ID | Fuente | Regla extraída | Verificada | Efecto |
|---|---|---|---|---|
| HL-1 | Decreto N.º 2.301, G.O. 6.224 Ext. (18-04-2016), arts. 1–3 | Hora legal UTC−4; el 01-05-2016 a las 02:30 se pasa a las 03:00 | **sí** (TSJ) | Coincide con IANA (2016-05-01T07:00Z). Se usa `ZoneInfo`, no un −04:00 fijo (OD-TIME-07). No hay horario de verano |
| HL-2 | Reforma de la Ley de Metrología 2007 (UTC−4:30 desde 09-12-2007) | — | **no** → NORMATIVE_SOURCE_MISSING | Sin efecto: el producto no reinterpreta datos históricos y `ZoneInfo` modela la transición (HISTORICAL_DATA_IMPACT = NONE_MEASURED) |
| FA-1 | SNAT/2011/00071, G.O. 39.795, art. 13.6 | Factura de formato libre: fecha de emisión de 8 dígitos | parcial | La fecha de emisión es fecha civil legal (Caracas) |
| FA-2 | SNAT/2024/000102, G.O. 43.032 (19-12-2024), arts. 7.6, 8 y 10.2 | Digital: fecha y hora de emisión | sí | INSTANT, mostrado en hora legal (Caracas) |
| IVA-1 | Ley del IVA, G.O. 6.507 Ext. (29-01-2020), arts. 13, 32 y 56 | Período = mes calendario del **perfeccionamiento del hecho imponible** | sí | **No se filtra un libro por fecha de emisión** → PDD-TIME-11 |
| IVA-2 | Reglamento de la Ley del IVA, G.O. 5.363 Ext., arts. 70–78 | — | no → NORMATIVE_SOURCE_MISSING | LEGAL_VALIDATION_REQUIRED para libros |
| RET-1 | SNAT/2025/000054, G.O. 43.171 (16-07-2025), arts. 7, 13, 14, 16, 20 y 21 | La retención se practica al pago o abono; enteramiento quincenal; el comprobante se registra en el período de su emisión o entrega; **deroga la SNAT/2015/0049** | sí | Sin implementar; deuda FISCAL-RETENCION-NORMA-2025 |
| TC-1 | Ley del IVA, art. 25 | Tipo de cambio del día del hecho imponible; en día no hábil financiero, el del día hábil **siguiente** | sí | Sin cambio en 03; contrastar con el «arrastre» de tasas → LEGAL_VALIDATION_REQUIRED (deuda RATE-NON-BUSINESS-DAY-RULE) |
| TC-2 | Convenio Cambiario N.º 1, G.O. 6.405 Ext., arts. 8, 9 y 84 | Tasa de referencia del BCV; «vigente para la fecha de la liquidación» | parcial | Choca con TC-1 → LEGAL_VALIDATION_REQUIRED |
| PL-1 | COT, G.O. 6.507 Ext., art. 10 | Plazos en días hábiles salvo que la ley diga continuos; un vencimiento en día inhábil se prorroga | sí | Sin uso hoy en el producto; anotado |

**NORMATIVE_RESEARCH_COMPLETE = 1 · NORMATIVE_SOURCES = 10 · NORMATIVE_SOURCE_MISSING = 1** (HL-2 e IVA-2). Ninguna regla fiscal nueva se implementa.

## 5. Gobierno (relectura antes del diseño)

Hashes sin cambios en `9a41503`:

| PDF | SHA-256 |
|---|---|
| Ingeniería de requisitos | `8f86615f…` |
| Biblioteca normativa | `4a980bb9…` |

| Requisito | Relación |
|---|---|
| **RNF-GOV-003** (P0) «Fecha civil America/Caracas para negocio; UTC para timestamps técnicos, conservando zona/origen» | **Es exactamente el modelo de este delta** (ADR-020). «Conservando zona» = el instante se guarda con zona y la API lo emite con desfase |
| RNF-GOV-005 (timestamp en cada transacción) | INSTANT sin cambio |
| RNF-GOV-008 (versión normativa con vigencia) | Vigencias = BUSINESS_DATE o INSTANT, según el campo |
| RNF-GOV-009, GOV-CTL-007 (cifras y rendición por período) | El contrato PERIOD (AD-6) es la base; los libros oficiales esperan validación legal |
| GOV-BUD-013 (fecha efectiva), GOV-TRE-005 (fecha valor), GOV-DOC-003 (fecha de eficacia), GOV-BUD-001/017 (ejercicio, cierre) | Se clasificarán como BUSINESS_DATE o PERIOD; sin implementación (Gobierno = 0) |
| GOV-DOC-010, GOV-ACC-011 | Sin efecto temporal propio |

## 6. Requisitos

| ID | Requisito |
|---|---|
| FR-001-246 | Una sola zona de negocio, `America/Caracas`, constante e IANA. La aplicación no arranca si se configura otra (OD-TIME-01/07; sin respaldo silencioso) |
| FR-001-247 | El núcleo temporal da: fecha de negocio de un instante, límites UTC semiabiertos de un día de negocio y de un período «AAAA-MM», y la validación del período |
| FR-001-248 | Ninguna fecha de negocio sale de `.date()` sobre un instante sin pasar por Caracas (B1, B3) |
| FR-001-249 | Importación de tasas: «AAAA-MM-DD» rige desde las 00:00 de Caracas; hora sin zona = hora de Caracas; con desfase, tal cual (B2) |
| FR-001-250 | El estado de cuenta emite `date` como fecha de negocio «AAAA-MM-DD» en todas sus líneas (B5) |
| FR-001-251 | El resultado de negocio no depende de la zona de sesión de PostgreSQL; la sesión de la aplicación es UTC (B6) |
| FR-009-015 (cumplimiento parcial, PDD-TIME-11) | El período «AAAA-MM» se valida (si es inválido, 422 `INVALID_PERIOD`); «»/«0» = sin filtro. `executive_ventas` filtra `issued_at ∈ [inicio, fin)` del mes de Caracas; todo reporte con período devuelve `period_applied` |
| FR-001-252 | Libros fiscales: `period_applied=false` y `period_rule="LEGAL_VALIDATION_REQUIRED"`; la UI lo avisa |
| FR-001-253 | Todo instante se muestra en Caracas, con zona explícita y desde el módulo central; nunca en la zona del navegador ni cortando el ISO |
| FR-001-254 | Una fecha civil elegida en un `type="date"` no pasa por `Date`; una hora elegida en `datetime-local` es hora de Caracas, convertida con la base de zonas |
| FR-001-255 | La delegación elegida «hasta D» rige hasta el final del día D en Caracas |
| FR-001-256 | Una guarda de arquitectura del frontend impide reintroducir formateo implícito de fechas fuera del módulo central |
| FR-012-QA-01 | El resumen de la suite dice explícitamente si hubo salto de reloj |

## 7. Diseño

### AD-1 · Núcleo backend (`app/shared/clock.py`), sin dispersar `ZoneInfo`
- `ZONA_DE_NEGOCIO = ZoneInfo("America/Caracas")`; `zona_de_negocio()` la devuelve.
- Se conservan `ahora_de_negocio(instante=None)` y `hoy_de_negocio(instante=None)`. La inyección del reloj es por parámetro, el patrón existente: un instante fijo da siempre lo mismo.
- Nuevas funciones:
  - `inicio_del_dia_de_negocio(d)`: 00:00 de Caracas del día `d`, con zona;
  - `limites_del_dia_utc(d)` y `limites_del_periodo_utc(periodo)`: `(inicio, fin_exclusivo)` en UTC;
  - `periodo_valido(texto)`: «AAAA-MM» con mes 01–12; en otro caso, `KontrolError` `INVALID_PERIOD` (422).
- `config.py`: un validador de `business_timezone` que exige `America/Caracas`. Con otro valor, error de arranque (sin respaldo silencioso).

### AD-2 · Tasas (B1, B2)
- `rate_date=hoy_de_negocio(momento)`.
- `active_policy(…, hoy_de_negocio(momento))`.
- `_fecha`: si el texto es una fecha, `_momento(date)` (00:00 de Caracas); si es una hora sin zona, `replace(tzinfo=ZONA_DE_NEGOCIO)`; si trae desfase, tal cual.
- El algoritmo de selección no cambia.

### AD-3 · Documentos (B3)
`is_expired`: `today or hoy_de_negocio()`.

### AD-4 · Estado de cuenta (B5)
Las líneas cuya `date` era un instante emiten `hoy_de_negocio(instante).isoformat()`.

### AD-5 · Sesión de PostgreSQL (B6)
`create_engine(..., connect_args={"options": "-c timezone=UTC"})` solo cuando la URL es PostgreSQL. Una prueba solo-PG abre un motor con la sesión en `Asia/Tokyo` y otro en `America/Caracas` y comprueba que la lógica de negocio da el mismo resultado.

### AD-6 · PERIOD y reportes (B7, PDD-TIME-11)
- `report(…, period)`: «» o «0» → sin filtro, `period_applied=false`; si no, `periodo_valido` y luego el filtro.
- `executive_ventas`: `SalesInvoice.issued_at >= inicio AND < fin`, en UTC del mes de Caracas.
- Libros fiscales: no filtran; `period_applied=false` y `period_rule="LEGAL_VALIDATION_REQUIRED"`.
- La exportación hereda el mismo camino. El sello técnico del nombre (02E) no cambia (OD-TIME-06).

### AD-7 · Núcleo frontend (`src/lib/fecha-de-negocio.ts`, el módulo central existente)
- Se conservan `ZONA_DE_NEGOCIO` y `hoyDeNegocio`.
- Nuevas funciones:

| Función | Qué hace |
|---|---|
| `formatearInstante(iso)` | Fecha y hora es-VE con `timeZone` Caracas; nulo o inválido → «—» |
| `formatearFechaDeInstante(iso)` | Solo la fecha de Caracas, DD/MM/AAAA |
| `fechaDeNegocioDeInstante(iso)` | «AAAA-MM-DD» de Caracas |
| `formatearFechaDeNegocio("AAAA-MM-DD")` | DD/MM/AAAA por texto, sin `Date` |
| `instanteDesdeHoraDeCaracas("AAAA-MM-DDTHH:mm")` | ISO UTC; el desfase de Caracas para esa hora se obtiene con `Intl`, sin −04:00 fijo |
| `horaDeCaracasParaInput(instante?)` | «AAAA-MM-DDTHH:mm» de Caracas |
| `finDelDiaDeNegocio("AAAA-MM-DD")` | Instante ISO de las 23:59:59.999 de Caracas |

- `i18n.formatearFecha` delega en `formatearInstante`; `format.ts::formatDate` delega en el módulo central.

### AD-8 · Presentación (F1–F3, F6)
Cada sitio del inventario pasa al módulo central:
- instante con hora → `formatearInstante`;
- instante como día → `formatearFechaDeInstante`;
- BUSINESS_DATE → texto «AAAA-MM-DD» o `formatearFechaDeNegocio`, según la pantalla, sin `Date`.

### AD-9 · Entradas (F4, F5)
| Pantalla | Cambio |
|---|---|
| Delegaciones | `valid_to = finDelDiaDeNegocio(D)` |
| Tasas | Valor por defecto `horaDeCaracasParaInput()`; envío `instanteDesdeHoraDeCaracas(vigencia)` |
| Recepciones | Envío `instanteDesdeHoraDeCaracas` |

### AD-10 · Guarda de arquitectura del frontend (FR-001-256)
Prueba que recorre `src/` (sin tests ni `src/lib/fecha-de-negocio.ts`) y prohíbe:
- `toLocaleDateString(` y `toLocaleTimeString(`;
- `toLocaleString(` aplicado a `new Date(…)`;
- `Intl.DateTimeFormat(` y `new Date(` seguidos de `.toISOString()` sobre un valor de input;
- `.slice(0, 10|16|19)` sobre identificadores temporales (`*_at`, `*date*`, `valid_*`, `expires*`, `getValue()`).

Lista blanca con motivo escrito; por ejemplo, el hash de `PermisosPage`, que es TECHNICAL_STAMP. `toLocaleString` sobre números es legítimo y no se persigue.

### AD-11 · QA (Q1 de OBS-TIME-01)
La línea de resumen de `qa/suite_tiempos.py` añade `salto de reloj: SÍ|NO`. Con salto, añade «(suspensión o ajuste del reloj del anfitrión; la duración monotónica sigue siendo válida)».

### AD-12 · E2E (Q1)
`e2e/business-date.spec.ts` con `test.use({ timezoneId })` en tres bloques: `UTC`, `Asia/Tokyo` y `America/Caracas`. La expectativa de `auditoria-fecha.spec.ts` pasa a ser la hora de Caracas, no la del navegador.

### Contratos que se documentan (no cambian el comportamiento)
- Instantes sin zona en la API = UTC (B8).
- TECHNICAL_STAMP en UTC: run_id, sufijo de exportación y clave diaria de licencias.

**ADR-020** recoge el modelo INSTANT / BUSINESS_DATE / PERIOD / DISPLAY / DURATION / TECHNICAL_STAMP.

## 8. Seguridad

- Sesiones, MFA, reset y tokens siguen siendo INSTANT/DURATION, sin conversión.
- La delegación (F4) **amplía** la vigencia real hasta lo que la persona eligió. Hoy expira antes, que es el defecto. El techo de delegación (02B) no cambia: es backend.
- Ningún cambio de autorización, alcance ni auditoría.

## 9. Gate de la Constitución

| Criterio | Resultado |
|---|---|
| Requisitos completos | PASS |
| Inventario completo | PASS |
| Normativa suficiente para lo que se implementa | PASS: no se implementa regla fiscal nueva |
| OD aplicadas | PASS |
| Modelo coherente | PASS |
| Migración | NOT_APPLICABLE: ningún cambio de tipo; los datos históricos no se reinterpretan (OD-TIME-09) |
| Pantallas | PASS (§11) |
| Plan de pruebas | PASS (§10) |
| MATERIAL_OQ en el alcance | 0: PDD-TIME-11 (decisión de diseño del proyecto; ver §0) |

P1/P2 PASS · P6 PASS · P7 PASS · P10 PASS (rojo primero) · P12: **ADR-020** · P13 PASS · P21 PASS · P27 PASS.

Contadores: BLOCKER, CRITICAL, CONTRADICTIONS, MATERIAL_OQ y UNKNOWN = 0.

## 10. Tareas

Todas: EXECUTOR DEEPSEEK y RETRY_MAX 2. Prueba roja primero: el bloque de prueba se aplica antes que el de producto.

| Tarea | Modelo | Ficheros | Pruebas | DONE_WHEN |
|---|---|---|---|---|
| T01 | pro | `app/shared/clock.py`, `app/core/config.py`, `tests/test_business_civil_date.py` (nuevo) | Vectores 01–05, transición 2016, periodo válido/inválido, límites, validador de zona | Rojo y después verde |
| T02 | pro | `app/modules/treasury/rates.py`, prueba en `tests/test_business_civil_date_rates.py` | `rate_date` y política a las 23:30 de Caracas (en Z); CSV con fecha y hora sin zona | Ídem |
| T03 | flash | `app/modules/documents/service.py`, prueba | `is_expired` en la frontera | Ídem |
| T04 | pro | `app/modules/sales/service.py` (estado de cuenta), prueba | Línea a las 23:30 de Caracas → día de Caracas | Ídem |
| T05 | pro | `app/core/database.py`, `tests/test_business_civil_date_pg.py` | Sesión en Tokyo y en Caracas → mismo resultado (solo PG) | Ídem |
| T06 | pro | `app/modules/reporting/service.py`, `app/modules/fiscal/service.py` (solo `period_applied`), prueba | Borde de mes, 422, libros `period_applied=false` | Ídem |
| T07 | flash | `qa/suite_tiempos.py` + su prueba | Resumen con salto | Ídem |
| T08 | pro | `src/lib/fecha-de-negocio.ts` + prueba, `src/i18n/index.ts`, `src/lib/format.ts` | Vectores en navegador simulado | vitest |
| T09–T12 | flash | Sitios de presentación por grupo (inventario §3.2) | Pruebas de página existentes + una por grupo | vitest, tsc |
| T13 | pro | Delegaciones, Tasas, Recepciones + pruebas | Entradas | vitest |
| T14 | pro | `CentroReportesPage` (período validado), `LibrosPage` (aviso) + pruebas | — | vitest |
| T15 | flash | `src/tests/architecture-temporal.test.ts` | Guarda | vitest |
| T16 | pro | `e2e/business-date.spec.ts`, `e2e/auditoria-fecha.spec.ts` | BUSINESS-DATE-E2E | 3 navegadores |
| T17 | flash | `specs/001-fundacion/adr/ADR-020.md` y los contratos de API afectados | — | Revisado |

## 11. Pantallas afectadas (TEMPORAL_SCREEN_MATRIX)

Ver `evidence/business-civil-date/screen-form-completeness.md`, que se completa al cerrar.

## 12. Inventario de suites obligatorias

| RS | Suite |
|---|---|
| RS-01 | OBS-TIME-01 (§1) |
| RS-02 | Evidencia normativa (§4) |
| RS-03 | Backend dirigidas en PG |
| RS-04 | Backend dirigidas en SQLite |
| RS-05 | vitest dirigidas |
| RS-06 | PG completo con analizador |
| RS-07 | SQLite completo con analizador |
| RS-08 | vitest completo |
| RS-09 | tsc |
| RS-10 | eslint |
| RS-11 | build |
| RS-12 | ruff |
| RS-13 | mypy (≤ 154, MYPY_NEW_ERRORS = 0) |
| RS-14 | Alembic (cabeza 0060, sin migración) |
| RS-15 | OpenAPI |
| RS-16 | BUSINESS-DATE-E2E en 3 navegadores |
| RS-17 | Regresión E2E: READ, alcance, delegación y UI-SCOPE (105), DOWNLOAD (27), auditoria-fecha, licencia-periodo, rates, receivables, billing y treasury |
| RS-18 | E2E canónica (357 + nuevas) |
| RS-19 | Mutaciones |
| RS-20 | Accesibilidad |
| RS-21 | Responsive |
| RS-22 | Puerta de pantallas |
| RS-23 | Base de datos tras la E2E |
| RS-24 | Barrido de secretos |
| RS-25 | Residuos (incluida la restitución de `TZ`) |

## 13. Ejecución (D-T: C03-T01..T17)

Detalle por tarea, rechazos y coste: `evidence/business-civil-date/orchestration.md`.

**Tareas que nacieron durante la implementación:**
- **T06b**: adaptar `test_export_auditada`, que solo pasaba porque el período se ignoraba;
- **T16c**: reclasificación de T16 tras agotar 2 reintentos, con causa raíz medida en la prueba (compuerta de empresa y un inicio de sesión de más).

**Hallazgos de la implementación:**
- **SQLite guardaba en hora de pared de Caracas** las fechas registradas en tasas, que al releerlas se tomaban como UTC. Se corrigió normalizando a UTC al persistir. Rojo: las 2 pruebas sobre `sesion_de_prueba` fallaban en SQLite con el `rates.py` original.
- **El estado de cuenta** necesitaba un orden por fecha de negocio y por instante, sin exponer el instante.
- **DATE-13** (Spec 001, auditoria-fecha) es una decisión ratificada: un instante inválido no se disfraza de «—». El núcleo frontend la conserva (`FECHA_INVALIDA`).

## 14. Resultados

| RS | Suite | Resultado | Evidencia |
|---|---|---|---|
| RS-01 | OBS-TIME-01 | QA_CLASSIFIER_DEFECT, corregido; causas EXPLAINED + HOST_ONLY | `evidence/…/obs-time-01.md` |
| RS-02 | Normativa | 10 fuentes; NORMATIVE_SOURCE_MISSING = 1 (HL-2, IVA-2, Convenio) | `evidence/…/normativa.md` |
| RS-03/04 | Backend dirigidas | PG 179/0 · SQLite 93/0 (86 solo-PG) | `evidence/…/rojo.md` |
| RS-05/08 | vitest | **668/668** (58 ficheros; antes 646/56) | — |
| RS-06 | PostgreSQL completo con analizador | **3593/0** (18 omitidas, igual que la base) · salto de reloj: NO · NORMAL | `qa/backend-runs/r20261028t011722p88188na5e614` |
| RS-07 | SQLite completo con analizador | **2513/0** (1098 omitidas: +16 solo-PG nuevas) · salto de reloj: NO · NORMAL | `qa/backend-runs/r20261028t015319p460317n8c3bc0` |
| RS-09/10/11 | tsc / eslint / build | 0 / 0 / correcto | — |
| RS-12 | ruff | limpio | — |
| RS-13 | mypy | 154 = 154 en HEAD (diff vacío) · MYPY_NEW_ERRORS = 0 | — |
| RS-14 | Alembic | cabeza `0060_spec003_admin_split`; sin migración | — |
| RS-15 | OpenAPI | 420 = 420 rutas; esquemas y operaciones sin cambios | — |
| RS-16 | BUSINESS-DATE-E2E en 3 navegadores × 3 zonas | **39/39** | `qa/e2e-runs/r20261028t015009p443921n0fd8de` |
| RS-17 | Regresión E2E | auditoria-fecha 3/3, rates 39, treasury 48, receivables 27, billing 24, licencia-periodo 12 (total de la corrida 192/192) · seguridad (105) y DOWNLOAD (27): **132/132** (105 + 27) | ídem · `qa/e2e-runs/r20261028t020713p576892n69a75c` |
| RS-18 | E2E canónica con analizador | **370/370** (357 + 13 BUSINESS-DATE-E2E de Chromium) · limpieza LIMPIA | `qa/e2e-runs/r20261028t020939p603303n7e5080` |
| RS-19 | Mutaciones | **35/35** muertas · 0 equivalentes · 0 supervivientes | `evidence/…/mutaciones.md` |
| RS-20/21 | Accesibilidad / responsive | BD-E2E-05: 320 px sin desbordamiento; axe sin críticos ni graves en `main` | — |
| RS-22 | Puerta de pantallas | PASS | `evidence/…/screen-form-completeness.md` |
| RS-23 | Base de datos tras la E2E | PASS: 0 bases de corrida, base efímera ELIMINADA (0 conexiones cortadas), material MFA: 0 | — |
| RS-24/25 | Secretos y residuos | CLEAN (§16) | §16 |

## 15. Gobierno (relectura de cierre)

Hashes sin cambios respecto de 9a41503 (`8f86615f…` y `4a980bb9…`).

- **RNF-GOV-003** queda cubierto por el núcleo compartido, con la regla de ADR-020 y sus pruebas.
- RNF-GOV-005, RNF-GOV-008, RNF-GOV-009, GOV-CTL-007 y los requisitos de fecha efectiva, fecha valor, fecha de eficacia y ejercicio se reconcilian con las clases de ADR-020, sin implementación de Gobierno.
- Ningún requisito temporal aplicable queda sin explicar: **ENGINEERING_REQUIREMENTS_RECONCILED = 1 · APPLICABLE_REQUIREMENTS_COVERAGE = 100 %**.
- GOVERNMENT_IMPLEMENTATION_AUTHORIZED, GOVERNMENT_SPEC_STARTED y GOV0_STARTED siguen en 0.

## 16. Seguridad y residuos

| Control | Resultado |
|---|---|
| JWT, `Bearer <valor>`, rutas personales, `KONTROL_SECRET_KEY` o claves privadas en los ficheros del ciclo | 0 / 0 / 0 |
| Bases efímeras tras las E2E (`qa/e2e-bases.py listar`) | 0 |
| Puertos 8000/5173 | libres |
| `.bak`, `.mutbak`, `.orig`, `.rej` | 0 |
| `TZ` del entorno | sin definir (las pruebas lo cambian y lo restauran en `finally`) |
| Copias normativas | fuera de Git (scratchpad), con SHA-256 en la evidencia |
| `requerimientos/KONTROL_SNAT_2026_00093.docx` | sin tocar, sin seguimiento |
| Sesiones, MFA y reset | INSTANT/DURATION sin conversión; E2E de MFA, reset y delegación verdes en la canónica |
| PRODUCTION_TOUCHED | 0 |

**SECRET_EXPOSURE = 0 · RESIDUE = CLEAN.**

## 17. Deuda (al cerrar)

| ID | Severidad | Estado |
|---|---|---|
| POLICY-CLOCK-LOCAL, endurecido (presentación, entradas, período, motores) | — | **CERRADA** en este delta |
| REPORT-PERIOD-NOT-APPLIED (FR-009-015) | — | **CERRADA en 04** (conciliación del encargo 04, §7): el único reporte no fiscal con período aplicable (`executive_ventas`) filtra; `operational_inventario`, `financial_aging` y `regulatory_evaluaciones` son fotos «a hoy» donde un mes no aplica y lo declaran con `period_applied=false`. Lo único pendiente es fiscal y vive solo en FISCAL-BOOK-PERIOD-RULE; el aviso de UI para esos tres queda como REPORT-PERIOD-INPUT-ON-SNAPSHOT-REPORTS (LOW) |
| FISCAL-BOOK-PERIOD-RULE | HIGH | **Abierta, LEGAL_VALIDATION_REQUIRED** (Ley del IVA, arts. 13 y 56; Reglamento, arts. 70–78 sin fuente primaria) |
| FISCAL-RETENCION-NORMA-2025 | MEDIUM | **Abierta**: la SNAT/2025/000054 deroga la 2015/0049; verificar qué cita el producto (D0-07) |
| RATE-NON-BUSINESS-DAY-RULE | MEDIUM | **Abierta, LEGAL_VALIDATION_REQUIRED**: Ley del IVA, art. 25 (día hábil siguiente) frente al arrastre de tasas y al Convenio Cambiario N.º 1, art. 84 |
| API-NAIVE-DATETIME-INPUT | MEDIUM | **Abierta**: un instante sin zona en la API se lee como UTC (documentado en ADR-020); el 422 va al ciclo UNDECLARED QUERY PARAMETERS → 422 |
| LICENSE-TIMEZONE-DEAD-CONSTANT | LOW | **Abierta** (Spec 004): `license_timezone` no se lee |
| AUDIT-DATE-FILTER-MISSING | LOW | **Abierta** (FUTURE_SPEC): la bitácora no filtra por fecha; cuando exista, `limites_del_dia_utc` |
| STATEMENT-CONTRACT-UNDOCUMENTED | LOW | **Abierta**: el estado de cuenta no tiene contrato escrito; el campo `date` queda documentado aquí (FR-001-250) |
| RECEPCIONES-IMPORT-DUPLICADO | LOW | **Abierta**: dos imports del mismo módulo en `RecepcionesPage.tsx`; eslint no lo marca |
| SQLITE-HISTORIC-WALLTIME-RATES | LOW | **Abierta, NEEDS_DATA_AUDIT** (solo SQLite de desarrollo): las filas de tasas guardadas antes de este ciclo con fecha suelta quedaron en hora de pared de Caracas. PostgreSQL no está afectado. Sin reparación (OD-TIME-09) |
| EXPORT-CREATE-IDEMPOTENCY-CONTRACT-GAP, EXPORT-CSV-EMPTY-WITHOUT-HEADER, REPORT-JOB-RESULT-NOT-DOWNLOADABLE, CROSS-MODULE-SELECTOR-COMPOSITION, TABLE-HEADER-CONTRAST-AA (PARCIAL) y el resto de §90 del encargo | — | Sin cambio, no absorbidas |

## 18. Convergencia (equivalente explícito)

La skill formal resuelve la Spec por la rama (`develop`), no por el delta. Aplico su procedimiento a este delta; la intención es §6 (FR-001-246..256, FR-009-015 parcial, FR-012-QA-01), §7 (AD-1..12) y la Constitución.

| Requisito | Evidencia | Hallazgo |
|---|---|---|
| FR-001-246 | `test_zona_de_negocio_es_constante`, `test_config_business_timezone_puede_ser_solo_caracas`, B01, B03, B14 | — |
| FR-001-247 | VECTOR-01..05, límites de día y de período, 2016, B02, B15 | — |
| FR-001-248 | rates a/b, documents, B06, B07, B11, B13 | — |
| FR-001-249 | rates e/f/g, B09, B10 | — |
| FR-001-250 | statement ×3, B12, B19 | — |
| FR-001-251 | pg ×8, B16 | — |
| FR-009-015 (parcial) | reports ×5, B04, B05, B18, CR-08/09, BD-E2E-04 | Libros: deuda legal registrada (PDD-TIME-11) |
| FR-001-252 | reports, B17, LIB-01/02, CR-10, F08, F09 | — |
| FR-001-253 | fecha-de-negocio.test (4 zonas), AuditoriaPage.fecha, guarda, BD-E2E-01, F01–F06, F10, F11, F14, F15 | — |
| FR-001-254/255 | BD-E2E-02/03, guarda, F12, F13 | — |
| FR-001-256 | `architecture-temporal.test.ts` (0 ofensas), F11–F14 | — |
| FR-012-QA-01 | O12-21/22, Q01 | — |
| Constitución P6/P7/P10/P13/P21/P27 | §9, §14 | — |

**Hallazgos: 0 · missing 0 · partial 0 (lo parcial es la deuda legal declarada) · contradicts 0 · unrequested 0. ✅ Converged.**
