# SPEC 046 · Delta de diagnóstico — DOCUMENT-UPLOAD-HOLDS-DB-CONNECTION-DURING-SCAN

Dueña: Spec 046 (gestión documental). Apoyo: Spec 001 (sesión por petición). Origen: diagnóstico de la Spec 054,
`specs/012-auditoria-integral-e2e/spec054-e2e-pool-exhaustion-diagnosis-delta.md`. Fecha 2026-10-19, `develop`, HEAD
`0e2cb7b`. Sin cambio de producto, de pruebas ni de QA. Evidencia: `evidence/document-upload-db-connection-scan-diagnosis/`.

## 1. Specify · 2. Clarify
Hay que determinar por qué una carga retiene una conexión durante el análisis, y si existe una frontera segura que lo
evite sin tocar autenticación, autorización, auditoría, atomicidad ni semántica documental. Ciclo de diagnóstico: no se
implementa nada.

## 3. Plan · 4. Constitution gate · 5. Tareas
Inventario del flujo, sondas desechables D1-D9 y análisis de frontera. Sin producto, pool, timeouts ni analizador ✔.
DeepSeek 0: no hubo código versionado.

## 6. Resultado
**DIAGNOSIS COMPLETE — ROOT CAUSE AND SAFE BOUNDARY PROVEN.**
- **Causa.** La sesión por petición hace autobegin de una transacción de solo lectura en su primera sentencia (la licencia
  de escritura). `upload_version` analiza dentro de ella y nadie la confirma hasta el final. Detalle en `root-cause.md`.
- **Frontera segura B1.** Confirmar esa transacción, sin escrituras y fallando cerrado si las hubiera, antes del servicio.
  El contrafactual D9 lo valida. Detalle en `safe-boundary-and-design.md`.

**Defectos previos encontrados (no absorbidos; cada uno con su ciclo):**
- `DOCUMENT-ARCHIVE-LOST-UPDATE-DURING-UPLOAD` (D7a): archivar durante una carga se pierde; el documento vuelve a ACTIVE.
- `DOCUMENT-DELETE-DURING-UPLOAD-ORPHAN-500` (D7b): borrar durante una carga da 500 y deja un binario huérfano.
- `DOCUMENT-SCAN-REJECTION-AUDIT-NOT-PERSISTED` (D2b): la auditoría `DOCUMENT_SCAN_REJECTED` se revierte con el 422.

## 7. Siguiente
Ciclo de corrección de la frontera B1 (dueña 046). Los tres defectos previos requieren decisiones de contrato de la dueña.
Estado de la deuda: **ROOT CAUSE AND SAFE BOUNDARY PROVEN — FIX NOT IMPLEMENTED (OPEN)**.
