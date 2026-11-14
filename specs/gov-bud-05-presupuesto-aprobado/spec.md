# Spec · BUD-05 Presupuesto aprobado: estimación de ingresos, créditos presupuestarios y cuadre (P0)

## Requisito literal y alcance

```text
BUD05_REQUIREMENT_EXACT_TEXT (matriz canónica, proceso BUD-05 «Formulación: anteproyecto, proyecto y presupuesto aprobado con su acto»)=
  GOV-BUD-006 «Formular recursos/ingresos y egresos/gastos con escenarios, supuestos, techos y justificacion.» (N03,N04,N07,N08; P0)
  GOV-BUD-007 «Mantener anteproyecto, proyecto y presupuesto aprobado como versiones distintas e inmutables una vez aprobadas.» (N03,N04,N24; P0)
  GOV-BUD-008 «Soportar ordenanza/ley de presupuesto y su acto de aprobacion como documento fuente del ejercicio.» (N24,N07,N08,N37; P0)
D_GOV_02 (CLOSED, A/1/1/1)= V1_SCOPE=APPROVED_BUDGET_AND_EXECUTION; FULL_FORMULATION_V1=0.
  Con A, BUD-05 = «aprobado con su acto» (GOV-BUD-008 y la parte de aprobado de 007). GOV-BUD-006 (escenarios, supuestos,
  techos), anteproyecto y proyecto como flujo y presupuesto participativo: LATER_PHASE (no se construyen).
GOV_BUD_004_EXACT_EFFECT= «impedir creditos huerfanos cuando la norma local exija categoria programatica»: LOPPM 239 la exige;
  todo crédito referencia por FK una categoría imputable del mismo ejercicio. BUD-03 dejó este contrato para BUD-05.
GOV_BUD_005_EXACT_EFFECT= las restricciones de uso de BUD-04 se hacen cumplir en backend al registrar créditos.
LEGAL_RULES_USED (LOPPM N24, clase A, en custodia)=
  229 ordenanza anual de ingresos y gastos · 238 ingresos por ramos y estimación · 239 gastos por categorías programáticas y
  partidas · 240 gastos ≤ ingresos, admite hasta la mitad de las existencias del Tesoro no comprometidas · 242 los créditos
  son el límite máximo para gastar · 246 sin afectación de ingresos salvo por ley.
OWNER_DECISIONS (2026-11-14)=
  OD-BUD05-01=A aprobado completo: estimación de ingresos por partida RECURSO + créditos categoría × partida EGRESO × fuente,
    transcritos de la ordenanza; aprobar y reconducir exigen el cuadre LOPPM 240.
  OD-BUD05-02=declarada con soporte: existencias del Tesoro no comprometidas, monto opcional con certificación DOC-08; el cuadre
    suma como máximo la mitad.
```

## Frontera

- GOV-BUD-008 ya lo cubre BUD-01: aprobar exige la ordenanza (referencia, fecha y documento DOC-08) y guarda el fundamento inmutable. BUD-05 añade el **contenido** del aprobado: ingresos, créditos, existencias y cuadre, que entran en la fotografía y la huella.
- GOV-BUD-007: el aprobado ya es inmutable tras fijar (BUD-01). Las versiones anteproyecto y proyecto son LATER_PHASE (D-GOV-02 A).
- **No se construye:** disponibilidad, reserva, precompromiso, compromiso, causado, pagado, ledger, modificaciones (traspasos, créditos adicionales, rectificaciones, insubsistencias), escenarios, techos ni reportes.

## Requisitos

