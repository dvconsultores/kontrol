# CRITERIOS DE ACEPTACIÓN — SPEC 008

Toda ejecución sobre **PostgreSQL 18.x** (P21).

## AC-008-01 · Almacén simple funciona sin tramos
**Dado** un almacén con `structure_levels` vacío
**Cuando** creo cinco ubicaciones directamente
**Entonces** se crean sin exigir zona, pasillo, rack ni nivel
**Y** la pantalla no muestra pestañas de tramos vacías.

## AC-008-02 · Almacén complejo con la cadena completa
**Dado** un almacén que declara los cuatro tramos
**Cuando** creo zona → pasillo → rack → nivel → ubicación
**Entonces** la ubicación conoce su cadena y su etiqueta derivada la refleja.

## AC-008-03 · Cadena incoherente rechazada en base de datos
**Cuando** creo una ubicación cuyo rack pertenece a otro pasillo
**Entonces** 422 `HIERARCHY_INCOHERENT`
**Y** la inserción directa en base de datos también falla.

## AC-008-04 · Tramo de otro almacén rechazado
**Cuando** asigno a una ubicación una zona de otro almacén
**Entonces** 422 `HIERARCHY_CROSS_WAREHOUSE`.

## AC-008-05 · Aislamiento multiempresa
**Dado** un usuario de la empresa A
**Cuando** lista, consulta o referencia ubicaciones de B
**Entonces** no las ve y la referencia se rechaza con 403.

## AC-008-06 · Código único por almacén
**Cuando** creo dos ubicaciones con el mismo código en un almacén
**Entonces** 409 `LOCATION_CODE_DUPLICATE`
**Y** dos peticiones **simultáneas** producen una sola ubicación.

## AC-008-07 · Etiqueta derivada, no persistida
**Dado** una ubicación en la zona «Alta rotación»
**Cuando** renombro la zona a «Zona A»
**Entonces** la etiqueta cambia sin tocar la ubicación
**Y** no existe ninguna columna con la etiqueta.

## AC-008-08 · Orden físico determinista
**Dado** ubicaciones con y sin zona
**Cuando** consulto `/locations/ordered` dos veces
**Entonces** el orden es idéntico, total y sigue
`(zona, pasillo, rack, nivel, ubicación, código)` con `NULLS FIRST`.

## AC-008-09 · `FULL` no se persiste
**Cuando** busco un estado `FULL` en el modelo
**Entonces** no existe: los estados son `ACTIVE`, `INACTIVE`, `BLOCKED`, `MAINTENANCE`.

## AC-008-10 · Estado de ubicación ≠ estado de mercancía
**Dado** una ubicación con existencia disponible
**Cuando** la bloqueo
**Entonces** la ubicación queda `BLOCKED`
**Y** el estado de la mercancía **no cambia**, y sigue consultándose.

## AC-008-11 · Borrado protegido
**Dado** una ubicación con movimientos
**Cuando** intento borrarla
**Entonces** 409 `LOCATION_HAS_HISTORY`
**Y** `can_delete` es `false` y `allowed_actions` no ofrece `delete`.

## AC-008-12 · Desactivación reversible
**Cuando** desactivo y reactivo una ubicación
**Entonces** ambas operaciones funcionan y quedan auditadas.

## AC-008-13 · Sin desactivación en cascada silenciosa
**Cuando** desactivo una zona con pasillos activos
**Entonces** 409 `NODE_HAS_ACTIVE_CHILDREN` con la lista de lo que lo impide.

## AC-008-14 · Reubicación con historial rechazada
**Dado** una ubicación con saldo
**Cuando** cambio su zona
**Entonces** 409 `LOCATION_HAS_HISTORY`
**Cuando** la ubicación está vacía y sin historial
**Entonces** el cambio se permite y se audita.

## AC-008-15 · Sin cascade delete-orphan
**Cuando** borro un almacén sin ubicaciones
**Entonces** funciona
**Cuando** tiene ubicaciones
**Entonces** se rechaza y **ninguna** ubicación se borra.

## AC-008-16 · Las dos referencias son FK reales
**Cuando** inserto un saldo o una línea de conteo con una ubicación inexistente
**Entonces** PostgreSQL lo rechaza con violación de clave foránea.

