# WIREFRAMES — SPEC 008

Estándar Maestro de Frontend, ADR-006, ADR-015 y P18: **pantallas completas con
URL propia**; modal solo para confirmación breve.

## Rutas

| Ruta | Pantalla | Permiso |
|---|---|---|
| `/organizacion/almacenes` | Almacenes (lista) | `organization:view` |
| `/organizacion/almacenes/nuevo` | Alta de almacén | `organization:create` |
| `/organizacion/almacenes/:id` | Detalle y estructura | `organization:view` |
| `/organizacion/almacenes/:id/editar` | Edición de almacén | `organization:edit` |
| `/organizacion/almacenes/:id/ubicaciones` | Ubicaciones del almacén | `organization:view` |
| `/organizacion/almacenes/:id/ubicaciones/masiva` | Creación por patrón | `organization:create` |
| `/organizacion/tipos-zona` · `/organizacion/tipos-ubicacion` | Catálogos | `organization:view` |

## Principio de UX: la estructura se adapta al almacén

El §36 del encargo advierte contra un árbol inusable. La respuesta no es un árbol
mejor: es **no mostrar lo que ese almacén no usa**.

```
structure_levels = {}                       → la pantalla muestra solo ubicaciones
structure_levels = {zone}                   → dos niveles de navegación
structure_levels = {zone,aisle,rack,level}  → cinco niveles con drill-down
```

Un almacén simple **nunca ve** pestañas de zonas, pasillos, racks y niveles vacías.

## WF-008-01 · Almacenes (lista)

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Inicio › Organización › Almacenes            [Empresa activa ▾] [+ Nuevo]│
│ Almacenes de la empresa. Un almacén sin sucursal es central.             │
│                                                                          │
│ [Buscar…]   Sucursal ▾   Estado ▾   ☐ Solo gestionados por ubicación     │
│ ┌────────┬────────────────┬───────────┬────────────┬──────────┬────────┐ │
│ │ Código │ Nombre         │ Sucursal  │ Estructura │ Ubicac.  │Acciones│ │
│ ├────────┼────────────────┼───────────┼────────────┼──────────┼────────┤ │
│ │ ALM-01 │ Principal      │ Valencia  │ Zona·Pas.  │   1.240  │  ⋯     │ │
│ │ ALM-02 │ Central        │ —         │ Simple     │      12  │  ⋯     │ │
│ └────────┴────────────────┴───────────┴────────────┴──────────┴────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

«Estructura» resume `structure_levels` en una palabra: el usuario ve de un
vistazo qué almacenes son simples y cuáles no.

## WF-008-02 · Alta y edición de almacén — pantalla completa

```
┌──────────────────────────────────────────────────────────────────────────┐
│ … › Almacenes › Nuevo                              [Cancelar] [Guardar]  │
│                                                                          │
│ ── Identificación ──────────────────────────────────────────────────────  │
│  Código *[__________]  Nombre *[____________________]                    │
│  Sucursal [Ninguna (central) ▾]   Tipo [Físico ▾]   Responsable [____]   │
│  Dirección [______________________________]                              │
│                                                                          │
│ ── Estructura física ───────────────────────────────────────────────────  │
│  ☑ Gestionar inventario por ubicación                                    │
│     Sin marcar, el inventario opera a nivel de almacén.                  │
│                                                                          │
│  Tramos que usa este almacén:                                            │
│   ☑ Zonas   ☑ Pasillos   ☐ Racks   ☐ Niveles                             │
│   Las ubicaciones son siempre obligatorias.                              │
│                                                                          │
│ ── Códigos de ubicación ────────────────────────────────────────────────  │
│  ( ) Manual — los escribe el usuario                                     │
│  (•) Generados — patrón [{zona}-{pasillo}-{secuencia}]                    │
└──────────────────────────────────────────────────────────────────────────┘
```

Los tramos desmarcados **desaparecen** de las pantallas siguientes. Protección de
cambios sin guardar activa (FR-008-076).

## WF-008-03 · Detalle del almacén y su estructura

```
┌──────────────────────────────────────────────────────────────────────────┐
│ … › Almacenes › ALM-01                        [Editar] [Desactivar]      │
│ Principal · Valencia · gestionado por ubicación · 1.240 ubicaciones      │
│                                                                          │
│ [ Zonas (4) ] [ Pasillos (18) ] [ Ubicaciones (1.240) ]                  │
│  ─────────────                                                           │
│ [Buscar zona…]                                        [+ Nueva zona]     │
│ ┌─────┬───────────────────┬──────────────────┬─────┬────────┬─────────┐  │
│ │ Ord.│ Código            │ Nombre           │Tipo │ Estado │ Acciones│  │
│ ├─────┼───────────────────┼──────────────────┼─────┼────────┼─────────┤  │
│ │  1  │ ZA                │ Alta rotación    │ Alta│ Activa │  ⋯      │  │
│ │  4  │ ZD                │ Incidencias      │ Inc.│ Activa │  ⋯      │  │
│ └─────┴───────────────────┴──────────────────┴─────┴────────┴─────────┘  │
│  Al abrir una zona se navega a sus pasillos, con breadcrumb.             │
└──────────────────────────────────────────────────────────────────────────┘
```

Las pestañas **solo muestran los tramos declarados**. Un almacén simple ve una
sola pestaña: Ubicaciones. «Ord.» es la secuencia física, editable en línea.

## WF-008-04 · Ubicaciones del almacén

