# WIREFRAMES — SPEC 045

Conforme al Estándar Maestro de Frontend, ADR-006, ADR-015 y P18: **pantallas completas con URL
propia**; modales solo para confirmación breve. Componentes del design system compartido; sin
variantes locales.

## Rutas

| Ruta | Pantalla | Permiso |
|---|---|---|
| `/aprobaciones/bandeja` | Mis aprobaciones | `aprobaciones:approve` |
| `/aprobaciones/politicas` | Políticas (lista) | `aprobaciones:view` |
| `/aprobaciones/politicas/:id` | Política (edición completa) | `aprobaciones:configure` |
| `/aprobaciones/delegaciones` | Delegaciones | `aprobaciones:view` |
| *(panel embebido)* | Historial de aprobaciones | `aprobaciones:view` |

## WF-045-01 · Mis aprobaciones

```
┌────────────────────────────────────────────────────────────────────────┐
│ Inicio › Aprobaciones › Mis aprobaciones            [Empresa activa ▾] │
│ ── Mis aprobaciones ──────────────────────────────────────────────────  │
│ Solicitudes que esperan tu decisión                                     │
│                                                                         │
│ [Buscar…]  Proceso ▾  Estado ▾  Antigüedad ▾  ☐ Solo vencidas          │
│                                                                         │
│ ┌────────┬──────────────┬────────────┬──────────┬───────┬────────────┐ │
│ │Proceso │ Documento    │ Solicitante│ Monto    │ Nivel │ Vence      │ │
│ ├────────┼──────────────┼────────────┼──────────┼───────┼────────────┤ │
│ │Orden   │ OC-2026-0182 │ …          │ 547.500,00│ 2 de 2│ en 6 h  ⚠ │ │
│ │Ajuste  │ AJ-2026-0031 │ …          │        —  │ 1 de 1│ —          │ │
│ │Crédito │ OV-2026-0904 │ …          │  98.200,00│ 1 de 2│ vencido 🔴│ │
│ └────────┴──────────────┴────────────┴──────────┴───────┴────────────┘ │
│                                              11-20 de 34  ‹ 1 2 3 4 ›   │
└────────────────────────────────────────────────────────────────────────┘
```

- **Monto siempre en moneda base**, con `tabular-nums` y la moneda indicada en la cabecera.
- Vencimiento como estado visible, no solo como fecha.
- Sin scroll horizontal: en móvil la tabla se convierte en tarjetas (P11).
- El detalle abre en **ruta propia**, no en modal.

## WF-045-02 · Detalle de solicitud

```
┌────────────────────────────────────────────────────────────────────────┐
│ … › Mis aprobaciones › OC-2026-0182                                     │
│ ── Orden de compra OC-2026-0182 ──────────────  [En revisión · Nivel 2] │
│                                                                         │
│ Solicitante …          Monto base 547.500,00 VED (tasa 36,50)           │
│ Política  Compras v3   Solicitada hace 2 días                           │
│                                                                         │
│ ── Niveles ───────────────────────────────────────────────────────────  │
│  ✓ Nivel 1 · Aprobado · … · hace 1 día                                 │
│      «Revisado contra presupuesto»                                      │
│  ● Nivel 2 · En revisión · cuórum 2 de 3 · 1 decisión registrada        │
│  ○ —                                                                    │
│                                                                         │
│ ── Documento ─────────────────────────────────────────────────────────  │
│  [tabla de líneas en solo lectura]                        [Ver orden →] │
│                                                                         │
│ ── Evidencia ─────────────────────────────────────────────────────────  │
│  (disponible con la Spec 046)                                           │
│                                                                         │
│                        [Devolver]   [Rechazar]   [Aprobar]              │
└────────────────────────────────────────────────────────────────────────┘
```

Los tres botones se renderizan **solo** si `allowed_actions` los incluye. Ocultarlos es presentación;
la autoridad es el 403 del backend (P6).

## WF-045-03 · Confirmación (único modal admitido)

```
        ┌──────────────────────────────────────────┐
        │  Devolver para corrección                │
        │                                          │
        │  Motivo *                                │
        │  ┌────────────────────────────────────┐  │
        │  │                                    │  │
        │  └────────────────────────────────────┘  │
        │  Se devolverá a … para corrección.       │
        │  El historial se conserva.               │
        │                                          │
        │              [Cancelar]  [Devolver]      │
        └──────────────────────────────────────────┘
```

