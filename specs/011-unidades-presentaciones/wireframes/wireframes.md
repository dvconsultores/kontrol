# WIREFRAMES — SPEC 011

Principio de estas pantallas: **una conversión mal entendida se configura mal.**
La interfaz no muestra «Factor = 100»; muestra qué significa (FR-011-092).

---

## W-011-01 · Unidades de medida · `/maestros/unidades`

```
┌──────────────────────────────────────────────────────────────────┐
│ Maestros › Unidades de medida                                    │
│ Unidades de medida                                    [+ Nueva]  │
│ Las que usa su empresa, más el catálogo estándar de la plataforma│
├──────────────────────────────────────────────────────────────────┤
│ Buscar [____________]  Dimensión [Todas ▾]  Ámbito [Todos ▾]     │
├──────────────────────────────────────────────────────────────────┤
│ Código  Nombre      Símbolo  Dimensión  Decimales  Ámbito  Acc.  │
│ UND     Unidad      und      Cantidad   0          Global    👁   │
│ KG      Kilogramo   kg       Peso       3          Global    👁   │
│ SACO    Saco        saco     Peso       2          Empresa  ✎ ⏻ 🗑│
├──────────────────────────────────────────────────────────────────┤
│                                        ‹ 1 2 3 ›  30 registros   │
└──────────────────────────────────────────────────────────────────┘
```

- Las globales muestran solo **ver**: una empresa no las edita (`UOM_GLOBAL_READ_ONLY`).
- La lista **nace vacía** en una instalación nueva: KONTROL no entrega unidades.
- `Decimales` se muestra porque es lo que decide si la unidad admite fracciones —
  y es dato, no regla codificada.

## W-011-02 · Alta de unidad

```
┌──────────────────────────────────────────────────────────────────┐
│ Nueva unidad de medida                                           │
├──────────────────────────────────────────────────────────────────┤
│ Código *      [________]     Nombre *   [________________]       │
│ Símbolo *     [______]       Dimensión* [Cantidad        ▾]      │
│                                                                  │
│ Decimales *   [__]           Redondeo * [Medio hacia arriba ▾]   │
│   ⓘ Cuántos decimales admite. 0 = no admite fracciones.          │
│                                                                  │
│                                   [ Cancelar ]  [ Guardar ]      │
└──────────────────────────────────────────────────────────────────┘
```

Numéricos **vacíos** al inicio, sin `0` precargado (FR-011-095).

## W-011-03 · Presentaciones del producto · `/maestros/productos/{id}/presentaciones`

**Página completa con URL propia**, no modal (P18, FR-011-091).

```
┌──────────────────────────────────────────────────────────────────┐
│ Maestros › Productos › TOR-X › Presentaciones                    │
│ TORNILLO X                                        [+ Presentación]│
│ Unidad base: UND (Unidad)                                        │
├──────────────────────────────────────────────────────────────────┤
│ Código  Nombre        Equivale a          Usos          Estado   │
│ BOLSA   Bolsa         20 UND              Venta         Activa ✎ │
│ CAJA    Caja          100 UND              Compra,Venta Activa ✎ │
│ PALLET  Pallet        2.000 UND            Compra       Activa ✎ │
├──────────────────────────────────────────────────────────────────┤
│  ⓘ Este producto se controla en UND. Las presentaciones son      │
│    formas de comprarlo o venderlo, no productos distintos.       │
└──────────────────────────────────────────────────────────────────┘
```

- La columna dice **«Equivale a 100 UND»**, no «Factor 100». Es la diferencia
  entre entenderlo y adivinarlo.
- El aviso al pie desactiva de entrada la confusión presentación/SKU (§16).
- Un producto **sin presentaciones** muestra la pantalla vacía con una sola línea:
  *«Este producto se maneja en UND. No necesita presentaciones.»* No se le fuerza
  a crear una presentación «Unidad» (FR-011-024, FR-011-097).

## W-011-04 · Definir presentación y factor

```
┌──────────────────────────────────────────────────────────────────┐
│ Nueva presentación de TORNILLO X                                 │
├──────────────────────────────────────────────────────────────────┤
│ Código *  [CAJA____]       Nombre *  [Caja______________]        │
│                                                                  │
│ ── Equivalencia ───────────────────────────────────────────      │
│   Una  CAJA  equivale a  [______] UND                            │
│                          └ obligatorio, mayor que cero           │
│                                                                  │
│   Vigente desde * [2026-01-01]                                   │
│                                                                  │
│   ┌ Vista previa ─────────────────────────────────────┐          │
│   │  10 CAJAS  =  1.000 UND                           │          │
│   └───────────────────────────────────────────────────┘          │
│                                                                  │
│ ── Se puede usar en ───────────────────────────────────────      │
│   [x] Compras   [x] Ventas   [ ] Almacenamiento  [x] Despacho    │
│                                                                  │
│                                   [ Cancelar ]  [ Guardar ]      │
└──────────────────────────────────────────────────────────────────┘
```

- La frase **«Una CAJA equivale a ___ UND»** es el formulario: el usuario no
  rellena un factor abstracto, completa una oración.
- La vista previa se actualiza al teclear y es **informativa**: el backend
  recalcula al guardar (FR-011-093, FR-011-044).
- Si el factor produce fracciones en la unidad base, aparece un aviso que exige
  marcarlo explícitamente; el sistema no redondea en silencio (R-D0-09-5).

## W-011-05 · Historial de versiones del factor

```
┌──────────────────────────────────────────────────────────────────┐
│ CAJA de TORNILLO X · Historial de equivalencias                  │
├──────────────────────────────────────────────────────────────────┤
│ Vigente desde  Hasta        Equivale a   Estado    En uso        │
│ 2026-06-01     —            120 UND      Vigente   Sí            │
│ 2024-01-01     2026-05-31   100 UND      Cerrada   Sí      🔒    │
├──────────────────────────────────────────────────────────────────┤
│  ⓘ Las equivalencias cerradas no se editan ni se borran: los     │
│    documentos emitidos con ellas siguen significando lo mismo.   │
│    Para corregir, cree una equivalencia nueva.                   │
│                                        [+ Nueva equivalencia]    │
└──────────────────────────────────────────────────────────────────┘
```

El candado no es decorativo: la API **no expone** edición de versión
(FR-011-094, FR-011-036).

## W-011-06 · Línea de documento con unidad — contrato visual

011 **no** implementa estas pantallas; define cómo deberán comportarse las de las
Specs consumidoras (§39).

```
│ Producto      Presentación   Cantidad   Equivale a               │
│ TORNILLO X    [Caja      ▾]  [   10  ]  1.000 UND                │
│                                          └ calculado por el       │
│                                            servidor al guardar    │
```

En un documento **emitido**, la presentación deja de ser editable y la
equivalencia muestra el valor **congelado**, no el vigente (FR-011-055).

## W-011-07 · Bloqueo de la unidad base

```
┌──────────────────────────────────────────────────────────────────┐
│ TORNILLO X · Unidad base                                         │
│   Unidad base:  UND                              [ Cambiar ]     │
│                                                   └ deshabilitado│
│  ⓘ No se puede cambiar: este producto tiene 1.240 movimientos    │
│    registrados. Cambiar la unidad base reinterpretaría todas     │
│    las cantidades históricas.                                    │
└──────────────────────────────────────────────────────────────────┘
```

El motivo y el recuento los **devuelve el backend** en `reason` y
`dependencies`; la interfaz no redacta la explicación ni decide el bloqueo
(P6, FR-011-083).
