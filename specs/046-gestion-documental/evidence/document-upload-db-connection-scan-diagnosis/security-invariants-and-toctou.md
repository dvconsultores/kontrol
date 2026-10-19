# Invariantes de seguridad y TOCTOU
| Invariante | Antes del análisis | Necesita base |
|---|---|---|
| AUTH_BEFORE_SCAN | sí (`get_current_user`) | sí |
| AUTHORIZATION_BEFORE_SCAN | sí (`require_permission("documentos", "upload")`) | sí |
| TENANT_SCOPE_BEFORE_SCAN | sí (usuario del tenant del token) | sí |
| COMPANY_SCOPE_BEFORE_SCAN | sí (`get_company_context`) | sí |
| RESOURCE_SCOPE_BEFORE_SCAN | sí (`_get_document`, `_get_type` con `_alcance`) | sí |
| LICENSE_WRITE_BEFORE_SCAN | sí (`require_write_allowed`) | sí |
Ninguna comprobación se apoya en mantener la transacción abierta: con READ COMMITTED cada sentencia ve lo último
confirmado y no hay bloqueos de fila, así que **la transacción retenida no impide que nada cambie durante el análisis**
(D7a, D7b medidos con la conexión retenida).

**TOCTOU existente hoy (independiente de la retención).** Entre la autorización y la persistencia pasan N segundos. Pueden
cambiar el documento (archivado o borrado), el permiso, la licencia y el tipo documental. La persistencia no revalida nada:
- **D7a:** se pierde la actualización del archivado; el documento vuelve a ACTIVE y recibe una versión.
- **D7b:** el borrado concurrente acaba en 500 y deja un binario huérfano.
- El permiso o la licencia revocados durante el análisis no se vuelven a mirar.

**Impacto de liberar la conexión antes del análisis.** TOCTOU_INTRODUCED = **0**: la ventana y su efecto son los mismos,
porque la transacción retenida no protegía nada. OWNERSHIP_MUST_BE_REVALIDATED (para cerrar el TOCTOU existente) = sí, pero
eso es una mejora de contrato, no una condición para liberar la conexión.
