# INVESTIGACIÓN — SPEC 008

## 1. Estado verificado del código

Inspección directa sobre `develop @ 92c93d5`, no lectura del GAP Analysis.

```
Warehouse   → existe: company_id, branch_id?, code, name, warehouse_type,
              policies JSON, StatusMixin
Location    → existe: warehouse_id FK, code, zone?, aisle?, rack? (TEXTO LIBRE),
              capacity?, restrictions JSON, StatusMixin
              SIN level, SIN position, SIN sequence, SIN unicidad de código
Endpoints   → GET/POST /warehouses, GET/POST /locations  (nada más)
Frontend    → AlmacenesPage 173 líneas, UbicacionesPage 158 líneas
```

### Hallazgo 1 · `cascade="all, delete-orphan"`

`Warehouse.locations` declara `cascade="all, delete-orphan"`. Borrar un almacén
borraría en cascada sus ubicaciones, y con ellas la referencia de todo movimiento
histórico. Contradice el Principio 5. **Se retira en 008** (FR-008-007).

### Hallazgo 2 · La fontanería del ledger ya existe

Corrige un matiz del GAP Analysis: `record_movement` **sí** acepta `location_id`,
lo escribe en `InventoryMovement` (FK real) y lo propaga a `InventoryBalance`.
Lo que falta no es la dimensión en el motor, sino:

- que alguien la suministre — `accept_receipt` llama sin ella (alcance de 019/022);
- que el modelo físico esté completo — sin nivel, posición ni secuencia;
- que las dos referencias restantes sean FK reales, no `String(36)`.

Esto reduce el alcance de 008 y lo hace más preciso: **008 completa el maestro y
la integridad; las Specs consumidoras escriben la ubicación.**

### Hallazgo 3 · Tres referencias sin FK

| Referencia | Tipo actual |
|---|---|
| `InventoryMovement.location_id` | `ForeignKey("locations.id")` ✔ |
| `InventoryBalance.location_id` | `String(36)` ✖ |
| `StockCountLine.location_id` | `String(36)` ✖ |

La inconsistencia permite hoy saldos y conteos que apuntan a ubicaciones
inexistentes. En PostgreSQL se convierte en integridad real (FR-008-054).

## 2. Modelo jerárquico: alternativas evaluadas

| Alternativa | Ordenación física | Tramos opcionales | Complejidad | Veredicto |
|---|---|---|---|---|
| **A · Tabla auto-referenciada** (`parent_id`) | Requiere CTE recursiva; `ORDER BY` físico costoso | Naturalmente | Baja en esquema, alta en consulta | **Descartada**: NFR-008-03 exige ordenar en base de datos con consulta plana |
| **B · Entidades separadas + hoja con cadena completa** | `ORDER BY` plano sobre columnas de secuencia | Sí, cada FK es nullable | Media | **ADOPTADA** |
| **C · Todo en la hoja** (zona/pasillo/rack como texto, como hoy) | Imposible ordenar de forma fiable | Sí | Muy baja | **Descartada**: es el modelo actual y el origen del problema |
| **D · Materialized path** (`ZA.P03.R02`) | Orden lexicográfico frágil (P10 antes que P3) | Sí | Media | **Descartada**: el orden lexicográfico no es el orden físico |

La alternativa B tiene un coste explícito: la hoja guarda hasta cuatro FK y hay
que garantizar que la cadena sea coherente. Se paga con una restricción
verificable, no con confianza en el servicio.

## 3. Ordenación física determinista

Requisito de la Spec 031: recorrer el almacén en el orden real.

Orden adoptado:

```
ORDER BY zone.sequence, aisle.sequence, rack.sequence, level.sequence, location.sequence
```

Con tramos nulos, PostgreSQL ordena `NULL` al final por defecto; se fija
`NULLS FIRST` para que una ubicación sin zona no quede sistemáticamente al final
de un almacén mixto. El desempate final es `location.sequence` y, a igualdad,
`location.code`, de modo que **el orden es siempre total y estable** (FR-008-033).

