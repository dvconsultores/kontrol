# RECONCILIACIÓN GLOBAL — MASTER56 → MASTER57, SPEC057 Y MARCO FISCAL (2026-10-07)

> Ciclo **exclusivamente documental**, de requisitos y planificación. Dueño: **Producto global / roadmap
> maestro**, con la **057** como nueva Master Spec; apoyo fiscal 039–043, 056 y D0-07. Checkpoint
> `5075e12` (`develop` = `origin/develop`, 0 bases de corrida, puertos libres). Único fichero sin
> seguimiento al abrir: `requerimientos/KONTROL_SPEC057_Ingenieria_Requerimientos_Activos_Fijos.pdf`,
> colocado por la dueña: **requisito oficial de producto**, se incorpora al repositorio tal cual.
> Cambios de código, esquema, licenciamiento, autoridad central o fiscal: **0** (verificado en
> `docs/evidence/master-57-reconciliation/validaciones.txt`).

## 1. `/speckit.specify` — requisitos del ciclo

FR-ROADMAP-001..012 (inventario 56 → 57; 057 incorporada como `PLANNED / NOT_STARTED`; PDF con
seguimiento y como fuente funcional; sin iniciar; no absorbida por la 023; dependencias según la
Ingeniería y la arquitectura; posición en el roadmap; MASTER57 en documentos vivos; historia no
reescrita; semántica de `NEXT SPEC = 029` reconciliada) · FR-FISCAL-001..010 (homologación bajo
SNAT/2024/000121 fuera de la planificación si la derogatoria se verifica; verificación documental;
obligaciones vigentes intactas; D0-07 acotada; 039–043 ni bloqueadas por homologación ni cerradas
sin evidencia; 056 redefinida conservando su papel de compuerta; 044 intacta; ruta fiscal
implementación → validación vigente → QA/UAT → liberación) · FR-GLOBAL-001..005 (sin código, sin
esquema, sin reabrir deuda cerrada, sin iniciar 057 ni ninguna implementación).

## 2. `/speckit.clarify` — las 25, resueltas

1–5 ficheros canónicos: `master-56-specs-status.md` (inventario, nombre histórico), `roadmap-by-waves.md`
+ `spec-dependency-graph.md` + `master-backlog.md` + `critical-path-analysis.md` (roadmap),
`next-spec-decision.md`, `D0-blockers.md`, `D0-decision-register.md` · 6 D0-07: «LEGAL_VALIDATION_PENDING
(todos los valores)», rol «especialista en homologación», R-D0-07-5 ligado al «acto formal de la 056»,
OQ-09 «plazo de homologación» · 7–11 039–043: `BLOCKED_BY_LEGAL_VALIDATION` por D0-07 (sin ninguna
referencia que las bloqueara **solo** por homologación; la 042 además sin UI de contingencia) · 12
056: «Homologación fiscal y release», `BLOCKED_BY_LEGAL_VALIDATION`, carpeta `011-homologacion-liberacion`,
módulo `homologation` (3 tablas, 8 rutas, frontend `homologacion`) · 13–14 referencias: inventariadas
y clasificadas en §5 · 15–16 fuente legal: Gaceta íntegra no disponible en el repositorio; verificación
por documentación jurídica fiable (§4) · 17 PDF: leído entero (24 páginas; §6) · 18 shell: la 018
`NOT_STARTED` no tiene carpeta → **no se crea** `specs/057` · 19 dependencias: PDF §28/§33 · 20
posición: tras compras/importaciones/CxP y costos/cierres, antes de reportes/dashboard/integraciones
(PDF §33.2) → OLA 7b · 21 propagación: documentos vivos a 57; históricos intactos · 22–23 puntero: caso
C, obsoleto como «siguiente pendiente» (ver `next-spec-decision.md`) → **`NEXT-SPEC-POINTER-AMBIGUO —
MATERIAL_DECISION_REQUIRED`**, aislado · 24 estimaciones: solo cualitativas (PDF §34: ~cinco ciclos;
ruta crítica sin el riesgo externo de homologación) · 25 frontera: nada en `resources/`, `qa/`,
`Dockerfile*`, `compose*`. `MATERIAL OQ = 0` salvo el puntero, separado como permite el encargo.

