# Plan · GOV-CTL-04 Consulta y muestreo read-only del auditor (+ FIND-ORG07-01)

## Decisiones de arquitectura

| Id | Decisión | Razón |
|---|---|---|
| AD-CTL04-01 | Proyección sobre `audit_events` y el catálogo cerrado: alcance de Gobierno por `owner_module == "government"`; nada de una segunda bitácora | Reutilizar el núcleo; clasificación por catálogo, no por cadenas |
| AD-CTL04-02 | Servicio `service_auditoria.py` + router `api_auditoria.py` bajo `/gobierno/auditoria`; guardas permiso → empresa → módulo | Patrón de Gobierno; la empresa activa es el ente |
| AD-CTL04-03 | Muestra en dos tablas de solo inserción con disparadores de inmutabilidad en PostgreSQL (mismo patrón que `audit_events`) | OD-CTL04-02; ninguna API de cambio o borrado |
| AD-CTL04-04 | Aleatoria con `random.Random(semilla).sample` sobre la población ordenada (`event_time`, `id`); semilla y población guardadas | Reproducibilidad verificable sin métodos estadísticos impuestos |
| AD-CTL04-05 | Rastreo y enlaces de documentos calculados en el backend; la interfaz los pinta solo con la capacidad del destino | El backend es dueño del alcance; nada de enlaces rotos |
| AD-CTL04-06 | `audit:view` y `gobierno_auditoria` son independientes | OD-CTL04-03; no amplía la bitácora privada |
| AD-ORG07-09 | `competencias_en_vigor(db, cargo, fecha)` pública en `service_autoridad.py`, usada por ORG-07 y DOC-02 | Una sola verdad de autoridad histórica (FIND-ORG07-01) |

## Decisiones de diseño (de Claude, dentro de las de la dueña)

- PDD-CTL04-01: código de muestra `MU-<año>-<n.º correlativo de 4 cifras por empresa y año>`, asignado al registrar.
- PDD-CTL04-02: el filtro `usuario` es el nombre de usuario exacto dentro del tenant.
- PDD-CTL04-03: los límites de 2000 partidas (TODAS) y 500 (ESPECIFICA y ALEATORIA) acotan la carga; superarlos pide acotar la población.
- PDD-CTL04-04: el CSV lleva primero unas líneas de definición (`#` clave: valor) y después la tabla de partidas.

## Puerta de la Constitución

| Compuerta | Valor |
|---|---|
| Rama / remotas / HEAD == origin | develop / 1 / 1 (`4d4f76c`) |
| REQUIREMENTS · FULL_PROCESS · EVENT_SCOPE · SAMPLING · ROLE · READ_ONLY · EVIDENCE | 1 · 1 · 1 · 1 · 1 · 1 · 1 |
| MENU · SCREEN_MATRIX · API · SECURITY · REPORT · OWNER_UAT_SCENARIO | 1 · 1 · 1 · 1 · 1 · 1 |
| MATERIAL_BLOCKER · MATERIAL_OQ · UNKNOWN · CONTRADICTIONS | 0 · 0 · 0 · 0 |

**GATE = PASS.**
