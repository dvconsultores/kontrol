# Spec · BUD-03 + BUD-04 Plan operativo, metas y responsables + fuentes de financiamiento (P0)

## Requisitos literales (IR v1.0 §7.2)

```text
BUD03_REQUIREMENT_EXACT_TEXT=
  GOV-BUD-003 «Modelar plan, objetivo, programa, subprograma, proyecto, accion especifica, meta fisica, indicador y responsable.»
    (N30, N31, N04, N07, N08; P0)
  GOV-BUD-004 «Vincular presupuesto a plan operativo y metas fisicas; impedir creditos huerfanos cuando la norma local exija
    categoria programatica.» (N31, N07, N08; P0)
BUD04_REQUIREMENT_EXACT_TEXT=
  GOV-BUD-005 «Registrar fuentes de financiamiento y restricciones de uso con vigencia.» (N03, N04, N07, N08; P0)
APPLICABLE_NORMATIVE_SOURCES=
  LOPPM (N24, A, en custodia): art. 233 (proyecto de ordenanza junto con el Plan Operativo Anual), art. 239 (categorías
    programáticas), art. 246 (sin afectación específica de ingresos salvo afectaciones legales), art. 247 (fuentes de los
    créditos adicionales)
  N31 LOPPP (A): «Vincular plan, metas y presupuesto cuando corresponda. Versionar objetivos/programas/proyectos y resultados.»
  N04 (A): versionar ejercicio y separar formulación, aprobado y ejecución
  N07: estadal, no aplica; N08: formularios (C), sin reglas atribuidas
UNEXPLAINED_REQUIREMENT_OMISSIONS=0
```

## Frontera con BUD-01/02

- **Programa, subprograma, proyecto y acción específica** ya existen como categorías programáticas con niveles configurables (BUD-02, D02-C). **No se crea un segundo árbol.**
- **Plan y objetivo:** plan operativo anual del ejercicio con sus objetivos (LOPPM 233, N31).
- **Responsable:** unidad de la estructura organizativa ORG-02 del mismo año (VIGENTE), vinculada a cada categoría.
- **Meta física e indicador:** por categoría programática, con cantidad no monetaria (Decimal).
- **«Impedir créditos huérfanos»:** los créditos nacen en BUD-05. Esta Spec deja el contrato: todo crédito futuro deberá referenciar una categoría programática del ejercicio (LOPPM 239 la exige para los gastos municipales). No se implementa aquí.

## Requisitos

| Id | Requisito |
|---|---|
| B34-01 | Plan operativo del ejercicio: denominación y documento DOC-08 vinculado al ejercicio (procedencia con sha256). Uno por ejercicio |
| B34-02 | Objetivos del plan: código (único en el ejercicio) y descripción. No se borra un objetivo vinculado a categorías (409) |
| B34-03 | Vínculo de cada categoría programática con su **unidad responsable** (GovernmentUnit ACTIVA de la estructura ORG-02 VIGENTE del mismo año y empresa) y con un **objetivo** del plan. Ambos opcionales y modificables en BORRADOR. Una unidad de otra estructura, año o empresa da 422/404 |
| B34-04 | Metas físicas por categoría: descripción, unidad de medida, cantidad programada (Decimal > 0, hasta 4 decimales; sin dinero), indicador (nombre) y fórmula opcional |
| B34-05 | Fuentes de financiamiento del ejercicio registradas por el ente: código (único), denominación, procedencia (texto) y documento opcional DOC-08 con sha256; vigencia dentro del año (por defecto desde el 1 de enero) |
| B34-06 | Restricciones de uso por fuente: descripción, fundamento (p. ej. afectación legal, LOPPM 246) y, opcionalmente, las partidas de EGRESO del clasificador del ejercicio a las que se limita. BUD-05 las hará cumplir |
| B34-07 | Todo queda congelado al fijar el ejercicio: el servicio da 409 GOV_BUDGET_YEAR_FROZEN y hay triggers en la base. La fotografía del fundamento incluye plan, objetivos, vínculos, metas, fuentes y restricciones |
| B34-08 | Historia, auditoría CTL-02 (13 eventos), If-Match con la versión del ejercicio, aislamiento 404, 403 sin capacidad. Se reutiliza `gobierno_presupuesto` view/manage |
| B34-09 | Pantalla: dentro del detalle del ejercicio, secciones «Plan operativo y metas» y «Fuentes de financiamiento», con selectores humanos (nunca UUID) |

## Criterios de aceptación

- **AC-01** Plan con documento. Objetivos O1 y O2. Borrar O1 vinculado da 409.
- **AC-02** Vincular la categoría 01 con la unidad DESP (estructura VIGENTE del año) y el objetivo O1. Una unidad de otra empresa o de otro año da 422.
- **AC-03** Meta «Consultas atendidas», unidad «consulta», cantidad 1200.5, indicador «Consultas por mes». Una cantidad ≤ 0 o con 5 decimales da 422.
- **AC-04** Fuente F01 «Ingresos propios» con procedencia y vigencia. Un código duplicado da 422. Una vigencia fuera del año da 422.
- **AC-05** Restricción de F01 con partida 401. Una partida inexistente o de RECURSO da 422.
- **AC-06** Tras aprobar: las mutaciones de plan, metas, vínculos y fuentes dan 409, y el trigger rechaza en la base. La fotografía contiene "plan" y "fuentes".
- **AC-07** Historia y auditoría por cada acción. Otra empresa: 404. Sin capacidad: 403. If-Match obsoleto: 409.
- **AC-08** E2E por el menú, 1280/390/320, Axe sin violaciones serias.

## Compuertas

- **REPORTING_REQUIRED:** BUD03=0 y BUD04=0. Los requisitos no piden reporte; plan frente a ejecución es REP-02. **REPORTING=NOT_APPLICABLE.**
- **DOCUMENTS:** sí (documento del plan y procedencia de las fuentes).

## Fuera de alcance

BUD-05 (créditos y montos), disponibilidad, compromiso, causado y pagado, modificaciones, formulación, avance físico de metas (REP-02), N37, D-GOV-04.