## 3. `/speckit.plan`, compuerta, checklist y tareas

W01–W28 ejecutados en este orden: reconciliación y orquestación (`VERIFIED_END_TO_END`, sin delegación:
el ciclo es interpretación de alcance, roadmap y marco legal, `CLAUDE_ONLY`; `DEEPSEEK CALLS = 0`),
localización de inventario, roadmap, next-spec, registros D0, Specs fiscales y 056, inventario de
referencias a homologación (§5), verificación legal (§4), lectura del PDF (§6), convención de carpeta,
dependencias, migración 56 → 57, política de referencias históricas, D0-07, 039–043, 056, 044, ruta
fiscal, puntero, aplicación de cambios, `git add` del PDF, búsqueda de consistencia, prueba de no-código,
`analyze`, trazabilidad y convergencia. **Compuerta G01–G28: PASS** (G10 verificada; G28 con la
excepción aislada del puntero). Tareas T01–T10 (`CLAUDE_ONLY` todas; `LEGAL_SENSITIVE` T06–T09):
inventario, PDF, legal, master 57, roadmap, D0-07, 039–043/056/044, puntero, evidencia, Git.

## 4. Compuerta de verificación legal

`LEGAL_REFERENCE` SNAT/2026/00084 · `OFFICIAL_GAZETTE` G.O. N.º 43.435 · `DATE` 12-08-2026 ·
`REPEALED_RULE` SNAT/2024/000121 (26-11-2024; G.O. N.º 43.032, 19-12-2024) · `SOURCE` Nota de Actualidad
Corporativa STL de PwC Venezuela (14-08-2026), sumario de la G.O. 43.435 (IUSDATA), Acceso a la
Justicia y resúmenes concordantes · `VERIFIED` **sí**, por documentación jurídica fiable; el texto
íntegro de la Gaceta no está en el repositorio. Detalle y paráfrasis mínima:
`docs/evidence/master-57-reconciliation/referencia-legal.md`. Las fuentes señalan además un vacío
normativo a la espera de nuevos lineamientos: si llega un régimen nuevo, entra en
`authority-matrix.md` como norma vigente, no como reaparición de la 121.

## 5. Inventario y clasificación de referencias

| Referencia | Clasificación | Acción |
|---|---|---|
| `master-56-specs-status.md` (título, recuento, filas 039–043 y 056) | CURRENT · NEEDS_UPDATE | Título MASTER 57 con nota; fila 057; 039–043 «D0-07 (reglas), sin dependencia de homologación»; 056 redefinida; recuento 57 (nombre del fichero conservado por las referencias existentes) |
| `spec-equivalence-map.md`, `spec-dependency-graph.md`, `roadmap-by-waves.md`, `master-backlog.md`, `critical-path-analysis.md`, `source-inventory.md`, `requirements-to-specs-map.md` | CURRENT · NEEDS_UPDATE | 057 incorporada; 056 renombrada; B-073 reescrito, B-094 nuevo; OLA 7b; OLA 9 «liberación»; nota de ruta crítica; PDF registrado como fuente 19 |
| `56-specs-gap-analysis.md` | HISTORICAL (auditoría 2026-08-29) + fuente de numeración | Adenda fechada con la fila 057; sin reescribir la medición |
| `master-56-convergence.md`, `master-56-traceability.md`, `operational-chain-*.md`, deltas de licenciamiento («MASTER56: 56 filas») | HISTORICAL | Sin cambio: describen fielmente su momento |
| `ADR-D0-007`, `D0-final-resolution.md` (D0-07, OQ-09), `D0-open-questions.md` (OQ-09), `D0-blockers.md` (BLK-D0-02), `D0-fiscal-validation-matrix.md` (roles), `POL-D0-006` | CURRENT · NEEDS_UPDATE | Homologación retirada como bloqueo (`HOMOLOGATION_REQUIREMENT_REMOVED`); D0-07 `NARROWED`; reglas y obligaciones intactas; rol «especialista fiscal (facturación)» |
| `authority-matrix.md` (fila 000121) | CURRENT · OBSOLETE | Marcada `DEROGADA`; fila nueva para la 00084 |
| `document-conflicts.md` CON-10 | CURRENT · NEEDS_UPDATE | Nota de derogatoria |
| `specs/011-homologacion-liberacion/spec.md` | CURRENT · NEEDS_UPDATE | Nombre nuevo y bloque «Actualización de alcance 2026-10-07»; el cuerpo de 2026-08-04 no se reescribe |
| `specs/001-fundacion/research.md` (fila Homologación) | CURRENT · OBSOLETE | `DEROGADA (2026-08-12)`; FR-001-071 (auditoría inmutable) sigue vigente por principio propio |
| `G0-final-resolution.md`, `D0-impact-matrix.md`, `KONTROL_ARCHITECTURE_BASELINE.md` (prohibición de declarar homologación), `specs/007-nucleo-fiscal/*` (CL-007-05, AC-007-060), `auditoria-001-011.md`, `spec-equivalence-map` fila `011-homologacion-liberacion`, `code-to-specs-map.md`, `screens-to-specs-map.md`, `docs/seniat/*` (expediente preparado para el trámite de la 121), `docs/manual-usuario` §13 | HISTORICAL o STILL_VALID | Sin cambio: la prohibición de declarar homologación sigue (más estricta aún); los nombres de carpeta, módulo, migración `0011_homologacion` y pantallas se mantienen hasta que la 056 ejecute su ciclo; el expediente SENIAT queda como evidencia histórica |
| `docs/roadmap/046-*.md` | HISTORICAL | Sin cambio |
| Código y frontend | — | 0 referencias a homologación como requisito en `resources/`; el módulo `homologation` no se toca |

