# SCOPE_ERROR_MATRIX — ciclo 07

Semántica de error por clase de operación y caso hostil. Se preservan los contratos certificados (OD-ISO-04); no hay reescritura global. Solo los GAP de §1.1 adoptan una respuesta nueva, que es la del objeto relacionado, idéntica a la de inexistente.

## Casos

| Caso | Significado |
|---|---|
| FOREIGN_TENANT | El recurso o la empresa es de otro tenant |
| INACCESSIBLE_COMPANY | Empresa del mismo tenant sin acceso (sin `UserScope`) |
| NO_CAPABILITY | El actor no tiene la capacidad en ninguna empresa |
| CAPABILITY_OTHER_COMPANY | Accede a la empresa activa, pero la capacidad la tiene en otra |
| DIRECT_FOREIGN_OBJECT_ID | Id de un objeto de otra empresa (mismo u otro tenant) en la ruta o en el cuerpo |

## Matriz

| Clase de operación | FOREIGN_TENANT | INACCESSIBLE_COMPANY | NO_CAPABILITY | CAPABILITY_OTHER_COMPANY | DIRECT_FOREIGN_OBJECT_ID |
|---|---|---|---|---|---|
| Cabecera `X-Kontrol-Company` | 404 `COMPANY_NOT_FOUND` | 404 `COMPANY_NOT_FOUND` | — | 403 `COMPANY_SCOPE_FORBIDDEN` (auditado `COMPANY_SCOPE_DENIED`) | — |
| Lista, búsqueda y recuento de empresa | sin filas ajenas; `total` propio | idem | 403 `PERMISSION_DENIED` | 403 `COMPANY_SCOPE_FORBIDDEN` | — |
| Detalle, PATCH, DELETE y acción con id en la ruta | 404 del recurso | 404 del recurso | 403 `PERMISSION_DENIED` | 403 `COMPANY_SCOPE_FORBIDDEN` | 404 del recurso, idéntico a inexistente (ADR-D0-014) |
| Id relacionado en el cuerpo (GAP corregidos) | 404 del objeto relacionado | idem | 403 `PERMISSION_DENIED` | 403 `COMPANY_SCOPE_FORBIDDEN` | 404 del objeto relacionado, idéntico a inexistente |
| Id relacionado: regla de notificaciones (contrato vigente) | 422 `NOTIFICATION_RULE_INVALID` (motivo `ROLE_NOT_FOUND`) | idem | 403 | 403 | idéntico a inexistente |
| Escritura global desde empresa (OD-ISO-10) | — | — | 403 `PERMISSION_DENIED` | — | 403 `GLOBAL_SCOPE_FORBIDDEN` |
| Descarga o vista previa de documento | 404 `DOCUMENT_NOT_FOUND`/versión | 404 | 403 | 403 | 404 |
| Descarga de exportación | 404 `EXPORT_NOT_FOUND` | 404 | 403 (capacidad de origen) | 403 | 404 |
| Bitácora de auditoría | sin eventos ajenos; `total` propio (ciclo 04) | sin eventos de empresas no auditables | 403 | sin eventos de esa empresa | — |
| Usuarios y roles (tenant) | 404 `USER_NOT_FOUND`/`ROLE_NOT_FOUND` | — | 403 | — | 404 (OD-ISO-11; rol de otro tenant = inexistente) |
| Sesión propia (`DELETE /auth/sessions/{id}`) | 404 `SESSION_NOT_FOUND` (G-SES-01; antes 403) | — | — | — | 404 |
| Nodo de estructura de almacén en la cadena | 404 `<NIVEL>_NOT_FOUND` (G-WH-01; antes 422) | 404 | — | — | dentro de la misma empresa y otro almacén: 422 `HIERARCHY_CROSS_WAREHOUSE` (se conserva) |
| Rutas de instalación (licencia, fiscal, homologación) | no aplica: instalación por diseño | — | 403 | — | — |
| Paso de aprobación | elegibilidad congelada (N10): no decide | — | 403 | — | no decide |

Reglas comunes:
- ningún mensaje de error lleva datos del recurso ajeno (código, nombre, importe ni existencia);
- el 404 de no enumeración no se audita (ciclo 04);
- el 403 de alcance sí: `COMPANY_SCOPE_DENIED`.

`SCOPE_ERROR_CONTRACT_RECONCILED = 1`.