Se descartó ordenar por el código de ubicación: obligaría a que el código
codificara la jerarquía, lo que CL-008-07 rechaza.

## 4. Código y etiqueta

Dos conceptos distintos que el modelo actual confunde:

| Concepto | Naturaleza | Ejemplo |
|---|---|---|
| `code` | Identificador humano estable, único por almacén | `A-0345` o `ZA-P03-R02-N04-P05` |
| Etiqueta legible | **Derivada** de la jerarquía, para mostrar e imprimir | `ALM-01 / Alta rotación / P03 / R02 / N04 / POS-05` |

La etiqueta no se persiste: se calcula. Si se guardara, un cambio de nombre de
zona la dejaría desactualizada en silencio.

Política de código por almacén: `MANUAL` o `GENERATED`. La generación usa el
patrón declarado en el almacén, con los tramos que ese almacén utiliza.

## 5. Endpoint de estructura: comparativa

| Opción | Tamaño de respuesta | Consultas | UX | Veredicto |
|---|---|---|---|---|
| Solo listados por tramo | Pequeño | 5-6 por pantalla | Pobre en almacenes pequeños | Insuficiente |
| Solo `/structure` completo | Inviable con 50.000 ubicaciones | 1 | Buena hasta que crece | Insuficiente |
| **Ambos, con `depth` y paginación** | Controlado | 1 o N según necesidad | Buena en ambos extremos | **ADOPTADA** |

`GET /warehouses/{id}/structure?depth=N` devuelve hasta el tramo pedido y
**nunca** incluye ubicaciones salvo petición explícita con paginación. Un almacén
simple pide `depth=locations&limit=50` y resuelve su pantalla con una llamada.

## 6. Reubicación estructural

El riesgo real: cambiar el padre de una ubicación con stock reescribe el
significado de sus movimientos históricos, que dirán que la mercancía estuvo en
una zona en la que nunca estuvo.

Opciones evaluadas:

1. **Permitirlo y registrar auditoría** — insuficiente: la auditoría explica el
   cambio pero el Kardex sigue mintiendo.
2. **Permitirlo con snapshot de jerarquía en cada movimiento** — resolvería el
   histórico, pero añade cuatro columnas a `InventoryMovement`, que es alcance de
   la Spec 023, no de 008.
3. **Rechazarlo cuando hay stock o movimientos** — ← **ADOPTADA**. El traslado
   físico de mercancía es un movimiento de inventario, no una edición de
   metadatos. Una ubicación vacía y sin historial sí puede reorganizarse.

La opción 2 queda registrada como capacidad futura para la Spec 023, si el
negocio llega a exigir reorganizaciones con stock.

## 7. Rendimiento

Escenarios de dimensionamiento:

| Escenario | Ubicaciones | Estrategia |
|---|---|---|
| Almacén simple | 5-50 | Una llamada con `depth=locations` |
| Almacén medio | 500-5.000 | Navegación por tramo + búsqueda |
| Almacén grande | 20.000-50.000 | Búsqueda paginada; nunca árbol completo |

Índices previstos en `data-model.md`, todos justificados por una consulta concreta.
Se rechazan índices «por si acaso».

## 8. Caso de validación del cliente

El proceso documentado describe zonas de alta, media y baja rotación, incidencias
y sobredimensionados. Sirve como **caso de prueba** de que el modelo genérico lo
representa:

```
ZoneType (catálogo de la empresa): HIGH_ROTATION, MEDIUM_ROTATION, LOW_ROTATION,
                                   INCIDENT, OVERSIZED
WarehouseZone: name="Zona A", type=HIGH_ROTATION, sequence=1
               name="Zona D", type=INCIDENT,      sequence=4
```

Ningún nombre, código ni regla de ese cliente entra en el producto.

## 9. Riesgo identificado durante la investigación

