# Plan · GOV-TRE-05 · Retenciones y comprobantes

| Campo | Valor |
|---|---|
| Base | `9f2c3dd` (= `origin/develop`), cabeza `0128_gov_tre04_pago` |
| Migración | `0129_gov_tre05_retencion`, down `0128_gov_tre04_pago` |
| Módulo | `app/modules/government` (FastAPI, SQLAlchemy, PostgreSQL); frontend `src/modules/gobierno/tesoreria/retenciones/` |
| DeepSeek | `deepseek-v4-pro`, tope duro 20 (1 reservada para integrar P2); 2 reintentos por subproblema |
| No se reutiliza | `fiscal.WithholdingRule` (privado, IVA/ISLR cerrado, sin versión ni congelado; otro contrato, Spec 007) |
| Se reutiliza | pago TRE-04, `tasa_aplicable`/`instantanea_tasa` (TRE-09), `_autoridad_valida` + `exigir_autoridad_funcional` (ORG-03/04/07), `mfa_policy`, CTL-01, documentos y PDF con reportlab (patrón CTL-09), numeración por patrón (patrón TRE-04) |

## 0. Clasificación de reglas

| Regla | Clase |
|---|---|
| Decimal exacto, bruto = total + neto, total ≤ bruto, maker ≠ checker, aislamiento, inmutabilidad tras aprobar/aplicar | PLATFORM_INVARIANT |
| Alícuotas, bases, umbrales, sustraendos, topes, exclusiones, condiciones, conceptos | INSTITUTIONAL_POLICY del ente (N37/N38 clase C; `estado_verificacion=PENDING_PIN`) |
| Patrón y serie del comprobante, redondeo por política | OPERATIONAL_CONFIGURATION |
| Cualquier regla `LEGAL_MANDATORY` | rechazada (`GOV_WITHHOLDING_LEGAL_SOURCE_UNVERIFIED`) mientras no haya fuente N38 verificada (`estado_verificacion=VERIFIED`, sin vía en este ciclo) |

## 1. Modelo (migración 0129)

Constantes nuevas en `models.py`:

- `TIPOS_CATALOGO_RETENCION = ("CONCEPTO", "CONDICION")`
- `CLASES_CONCEPTO_RETENCION = ("TRIBUTARIA", "CONTRACTUAL", "OTRA")`
- `ESTADOS_CATALOGO_RETENCION = ("ACTIVO", "INACTIVO")`
- `ESTADOS_POLITICA_RETENCION = ("BORRADOR", "VIGENTE", "CERRADA")`
- `VERIFICACION_REGLA_RETENCION = ("PENDING_PIN", "VERIFIED")`
- `MODOS_REDONDEO_RETENCION = ("HALF_UP", "HALF_EVEN", "DOWN")`
- `BASES_RETENCION = ("MONTO_BRUTO", "PORCENTAJE_DEL_BRUTO")`
- `UMBRALES_RETENCION = ("NINGUNO", "MONTO", "MULTIPLO_TASA")`
- `TIPOS_PERSONA_RETENCION = ("NATURAL", "JURIDICA")`
- `ESTADOS_LIQUIDACION_RETENCION = ("CALCULADA", "APROBADA", "APLICADA", "ANULADA")`
- `MOTIVOS_NO_APLICA_RETENCION = ("CONCEPTO_NO_SELECCIONADO", "TIPO_PERSONA", "CONDICION_FALTANTE", "EXCLUSION", "UMBRAL", "SIN_MONTO")`
- `ESTADOS_COMPROBANTE_RETENCION = ("EMITIDO", "ANULADO")`
- `RECURSOS_HISTORIA_RETENCION = ("POLITICA", "LIQUIDACION", "COMPROBANTE")`

Tablas (todas `Scope.COMPANY`, `company_id` FK `companies.id`):

