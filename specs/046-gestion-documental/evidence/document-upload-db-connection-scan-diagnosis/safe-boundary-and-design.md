# Frontera segura y diseño recomendado (NO implementado)

**Frontera propuesta (B1).**
- En `documents/api.py::upload_version`, después de las comprobaciones de licencia, autenticación, permiso, empresa,
  documento, tipo e idempotencia, y antes de `service.upload_version`:
  - si la sesión tiene escrituras pendientes (`db.new`, `db.dirty` o `db.deleted`), fallar cerrado con 500, porque es un
    defecto;
  - si no, `db.commit()` de la transacción de solo lectura.
- `expire_on_commit=False` mantiene `document`, `doc_type` y `actor` cargados.
- Las escrituras posteriores al análisis vuelven a abrir conexión y transacción, y siguen siendo atómicas en un único
  `commit` final.

**Evidencia.** El contrafactual D9 deja 0 conexiones prestadas durante el análisis con el mismo resultado funcional (200,
versión y auditoría). D9b mantiene el rechazo de INFECTED sin versión ni fichero.

| Criterio | B1 |
|---|---|
| SECURITY_PRESERVED | sí: todas las comprobaciones siguen antes del análisis |
| TOCTOU_INTRODUCED | **0**: la ventana es la misma; la transacción retenida no protegía nada (D7a, D7b, D8) |
| OWNERSHIP_MUST_BE_REVALIDATED | no para B1; sí para cerrar el TOCTOU existente (deuda aparte) |
| RESOURCE_CAN_CHANGE_DURING_SCAN | sí, hoy y con B1, igual |
| IDEMPOTENCY_IMPACT | ninguno: la consulta es previa y el registro es posterior, en la misma transacción final |
| AUDIT_IMPACT | ninguno: la auditoría de subida sigue en la transacción final; la de rechazo ya se pierde hoy (deuda aparte) |
| ATOMICITY_IMPACT | ninguno: todas las escrituras quedan en una transacción (la posterior al análisis) |
| STORAGE_ORPHAN_RISK | igual que hoy: binario escrito y fallo en base dejan basura recuperable (D7b) |
| DB_ORPHAN_RISK | ninguno nuevo |
| FAIL_CLOSED_PRESERVED | sí: sin análisis no hay versión; INFECTED y SCAN_FAILED se rechazan igual |

**Alternativas descartadas:**
- **B2, analizar antes de autenticar.** Analizaría ficheros de usuarios no autorizados y abriría una vía de coste o DoS.
- **B3, revalidar el recurso tras el análisis.** No es necesaria para liberar la conexión, y cambia el contrato documental
  (archivado y borrado concurrentes). Queda como decisión aparte junto con la actualización perdida.

SAFE_BOUNDARY_PROVEN = **1** para B1 · OWNER_DECISION_REQUIRED_FOR_FIX = **0**: no cambia semántica, seguridad, auditoría
ni atomicidad; solo parte una transacción de solo lectura sin propósito. MATERIAL_OQ = 0.
