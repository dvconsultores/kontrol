# ARCHITECTURE_CONSEQUENCES · D-GOV-02 (bajo la opción A; nada se construye sin la decisión)

## STRUCTURAL_MODEL frente a EXERCISE_SPECIFIC_CATALOG

- **Modelo estructural** (código, con fuente A): ejercicio; versión del clasificador; nodo del clasificador (código, denominación, tipo ingreso o gasto, nivel, padre, vigencia); categoría programática con niveles configurables; fuente de financiamiento; crédito presupuestario (categoría × partida × fuente × unidad ejecutora); modificación; movimiento del ledger; certificación.
- **Catálogo del ejercicio** (dato, clase C): los códigos y denominaciones ONAPRE de cada año. El ente los registra o importa con su procedencia (edición, fecha y documento custodiado vía DOC-08). **No se precarga ningún código** ni ninguna jerarquía real.

## Decisiones de diseño previstas (a fijar en cada Spec BUD)

1. **Ejercicio.** Será una entidad propia con estado: BORRADOR → APROBADO | RECONDUCIDO → CERRADO.
   - Lleva calendario (LOPPM 250), moneda funcional y la versión del clasificador.
   - La transición RECONDUCIDO sigue LOPPM 234-236: el reconducido pasa a definitivo al 31 de marzo.
   - Los enteros `ejercicio` de ORG-02, TRE-02 y CTL-05 **no se migran**. Se relacionan por (ente, año).
2. **Aprobado.** Es inmutable una vez registrado, y se enlaza a su acto:
   - la **ordenanza** del Concejo (no es un acto LOPA de DOC-02): número y fecha de Gaceta, con el documento por DOC-08;
   - o la publicación del **reconducido** (LOPPM 235).
   - La formulación futura entra como versiones previas del mismo presupuesto (GOV-BUD-007).
3. **Ledger.** Es append-only, con triggers como en `audit_events`. El saldo se reconstruye: aprobado + modificaciones − compromisos − causados (− pagados cuando exista TRE-04). No habrá saldos editables.
4. **Dinero.** `NUMERIC(20,2)` y `Decimal`. La escala exacta se fija en la Spec de BUD-05, con vectores de prueba. No se compensan redondeos.
5. **Modificaciones.** Los tipos vienen de la LOPPM:
   - traspaso: lo acuerda el alcalde, dentro de los límites de la ordenanza (dato);
   - crédito adicional: lo aprueba el Concejo, con una de las 5 fuentes de LOPPM 247;
   - rectificación: tope del 3 % de los ingresos estimados, no se incrementa por traspaso;
   - insubsistencia.

   Cada modificación requiere un acto: DOC-02 para los actos del alcalde, y el registro normativo para los del Concejo. La autoridad sale de ORG-07.
6. **Disponibilidad.** Se calcula en el momento de la operación, con bloqueo por crédito (concurrencia). No admite saldo negativo silencioso (GOV-BUD-012).
7. **Cierre** (LOPPM 248-249). Pasado el 31 de diciembre no se compromete ni se causa. Lo comprometido y no causado se imputa al ejercicio siguiente como movimiento trazable, nunca por sobrescritura.
8. **Aislamiento.** El ente y la empresa salen del contexto del backend. Una consulta cruzada entre entes devuelve 404. La auditoría va por CTL-02 y la SoD por CTL-01: quien certifica no compromete.
9. **Shared Core.** `SHARED_CORE_CHANGE_REQUIRED=0` previsto. Si alguna Spec lo necesitara, se declara antes de tocarlo (§23 del encargo).
10. **Capacidades.** Una nueva familia `gobierno_presupuesto`, con acciones de consulta, registro, modificación, certificación y cierre (MFA en las de efecto). Se diseña en la Spec de BUD-01.

## Primer proceso si la dueña elige A (orden por dependencia real, no por nombre)

BUD-01 y BUD-02 son mutuamente necesarios:

- el ejercicio declara su clasificador (GOV-BUD-001);
- el clasificador se versiona por ejercicio (GOV-BUD-002).

**Primer ciclo:** BUD-01 + BUD-02 estructural, «Ejercicio presupuestario y su clasificador versionado». Después:

1. BUD-04 + BUD-03 (estructura);
2. BUD-05 aprobado + BUD-06;
3. BUD-08;
4. BUD-10;
5. BUD-11 y BUD-12.
