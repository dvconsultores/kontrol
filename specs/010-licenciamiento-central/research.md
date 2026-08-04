# INVESTIGACIÓN — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/010-licenciamiento-central/research.md` |

## 1. Referencias normativas / fuentes

| Fuente | Contenido relevante | Impacto en 010 |
|---|---|---|
| DOC-01 §4 | Administrador de plataforma: tenant, licencias, soporte, operación técnica | Configuración central y renombramiento de módulos |
| DOC-01 §5 | Reglas de negocio, denegación por defecto | Entitlements por módulo |
| DOC-03 §12 | Reglas de datos (decimales, índices, integridad) | FR-010-100 |
| DOC-08 | UI/UX | FR-010-101 |
| Módulo licensing (001) | LicenseState, LicenseArtifact, LicenseEvent, LicenseRenewalRequest, Installation; service: get_or_create_installation, import_license, get_status, current_mode, create_renewal_request, get_history | Base a extender (CL-010-01) |
| Módulos 002-009 | Cada uno define su alcance de negocio | Matriz de entitlements |

## 2. Términos clave

- **Licenciamiento central**: sincronización de licencias/entitlements contra un servidor central.
- **Entitlement**: derecho a usar un módulo.
- **Reloj confiable / `last_reliable_date`**: última fecha verificada contra el central; base de la gracia offline.
- **Contrato v1**: interfaz HTTP del servidor central (ver contracts/api-contracts.md).

## 3. Reutilización y no-redefinición

010 reutiliza las entidades y el servicio de licensing de 001. No reimplementa. Solo añade configuración central, sincronización, entitlements y renovación central.

## 4. Conclusiones preliminares

- No hay bloqueos funcionales; CL-010-09/CL-010-10 quedan registrados como pendientes de decisión operativa.
- La implementación requiere 001 certificada y 002-009 implementados (ya cumplido).
