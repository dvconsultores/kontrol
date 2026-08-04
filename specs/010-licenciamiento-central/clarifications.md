# CLARIFICACIONES — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Fecha | 2026-08-04 |
| Responsable | Analista funcional senior / Especialista en convergencia |
| Ruta | `specs/010-licenciamiento-central/clarifications.md` |

## 1. Ambigüedades resueltas

| ID | Tema | Pregunta | Decisión | Responsable | Estado |
|---|---|---|---|---|---|
| CL-010-01 | Alcance | ¿010 reimplementa licensing? | **No.** 010 **extiende** el módulo licensing de 001 (LicenseState/Artifact/Event/RenewalRequest) | Arquitecto | Resuelto |
| CL-010-02 | Servidor central | ¿Se implementa el backend en la nube? | El **servidor central real es un componente separado**; 010 implementa el **cliente de sincronización** y la gestión local con contrato v1 | Arquitecto | Resuelto |
| CL-010-03 | Offline | ¿Cómo se valida sin red? | Tolerancia a offline usando `last_reliable_date` (reloj confiable) y gracia configurable | Arquitecto | Resuelto |
| CL-010-04 | Entitlements | ¿Qué habilitan? | Matriz por módulo **002-009**; los módulos respetan la matriz en backend (seguridad por defecto) | Producto | Resuelto |
| CL-010-05 | Renovación | ¿Quién emite? | Solo el **proveedor central** emite la licencia renovada; el cliente solicita con comprobante | Proveedor | Resuelto |
| CL-010-06 | Modos | ¿Nuevos modos? | Reutiliza los modos de 001 y **refuerza** las transiciones y el bloqueo de escrituras | Arquitecto | Resuelto |
| CL-010-07 | Dependencias | ¿Se implementa sin 002-009? | Requiere **001 certificada** y **002-009 implementados** (entitlements) | Producto | Resuelto |
| CL-010-08 | Sincronización | ¿Frecuencia? | Configurable (manual + programada); cada ejecución registrada en `license_sync_runs` | Arquitecto | Resuelto |

## 2. Supuestos declarados

| ID | Supuesto | Riesgo | Mitigación |
|---|---|---|---|
| SU-010-01 | El servidor central existe fuera de este repo; el cliente usa su contrato v1 | Sin servidor real | Cliente configurable y testeable con fake server |
| SU-010-02 | El reloj local es confiable dentro de la gracia | Manipulación de reloj | `last_reliable_date` + verificación remota |
| SU-010-03 | Los entitlements se sincronizan como snapshot | Matriz desactualizada | Versionado + reintento |
| SU-010-04 | 010 no cambia datos de negocio | Acoplamiento | Solo lee la matriz vigente |
| SU-010-05 | READ_ONLY/SECURITY_SUSPENSION ya existentes | Bloqueo insuficiente | Refuerzo con `ensure_write_allowed` |

## 3. Ambigüedades que requieren decisión externa (pendientes)

| ID | Tema | Necesario para | Bloquea |
|---|---|---|---|
| CL-010-09 | Endpoint/URL real del servidor central y credenciales | Sincronización en producción | No la fase documental |
| CL-010-10 | Días de gracia offline por plan | Política de gracia | No la fase documental |

## 4. Estado de aprobación

| Elemento | Estado |
|---|---|
| Ambigüedades resueltas | ✔ |
| Supuestos declarados | ✔ |
| Pendientes registrados | ✔ |
| Aprobación | Pendiente |
