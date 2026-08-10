# AUDITORÍA INTEGRAL DE KONTROL — Reporte Ejecutivo

Fecha: 2026-08-10 · Rama: `develop` · Spec: `specs/012-auditoria-integral-e2e/`
Estado: **AUDITORÍA COMPLETADA (pasada 1, no destructiva)** · No se implementó ninguna corrección.

## 1. Resumen

KONTROL está **sustancialmente conectado**: 135/135 llamadas del frontend resuelven a endpoints reales,
57/57 rutas apuntan a páginas existentes, 0 TODO/console.log en frontend, y las suites (pytest 190, vitest 16)
están verdes. Sin embargo, **la cadena completa no está garantizada en todas las funciones**: se confirmaron
**2 menús rotos** (Seguridad → Usuarios y Seguridad → Roles, con 404 al navegar — el mismo defecto que
Sucursales) y **varias interfaces faltantes** (Establecimiento, Ubicación, Perfiles fiscales, movimientos de
inventario) pese a que el backend ya las expone.

## 2. Navegación
- 53 opciones de menú → 51 con ruta declarada · **2 sin ruta (Seguridad → 404)** · 0 rutas sin página.
- El flujo "Empresa activada → Sucursales" ya funciona (corregido y verificado).

## 3. Frontend
- Pantallas: 52 páginas con llamadas API; formularios/DataTables con patrón uniforme.
- **Sin placeholders mock ni código muerto evidente.**
- Pendiente: navegadores reales (solo motor simulado) y accesibilidad (axe).

## 4. Backend
- 285 endpoints inventariados; **0 llamadas frontend sin endpoint** (positivo).
- **117 endpoints sin consumidor frontend** (API sin interfaz): clasificar futuros vs brechas.

## 5. Base de datos
- 144 tablas / 1.678 columnas inventariadas.
- **58 columnas `FLOAT` para dinero/tasas** (riesgo de precisión fiscal).
- Drift ORM↔migraciones y timezone: pendiente de verificar en PostgreSQL real (SQLite no concluye).

## 6. Procesos
- Completos: Empresa, Sucursal, Almacén, Terceros, Maestros, Licencia.
- Incompletos: Establecimiento y Ubicación (sin UI), Seguridad (Usuarios/Roles), perfiles fiscales.
- Ventas/Compras/Inventario/Fiscal: pantallas y API presentes; **sin E2E de proceso integral** (unidad de validación = proceso).

## 7. Seguridad / Licencia / QA
- Renovación de sesión ante 401 implementada; licencia FULL_ACCESS en modo pruebas.
- Pruebas destructivas de seguridad, backup/restore real y rendimiento: **pendientes** (requieren ambiente autorizado).

## 8. Recomendación

**NO-GO** para certificación fiscal/producción bajo la definición estricta del Spec (existen HIGH y procesos no 100%).
**CONDITIONAL GO** para pruebas internas de módulos no fiscales.

Para alcanzar GO se requiere, en orden:
1. Resolver F-01/F-02 (Usuarios y Roles) y F-05 (Establecimiento/Ubicación).
2. Instalar puertas permanentes (test de completitud de menú/ruta/página/API — evita regresión tipo Sucursales).
3. Migrar dinero a `Numeric` (F-03) y verificar timezone/drift en PostgreSQL (F-06/F-07).
4. Validaciones pendientes: navegadores reales, accesibilidad, seguridad, backup/restore, rendimiento, auditoría fiscal.

Detalle: `findings.md` · `functional-completeness-matrix.md` · `remediation-plan.md` · `evidence/`.

---

## 9. Estado de remediación (avances)

### Ola 1 — usuarios, roles, establecimientos, ubicaciones (commit `d7f0bca`)
Páginas creadas y endpoints de roles/sesiones. Puertas permanentes G1–G4 instaladas
(`src/tests/audit-completeness.test.ts`).

### Olas 2–4 — precisión y procesos (commit `8615c24`)
Dinero Float→Numeric (58 columnas, migración `0012_numeric_money`), cadena de
migraciones validada offline en PostgreSQL, clasificación de 117 endpoints
huérfanos, tests E2E de procesos (`test_process_flows.py`) y crawler Playwright.

### GAP UI + permisos (commit `6ad6513`)
Perfiles fiscales y sesiones; fix crítico de permisos del rol ADMIN
(seed completo + migración `0013_seed_business_permissions`).

### Operar ventas/compras desde la UI (commits `8e06e43`, `5e15b57`)
- Órdenes/facturas de venta y compra: crear + agregar líneas.
- Cotizaciones: crear + líneas. CxC/CxP: cobros/pagos, anticipos, aplicaciones y cronogramas.
- Nuevas páginas: devoluciones (venta/compra), notas de venta (crédito/débito + post/aplicar),
  notas de crédito de proveedor, y picking/despacho (pick lists + envíos).
- Endpoints GET de listado añadidos para devoluciones, notas y pick lists.
- **Fix crítico pre-existente (alcance de almacenes)**: la organización crea almacenes con
  `company_id = Company.id`, pero los módulos de negocio validan contra `user.tenant_id`.
  Helper `warehouse_in_tenant_scope` (tenant-scoped) en ventas/compras/inventario —
  sin él, picking/despacho/inventario fallaban con almacenes creados desde la UI.

Validación acumulada: pytest 193 · ruff · mypy · tsc · eslint · vitest 172 ·
smoke E2E por API 40/40 OK. Re-auditoría: menú/rutas/páginas/endpoints 100% coherentes.

