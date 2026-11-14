# Spec · BUD-08 · Compromiso presupuestario (GOV-BUD-012)

**Requisito canónico (literal):** «Registrar compromiso presupuestario solo con autoridad, soporte y disponibilidad suficiente; no permitir
saldo negativo silencioso.» Fuentes N03, N04 y N20.

**Fuentes:**
- IR §7.2 y §8.
- D-GOV-02 = A y `specs/gov-bud-decision-02/ARCHITECTURE_CONSEQUENCES.md`:
  - §3 sin saldos editables;
  - §6 disponibilidad con bloqueo;
  - §7 LOPPM 248: pasado el 31-12 no se compromete;
  - §8 «quien certifica no compromete» (CTL-01).
- LOPPM 242 (no comprometer sin crédito disponible) y 248.
- BUD-05 (créditos) y BUD-06 (certificaciones).
- ORG-03 (competencia `COMPROMETER × PRESUPUESTO` con límite por operación), ORG-04, ORG-06 (guarda de identidad funcional) y ORG-07.
- CTL-01 (equivalencia de actores) y CTL-02 (auditoría).

**Producto:** Gobierno → Presupuesto → Ejercicios → «Ejercicio AAAA» → sección **Compromisos**. El sponsor:
- elige una o varias CDP vigentes y ve, de cada una, lo certificado, lo consumido y el remanente;
- registra un compromiso con 1..N imputaciones;
- ve el total, la autoridad, el soporte y el expediente;
- descarga la constancia PDF;
- anula el compromiso con motivo, y el remanente de la CDP se restituye.

## Fórmula (autoridad única: `disponible_de_credito`)

```text
CONSUMIDO(cdp)   = Σ líneas de compromisos VIGENTES que imputan la CDP
REMANENTE(cdp)   = cdp.monto − CONSUMIDO(cdp)        0 ≤ CONSUMIDO ≤ cdp.monto
DISPONIBLE(cred) = cred.monto − Σ REMANENTE(cdp VIGENTE del crédito) − Σ COMPROMISOS VIGENTES del crédito
```

Convertir una CDP en compromiso no cambia DISPONIBLE: no hay doble descuento. No se guarda ningún saldo; la CDP no se edita.

**Situación derivada de la CDP:**

| Situación | Condición |
|---|---|
| DISPONIBLE | consumido = 0 |
| PARCIALMENTE_CONSUMIDA | 0 < consumido < monto |
| AGOTADA | consumido = monto |

BUD-06 conserva sus estados VIGENTE y ANULADA.

## Contratos

| Id | Contrato |
|---|---|
| B08-01 | Todo compromiso consume CDP de BUD-06 en estado VIGENTE del mismo ejercicio y empresa. No hay ruta directa contra el crédito. |
| B08-02 | El remanente de la CDP es derivado (fórmula arriba). Una imputación por encima del remanente da 422 `GOV_BUDGET_CERTIFICATE_INSUFFICIENT_REMAINING` (details: remanente, solicitado). |
| B08-03 | Sin doble descuento: `disponible_de_credito` aplica la fórmula; el disponible del crédito no cambia al comprometer ni al anular un compromiso. |
| B08-04 | Identidad: compromiso de cabecera (`gov_budget_commitments`) y líneas (`gov_budget_commitment_lines`). |
| B08-05 | Multiimputación de 1 a 20 líneas, con CDP distintas, del mismo ejercicio, empresa y moneda funcional. El crédito de la línea se deriva de la CDP; el cliente no lo elige. |
| B08-06 | El total es Σ de los montos de las líneas, derivado por el backend. El cuerpo no lleva total. |
| B08-07 | Autoridad funcional: cargo ORG-03 con `COMPROMETER × PRESUPUESTO` vigente hoy (`_autoridad_valida`) más la guarda ORG-06 (`exigir_autoridad_funcional`). Si falla, 422 `GOV_BUDGET_COMMITMENT_AUTHORITY_INVALID`. |
| B08-08 | Límite: SIN_LIMITE pasa. Con MONTO, total ≤ límite; si lo excede, 422 `GOV_BUDGET_COMMITMENT_AUTHORITY_AMOUNT_EXCEEDED`. |
| B08-09 | Misma moneda: si la moneda del límite difiere de la del ejercicio, 422 `GOV_BUDGET_COMMITMENT_AUTHORITY_CURRENCY_MISMATCH`, sin conversión ni excepción. |
| B08-10 | Soporte obligatorio: documento ACTIVO vinculado al ejercicio (`_documento_valido`). Se guardan su id y su sha256. Si falla, 422 `GOV_BUDGET_INVALID_DOCUMENT`. |
| B08-11 | Expediente derivado de las CDP: todas deben compartir `procurement_file_id` y `expediente_referencia`. Si no coinciden, 422 `GOV_BUDGET_COMMITMENT_EXPEDIENTE_MISMATCH`. No se crea otro expediente. |
| B08-12 | Inmutabilidad: trigger PG. La cabecera solo admite VIGENTE→ANULADO más los datos de anulación. Las líneas no admiten UPDATE, DELETE ni TRUNCATE. |
| B08-13 | Anulación total (FULL_REVERSAL_ONLY): motivo de 10 a 500 caracteres, actor, fecha y MFA. Una segunda anulación da 409 `GOV_BUDGET_COMMITMENT_NOT_ACTIVE`. Al anular, el remanente vuelve a la CDP. |
| B08-14 | Guarda de la CDP: anular una CDP con consumo > 0 da 409 `GOV_BUDGET_CERTIFICATE_IN_USE`. Si todos sus compromisos se anulan, vuelve a ser anulable. |
| B08-15 | Concurrencia: bloqueo FOR UPDATE del ejercicio (serializa el correlativo, las CDP y la anulación de la CDP), de las CDP en orden de id y de sus créditos. Con dos peticiones de 700 sobre un remanente de 1000: una 201 y una 422. |
| B08-16 | SoD «quien certifica no compromete». Si el actor (o un usuario equivalente por vínculo institucional, `usuarios_equivalentes` de CTL-01) emitió alguna CDP de las líneas, o uno de sus funcionarios (`funcionarios_de_actor`) es el firmante de la CDP: 409 `GOV_SOD_CONFLICT` y un intento auditado `GOV_BUDGET_COMMITMENT_SOD_BLOCKED`. Es una regla vinculante (ARCH §8): no se configura y no se crea un motor paralelo. |
| B08-17 | Exactitud: NUMERIC(18,2) y Decimal; monto > 0, como máximo 2 decimales; sin float ni redondeo. Si no, 422 `VALIDATION_ERROR` o `GOV_BUDGET_INVALID`. |
| B08-18 | Aislamiento: otra empresa recibe 404 en todo. |
| B08-19 | Auditoría (CTL-02): `GOV_BUDGET_COMMITMENT_ISSUED`, `GOV_BUDGET_COMMITMENT_ANNULLED` y `GOV_BUDGET_COMMITMENT_SOD_BLOCKED`. Historia del ejercicio: `COMPROMISO_REGISTRADO` y `COMPROMISO_ANULADO`. |
| B08-20 | Frontera BUD-09: no hay causado. Cuando exista, anular un compromiso causado se bloqueará en `anular`. BUD09_IMPLEMENTED=0. |
| B08-21 | Frontera BUD-11: no hay ledger; los compromisos son registros propios inmutables. SECOND_BUDGET_LEDGER_CREATED=0. |
| B08-22 | E2E y UAT: recorrido completo por el menú a 1280, 390 y 320 px con Axe; pila UAT con humo. |

