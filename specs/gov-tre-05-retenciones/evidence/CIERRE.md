# TRE-05 · Cierre (2026-11-20)

- **Entrada:** `9f2c3dd` (ORG-07), con la cabeza en `0128_gov_tre04_pago`.
- **Salida:** cabeza `0129_gov_tre05_retencion`, única, sobre `0128_gov_tre04_pago`.
- **Paralelo (P2):** P2 publicó CTL-02 «autoridad canónica de procesos» (`b61fd44`, `24b6437`, `b726c1d`), sin migración.
  - Se integró con una fusión ordinaria (`9f1cdb8`), sin conflictos.
  - La guarda `test_ctl02_p05` exigía un proceso para los 15 eventos `GOV_WITHHOLDING_*`: se registró `TRE-05 · Retenciones` en `procesos.py` (llamada 45).
- **DeepSeek:** 47 llamadas, 0,293779 USD. La dueña amplió el tope 20 → 32 → 40 → 43 → 45 → 47. Detalle en `ATTEMPT_LOG.md`.
- **Pausas:** el ciclo se pausó con WIP local una vez y por traslado tres veces. Al retomar se siguió `PAUSA.md`.

## Qué se entregó

- **Menú:** Gobierno · Tesorería › **Retenciones** y **Políticas de retención**. En el detalle de cada pago (TRE-04), la sección **«Retenciones»**.
- **Pantallas:**
  - **políticas:** lista, catálogo del ente (conceptos y condiciones), numeración de comprobantes y ficha versionada con editor de reglas. Se activan, se cierran y admiten nueva versión;
  - **sección del pago:** resumen bruto / retenido / neto, cálculo, ajuste, aprobación, descarte, anulación y comprobantes con PDF;
  - **página Retenciones:** pestañas Liquidaciones (filtros y CSV) y Comprobantes (anulación con sustituto).
- **API:** 24 rutas nuevas bajo `/gobierno/tesoreria/retenciones`. OpenAPI frente a `origin/develop`: 0 retiradas. Solo cambian los 4 esquemas SoD y las 2 operaciones SoD que los usan, por el proceso `TRE-05`.
- **Migración:** `0129_gov_tre05_retencion`, con 8 tablas:
  - configuración, catálogo, políticas, reglas, liquidaciones, líneas, comprobantes e historia;
  - guardas PG: política no BORRADOR inmutable, líneas y comprobantes protegidos e historia append-only;
  - CHECK `tipo_regla <> 'LEGAL_MANDATORY' OR estado_verificacion = 'VERIFIED'`.
- **Permisos:** `gobierno_retenciones`. `view`, `manage` y `calculate` son STANDARD; `policy`, `approve` y `cancel` son SENSITIVE (MFA).
- **Motor puro** (`motor_retenciones.calcular`):
  - aplicabilidad: concepto elegido, tipo de persona, condiciones exigidas y exclusiones;
  - base: monto bruto o porcentaje del bruto;
  - alícuota;
  - umbral por monto o por múltiplo de una tasa oficial TRE-09 aprobada, congelada en el cálculo;
  - sustraendo, tope y redondeo configurable (HALF_UP, HALF_EVEN o DOWN);
  - el total nunca supera el bruto.
- **Proyección única:** `proyeccion_retenciones.montos_de_pago` da bruto / retenido / neto y si es definitivo. El detalle del pago la expone en `retenciones`.
- **Liquidación:**
  - estados CALCULADA → APROBADA → APLICADA, más ANULADA;
  - **maker-checker** por identidad (`usuarios_equivalentes`): quien calculó o ajustó no aprueba;
  - **autoridad del checker:** el cargo con la competencia que fija la política, en vigor (ORG-03/04/06), y `evaluar_antes_de_actuar("TRE05_APROBAR")` de CTL-01.
