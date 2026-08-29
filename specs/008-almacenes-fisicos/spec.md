# SPEC 008 — ALMACENES FÍSICOS

| Campo | Valor |
|---|---|
| Iniciativa | `008-almacenes-fisicos` |
| Spec maestra | **008** (catálogo de 56) |
| Versión | 1.0 |
| Estado | Especificada — **sin autorización de implementación** |
| Rama | `develop` |
| Fecha | 2026-08-29 |
| Autoridad | Constitución v1.1 · `ADR-D0-004` · `POL-D0-003` · Baseline arquitectónica v1.0 · 29 ADR vigentes |
| Prioridad | **P0** — segunda del roadmap tras 045 |

---

## 1. Propósito

Cerrar la **arquitectura física genérica** de almacenamiento de KONTROL: una
estructura parametrizable, multiempresa y multisector que sirva igual a un
almacén de cinco ubicaciones que a uno con zonas, pasillos, racks, niveles y
posiciones.

El principio que gobierna toda la Spec:

> **La ubicación no es solo un maestro. Es una dimensión operativa del inventario.**

Esto no es retórica: el GAP Analysis documentó que KONTROL tiene maestros que las
transacciones ignoran, y `locations` es el caso más claro. Esta Spec existe para
que eso deje de ser cierto.

## 2. Punto de partida real (verificado, no supuesto)

El GAP Analysis situó 008 en `PARTIAL 36 %`. La inspección del código lo confirma
y lo matiza:

| Elemento | Estado real | Consecuencia para 008 |
|---|---|---|
| `Warehouse` | Existe: `company_id`, `branch_id` nullable, `code`, `name`, `warehouse_type`, `policies` JSON, estado | Se **extiende**, no se recrea |
| `Location` | Existe, pero `zone`/`aisle`/`rack` son **texto libre**; **sin `level`, sin `position`, sin secuencia** | Se **reestructura** |
| Unicidad de código | **No existe** ninguna | Se añade |
| `cascade="all, delete-orphan"` de `warehouse → locations` | **Existe** | **Se retira**: borra ubicaciones con historial (contradice P5) |
| Endpoints | Solo `GET`/`POST` de `warehouses` y `locations` | Faltan detalle, edición, activación, jerarquía, búsqueda |
| `InventoryMovement.location_id` | **FK real**, y `record_movement` lo acepta y propaga al saldo | **La fontanería del ledger ya existe** |
| `InventoryBalance.location_id`, `StockCountLine.location_id` | `String(36)` **sin FK** | Se convierten a FK real |
| Quién suministra la ubicación | **Nadie**: `accept_receipt` llama a `record_movement` sin ella | Es alcance de 019/022, no de 008 |
| Frontend | `AlmacenesPage` (173 líneas) y `UbicacionesPage` (158) | Se sustituyen por la estructura jerárquica |

**Matiz importante frente al GAP Analysis:** el motor de inventario ya acepta y
propaga `location_id`. 008 no tiene que inventar la dimensión en el ledger; tiene
que **completar el modelo físico, imponer integridad y suministrar la secuencia**.
Quién escribe la ubicación es alcance de las Specs consumidoras.

## 3. Alcance

### Incluido

1. **Modelo físico jerárquico y opcional por tramos**: almacén → zona → pasillo →
   rack → nivel → ubicación, donde **solo el almacén y la ubicación son
   obligatorios**.
2. **Tipos de zona y de ubicación** como catálogo por empresa, nunca como enum del producto.
3. **Secuencia física determinista** en cada tramo, suficiente para que la Spec
   031 construya una ruta de picking ordenada.
4. **Código de ubicación** único por almacén, legible, con política de generación configurable.
5. **Estados** de cada nodo, con la separación explícita entre estado de la
   ubicación y estado de la mercancía.
6. **Integridad referencial real** en PostgreSQL: sin jerarquías incoherentes, sin
   referencias entre empresas.
