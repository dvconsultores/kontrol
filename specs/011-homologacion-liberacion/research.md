# INVESTIGACIÓN — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/011-homologacion-liberacion/research.md` |

## 1. Referencias normativas / fuentes

| Fuente | Contenido relevante | Impacto en 011 |
|---|---|---|
| DOC-01 §5 | "No declarar que Kontrol está homologado sin acto formal y versión fiscal aprobada" | FR-011-005 |
| DOC-01 §8 (Homologación) | Versión fiscal identificada, registros de eventos, integridad, trazabilidad, conservación y proceso formal | FR-011-001..004 |
| DOC-01 §10 | "La situación de homologación y modalidad fiscal se documenta antes de producción"; bloqueo si falta documento obligatorio | FR-011-010..013 |
| DOC-01 §13 | Timeline/auditoría | FR-011-020 |
| DOC-03 §12/§13 | Reglas de datos y máquinas de estado | FR-011-100 |
| DOC-08 | UI/UX | FR-011-021 |
| Módulo licensing (001) | `Installation`, `current_mode`, `ensure_write_allowed` | Gate de liberación (FULL_ACCESS) |

## 2. Términos clave

- **Homologación**: proceso formal que documenta que una versión fiscal cumple los requisitos (acto formal + evidencia).
- **Versión fiscal**: versión identificada del esquema/requisitos fiscales aplicable.
- **Liberación**: proceso de release de una versión del producto a producción con gates.
- **Acto formal**: documento/expediente externo que acredita la homologación.

## 3. Reutilización y no-redefinición

011 reutiliza la identidad de instalación y el modo de licencia de 001. No reimplementa licensing ni regulación; no fabrica actos externos.

## 4. Conclusiones preliminares

- No hay bloqueos funcionales; CL-011-09/CL-011-10 quedan registrados como pendientes de decisión operativa.
- La implementación requiere 001 certificada y 002-010 implementados (ya cumplido).
