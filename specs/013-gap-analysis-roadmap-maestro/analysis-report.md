# /speckit.analyze — INFORME DE CONSISTENCIA — 013

## 1. Consistencia interna de la auditoría

| Verificación | Resultado |
|---|---|
| Suma de estados principales = 56 | ✔ 25 + 20 + 5 + 5 + 1 = 56 |
| Suma de niveles de madurez = 56 | ✔ 5 + 6 + 8 + 12 + 25 = 56 |
| Cada Spec maestra tiene exactamente un estado | ✔ |
| Cada Spec maestra tiene fila en la matriz | ✔ 56 filas |
| Los 16 artefactos obligatorios existen | ✔ |
| Los 9 artefactos de la Spec existen | ✔ |
| Ninguna Spec declarada `COMPLETE_100` sin E2E sobre PG | ✔ (0 declaradas) |
| Ninguna clasificación `FUTURE_SCOPE` usada como excusa de defecto | ✔ (0 usadas) |
| Prohibición de implementar respetada | ✔ Sin cambios en `resources/` |
| `/speckit.implement` no ejecutado | ✔ |

## 2. Conflictos detectados entre documentos del propio proyecto

| # | Conflicto | Autoridad prevalente | Resolución aplicada |
|---|---|---|---|
| C-01 | `AUDITORIA_INTEGRAL_KONTROL.md` §1-2 dice bundle 375 KB y 0 Float; §3-5 dicen 694 KB y 18 Float | Código | Se toma el código: 375 KB, 0 Float. Documento marcado como desfasado |
| C-02 | El mismo reporte declara KAUD-001 `RESUELTO`; el código muestra 7 de 9 módulos instrumentados | Código (jerarquía N7 no justifica contradicción, pero el hecho es verificable) | Hallazgo reabierto como FC-06 |
| C-03 | `012/tasks.md` marca T-12..T-16 pendientes; los commits muestran ejecución | Evidencia de ejecución | Tareas consideradas ejecutadas; documento desfasado |
| C-04 | `012/requirements-coverage.md` declara Seguridad `BROKEN` | Código | Superado: Usuarios y Roles existen desde `d7f0bca` |
| C-05 | README declara «Iniciativa actual: 001-fundacion», rama `feature/001-fundacion` | Git | Se trabaja en `develop` con 12 Specs |
| C-06 | Constitución P14 prohíbe `latest`; `compose.yaml` lo usa como default | **Constitución (Nivel 2)** | Registrado como deuda DT-10 |
| C-07 | Constitución P8 prohíbe hardcodear reglas; precios y descuentos son texto libre | **Constitución (Nivel 2)** | Registrado como brecha 012 |
| C-08 | DOCX de proceso (2026-08-25) exigen etapas que ninguna Spec recoge | **Vol. 3 / documento maestro (Nivel 3)** | Alcance ampliado: Specs 018, 020, 021, 022, 031, 032, 033 |

## 3. Cobertura del prompt maestro

| Sección del prompt | Cumplida | Artefacto |
|---|---|---|
| §5 Primera actividad sin tocar código | ✔ | `git status` verificado, 3 untracked intactos |
| §6 Lectura completa de requerimientos | ✔ | `source-inventory.md` (18 archivos) |
| §7 Cinco estados fundamentales | ✔ | Columnas de la matriz |
| §8 Catálogo de 56 | ✔ | `56-specs-gap-analysis.md` |
| §9 No renombrar; tabla de equivalencias | ✔ | `spec-equivalence-map.md` |
| §10-11 Estados y puntuación | ✔ | Estado principal + % auxiliar |
| §12 Matriz de 56 filas | ✔ | 56 filas exactas |
| §13-16 Auditoría frontend | ✔ | `screens-to-specs-map.md` |
| §17-19 Backend y OpenAPI | ✔ | `code-to-specs-map.md`, 275 endpoints |
| §20-23 Base de datos y Alembic | ✔ | 144 tablas, head único, sin modificar |
| §24-25 Pruebas y E2E | ✔ | `current-quality-baseline.md` |
| §26 Integraciones | ✔ | `technical-dependencies.md` |
| §27-32 Procesos operativos | ✔ | `processes-to-specs-map.md` (21 procesos) |
| §33-36 Inventario, CxC/CxP, fiscal, licencia | ✔ | Informe maestro §18, §22 |
| §37-40 UI/UX, browsers, seguridad, Docker | ✔ | `current-quality-baseline.md` |
| §41-47 Duplicados, hardcode, huérfanos | ✔ | `code-to-specs-map.md` §Código sin Spec |
| §48-50 Dependencias y prioridad | ✔ | `spec-dependency-graph.md` |
| §51-56 Roadmap y definiciones | ✔ | `roadmap-by-waves.md` |
| §57-59 Salida numérica y TOP 10 | ✔ | Informe maestro §4, §12 |
| §60 Falsas terminaciones | ✔ | `false-completion-findings.md` |
| §61 Riesgos de retrabajo | ✔ | Informe maestro §13 |
| §62-65 Próximas Specs y rebaseline | ✔ | Informe maestro §25, §29 |
| §66-70 Matrices | ✔ | 5 matrices |
| §71-72 Bloqueantes y decisiones | ✔ | Informe maestro §27, §28 |
| §77-79 Calidad, madurez, índice global | ✔ | `current-quality-baseline.md` |
| §86-88 Deuda y backlog | ✔ | 3 artefactos |
| §97 Punto de detención | ✔ | Sin implementación; autorización solicitada |
| §99 Reglas estrictas | ✔ | Ninguna violada |

## 4. Limitaciones declaradas de este análisis

| Limitación | Efecto sobre las conclusiones |
|---|---|
| Sin instancia PostgreSQL | Ningún estado puede elevarse a `COMPLETE_100`; el drift real es desconocido |
| Sin navegadores reales ni dispositivos | Cobertura de 054 clasificada como `SIMULATED_ONLY` donde corresponde |
| Sin equipo fiscal | Todo el bloque 039-043 queda en `LEGAL_VALIDATION_REQUIRED` |
| `procesos.png` no interpretado | Puede contener etapas adicionales no recogidas aquí |
| Vol. 3 (modelo de datos) y Vol. 4 (wireframes) leídos parcialmente | El contraste campo a campo del modelo objetivo queda pendiente |
| Producción no re-verificada | El 502 se reporta como último estado conocido, no como estado actual |

## 5. Veredicto

La auditoría es **internamente consistente** y sus conclusiones son **verificables**: cada
afirmación de este informe apunta a un archivo y una línea, o a un comando ejecutado en esta sesión.

Las tres conclusiones que más cambian la planificación del proyecto son:

1. El alcance real (documentos de proceso de agosto) es **mayor** que el alcance especificado (12 Specs).
2. La deuda funcional está **concentrada en un bloque coherente**, no dispersa.
3. Tres de las deudas estructurales **se encarecen con cada día de operación** y deben tratarse
   por encima de su severidad nominal.