7. **Desactivación en lugar de borrado** cuando existe historial, con reglas por nodo.
8. **Reubicación estructural** gobernada: cambiar el padre de una ubicación con
   stock exige proceso, no un `PATCH`.
9. **API** de estructura, búsqueda y jerarquía, con `allowed_actions` en backend.
10. **Frontend** con pantallas completas y navegación jerárquica usable.
11. **Conversión a FK real** de las dos referencias de ubicación que hoy son texto.
12. **Contratos declarados** para 019, 022, 023, 025, 031, 032 y 036.

### Fuera de alcance

- **StockLedger y saldos por ubicación** — Spec 023. 008 fija el contrato.
- **Put-away** (asignación, traslado, confirmación física) — Spec 022.
- **Recepción física** y su ubicación de destino — Spec 019.
- **Cola y ruta de picking** — Spec 031. 008 suministra la secuencia, no el algoritmo.
- **Picking y consolidación** — Spec 032.
- **Transferencias, conteos, ajustes y devoluciones** — Specs 025 y 036.
- **WMS completo**: slotting automático, optimización de ruta, cross-docking, olas.
- **Impresión de etiquetas** de ubicación — el modelo no lo impide; 008 no lo implementa.
- **Planos o archivos** del almacén — Spec 046. Contrato compatible, sin implementación.
- **Aprobaciones** del CRUD de almacenes: no se introducen procesos innecesarios
  (§31 del encargo). Si alguna acción llegara a requerirlas, consumirá la Spec 045.

### Dependencias

| Dependencia | Spec | Estado | Tratamiento |
|---|---|---|---|
| Motor de aprobaciones | **045** | **COMPLETE_100** | Disponible; 008 no lo necesita por defecto |
| PostgreSQL obligatorio | D0-01 / P21 | Resuelto en el cierre de 045 | Toda la evidencia sobre PostgreSQL |
| Dimensiones organizacionales | `ADR-D0-013` | Aprobado | 008 respeta la matriz; no inventa relaciones |
| Estados de mercancía | `ADR-D0-010` | Aprobado | 008 define estado de **ubicación**, distinto del de mercancía |
| Gestión documental | 046 | No construida | Contrato compatible; sin implementación |
| Unidades y presentaciones | 011 | No construida | La capacidad de ubicación se expresa en unidad declarada; no depende de 011 |

## 4. Actores

| Actor | Uso |
|---|---|
| Administrador de empresa | Define almacenes y su estructura física |
| Supervisor de almacén | Mantiene zonas, pasillos, racks, niveles y ubicaciones; activa y desactiva |
| Almacenista | Consulta y busca ubicaciones; no las configura |
| Inventario / control de stock | Consulta existencias por ubicación (vía Spec 023) |
| Auditor | Consulta la estructura y su historial de cambios |
| Sistema | Genera códigos y valida coherencia jerárquica |

## 5. Historias de usuario

**HU-008-01 · Almacén simple que funciona desde el primer día**
Como administrador de una empresa pequeña quiero crear un almacén y darle cinco
ubicaciones sin definir zonas, pasillos, racks ni niveles, **para** empezar a
operar sin montar una estructura que no tengo.
*Criterio:* creo almacén y ubicaciones directamente; el sistema no exige ningún
tramo intermedio; el inventario opera con esas ubicaciones.

**HU-008-02 · Almacén complejo con la jerarquía completa**
Como supervisor de un almacén grande quiero definir zonas, pasillos, racks,
niveles y posiciones, **para** que cada unidad tenga una dirección física exacta.
*Criterio:* creo la jerarquía completa; cada ubicación conoce su cadena; la
etiqueta legible se deriva de ella.

**HU-008-03 · Zonas con el nombre de mi empresa**
Como administrador quiero nombrar mis zonas como las llama mi gente —«Zona D»,
«Refrigerados», «Pulmón»— y clasificarlas por su función, **para** que el sistema
hable mi idioma sin dejar de entender qué es cada cosa.
*Criterio:* el nombre es libre; el tipo procede de un catálogo que yo mismo
administro; KONTROL no trae ninguna zona predefinida obligatoria.

