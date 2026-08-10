# Spec 012 — Checklist de Rendimiento (T-15)

**Estado: guía lista para ejecutar** (requiere stack levantado con dataset
representativo, no 5 registros). El objetivo es detectar N+1, índices faltantes
y latencia de los endpoints más usados.

## Backend
- [ ] Levantar backend con dataset >10k filas (terceros, ítems, órdenes, movimientos).
- [ ] Medir P50/P95/P99 de los endpoints más usados (login, listados de negocio, kardex, existencias):
      `/auth/login`, `/sales/orders`, `/sales/invoices`, `/inventory/balances`,
      `/inventory/movements`, `/maestros/terceros`, `/reporting/*`.
- [ ] Buscar N+1: revisar listados que serializan líneas/hijos (orders con `lines`,
      invoices, shipments) — cada `line` no debe disparar query adicional por fila.
- [ ] Verificar índices en FKs y columnas de filtro usadas en `.where()`:
      `company_id`, `product_id`, `warehouse_id`, `status`, `created_at`.
- [ ] `EXPLAIN ANALYZE` de los 5 queries más lentos; confirmar seq_scan evitables.
- [ ] Prueba de carga básica (p.ej. `locust`/`hey`) con concurrencia 10–50; sin 5xx.

## Frontend
- [ ] Revisar bundle: `vite build` → tamaño de chunks; lazy-loading de páginas pesadas.
- [ ] Evitar re-renders: queries con `staleTime` adecuado; DataTable con paginación real.
- [ ] Medir LCP/INP en Lighthouse (≥90 en las rutas principales).

## Notas
- El saldo/aging se calcula en el servidor (no se edita); validar que las agregaciones
  de aging/valuation no hagan full-scan en tablas grandes (índices por `company_id+status`).
