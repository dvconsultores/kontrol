# SPEC — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Código | 010-licenciamiento-central |
| Nombre | Licenciamiento central: sincronización, activación, entitlements por módulo, renovación y modos de operación |
| Versión | 1.0 (especificada — pendiente de `/speckit.analyze` y autorización expresa) |
| Estado | ESPECIFICADA |
| Fecha | 2026-08-04 |
| Responsable | Product Owner de KONTROL |
| Dependencia | **001-fundacion** (módulo `licensing`: LicenseState, LicenseArtifact, LicenseEvent, LicenseRenewalRequest) + módulos **002-009** (entitlements). La implementación requiere 001 certificada, 002-009 implementados, y autorización expresa |
| Fuente | DOC-01 §4 (Administrador de plataforma), módulo licensing de 001 (data-model §2.3), DOC-03 §12 |
| Ruta | `specs/010-licenciamiento-central/spec.md` |

> **Regla de inicio (Constitución P1/P2):** esta iniciativa se implementa solo tras completar su propio flujo `/speckit.specify → clarify → plan → checklist → tasks → analyze` y obtener autorización expresa que mencione **010-licenciamiento-central**.

---

## 1. Problema

El módulo `licensing` de 001 gestiona la licencia **local** (instalación, importación de artefactos JWS, modos y renovación). Falta el **licenciamiento central**: sincronización con un servidor de licencias, activación/verificación, **entitlements por módulo** (002-009), renovación con comprobante y workflow central, gestión de múltiples instalaciones y refuerzo de los modos de operación (FULL_ACCESS → READ_ONLY → SECURITY_SUSPENSION). DOC-01 §4 define al Administrador de plataforma como quien configura tenant, licencias, soporte y operación técnica sin acceso a datos de negocio.

## 2. Objetivos

1. **Configuración central**: endpoint del servidor de licencias, clave pública y política de sincronización.
2. **Sincronización/activación**: verificación de la licencia con el servidor central (contrato v1) con tolerancia a **offline** mediante reloj confiable (`last_reliable_date`).
3. **Entitlements por módulo**: matriz que habilita/bloquea módulos 002-009; sincronización de la matriz vigente.
4. **Renovación central**: solicitud con comprobante de pago y workflow (REPORTED → VERIFIED → ISSUED / REJECTED).
5. **Multi-instalación**: registro y gestión de instalaciones vinculadas al tenant.
6. **Modos de operación**: transiciones y refuerzo de FULL_ACCESS / RENEWAL_NOTICE / CRITICAL_RENEWAL_NOTICE / READ_ONLY / SECURITY_SUSPENSION.
7. **Auditoría**: eventos de licencia (activación, sincronización, renovación, cambio de modo) reutilizando `LicenseEvent`.
8. **Integración**: los módulos 002-009 respetan los entitlements vigentes.

## 3. Fuera de alcance

- **Reimplementar** el módulo licensing de 001: 010 lo **extiende**.
- El **servidor central real** (backend en la nube) es un componente separado; 010 implementa el **cliente de sincronización** y la gestión local con contrato v1.
- La **contabilidad formal** y los **reportes** (009 ya cubiertos).

## 4. Actores

| Actor | Uso |
|---|---|
| Administrador de plataforma | Configura tenant, licencias y sincronización (DOC-01 §4) |
| Proveedor (central) | Emite/renueva licencias y verifica comprobantes |
| Auditor | Revisa eventos de licencia |

## 5. Historias de usuario

| ID | Historia |
|---|---|
| US-010-001 | Como administrador, quiero configurar el servidor central de licencias y su clave pública. |
| US-010-002 | Como administrador, quiero sincronizar/activar la licencia contra el servidor central. |
| US-010-003 | Como administrador, quiero ver qué módulos están habilitados por entitlement. |
| US-010-004 | Como administrador, quiero solicitar renovación con comprobante y verificar su workflow. |
| US-010-005 | Como auditor, quiero el historial de eventos de licencia. |

## 6. Requisitos funcionales

Convención: `FR-010-XXX`. Cada requisito tiene fuente (DOC), prioridad (P0/P1/P2), actor, precondición, flujo, excepciones, resultado, auditoría y prueba.

### 6.1 Configuración y sincronización

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-010-001 | Configuración del servidor central (URL, clave pública, política de sincronización). | DOC-01 §4 | P0 | Administrador |
| FR-010-002 | Sincronización de la licencia contra el servidor central (contrato v1) con registro de evento. | DOC-01 §4 | P0 | Sistema |
| FR-010-003 | Activación/verificación con tolerancia a **offline** usando `last_reliable_date` (reloj confiable). | DOC-01 §4 | P0 | Sistema |
| FR-010-004 | `license_sync_runs`: cada sincronización queda registrada (éxito/error, respuesta). | DOC-01 §4 | P0 | Sistema |

### 6.2 Entitlements por módulo

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-010-010 | Matriz de entitlements por módulo (002-009) sincronizada y versionada. | DOC-01 §4 | P0 | Sistema |
| FR-010-011 | Los módulos 002-009 respetan los entitlements vigentes (bloqueo/lectura). | DOC-01 §5 | P0 | Sistema |
| FR-010-012 | `license_entitlement_snapshots`: snapshot de la matriz por sincronización. | DOC-01 §4 | P0 | Sistema |

### 6.3 Renovación central

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-010-020 | Solicitud de renovación con comprobante de pago (reutiliza `LicenseRenewalRequest`). | DOC-01 §4 | P0 | Administrador |
| FR-010-021 | Workflow: REPORTED → VERIFIED → ISSUED / REJECTED; solo el proveedor emite. | DOC-01 §4 | P0 | Proveedor |

### 6.4 Modos de operación y auditoría

| ID | Descripción | Fuente | Prioridad | Actor |
|---|---|---|---|---|
| FR-010-030 | Transiciones de modo: FULL_ACCESS → RENEWAL_NOTICE → CRITICAL_RENEWAL_NOTICE → READ_ONLY → SECURITY_SUSPENSION. | DOC-01 §4 | P0 | Sistema |
| FR-010-031 | READ_ONLY/SECURITY_SUSPENSION refuerzan el bloqueo de escrituras (reutiliza `ensure_write_allowed`). | DOC-01 §5 | P0 | Sistema |
| FR-010-032 | Historico de eventos de licencia (activación, sincronización, renovación, cambio de modo) vía `LicenseEvent`. | DOC-01 §4 | P0 | Auditor |
| FR-010-100 | Aislamiento multi-tenant; idempotencia en sincronización; decimal exacto. | DOC-03 §12 | P0 | Sistema |
| FR-010-101 | Frontend: configuración central, sincronización, entitlements, renovación y eventos. | DOC-08 | P0 | Sistema |

## 7. Reglas no negociables aplicables (Constitución / DOC-01 §4/§5)

- La licencia y sus artefactos son inalterables; toda corrección por emisión de un nuevo artefacto (P5).
- El Administrador de plataforma no accede a datos de negocio.
- Los entitlements vigentes se respetan en backend (seguridad por defecto).
- READ_ONLY/SECURITY_SUSPENSION bloquean escrituras.
- 010 extiende el módulo licensing de 001; no lo reimplementa.

## 8. Criterios de éxito (resumen)

- Configuración del servidor central y sincronización registrada.
- Activación/verificación con tolerancia offline (reloj confiable).
- Matriz de entitlements por módulo respetada en backend.
- Renovación con comprobante y workflow central.
- Transiciones de modo y bloqueo de escrituras reforzado.
- Histórico completo de eventos de licencia.