- **Integración TRE-04:**
  - `registrar_pago` exige una liquidación APROBADA si existe (409 `GOV_WITHHOLDING_PENDING_APPROVAL`). Al registrar, la pasa a APLICADA y emite los comprobantes;
  - rechazar o anular el pago anula la liquidación;
  - con liquidación, el pago no se edita ni se descarta.
- **Comprobantes:** número según el patrón del ente, instantánea inmutable con huella SHA-256 y PDF generado bajo demanda desde la instantánea. La anulación admite un sustituto con datos corregidos.
- **Auditoría (CTL-02):** 15 eventos `GOV_WITHHOLDING_*` con claves de detalle estrictas y proceso `TRE-05` en la autoridad canónica de procesos.
- **Normativa:** sin regla `LEGAL_MANDATORY`. Ver `N38_VALIDATION.md`:
  - N37 Gaceta 512 custodiada, sin regla de retención del pagador;
  - N38 sin copia custodiada.

```ini
N37_PUBLIC_PAYER_MANDATORY_WITHHOLDING=NOT_VERIFIED
N38_CUSTODIED_SOURCE=ABSENT
LEGAL_MANDATORY_WITHHOLDING_RULES=0
HARDCODED_WITHHOLDING_RATES=0
TENANT_CONFIGURED_RULES_WITH_PROVENANCE=YES
```

## Evidencia (árbol final)

| Puerta | Resultado |
|---|---|
| Pruebas TRE-05 (PG) | 31/31 (`test_gov_tre05_retencion.py` 01–13, `_b.py` 16–30 + 29b, `_c.py` 14–15) |
| Integración con P2 (CTL-02 procesos + CTL-04, PG) | 40/40 |
| Mutaciones M1–M10, una por criterio de cierre | 10/10 muertas: aplicabilidad, base, alícuota, umbral, exclusiones, varias retenciones, bruto/neto, versión congelada, comprobante y maker-checker |
| Vitest completo (Node 22) | 2567/2567 (234 ficheros) |
| tsc / eslint / build | 0 / 0 / OK |
| ruff | OK |
| E2E `gobierno-retenciones` + regresión `gobierno-pagos` (`r20261120t205853…`) | 13/13, limpieza LIMPIA |
| Detalle de los 6 casos de TRE-05 | principal por la interfaz con maker y checker en sesiones distintas, y Axe a 1280/390/320 en 4 pantallas; varias reglas; umbral; exclusión; versión congelada; comprobante (409 pendiente, PDF y anulación con sustituto) |
| Humo UAT (`r20261120t210601…`) | 1/1, con «Retenciones» y «Políticas de retención» |
| Migración | Una cabeza (`0129`). Sube, baja a `0128` y vuelve a subir en una base PG propia (`kmig0129`, ya borrada) |
| OpenAPI frente a origin | 24 rutas nuevas, 0 retiradas, 0 cambios inesperados |
| Auditoría de hardcode | PASS: 0 alícuotas, 0 umbrales, 0 conceptos y 0 reglas legales en el código. `LEGAL_MANDATORY` aparece solo como guarda de rechazo. La migración solo siembra permisos |
| Fixtures del frontend | Regenerados con `qa/fixtures_de_frontend.py` |
| PG completa | Ver la sección «PG completa» |

## PG completa

- **PG completa** (`qa/suite_tiempos.py --motor postgres --con-analizador`, `r20261120t210802…`): 5837 pasan, 17 fallan, 18 omitidas y 78 errores, en 8648,7 s; reloj NORMAL.
  - **5 de línea base**, los mismos de TRE-04: `test_imb_07_pip_check_limpio`, `test_el_orm_y_la_base_no_difieren_en_nada` (6 columnas `import_*.created_by`), `test_guard_d01_ningun_datetime_desnudo` (`abierta_en` de PROC-07) y las 2 de `test_spec019_receipt.py`.
  - **95 atribuibles a TRE-05, corregidos (llamada 47):**
    - `server_default=text("now()")` en `calculado_en` y `emitido_en` emite `DEFAULT now()`, que SQLite no acepta. Rompía toda prueba que crea el esquema en SQLite: backup, migraciones offline, scope scan, volumen de instalación, flujos y seguridad;
    - la fijación `test_cr01` no listaba el proceso SoD TRE-05.
  - **Tras el arreglo** se repitieron en PG los 15 ficheros que fallaban: 165 pasan y 5 fallan (los 5 de línea base). n10 y guard_d01 no citan nada de TRE-05.
