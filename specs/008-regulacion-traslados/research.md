# INVESTIGACIÓN — 008-REGULACION-TRASLADOS

| Campo | Valor |
|---|---|
| Iniciativa | 008-regulacion-traslados |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Ruta | `specs/008-regulacion-traslados/research.md` |

## 1. Referencias documentales

| Doc | Sección | Contenido usado | Estado |
|---|---|---|---|
| DOC-01 | §5 | La guía fiscal no sustituye SICA, SIGESAI o SACS cuando aplican; no eliminación física de permisos; picking no ampara traslado. | ✔ |
| DOC-01 | §7 | Maestros Regulatorio: organismos, tipos de permiso, registros oficiales, perfiles, vehículos y certificados. | ✔ |
| DOC-01 | §10 | Un despacho puede requerir simultáneamente documento fiscal/comercial, Guía SICA, permiso SIGESAI, guía SACS u otros; aplicabilidad por rubro/presentación/actor/actividad/origen/destino/establecimiento/cantidad/unidad/operación/vigencia; Kontrol registra y valida documentos oficiales (no fabrica permisos); bloqueo si falta/vencido/no coincide; cada documento conserva número/organismo/emisión/vigencia/archivo/hash/verificación/estado/auditoría; contingencias solo con regla oficial versionada. | ✔ |
| DOC-02 | §3 | Maestros / Regulatorio: organismos; tipos de permiso; registros; perfiles; vehículos; certificados. | ✔ |
| DOC-02 | §5 | Transportista: registro, seguros, vehículos, permisos y contratos. | ✔ |
| DOC-02 | §11 | La regulación evalúa cada línea de despacho y consolida requisitos del movimiento. | ✔ |
| DOC-02 | §12 | Roles: Permiso regulatorio — Logística crea, Responsable regulatorio revisa, Aprobador de salida aprueba. | ✔ |
| DOC-03 | §11 | Entidades: RegulatoryAuthority (SENIAT, SUNAGRO, INSAI, SACS), PermitType, RegulatoryProfile, OfficialRegistration, PermitInstance, RegulatoryEvaluation, ApprovalRequest, AuditEvent, OutboxEvent. | ✔ |
| DOC-03 | §13 | Permiso: DRAFT → REGISTERED → VERIFIED → APPROVED_FOR_USE → USED → EXPIRED; REJECTED/CANCELLED. | ✔ |
| DOC-08 | — | Wireframes: organismos/perfiles, vehículos, permisos, evaluación de despacho. | ✔ |

## 2. Estado de dependencias en el código

| Dependencia | Estado | Uso en 008 |
|---|---|---|
| 001-fundacion | Implementada (certificada) | `companies`, `warehouses`, `locations` |
| 002-maestros | Implementada | `parties`, `catalog_items` (rubros) |
| 003-inventario | Implementada | lotes/seriales/cantidades para coincidencia |
| 005-ventas | Implementada | `Shipment`/`ShipmentLine` objeto de evaluación (contrato v1) |
| 007-fiscal | Implementada | guía fiscal ≠ guías SICA/SIGESAI/SACS (no confundir) |
| 009-reportes | NO (futuro) | matrices y exportación regulatoria |

## 3. Patrones reutilizables verificados

- Módulo backend plano `models.py`/`service.py`/`api.py` + registro en `init_models` y `app/main.py`.
- Máquinas de estado con transiciones explícitas (igual que 004/005/007).
- Hash/trazabilidad de documentos (igual que 007).
- Contrato de integración v1 (005) para consumir despachos.

## 4. Riesgos de investigación

| Riesgo | Detalle | Mitigación |
|---|---|---|
| Fabricar permisos externos | Contrario a DOC-01 §10 | Solo registro/validación documental (CL-008-01) |
| Bloqueo insuficiente del despacho | Fuga de mercancía | Evaluación por línea + bloqueo por regla (FR-008-022) |
| Hardcodear aplicabilidad | Reglas por organismo/rubro cambian | Perfiles versionados (P8) |
| Duplicar el despacho de 005 | 008 podría reimplementarlo | Consumir `Shipment` vía contrato (CL-008-07) |
