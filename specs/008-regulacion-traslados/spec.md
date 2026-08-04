# SPEC — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Código | 008-regulacion-traslados |
| Nombre | Regulación y traslados: guías (SICA, SIGESAI, SACS), permisos, vehículos/conductores, evaluación y bloqueo del despacho |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** + **002-maestros** + **003-inventario-logistica** + **005-ventas-cuentas-por-cobrar** (despacho). La implementación requiere 001 certificada, 002/003/005 implementados, y autorización expresa |
| Fuente | DOC-01 §5, §7, §10; DOC-02 §3, §5, §11, §12; DOC-03 §11, §13 |
| Ruta | `specs/008-regulacion-traslados/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **008-regulacion-traslados**.

---

## 1. Problema

Los despachos de 005 se validan documentalmente, pero falta la **regulación sectorial** que gobierna el traslado físico de mercancías: guías SICA, SIGESAI, SACS y otros organismos; permisos con ciclo de vida; vehículos y conductores; y la **evaluación regulatoria por línea de despacho** que consolida requisitos del movimiento y **bloquea la salida** cuando falta un documento obligatorio, está vencido o no coincide con producto, lote, cantidad, origen, destino, vehículo o conductor (DOC-01 §10).

DOC-01 §5 y §10 son claros: la guía fiscal **no sustituye** SICA/SIGESAI/SACS; Kontrol **registra y valida documentos oficiales, no fabrica permisos** de organismos externos; el picking no ampara el traslado físico; cada documento conserva número, organismo, emisión, vigencia, archivo, hash, verificación, estado y auditoría; y las contingencias se habilitan solo mediante regla oficial versionada.

## 2. Objetivos

1. **Maestros regulatorios** (DOC-01 §7, DOC-02 §3): organismos, tipos de permiso, registros oficiales, perfiles regulatorios, vehículos, conductores y certificados.
2. **Aplicabilidad** por rubro, presentación, actor, actividad, origen, destino, establecimiento, cantidad, unidad, operación y vigencia (DOC-01 §10).
3. **Evaluación regulatoria por línea de despacho** que consolida requisitos del movimiento (DOC-02 §11) y **bloquea** la salida ante falta/vigencia/coincidencia de documentos (DOC-01 §10).
4. **Guías de traslado** (SICA, SIGESAI, SACS): registro y validación de documentos oficiales (no se fabrican permisos externos).
5. **Permisos** con ciclo de vida: DRAFT → REGISTERED → VERIFIED → APPROVED_FOR_USE → USED → EXPIRED; REJECTED/CANCELLED (DOC-03 §13).
6. **Trazabilidad y auditoría**: cada documento conserva número, organismo, emisión, vigencia, archivo, hash, verificación, estado y auditoría; no hay eliminación física de permisos (P5).
7. **Contingencias** habilitadas solo mediante regla oficial versionada (P8, DOC-01 §10).
8. **Integración**: evaluar los despachos de 005 y gobernar la salida física.

## 3. Fuera de alcance

- **Núcleo fiscal / guías fiscales** — Spec 007 (la guía fiscal no sustituye SICA/SIGESAI/SACS).
- **Reportes** — Spec 009.
- La **emisión de permisos por organismos externos** (SENIAT, SUNAGRO, INSAI, SACS) — Kontrol registra/valida, no fabrica (DOC-01 §10).
- La **homologación** de la versión regulatoria — proceso formal externo.

## 4. Actores

| Actor | Uso |
|---|---|
| Logística | Crea guías, registra vehículos/conductores y movilización (DOC-02 §12) |
| Responsable regulatorio | Revisa requisitos y permisos (DOC-02 §12) |
| Aprobador de salida | Aprueba el despacho regulado (DOC-02 §12) |
| Despacho / logística | Vehículos, conductores, documentos y entrega (DOC-01 §4) |
| Auditor | Trazabilidad de permisos, guías y evaluaciones |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-008-001 | Como logística, quiero registrar organismos, tipos de permiso y registros oficiales. |
| US-008-002 | Como logística, quiero registrar vehículos, conductores y certificados. |
| US-008-003 | Como logística, quiero definir perfiles regulatorios que determinan qué documentos aplican por rubro/operación/origen/destino. |
| US-008-004 | Como logística, quiero registrar y validar guías SICA/SIGESAI/SACS y permisos oficiales. |
| US-008-005 | Como logística, quiero que cada línea de despacho evalúe sus requisitos regulatorios y consolide el movimiento. |
| US-008-006 | Como aprobador de salida, quiero que el despacho se bloquee si falta un documento, está vencido o no coincide. |
| US-008-007 | Como auditor, quiero la trazabilidad completa de permisos, guías y evaluaciones (hash y auditoría). |
| US-008-008 | Como logística, quiero habilitar contingencias solo con regla oficial versionada. |

## 6. Requisitos funcionales

Convención: `FR-008-XXX`. Cada requisito tiene fuente (DOC), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 6.1 Maestros regulatorios

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-008-001 | `RegulatoryAuthority`: SENIAT, SUNAGRO, INSAI, SACS u otro, con código y validación. | DOC-03 §11 | P0 | Logística |
| FR-008-002 | `PermitType`: autoridad, código, nombre, alcance, método de validación y estado. | DOC-03 §11 | P0 | Logística |
| FR-008-003 | `OfficialRegistration`: empresa/tercero/sitio/vehículo/persona, autoridad, número, fechas, archivo y estado. | DOC-03 §11 | P0 | Logística |
| FR-008-004 | Vehículos y conductores: registro con identificación, capacidad y documentos. | DOC-02 §3/§5 | P0 | Logística |
| FR-008-005 | `RegulatoryProfile`: condiciones por rubro/producto/operación/origen/destino y documentos requeridos. | DOC-03 §11 | P0 | Logística |

### 6.2 Permisos y guías

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-008-010 | `PermitInstance`: número, emisión, vencimiento, origen/destino, productos/lotes/cantidad, transporte, archivo y verificación. | DOC-03 §11 | P0 | Logística |
| FR-008-011 | Ciclo del permiso: DRAFT → REGISTERED → VERIFIED → APPROVED_FOR_USE → USED → EXPIRED; REJECTED/CANCELLED. | DOC-03 §13 | P0 | Sistema |
| FR-008-012 | Guías SICA/SIGESAI/SACS: Kontrol **registra y valida** documentos oficiales; no fabrica permisos externos. | DOC-01 §10 | P0 | Logística |
| FR-008-013 | Cada documento conserva número, organismo, emisión, vigencia, archivo, hash, verificación, estado y auditoría. | DOC-01 §10 | P0 | Sistema |
| FR-008-014 | No existe eliminación física de permisos; corrección por documento vinculado (P5). | DOC-01 §5 | P0 | Sistema |

### 6.3 Evaluación y bloqueo del despacho

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-008-020 | La regulación **evalúa cada línea de despacho** y consolida requisitos del movimiento. | DOC-02 §11 | P0 | Sistema |
| FR-008-021 | `RegulatoryEvaluation`: despacho/línea, versión del perfil, requisitos, resultados, bloqueos y anulación. | DOC-03 §11 | P0 | Sistema |
| FR-008-022 | El despacho se **bloquea** si falta un documento obligatorio, está vencido o no coincide con producto, lote, cantidad, origen, destino, vehículo o conductor. | DOC-01 §10 | P0 | Sistema |
| FR-008-023 | La aplicabilidad se determina por rubro, presentación, actor, actividad, origen, destino, establecimiento, cantidad, unidad, operación y vigencia. | DOC-01 §10 | P0 | Sistema |
| FR-008-024 | Un despacho puede requerir simultáneamente documento fiscal/comercial, Guía SICA, permiso SIGESAI y guía SACS. | DOC-01 §10 | P0 | Sistema |
| FR-008-025 | `ApprovalRequest`: objeto, regla, solicitante, aprobadores, riesgo, monto, plazo, decisión y estado. | DOC-03 §11 | P1 | Aprobador |

### 6.4 Contingencias e integración

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-008-030 | Las contingencias se habilitan **solo mediante regla oficial versionada**. | DOC-01 §10 | P0 | Sistema |
| FR-008-031 | El picking no ampara el traslado físico; la guía fiscal no sustituye SICA/SIGESAI/SACS. | DOC-01 §5 | P0 | Sistema |
| FR-008-032 | 008 consume los despachos de 005 (`Shipment`) y gobierna la validación de salida (contrato v1). | DOC-01 §1 | P0 | Sistema |
| FR-008-100 | Aislamiento multiempresa; idempotencia; decimal exacto; versionado de reglas (P8). | DOC-03 §12 | P0 | Sistema |
| FR-008-101 | Frontend: organismos/perfiles, vehículos, guías/permisos, evaluación del despacho y contingencias. | DOC-08 | P0 | Sistema |

## 7. Reglas no negociables aplicables (Constitución / DOC-01 §5/§10)

- Kontrol **registra y valida documentos oficiales; no fabrica permisos** de organismos externos.
- El despacho se bloquea si falta un documento obligatorio, está vencido o no coincide con producto, lote, cantidad, origen, destino, vehículo o conductor.
- Cada documento conserva número, organismo, emisión, vigencia, archivo, hash, verificación, estado y auditoría.
- Las contingencias se habilitan solo mediante regla oficial versionada (P8).
- No existe eliminación física de permisos; corrección por documento vinculado (P5).
- La guía fiscal no sustituye SICA, SIGESAI o SACS cuando aplican.
- El picking no ampara el traslado físico.

## 8. Criterios de éxito (resumen)

- Maestros regulatorios (organismos, tipos, registros, perfiles, vehículos, conductores, certificados) disponibles.
- Permisos con ciclo de vida completo y trazabilidad (hash/auditoría).
- Guías SICA/SIGESAI/SACS registradas y validadas (no fabricadas).
- La regulación evalúa cada línea de despacho y consolida requisitos del movimiento.
- El despacho se bloquea ante faltante/vencido/no coincidencia.
- Contingencias solo con regla oficial versionada.
- 008 consume los despachos de 005 sin duplicar su lógica.
