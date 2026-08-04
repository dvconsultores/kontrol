# CONVERGENCIA — 011-HOMOLOGACION-LIBERACION

| Campo | Valor |
|---|---|
| Iniciativa | 011-homologacion-liberacion |
| Versión | 1.0 |
| Ruta | `specs/011-homologacion-liberacion/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-011-01 | Integración con CI/CD externo (pipeline de gates) | Decisión operativa (CL-011-09) | Arquitecto | Pendiente |
| CVG-011-02 | Plantilla oficial del acto formal (expediente) | Decisión operativa (CL-011-10) | Producto/legal | Pendiente |
| CVG-011-03 | Firma/estampa temporal de eventos (hash encadenado) | Mejora de integridad | Arquitecto | Pendiente |
| CVG-011-04 | Vínculo de la versión liberada con el frontend "Acerca de" | Integración UI | Producto | Pendiente |

## 3. Implementado (011)

| Elemento | Estado |
|---|---|
| Módulo nuevo `app/modules/homologation/` (models/service/api) | ✔ |
| Acto de homologación: DRAFT → SUBMITTED → APPROVED/REJECTED con acto formal y evidencia SHA-256 | ✔ |
| Segregación de funciones (quien crea no evalúa) | ✔ |
| Regla de "homologado" derivada (solo APPROVED + acto formal) | ✔ |
| Eventos append-only (`homologation_events` con source/entity_id) | ✔ |
| Liberación de versión: DRAFT → CANDIDATE → RELEASED/BLOCKED con changelog y gates | ✔ |
| Gate de liberación: homologación aprobada + gates verdes + licencia FULL_ACCESS + no re-liberar versiones anteriores | ✔ |
| Timeline consultable de homologación y liberación | ✔ |
| Migración Alembic `0011_homologacion` (head) | ✔ |
| API `/homologation/*` (8 endpoints; 213 rutas totales) | ✔ |
| Permisos `homologacion: view/create/edit/approve` en seed de setup | ✔ |
| Frontend `src/modules/homologacion/`: actos, versiones/liberación, timeline | ✔ |
| **Fix latente**: `compute_mode` normaliza datetimes naive a UTC (SQLite) | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 190/190 (173 previos + 17 de homologación) |
| Backend ruff | ✔ limpio |
| Backend mypy | ✔ 96 archivos, 0 issues |
| Alembic | ✔ head `0011_homologacion`; cadena validada offline (PostgreSQL) |
| OpenAPI | ✔ 8 endpoints `/homologation/*` (213 rutas totales) |
| Frontend tsc / eslint | ✔ limpios |
| Frontend vitest / build | ✔ 16/16 · build OK |

## 5. Notas de arquitectura

- **011 es un módulo nuevo** (`homologation`) que reutiliza la identidad de instalación y el modo de licencia de 001; no reimplementa licensing ni regulación.
- El **acto formal no se fabrica**: se registra la referencia y la evidencia (SHA-256). El sistema **nunca declara homologado** sin acto formal + versión fiscal aprobada (DOC-01 §5).
- La **liberación de versión** (release) es distinta de la liberación de lotes (CL-011-03). Queda gateada en backend.
- **Fix de `compute_mode`** (app/core/license.py): normaliza datetimes naive a UTC, corrigiendo un fallo latente al leer `DateTime(timezone=True)` desde SQLite (producción PostgreSQL no se afecta).

## 6. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002-010 implementados + autorización expresa) |
| Certificación (Docker/CI/legal) | Pendiente — depende de 001 certificada y de las decisiones CL-011-09/10 |
