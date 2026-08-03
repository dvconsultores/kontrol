# CRITERIOS DE ACEPTACIÓN — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Ruta | `specs/001-fundacion/acceptance-criteria.md` |

## Criterios globales

| ID | Criterio | Verificación |
|---|---|---|
| AC-001 | Instalación reproducible desde `compose.yaml` + migraciones + seeds | E2E instalación (T-047) |
| AC-002 | No existen credenciales fijas ni secretos en el repositorio | Escaneo de secretos (CI) |
| AC-003 | La identidad de instalación persiste ante recreación de contenedores | E2E recreación (T-012) |
| AC-004 | La licencia se verifica por firma; solo el propietario la emite/renueva | Test de firma (T-013) |
| AC-005 | READ_ONLY bloquea toda escritura desde backend, jobs e integraciones; conserva consulta/exportación/respaldo | Test de bloqueo (T-016) + E2E |
| AC-006 | El administrador local gestiona su empresa sin poder modificar la licencia | Test de permisos/licencia |
| AC-007 | La navegación respeta permisos y alcance; el backend es autoridad | Contract test + E2E |
| AC-008 | La auditoría registra los eventos obligatorios de forma inmutable | Test de auditoría (T-029) |
| AC-009 | Los health checks y el diagnóstico reportan el estado real | Test de health/diagnóstico |
| AC-010 | Backup y restauración verificados con evidencia | Test restore (T-042) |
| AC-011 | Los requisitos tienen identificador, fuente, dueño, criterio y prueba | Trazabilidad (TMM-001) |
| AC-012 | Se cumple el Estándar Maestro de Frontend (FR-001..FR-040) | Checklist por pantalla |

## Criterios por historia (US)

| Historia | Criterios |
|---|---|
| US-001 | `docker compose up -d` levanta frontend/backend/db/proxy con health OK |
| US-002 | Tras recrear contenedores, `installation_uuid` no cambia |
| US-003 | Se importa licencia firmada; estado pasa a FULL_ACCESS |
| US-004 | Asistente crea empresa inicial y administrador sin credenciales fijas |
| US-005 | Primer login exige cambio de contraseña; sin cambio no se opera |
| US-006 | Login/refresh/logout funcionan; sesiones revocables |
| US-007 | El menú muestra solo lo permitido por rol/alcance |
| US-008 | Acción sin permiso devuelve 403 y pantalla Forbidden |
| US-009 | La auditoría registra inicios, cierres y fallos |
| US-010 | Mi licencia muestra modo, período, límites y comprobante |
| US-011 | Al 1 de mayo sin renovación: READ_ONLY bloquea escritura |
| US-012 | Backup y restore verificados con restauración probada |
| US-013 | `/health/live`, `/health/ready` y diagnóstico responden estado real |
| US-014 | Errores amigables y persistentes con request ID |
| US-015 | Recuperación con token de un solo uso funciona |
| US-016 | Revocar sesión cierra en todas las pestañas |
| US-017 | Configuración inicial de empresa completa dentro de límites |
| US-018 | Cada acción relevante genera evento de auditoría |

## Criterios de la fase documental (cerrados en esta iniciativa)

| ID | Criterio | Estado |
|---|---|---|
| AC-DOC-001 | Todos los documentos inventariados y clasificados | ✔ |
| AC-DOC-002 | Duplicados y conflictos identificados | ✔ |
| AC-DOC-003 | Referencias INNOVA clasificadas como legado | ✔ |
| AC-DOC-004 | Marca nueva KONTROL en todos los artefactos nuevos | ✔ |
| AC-DOC-005 | Constitución existe | ✔ |
| AC-DOC-006 | Spec 001 completa | ✔ |
| AC-DOC-007 | Ambigüedades resueltas o bloqueadas | ✔ (pendientes registrados) |
| AC-DOC-008 | Plan pasa la Constitución | ✔ |
| AC-DOC-009 | Modelo de datos documentado | ✔ |
| AC-DOC-010 | Arquitectura Docker documentada | ✔ |
| AC-DOC-011 | Frontend especificado | ✔ |
| AC-DOC-012 | Licenciamiento especificado | ✔ |
| AC-DOC-013 | Contratos definidos | ✔ |
| AC-DOC-014 | Tareas atómicas | ✔ |
| AC-DOC-015 | Cada requisito tiene prueba | ✔ (test-plan) |
| AC-DOC-016 | Cada riesgo tiene control | ✔ (risk-register) |
| AC-DOC-017 | Versiones tecnológicas propuestas con evidencia | Parcial (verificar al fijar lockfiles) |
| AC-DOC-018 | Git gobernado | ✔ |
| AC-DOC-019 | Artefactos existen físicamente | ✔ (verificar al final) |
| AC-DOC-020 | `/speckit.analyze` sin contradicciones bloqueantes | Pendiente — se ejecuta en `analysis-report.md` |
| AC-DOC-021 | Autorización solicitada antes de implementar | ✔ (punto de detención) |
