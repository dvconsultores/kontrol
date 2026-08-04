# CONVERGENCIA — 010-LICENCIAMIENTO-CENTRAL

| Campo | Valor |
|---|---|
| Iniciativa | 010-licenciamiento-central |
| Versión | 1.0 |
| Ruta | `specs/010-licenciamiento-central/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la implementación. `/speckit.converge` se ejecuta al cierre.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-010-01 | Servidor central real (backend en la nube) y credenciales | Decisión operativa (CL-010-09) | Producto/Proveedor | Pendiente |
| CVG-010-02 | Días de gracia por plan y política de reintentos | Decisión operativa (CL-010-10) | Producto | Pendiente |
| CVG-010-03 | Sincronización programada con scheduler (ahora manual + on-demand) | Infraestructura | Arquitecto | Pendiente |
| CVG-010-04 | Verificación remota de revocación inmediata (TLS de confianza) | Contrato v2 | Arquitecto | Pendiente |

## 3. Implementado (010)

| Elemento | Estado |
|---|---|
| Configuración del servidor central (`license_central_config`) con gracia offline | ✔ |
| Sincronización/activación contra servidor central (contrato v1), idempotente por día | ✔ |
| `license_sync_runs`: cada ejecución registrada (SUCCESS/FAILED) | ✔ |
| Entitlements por módulo 002-009 + snapshots versionados (`license_entitlement_snapshots`) | ✔ |
| Consulta backend de entitlement (denegación por defecto) | ✔ |
| Tolerancia offline con `last_reliable_date` (reloj confiable) | ✔ |
| Renovación central con comprobante y workflow REPORTED→VERIFIED→ISSUED/REJECTED | ✔ |
| Transiciones de modo (máquina de estados) y refuerzo de `ensure_write_allowed` | ✔ |
| Eventos de licencia (activación, sincronización, renovación, cambio de modo) | ✔ |
| Migración Alembic `0010_licenciamiento` (head) | ✔ |
| API `/licensing/*` (10 endpoints; 205 rutas totales) | ✔ |
| Permisos `license: create/edit/approve` en seed de setup | ✔ |
| Frontend `src/modules/licenciamiento/`: configuración central, entitlements, renovación, eventos | ✔ |

## 4. Validación local

| Compuerta | Resultado |
|---|---|
| Backend pytest | ✔ 173/173 (158 previos + 15 de licenciamiento central) |
| Backend ruff | ✔ limpio |
| Backend mypy | ✔ 90 archivos, 0 issues |
| Alembic | ✔ head `0010_licenciamiento`; cadena validada offline (PostgreSQL); ALTER de 0004 requiere PostgreSQL, igual que CI |
| OpenAPI | ✔ 10 endpoints `/licensing/*` (205 rutas totales) |
| Frontend tsc / eslint | ✔ limpios |
| Frontend vitest / build | ✔ 16/16 · build OK |

## 5. Notas de arquitectura

- **010 extiende el módulo licensing de 001**; no lo reimplementa (CL-010-01). Reutiliza `LicenseState/Artifact/Event/RenewalRequest/Installation`.
- El **servidor central real es un componente separado**; el cliente usa el contrato v1 (`POST /v1/license/sync`) y es **inyectable** en `sync_license` (fake server en tests).
- La **idempotencia** de la sincronización usa una clave estable (instalación + licencia + módulos + día), sin campos volátiles.
- Los **entitlements** se consultan en backend (denegación por defecto); el snapshot es versionado.
- `READ_ONLY`/`SECURITY_SUSPENSION` son **terminales** en la transición manual; solo se salen re-importando o re-sincronizando una licencia válida.
- La validación de la cadena Alembic sobre SQLite no es posible por un `create_unique_constraint` preexistente en `0001` (las migraciones apuntan a PostgreSQL); se validó en modo offline con dialecto PostgreSQL.

## 6. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación | ✔ (sujeta a 001 certificada + 002-009 implementados + autorización expresa) |
| Certificación (Docker/CI/legal, integración 011) | Pendiente — depende de 001 certificada y del servidor central real (CL-010-09) |
