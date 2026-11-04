# CTL-01 · matriz de reutilización de la Spec 045 (motor de aprobaciones y segregación)

La Spec 045 es referencia privada y transversal. CTL-01 **no** la implanta entera.

| Concepto de la Spec 045 | Clasificación | Uso en CTL-01 |
|---|---|---|
| Versionado de políticas (`ApprovalPolicy`, snapshot congelado) | REUSE_PATTERN_ONLY | La regla SoD guarda su versión; el evento de bloqueo registra `regla_version` |
| Catálogo de procesos y documentos | GOVERNMENT_ADAPTATION_REQUIRED | Catálogo propio de Gobierno, cerrado en código, con acción de auditoría por entrada |
| Condiciones (importes, atributos) | NOT_APPLICABLE | La SoD de Gobierno no condiciona por importe |
| Niveles de aprobación | NOT_APPLICABLE | — |
| Solicitudes de aprobación (`ApprovalRequest`, pasos, decisiones) | NOT_APPLICABLE | — |
| Bandeja de aprobaciones | NOT_APPLICABLE / FORBIDDEN_SCOPE_EXPANSION | — |
| Quórum | FORBIDDEN_SCOPE_EXPANSION | — |
| Delegaciones y suplencias | FORBIDDEN_SCOPE_EXPANSION | ORG-04 está bloqueado (N37) |
| Guarda de segregación y autoaprobación (`requires_segregation`, «quien crea no resuelve») | REUSE_PATTERN_ONLY | La misma idea, «el mismo actor no hace B tras A», pero configurable por par de acciones y por objeto, sobre el ledger de auditoría |
| Auditoría de rechazos (REJECTION tras rollback) | REUSE_AS_IS | `record_audit_after_rollback` (OD-AUD-07) |
| Eventos del motor (`ApprovalEvent`) | NOT_APPLICABLE | La evidencia es `AuditEvent` |
| Migraciones de aprobaciones de compras, ventas, inventario y regulatorio | FORBIDDEN_SCOPE_EXPANSION | — |

**Resultado:** SPEC045_WHOLE_ENGINE_REQUIRED = 0. Casi todo el flujo de aprobación es NOT_APPLICABLE.
