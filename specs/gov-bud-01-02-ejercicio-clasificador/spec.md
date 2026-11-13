# Spec · BUD-01 + BUD-02 Ejercicio presupuestario y clasificador versionado (GOV-BUD-001, GOV-BUD-002; P0)

## Autorización y decisión

- Encargo P1 «BUD-01 + BUD-02» de la dueña (2026-11-13), que nombra la iniciativa.
- D-GOV-02 CLOSED con A/1/1/1 (`specs/gov-bud-decision-02/OWNER_DECISION.md`):
  - `V1_SCOPE=APPROVED_BUDGET_AND_EXECUTION`;
  - `FULL_FORMULATION_V1=0`;
  - `CLASSIFIER_SOURCE=TENANT_PROVIDED_WITH_PROVENANCE`;
  - niveles programáticos configurables por ente;
  - precompromiso configurable, apagado por defecto.

## Fuentes

- **IR §7.2:**
  - GOV-BUD-001: crear ejercicios con estado, calendario, moneda funcional, clasificadores y versión normativa aplicable;
  - GOV-BUD-002: importar o versionar el clasificador por ejercicio con código, denominación, tipo, nivel y vigencia;
  - GOV-BUD-003 (sólo la estructura): categorías programáticas.
- **LOPPM (N24, clase A, en custodia):**
  - art. 229: ordenanza anual;
  - arts. 234-236: reconducción;
  - art. 239: sectores, programas, subprogramas, proyectos o categorías equivalentes, más partidas;
  - art. 248: cierre al 31 de diciembre;
  - art. 250: ejercicio = año calendario.
- **N04 (clase A):** separar formulación, aprobado, modificaciones y ejecución; versionar ejercicio y clasificador; no codificar una edición anual.
- **N08, N09 y N10 (clase C, no custodiados):** no se les atribuye ninguna regla. El clasificador es un dato del ente.
- **N07** es estadal y no gobierna el piloto municipal.

## Historia

Como **Presupuesto del ente** quiero:

1. crear el ejercicio del año;
2. declarar los niveles de mi estructura programática y registrar sus categorías;
3. registrar o importar el clasificador presupuestario que aplico, con su procedencia y documento;
4. fijar el ejercicio como **aprobado** (ordenanza sancionada) o **reconducido** (sin sanción al 15 de diciembre), con su soporte;
5. al terminar el año, **cerrarlo**.

Lo fijado no se puede alterar en silencio, y toda la historia queda auditada.

## Requisitos

