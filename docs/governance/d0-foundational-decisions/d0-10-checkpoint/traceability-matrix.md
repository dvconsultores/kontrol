# D0-10 · TRAZABILIDAD DEL CHECKPOINT DE DECISIÓN

## A · Requisitos del ciclo

| Requisito | OQ | Evidencia | Decisión | Regla ADR | Owner | Artefacto | Estado |
|---|---|---|---|---|---|---|---|
| FR-D010-C-001 · los 15 estados identificados | 01 | `ADR-D0-010` §Conjunto | catálogo extraído | — | D0-10 | matriz de dueños | ✔ |
| FR-D010-C-002 · no se mezclan con lote/serial | 01 | `FR-003-035` · `LOT_SERIAL_TRANSITIONS` | dos vocabularios, 6 etiquetas comunes, 0 semánticas | — | D0-10 | matriz de dueños §1 | ✔ |
| FR-D010-C-003 · cada transición activa tiene origen y destino | 01 | tabla de nueve | declarada | R-D0-10-7 | 023 | matriz de transiciones | ✔ |
| FR-D010-C-004 · cada transición activa tiene owner del evento | 01 | columna «Owner» | 019, 020, 021, 025 | — | proceso | matriz de transiciones | ✔ |
| FR-D010-C-005 · regla de permiso | 01 | columna «Permiso» | `compras:receive`, `compras:incident`, `inventario:release`, `inventario:transfer` | — | 002/003 | matriz de transiciones | ✔ |
| FR-D010-C-006 · regla de aprobación | 01 | columna «Aprobación» | solo #9, vía Spec 045 | — | 045 | matriz de transiciones | ✔ |
| FR-D010-C-007 · lo no declarado se rechaza | 01 | regla de gobierno | `DENIED` | **R-D0-10-7** | 023 | matriz de transiciones | ✔ |
| FR-D010-C-008 · R-D0-10-7 implementable sin inferencias | 01 | `can_transition` determinista | sí | R-D0-10-7 | 023 | ADR v2 §Gobierno | ✔ |
| FR-D010-C-009 · la 021 recibe sus transiciones mínimas | 01 | #2, #3, #7, #8 (+#1) | cuatro, con autoridad | R-D0-10-4 | 021 | matriz de transiciones | ✔ |
| FR-D010-C-010 · no se inventan transiciones futuras | 01 | tabla FUTURE_OWNER | `DENIED` hasta que su Spec las active | R-D0-10-7 | cada Spec | matriz de transiciones | ✔ |
| FR-D010-C-011 · no deja `qty_reserved > qty_on_hand` | 02 | `POL-D0-002` §6 | invariante declarada | **R-D0-10-9** | 023 | ADR v2 | ✔ |
| FR-D010-C-012 · sin negativos fuera de `allow_negative` | 02 | `POL-D0-002` §6 | prohibido explícitamente | R-D0-10-9 | 023 | análisis del conflicto | ✔ |
| FR-D010-C-013 · no se liberan compromisos en silencio | 02 | `POL-D0-002` §8 tabla cerrada | opción C rechazada | R-D0-10-10 | 030 | análisis del conflicto | ✔ |
| FR-D010-C-014 · el conflicto tiene resolución contractual | 02 | ninguna arista activa lo produce | `DENIED` por no declarada; elección diferida con dueño | R-D0-10-10 | Spec que active | análisis del conflicto | ✔ |
| FR-D010-C-015 · la 023 no modifica pedidos | 02 | frontera explícita | sí | R-D0-10-10 | 023 | ADR v2 §Gobierno | ✔ |
| FR-D010-C-016 · la 030 conserva la autoridad de reservas | 02 | `D0-03` · `POL-D0-002` §8 | intacta | — | 030 | ADR v2 §Alternativas | ✔ |
| FR-D010-C-017 · conservación física | 01 | R-D0-10-5 | derivable, no requiere decisión | R-D0-10-5 | 023 | análisis del conflicto | ✔ |
| FR-D010-C-018 · lote/serial fuera de la matriz | 01 | `FR-003-035` | no participa | — | 024 | matriz de dueños §1 | ✔ |
| FR-D010-C-019 · el movimiento conservará origen y destino | — | ledger sin estado (medido) | exigido al próximo ciclo | R-D0-10-5 | 023 | ADR v2 §Consecuencias | ✔ diferido |
| FR-D010-C-020 · `recompute_balances` sin colapsar | — | fija `DISPONIBLE` (medido) | exigido al próximo ciclo | R-D0-10-5 | 023 | ADR v2 §Consecuencias | ✔ diferido |
| FR-D010-C-021 · `confirm_transfer_receipt` respetará el destino | — | defecto vivo (medido) | transición #9 le da autoridad | `FR-003-062` | 023 | ADR v2 §Consecuencias | ✔ diferido |
| FR-D010-C-022 · los diez call sites implementables sin decisiones | — | matriz del ciclo de 023 | sí | — | 023 | `spec023-multistate-cycle.md` §2.3 | ✔ |
| FR-D010-C-023 · la 021 no se implementa | — | — | no se tocó | — | — | — | ✔ |
| FR-D010-C-024 · cambios de código = 0 | — | `git diff` | backend 0 · frontend 0 · Alembic 0 | — | — | guardia de commit | ✔ |
| FR-D010-C-025 · trazabilidad 100 % | — | esta tabla | 25/25 | — | — | — | ✔ |

## B · Estado → productor → consumidor → regla

Ver `d0-10-state-owner-matrix.md`. Quince estados, cada uno con productor, consumidor y clasificación
(`ACTIVO`, `FUTURE`, `FUTURE_OWNER`, `SIN DUEÑO`). Diez sin productor hoy; nueve por Spec no
construida y uno —`RESERVADO`— porque el reservado real es un contador, no una custodia.

## C · Conflicto de reservas

| Requisito | Decisión | Fuente de la política | Impacto en 030 | Impacto en 023 | Implicación de prueba |
|---|---|---|---|---|---|
| No dejar reservado > físico | **R-D0-10-9** | `POL-D0-002` §6 | ninguno | valida antes de mover | hostil: reclasificar con reserva viva |
| No liberar reservas desde inventario | opción C **rechazada** | `POL-D0-002` §8 (tabla cerrada) | autoridad intacta | no toca `Reservation` | guardia estructural |
| No reasignar a otro stock | opción D **FUTURE** | `POL-D0-002` §7 | ninguno | fuera de alcance | — |
| Elegir entre bloquear y parcial | **R-D0-10-10**, en el ciclo que active la arista | — | por determinar | por determinar | del ciclo que la active |
| Caso canónico hoy | `DENIED` | R-D0-10-7 | ninguno | rechaza la transición | `can_transition(DISPONIBLE, no vendible) → DENIED` |

**Cobertura: 100 %. Huérfanos: 0. OQ materiales: 0.**
