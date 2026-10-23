# Primer intento de certificación E2E final (2026-10-22, 21:58–22:11 UTC): no verde, atribuido a ENVIRONMENT

| Corrida | Intérprete del arnés = migración | Resultado | Suite | Ayudantes (muestreo /proc) |
|---|---|---|---|---|
| `r20261022t215832` V0 | 3.11.16 = 3.11.16 | 280 / 1 fallo / 3 sin ejecutar | 331,4 s | 102 de 102 en 3.11 |
| `r20261022t220434` V5 | 3.13.16 = 3.13.16 | 277 / 3 fallos / 4 sin ejecutar | 347,4 s | **90 de 90 en 3.13** (el arreglo funciona) |

**Firma:** `Test timeout of 30000ms exceeded`.
- V0: `licencia-revision.spec.ts:115`.
- V5: `documents-a11y.spec.ts:98`, `documents.spec.ts:246` y `:286`, las tres cargas de documentos que pasan por `clamscan`.

**Anfitrión** (`telemetria.jsonl`):

| Corrida | Swap | Páginas leídas de swap | Carga |
|---|---|---|---|
| Previas que pasaron | 1,1 → 3,8 GB | +232 000 (V0), +370 000 (V5) | — |
| Final V0 | 3,6 → 5,7 GB | +628 000 | load1 14,3 al terminar |
| Final V5 | 5,7 → 6,8 GB | +1 253 000 | load1 15,2 al empezar |

- Procesos ajenos a la certificación en ese momento: varios `WPEWebProcess` (WebKit; uno al 232 % de CPU, ≈ 4 GB de RSS entre todos) y un `next-server` de otro proyecto.
- `boottime − monotonic` constante (31 281,5 s): sin suspensión durante las corridas. Reloj sin salto y red sin cambio.

**Causalidad del ciclo = 0:**
- **V0:** el ciclo no cambia el intérprete de los ayudantes (V0 antes y después). `licencia-revision` pasó de 19,5 s en la previa V0 a 34,4 s en la final V0, con el mismo código efectivo.
- **V5:** microbanco intercalado de arranque e imports reales de los ayudantes (`microbanco.txt`, 12 rondas, con load ≈ 15), V5/V0 = **1,08×** en la mediana (1,22 s frente a 1,13 s). Además, las tres pruebas de documentos que fallan no lanzan ayudantes Python.

**ROOT_CAUSE_CLASS = ENVIRONMENT** (contención del anfitrión). Es una recurrencia de E2E-LICENSE-REVISION-ENVIRONMENT-LATENCY, que esta vez también alcanza a las cargas con `clamscan`. No se absorbe: ningún timeout, reintento ni prueba cambia.

**Decisión de certificación:** no se repite para conseguir verde. La E2E final se vuelve a ejecutar **una vez por intérprete**, solo cuando se cumple una condición de salud explícita y medida (`salud.jsonl`): load1 < 3, más de 5 GB disponibles y paginación entrante < 2000 páginas/min, durante 3 minutos seguidos.