| Id | Requisito |
|---|---|
| BUD12-01 | **Identidad del ejercicio.** Ente (empresa) + año (2000–2100), único por ente. Calendario: 1 de enero a 31 de diciembre (LOPPM 250). Moneda funcional: se copia de la moneda funcional de la empresa al crear el ejercicio y es inmutable. No hay multimoneda presupuestaria |
| BUD12-02 | **Propiedad.** `tenant_id` y `company_id` salen siempre del contexto autenticado; nunca del cliente |
| BUD12-03 | **Ciclo de vida.** `BORRADOR → APROBADO`, `BORRADOR → RECONDUCIDO`, `APROBADO \| RECONDUCIDO → CERRADO`. Cualquier otra transición devuelve 409. Sin borrado de ejercicios |
| BUD12-04 | **Semántica legal.** Ver el contrato de estados del plan. **APROBADO** exige la ordenanza sancionada: referencia, fecha de sanción y documento. **RECONDUCIDO** solo se admite pasado el 15 de diciembre del año anterior (LOPPM 234) y exige la publicación del reconducido (LOPPM 235). `reconduccion_definitiva` es un dato calculado: RECONDUCIDO y hoy > 31 de marzo del año (LOPPM 236). El paso RECONDUCIDO → APROBADO (sanción tardía) queda para BUD-05, donde se cargan los créditos. **CERRADO** solo pasado el 31 de diciembre del año (LOPPM 248) |
| BUD12-05 | **Jerarquía programática configurable.** El ente declara de 1 a 8 niveles con nombre propio. Las categorías tienen nivel y padre: el padre es del mismo ejercicio y del nivel inmediatamente superior; el nivel 1 no tiene padre. El código completo se compone por segmentos. Sin ciclos, sin padres ajenos y sin niveles salteados |
| BUD12-06 | **Versión del clasificador.** Un clasificador por ejercicio (edición, fecha de edición). Sus partidas llevan tipo (RECURSO o EGRESO), código, denominación, nivel (1–12), padre del mismo tipo y nivel −1, y vigencia dentro del año. Alta individual e **importación CSV todo-o-nada** (hasta 5000 filas) |
| BUD12-07 | **Procedencia.** Descripción de la procedencia (obligatoria), documento ACTIVO vinculado al ejercicio y su sha256. La UI dice «Clasificador registrado por el ente» y nunca «oficial» |
| BUD12-08 | **Fotografía inmutable.** Al aprobar o reconducir se guarda un **fundamento** append-only: tipo, referencia, fecha, documento, sha256, una fotografía canónica de niveles, categorías y clasificador, y su huella sha256. Desde entonces niveles, categorías, clasificador y partidas quedan congelados (409 y triggers en la base) |
| BUD12-09 | **Evidencia por DOC-08.** Los documentos se cargan por el panel de documentos con el recurso `GovernmentBudgetYear`, sin almacenamiento paralelo. La ordenanza **no** se registra como acto LOPA |
| BUD12-10 | **Historia.** Historia append-only por ejercicio con cada evento material |
| BUD12-11 | **Permisos.** `gobierno_presupuesto`: `view` (consultar), `manage` (crear y configurar en BORRADOR), `approve` (aprobar, reconducir y política de precompromiso), `close` (cerrar) |
| BUD12-12 | **MFA.** `approve` y `close` en SENSITIVE_PERMISSIONS (exige MFA, igual que `gobierno_caja:activate`); `view` y `manage` en STANDARD_PERMISSIONS (patrón TRE-02). Corregido tras medir la política real: el borrador decía PRIVILEGED/SENSITIVE |
| BUD12-13 | **Auditoría.** Por CTL-02 (`record_audit`) con 14 eventos de catálogo. Sin segundo ledger |
| BUD12-14 | **Aislamiento.** Recurso de otro ente: 404 |
| BUD12-15 | **Concurrencia.** `If-Match` con la versión del ejercicio en toda mutación, más bloqueo de fila del ejercicio. Cada cambio de hijos sube la versión. Doble aprobación, edición contra aprobación y cierre doble: uno gana y el otro recibe 409 |
| BUD12-16 | **Compatibilidad aguas abajo.** Los ids de ejercicio, categoría y partida son estables y referenciables por futuros créditos y movimientos. El precompromiso queda como política (`activo`, `vigente_desde`) sin transacciones. Los enteros `ejercicio` de ORG-02, TRE-02 y CTL-05 no se tocan |
| BUD12-17 | **UAT.** Menú Gobierno › Presupuesto › Ejercicios presupuestarios, con pantalla de lista y de detalle, humo y tarjeta de la dueña |

## Criterios de aceptación

- **AC-01** Se crea el ejercicio 20XX: queda BORRADOR, con la moneda de la empresa. Un duplicado del mismo año devuelve 409.
- **AC-02** Se declaran 3 niveles y se crean categorías padre e hijo. Un hijo sin padre, con padre de otro nivel o de otro ejercicio da 422. Borrar una categoría con hijos da 409.
- **AC-03** Se registra el clasificador con procedencia y documento, y se importa un CSV. Un CSV con un solo error no importa nada (422 con la fila).
- **AC-04** Aprobar sin estructura completa da 422. Aprobado con fundamento: estado APROBADO, fundamento con huella. Editar después da 409, y en la base el trigger lo rechaza.
- **AC-05** Reconducir antes del 16 de diciembre del año anterior da 409. Después, RECONDUCIDO con fundamento.
- **AC-06** Cerrar un ejercicio del año en curso da 409. Uno pasado y aprobado pasa a CERRADO.
- **AC-07** Precompromiso: falso al crear. Activarlo exige `approve`, queda en historia y en auditoría, y no crea transacciones.
- **AC-08** Otra empresa recibe 404. Sin permiso, 403.
- **AC-09** Dos aprobaciones con la misma versión: una 200 y otra 409.
- **AC-10** E2E por el menú a 1280, 390 y 320 px, sin violaciones serias de Axe.

## Fuera de alcance

Formulación; créditos y montos; disponibilidad; precompromiso transaccional; compromiso, causado y pagado; modificaciones; catálogo ONAPRE precargado; formularios ONAPRE; N37; D-GOV-04; PAGADOR.
