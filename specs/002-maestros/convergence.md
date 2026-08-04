# CONVERGENCIA — 002-MAESTROS

| Campo | Valor |
|---|---|
| Iniciativa | 002-maestros |
| Versión | 1.0 |
| Ruta | `specs/002-maestros/convergence.md` |

## 1. Propósito

Registrar brechas y nuevas tareas tras la fase documental. `/speckit.converge` se ejecuta al cierre de la implementación.

## 2. Brechas identificadas

| ID | Brecha | Acción | Responsable | Estado |
|---|---|---|---|---|
| CVG-002-01 | Catálogo semilla global (sectores/rubros) | Definir alcance (CL-002-11) | Producto | Pendiente |
| CVG-002-02 | Conjunto base de atributos obligatorios por rubro | Definir política (CL-002-12) | Producto | Pendiente |
| CVG-002-03 | Migración `0002` y seeds | T-002-001, T-002-025 | Datos | ✔ Completado (implementación) |
| CVG-002-04 | Evidencia de pruebas | T-002-021..023 | QA | ✔ Completado (backend 37, frontend 16) |
| CVG-002-05 | Integración con documentos futuros (snapshot de maestros) | Alinear con Specs 003-007 | Arquitecto | Pendiente |

## 3. Estado

| Elemento | Estado |
|---|---|
| Fase documental | ✔ |
| Implementación backend | ✔ Modelos (23 tablas), servicio, API `/maestros` (12 endpoints), migración `0002`, seeds idempotentes |
| Implementación frontend | ✔ Páginas (Terceros, Productos, Nuevo producto, Servicios, Catálogo), `AsyncCombobox`, rutas y sidebar |
| Validación local | ✔ Backend: 37/37 tests, ruff, mypy, Alembic head `0002_maestros`, OpenAPI 12 endpoints — Frontend: tsc, eslint, vitest 16/16, build |
| Convergencia final | Pendiente (tras certificación 001: CI E3, Docker B5/C5/D1-D5, PR F2) |
