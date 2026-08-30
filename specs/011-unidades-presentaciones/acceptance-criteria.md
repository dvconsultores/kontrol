# CRITERIOS DE ACEPTACIÓN — SPEC 011

Toda ejecución sobre **PostgreSQL 18.x** (P21).

## AC-011-01 · Catálogo de unidades vacío
**Dado** una instalación nueva
**Cuando** consulto las unidades de medida
**Entonces** la lista está **vacía**: KONTROL no entrega `UND`, `KG` ni ninguna otra.

## AC-011-02 · Unidad global y de empresa
**Dado** una unidad global `UND` y una unidad de empresa `SACO`
**Entonces** la empresa ve ambas
**Y** editar la global se rechaza con `UOM_GLOBAL_READ_ONLY`
**Y** puede existir una unidad de empresa con el mismo código que una global.

## AC-011-03 · Conversión física solo dentro de la dimensión
**Cuando** declaro `KG → 1000 G`
**Entonces** se acepta
**Cuando** declaro `KG → L`
**Entonces** 422 `UOM_DIMENSION_MISMATCH`.

## AC-011-04 · Unidad base obligatoria en inventariables
**Cuando** creo un producto sin unidad base
**Entonces** 422 `BASE_UNIT_REQUIRED`
**Cuando** creo un **servicio** sin unidad base
**Entonces** se acepta.

## AC-011-05 · Producto simple sin presentaciones
**Dado** un producto con unidad base `UND` y sin presentaciones
**Cuando** registro una cantidad de 7
**Entonces** funciona, con `presentation_id` nulo, factor 1 y `base_quantity` 7
**Y** la interfaz **no** exige crear una presentación «Unidad».

## AC-011-06 · Producto complejo
**Dado** `UND` base, con `BOLSA = 20`, `CAJA = 100` y `PALLET = 2000`
**Cuando** registro 5 BOLSAS
**Entonces** `base_quantity` es 100
**Y** las tres presentaciones coexisten sin crear productos distintos.

## AC-011-07 · Factor decimal sin error de coma flotante
**Dado** unidad base `KG` y presentación `SACO = 25.5`
**Cuando** registro 3 SACOS
**Entonces** `base_quantity` es exactamente `76.500000`
**Y** ninguna columna implicada es `Float`.

## AC-011-08 · Cantidad decimal
**Entonces** 2,75 metros, 1,5 kg y 0,750 litros se registran sin pérdida.

## AC-011-09 · Factor inválido
**Cuando** declaro un factor 0 o negativo
**Entonces** 422 `FACTOR_INVALID`, y la base de datos también lo rechaza.

## AC-011-10 · Cambiar el factor crea versión
**Dado** `CAJA = 100` vigente
**Cuando** declaro `CAJA = 120` desde una fecha
**Entonces** se crea una **versión nueva** y la anterior se cierra
**Y** no existe endpoint que edite la versión anterior.

## AC-011-11 · El histórico no cambia — el corazón de la Spec
**Dado** una compra de 10 CAJAS emitida con `CAJA = 100`, es decir 1.000 UND
**Cuando** el factor pasa a 120
**Entonces** la compra sigue valiendo **1.000 UND**, no 1.200
**Y** su `conversion_factor_snapshot` sigue siendo 100
**Y** ningún saldo histórico se recalcula.

## AC-011-12 · Sin versiones solapadas
**Cuando** intento crear dos versiones vigentes del mismo par producto-presentación en fechas que se solapan
**Entonces** 409 `PRESENTATION_VERSION_OVERLAP`
**Y** dos peticiones **simultáneas** producen una sola versión abierta.

## AC-011-13 · Resolución por fecha
**Dado** `CAJA = 100` hasta el 31-05 y `CAJA = 120` desde el 01-06
**Cuando** resuelvo con fecha 15-05
**Entonces** obtengo 100
**Cuando** resuelvo con fecha 15-06
**Entonces** obtengo 120
**Cuando** resuelvo con una fecha anterior a toda versión
**Entonces** 422 `CONVERSION_NOT_RESOLVABLE`; no se inventa un factor.

## AC-011-14 · La fecha efectiva es la del documento
**Dado** una factura con fecha 01-06 registrada el 05-06, y un cambio de factor el 03-06
**Entonces** se aplica el factor vigente el **01-06**.

## AC-011-15 · Snapshot al emitir; recálculo mientras es borrador
**Dado** un borrador con `CAJA = 100`
**Cuando** se activa `CAJA = 120` y el documento **sigue en borrador**
**Entonces** al recalcularlo usa 120
**Cuando** el documento se emite
**Entonces** el factor queda congelado y no vuelve a cambiar jamás.

## AC-011-16 · Cambio de presentación en línea emitida
**Cuando** cambio la presentación de una línea de un documento emitido
**Entonces** 409 `SNAPSHOT_IMMUTABLE`
**Cuando** el documento es editable
**Entonces** se permite y `base_quantity` se recalcula.

## AC-011-17 · Reimpresión fiel
**Cuando** reimprimo una factura de hace dos años
**Entonces** muestra la cantidad, el símbolo de unidad y la etiqueta de presentación **del snapshot**
**Y** no se consulta ni una sola vez el maestro de conversiones.

## AC-011-18 · El backend es la autoridad
**Cuando** envío una `base_quantity` distinta de la correcta
**Entonces** el backend la **recalcula** e ignora la enviada
**Y** el valor almacenado es el del servidor.

## AC-011-19 · Redondeo en un solo lugar
**Dado** una unidad base con 0 decimales
**Cuando** una conversión produce fracciones
**Entonces** se aplica el `rounding_mode` declarado
**Y** frontend, backend y base de datos coinciden en el resultado
**Y** si la presentación no declaró `exact_in_base = false`, se rechaza con `CONVERSION_NOT_EXACT`.