**HU-008-04 · Encontrar una ubicación en un catálogo grande**
Como almacenista quiero buscar una ubicación por código o por cualquier tramo de
su jerarquía, **para** localizarla entre miles sin recorrer un árbol entero.
*Criterio:* búsqueda por código, nombre, zona, pasillo, rack; resultados
paginados; respuesta útil con decenas de miles de ubicaciones.

**HU-008-05 · Recorrido físico ordenado**
Como responsable de preparación quiero que las ubicaciones tengan un orden físico
declarado, **para** que la futura ruta de picking siga el recorrido real del
almacén y no un orden arbitrario.
*Criterio:* cada tramo tiene secuencia; consultar ubicaciones ordenadas
físicamente devuelve un orden estable y determinista.

**HU-008-06 · No perder la historia**
Como auditor quiero que una ubicación con movimientos no pueda borrarse, **para**
que el Kardex histórico siga siendo reconstruible.
*Criterio:* el borrado se rechaza y `allowed_actions` no lo ofrece; la
desactivación sí es posible y es reversible.

**HU-008-07 · Bloquear una ubicación sin tocar su mercancía**
Como supervisor quiero bloquear una ubicación por mantenimiento sin que eso
cambie el estado de lo que contiene, **para** no falsear el inventario.
*Criterio:* la ubicación pasa a `BLOCKED`; el stock conserva su propio estado; la
consulta de existencias sigue mostrándolo.

**HU-008-08 · Reorganizar el almacén sin corromper el inventario**
Como supervisor quiero mover una ubicación a otra zona, **para** reflejar una
reorganización física.
*Criterio:* si la ubicación no tiene stock ni movimientos, el cambio es directo;
si los tiene, el sistema lo impide y explica por qué.

**HU-008-09 · Aislamiento entre empresas**
Como administrador de la empresa A quiero no ver ni poder asignar ubicaciones de
la empresa B, **para** que el aislamiento multiempresa sea real.
*Criterio:* toda consulta filtra por empresa; una referencia cruzada se rechaza
en base de datos, no solo en la interfaz.

**HU-008-10 · Estructura navegable, no un árbol imposible**
Como supervisor quiero recorrer la estructura de mi almacén sin perderme en siete
formularios encadenados, **para** poder mantenerla de verdad.
*Criterio:* navegación por niveles con breadcrumb, búsqueda en cada nivel y
creación en la pantalla del nivel correspondiente.

## 6. Modelo jerárquico

```
Company
 └─ Branch (opcional)
     └─ Warehouse                      ← OBLIGATORIO
         └─ WarehouseZone (opcional)
             └─ WarehouseAisle (opcional)
                 └─ WarehouseRack (opcional)
                     └─ WarehouseLevel (opcional)
                         └─ WarehouseLocation   ← OBLIGATORIO (hoja)
```

> **R-008-1 · Tramos opcionales, hoja obligatoria.** Solo `Warehouse` y
> `WarehouseLocation` son obligatorios. Cada tramo intermedio es opcional y se
> declara **por almacén**, no por instalación. Una ubicación puede colgar
> directamente del almacén.

> **R-008-2 · Coherencia de cadena.** Si una ubicación declara rack, ese rack debe
> pertenecer al pasillo declarado, ese pasillo a la zona declarada y esa zona al
> mismo almacén. No se admite una cadena con huecos intermedios
> (p. ej. rack sin pasillo cuando el almacén declara pasillos).

> **R-008-3 · Nada de zonas fijas.** KONTROL no define «Zona A…E» ni ninguna lista
> de zonas. Las zonas del proceso documentado del cliente son **un ejemplo de
> configuración**, no el modelo (`ADR-D0-004` R-D0-04-1).

## 7. Requisitos funcionales