Migrar `zone`/`aisle`/`rack` de texto libre a entidades tiene un riesgo que no es
técnico: **si se convierte automáticamente, se inventan datos**. Dos ubicaciones
con `zone="A "` y `zone="A"` producirían dos zonas distintas; una con `zone=null`
quedaría huérfana. Mitigación adoptada (CL-008-15): el texto se conserva en
`legacy_path` y la conversión es una decisión del cliente, asistida por pantalla,
no automática.

---

# INVESTIGACIÓN ADICIONAL DEL GATE PRE-IMPLEMENTACIÓN

## A. Política ante referencias huérfanas al imponer una FK

| Alternativa | Qué hace | Por qué se descarta o se adopta |
|---|---|---|
| **A1 · Anular todo lo inválido** | `UPDATE ... SET location_id = NULL WHERE NOT EXISTS (...)` y crear la FK | **Descartada.** Es exactamente la pérdida silenciosa que P5 prohíbe. La migración «pasa» destruyendo dato que nadie volverá a ver |
| **A2 · Abortar ante cualquier huérfana** | La migración falla si hay una sola inválida | **Descartada.** Bloquea el despliegue por filas irrelevantes —un saldo cero de un almacén sin ubicaciones—. Es la lección inversa de `0016` en la Spec 045 |
| **A3 · Borrar las filas huérfanas** | `DELETE` de lo que no cumple | **Descartada de plano.** Destruye registros de negocio para satisfacer una restricción técnica |
| **A4 · FK `NOT VALID`** | Crear la FK sin validar lo existente y validar más tarde | **Descartada como solución.** Deja la deuda indefinidamente y contradice P23: es exactamente el estado del que 008 quiere salir |
| **A5 · Clasificar y actuar según la clase** | Cuatro clases; reparar lo reconstruible, anular solo lo legítimo, **bloquear** lo crítico | **Adoptada.** Es la única que distingue el saldo cero irrelevante del saldo vivo irrecuperable |

**A5** cuesta más de implementar que A1 y esa es su ventaja: obliga a mirar el dato
antes de tocarlo. A2 y A5 coinciden en el caso crítico; se diferencian en que A5 no
paraliza el despliegue por ruido.

### Sobre las fuentes de reconstrucción

Se evaluó reconstruir desde `zone`/`aisle`/`rack`. **Se rechaza.** `"A"`, `"a"`,
`"Zona A"` y `"A "` no son demostrablemente la misma zona; afirmar que lo son es
una decisión de negocio, no una migración. Solo se admite `inventory_movements`
—FK real desde el origen, luego dato íntegro— y únicamente cuando resuelve a **una**
candidata.

## B. Régimen de cambio de `structure_levels`

| Alternativa | Qué hace | Veredicto |
|---|---|---|
| **B1 · Editable siempre** | Un `UPDATE` más | **Descartada.** Retirar `RACK` de un almacén operativo reinterpreta retroactivamente cada ubicación y cada movimiento |
| **B2 · Inmutable tras crearse el almacén** | Se fija al crear | **Descartada.** Demasiado rígida: un almacén configurado y aún vacío debe poder corregirse |
| **B3 · Migración estructural automática** | Al retirar un tramo, reasignar los hijos al abuelo | **Descartada.** Es reestructuración disfrazada de edición, sin simulación, sin aprobación y sin reversión |
| **B4 · Dos regímenes por existencia de datos** | `INITIAL` libre; `OPERATIONAL` con los tramos utilizados protegidos | **Adoptada.** El criterio es objetivo —¿existe algún nodo?— y no depende de la intención de quien edita |

La granularidad correcta resultó ser **el tramo, no el almacén**: un almacén
operativo puede seguir retirando un tramo que declaró y nunca usó. Proteger el
almacén entero habría sido más simple y más equivocado.

## C. Dónde vive el bloqueo

Se descarta apoyarlo en la UI. P6 lo zanja: una operación prohibida invocada por API
directamente debe rechazarse igual. El frontend deshabilita el control **y además**
el backend rechaza; la primera es cortesía, la segunda es la garantía.