1. `gov_withholding_settings`: `patron String(60)` por defecto `{ANIO}-{NUMERO:6}` (variables `{ANIO}`, `{NUMERO:n}`, `{SERIE}`); único por empresa; VersionMixin.
2. `gov_withholding_catalog`: `tipo`, `codigo String(20)`, `nombre String(120)`, `descripcion Text?`, `clase String(12)?` (obligatoria si y solo si `tipo=CONCEPTO`), `serie_comprobante String(10)?` (solo CONCEPTO), `estado` ACTIVO/INACTIVO; único `(company_id, tipo, codigo)`; VersionMixin.
3. `gov_withholding_policies`: `codigo String(20)`, `numero_version`, `version_anterior_id`, `nombre String(200)`, `descripcion Text?`, `moneda` (MONEDAS_LIMITE), `tipo_regla` (TIPOS_REGLA_ORDEN_PAGO), `estado_verificacion` (por defecto PENDING_PIN), `fuente_descripcion String(500)?`, `fuente_referencia String(200)?`, `fuente_documento_id FK documents?`, `act_id FK gov_acts?`, `aprobador_competencia_accion` y `aprobador_competencia_materia` (obligatorias; ACCIONES/MATERIAS_COMPETENCIA), `permite_ajuste Boolean false`, `redondeo_decimales Integer 2` (0–4), `redondeo_modo` HALF_UP, `vigente_desde`, `vigente_hasta?`, `fundamento String(2000)?`, `estado`, `activada_por/en`, `cerrada_por/en`, `motivo_cierre`; único `(company_id, codigo, numero_version)`; CHECK: fuera de BORRADOR exige `fundamento` y `fuente_descripcion`; `tipo_regla <> 'LEGAL_MANDATORY' OR estado_verificacion = 'VERIFIED'`; vigencia; VersionMixin.
4. `gov_withholding_policy_rules`: `policy_id`, `orden`, `concept_id FK gov_withholding_catalog`, `base_tipo`, `base_porcentaje Numeric(9,4)?` (si y solo si PORCENTAJE_DEL_BRUTO; 0 < p ≤ 100), `tasa Numeric(9,4)` (0 < t ≤ 100), `umbral_tipo`, `umbral_monto Numeric(18,2)?` (si y solo si MONTO; ≥ 0), `umbral_multiplo Numeric(18,4)?` y `umbral_moneda_tasa String(3)?` (si y solo si MULTIPLO_TASA; > 0; MONEDAS_TASA), `sustraendo Numeric(18,2)?` (≥ 0), `tope Numeric(18,2)?` (> 0), `condiciones_exigidas JSON` (lista de códigos), `exclusiones JSON` (lista), `tipos_persona JSON?` (null = cualquiera), `exige_comprobante Boolean`; únicos `(policy_id, orden)` y `(policy_id, concept_id)`.
5. `gov_withholding_settlements` (liquidación): `payment_id FK gov_payments`, `policy_id`, `policy_numero_version`, `policy_snapshot JSON`, `estado`, `fecha_referencia Date` (= `fecha_pago` del pago), `moneda`, `bruto`, `total_retenido`, `neto` (Numeric(18,2)), `conceptos JSON`, `beneficiario JSON` (`nombre`, `identificacion_fiscal`, `tipo_persona`, `condiciones`), `calculado_por/en`, `aprobado_por/en`, `aprobador_cargo_id/codigo/nombre`, `aprobador_unidad`, `aprobador_funcionario_id/nombre`, `aplicado_en`, `anulado_por/en`, `motivo_anulacion`, `huella String(64)?`; índice único parcial `(company_id, payment_id) WHERE estado <> 'ANULADA'`; CHECK `bruto = total_retenido + neto`, `total_retenido >= 0`, `neto >= 0`, `bruto > 0`; coherencia de aprobación, aplicación y anulación; VersionMixin.
6. `gov_withholding_settlement_lines`: `settlement_id`, `orden`, `rule_snapshot JSON`, `concept_id`, `concepto_codigo`, `concepto_nombre`, `clase`, `base`, `tasa`, `umbral Numeric(18,2)?`, `tasa_referencia JSON?` (instantánea TRE-09), `aplica Boolean`, `motivo_no_aplica?`, `monto_calculado`, `monto_aprobado`, `motivo_ajuste String(500)?`, `ajustado_por/en`, `exige_comprobante`; CHECK `aplica OR (monto_calculado = 0 AND monto_aprobado = 0 AND motivo_no_aplica IS NOT NULL)`, `monto_aprobado >= 0`, `monto_aprobado = monto_calculado OR motivo_ajuste IS NOT NULL`.
7. `gov_withholding_receipts`: `settlement_id`, `payment_id`, `concept_id`, `numero`, `serie String(10)?`, `codigo String(60)`, `estado`, `sustituye_a_id FK self?`, `snapshot JSON`, `huella String(64)`, `document_id FK documents?`, `emitido_por/en`, `anulado_por/en`, `motivo_anulacion`; único `(company_id, codigo)`.
8. `gov_withholding_history`: `recurso`, `recurso_id`, `evento String(40)`, `actor_id`, `instantanea JSON`.

