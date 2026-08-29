# POLÍTICA DE MUTABILIDAD ESTRUCTURAL

**Spec 008 · Control 2 del Gate pre-implementación · Normativo**

Define qué puede cambiarse en la estructura física de un almacén, cuándo, y qué
está prohibido. Complementa R-008-1 (los tramos intermedios son opcionales por
almacén) respondiendo la pregunta que R-008-1 dejaba abierta: **qué ocurre
después de que el almacén empieza a operar.**

---

## 1. El problema

Un almacén se configura como `ZONE → AISLE → RACK → LEVEL → LOCATION`. Se crean
zonas, pasillos, racks, niveles y ubicaciones. Entra stock. Se registran
movimientos, ajustes y conteos. Meses después un administrador edita
`structure_levels` y retira `RACK`.

Eso **no** es un `UPDATE` de configuración. Es una reinterpretación retroactiva
del significado de cada ubicación del almacén y de cada movimiento que la
referencia. Rompe la cadena, la trazabilidad, las rutas de recorrido y el
histórico.

> **R-008-6.** `structure_levels` **no** es un campo de configuración editable.
> Es una declaración estructural cuyo régimen de cambio depende de si existe
> estructura dependiente.

---

## 2. Los dos regímenes

### 2.1 `INITIAL` — configuración inicial

**Condición:** el almacén no tiene **ningún** nodo estructural creado, ninguna
ubicación, y por tanto ningún dato dependiente.

`structure_levels` puede modificarse libremente dentro de las reglas de validez
del propio modelo: los tramos declarados mantienen el orden canónico
`ZONE → AISLE → RACK → LEVEL`, se pueden añadir y retirar, y el almacén puede
pasar de simple a complejo y a la inversa.

### 2.2 `OPERATIONAL` — configuración operativa

**Condición:** existe al menos un nodo estructural o una ubicación en el almacén.

El almacén entra en este régimen **de forma irreversible** en el momento en que
se crea su primer nodo o su primera ubicación. No se sale de él por borrar los
datos: el régimen refleja que el almacén ha existido operativamente.

En este régimen, sobre un **tramo utilizado** están prohibidos:

| Operación prohibida | Por qué |
|---|---|
| **Eliminar** el tramo | Deja huérfano cada nodo de ese tramo y desconecta la cadena de sus ubicaciones |
| **Reordenar** los tramos | Cambia el significado de las relaciones padre-hijo ya establecidas |
| **Cambiar la semántica** del tramo | Un rack que pasa a significar «nivel» reescribe retroactivamente el histórico |
| **Colapsar** dos tramos en uno | Fusión de datos sin regla demostrable — es invención, no migración |

Un tramo se considera **utilizado** cuando existe al menos un nodo de ese tramo
en el almacén, activo o inactivo. Un tramo declarado pero sin ningún nodo creado
**sí** puede retirarse: no hay nada que romper.

> **R-008-7.** Añadir un tramo **no utilizado** al final de la cadena declarada
> se permite en régimen operativo únicamente si el almacén no tiene ubicaciones;
> con ubicaciones existentes, añadir profundidad dejaría cadenas incompletas y se
> rechaza. Esa transformación pertenece al proceso de reestructuración (§6).

---

## 3. Cambio de metadata frente a cambio estructural

La distinción decide qué controles aplican. **No** es la misma operación editar
el nombre de una zona que cambiar su padre.

### 3.1 Metadata — editable en ambos regímenes

Nombre · descripción · etiquetas · notas · atributos de capacidad y restricción
no estructurales · `sequence` **dentro del mismo padre** (reordenar hermanos no
altera la jerarquía, solo el recorrido) · estado de activación según §5.

Controles: permiso, auditoría, control de concurrencia optimista.

### 3.2 Estructural — sujeto a los controles estrictos

`structure_levels` del almacén · el padre de cualquier nodo · el tramo al que
pertenece un nodo · la profundidad de la cadena · retirar, reordenar o colapsar
tramos utilizados · convertir un almacén complejo en simple o a la inversa una
vez operativo.

Controles: permiso, auditoría, control de concurrencia, **y** las prohibiciones
de §2.2 y §5.

> La etiqueta derivada de una ubicación cambia cuando se renombra una zona. Eso
> es correcto y esperado (AC-008-07): la etiqueta es presentación, no dato. Un
> cambio de nombre **no** es un cambio estructural.

---

## 4. Bloqueo — backend es la autoridad

Cuando existe estructura dependiente, **el backend impide la operación**. No se
confía en deshabilitar controles visuales: el frontend refleja el bloqueo, no lo
produce (P6).

