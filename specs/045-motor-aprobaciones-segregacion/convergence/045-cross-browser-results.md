# CROSS-BROWSER Y RESPONSIVE — SPEC 045 (CVG-045-06)

## Motores

```
CHROMIUM: PASS   E2E 11/11 · axe 22/22
FIREFOX:  PASS   E2E 11/11 · axe 22/22
WEBKIT:   PASS   E2E 11/11 · axe 22/22
```

**No se afirma Safari real**: solo se ejecutó WebKit (§25).
Edge y Opera no se ejecutaron: no hay binarios en el entorno.

## Escenarios cubiertos en los tres motores (§26)

Login · lista de políticas · crear política · editar (regla, niveles) · simular ·
activar · bandeja · aprobar · rechazar · devolver · historial · navegación ·
`ConfirmationDialog` con motivo · conflicto `If-Match` · mensajes de error ·
`allowed_actions` (botones que el backend autoriza) · estados de carga y vacío.

## Responsive (§27)

36 rutas × 6 viewports (320, 375, 412, 768, 1366, 1920) = **216 comprobaciones**.

| Ámbito | Comprobaciones | Scroll horizontal |
|---|---:|---:|
| **Rutas de la Spec 045** (bandeja, políticas, delegaciones) | **18** | **0** |
| Rutas preexistentes | 198 | **22** |

### Hallazgo: 22 violaciones de P11 en rutas preexistentes

Al corregir el crawler para que navegara de verdad (antes medía `/`), afloraron
violaciones reales del Principio 11 («las tablas no usan scroll horizontal»):

| Ruta | Viewports afectados |
|---|---|
| `/inventario/transferencias` | 320, 375, 412 |
| `/compras/cuentas-por-pagar` | 320, 375, 412 |
| `/ventas/cuentas-por-cobrar` | 320, 375, 412 |
| `/inventario/movimientos` | 320, 375 |
| `/maestros/atributos`, `/inventario/seriales`, `/inventario/reservas`, `/inventario/tipos-movimiento`, `/compras/{ordenes,facturas,cotizaciones}`, `/ventas/{ordenes,facturas}`, `/fiscal/lotes-declaracion`, `/seguridad/roles` | 320 |

**Ninguna pertenece a la Spec 045.** Escaladas a las Specs propietarias y a la
Spec 054. Corregirlas aquí sería ampliar el alcance.

## Accesibilidad (§28)

axe-core WCAG 2.2 AA, 22 páginas, tres motores, **0 violaciones serias o críticas**.
Operación con teclado verificada en la bandeja. Foco visible en todos los
controles interactivos.

### Defectos de accesibilidad corregidos

Al medir las rutas reales aparecieron violaciones que la instrumentación previa
no podía ver. Todas de contraste o de nombre accesible, ninguna introducida por 045:

| Elemento | Antes | Después | Alcance |
|---|---|---|---|
| Títulos de sección del Sidebar | `text-400` 2,56:1 | `text-500` 4,76:1 | **Todas** las páginas autenticadas |
| Cabecera de `DataTable` | `text-500` sobre `surface-100` 4,34:1 | `text-600` 6,92:1 | **Toda** tabla con datos |
| «Sin empresa activa» (Topbar) | `text-400` 2,56:1 | `text-500` | Global |
| Nota de `DataTable` | `text-400` | `text-500` | Global |
| Etiquetas de indicador del Dashboard | `text-400` | `text-500` | `/` |
| Tres `<select>` sin nombre accesible en Reservas | — | `aria-label` | `/inventario/reservas` |

Iconos decorativos, `placeholder` y estados `disabled` conservan `text-400`: axe
no los exige y cambiarlos alteraría el diseño sin motivo.
