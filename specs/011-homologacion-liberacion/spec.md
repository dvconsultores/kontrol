# SPEC — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Código | 011-homologacion-liberacion |
| Nombre | Homologación fiscal y liberación de versión: acto formal, versión fiscal, gates de liberación y trazabilidad |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** (licencia/modos, identidad, instalación) + módulos **002-010** implementados. La implementación requiere 001 certificada y autorización expresa |
| Fuente | DOC-01 §5/§8 (Homologación), §10 (requerimientos regulatorios), §13; DOC-03 §13; DOC-04 |
| Ruta | `specs/011-homologacion-liberacion/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **011-homologacion-liberacion**.

---

## 1. Problema

DOC-01 exige (i) **no declarar que KONTROL está homologado sin acto formal y versión fiscal aprobada** (§5, línea 130), (ii) una vista de **Homologación** con "versión fiscal identificada, registros de eventos, integridad, trazabilidad, conservación y proceso formal" (§8, línea 212), y (iii) que **la situación de homologación y modalidad fiscal se documente antes de producción** (§10, línea 271). Hoy no existe un registro formal y auditable del acto de homologación ni un proceso de **liberación de versión** con gates que impida declarar/producir una versión sin la homologación documentada.

## 2. Objetivos

1. **Homologación fiscal**: registrar el acto de homologación de una versión fiscal (modalidad, versión, acto formal, evidencia con hash), con proceso formal y trazabilidad.
2. **Regla de homologación**: el estado "HOMOLOGADO" solo es válido con acto formal + versión fiscal aprobada (denegación por defecto).
3. **Liberación de versión**: gestionar versiones del producto (DRAFT → CANDIDATE → RELEASED / BLOCKED) con changelog y gates.
4. **Gate de producción**: una versión solo se libera si la homologación está documentada (aprobada), los gates pasan y la licencia es válida.
5. **Auditoría**: registros de eventos append-only (integridad, trazabilidad, conservación).
6. **Integración**: reutiliza la identidad de instalación y el modo de licencia de 001.

## 3. Fuera de alcance

- **Fabricar** el acto formal o la aprobación externa: 011 registra la referencia y la evidencia (hash); el acto lo emite el organismo/proceso externo.
- La **liberación de lotes de inventario** (no hay evidencia en DOC; "liberación" aquí = liberación de versión).
- La **contabilidad formal** y la matriz normativa en sí (es entrada, no salida).

## 4. Actores

| Actor | Uso |
|---|---|
| Administrador de plataforma | Configura y libera versiones; opera el proceso de homologación |
| Contador / fiscal | Evalúa y aprueba la homologación de una versión fiscal |
| Auditor | Revisa el timeline de homologación y liberación |
| Equipo de homologación / QA | Registra evidencia y gates |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-011-001 | Como administrador, quiero registrar el acto de homologación de una versión fiscal con su evidencia. |
| US-011-002 | Como fiscal, quiero evaluar y aprobar/rechazar una homologación con acto formal. |
| US-011-003 | Como administrador, quiero crear una versión con changelog y gates y liberarla solo si está lista. |
| US-011-004 | Como auditor, quiero el timeline inmutable de homologación y liberación. |

## 6. Requisitos funcionales

Convención: `FR-011-XXX`. Prioridad P0/P1/P2.

### 6.1 Homologación fiscal

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-011-001 | Registrar acto de homologación en DRAFT (versión fiscal, modalidad, acto formal, evidencia con SHA-256). | DOC-01 §8 | P0 | Administrador |
| FR-011-002 | Someter la homologación (DRAFT → SUBMITTED) con evidencia y versión fiscal identificada. | DOC-01 §8 | P0 | Administrador |
| FR-011-003 | Evaluar: SUBMITTED → APPROVED/REJECTED con acto formal y evaluador (segregación: quien crea no aprueba). | DOC-01 §5 | P0 | Fiscal |
| FR-011-004 | Eventos append-only de homologación (integridad, trazabilidad, conservación). | DOC-01 §8 | P0 | Sistema |
| FR-011-005 | Regla: el estado HOMOLOGADO solo es válido con acto formal + versión fiscal aprobada; sin ello el sistema NO declara homologado. | DOC-01 §5 | P0 | Sistema |

### 6.2 Liberación de versión

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-011-010 | Crear versión de liberación en DRAFT con changelog y gates. | DOC-01 §10 | P0 | Administrador |
| FR-011-011 | Promover a CANDIDATE con los gates verificados. | DOC-01 §10 | P0 | Administrador |
| FR-011-012 | Liberar (CANDIDATE → RELEASED) solo si: homologación documentada y aprobada + gates verdes + licencia válida (FULL_ACCESS); en caso contrario BLOCKED. | DOC-01 §10 | P0 | Sistema |
| FR-011-013 | Registro de liberación (quién/cuándo/versión) y bloqueo de re-liberación de versiones anteriores. | DOC-01 §10 | P0 | Sistema |
| FR-011-020 | Estado/historial consultable de homologación y liberación (timeline). | DOC-01 §13 | P0 | Auditor |
| FR-011-021 | Frontend: panel de homologación y liberación (registro, evaluación, gates, timeline). | DOC-08 | P0 | Sistema |
| FR-011-100 | Aislamiento por tenant/instalación; idempotencia; hash de evidencia; decimal exacto si aplica. | DOC-03 §12 | P0 | Sistema |

## 7. Reglas no negociables aplicables (Constitución / DOC-01)

- No declarar homologado sin acto formal y versión fiscal aprobada (P5/DOC-01 §5).
- La situación de homologación y modalidad fiscal se documenta **antes de producción** (DOC-01 §10).
- Un usuario no crea y aprueba su propia excepción crítica (segregación de funciones).
- Registros de eventos append-only con integridad y trazabilidad.
- 011 no fabrica permisos/actos de organismos externos; registra y valida.

## 8. Criterios de éxito (resumen)

- Acto de homologación registrado y evaluado con acto formal y evidencia con hash.
- El sistema no declara homologado sin acto formal + versión fiscal aprobada.
- Versiones con changelog y gates; la liberación exige homologación documentada + gates + licencia válida.
- Timeline inmutable de homologación y liberación.