## 6. SPEC057 — lo que dice la fuente (leída entera)

`KONTROL_SPEC057_Ingenieria_Requerimientos_Activos_Fijos.pdf`, v1.0, 24 páginas, «Documento funcional y
técnico de alcance empresarial»; estado declarado `PLANNED / NOT STARTED`, `NEW PRODUCT SCOPE`, «Master
global: MASTER57 = 57 Specs». Owner funcional: Administración / Finanzas / Contabilidad. Secciones
1–35 + anexos A (matriz RF) y B (glosario). Requisitos: **RF-AF-001..202** (maestros y políticas
versionadas; alta y origen; capitalización, fecha disponible para uso, costo inicial multimoneda,
activo en construcción, capitalización parcial; componentización; ubicación, custodia, historial,
etiquetado; estados y ciclo de vida; libros contable/fiscal independientes, corridas simuladas →
revisadas → aprobadas → ejecutadas → cerradas, inmutabilidad, cambios de estimación, prorrateo,
unidades de producción, cierre de libro; mejoras; revaluación; deterioro sin automatización
especulativa; transferencias internas, entre empresas y masivas; inventario físico con universo
congelado y conciliación aprobada; desincorporación sin borrado; documentos (046), garantías,
seguros, alertas (047); mantenimiento mínimo (no CMMS); eventos financieros idempotentes y
desacoplados; cierres coordinados con 043; permisos `fixed_asset:*` y SoD con 003/045),
**RN-AF-001..006** (multiempresa: `RequestContext` canónico, sin fuga cross-company, transferencias
entre empresas como proceso), **AF-INV-01..24** (invariantes: un desincorporado no se deprecia, una
depreciación definitiva no se edita, Decimal nunca float, libros independientes, moneda/tasa
congeladas…), **RNF-AF-001..018** (Decimal, UUID, America/Caracas, PostgreSQL autoritativo,
paginación server-side, DataTables sin scroll horizontal, páginas no modales, estados de UI, WCAG 2.2
AA, idempotencia, lotes, observabilidad, pruebas unitarias + PG + E2E + mutaciones). Modelo lógico
preliminar de 26 entidades (§27) a resolver en `data-model.md`. Integraciones (§28): 003, 006, 007, 008,
009, 010, 013, 015–017, 018, 019, 026, 027, 043, 045, 046, 047, 048, 049, 050, 051, 052, 053, 054, 055; **regla
de ownership: la 023 no es dueña**. Marco contable (§32): VEN-NIF, NIC 16, NIC 36; sin porcentajes
fiscales en código. Dependencias antes de iniciar (§33.1): 007, 009, 013, 017, 019, 026, 027, 045, 046 y,
a ser posible, 018. Estrategia (§34): una Master Spec en ~cinco ciclos AF-1..AF-5 (18–27 días
laborables orientativos; la estimación global del proyecto se recalcula al iniciar). Criterio de
cierre (§35). Exclusiones v1 (§31): CMMS avanzado, IoT, GPS, combustible, flotas, mantenimiento
predictivo, leasing e IFRS 16 completos, inmobiliaria, CAPEX completo, módulo asegurador, tasación
automática. Nada del PDF se reescribe: el repositorio lo enlaza.

