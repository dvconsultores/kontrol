# N10 — INVENTARIO GLOBAL DE ALCANCE

166 modelos, 166 tablas, **0 sin clasificar**. Medido con
`Base.registry.mappers` tras `init_models()`, no leído de un informe.

| Alcance | Modelos | Con columna propia | Por ruta derivada |
|---|---:|---:|---:|
| COMPANY | 136 | 100 | 36 |
| TENANT | 8 | 4 | 4 |
| INSTALLATION | 18 | — | 1 |
| GLOBAL | 4 | — | — |
| **UNKNOWN** | **0** | | |

## Lo que N10 cambió en la clasificación

Cuatro modelos declaraban `TENANT` sin tener por dónde llegar a un tenant: ni
columna, ni relación, ni ruta declarada. Su alcance estaba escrito pero era
imposible de verificar, que es otra manera de no estar clasificado.

| Modelo | Era | Es | Por qué |
|---|---|---|---|
| `Role` | TENANT | **INSTALLATION** | No hay `tenant_id` ni camino a uno. El catálogo lo crea el arranque, no existe ruta para crear roles, y un segundo tenant reutiliza el `ADMIN` existente: hay un catálogo, no uno por tenant |
| `RolePermission` | TENANT | **INSTALLATION** | Sigue a `Role`. Declara `role_id → roles` |
| `IdempotencyRecord` | TENANT | **INSTALLATION** | Clave única en toda la instalación; quien escribe la fila guarda usuario y empresa, nunca tenant |
| `LegacyDocumentReference` | TENANT | **INSTALLATION** | Anota el legado **antes** de saber de quién es la fila original. Por eso su empresa admite nulo: es el caso MC-D |

Y cuatro que sí son de tenant y llegan por su usuario ahora lo declaran:
`sessions`, `password_resets`, `user_roles` y `user_scopes`, todos con
`user_id → users`, clave foránea obligatoria.

## El estrechamiento, y por qué se comprueba en todos los alcances

Una tabla que no es de empresa **puede** llevar `company_id` si el nulo
significa «todas»: es un estrechamiento, no una propiedad. La prueba de N7 lo
exigía solo en las tablas de tenant. Al reclasificar tres a `INSTALLATION`
habrían salido de la comprobación sin dejar de llevar la columna, así que la
regla pasó a mirar el estrechamiento y no el alcance que lo usa.

Once columnas `company_id` anulables, todas con referencia a `companies`:
`audit_events`, `costing_profiles`, `idempotency_records`,
`legacy_document_references`, `movement_types`, `outbox_events`, `roles`,
`stored_files`, `units_of_measure`, `user_roles`, `user_scopes`.

`units_of_measure` es el caso más instructivo: se declara de empresa y su
columna admite nulo porque una unidad de plataforma la ven todas las empresas y
es de solo lectura para ellas. El nulo no es un dueño ausente: es un dueño que
es la instalación.