Guardas PG (mismo patrón que `GOV_PAYMENTS_GUARD_PG`): historia sin UPDATE ni DELETE; comprobantes sin DELETE, y su UPDATE solo EMITIDO → ANULADO; liquidaciones sin DELETE, montos inmutables fuera de CALCULADA; líneas inmutables si la liquidación no está CALCULADA; políticas VIGENTE/CERRADA solo cambian los campos de cierre; reglas inmutables si la política no está en BORRADOR.

## 2. Autoridades únicas

- `proyeccion_retenciones.py`: `montos_de_pago(db, ctx, pago) -> {bruto, total_retenido, neto, liquidacion_id, estado_liquidacion}`. Toma la liquidación activa (no ANULADA). Sin liquidación: total 0 y neto = bruto. Solo lo APLICADO es definitivo (`definitivo=True`). Es la única fuente para el detalle del pago, la UI, el CSV y el comprobante.
- `motor_retenciones.py` (puro, sin sesión): `calcular(politica_snapshot, conceptos, beneficiario, bruto, tasas: dict[moneda, instantanea]) -> lineas, total`. Hace el redondeo con `Decimal.quantize`, con los decimales y el modo de la política.

Algoritmo por regla, en orden:

1. Si el concepto no está seleccionado → CONCEPTO_NO_SELECCIONADO.
2. Si hay `tipos_persona` y el declarado no está → TIPO_PERSONA.
3. Si falta alguna condición exigida → CONDICION_FALTANTE.
4. Si el declarado tiene alguna condición excluida → EXCLUSION.
5. Base: el bruto, o `round(bruto × p / 100)`.
6. Umbral: MONTO → `umbral_monto`; MULTIPLO_TASA → `round(multiplo × valor_tasa)` en VES, solo si la política es VES (si no, 422 `GOV_WITHHOLDING_THRESHOLD_CURRENCY`). Sin tasa aprobada a la fecha → 422 `GOV_WITHHOLDING_RATE_MISSING`. Si `base < umbral` → UMBRAL.
7. Monto: `round(base × tasa / 100) − sustraendo`, limitado por el tope. Si el resultado es ≤ 0 → SIN_MONTO.

`total = Σ monto_aprobado`; si `total > bruto` → 422 `GOV_WITHHOLDING_EXCEEDS_GROSS`. Un concepto elegido sin regla en la política → 422 `GOV_WITHHOLDING_CONCEPT_NOT_IN_POLICY`.

## 3. Servicios

- `service_tesoreria_retencion_politicas.py`: configuración, catálogo, políticas (crear y actualizar con reglas, activar con MFA, fundamento y fuente, cerrar con motivo y MFA, nueva versión, historia, `politica_vigente_en(codigo, fecha)`) y validación de reglas.
- `service_tesoreria_retencion.py`: `opciones(payment_id)`, `calcular`, `ajustar_linea`, `aprobar`, `anular`, listar, CSV, detalle, `al_registrar_pago`, `al_cancelar_pago`, `exigir_sin_liquidacion`.
- `service_tesoreria_retencion_comprobantes.py`: `emitir_comprobantes(liquidacion)`, PDF desde la instantánea guardado en documentos, listar, detalle, `anular_comprobante(sustituir, beneficiario_corregido)`.

Calcular:

- El pago debe estar en BORRADOR, PENDIENTE_AUTORIZACION o AUTORIZADO, sin otra liquidación activa (409 `GOV_WITHHOLDING_SETTLEMENT_EXISTS`).
- La política debe ser VIGENTE a `pago.fecha_pago` y de la misma moneda (422 `GOV_WITHHOLDING_POLICY_NOT_APPLICABLE` o `GOV_WITHHOLDING_CURRENCY_MISMATCH`).
- Los conceptos deben estar ACTIVOS en el catálogo, y las condiciones también.
- El beneficiario declarado necesita `nombre`, `tipo_persona` ∈ TIPOS_PERSONA, `identificacion_fiscal` opcional (≤ 30) y `condiciones` ⊆ el catálogo.
- Resultado: liquidación CALCULADA, historia, auditoría.