## 7. Veredicto, validaciones y trazabilidad

`GLOBAL ROADMAP RECONCILIATION — CLOSED / CONVERGED` · `MASTER57 — ACTIVE` · `SPEC057 — PLANNED / NOT
STARTED` · `FISCAL HOMOLOGATION ASSUMPTION — RECONCILED` · `D0-07 — LEGAL_VALIDATION_PENDING / NARROWED`
· **aparte:** `NEXT-SPEC-POINTER-AMBIGUO — MATERIAL_DECISION_REQUIRED` (no impide el cierre: MASTER57 y
057 quedan correctamente incorporadas).

Validaciones (`docs/evidence/master-57-reconciliation/validaciones.txt`): VAL-01 57 filas · VAL-02 la
057 una vez · VAL-03 `PLANNED / NOT_STARTED` · VAL-04 PDF con seguimiento · VAL-05 referenciado desde
inventario, equivalencias, brechas, olas, grafo, fuentes, requisitos y backlog · VAL-06/07/08 0 ficheros
de activos fijos, 0 migraciones, 0 cambios de código · VAL-09 documentos vivos sin «total 56» · VAL-10
históricos intactos · VAL-11 sin homologación como requisito vigente · VAL-12 D0-07 conserva las 24
reglas · VAL-13 039–043 siguen `BLOCKED_BY_LEGAL_VALIDATION` · VAL-14 056 redefinida · VAL-15 044 sin
cambio · VAL-16/17/18 licenciamiento, backend y frontend sin cambio. `E2E_GLOBAL =
NOT_REQUIRED_FOR_DOCUMENTATION_ONLY_DELTA` (ningún fichero de `resources/`, `qa/` ni de despliegue cambia;
las suites se corrieron íntegras en `5075e12`).

`analyze` final: `CANONICAL_MASTER_COUNT_MISMATCH = 0` · `SPEC057_MISSING = 0` · `SPEC057_DUPLICATE = 0` ·
`SPEC057_IMPLEMENTED_ACCIDENTALLY = 0` · `SPEC057_WRONG_OWNER = 0` · `PDF_UNTRACKED = 0` ·
`CURRENT_MASTER56_REFERENCE = 0` · `HOMOLOGATION_121_ACTIVE_REQUIREMENT = 0` ·
`D0_07_HOMOLOGATION_ONLY_BLOCKER = 0` · `SPEC056_OBSOLETE_HOMOLOGATION_SCOPE = 0` ·
`FISCAL_OBLIGATIONS_REMOVED = 0` · `FALSE_FISCAL_CLOSURE = 0` · `SPEC044_UNJUSTIFIED_CHANGE = 0` ·
`PRODUCT_CODE_CHANGE = 0` · `PRODUCT_SCHEMA_CHANGE = 0` · `LICENSING_REGRESSION = 0` · `SECRET_EXPOSURE = 0`
· `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0` · huérfanos 0 · `UNKNOWN = 0` ·
trazabilidad 100 %: decisión Activos Fijos → PDF → fila 057 → MASTER57 → roadmap (OLA 7b, grafo,
backlog, fuentes, requisitos) → `PLANNED`; derogatoria → referencia verificada → D0-07 → 039–043 → 056 →
ruta fiscal.
