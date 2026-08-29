# SPEC 013 — GAP ANALYSIS INTEGRAL Y ROADMAP MAESTRO

| Campo | Valor |
|---|---|
| Iniciativa | `013-gap-analysis-roadmap-maestro` |
| Versión | 1.0 |
| Estado | Ejecutada (auditoría) — **sin implementación** |
| Rama | `develop` · HEAD `def2b52` |
| Fecha | 2026-08-29 |
| Autoridad | Nivel 4 (Spec) bajo Constitución v1.0 |

## 1. Propósito

Determinar con evidencia, y no por inspección superficial, el estado real de KONTROL
frente a un **catálogo maestro funcional de 56 Specs**, para establecer el orden correcto
de construcción y eliminar el riesgo de seguir edificando procesos desconectados.

Esta iniciativa **no implementa código**. Su entregable es conocimiento accionable:
matrices, clasificación, grafo de dependencias, roadmap por olas y backlog maestro.

## 2. Alcance

- Inventario documental de `requerimientos/` (15 PDF + 3 documentos de proceso nuevos).
- Inventario de las 12 Specs existentes y su equivalencia con el catálogo maestro de 56.
- Auditoría de frontend real (rutas, menú, páginas, componentes, llamadas API).
- Auditoría de backend real (endpoints, servicios, modelos, máquinas de estado).
- Auditoría de base de datos real (144 tablas, 14 migraciones, drift).
- Auditoría de integraciones, pruebas, seguridad e infraestructura.
- Contraste contra los procesos documentados de importación/recepción y pedido/despacho.
- Clasificación de cada una de las 56 Specs en un estado único.
- Grafo de dependencias, priorización y roadmap por olas.

## 3. Fuera de alcance

- Implementar, corregir o refactorizar código (prohibido por el prompt maestro y por P2).
- Ejecutar `/speckit.implement`.
- Crear las Specs del roadmap (requiere autorización expresa posterior).
- Validación normativa fiscal (requiere equipo legal — se registra como bloqueo).
- Pruebas destructivas o emisión de documentos fiscales productivos.

## 4. Requisitos funcionales de la auditoría

| ID | Requisito | Evidencia |
|---|---|---|
| FR-013-001 | Verificar la cadena completa Requisito→Spec→Menú→Ruta→Página→API→Backend→Modelo→DB→Efecto→Auditoría→Prueba para cada dominio | `docs/roadmap/56-specs-gap-analysis.md` |
| FR-013-002 | Detectar sistemáticamente el **patrón Sucursales** (etapa ausente en una cadena que el sistema asume existente) | `docs/roadmap/false-completion-findings.md` |
| FR-013-003 | Distinguir cinco estados: DOCUMENTADO / ESPECIFICADO / IMPLEMENTADO / PROBADO / OPERATIVO E2E | `56-specs-gap-analysis.md` |
| FR-013-004 | Clasificar cada Spec maestra en exactamente un estado principal; la suma debe ser 56 | `KONTROL_GAP_ANALYSIS_ROADMAP_MAESTRO.md` §4 |
| FR-013-005 | Mapear requerimientos documentados → 56 Specs y detectar requisito sin Spec | `requirements-to-specs-map.md` |
| FR-013-006 | Mapear código real → 56 Specs y detectar código sin Spec | `code-to-specs-map.md` |
| FR-013-007 | Construir el grafo de dependencias completo entre las 56 | `spec-dependency-graph.md` |
| FR-013-008 | Producir un roadmap por olas **ejecutable**, ordenado por dependencia real y no por número | `roadmap-by-waves.md` |
| FR-013-009 | Producir backlog maestro con criterio de aceptación y estimación relativa | `master-backlog.md` |
| FR-013-010 | Registrar bloqueantes y decisiones pendientes sin inventarlas | `KONTROL_GAP_ANALYSIS_ROADMAP_MAESTRO.md` §12-13 |

## 5. Criterio de completitud (P10, P3)

Una Spec maestra **no** se declara completa por existir archivos, menú, endpoint o tabla.
Requiere flujo funcional demostrado de extremo a extremo. `COMPLETE_100` exige además
evidencia E2E sobre el motor de persistencia de producción (PostgreSQL), que hoy **no existe**
para ningún dominio.

## 6. Regla de autoridad (P73 del prompt maestro)

El código actual **no** es la autoridad funcional. Cuando el requerimiento documentado exige
una etapa que el código no tiene, se registra brecha; no se elimina la etapa del roadmap
para poder declarar completo.