```
┌──────────────────────────────────────────────────────────────────────────┐
│ … › ALM-01 › Ubicaciones                     [+ Nueva] [+ Creación masiva]│
│                                                                          │
│ [Buscar código o nombre…]  Zona ▾  Pasillo ▾  Tipo ▾  Estado ▾           │
│ ☐ Orden físico de recorrido                                              │
│ ┌──────────┬──────────────────────────────────┬────────┬────────┬──────┐ │
│ │ Código   │ Ubicación                        │ Tipo   │ Estado │Acc.  │ │
│ ├──────────┼──────────────────────────────────┼────────┼────────┼──────┤ │
│ │ A-0345   │ Alta rotación / P03              │ Almac. │ Activa │ ⋯    │ │
│ │ Q-0001   │ Incidencias                      │ Cuaren.│Bloquead│ ⋯    │ │
│ └──────────┴──────────────────────────────────┴────────┴────────┴──────┘ │
│                                        1-50 de 1.240   ‹ 1 2 3 … 25 ›    │
└──────────────────────────────────────────────────────────────────────────┘
```

La columna «Ubicación» es la **etiqueta derivada**, no un campo. La casilla
«Orden físico» cambia a `/locations/ordered`: es la vista que la Spec 031
consumirá, visible aquí para que el usuario compruebe que el recorrido es el real.

## WF-008-05 · Creación masiva por patrón

```
┌──────────────────────────────────────────────────────────────────────────┐
│ … › ALM-01 › Ubicaciones › Creación masiva          [Cancelar] [Crear]   │
│                                                                          │
│  Zona [Alta rotación ▾]   Pasillo [P03 ▾]                                │
│  Desde [1]  Hasta [40]   Tipo [Almacenamiento ▾]                         │
│                                                                          │
│  ── Vista previa ────────────────────────────────────────────────────────│
│   Se crearán 40 ubicaciones: ZA-P03-001 … ZA-P03-040                     │
│   ⚠ 3 códigos ya existen y se omitirán.                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

Vista previa **antes** de crear: 40 ubicaciones creadas por error se borran una a
una, y las que reciban movimientos ya no se podrán borrar.

## WF-008-06 · Confirmación (único modal admitido)

```
        ┌────────────────────────────────────────────┐
        │  Desactivar ubicación A-0345               │
        │                                            │
        │  Dejará de ofrecerse para nuevas           │
        │  operaciones. Su historial se conserva y   │
        │  puede reactivarse.                        │
        │                                            │
        │               [Cancelar]  [Desactivar]     │
        └────────────────────────────────────────────┘
```

Cuando la acción no procede, no hay modal: el botón no se ofrece porque
`allowed_actions` no lo incluye, y la interfaz explica por qué.

## Estados obligatorios

Loading · Ready · Empty · Forbidden · NotFound · Error, con los componentes
compartidos.

Vacíos con sentido, no tablas en blanco:
- Sin almacenes: «Aún no hay almacenes. Cree el primero para empezar a operar.»
- Sin zonas: «Este almacén no usa zonas. Actívelas en su configuración si las necesita.»
- Sin ubicaciones: «Sin ubicaciones. Créelas una a una o de forma masiva.»

## Responsive y accesibilidad

- 320-1920 px sin scroll horizontal; en móvil las tablas pasan a tarjetas.
- Zoom 125 % y 150 % sin pérdida de contenido.
- Navegación completa por teclado; foco visible; primer error enfocado.
- Toda acción de icono con `aria-label` y tooltip; iconos de Lucide React.
- Paginación desde 11 registros.

---

## W-008-07 · Bloqueo estructural — cómo se muestra

El frontend **refleja** el bloqueo del backend; no lo sustituye. Un control
deshabilitado sin explicación es peor que uno habilitado que falla: el usuario no
sabe qué le falta.

```
┌──────────────────────────────────────────────────────────────┐
│ Almacén Principal · Estructura                               │
├──────────────────────────────────────────────────────────────┤
│ Tramos declarados                                            │
│                                                              │
│  [✓] Zona      42 nodos     — en uso                         │
│  [✓] Pasillo  128 nodos     — en uso                         │
│  [✓] Rack      42 nodos     — en uso        ⚠ no se puede    │
│                                                 retirar      │
│  [ ] Nivel      0 nodos     — se puede retirar               │
│                                                              │
│  ⓘ Este almacén está en operación. Los tramos que ya tienen  │
│    nodos no pueden retirarse ni reordenarse: cambiarlos      │
│    reinterpretaría las ubicaciones y el historial existentes.│
│    Puede desactivar nodos que no use.                        │
│                                                              │
│                              [ Cancelar ]  [ Guardar ]       │
└──────────────────────────────────────────────────────────────┘
```

Reglas de la pantalla:

- El recuento de nodos por tramo se muestra **siempre**: es lo que explica el
  bloqueo sin que el usuario tenga que provocarlo.
- Un tramo con `0 nodos` sí se puede retirar, y la interfaz lo dice.
- En régimen `INITIAL` el aviso no aparece y todos los tramos son editables.
- Si el usuario fuerza la operación, el mensaje que se muestra es el `reason` y las
  `dependencies` que **devuelve el backend**, no un texto inventado por la UI.

## W-008-08 · Nodo con histórico — borrar frente a desactivar

```
┌──────────────────────────────────────────────────────────────┐
│ Zona · Alta rotación                                         │
├──────────────────────────────────────────────────────────────┤
│  Estado: Activa                                              │
│                                                              │
│  [ Editar ]  [ Desactivar ]  [ Eliminar ]                    │
│                                  └── deshabilitado           │
│                                                              │
│  ⓘ No se puede eliminar: 3 ubicaciones de esta zona tienen   │
│    movimientos registrados. Desactivarla la retira del uso   │
│    conservando el historial, y es reversible.                │
└──────────────────────────────────────────────────────────────┘
```

`allowed_actions` del backend decide qué botones se ofrecen. El motivo procede de
`reason` y `dependencies`. Desactivar se presenta como la **alternativa**, no como
un consuelo: es la operación correcta para un nodo con historial.
