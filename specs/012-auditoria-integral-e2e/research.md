# Spec 012 — Research / Método

## Método empleado
1. **Inventario programático** (Python, no destructivo):
   - `audit_frontend.py`: menú (Sidebar), rutas+imports (router), apiFetch por página, escaneo estático.
   - `audit_backend.py`: carga la app FastAPI, extrae rutas OpenAPI (285), compara con llamadas frontend (135) y calcula huérfanos.
   - `audit_db.py`: inventario de 144 tablas/1.678 columnas y detección de dinero en `Float`.
2. **Reproducciones E2E** (TestClient + BD en memoria): setup→login→licencia FULL_ACCESS→empresa→sucursal→almacén (200).
3. **Suites existentes**: pytest (190) y vitest (16) verdes; tsc/eslint limpios.

## Limitaciones (declaradas)
- Sin PostgreSQL real: no se pudo verificar drift ORM↔migraciones ni timezone.
- Sin navegador/dispositivo real: validación de motores solo simulada.
- Sin pruebas destructivas: seguridad, backup/restore, rendimiento y fiscal normativa pendientes.

## Fuentes
- Código real: `resources/frontend/src`, `resources/backend/app`.
- Evidencia generada: `specs/012-auditoria-integral-e2e/evidence/*.json`.
- Contexto previo: memoria de repo (010, 011, auditoría 001-011).