## AC-011-20 · Unidad base inmutable con historial
**Dado** un producto con movimientos
**Cuando** intento cambiar su unidad base
**Entonces** 409 `BASE_UNIT_LOCKED`, con el recuento de movimientos en `dependencies`
**Cuando** el producto no tiene movimientos
**Entonces** el cambio se permite y queda auditado.

## AC-011-21 · Borrado protegido
**Cuando** intento borrar una unidad o una presentación referenciada por alguna línea
**Entonces** 409 `UOM_IN_USE` / `PRESENTATION_IN_USE`
**Y** `allowed_actions` ofrece `deactivate`
**Y** desactivar y reactivar funcionan y quedan auditados.

## AC-011-22 · Versión en uso inmutable
**Cuando** intento editar o borrar una versión referenciada por un snapshot
**Entonces** 409 `PRESENTATION_VERSION_IMMUTABLE`.

## AC-011-23 · Las 17 tablas conservan la semántica
**Cuando** inspecciono las 17 tablas `MUST_HAVE_NOW`
**Entonces** todas tienen `uom_id`, `presentation_id`, `conversion_factor_snapshot`, `base_quantity` y `uom_source`
**Y** `inventory_balances`, `cost_layers` y `triple_matches` **no** los tienen, por diseño.

## AC-011-24 · Ningún `Float`
**Cuando** busco columnas de cantidad o factor de tipo `Float`
**Entonces** hay **0** en el esquema, frente a las 31 de partida.

## AC-011-25 · Coherencia aritmética
**Entonces** para toda línea capturada se cumple
`base_quantity = quantity × conversion_factor_snapshot`, con el redondeo declarado.

## AC-011-26 · Backfill · clase determinista
**Dado** líneas cuyo producto declara unidad base
**Cuando** se ejecuta el backfill
**Entonces** reciben esa unidad, factor 1 y `uom_source = LEGACY_ASSUMED_BASE`
**Y** la `quantity` original **no se modifica**.

## AC-011-27 · Backfill · clase reconstruible
**Dado** un producto sin unidad base pero con una **única** unidad en sus movimientos
**Entonces** se asigna esa unidad con `uom_source = LEGACY_RECONSTRUCTED`
**Y** el reporte registra la regla concreta que la produjo.

## AC-011-28 · Backfill · clase ambigua no se adivina
**Dado** un producto sin unidad base y con **dos** unidades distintas en su evidencia
**Entonces** la línea queda con `uom_id` nulo y `uom_source = LEGACY_UNRESOLVED`
**Y** **no** se le asigna la unidad más frecuente
**Y** no entra en ningún cálculo de saldo base.

## AC-011-29 · Backfill · fiscal irreconstruible no se toca
**Dado** una línea de factura emitida que resulta ambigua
**Entonces** **ninguna** columna de esa línea se escribe
**Y** se marca `LEGACY_UNVERSIONED` y se registra la incidencia
**Y** si el recuento supera el umbral, la migración **aborta** sin aplicar nada.

## AC-011-30 · Reporte de backfill
**Entonces** el reporte trae los once recuentos
**Y** se cumple `deterministic + reconstructed + ambiguous + non_reconstructible = total_lines_checked`
**Y** `assigned_presentation` es **0**: ninguna presentación pudo existir
**Y** no contiene importes, nombres de tercero ni datos comerciales.

## AC-011-31 · Conversión de tipo reportada
**Cuando** las 31 columnas pasan de `Float` a `NUMERIC`
**Entonces** se reporta toda fila cuyo valor cambie
**Y** ninguna se redondea en silencio.

## AC-011-32 · Migración repetida
**Cuando** se reejecuta el backfill sobre una base ya migrada
**Entonces** es idempotente: no reclasifica ni reescribe.

## AC-011-33 · Aislamiento multiempresa
**Dado** un usuario de la empresa A
**Cuando** consulta, edita o referencia presentaciones o unidades de empresa de B
**Entonces** no las ve y la referencia se rechaza
**Y** no puede asociar un producto de A con una presentación de B.

## AC-011-34 · Autoridad única de conversión
**Cuando** busco cálculos de conversión en el código
**Entonces** existe **un solo** lugar donde se convierte
**Y** ningún módulo de compras, ventas, inventario o picking lo replica.

## AC-011-35 · Sin negocio en el código
**Cuando** busco nombres de unidad o presentación codificados
**Entonces** hay **0** coincidencias: todo procede de datos.

## AC-011-36 · Rendimiento sin N+1
**Dado** un documento de 1.000 líneas
**Cuando** se resuelven sus conversiones
**Entonces** el número de consultas es constante, no proporcional a las líneas.

## AC-011-37 · La caché no altera el histórico
**Cuando** se activa una versión nueva del factor
**Entonces** ninguna petición posterior devuelve el factor anterior desde caché
**Y** ningún snapshot ya escrito cambia.

## AC-011-38 · Accesibilidad y responsive
**Entonces** las pantallas de 011 pasan axe WCAG 2.2 AA en Chromium, Firefox y WebKit,
son operables solo con teclado y no producen scroll horizontal entre 320 y 1920 px.

## AC-011-39 · Auditoría
**Entonces** quedan auditados: alta, edición, activación y desactivación de unidad y presentación,
creación de versión, y los **intentos denegados** de cambio destructivo.

## AC-011-40 · Concurrencia optimista
**Dado** dos ediciones de la misma unidad con la misma versión
**Entonces** una prospera y la otra recibe 409 `VERSION_CONFLICT`.