| Código | Cuándo | HTTP |
|---|---|---|
| `STRUCTURE_LEVEL_IN_USE` | Se intenta eliminar un tramo con nodos existentes | 409 |
| `STRUCTURE_REORDER_FORBIDDEN` | Se intenta reordenar tramos utilizados | 409 |
| `STRUCTURE_DEPTH_CHANGE_FORBIDDEN` | Se intenta añadir profundidad con ubicaciones existentes | 409 |
| `NODE_HAS_ACTIVE_CHILDREN` | Se desactiva un nodo con descendientes activos | 409 |
| `NODE_HAS_HISTORY` | Se borra un nodo con histórico | 409 |
| `LOCATION_HAS_HISTORY` | Se borra o reubica una ubicación con histórico | 409 |

Toda respuesta de bloqueo incluye:

- **`code`** — estable, del cuadro anterior.
- **`reason`** — qué regla lo impide, en lenguaje del usuario.
- **`dependencies`** — qué existe concretamente que lo impide: tramo, recuento de
  nodos, ejemplos identificables y acotados.
- **`allowed_actions`** — qué **sí** puede hacer el usuario en su lugar
  (típicamente `deactivate` en vez de `delete`).

El frontend muestra el motivo y las dependencias. Nunca presenta un control
habilitado que el backend vaya a rechazar, ni oculta la razón del rechazo.

---

## 5. Nodos con histórico — política por entidad

Aplica a `Warehouse`, `WarehouseZone`, `WarehouseAisle`, `WarehouseRack`,
`WarehouseLevel` y `WarehouseLocation`.

Un nodo tiene **histórico** si existe al menos uno de: stock, movimiento de
inventario, línea de ajuste, línea de conteo, reserva, referencia desde un
documento, o cualquier descendiente que a su vez tenga histórico.

| Situación | Borrado físico | Desactivación |
|---|---|---|
| Sin descendientes y sin histórico | **Permitido** | Permitido |
| Con descendientes activos | Rechazado — `NODE_HAS_ACTIVE_CHILDREN` | Rechazado — desactivar primero los descendientes |
| Con descendientes, todos inactivos, sin histórico | Rechazado — desactivar | **Permitido** |
| Con histórico, propio o heredado | **Rechazado — `NODE_HAS_HISTORY`** | **Permitido — es la vía correcta** |

Reglas transversales:

> **R-008-8.** **Ningún** `cascade` destructivo en la jerarquía física. El
> `cascade="all, delete-orphan"` que hoy existe en `Warehouse.locations` se
> retira en F1: borrar un almacén nunca puede destruir ubicaciones con historial.

> **R-008-9.** **No hay desactivación en cascada silenciosa.** Desactivar un
> nodo con descendientes activos se rechaza enumerándolos; el usuario decide y
> ejecuta, y cada desactivación queda auditada por separado.

> **R-008-10.** La desactivación es **reversible** y auditada en ambos sentidos.
> El borrado es irreversible, y por eso solo se permite donde no destruye nada.

Reubicación de una ubicación (cambiar su padre estructural): permitida solo si
está vacía y sin histórico; con saldo o movimientos se rechaza con
`LOCATION_HAS_HISTORY`. Mover mercancía es un **movimiento**, no una edición de
maestro — ya recogido en FR-008-056 y AC-008-14.

---

## 6. Reestructuración futura — fuera del alcance de 008

Eliminar un tramo utilizado, fusionar zonas, mover racks entre pasillos, cambiar
la profundidad estructural o convertir un almacén complejo en simple son
operaciones legítimas que KONTROL puede necesitar. **No se implementan en 008.**

Cuando se necesiten, deberán realizarse mediante un **proceso controlado de
reestructuración** con su propia especificación, que como mínimo contemple:
simulación previa con impacto calculado, aprobación mediante el motor de la Spec
045, ejecución transaccional, conservación íntegra del histórico bajo su
significado original, y reversión.

**Lo que 008 sí hace, y es su responsabilidad completa:**

1. **Impedir** que esos cambios ocurran hoy por edición simple.
2. **Conservar** el histórico intacto.
3. **Dejar la arquitectura preparada**: los tramos son entidades con identidad
   propia y `sequence` explícita, no columnas de texto, de modo que una
   reestructuración futura tenga sobre qué operar.

Este es un límite de alcance deliberado, no una omisión: implementar la
reestructuración dentro de 008 sería scope creep sobre una Spec ya aprobada.

---

## 7. Qué se prueba

Los ocho casos A..H del Control 2 están en `test-plan.md` §10.

| Qué | Dónde |
|---|---|
| Implementación de las reglas | T-008-036a..036h (F3) |
| Pruebas de los casos A..H | T-008-068a..068d (F5) |
| Prueba de que el bloqueo es del backend | T-008-068e (F5) |
| Criterios de aceptación | AC-008-31 a AC-008-40 |