Ajustar:

- Solo con `permite_ajuste`, en CALCULADA, con motivo ≥ 10 y sobre una línea que aplica.
- `0 ≤ aprobado ≤ base`.
- Recalcula totales. Si no se permite → 422 `GOV_WITHHOLDING_ADJUSTMENT_FORBIDDEN`.

Aprobar:

- La liquidación debe estar en CALCULADA y el pago no REGISTRADO.
- Maker ≠ checker: 409 `GOV_WITHHOLDING_MAKER_CHECKER`, comparando con `usuarios_equivalentes`, igual que TRE-04.
- El cargo debe tener la competencia de la política vigente hoy (`_autoridad_valida`), más `exigir_autoridad_funcional` y la evaluación CTL-01 del proceso TRE-05.
- Fija la huella SHA-256 de la instantánea y pasa a APROBADA.

Anular:

- Requiere motivo ≥ 10. Posible en CALCULADA o APROBADA, nunca en APLICADA (409 `GOV_WITHHOLDING_APPLIED_IMMUTABLE`).
- En APROBADA pide MFA (`cancel`).

Integración TRE-04 (único punto de contacto; TRE-05 no crea un pago paralelo):

- `registrar_pago` llama a `al_registrar_pago`:
  - una liquidación CALCULADA → 409 `GOV_WITHHOLDING_PENDING_APPROVAL`;
  - una APROBADA → pasa a APLICADA, con `aplicado_en`, y se emiten los comprobantes en la misma transacción.
- `rechazar_pago` y `anular_pago` llaman a `al_cancelar_pago`, que anula la liquidación activa no aplicada con el motivo del pago.
- `actualizar_pago` (BORRADOR) llama a `exigir_sin_liquidacion`: 409 `GOV_WITHHOLDING_SETTLEMENT_EXISTS`.
- `_pago_a_dict` añade `retenciones = montos_de_pago(...)`.

Comprobante:

- Se emite uno por concepto con alguna línea que aplica y `exige_comprobante`.
- `numero` es el siguiente por año, con `FOR UPDATE` sobre la configuración; `codigo` sale del patrón (`{SERIE}` = la serie del concepto o vacía).
- La instantánea lleva tipo (clase y concepto), número, serie, beneficiario declarado, pago (código, fecha, cuenta, moneda, bruto), líneas (base, alícuota, monto), total del comprobante, fecha, emisor (empresa), fuente y versión de la política.
- El PDF se genera solo desde la instantánea. Anular pide motivo y MFA. `sustituir=true` crea otro EMITIDO con número nuevo, los mismos montos y el beneficiario corregido (`sustituye_a_id`).

## 4. Permisos, MFA, auditoría y CTL-01

- `gobierno_retenciones`: `view`, `manage` (catálogo, configuración y borradores de política), `calculate` (calcular, ajustar, anular CALCULADA), `policy` (activar, cerrar, nueva versión), `approve`, `cancel` (anular APROBADA y comprobantes).
- SENSITIVE: `policy`, `approve`, `cancel`. STANDARD: `view`, `manage`, `calculate`.
- Auditoría (15): `GOV_WITHHOLDING_SETTINGS_UPDATED`, `GOV_WITHHOLDING_CATALOG_CREATED`, `GOV_WITHHOLDING_CATALOG_UPDATED`, `GOV_WITHHOLDING_POLICY_CREATED`, `GOV_WITHHOLDING_POLICY_UPDATED`, `GOV_WITHHOLDING_POLICY_ACTIVATED`, `GOV_WITHHOLDING_POLICY_CLOSED`, `GOV_WITHHOLDING_POLICY_VERSIONED`, `GOV_WITHHOLDING_CALCULATED`, `GOV_WITHHOLDING_ADJUSTED`, `GOV_WITHHOLDING_APPROVED`, `GOV_WITHHOLDING_APPLIED`, `GOV_WITHHOLDING_CANCELLED`, `GOV_WITHHOLDING_RECEIPT_ISSUED`, `GOV_WITHHOLDING_RECEIPT_CANCELLED`.
- CTL-01, proceso `TRE-05`: `TRE05_CALCULAR` («Calcular la liquidación de retenciones», `GOV_WITHHOLDING_CALCULATED`) frente a `TRE05_APROBAR` («Aprobar la liquidación de retenciones», `GOV_WITHHOLDING_APPROVED`).

