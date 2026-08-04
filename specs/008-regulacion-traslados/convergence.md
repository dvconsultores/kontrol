# CONVERGENCIA — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Ruta | `specs/008-regulacion-traslados/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-008-01 | Matrices oficiales concretas por organismo/rubro (tolerancias) | Carga de datos como perfiles (CL-008-11) | Regulatorio | Pendiente |
| CVG-008-02 | Verificación en línea con organismos (servicio oficial) | Esfuerzo externo (SU-008-02) | Producto | Pendiente |
| CVG-008-03 | Contingencias con regla oficial versionada en UI ampliada | Frontend contingencia | Regulatorio | Pendiente |
| CVG-008-04 | Guía fiscal del despacho (SENIAT) integrada con 007 | Trabajo de integración fiscal | Fiscal | Pendiente |
| CVG-008-05 | Exportación/reportes regulatorios (matrices) | Spec 009 | Reportes | Pendiente (009) |

## 3. Implementado (008)

| Elemento | Estado |
|---|---|
| Maestros regulatorios (autoridades, tipos de permiso, registros, perfiles, vehículos, conductores) | ✔ |
| Permisos con ciclo de vida (DRAFT→REGISTERED→VERIFIED→APPROVED_FOR_USE→USED→EXPIRED; REJECTED/CANCELLED) y hash | ✔ |
| Guías SICA/SIGESAI/SACS/guía fiscal: registro y validación (no fabricación) con hash/verificación | ✔ |
| Evaluación regulatoria por línea de despacho (consume `Shipment` de 005) con consolidación de requisitos | ✔ |
| Bloqueo del despacho ante faltante/vencido y anulación auditada (override) | ✔ |
| Contingencias solo con regla oficial versionada | ✔ |
| Solicitudes de aprobación con decisión | ✔ |
| Migración Alembic `0008_regulacion` (head) | ✔ |
| API `/regulatory/*` (15 endpoints) + `GET /sales/shipments` (005, aditivo) | ✔ |
| Frontend: organismos, vehículos/conductores, permisos/guías, evaluación y contingencias | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 145/145 (130 previos + 15 de regulación) |
| Backend ruff | ✔ limpio |
| Backend mypy | ✔ 82 archivos, 0 issues |
| Alembic | ✔ head `0008_regulacion` (0001→0008; ALTER de 0004 requiere PostgreSQL, igual que CI) |
| OpenAPI | ✔ 15 endpoints `/regulatory/*` + `GET /sales/shipments` (188 rutas totales) |
| Frontend tsc / eslint | ✔ limpios |
| Frontend vitest / build | ✔ 16/16 · build OK |

## 5. Notas de arquitectura

- 008 **consume** los despachos de 005 (`Shipment`) vía contrato v1; se añadió `GET /sales/shipments` (aditivo, retrocompatible).
- Kontrol **registra y valida** guías/permisos (hash/verificación); no fabrica permisos externos (DOC-01 §10).
- El bloqueo es por regla/perfil versionado; las contingencias exigen regla oficial (FR-008-030).

## 6. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002/003/005 implementados + autorización expresa) |
| Certificación (Docker/CI/legal, integración 009/010/011) | Pendiente — depende de 001 certificada y de Specs 009/010/011 |