### Almacén

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-001 | `Warehouse` con empresa, sucursal opcional, código, nombre, tipo, dirección, responsable, descripción, estado y política de estructura | P0 |
| FR-008-002 | Código único por empresa | P0 |
| FR-008-003 | Almacén central admitido: `branch_id` nulo es válido y significa alcance de empresa | P0 |
| FR-008-004 | `structure_levels`: qué tramos usa este almacén (zona, pasillo, rack, nivel), configurable | P0 |
| FR-008-005 | `location_managed`: si es `false`, el inventario opera a nivel de almacén (`ADR-D0-004` R-D0-04-3) | P0 |
| FR-008-006 | Desactivación reversible; **borrado prohibido** con estructura o movimientos | P0 |
| FR-008-007 | Retirar `cascade="all, delete-orphan"` de la relación con ubicaciones | P0 |

### Zona, pasillo, rack y nivel

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-010 | `WarehouseZone`: almacén, código, nombre, tipo, secuencia, estado, descripción | P0 |
| FR-008-011 | `ZoneType` como **catálogo por empresa**, no enum del producto | P0 |
| FR-008-012 | Distinción entre **tipo conceptual** y **nombre**: `type=QUARANTINE`, `name="Zona D"` | P0 |
| FR-008-013 | `WarehouseAisle`: zona opcional, código, nombre, secuencia, estado | P0 |
| FR-008-014 | `WarehouseRack`: pasillo opcional, código, nombre, secuencia, estado | P0 |
| FR-008-015 | `WarehouseLevel`: rack opcional, código, orden vertical, secuencia, estado | P0 |
| FR-008-016 | Código único dentro de su padre inmediato | P0 |
| FR-008-017 | Un almacén sin racks o sin niveles es válido | P0 |

### Ubicación

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-020 | `WarehouseLocation` con almacén obligatorio y zona, pasillo, rack y nivel opcionales | P0 |
| FR-008-021 | Código único por almacén | P0 |
| FR-008-022 | Etiqueta legible **derivada** de la jerarquía, no una columna editable | P0 |
| FR-008-023 | Política de código por almacén: **manual** o **generado** | P0 |
| FR-008-024 | `location_type` de catálogo por empresa (almacenamiento, recepción, cuarentena, despacho, daño, devolución, tránsito interno) | P0 |
| FR-008-025 | `sequence` propia dentro de su padre | P0 |
| FR-008-026 | Capacidad en unidades y peso máximo, ambos opcionales | P1 |
| FR-008-027 | Restricciones declarativas por producto o categoría | P1 |
| FR-008-028 | Campo para identificador de barras/QR, sin implementar impresión | P2 |
| FR-008-029 | Creación masiva de ubicaciones a partir de un patrón de la jerarquía | P1 |

### Secuencia física

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-030 | Cada tramo expone `sequence` entera, editable y con valor por defecto | P0 |
| FR-008-031 | Orden físico determinista: `(zona, pasillo, rack, nivel, ubicación)`, con la ubicación como desempate final | P0 |
| FR-008-032 | Consulta de ubicaciones ordenadas físicamente, con almacén y filtros | P0 |
| FR-008-033 | El orden es **estable**: dos consultas idénticas devuelven el mismo orden | P0 |

### Estados

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-040 | Estados de nodo: `ACTIVE`, `INACTIVE`, `BLOCKED`, `MAINTENANCE` | P0 |
| FR-008-041 | **`FULL` no se persiste**: la ocupación es derivable del saldo (Spec 023) | P0 |
| FR-008-042 | El estado de la ubicación **no** determina el de la mercancía (`ADR-D0-010`) | P0 |
| FR-008-043 | Desactivar un padre no desactiva a los hijos en cascada silenciosa: se rechaza si hay hijos activos y se explica | P0 |

