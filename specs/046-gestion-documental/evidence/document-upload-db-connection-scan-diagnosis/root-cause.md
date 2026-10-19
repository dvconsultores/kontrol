# Causa raíz — PROVEN
**ROOT_CAUSE_CLASS = `REQUEST_SCOPED_SESSION_HOLDS_CONNECTION` + `RESOURCE_LOOKUP_OPENS_TRANSACTION`** (C + B).
- La sesión por petición de `get_db` hace autobegin de una transacción en su primera sentencia, que es la dependencia de
  licencia de escritura (`SELECT installations`).
- Las lecturas de autenticación, permiso, empresa, documento y tipo continúan en esa transacción.
- `upload_version` ejecuta el análisis dentro de ella, y nadie la confirma hasta el `commit` final.
- La conexión queda prestada durante todo el análisis, de 6 a 21 s medidos, en estado `idle in transaction`.

**No es intencional (descartada D).** La transacción es de solo lectura (sin `xid`), sin bloqueos de fila y en READ
COMMITTED: no protege ningún dato ni invariante (TRANSACTION_PURPOSE = ninguno). El código lo confirma: el comentario del
paso 7 solo exige la atomicidad de las escrituras posteriores, que siguen en una transacción propia.

**Descartadas:**
| Causa | Veredicto |
|---|---|
| A, autenticación | solo es una de las lecturas |
| E, auditoría | posterior al análisis |
| F, almacenamiento | posterior al análisis |

**Efecto.** Cada carga en curso inmoviliza una conexión del pool, y con 10 concurrentes hubo 10 prestadas. Por encima de 15
satura el pool. Tras LICENSE-MIDDLEWARE-BLOCKS-EVENT-LOOP eso ya no congela el servidor, pero otras peticiones esperan
conexión hasta 30 s. Además, los `AccessShareLock` retenidos bloquean DDL (migraciones) durante el análisis.

**Dueña.** OWNER_SPEC = **046** (flujo de carga). SUPPORTING_SPECS = 001 (patrón de sesión por petición). Diagnóstico sin
decisión de la dueña.
