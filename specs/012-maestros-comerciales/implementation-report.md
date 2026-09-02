# SPEC 012 — INFORME DE IMPLEMENTACIÓN

## Qué se construyó

Once entidades, un módulo de backend, catorce rutas y dos pantallas. Ninguna
regla comercial inventada: todo lo que decide se lee de tablas que nacen vacías.

| Capa | Qué |
|---|---|
| Modelos | `app/modules/commercial/models.py` — las once, con alcance declarado |
| Servicios | `app/modules/commercial/service.py` — resolución acotada por empresa |
| API | `app/modules/commercial/api.py` — 14 rutas, 22 operaciones |
| Migraciones | `0040` las tablas · `0041` lo que la base impide sola |
| Permisos | `comercial:` view · create · edit · manage_policies · publish · archive |
| Frontend | Listas de precios (jerarquía completa) y condiciones de pago |

## Alcance

| | |
|---|---:|
| Entidades | 11 |
| Directas de empresa | 8 |
| Derivadas | 3 |
| **Indeterminadas** | **0** |

Las tres derivadas **no** llevan `company_id`. La cadena, con cada eslabón
obligatorio:

```
price_list_items.version_id  → price_list_versions → price_lists → companies
customer_commercial_terms.customer_id → customers → parties → companies
```

## Lo que la implementación descubrió

**Tres invariantes solo se sostienen en la base.** El solape de vigencias entre
versiones activas, la unicidad de ítems con columnas anulables y la unicidad por
empresa. Ninguna de las tres aguanta en Python: una comprobación en el servicio
pierde ante dos peticiones simultáneas, y la Spec 046 ya enseñó que dos subidas
concurrentes producen dos versiones si nada en la base lo impide.

**Y una tuvo que declararse dos veces.** La restricción de exclusión estaba solo
en la migración, y la prueba que la verificaba pasaba en verde sin comprobar
nada: las suites levantan el esquema con `create_all`, desde el ORM, así que
interrogaban un esquema más débil que el de producción. Es exactamente lo que N7
encontró con 80 claves foráneas.

Se declara ahora en el ORM con `ExcludeConstraint`, más un `before_create` que
crea `btree_gist`. La migración la conserva para el camino de actualización.

**Tres `flush` tuvieron que retirarse.** El choque de unicidad y el de exclusión
saltaban dentro del servicio, donde no hay quien los traduzca, y llegaban al
cliente como `500`. Ahora llegan al `commit`, donde se convierten en `409` con
su motivo. La restricción siempre funcionó; lo que no funcionaba era contarlo.

## Lo que no se implementó, y por qué

| Qué | Motivo |
|---|---|
| `SalesCommissionPolicy` | **Reservada** por `FR-012-090`. Tabla y alcance, sin servicio, ruta ni interfaz |
| Motor de aprobación propio | La Spec 045 ya existe (`FR-012-034`) |
| Motor de unidades propio | La Spec 011 ya existe |
| Motor de monedas o de tasas | Los maestros ya existen, y son de empresa |
| Emisión de eventos | `FR-012-073`: la 012 no emite eventos ni notifica |
| Valores comerciales por defecto | `P8`: los catálogos nacen vacíos |

## `OQ-06`

Sigue `CONFIGURABLE_AT_RUNTIME`. `price_precedence` guarda el orden **como
dato**: si una empresa no lo ha configurado se usa el de `ADR-D0-005` y la
respuesta dice de dónde salió (`precedence_configured: false`). La prueba
`test_la_precedencia_es_dato_y_cada_empresa_tiene_la_suya` lo demuestra
haciendo que A y B difieran; si estuviera codificada, no podrían.