### Integridad y alcance

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-050 | FK reales en toda la jerarquía; PostgreSQL es la autoridad | P0 |
| FR-008-051 | Rechazo de jerarquía incoherente (R-008-2) por restricción, no solo por servicio | P0 |
| FR-008-052 | Toda consulta y escritura filtra por empresa | P0 |
| FR-008-053 | Referencia entre empresas rechazada | P0 |
| FR-008-054 | `InventoryBalance.location_id` y `StockCountLine.location_id` pasan a **FK real**; `InventoryMovement.location_id` ya lo es | P0 |
| FR-008-055 | Una ubicación con movimientos o saldo **no puede borrarse**; `can_delete` y `allowed_actions` lo reflejan | P0 |
| FR-008-056 | Cambiar el padre estructural de una ubicación con stock o movimientos se **rechaza** (ver §Reubicación) | P0 |

### Migración de referencias (`0018`)

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-100 | Toda referencia huérfana detectada por `0018` se **clasifica** en `VALID_REFERENCE`, `RECONSTRUCTIBLE_ORPHAN`, `NON_RECONSTRUCTIBLE_BUT_NULL_ALLOWED` o `CRITICAL_NON_RECONSTRUCTIBLE`; la acción se deriva de la clase, nunca de la conveniencia (R-008-4) | P0 |
| FR-008-101 | Una referencia solo se anula si es reconstruiblemente imposible **y** el modelo histórico admite la ausencia; el valor original se conserva siempre en `legacy_location_id` | P0 |
| FR-008-102 | Una sola referencia `CRITICAL_NON_RECONSTRUCTIBLE` **aborta** `0018` de forma controlada antes de escribir nada (R-008-5) | P0 |
| FR-008-103 | `0018` produce un reporte auditable con recuentos por clase y detalle por referencia modificada o crítica, con datos mínimos necesarios | P0 |
| FR-008-104 | El texto legacy `zone`/`aisle`/`rack` se conserva en `legacy_path` y **no** es fuente admisible para reconstruir una referencia | P0 |

### Mutabilidad estructural

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-090 | `structure_levels` distingue régimen `INITIAL` (sin nodos ni ubicaciones) de `OPERATIONAL` (con estructura dependiente); el paso a `OPERATIONAL` es irreversible (R-008-6) | P0 |
| FR-008-091 | En régimen `OPERATIONAL`, eliminar, reordenar, resemantizar o colapsar un **tramo utilizado** se rechaza en backend | P0 |
| FR-008-092 | El modelo distingue **cambio de metadata** (nombre, descripción, etiquetas, `sequence` entre hermanos) de **cambio estructural** (padre, tramo, profundidad); solo el segundo queda sujeto a los controles estrictos | P0 |
| FR-008-093 | Todo bloqueo estructural devuelve `code` estable, `reason`, `dependencies` y `allowed_actions`; el frontend refleja el bloqueo pero no lo produce | P0 |
| FR-008-094 | Ningún nodo de la jerarquía con histórico —propio o heredado— puede borrarse físicamente; la vía es la desactivación (R-008-8) | P0 |
| FR-008-095 | No existe desactivación en cascada silenciosa: un nodo con descendientes activos se rechaza enumerándolos (R-008-9) | P0 |
| FR-008-096 | La desactivación es reversible y auditada en ambos sentidos (R-008-10) | P0 |
| FR-008-097 | 008 **no implementa** reestructuración; deja la arquitectura preparada para un proceso controlado posterior | P0 |

### API, permisos y auditoría

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-060 | Endpoints de listado, detalle, creación, edición, activación y desactivación de los seis nodos | P0 |
| FR-008-061 | `GET /organization/warehouses/{id}/structure` con jerarquía y control de profundidad | P0 |
| FR-008-062 | Búsqueda de ubicaciones paginada y filtrable | P0 |
| FR-008-063 | `allowed_actions` calculado en backend para cada nodo | P0 |
| FR-008-064 | Permisos del recurso `organization`, coherentes con la convención vigente | P0 |
| FR-008-065 | Auditoría de creación, modificación, activación, desactivación, cambio de jerarquía e intento prohibido, vía `record_audit` | P0 |
| FR-008-066 | Concurrencia optimista con `If-Match` sobre los nodos editables | P1 |

