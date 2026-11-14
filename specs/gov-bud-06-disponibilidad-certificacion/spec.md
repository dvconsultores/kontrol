# Spec · BUD-06 Disponibilidad presupuestaria y certificación (P0)

## Requisitos literales (IR v1.0 §7.2)

```text
GOV-BUD-009 «Controlar disponibilidad presupuestaria en tiempo real por partida, fuente, programa/proyecto y unidad ejecutora.» (N03,N04,N20; P0)
GOV-BUD-010 «Emitir certificacion de disponibilidad presupuestaria con identificador, monto, saldo antes/despues, firmante y expediente.» (N03,N04,N11,N20; P0)
D-GOV-02 (CLOSED A/1/1/1): BUD-06 construible tras el aprobado. ARCH §6: disponibilidad calculada al operar, bloqueo por crédito, sin saldo negativo
  silencioso; ARCH §8: quien certifica no compromete (CTL-01). PRECOMMITMENT_DEFAULT_ENABLED=0 (BUD-07 aparte).
LOPPM 242: los créditos son el límite máximo para gastar; ningún gasto sin previsión. LOPPM 234-236: el reconducido rige como presupuesto.
LOPPM 248 y 250: ejercicio del 1-ene al 31-dic; tras el cierre no se compromete ni se causa.
```

## Fórmula (única autoridad de dominio)

```text
DISPONIBLE(crédito) = CREDITO_APROBADO(crédito) − Σ monto de certificaciones VIGENTES del crédito
```

- No hay saldo persistido ni editable.
- Extensión futura en la misma función, sin tocar certificados emitidos: `+ MODIFICACIONES_NETAS (BUD-10) − COMPROMISOS (BUD-08)`.

## Requisitos

| Id | Contrato |
|---|---|
| B06-01 | **Autoridad del crédito.** Solo créditos BUD-05 del mismo ente y ejercicio. BUD-06 no crea ni modifica créditos, ingresos, fuentes, categorías ni existencias |
| B06-02 | **Disponibilidad en tiempo real.** Se calcula en cada consulta y operación con la fórmula de arriba |
| B06-03 | **Proyección por dimensiones.** Por crédito: categoría (programa/proyecto), unidad ejecutora (BUD-03), partida, fuente; filtros por categoría, unidad, partida y fuente; totales del conjunto filtrado (crédito, certificado vigente, disponible) |
| B06-04 | **Efecto.** Una certificación VIGENTE reduce de inmediato la disponibilidad del crédito |
| B06-05 | **Identificador** `CDP-{AAAA}-{NNNN}`: correlativo por ejercicio y ente (UNIQUE(year_id, numero)), asignado bajo bloqueo del ejercicio; patrón «HA-{AAAA}-{NNNN}» de CTL-06 |
| B06-06 | **Saldo antes y después** persistidos como evidencia; CHECK saldo_despues = saldo_antes − monto ≥ 0 |
| B06-07 | **Firmante:** cargo ORG-03 con competencia FIRMAR × PRESUPUESTO en vigor hoy (estructura del año, cargo VIGENTE o INACTIVO con vigencia que cubre la fecha; mismo criterio que DOC-02). Además: guarda ORG-06 `exigir_autoridad_funcional(cargo, "FIRMAR", "PRESUPUESTO")`, capacidad técnica `gobierno_presupuesto:certify` (SENSITIVE, con MFA). Se guarda una instantánea: cargo (código y nombre), unidad del cargo, funcionario vinculado (ORG-06, si lo hay) y usuario emisor |
| B06-08 | **Expediente:** obligatorio. Con `expediente_id` se vincula a un expediente PROC-03 del mismo ente y la referencia es su número. Sin él, `expediente_referencia` textual (3–120 caracteres) |
| B06-09 | **Documento:** PDF ReportLab generado al emitir y guardado en el almacenamiento con sha256 (patrón PROC-08), con descarga verificada. Contenido: identificador, ente, ejercicio, fecha, expediente, concepto, categoría, unidad, partida, fuente, monto, saldo antes y después, firmante y cargo, estado y huella. **No es firma electrónica (DOC-05)** |
| B06-10 | **Inmutable.** Ni edición ni borrado; trigger PG que solo admite la transición VIGENTE → ANULADA con sus campos |
| B06-11 | **Anulación:** motivo (10–500), actor, instante y MFA (`certify`). No borra; libera la disponibilidad. Solo con el ejercicio APROBADO o RECONDUCIDO. **Frontera BUD-08:** cuando exista consumo, no se podrá anular una certificación consumida |
| B06-12 | **Concurrencia:** se bloquean la fila del ejercicio y la del crédito (SELECT … FOR UPDATE) antes de calcular; dos emisiones que excedan juntas: una pasa y otra recibe 422; doble anulación: una 200 y otra 409 |
| B06-13 | **Dinero:** NUMERIC(18,2) y Decimal; monto > 0, como máximo 2 decimales; sin redondeo; moneda = moneda funcional del ejercicio |
| B06-14 | **Aislamiento:** otro ente → 404. Ejercicio en BORRADOR o CERRADO → 409 GOV_BUDGET_YEAR_INVALID_STATE. Fecha de emisión (hoy, Caracas) fuera del año del ejercicio → 422 |
| B06-15 | **Auditoría** CTL-02: GOV_BUDGET_CERTIFICATE_ISSUED y _ANNULLED; historia del ejercicio CERTIFICACION_EMITIDA y CERTIFICACION_ANULADA |
| B06-16 | **BUD-07 aparte:** no es precompromiso ni reserva, y no lee la política de precompromiso |
| B06-17 | **BUD-08 futura:** sin endpoint ni transición; el actor y el cargo quedan registrados para la SoD «quien certifica no compromete» |
| B06-18 | **Pantalla:** sección «Disponibilidad y certificaciones» del detalle del ejercicio aprobado, más E2E 1280/390/320 con Axe y UAT |

## Vectores (fijados antes del primer encargo)

| Vector | Caso | Resultado esperado |
|---|---|---|
| A | crédito 1000.00; se certifican 300.00 | antes 1000.00, después 700.00: PASS |
| B | crédito 1000.00 con 300.00 vigentes; se certifican 700.00 | antes 700.00, después 0.00: PASS |
| C | crédito 1000.00 con 300.00 vigentes; se certifican 700.01 | 422 GOV_BUDGET_INSUFFICIENT_AVAILABILITY; no se crea nada |
| D | dos emisiones concurrentes de 700.00 sobre 1000.00 | una pasa y la otra se bloquea; el saldo final es 300.00 |
| E | crédito 1000.00 con certificado de 300.00 (saldo 700.00); se anula | saldo 1000.00 |
| F | consulta o emisión sobre un crédito de otra empresa | 404 |

## Compuertas

- **REPORTING_REQUIRED_BY_BUD06=0:** la lista es superficie operativa, no REP-01. REPORTING=NOT_APPLICABLE.
- **DOCUMENTS:** sí (PDF de la certificación).
- **No se absorbe:** BUD-07, BUD-08, BUD-10, BUD-11, caja (TRE-02), conversión de moneda ni formulación.