Confirmación breve con motivo obligatorio: es el caso que ADR-015 sí permite. Toda la configuración
va en pantalla completa.

## WF-045-04 · Políticas (lista)

```
┌────────────────────────────────────────────────────────────────────────┐
│ … › Aprobaciones › Políticas                        [+ Nueva política] │
│ Reglas de autorización por proceso. Las políticas se versionan.        │
│                                                                         │
│ ┌──────────────┬─────┬─────────┬────────────┬───────────┬────────────┐ │
│ │ Proceso      │ Ver.│ Estado  │ Vigente    │ Reglas    │ Segregación│ │
│ ├──────────────┼─────┼─────────┼────────────┼───────────┼────────────┤ │
│ │ Orden compra │  3  │ Activa  │ desde …    │ 4         │ Sí         │ │
│ │ Orden compra │  2  │ Cerrada │ … – …      │ 3         │ Sí         │ │
│ │ Ajuste inv.  │  1  │ Borrador│ —          │ 2         │ Sí         │ │
│ └──────────────┴─────┴─────────┴────────────┴───────────┴────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

Las versiones cerradas se muestran, no se ocultan: son la historia de la política.

## WF-045-05 · Edición de política — pantalla completa

```
┌────────────────────────────────────────────────────────────────────────┐
│ … › Políticas › Orden de compra v4 (borrador)      [Guardar] [Activar] │
│                                                                         │
│ ── General ───────────────────────────────────────────────────────────  │
│  Proceso [Orden de compra ▾]   Moneda base [VED ▾]                     │
│  ☑ Exigir segregación de funciones                                     │
│  ☐ Permitir autoaprobación                                             │
│  ☑ Exigir aprobadores distintos entre niveles                          │
│                                                                         │
│ ── Regla 1 ──────────────────────────────────────────  [Eliminar regla]│
│  Condiciones (se cumplen todas)                                        │
│   [Monto base ▾] [mayor que ▾] [__________]              [Quitar]      │
│   [Categoría  ▾] [igual a    ▾] [__________ ▾]           [Quitar]      │
│   [+ Añadir condición]                                                  │
│                                                                         │
│  Niveles                                                                │
│   1. Resuelve [Rol ▾][__________ ▾]  Cuórum [Cualquiera ▾]  SLA [__] h │
│   2. Resuelve [Rol ▾][__________ ▾]  Cuórum [N de M ▾] N[_]  SLA [__] h│
│   [+ Añadir nivel]                                                      │
│                                                                         │
│  [+ Añadir regla]        Varias reglas equivalen a «o»                  │
│                                                                         │
│ ── Simulación ────────────────────────────────────────────────────────  │
│  Probar con un documento de ejemplo             [Simular]               │
│  → Requiere 2 niveles. Campos de la huella: monto, categoría.           │
└────────────────────────────────────────────────────────────────────────┘
```

- Los campos de umbral están **vacíos**: KONTROL no entrega valores (P8, CL-045-12).
- La simulación (FR-045-008) permite verificar antes de activar, sin crear solicitudes.
- Protección de cambios sin guardar (Vol. 2 §2).

## WF-045-06 · Historial (panel embebido)

Reutilizable desde cualquier documento; no es una ruta propia.

```
── Aprobaciones ──────────────────────────────────────────────────────────
 Solicitud #2 · Aprobada · Política Compras v3
   ✓ Nivel 1 … «Revisado contra presupuesto»
   ✓ Nivel 2 … · por delegación de …
 Solicitud #1 · Devuelta · Política Compras v3
   ↩ Nivel 1 … «Falta centro de costo»
```

Muestra la cadena completa incluidas las solicitudes encadenadas por devolución (FR-045-030) y la
delegación con la que se ejerció cada decisión (FR-045-045).

## Estados obligatorios

Loading · Ready · Empty · Forbidden · NotFound · Error, con los componentes compartidos (Vol. 2 §2).

Vacío de la bandeja: «No tienes aprobaciones pendientes» — no una tabla vacía.