**Más reglas:**
- El ejercicio debe estar APROBADO o RECONDUCIDO; si no, 409 `GOV_BUDGET_YEAR_INVALID_STATE`.
- La fecha (hoy, en Caracas) debe caer dentro del año del ejercicio (LOPPM 248).
- El concepto tiene de 10 a 500 caracteres.
- El código es `CP-AAAA-NNNN`, único por ejercicio y por empresa, y se genera bajo bloqueo.
- Constancia PDF almacenada con sha256. Contiene:
  - código, ente, ejercicio, fecha, expediente y concepto;
  - por línea: categoría, unidad, partida, fuente, CDP y monto;
  - total, moneda, autoridad, soporte, estado y huella.
  - No es firma DOC-05.
- Capacidad `gobierno_presupuesto:commit`, SENSITIVE (MFA). Sirve para emitir y anular. No vale `manage` ni `certify`.
- La consulta exige `view`.

## Vectores (obligatorios antes de implementar)

| Vector | Entrada | Resultado |
|---|---|---|
| A | crédito 1000, CDP 300, compromiso 300 | disponible 700 → 700; remanente 0 |
| B | crédito 1000, CDP 300, compromiso 200 | disponible 700 → 700; remanente 100 |
| C | remanente 100, compromiso 100.01 | BLOCK (`GOV_BUDGET_CERTIFICATE_INSUFFICIENT_REMAINING`) |
| D | remanente 1000; A = 700 y B = 700 a la vez | una pasa y otra se bloquea |
| E | CDP 300, compromiso 200, remanente 100; se anula el compromiso | remanente 300; disponible 700 |
| F | CDP 300 con compromiso vigente 200; se anula la CDP | BLOCK (`GOV_BUDGET_CERTIFICATE_IN_USE`) |
| G | límite 500 VES, compromiso 400 VES | PASS |
| H | límite 500 VES, compromiso 500.01 VES | BLOCK (`..._AMOUNT_EXCEEDED`) |
| I | límite 500 USD, ejercicio en VES | BLOCK (`..._CURRENCY_MISMATCH`), sin conversión |
| J | multilínea: CDP-A 600 y CDP-B 500; líneas 400 y 300 | total 700; remanentes 200 y 200; disponible sin cambio |

## Fuera de alcance

| Decisión | Valor |
|---|---|
| Maestro de proveedores o beneficiarios | 0 (GOV-BUD-012 no lo exige; CTL-08 y PROC-05 no bloquean) |
| BUD-07 (precompromiso o reserva; bloqueado por N37) | 0 |
| BUD-09 (causado) | 0 |
| BUD-10 (modificaciones) | 0 |
| BUD-11 (ledger) | 0 |
| Caja TRE-02 | no se toca |
| Conversión de moneda | no |
| Reverso parcial | no |
| Reporte dedicado | REPORTING = NOT_APPLICABLE |
