# Spec 012 — Checklist de Auditoría

## Inventarios
- [x] Menú (53 opciones) → `evidence/menu-inventory.json`
- [x] Router (57 rutas) → `evidence/route-audit.json`
- [x] Páginas con apiFetch (52) → `evidence/frontend-api-calls.json`
- [x] Endpoints backend (285) → `evidence/backend-endpoints.json`
- [x] Endpoints sin consumidor (117) → `evidence/backend-orphan-endpoints.json`
- [x] BD: tablas/columnas → `evidence/database-schema-audit.json`
- [x] Escaneo estático (TODO/marcadores)

## Verificaciones de completitud
- [x] Menú → ruta declarada (51/53; **2 rotas**: Seguridad Usuarios/Roles)
- [x] Ruta → página existe (57/57)
- [x] Frontend → endpoint (135/135)
- [x] Backend → interfaz (117 huérfanos: clasificar)
- [x] Dinero en `Float` (58 columnas)
- [ ] Navegadores reales (pendiente)
- [ ] Responsive / axe (pendiente)
- [ ] Seguridad destructiva (pendiente)
- [ ] Backup/restore real (pendiente)
- [ ] E2E de procesos (pendiente)

## Resultado
- HIGH: 2 · MEDIUM: 3 · LOW: 1 · INFO positivos: 5 · PENDIENTES: F-07..F-09
- Veredicto: **NO-GO** (definición estricta) · Detalle en `findings.md` y `AUDITORIA_INTEGRAL_KONTROL.md`
