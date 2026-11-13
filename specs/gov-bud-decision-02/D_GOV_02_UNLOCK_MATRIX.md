# D_GOV_02_UNLOCK_MATRIX (recalculada; la tabla supone la opción recomendada A)

`UNLOCKED_BY_D_GOV_02`:

- **YES**: tras la decisión, el proceso queda solo con dependencias de construcción (otros procesos BUD) o con datos que el ente registra.
- **PARTIAL**: una parte queda libre y otra sigue bloqueada.
- **NO**: sigue bloqueado por otra causa material o externa.

| PROCESS | CURRENT_BLOCKER | UNLOCKED_BY_D_GOV_02 | STILL_BLOCKED_BY | P0_P1 | DOWNSTREAM_PROCESSES_UNLOCKED |
|---|---|---|---|---|---|
| BUD-01 | D-GOV-02; N07, N08, N10 | **YES** | N07 no aplica (estadal). N08 y N10 solo afectan formularios y catálogo, no el ejercicio (LOPPM 234-236, 250 son clase A) | P0 | Todo BUD |
| BUD-02 | D-GOV-02; N10 | **YES (estructura)** | El contenido del catálogo depende de la sub-decisión D02-B (importa el ente con procedencia, o espera la copia oficial) | P0 | BUD-05, 06, CTL-08 (en parte) |
| BUD-03 | D-GOV-02; N07, N08 | **PARTIAL** | Las categorías programáticas quedan libres (LOPPM 239). Metas físicas, indicadores y POA: GOV-BUD-004 lo exige «cuando la norma local» lo pida (N37) | P0 | REQ-01 (en parte), ORG-05 (en parte), REP-02 (en parte) |
| BUD-04 | D-GOV-02; N07, N08 | **YES** | — (LOPPM 247 enumera las fuentes) | P0 | BUD-05, BUD-10 |
| BUD-05 | D-GOV-02; N07, N08, N37 | **PARTIAL** | Con A se registra el **aprobado con su acto** (GOV-BUD-008 y parte de 007). La **formulación** (GOV-BUD-006, escenarios y techos) pasa a LATER_PHASE; además necesitaría N08 y el calendario local | P0 | BUD-06, 08, 10, 11, 12 |
| BUD-10 | D-GOV-02; N09, N37 | **YES (tipos LOPPM)** | Los límites concretos los fija la ordenanza: dato del ente, no regla codificada. Los tipos que no están en la LOPPM esperan N09 | P0 | BUD-11, REP-01 |
| BUD-13 | D-GOV-02; N07-N10 | **NO** | N08, N10 y plantillas oficiales (clase C) | P1 | INT-05 |
| INT-05 | D-GOV-02; D-GOV-04 | **NO** | D-GOV-04 (plan de cuentas ONCOP) | P1 | — |
| REP-01 | D-GOV-02 | **YES** (cuando exista la cadena) | Construir BUD-05..11 | P1 | — |
| REP-02 | D-GOV-02 | **PARTIAL** | Metas físicas (BUD-03 completo) | P1 | — |
| CTL-08 | D-GOV-02; proveedores N37; OQ-CTL08-01 | **NO** | Proveedores N37 y OQ-CTL08-01 | P0 | — |

## Recuento

```text
CITAN_D_GOV_02=11
UNLOCKED_YES=5        (BUD-01, BUD-02 estructural, BUD-04, BUD-10 tipos LOPPM, REP-01)
UNLOCKED_PARTIAL=3    (BUD-03, BUD-05 aprobado, REP-02)
STILL_BLOCKED=3       (BUD-13, INT-05, CTL-08)
P0_UNLOCKED_YES_OR_PARTIAL=6   (BUD-01, 02, 03, 04, 05, 10)
```

**Cadena aguas abajo que queda construible** (hoy NOT_STARTED, sin otra decisión material):

- BUD-06 disponibilidad y certificación;
- BUD-08 compromiso;
- BUD-11 ledger;
- BUD-12 cierre y reconducción;
- REQ-02 verificación previa a la contratación.

Son 5 P0 más; con los anteriores suman **11 P0 alcanzables**.

**Siguen bloqueados por otras causas**, aunque se cierre D-GOV-02:

- BUD-07: N37;
- BUD-09: N36, para el asiento;
- CNT-01: monto;
- TRE-03/08/10: TRE-04 y N37;
- ACC-05: D-GOV-04.
