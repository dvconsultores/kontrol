# Firmas de fallo

| Firma | Qué | Observada |
|---|---|---|
| F1 unexpected 500 | el INSERT del segundo hilo falla con `ResourceClosedError` (3 de 4 fallos) o `sqlite3.DatabaseError` (1 de 4) sobre la conexión compartida; no es `IntegrityError` → 500 | **sí** (sonda) |
| F2 wrong number of successful inserts | — | no (siempre 1 fila) |
| F3 wrong number of conflicts | sí, como consecuencia de F1: `[200]` en vez de `[200, 409]` | **sí** (la aserción que se ve) |
| F4 wrong final row count | no (la fila del primer hilo sobrevive en los fallos naturales; en el entrelazado I0 sobre la conexión compartida sí: véase `controlled-interleaving.md`) | parcial |
| F5 IntegrityError leaked | no: el `IntegrityError` genuino se traduce a 409 | no |
| F6 OperationalError database is locked | no (una sola conexión) | no |
| F7 transaction closed / invalid state | `ResourceClosedError` es exactamente eso: el cursor/resultado cerrado por el `commit` del otro hilo | **sí** |
| F8 SQLite programming error | no | no |
| F9 assertion-only mismatch | la aserción `[200] == [200, 409]` es el síntoma visible | **sí** |
| F10 other | `sqlite3.DatabaseError` en lugar de `IntegrityError` para la misma violación única | **sí** |

`UNKNOWN = 0`. Frecuencia de la prueba sola: 8/20 sin sonda (`[200]` ×6, `[]` ×1 —los dos hilos muertos—, `[409]` ×1 —el
rollback del perdedor deshizo la fila del ganador—) y 4/20 con sonda: **intermitente ya en solitario**, no solo bajo la
suite completa. Series completas en `frequency-study.md`.
