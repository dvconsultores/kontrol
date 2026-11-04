# Plan · GOV-CTL-06 Hallazgos, recomendaciones y planes de acción correctiva (CTL-06, GOV-CTL-008)

## Decisiones de arquitectura

| Id | Decisión | Razón |
|---|---|---|
| AD-CTL06-01 | Servicio `service_hallazgos.py`, esquemas `schemas_hallazgos.py` y router `api_hallazgos.py` bajo `/gobierno/hallazgos`; guardas permiso → empresa → módulo | Patrón de Gobierno (CTL-04, DOC-02) |
| AD-CTL06-02 | Seis tablas (spec §6). Recomendaciones, partidas, avances e historia son de solo inserción, con disparadores en PostgreSQL; hallazgo y acción admiten UPDATE, pero ninguno DELETE | Nada destructivo; el estado avanza por transiciones con historia |
| AD-CTL06-03 | El responsable es una FK a `gov_positions` más una instantánea (código, denominación, unidad, ejercicio) al asignar | OD-CTL06-01; la historia sigue legible aunque el cargo cambie |
| AD-CTL06-04 | La evidencia es documental (Spec 046): `ResourceKind("GovernmentCorrectiveAction")`; `AdjuntosPanel` en la interfaz; `freeze_links` al cerrar | Sin un segundo almacén; con analizador y congelado (patrón DOC-02) |
| AD-CTL06-05 | Maker-checker en el servicio: el verificador no es quien presentó el hallazgo ni autor de un avance | OD-CTL06-02 |
| AD-CTL06-06 | `If-Match` sobre la versión del hallazgo en toda escritura (helper `_version` de `api.py`) | Sin actualizaciones perdidas entre acciones y transiciones del mismo hallazgo |
| AD-CTL06-07 | CTL-04 incorpora el proceso CTL-06 (`owner_spec` `gov-ctl-06`) y rastrea `GovernmentFinding`; la muestra de CTL-04 ofrece «Registrar hallazgo» | Reutilizar CTL-04; la población de auditoría incluye la gestión de hallazgos |

## Decisiones de diseño (de Claude, dentro de las de la dueña)

- **PDD-CTL06-01:** código `HA-<año>-<nnnn>` por empresa y año de Caracas, igual que `MU-` en CTL-04.
- **PDD-CTL06-02:** el plan se congela al registrarlo. Recomendaciones y acciones solo se añaden en ABIERTO.
- **PDD-CTL06-03:** el estado de la acción se deriva del porcentaje del último avance, y el porcentaje no decrece. Llegar al 100 % exige evidencia vinculada.
- **PDD-CTL06-04:** CERRADO es terminal y no se reabre (la IR no lo define). Devolver vuelve de EVIDENCIA_PRESENTADA a EN_REMEDIACION.
- **PDD-CTL06-05:** `:view` y `:manage` son STANDARD y `:verify` es SENSITIVE.
- **PDD-CTL06-06:** el resumen del listado (abiertos, acciones vencidas, pendientes de verificación, cerrados) cubre toda la empresa, con independencia de los filtros. El CSV tiene una fila por acción y respeta los filtros.
- **PDD-CTL06-07:** «vencida» se calcula con la fecha de negocio de Caracas (`hoy_de_negocio`) y no se persiste.

## Puerta de la Constitución

| Compuerta | Valor |
|---|---|
| Rama / remotas / HEAD == origin | develop / 1 / 1 (`8b7675d`) |
| POSTGRESQL_FINAL_TREE_CERTIFIED | ver `evidence/REQUIRED_SUITE_INVENTORY.md` §0 (preflight) |
| REQUIREMENTS · FULL_PROCESS · RESPONSIBLE_SEMANTICS · ORG06_REQUIRED · CTL02_REQUIRED | 1 · 1 · 1 (OD-CTL06-01) · 0 · 0 |
| SOURCE · FINDING · RECOMMENDATION · ACTION_PLAN · STATE_MACHINE · DOCUMENT | 1 · 1 · 1 · 1 · 1 · 1 |
| MENU · SCREEN_MATRIX · FIELD · ROLE · REPORT · AUDIT · OWNER_UAT_SCENARIO | 1 · 1 · 1 · 1 · 1 · 1 · 1 |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 · 0 · 0 · 0 |

**GATE = PASS**, condicionado a la preflight de PostgreSQL: no se aplica código hasta que termine.
