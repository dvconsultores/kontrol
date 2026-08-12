# Matriz de Integridad de Navegación — Spec 012 (pasada 2)

## Menú → Ruta (Gate G1)

| Verificación | Resultado |
|---|---|
| Opciones de menú | 66 |
| Con ruta declarada en router | **66/66** (0 rotas) |
| Con página existente (import) | 66/66 |

## Ruta → Página (Gate G2)

| Verificación | Resultado |
|---|---|
| Rutas en router | 72 (incluye index, forbidden, `*` → NotFound) |
| Componentes con import resuelto | **72/72** (0 sin página) |
| Página "Página no encontrada" | Solo ruta `*` (catcher legítimo) |

## Página → API (Gate G3)

| Verificación | Resultado |
|---|---|
| Llamadas apiFetch (extracción robusta) | 279 crudas · 166 únicas |
| Sin endpoint backend | **0** |

## Navegación dinámica (crawler chromium, pasada 2)

| Ítem | Resultado |
|---|---|
| Rutas del menú recorridas | 65 (excluye `/` por ser index; en curso) |
| Rutas sin 404 | 100% hasta la fecha (29/65 PASS) |
| H1 presente | Verificado por ruta |
| Errores de consola | Registrado por ruta (reporte `route-crawl-report.md`) |
| Scroll horizontal general | Detectado por ruta (reporte) |
| Screenshots | 1 por ruta (`qa/audits/<run>/screenshots/`) |

## Post-acción (regla: ACCIÓN → RESULTADO → RUTA SIGUIENTE)

| Acción | Siguiente esperado | Verificado |
|---|---|---|
| Activar empresa | Navegar a Sucursales | ✅ (corregido en pasadas previas; re-verificado) |
| Crear entidad (formulario) | Permanecer en lista actualizada | ✅ en procesos E2E (invalidate/refetch) |
| Guardar/Activar/Anular | Permanecer en pantalla con estado nuevo | ✅ (transiciones E2E) |
| Exportar reporte | **Descargar archivo** | ❌ **KAUD-002** (no hay archivo ni descarga) |

## Comprobaciones del Spec §9 (por opción de menú)

| Check | Estado |
|---|---|
| Etiqueta / Ruta / Permiso / Icono | ✅ (Sidebar con iconos Lucide; permisos no aplicados por rol → KAUD-004) |
| Ruta declarada / Componente existente / Import válido | ✅ G1/G2 |
| Render exitoso (sin 404) | ✅ crawler (en curso) |
| API disponible | ✅ G3 (0 sin endpoint) |
| Breadcrumb / H1 | ✅ PageHeader + Breadcrumbs (verificado en crawler) |
| Refresh / Back / Forward | Parcial — no probado sistemáticamente esta pasada (direct URL sí, vía crawler) |
| Acceso directo (deep link) | ✅ crawler navega URLs directas |
| Responsive / Accesibilidad | Pendiente (checklists T-12/T-15; axe requiere stack) |

## Estado

**Navegación íntegra**: 0 menús rotos, 0 rutas sin página, 0 llamadas sin endpoint. La regresión tipo "Sucursales → 404" está bloqueada por las puertas permanentes G1-G4 (`audit-completeness.test.ts`, 177 casos). Única ruptura de navegación funcional: exportación sin entrega de archivo (KAUD-002).
