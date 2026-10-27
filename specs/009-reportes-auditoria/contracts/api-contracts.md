# CONTRATOS DE API — 009-REPORTES-AUDITORIA

| Campo | Valor |
|---|---|
| Iniciativa | 009-reportes-auditoria |
| Versión | 1.0 (contratos v1) |
| Fecha | 2026-08-04 |
| Ruta | `specs/009-reportes-auditoria/contracts/api-contracts.md` |

> Autenticación/contexto: `X-Company-Id`, `Authorization: Bearer`. Respuesta estándar `{data, meta}` o `{error}`. Los reportes son de **solo lectura**.

## 1. Dashboard

- `GET /reporting/dashboard` — indicadores agregados y vencimientos por módulo.

## 2. Reportes

- `GET /reporting/reports/{key}` — `key` ∈ ejecutivos/operativos/financieros/fiscales/regulatorios.
- Parámetros comunes: `period`, `company_id`, `currency`, `status`, `category`, `page`, `page_size`.
- `GET /reporting/reports/executive/ventas` · `.../operativos/inventario` · `.../financieros/aging` · `.../fiscales/libros/{tax_type}` (reutiliza 007) · `.../regulatorios/evaluaciones`.

## 3. Exportación auditada

- `POST /reporting/exports` — `{report_key, format: CSV|PDF, filters?}` → genera el archivo y registra `report_exports` (quién/cuándo/qué/filtros). **Idempotente**.
- `GET /reporting/exports` — histórico de exportaciones auditadas.
- `GET /reporting/exports/{export_id}/download` — archivo real de la exportación (`text/csv; charset=utf-8` o `application/pdf`) con `Content-Disposition: attachment; filename="report-<clave>-<AAAAMMDDhhmmss>-<12 hex>.<csv|pdf>"` (sufijo único: dos exportaciones nunca comparten archivo). Exige sesión (`Authorization: Bearer`; nunca en la URL), `reportes:export` y la capacidad de origen del reporte en la empresa activa (ADR-019). Errores en JSON: 401 `AUTH_REQUIRED`, 403 `PERMISSION_DENIED` / `COMPANY_SCOPE_FORBIDDEN`, 404 `EXPORT_NOT_FOUND` / `EXPORT_FILE_MISSING`. La interfaz la pide con el cliente autenticado y la entrega como `blob:` temporal (02E).

## 4. Trabajos asíncronos

- `POST /reporting/jobs` — `{report_key, params?}` → job PENDING.
- `GET /reporting/jobs/{id}` — estado (PENDING/RUNNING/DONE/FAILED) y error.

## 5. Auditoría

- `GET /reporting/audit/timeline` — consolida `AuditEvent` de 001 (cambios, impresiones, exportaciones, accesos, incidentes) con filtros por entidad/acción/usuario/fecha.

## 6. Contratos de integración (consumidos — v1, solo lectura)

| Contrato | Origen | Uso |
|---|---|---|
| `AuditEvent` | 001 | Timeline de auditoría |
| Balances/movimientos | 003 | Operativos |
| Open items/pagos | 004 | Financieros CxP |
| Facturas/órdenes/despachos | 005 | Ejecutivos/operativos |
| Transacciones bancarias/cajas | 006 | Tesorería |
| Libros de 007 | 007 | Fiscales |
| Evaluaciones/permisos | 008 | Regulatorios |

## 7. Endpoints (resumen estimado)

~12 rutas bajo `/reporting`. Se verificarán tras implementación con `app.openapi()['paths']`.
