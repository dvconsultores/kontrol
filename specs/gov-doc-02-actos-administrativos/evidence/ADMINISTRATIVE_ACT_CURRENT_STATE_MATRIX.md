# ADMINISTRATIVE_ACT_CURRENT_STATE_MATRIX (2026-11-01, HEAD `f462cc3`)

| SURFACE | MODULE | BUSINESS_PURPOSE | CURRENT_STORAGE | CURRENT_METADATA | DOCUMENT_TYPE | AUTHORITY_MODEL | MOTIVATION_MODEL | EFFECTIVE_DATE | NOTIFICATION | VERSIONING | AUDIT | CANONICAL_OR_AD_HOC | REUSE | MIGRATION_REQUIRED |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Acto de creación del ente | ORG-01 (`gov_entities`) | Soporte para activar el ente | columnas `acto_tipo` (LEY/DECRETO/ORDENANZA/RESOLUCION/OTRO), `acto_numero`, `acto_fecha`, `acto_publicacion` + `DocumentLink(GovernmentEntity)` | tipo, número, fecha, publicación | el que elija el usuario | ninguno | ninguno | ninguna | ninguna | `gov_entity_versions` | GOV_ENTITY_* | AD_HOC (metadatos propios del ente) | no (no se reinterpreta) | NO (fuera de alcance; posible enlace futuro) |
| Acto que aprueba la estructura | ORG-02 (`gov_structures`) | Soporte para poner en vigor la estructura | `DocumentLink(GovernmentStructure)` | ninguno estructurado | el que elija el usuario | ninguno | ninguno | ninguna | ninguna | versiones de unidad | GOV_STRUCTURE_* | AD_HOC (solo PDF) | no | NO |
| Acto del cargo | ORG-03 (`gov_positions`) | Soporte de competencias y límites | `DocumentLink(GovernmentPosition)` | ninguno estructurado | el que elija el usuario | el cargo (ORG-03) | ninguno | ninguna | ninguna | `gov_position_versions` | GOV_POSITION_* | AD_HOC (solo PDF) | sí: el cargo y sus competencias son la autoridad de DOC-02 | NO |
| Gestión documental | Spec 046 (`documents`, `document_links`) | Almacenar, analizar, versionar y vincular evidencia | tablas del núcleo | tipo documental, versión, hash, análisis, vínculo con `role` y congelado | catálogo por empresa | permiso sobre el recurso de destino | — | — | — | versiones de documento; `freeze_links` | DOCUMENT_* | CANONICAL (técnico) | sí: es la evidencia del acto | NO |
| Equivalentes de Empresarial | — | — | ninguno con semántica de acto administrativo | — | — | — | — | — | — | — | — | — | no | — |

Conclusión: hoy ningún acto de Gobierno es un objeto de dominio; los tres usos son adjuntos o metadatos ad hoc. DOC-02 crea el objeto
sin tocar esos usos (spec §4.8).