| Id | Requisito |
|---|---|
| B05-01 | **Estimación de ingresos** del ejercicio: partida RECURSO hoja del clasificador del ejercicio y monto. Una por partida |
| B05-02 | **Crédito presupuestario**: categoría programática hoja del ejercicio × partida EGRESO hoja del clasificador del ejercicio × fuente del ejercicio, con monto. Identidad única (ejercicio, categoría, partida, fuente). La unidad ejecutora se deriva del vínculo de BUD-03 y no se duplica |
| B05-03 | **Restricciones de la fuente (BUD-04)**: si la fuente tiene restricciones con partidas, la partida del crédito debe estar en la unión de esas listas, o descender de una de ellas. Si no, 422 `GOV_BUDGET_CREDIT_SOURCE_RESTRICTED`. Una restricción nueva, o la retirada de una, que deje créditos existentes fuera de lo permitido da 409 `GOV_BUDGET_FUNDING_RESTRICTION_CONFLICT` |
| B05-04 | **Dinero**: Decimal y NUMERIC(18,2), mayor que 0, hasta 2 decimales. Se rechaza el exceso; nunca se redondea. Moneda = moneda funcional del ejercicio (sin multimoneda) |
| B05-05 | **Existencias del Tesoro no comprometidas** (opcional, una por ejercicio): monto, fecha de corte y documento DOC-08 de certificación |
| B05-06 | **Cuadre LOPPM 240**: Σcréditos ≤ Σingresos + ½·existencias, con aritmética exacta (2·Σcréditos ≤ 2·Σingresos + existencias). Se valida al aprobar y al reconducir; si falla, 422 `GOV_BUDGET_UNBALANCED` con los totales. La vista muestra el cuadre en todo momento |
| B05-07 | **Imputabilidad al fijar**: un crédito o ingreso cuya categoría o partida dejó de ser hoja impide aprobar o reconducir (422 `GOV_BUDGET_NOT_IMPUTABLE`, con la lista) |
| B05-08 | **Integridad referencial de dominio**: no se elimina una categoría, partida o fuente usada por créditos o ingresos (409 `..._IN_USE`) |
| B05-09 | **Congelado y fotografía**: solo en BORRADOR (409 `GOV_BUDGET_YEAR_FROZEN` y trigger en la base). La fotografía del fundamento incluye ingresos, créditos, existencias y totales |
| B05-10 | **Historia** (8 tipos), **auditoría CTL-02** (8 eventos), If-Match con la versión del ejercicio, bloqueo de fila, aislamiento 404, 403 sin capacidad. Se reutiliza `gobierno_presupuesto` view/manage |
| B05-11 | **Pantalla** en el detalle del ejercicio: secciones «Presupuesto de ingresos», «Créditos presupuestarios», «Existencias del Tesoro» y «Cuadre (LOPPM art. 240)», con selectores humanos (código · nombre). El selector de partidas filtra por las restricciones de la fuente, pero el backend decide |

## Criterios de aceptación

- **AC-01** Ingreso 301 por 1.000.000,00. Duplicado → 422. Partida EGRESO o no hoja → 422. Monto 0, negativo o con 3 decimales → 422 (`VALIDATION_ERROR` del esquema; el servicio repite la regla).
- **AC-02** Crédito categoría 01.02 × partida 401.01 × fuente F01 por 600.000,00. Duplicado → 409. Categoría no hoja → 422. Partida RECURSO → 422. Categoría, partida o fuente de otro ejercicio → 422; de otro ente → 404 del ejercicio.
- **AC-03** F01 restringida a 401: crédito con 402.01 → 422 `GOV_BUDGET_CREDIT_SOURCE_RESTRICTED`; con 401.01 → 201. Restringir F01 a 403 con un crédito existente en 401.01 → 409.
- **AC-04** Créditos de 1.200.000,00 contra ingresos de 1.000.000,00: aprobar → 422 `GOV_BUDGET_UNBALANCED`. Con existencias de 400.000,00, la holgura es 200.000,00 y aprobar → 200.
- **AC-05** Tras aprobar, toda mutación de ingresos, créditos o existencias → 409 y el trigger rechaza en la base. La fotografía contiene la clave `presupuesto_aprobado` con `ingresos`, `creditos`, `existencias_tesoro` y `totales`.
- **AC-06** Eliminar una fuente, partida o categoría usada → 409.
- **AC-07** Historia y auditoría en cada acción. Otro ente → 404. Sin capacidad → 403. If-Match obsoleto → 409. Doble alta concurrente → una gana.
- **AC-08** E2E por el menú, con recarga, a 1280, 390 y 320 px, sin violaciones Axe serias.

## Compuertas

- **REPORTING_REQUIRED_BY_BUD05=0:** GOV-BUD-006/007/008 no piden reporte; los reportes presupuestarios son REP-01 y BUD-13. **REPORTING=NOT_APPLICABLE.**
- **DOCUMENTS:** sí (certificación de las existencias del Tesoro y, vía BUD-01, la ordenanza).
