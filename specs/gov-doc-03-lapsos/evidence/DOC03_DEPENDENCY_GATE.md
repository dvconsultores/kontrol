# DOC-03 · dependency gate

Encargo CTL10-EVIDENCE-FINAL + DOC03-DEPENDENCY-GATE-01. Base: `f48e98b`.

## DOC-01: expediente

¿Puede DOC-03 modelar completamente sus lapsos sobre un objeto existente y jurídicamente suficiente? **No.**

Objetos existentes: acto (DOC-02), notificación (DOC-04), hallazgo, programa, cuenta. Ninguno es una solicitud ni un procedimiento.

| Lapso | Sobre qué corre | ¿Existe? |
|---|---|---|
| Subsanación, art. 50 | Escrito o solicitud | No |
| Tramitación y prórroga, arts. 60-61 | Expediente, desde el recibo de la solicitud | No |
| Perención, art. 64 | Procedimiento a instancia de parte | No |
| Petición, art. 5 | Solicitud presentada | No |
| Recursos, arts. 91-99 | Acto notificado, y recurso interpuesto | Parcial: acto y notificación sí; recurso no |

Modelar solo los recursos sería un producto reducido. Crear ahí la solicitud o el procedimiento sería un pseudo-expediente, y el art. 51 asigna esa tramitación al expediente, que es GOV-DOC-001.

DOC01_DEPENDENCY_REQUIRED = 1 · DOC01_DEPENDENCY_SATISFIED = 0: DOC-01 sigue BLOCKED por LEGAL_VALIDATION_REQUIRED N40.

## DIG-02: subsanación digital

Frontera:

| DOC03_OWNS | DIG02_OWNS |
|---|---|
| Regla temporal versionada | Solicitud o trámite digital |
| Cómputo y vencimiento | Interacción del interesado |
| Prórroga, y suspensión si hay base expresa | Presentación de la subsanación |
| Historia auditable | Seguimiento visible por el interesado |

El registro interno de una solicitud pertenece al expediente: arts. 44-46 y 51, y GOV-DOC-001. DOC-03 no necesita el canal digital.

DIG02_DEPENDENCY_REQUIRED = 0 · CROSS_VERTICAL_DUPLICATION = 0. E2E-05 sí depende de DIG-02 y DIG-03: E2E05_FULL_PROCESS = BLOCKED.

## ORG-06: persona

La prórroga exige constancia de causa y autoridad, y el cargo de ORG-03 con su competencia cubre esa autoridad. Ninguno de los artículos revisados exige identidad personal más allá del usuario auditado.

ORG06_DEPENDENCY_REQUIRED = 0.

## Calendario

OFFICIAL_CALENDAR_REQUIRED = 1 (art. 42).

| Campo | Estado |
|---|---|
| OFFICIAL_CALENDAR_SOURCE_AVAILABLE | 0: ninguna fuente en la biblioteca normativa ni en el repositorio |
| OFFICIAL_CALENDAR_MODEL_AVAILABLE | 0: solo existe la zona America/Caracas |
| OFFICIAL_CALENDAR_OWNER_AVAILABLE | 0: ningún rol existente lo mantiene |
| CALENDAR_SOURCE | Por identificar: cada versión debe citar instrumento oficial |
| CALENDAR_VERSIONING | Dato institucional versionado y auditable |
| CALENDAR_MAINTAINER_ROLE | OWNER_DECISION_REQUIRED |
| CALENDAR_EFFECTIVE_FROM · TO | Por versión |

No se cargó ninguna fecha. OFFICIAL_CALENDAR_DESIGN_VALID = 1 como diseño; sin fuente ni responsable no es implementable.

## Regla versionada

Configuración tipada, sin motor: tipo de lapso, fundamento, unidad (día hábil, mes, año), duración, hito inicial, permite prórroga y su máximo, versión de calendario, vigencia, estado; inmutable tras usarse. Suspensión solo con fundamento expreso. GENERIC_RULE_ENGINE_REQUIRED = 0.

## Resultado

| Condición | Valor |
|---|---|
| NORMATIVE_RULESET_FROZEN | 0 |
| DOC-01 | Requerido y no satisfecho |
| DIG-02 | No requerido |
| ORG-06 | No requerido |
| OFFICIAL_CALENDAR_DESIGN_VALID | 1 |
| MATERIAL_OWNER_DECISIONS_PENDING | 1: responsable del calendario |
| SHARED_CORE_CHANGE_REQUIRED | 0 |

**DOC03_FULL_PROCESS_IMPLEMENTABLE = 0.** No se escribió producto reducido. ROUTING_DECISION = RUTA_B.

## Para desbloquear

1. Resolver LEGAL_VALIDATION_REQUIRED N40 de DOC-01, o acotar qué parte de DOC-01 lo necesita, e implementar DOC-01.
2. Identificar la fuente oficial del calendario y su responsable.
3. Archivar la copia oficial de G.O. 7.018 y verificar medidas del art. 6.
