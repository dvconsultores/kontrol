# CHECKLIST — SPEC 008

## Conformidad constitucional

- [ ] **P2** — no se implementa sin autorización expresa que mencione `008`
- [ ] **P3** — cada requisito con tarea, código, prueba y evidencia
- [ ] **P5** — sin borrado con historial; sin `cascade delete-orphan`; reubicación con stock rechazada
- [ ] **P6** — alcance, coherencia y `allowed_actions` decididos en backend
- [ ] **P7 / P17** — solo componentes del design system compartido
- [ ] **P8** — **ninguna** zona, tipo o estructura en código
- [ ] **P10** — sin evidencia no hay función terminada
- [ ] **P11** — WCAG 2.2 AA y responsive sin scroll horizontal
- [ ] **P13** — FK reales, restricciones y `If-Match`
- [ ] **P18 / ADR-015** — pantallas completas; modal solo para confirmar
- [ ] **P21** — toda la evidencia sobre PostgreSQL
- [ ] **P22** — auditoría, permisos y aprobaciones consumen las capacidades existentes
- [ ] **P23** — la FK de ubicación se impone antes de que 019/022 generen historial

## Conformidad con ADR

- [ ] `ADR-D0-004` — jerarquía, zonas configurables, `location_managed`, estados, integración transaccional
- [ ] `ADR-D0-010` — estado de ubicación distinto del de mercancía
- [ ] `ADR-D0-013` — dimensiones organizacionales sin inventar relaciones
- [ ] `ADR-011` — cadena `Company → Branch → Warehouse → Zone → Location`
- [ ] `ADR-012` — auditoría por `record_audit`, sin rastro paralelo
- [ ] `ADR-013` — `If-Match` y unicidad en base de datos
- [ ] `ADR-D0-001` — PostgreSQL 
- [ ] `ADR-D0-002` — si alguna acción requiriera aprobación, consume el motor; no se duplica

## Modelo jerárquico

- [ ] Solo almacén y ubicación son obligatorios
- [ ] Cada tramo intermedio es opcional y se declara por almacén
- [ ] Almacén simple (5 ubicaciones, sin tramos) funciona de extremo a extremo
- [ ] Almacén complejo (zonas, pasillos, racks, niveles) funciona
- [ ] Cadena incoherente rechazada en base de datos
- [ ] Tramo de otro almacén rechazado
- [ ] `branch_id` nulo = almacén central, válido

## Zonas y tipos

- [ ] `ZoneType` y `LocationType` son catálogos por empresa
- [ ] Los catálogos se crean **vacíos**
- [ ] Tipo conceptual y nombre son campos distintos
- [ ] **Ninguna** zona A-E ni nombre de cliente en el código
- [ ] Ubicaciones especiales por `location_type`, sin duplicar el concepto en zona

## Ubicación

- [ ] Código único por almacén
- [ ] Política de código manual o generada, por almacén
- [ ] Etiqueta legible **derivada**, nunca persistida
- [ ] Capacidad en unidades y peso, opcionales
- [ ] Restricciones por producto o categoría
- [ ] Campo de código de barras reservado, sin impresión
- [ ] Creación masiva con vista previa antes de crear

## Secuencia física

- [ ] Cada tramo con `sequence` editable
- [ ] Orden `(zona, pasillo, rack, nivel, ubicación, código)` con `NULLS FIRST`
- [ ] Orden total, estable y determinista entre consultas
- [ ] Resuelto en base de datos con índice compuesto, no en memoria

## Estados

- [ ] `ACTIVE`, `INACTIVE`, `BLOCKED`, `MAINTENANCE` y nada más
- [ ] `FULL` **no** se persiste
- [ ] Estado de ubicación y de mercancía independientes, probado
- [ ] Desactivar un padre con hijos activos se rechaza y se explica

## Integridad y alcance

- [ ] FK reales en toda la jerarquía
- [ ] `InventoryBalance` y `StockCountLine` con FK real
- [ ] Filtro por empresa en toda consulta y escritura
- [ ] Referencia entre empresas rechazada
- [ ] `cascade="all, delete-orphan"` retirado
- [ ] Ubicación con movimientos, saldo o reservas no borrable
- [ ] Reubicación con historial rechazada

## API

- [ ] Los 6 nodos con listado, detalle, alta, edición, activación y desactivación
- [ ] `/structure` con `depth` y paginación; nunca árbol completo por defecto
- [ ] `/locations/ordered` con orden físico
- [ ] Búsqueda paginada y filtrable
- [ ] `allowed_actions` y `can_delete` en backend
- [ ] 10 códigos de error del contrato
- [ ] `If-Match` en nodos editables

