# N10 — GRAFO DE DEPENDENCIAS

Specs afectadas por ARCH-MC-001, con su estado antes y después. Que la
multiempresa deje de bloquear a una Spec **no** significa que esa Spec esté
terminada: son dos afirmaciones distintas y aquí se mantienen separadas.

| Spec | Antes de ARCH-MC-001 | Después de N10 | Bloqueo restante |
|---|---|---|---|
| 045 — Aprobaciones | Bloqueada: la empresa venía del cuerpo | **Desbloqueada** | Ninguno de multiempresa. N10 corrigió además la elegibilidad de aprobadores, que ignoraba la empresa |
| 046 — Documentos | Bloqueada + `REM-046-001` abierta | **RECONVERGED**, remediación cerrada | S3 real (P1 externa) |
| 011 — Unidades y presentaciones | Consistente | Consistente | Dos rutas crean la misma conversión; unificar es cambio de contrato (registrado) |
| 012 — Maestros comerciales | `APTA_DOCUMENTALMENTE — BLOCKED_BY_ARCH_MC_001` | Ver revalidación documental de N10 | — |
| 052 — Retención | No empezada | No empezada | Planificador de retención (P1) |
| Spec futura de eventos | No empezada | No empezada | `outbox_events` migrada, **sin productores** |

## Consumidores de la 046

`STILL_BLOCKED_BY_046`: **0** (eran 2 antes de N9).
`FULLY_UNLOCKED`: **0**, y es correcto: ninguna de las consumidoras está
terminada por su propio alcance, con independencia de la 046.
