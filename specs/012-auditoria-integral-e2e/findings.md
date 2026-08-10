# Spec 012 — Hallazgos de la Auditoría Integral (findings.md)

Estado: **AUDITORÍA COMPLETADA (pasada 1)** · Sin implementación de correcciones.
Método: auditoría automática (menú↔ruta↔página↔API) + estática (BD, marcadores) + reproducciones E2E locales. No se ejecutaron pruebas destructivas contra producción.

---

## Resumen cuantitativo

| Ítem | Valor | Fuente |
|---|---|---|
| Opciones de menú | 53 | `evidence/menu-route-audit.json` |
| Opciones de menú con ruta declarada | 51 | idem |
| Opciones de menú **sin ruta** | **2** (Seguridad) | idem |
| Rutas en router | 57 | `evidence/route-audit.json` |
| Rutas con página existente | 57 (0 sin página) | idem |
| Llamadas apiFetch del frontend | 135 | `evidence/frontend-api-calls.json` |
| Llamadas frontend sin endpoint backend | **0** | `evidence/api-coverage.json` |
| Endpoints backend (método+path) | 285 | `evidence/backend-endpoints.json` |
| Endpoints backend **sin consumidor frontend** | **117** | `evidence/backend-orphan-endpoints.json` |
| Tablas / columnas | 144 / 1.678 | `evidence/database-schema-audit.json` |
| Columnas `FLOAT` para dinero/tasas | **58** | idem |
| TODO/FIXME/console.log (frontend) | **0** | escaneo estático |
| Pruebas backend / frontend | 190 / 16 (verde) | pytest / vitest |

---

## Hallazgos por severidad

### BLOCKER
Ninguno confirmado en esta pasada. (No se ejecutaron pruebas destructivas de seguridad ni backup/restore real.)

### CRITICAL
Ninguno confirmado en esta pasada.

### HIGH

**F-01 · Menú "Seguridad → Usuarios" (`/seguridad/usuarios`) → 404**
- Dominio: Seguridad / Identity · Responsable funcional: Admin · Responsable técnico: Frontend+Backend.
- Evidencia: `menu-route-audit.json` (`declared_in_router: false`); no existe página ni ruta; backend tiene `GET/POST /api/v1/users` **sin interfaz** (`backend-orphan-endpoints.json`).
- Clasificación: **RUTA_NO_DECLARADA / PAGE_MISSING / API_SIN_INTERFAZ** · **PATRÓN SUCURSALES**.
- Impacto: clic en Usuarios → "Página no encontrada"; no hay gestión de usuarios en UI.

**F-02 · Menú "Seguridad → Roles" (`/seguridad/roles`) → 404**
- Dominio: Seguridad · Evidencia: `menu-route-audit.json`; **no existe** endpoint de gestión de roles (solo `/maestros/terceros/{id}/roles/{role}` que es de terceros).
- Clasificación: **RUTA_NO_DECLARADA / PAGE_MISSING / SIN_API** · PATRÓN SUCURSALES.
- Impacto: 404; sin gestión de roles/permisos en UI.

### MEDIUM

**F-03 · 58 columnas `FLOAT` para dinero/tasas**
- Dominio: Financiero/Fiscal · Evidencia: `database-schema-audit.json` (ap_payments.amount, bank_transactions.amount, tax calculations, tesorería, etc.).
- Riesgo: precisión/redondeo en plataforma fiscal. Recomendación: `Numeric(scale=2)`/Decimal antes de certificación.

**F-04 · 117 endpoints backend sin consumidor frontend (API sin interfaz)**
- Dominio: transversal · Evidencia: `backend-orphan-endpoints.json`.
- Destacados: `/organization/establishments` (GET/POST), `/organization/locations`, `/inventory/movements`, `/inventory/balances`, `/inventory/balances/recompute`, `/inventory/movement-types`, `/maestros/perfiles`, `/users`, `/auth/sessions`, `/auth/password-reset/*`.
- Nota: algunos son de soporte (health, docs, licencia offline) y legítimamente no requieren UI; otros son **brechas de interfaz** (ver F-05).

**F-05 · Cadena organizacional incompleta: "Establecimiento" sin UI**
- Dominio: Organización · El flujo E2E Spec-27 (Empresa → Sucursal → **Establecimiento** → Almacén) exige Establecimiento; el backend tiene `/organization/establishments`, pero **no existe menú, ruta ni página**. → `PROCESS_INCOMPLETE`.

### LOW

**F-06 · `DataTable.tsx`: 1 `eslint-disable`** (varianza de TanStack Table) — justificado, se documenta, no es defecto.

### INFO / positivos (evidencia de que lo declarado sí está conectado)

- **P-01** Frontend↔backend: **135/135** llamadas resuelven a endpoints existentes.
- **P-02** Router: **57/57** rutas apuntan a páginas que existen (0 import rotos).
- **P-03** Sin TODO/FIXME/HACK/console.log en frontend.
- **P-04** `pytest` 190 verde · `vitest` 16 verde · `tsc`/`eslint` limpios (ejecutados en esta sesión).
- **P-05** Proceso Empresa→Sucursal→Almacén verificado E2E (repro 200).

### PENDIENTES DE VALIDACIÓN (NO validado, no afirmar)
- **F-07** `DATETIME` sin timezone: **no concluyente en SQLite** (el dialecto colapsa `timezone=True`) → verificar en PostgreSQL real.
- **F-08** Navegadores: solo motor simulado (Chromium); **Safari/Opera/Samsung no validados en dispositivo real** → `SIMULATED_ENGINE_VALIDATION`, no `REAL_BROWSER_VALIDATED`.
- **F-09** Backup/restore real, seguridad destructiva (OWASP), rendimiento con datasets grandes, accesibilidad (axe): **pendientes**, requieren ambiente autorizado.

---

## Remediación aplicada (autorizada, Ola 1 + puertas — 2026-08-10)

| Hallazgo | Acción | Estado | Verificación |
|---|---|---|---|
| F-01 · Usuarios | Página `modules/seguridad/usuarios/UsuariosPage.tsx` + ruta `/seguridad/usuarios` (consumo `GET/POST /users`) | ✅ | E2E 200; re-auditoría 0 rotos |
| F-02 · Roles | Página `modules/seguridad/roles/RolesPage.tsx` + ruta `/seguridad/roles` + endpoints `GET /roles`, `POST/DELETE /users/{id}/roles` | ✅ | E2E 200 (listar/asignar/quitar) |
| F-05 · Establecimiento | Página `EstablecimientosPage.tsx` + ruta `/organizacion/establecimientos` + menú | ✅ | Re-auditoría 0 rotos |
| F-05 · Ubicación | Página `UbicacionesPage.tsx` + ruta `/organizacion/ubicaciones` + menú | ✅ | Re-auditoría 0 rotos |
| Bug pre-existente | `POST /users` no hacía commit (usuario creado pero no persistido) — detectado durante la implementación | ✅ | E2E: crear→asignar→consultar→quitar 200 |
| T-08/T-09 · Puertas | Test `src/tests/audit-completeness.test.ts` (G1 menú→ruta, G2 ruta→página, G3/G4 página→endpoint OpenAPI) | ✅ | vitest 145/145 |

Menú ahora: **55/55 con ruta** · rutas: **61/61 con página** · llamadas API: **sin roturas** (re-auditoría).