### Frontend

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-070 | Lista de almacenes con búsqueda, filtros, paginación y acciones | P0 |
| FR-008-071 | Alta y edición de almacén en **pantalla completa con URL propia** | P0 |
| FR-008-072 | Detalle de almacén con navegación por su estructura | P0 |
| FR-008-073 | Gestión de cada tramo en su nivel, con breadcrumb de la cadena | P0 |
| FR-008-074 | Lista de ubicaciones con búsqueda por cualquier tramo | P0 |
| FR-008-075 | Creación masiva por patrón (FR-008-029) en pantalla propia | P1 |
| FR-008-076 | Protección de cambios sin guardar | P0 |
| FR-008-077 | Estados Loading, Ready, Empty, Forbidden, NotFound, Error | P0 |
| FR-008-078 | Un almacén sin tramos intermedios muestra una interfaz **simple**, no la jerarquía completa vacía | P0 |

### Contratos para Specs futuras

| ID | Requisito | Prioridad |
|---|---|---|
| FR-008-080 | Contrato para **019/022**: consulta de ubicaciones válidas de destino, filtrables por estado y tipo | P0 |
| FR-008-081 | Contrato para **023**: la ubicación es dimensión de saldo y movimiento, con FK real | P0 |
| FR-008-082 | Contrato para **025**: origen y destino de transferencia como ubicaciones | P0 |
| FR-008-083 | Contrato para **031/032**: consulta ordenada físicamente | P0 |
| FR-008-084 | Contrato para **036**: ubicaciones de devolución y cuarentena identificables por tipo | P1 |
| FR-008-085 | Contrato para **046**: adjuntos vinculables al almacén sin cambiar el modelo | P2 |

## 8. Requisitos no funcionales

| ID | Requisito |
|---|---|
| NFR-008-01 | Búsqueda de ubicaciones ≤ 200 ms P95 con **50.000 ubicaciones** |
| NFR-008-02 | La estructura **no se carga entera** por defecto: profundidad y paginación controladas |
| NFR-008-03 | Consulta ordenada físicamente resuelta en base de datos, no en memoria |
| NFR-008-04 | WCAG 2.2 AA verificado con axe; operable solo con teclado |
| NFR-008-05 | Responsive 320–1920 px sin scroll horizontal; zoom 125 % y 150 % |
| NFR-008-06 | Pantallas completas con URL propia; modal solo para confirmación breve |
| NFR-008-07 | **Toda la evidencia sobre PostgreSQL 18.x** (P21, `ADR-D0-001` `CONFIRMED_BY_EXECUTION`); nunca en modo `--sql` |
| NFR-008-08 | Sin valores de negocio en código: zonas, tipos y estructura son datos (P8) |

## 9. Reglas no negociables

1. KONTROL **no** define zonas fijas ni estructura obligatoria.
2. Solo almacén y ubicación son obligatorios; el resto es configuración.
3. La ubicación llega a las transacciones con **FK real**, no como texto.
4. Una ubicación con historial **no se borra**; se desactiva.
5. Estado de ubicación y estado de mercancía son **dimensiones independientes**.
6. La jerarquía incoherente se rechaza en **base de datos**.
7. Ninguna empresa ve ni referencia ubicaciones de otra.
8. `FULL` y la ocupación **no se persisten**: se derivan.
9. La secuencia física es dato editable, no un orden implícito por código.
10. 008 **no implementa** recepción, put-away, picking, transferencias ni ledger.
11. Una referencia huérfana **no se anula para que la migración pase**: se clasifica, y la clase decide.
12. Una referencia crítica irrecuperable **bloquea la migración**; no se pierde en silencio.
13. El texto legacy **nunca** se convierte automáticamente en jerarquía estructural.
14. `structure_levels` **no es configuración editable** una vez el almacén opera.