## Frontend

- [ ] 5 pantallas nuevas + sustitución de las 2 existentes
- [ ] Configuración en pantalla completa con URL propia
- [ ] Un almacén simple **no** muestra pestañas vacías
- [ ] Breadcrumb con la cadena
- [ ] Búsqueda en cada nivel
- [ ] Protección de cambios sin guardar
- [ ] Los 6 estados de UI con textos con sentido
- [ ] DataTable sin scroll horizontal; tarjetas en móvil
- [ ] `aria-label` y tooltip en acciones de icono
- [ ] Validación con borde rojo, mensaje y foco en el primer error

## PostgreSQL y migraciones

- [ ] `0017` y `0018` aplican sobre base limpia
- [ ] Aplican sobre base pre-008 con datos
- [ ] `alembic check` sin drift de 008
- [ ] `legacy_path` conserva el texto original
- [ ] Ninguna conversión automática de texto a jerarquía
- [ ] Saldos y conteos huérfanos **clasificados** antes de tocarse; lo crítico bloquea (ver Control 1)

## Pruebas

- [ ] Unidad: coherencia, código, etiqueta, orden, desactivación
- [ ] Integración: los 12 casos del §47, sobre PostgreSQL
- [ ] Concurrencia: mismo código simultáneo; desactivación durante uso
- [ ] Regresión: `inventory`, `purchasing`, `sales`, `regulatory`, procesos
- [ ] E2E: los 12 casos del §48, adaptados a tramos opcionales
- [ ] Cross-browser: Chromium, Firefox, WebKit — WebKit no se llama Safari
- [ ] axe WCAG 2.2 AA sobre las pantallas de 008
- [ ] Responsive 6 viewports sobre las pantallas de 008

## Prohibiciones

- [ ] Sin zonas A-E ni estructura de cliente en el código
- [ ] Sin StockLedger, put-away, picking, recepción ni transferencias
- [ ] Sin WMS: ni slotting, ni optimización de ruta, ni cross-docking
- [ ] Sin permisos, auditoría ni aprobaciones duplicados
- [ ] Sin impresión de etiquetas
- [ ] Sin corregir las 22 violaciones responsive preexistentes ajenas a 008
- [ ] SQLite no se usa como evidencia final

## Control 1 — Migración `0018`

- [ ] Las cuatro clases están implementadas y son exhaustivas y excluyentes
- [ ] Ninguna ruta de código anula una referencia sin clasificarla antes
- [ ] La reconstrucción exige candidata **unívoca**; dos candidatas degradan la fila
- [ ] `legacy_path` **no** se usa como fuente de reconstrucción
- [ ] `legacy_location_id` conserva el valor original en toda reparación y anulación
- [ ] Una sola clase D aborta la migración **antes** de cualquier escritura
- [ ] El reporte cumple el invariante `valid + reconstructed + nulled + critical = total`
- [ ] El reporte no contiene datos de producto, importes ni terceros
- [ ] Los 6 casos pasan sobre PostgreSQL real
- [ ] El caso 4 se verifica por inspección de la base tras el aborto, no solo por el error
- [ ] `0018` nunca se evidencia en modo `--sql`

## Control 2 — Mutabilidad estructural

- [ ] `structure_regime` existe y el paso a `OPERATIONAL` es irreversible
- [ ] Eliminar, reordenar, resemantizar o colapsar un tramo **utilizado** se rechaza
- [ ] Un tramo declarado **sin nodos** sí puede retirarse
- [ ] Metadata y cambio estructural están separados; `sequence` entre hermanos es metadata
- [ ] Los cuatro códigos estructurales devuelven `reason`, `dependencies` y `allowed_actions`
- [ ] Ningún nodo con histórico propio o **heredado** puede borrarse
- [ ] No queda ningún `cascade` destructivo en la jerarquía
- [ ] No hay desactivación en cascada silenciosa
- [ ] La desactivación es reversible y auditada en ambos sentidos
- [ ] Cada bloqueo se rechaza también al invocarlo por API sin pasar por la UI
- [ ] 008 **no** implementa reestructuración

## Control 3 — PostgreSQL

- [ ] La versión validada coincide con la que fija `ADR-D0-001`
- [ ] La evidencia está en `docs/governance/postgresql-version-validation.md`
- [ ] La suite de aceptación de 008 se ejecuta sobre esa versión
