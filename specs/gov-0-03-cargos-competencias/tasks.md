# Tareas · GOV-0-03 Cargos con competencias y límites de firma/aprobación

Todo el código lo escribe DeepSeek con un encargo de Claude; Claude audita, aplica, prueba y certifica. `RETRY_MAX: 2`. `EGRESS_SAFE`: sí (datos sintéticos; contraseñas solo de la constante del mundo de pruebas). Montos: fórmula, escala (`Numeric(18,2)`), redondeo (ninguno: se rechaza) y vectores los fija Claude en el encargo.

## Phase 0: Gobierno del repositorio y deudas documentales (Claude)

- [x] T000 Rama única: reconciliar `develop`/`feature/001-fundacion` (ancestro, 0 commits propios), rama por defecto `develop`, eliminar la rama remota, `git-governance.md` §0, `.claude/CLAUDE.md`, `ai-orchestration-policy.md` · CLAUDE · n-a
- [x] T000b LOAFSP: dejar de atribuir el año calendario a un artículo no verificado (spec de ORG-02 y matrices): la regla queda bajo OD-ORG02-01 y N03 sin número de artículo · CLAUDE · n-a
- [x] T000c Errata del commit `e993792` (vitest +43; real +36) documentada en la evidencia de ORG-02, sin reescribir historia · CLAUDE · n-a

## Phase 1: Corte vertical

- [x] T001 [RED] Suite `tests/test_gov0_cargos.py` (GC-01..): ciclo del cargo, campos, unidad de la misma estructura, competencias, límite (vectores de §5), duplicados, faltantes, acto, motivo, campos bloqueados, autoridad `publish` en VIGENTE, última competencia, desactivación, eliminación, historial, `If-Match`, CSV, auditoría, permisos, módulo, aislamiento, interacción con ORG-02 (copia, unidad con cargos) · EXECUTOR DEEPSEEK · MODEL pro · SECURITY_SENSITIVE sí · FILES `tests/test_gov0_cargos.py` · DONE_WHEN falla en rojo sin el código
- [x] T002 Modelos y migración 0065 (`GovernmentPosition`, `GovernmentPositionCompetency`, `GovernmentPositionVersion`; FK compuestas; CHECKs; concesión a FUNCIONAL_COMPLETO) · DEEPSEEK · pro · FILES `models.py`, `alembic/versions/0065_gov0_cargos.py` · TEST cabeza única y ciclo de migración en PG
- [x] T003a Esquemas `schemas_cargos.py` · DEEPSEEK · pro
- [x] T003b Servicio del cargo `service_cargos.py` (listar, crear, obtener, modificar, eliminar, activar, desactivar, versiones, exportar) · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T003c Servicio de competencias (agregar, cambiar, retirar; autoridad `publish`; última competencia) · DEEPSEEK · pro · SECURITY_SENSITIVE sí
- [x] T003d ORG-02: copia de cargos al abrir con copia; `GOV_UNIT_HAS_POSITIONS` al desactivar y eliminar unidad · DEEPSEEK · pro · TEST `test_gov0_estructura.py` + GC de interacción
- [x] T004 API `api_cargos.py` y registros (router en `main.py`, permisos, `ResourceKind`, 9 acciones de auditoría + espejo, MFA) · DEEPSEEK · pro/flash
- [x] T005 Guardas y contratos (cabeza 0065, catálogo de auditoría, N9 + semilla, MFA, barridos, techo de delegación, permisos de instalación) + fixtures del frontend (herramienta) · DEEPSEEK + herramienta
- [x] T006a Frontend: contrato (`api.ts`), rutas, `pantallas.ts`, menú · DEEPSEEK · pro
- [x] T006b Páginas de ejercicios y de cargos del ejercicio · DEEPSEEK · pro
- [x] T006c Formularios: cargo, competencia, desactivación · DEEPSEEK · pro
- [x] T006d Página del cargo (competencias, acto, historial, acciones) · DEEPSEEK · pro
- [x] T007 Pruebas de frontend (vitest): menú, estados, acciones por estado y capacidad, formularios, límite, errores · DEEPSEEK · pro
- [x] T008 E2E `e2e/gobierno-cargos.spec.ts` (login → menú → proceso completo; preparador sin `publish`; consulta; otro ente; validaciones; axe 1280/768/320) + regresión ORG-01/02 · DEEPSEEK · pro
- [x] T009 Mutaciones de negocio (herramienta de Claude) · CLAUDE · n-a
- [x] T010 Certificación: suites PG/SQLite, frontend, E2E ×3 navegadores y canónica, base tras la E2E, OpenAPI, residuos, ficha, tarjeta UAT, métricas · CLAUDE · n-a

## Phase 2: Correcciones de la ejecución (ciclo GOV-0-FUNCTIONAL-03)

Cada una con su encargo autocontenido, auditoría de Claude y prueba mínima tras aplicar. Reintentos por subtarea: máximo 2.

- [x] T001a/T001b Suite partida en dos encargos; D1 (`DocumentType` sin `title`, error del encargo de Claude) corregido dentro de T001b · DEEPSEEK · pro · T001b-r1: login del caso de otro tenant y orden de rutas de GC-24
- [x] T001c GC-27: cargo en unidad inactiva (mata el mutante OC25) · DEEPSEEK · flash · 0 reintentos
- [x] T002b FK simple `position_id → gov_positions.id`: la FK compuesta violaba la guarda `test_company_id_always_references_company` (hallado por la suite completa de PostgreSQL) · DEEPSEEK · flash · 0 reintentos
- [x] T003a-r1 Alias de dinero con `cast` y `TYPE_CHECKING` (5 errores nuevos de mypy) · DEEPSEEK · flash; orden de importaciones con `ruff --fix` I001 (excepción de formato registrada, error del encargo de Claude)
- [x] T003b-r1 dentro de T003c: `inicio/fin` usados antes de definirse, importación sin uso, tipo de `unidad` · DEEPSEEK · pro
- [x] T003d Copia de cargos y `GOV_UNIT_HAS_POSITIONS` en ORG-02 · DEEPSEEK · pro · 0 reintentos
- [x] T006b-r1 `caption` inexistente en DataTable y hook condicional · T006c1-r1 cambios de código y vigencia en borrador · T006c2-r1 (en T006d) variable sin uso · T006d-r1 hook condicional, fecha civil de fin en el aviso de inactivo, `useNavigate` tras eliminar · DEEPSEEK · flash
- [x] T006h Accesibilidad hallada por la E2E real: regiones desplazables enfocables con nombre en la página del cargo (axe `scrollable-region-focusable` a 768 px) · DEEPSEEK · flash · 0 reintentos
- [x] T007a/b/c Pruebas de frontend partidas en tres encargos; r1 de cada una (simulacros con la forma real de los datos, textos repetidos en opciones, rótulos reales); T007b-r2 fila de estado por celda · DEEPSEEK
- [x] T008-r1 y r2 (rótulos, id en la URL, alta desde la página del ejercicio, duplicado frenado por el formulario, variables sin uso) · T008b selectores de fila por celda · T008c espera del PATCH (hallados por la E2E real) · DEEPSEEK · flash
- [x] T009 Mutaciones: 40 (39 KILLED, 1 EQUIVALENT) · CLAUDE · n-a
- [x] T010 Certificación (ver evidence/REQUIRED_SUITE_INVENTORY.md) · CLAUDE · n-a