- **SQLite completa** (`r20261120t233903…`), tras el arreglo: 3382 pasan, 3 fallan y 2565 omitidas.
  - `imb_07` y `guard_d01` son de línea base.
  - `test_spec015_open_supply.py::test_api_fijar_destino` falla igual en `origin/develop` (`git archive`, 1 fallo de 9 en los dos árboles): BASELINE_FAILURE.
- **`FINAL_FULL_PG_NEW_FAILURES=0` · `FINAL_FULL_SQLITE_NEW_FAILURES=0`.**

## Defectos de producto que la auditoría y la E2E destaparon y que se corrigieron

1. **Listas de la página Retenciones** (PFIX-7): se leía `{items, total}` y el backend devuelve arrays. En la app real las tablas quedaban vacías, y el mock de Vitest lo ocultaba (verde falso).
2. **Cálculo** (PFIX-7): el formulario filtraba y enviaba **ids** de concepto y condición donde el backend espera **códigos**. No mostraba conceptos y el POST habría fallado.
3. **Listado de liquidaciones** (PFIX-8, hallado por la E2E): la página leía `beneficiario.nombre` y `comprobantes.length` sobre el resumen, que trae `beneficiario_nombre` y un conteo. TypeError al pintar la primera fila.
4. **Accesibilidad** (A11Y-1, hallado por Axe): el select de materia de la competencia del aprobador no tenía nombre accesible.
5. **Integración P2** (INT-P2): faltaba el proceso TRE-05 en la autoridad canónica de procesos.
6. **Guarda QC-02** (QC02): 8 llamadas de consulta con el prefijo `${API_RETENCIONES}`, que la guarda no resuelve. Pasan a rutas literales.

7. **SQLite** (SQLITE-1, hallado por la PG completa): `server_default=text("now()")` rompía la creación del esquema en SQLite. Pasa a `func.now()`, como en la migración.

## Deudas y observaciones

- **OBS-TRE05-DOC-01:** `GovernmentWithholdingReceipt.document_id` existe pero no se usa. El PDF se genera bajo demanda desde la instantánea, con huella verificada.
- **OBS-TRE05-AUDIT-01:** `GOV_WITHHOLDING_SETTINGS_UPDATED` usa `entity_id = company_id`. El patrón TRE-04 podría preferir el id de la fila.
- **OBS-TRE05-E2E-01:** dos defectos menores aceptados en `gobierno-retenciones.spec.ts`:
  - un `as never` redundante sobre un string real;
  - `pago.version + n` pasado a `registrarApi`, que relee la versión. Sin efecto.
- **N38-CUSTODY:** antes del freeze hay que custodiar la normativa tributaria N38 con hash para poder declarar reglas `LEGAL_MANDATORY`. Hasta entonces, todo es configuración del ente con procedencia.
- **OBS-TRE04-ARNES-01** (heredada): el título del humo sigue diciendo «catorce pantallas».

## DAG

- **`DIRECTLY_UNLOCKED`:** ninguno. En la reauditoría de bloqueados y no iniciados, ningún proceso lista TRE-05 como dependencia interna.
  - CNT-06 separa explícitamente las retenciones tributarias hacia TRE-05, pero no depende de él.
  - ACC-06 aplica las reglas N38 en TRE-05 sin depender de él.
- **`TRANSITIVELY_UNLOCKED`:** ninguno.

## Métricas

- `OWNER_UAT_READY`: 47 → **48** de 122 (39,34 %).
- Puertas de la matriz: 485 → **496** de 1268.
- `OWNER_ACCEPTED=NO`: solo lo concede la dueña.