## AC-008-17 · Migración conserva el texto original
**Dado** ubicaciones con `zone="A "`, `aisle="P3"`
**Cuando** se aplica `0018`
**Entonces** `legacy_path` conserva el texto
**Y** **no** se crea ninguna zona ni pasillo automáticamente.

## AC-008-18 · La migración actúa según la clase de la huérfana
**Dado** un saldo que apunta a una ubicación inexistente
**Cuando** se aplica `0018`
**Entonces** la fila se **clasifica** antes de tocarse
**Y** si es reconstruible de forma unívoca, se repara
**Y** si no lo es pero el nulo es legítimo, se anula conservando `legacy_location_id` y registrando la incidencia
**Y** si es crítica, la migración **se bloquea** en lugar de perder el dato
**Y** en ningún caso se anula una referencia solo para que la migración termine.

> Este criterio **sustituye** al enunciado anterior, que permitía anular y
> continuar sin distinguir la criticidad. Ver `migration-0018-policy.md`.

## AC-008-19 · La estructura no se carga entera
**Dado** un almacén con 50.000 ubicaciones
**Cuando** consulto `/structure` sin parámetros
**Entonces** no se devuelve ninguna ubicación
**Y** con `depth=locations` vienen paginadas.

## AC-008-20 · Rendimiento de búsqueda
**Dado** 50.000 ubicaciones
**Cuando** busco por código
**Entonces** P95 ≤ 200 ms.

## AC-008-21 · `allowed_actions` en backend
**Cuando** un usuario sin permiso consulta un nodo
**Entonces** `allowed_actions` es `[]`
**Y** la operación directa por API devuelve 403.

## AC-008-22 · Nada de negocio en el código
**Cuando** busco nombres de zona, estructura o reglas de cliente en el módulo
**Entonces** no hay coincidencias: todo procede de datos.

## AC-008-23 · Creación masiva con vista previa
**Cuando** solicito 40 ubicaciones por patrón
**Entonces** veo la vista previa y el aviso de las que ya existen **antes** de crear.

## AC-008-24 · Accesibilidad y responsive
**Entonces** las pantallas de 008 pasan axe WCAG 2.2 AA en Chromium, Firefox y
WebKit, son operables solo con teclado y no producen scroll horizontal entre
320 y 1920 px.

---

# CONTROL 1 — MIGRACIÓN `0018`

## AC-008-25 · Todas las referencias válidas
**Dado** una base pre-008 donde cada `location_id` apunta a una ubicación existente
**Cuando** se aplica `0018`
**Entonces** la migración **PASA**
**Y** el reporte da `valid_references = total_rows_checked`, `orphan_references = 0`,
`critical_orphans = 0`, `migration_blocked = false`
**Y** ninguna fila fue modificada.

## AC-008-26 · Huérfana reconstruible
**Dado** un saldo cuya referencia es inválida pero **una sola** ubicación la resuelve
de forma determinista según las fuentes admitidas
**Cuando** se aplica `0018`
**Entonces** la referencia queda **reparada**
**Y** `legacy_location_id` conserva el valor anterior
**Y** el reporte registra tabla, fila, valor anterior, valor nuevo y la regla aplicada
**Y** si hubiera **dos** candidatas, la fila **no** se repara: degrada a clase C o D.

## AC-008-27 · No reconstruible con nulo legítimo
**Dado** una línea de conteo con referencia inválida, saldo cero, sin movimientos, en
un almacén sin gestión de ubicaciones
**Cuando** se aplica `0018`
**Entonces** `location_id` queda `NULL`
**Y** `legacy_location_id` conserva el valor original
**Y** el reporte registra la incidencia con las tres condiciones evaluadas y el motivo
**Y** ningún total, Kardex, conteo cerrado ni cifra reportada cambia.

## AC-008-28 · Huérfana crítica bloquea la migración
**Dado** un saldo con cantidad distinta de cero cuya ubicación no existe y no puede
reconstruirse
**Cuando** se aplica `0018`
**Entonces** la migración **ABORTA** de forma controlada
**Y** `migration_blocked = true` y `critical_orphans ≥ 1`
**Y** el reporte completo identifica las filas críticas
**Y** **ninguna** escritura quedó aplicada: sin FK creadas, sin referencias anuladas,
sin `legacy_path` poblado.

