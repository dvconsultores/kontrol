# Spec · GOV-BUD-09 Causado / devengado (GOV-BUD-013)

| Campo | Valor |
|---|---|
| Proceso | BUD-09 (P0), REBASELINE_02_STATUS = BUILDABLE_NOW |
| Entrada | `ffcea9f`, alembic `0122_gov_cnt07_terminacion` |
| Autorización | Encargo «P1 — GOV-BUD-09 · CAUSADO / DEVENGADO» (2026-11-17), que nombra BUD-09 (Constitución P2) |
| Política vinculante | `docs/roadmap/government-product-completeness/GOVERNMENT_PARAMETERIZATION_POLICY.md` |
| Fuentes | N03 (LOAFSP), N06, N35: conocidas. N36 (ONCOP, clase C): pendiente; gobierna solo el asiento contable, que queda fuera de alcance |

## 1. Problema

El presupuesto de Gobierno ya registra aprobado, disponibilidad, certificación y compromiso (BUD-05, 06 y 08), pero no el **causado**: la obligación económicamente exigible contra un compromiso vigente. Sin él no hay orden de pago (TRE-03), pago (TRE-04), ejecución presupuestaria (REP-01) ni cadena E2E-01.

## 2. Alcance

```text
BUDGET_CAUSING=IN_SCOPE          ACCOUNTING_ENTRY=OUT_OF_SCOPE (ACC-02; N36 pendiente)
PAYMENT_ORDER=OUT_OF_SCOPE (TRE-03; solo se define la frontera de consumo)
```

## 3. Decisiones de la dueña (2026-11-17)

| Id | Decisión |
|---|---|
| OD-BUD09-01 | La separación comprometer/causar **reutiliza CTL-01**, en modo solo BLOQUEAR: el ente crea, activa o cierra la regla con vigencia y fundamento. La severidad WARN queda como deuda nombrada **SOD-WARN-MODE-01**, para un delta de CTL-01 |
| OD-BUD09-02 | La política de causado se activa con **fundamento obligatorio + MFA**. El acto administrativo (DOC-02) es **opcional** |

## 4. Historias y criterios de aceptación

**HU-1 · Configurar la política de causado (administración funcional).** La autoridad presupuestaria define, por tipo de gasto, qué hecho habilita causar y qué se exige.
- AC-1.1: una política tiene:
  - `tipo_gasto` (código libre del ente), nombre y disparador;
  - `requiere_recepcion`, `requiere_valuacion` y `requiere_conformidad`;
  - documentos exigidos (tipos documentales del ente, con obligatoriedad y etapa);
  - competencia exigida (acción × materia; por defecto CAUSAR × PRESUPUESTO);
  - vigencia, fundamento normativo y tipo de regla (`INSTITUTIONAL_POLICY` por defecto).
- AC-1.2: estados BORRADOR → VIGENTE → CERRADA. Solo se edita en BORRADOR. Activar exige fundamento y MFA; el acto es opcional.
- AC-1.3: cada cambio deja historia. No pueden coexistir dos políticas VIGENTES del mismo tipo de gasto con vigencias solapadas.
- AC-1.4: el producto no trae ninguna política precargada. Los ejemplos de la interfaz son ayudas, no datos.

**HU-2 · Preparar un causado.** La analista elige un compromiso VIGENTE del ejercicio, ve su saldo por línea, elige la política aplicable, imputa montos por línea, fija la fecha efectiva, vincula evidencias y documentos, y guarda el borrador.
- AC-2.1: no hay causado sin compromiso VIGENTE del mismo ente y ejercicio (**R1**).
- AC-2.2: el monto se imputa a las líneas del compromiso (partidas) y se admiten causados parciales y múltiples. **R2**: por línea, lo causado formalizado no anulado más lo solicitado no supera lo comprometido en la línea.
- AC-2.3: las evidencias son referencias tipadas (`resource_type`, `resource_id`) a recepciones, valuaciones conformadas, entregas conformes o facturas de CNT-03, o a documentos de 046. Se admiten varias por causado; se guarda una instantánea, sin copias mutables.
- AC-2.4: la fuente es tipada (`source_resource_type` / `source_resource_id`, p. ej. CONTRATO). El contrato no es obligatorio para todo causado.
- AC-2.5: el borrador se edita con control optimista (`If-Match`/versión).

**HU-3 · Revisar controles y formalizar.**
- AC-3.1: «Revisar controles» lista lo cumplido y lo que falta, sin formalizar: saldo, evidencia exigida, documentos exigidos, autoridad y segregación.
- AC-3.2: formalizar exige `gobierno_presupuesto:cause` + MFA y un cargo con la competencia de la política vigente en la fecha (**R5**; nunca nombres de cargo). Revalida R1, R2 y la política con el compromiso bloqueado (`FOR UPDATE`).
- AC-3.3: **R3** · si la política exige recepción, valuación o conformidad, debe existir evidencia de ese tipo en estado válido, con fecha ≤ fecha efectiva.
- AC-3.4: **R4** · `fecha_efectiva` ≠ `registrado_en`. La fecha efectiva cae en el año del ejercicio, no es futura y no es anterior a la fecha del compromiso.
- AC-3.5: una regla CTL-01 vigente del proceso BUD-09 («comprometer → causar») bloquea a quien emitió el compromiso. Sin regla vigente no bloquea: la decide el ente.
- AC-3.6: al formalizar se asigna número y código según el patrón configurado por el ente, se congela la instantánea con huella y queda la historia. **R6**: un causado formalizado no se modifica en sitio.

**HU-4 · Anular un causado formalizado.** Con motivo y MFA. El original permanece, la anulación es explícita y el saldo se restablece de forma transaccional. Nunca hay `DELETE`.

**HU-5 · Consultar y exportar.** Listado con filtros (estado, compromiso, fecha efectiva, texto), detalle con evidencias, documentos, líneas, saldo resultante e historia, y CSV.

**HU-6 · Frontera con TRE-03.** Cada causado expone `monto_causado`, `monto_ordenado` (0 hasta TRE-03) y `pendiente_de_ordenar`. El evento de formalización lleva lo necesario para un futuro mapeo contable (ACC-02) sin acoplamiento.

## 5. Integridad con BUD-08

Un compromiso con causados formalizados no anulados **no se puede anular** (409). Sin esto, R2 quedaría sin base.

## 6. Fuera de alcance

- asiento contable y plan de cuentas (ACC-01/02);
- orden de pago y pago (TRE-03/04);
- retenciones (TRE-05);
- WARN en CTL-01 (SOD-WARN-MODE-01);
- motor de procesos genérico (solo compatibilidad declarada).

## 7. Criterio de producto

BACKEND, FRONTEND, MENU, PROCESS, FIELDS, ROLES, DOCUMENTS, REPORTING, AUDIT, E2E y OWNER_UAT_CARD en PASS. Cero hardcode institucional: sin nombres de ente, unidad ni cargo; sin montos, plazos ni series en código.
