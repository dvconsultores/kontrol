# Certificación — huella de las bases protegidas (y cierre de B1)

**Árbol certificado:** HEAD `97e1ea8` + `qa/e2e_base.py` (`huella`) + `resources/backend/tests/test_e2e_base_ciclo.py`.
Todas las corridas usan `clamscan` real.

| Puerta | Corrida | Resultado | Reconciliación | Veredicto |
|---|---|---|---|---|
| SQLite #1 | `r20261019t185014p19659ndbb334` | rc 0 · **1885/0/1056** · 696,5 s · NORMAL | 1885/0/1046 + 10 omitidas: los 10 casos nuevos viven en un módulo que ya era solo de PostgreSQL (`pytestmark` preexistente) | PASS |
| SQLite #2 | `r20261019t190204p100654n1ae77f` | rc 0 · **1885/0/1056** · 691,2 s · NORMAL | ídem | PASS |
| **PostgreSQL** | `r20261019t191349p180737n5cb01b` | rc 0 · **2915/0/26** · 1819,6 s · NORMAL | 2904 + 1 (`test_e2ecorrida_01`, antes roja) + 10 casos nuevos = 2915 | **PASS** |
| E2E | `r20261019t194433p448963n7bdd73` | rc 0 · **284/0/0** · suite 271,7 s · limpieza LIMPIA | 284 | PASS |
| OpenAPI | — | **544/533/11**, esquema `BearerAccessToken` | sin cambio | PASS, OPENAPI_CHANGE = 0 |

**En la corrida de PostgreSQL:**
- `test_e2ecorrida_01`: PASS (16,2 s).
- `test_e2eciclo_23`: PASS.
- Huella 24–31: PASS. La 24, con autovacuum real, tardó 5,9 s.

**E2E:**
- Huella nueva en el manifiesto: `protegidas_sin_cambios = True`.
- `ktest`: `{oid 16386, sesiones 1054, clientes []}` igual antes y después.
- `backend.log`: 0 `QueuePool limit`, 0 «Error no controlado», 0 respuestas 500.

**Equipo:**
- Precheck: MemAvailable 7,2 GB, swap 0, carga 1,28, puertos libres, 0 clamscan.
- Muestreo de 1 Hz: 282 muestras; memoria disponible mínima 1339 MB, swap máxima 3086 MB, carga máxima 9,89, hasta 5
  clamscan.

**Entorno:**
- El equipo se reinició antes del ciclo: PostgreSQL de QA se volvió a arrancar y `ktest` se recreó con
  `qa/pg-provision.sh mkdb ktest`. Esa es la línea base de sesiones de esta corrida.
- Reloj sincronizado por NTP.