## AC-008-29 · Migración repetida
**Dado** una base ya migrada por `0018`
**Cuando** se aplica `0018` de nuevo
**Entonces** no se reclasifica ni reescribe nada, no se duplica ni se pierde dato
**Y** el resultado es idéntico al de la primera ejecución.

## AC-008-30 · Upgrade desde base real pre-008 con datos
**Dado** una base con el esquema hasta `0016` y datos de inventario, compras, ventas y
conteos
**Cuando** se aplica `alembic upgrade head` sobre **PostgreSQL**
**Entonces** la cadena completa aplica
**Y** los recuentos de filas de las tablas de negocio no varían
**Y** `legacy_path` conserva el texto original de `zone`/`aisle`/`rack`
**Y** **no** se creó automáticamente ninguna zona, pasillo, rack ni nivel
**Y** el invariante del reporte se cumple:
`valid + reconstructed + nulled + critical = total_rows_checked`.

---

# CONTROL 2 — MUTABILIDAD ESTRUCTURAL

## AC-008-31 · Modificar `structure_levels` sin datos dependientes
**Dado** un almacén sin nodos y sin ubicaciones (régimen `INITIAL`)
**Cuando** cambio los tramos declarados dentro de las reglas de validez
**Entonces** se permite y queda auditado.

## AC-008-32 · Eliminar un tramo utilizado
**Dado** un almacén con zonas y racks creados
**Cuando** intento retirar `RACK` de `structure_levels`
**Entonces** 409 `STRUCTURE_LEVEL_IN_USE`
**Y** la respuesta incluye `reason`, `dependencies` con el recuento de racks y
`allowed_actions`
**Y** un tramo **declarado pero sin ningún nodo** sí puede retirarse.

## AC-008-33 · Reordenar tramos utilizados
**Cuando** intento alterar el orden de tramos que ya tienen nodos
**Entonces** 409 `STRUCTURE_REORDER_FORBIDDEN`
**Y** la jerarquía existente no cambia.

## AC-008-34 · Desactivar nodo sin dependencias
**Dado** una zona sin hijos activos
**Cuando** la desactivo y luego la reactivo
**Entonces** ambas operaciones se permiten y quedan auditadas por separado.

## AC-008-35 · Eliminar nodo con histórico
**Dado** un nodo con stock, movimiento, conteo o descendiente con histórico
**Cuando** intento borrarlo físicamente
**Entonces** 409 `NODE_HAS_HISTORY`
**Y** `allowed_actions` ofrece `deactivate`, no `delete`
**Y** aplica igual a `Warehouse`, `WarehouseZone`, `WarehouseAisle`,
`WarehouseRack`, `WarehouseLevel` y `WarehouseLocation`.

## AC-008-36 · Cambiar el padre de una ubicación con histórico
**Dado** una ubicación con saldo o movimientos
**Cuando** cambio su zona, pasillo, rack o nivel
**Entonces** 409 `LOCATION_HAS_HISTORY`
**Y** sin histórico y vacía, el cambio se permite y se audita como cambio de jerarquía.

## AC-008-37 · Almacén simple opera de extremo a extremo
**Dado** un almacén con `structure_levels` vacío
**Entonces** `Warehouse → Location` funciona completo: crear, listar, buscar,
desactivar y consultar orden físico, sin exigir ni mostrar tramo alguno.

## AC-008-38 · Almacén complejo opera de extremo a extremo
**Dado** un almacén que declara los cuatro tramos
**Entonces** la cadena completa funciona, la etiqueta derivada la refleja y el orden
físico recorre los cinco niveles de forma determinista.

## AC-008-39 · El bloqueo lo produce el backend
**Cuando** invoco por API una operación estructural prohibida, saltándome el frontend
**Entonces** el backend la rechaza igualmente con el mismo código
**Y** el bloqueo **no** depende de que el control visual esté deshabilitado.

## AC-008-40 · Sin cascade destructivo ni desactivación silenciosa
**Cuando** borro un almacén con ubicaciones
**Entonces** se rechaza y **ninguna** ubicación se borra
**Cuando** desactivo una zona con pasillos activos
**Entonces** 409 `NODE_HAS_ACTIVE_CHILDREN` enumerando lo que lo impide, y **nada**
se desactiva en cascada.