## 5. API (`/api/v1/gobierno/tesoreria/retenciones`)

- `GET/PUT /configuracion`.
- `GET/POST /catalogo`, `PUT /catalogo/{id}`.
- Políticas: `GET/POST /politicas`, `GET/PUT /politicas/{id}`, `POST /politicas/{id}/activar|cerrar|nueva-version`, `GET /politicas/{id}/historia`.
- `GET /opciones?payment_id=`.
- Por pago: `GET /pagos/{payment_id}/liquidacion`, `POST /pagos/{payment_id}/liquidacion`.
- Liquidaciones: `GET /liquidaciones`, `GET /liquidaciones.csv`, `GET /liquidaciones/{id}`, `GET /liquidaciones/{id}/historia`, `PUT /liquidaciones/{id}/lineas/{linea_id}`, `POST /liquidaciones/{id}/aprobar|anular`.
- Comprobantes: `GET /comprobantes`, `GET /comprobantes/{id}`, `GET /comprobantes/{id}/pdf`, `POST /comprobantes/{id}/anular`.

`If-Match` en toda escritura sobre un recurso con versión. MFA por `mfa_policy`.

## 6. UI

- Menú Gobierno · Tesorería: «Retenciones» (`/gobierno/tesoreria/retenciones`) y «Políticas de retención» (`/gobierno/tesoreria/politicas-retencion`).
- `PoliticasRetencionPage`: lista de políticas, catálogo (conceptos y condiciones) y numeración.
- `PoliticaRetencionPage`: nueva, detalle y edición con un editor de reglas cuyos campos dependen de base y umbral, más activar, cerrar, nueva versión e historia. La fuente y la verificación pendiente se muestran siempre.
- `RetencionesPage`: pestañas Liquidaciones y Comprobantes, con filtros, CSV, PDF y anular/sustituir.
- `RetencionesPago` (sección del detalle del pago):
  - formulario de cálculo con política, conceptos y beneficiario declarado;
  - tabla con regla, base, alícuota, calculado, aprobado y fundamento o motivo de no aplicación;
  - ajuste;
  - aprobar con cargo y MFA;
  - anular;
  - resumen bruto / retenciones / neto;
  - comprobantes.
- Accesibilidad: Axe sin violaciones a 1280, 390 y 320. Rótulos, `aria-label` en tablas y regiones desplazables.

## 7. Pruebas

- Backend: los 30 casos del §46 del encargo en `tests/test_gov_tre05_retencion.py`, sobre PG y SQLite.
- Mutaciones M1–M10 del §47.
- Vitest del §48.
- E2E del §49–§55 en `e2e/gobierno-retenciones.spec.ts`, más el humo.
- PG dirigida del §57 y PG completa del §58.

## 8. Fronteras

- **TRE04_BOUNDARY:** TRE-05 lee el pago y solo se engancha en registrar, rechazar, anular y editar; no cambia monto, pagado ni pendiente.
- **TRE07_BOUNDARY:** nada revierte un pago registrado ni una liquidación aplicada; solo el comprobante se anula y sustituye con los mismos montos.
- **CNT06_BOUNDARY:** penalidades, anticipos y amortizaciones no se calculan aquí. Un concepto CONTRACTUAL es una retención que el ente configura con fuente (contrato o acto), sin leer cláusulas.

## 9. CONSTITUTION GATE

BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0; MATERIAL OQ = 0 (OD-TRE05-01..04 cerradas por la dueña); UNKNOWN = 0. MATERIAL_NORMATIVE_UNKNOWN = YES para toda alícuota, y queda como configuración del ente. MATERIAL_DATA_GAP = YES para el beneficiario, cubierto por la declaración. **PASS.**
