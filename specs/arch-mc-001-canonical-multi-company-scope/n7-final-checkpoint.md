# N7 — CHECKPOINT DE INTEGRIDAD ESTRUCTURAL

PostgreSQL **18.6** en UTC · head `0032` → `0037` · ciclo Spec completo

## 1. Qué añade la fase

N5 hizo que el sistema **se comporte** bien con dos empresas. N6 hizo que el
frontend **opere** sobre ese comportamiento. Las dos protecciones viven en
código: una consulta nueva, un trabajo de fondo, un script de importación o un
`INSERT` a mano las esquivan enteras.

N7 se lo pide a PostgreSQL, que no se puede olvidar de comprobarlo. Es la cuarta
capa de una defensa que ya tenía tres, y **ninguna de las anteriores se retira**.

## 2. El estado que se encontró al medir

El inventario se hizo contra `pg_constraint`, no contra el ORM, y esa distinción
resultó ser el hallazgo principal:

| Hecho | Antes | Después |
|---|---:|---:|
| Claves foráneas | 242 | **336** |
| `company_id` sin referencia | 90 | **0** |
| `tenant_id` sin referencia | 4 | **0** |
| Rutas derivadas válidas | 35 / 35 | 35 / 35 |
| Modelos sin alcance declarado | 13 | **0** |

## 3. Tres discrepancias documentales, corregidas por medir

**Las rutas derivadas son 35, no 36.** La matriz canónica arrastraba el número
de una medición anterior.

**Las restricciones de unicidad son 31, no 13.** El «13» era una estimación
previa a N3, que creó las tablas de empresa ya con su unicidad correcta.
**Ninguna necesitó cambiarse.**

**Trece tablas no declaraban su alcance**, entre ellas `warehouses` y
`branches` — precisamente las que N7 usa como modelo de lo que hay que
replicar. N0 reportó cero sin declarar; las de organización quedaron fuera de
aquel recuento.

## 4. Defectos reales encontrados

| Dónde | Qué pasaba |
|---|---|
| `inventory/service.py` | Los tipos de movimiento se buscaban solo por código: el «ENTRADA» de una empresa lo consumía la siguiente |
| `currencies`, `exchange_rates`, `report_definitions` | Declaraban alcance de tenant mientras el código exigía empresa y N5 ya había probado su aislamiento |
| `establishments` | Alcance de empresa sin declarar su autoridad: la ruta funcionaba, pero ninguna prueba podía comprobarla |
| `system_settings` | `tenant_id` sin referencia |
| 9 tablas de tenant | `company_id` como estrechamiento, sin referencia |

## 5. Cuatro clases de causa, resueltas por separado

Aplicar las claves rompió **111 pruebas**. El encargo pide distinguir entre
restricción incorrecta, fixture inválido, código de servicio incorrecto y
requisito contradictorio. Aparecieron tres de las cuatro.

**Fixture inválido.** Ocho suites usaban `COMPANY = "tenant-1"`, una cadena que
no es ni empresa ni tenant; otra daba a un usuario una empresa como tenant; otra
usaba el identificador de un usuario como tenant con recurso a la letra `"t"`.
Pasaban **por el mismo defecto** que esta Spec corrige.

**Código de servicio incorrecto.** Los tipos de movimiento, arriba.

**Restricción incorrecta.** Endurecí `movement_types` y `costing_profiles` a
obligatorias y rompieron ventas y compras. La primera lectura fue que los
fixtures estaban mal; leyendo el contrato resultó que su API expone
`global_scope`, y el nulo **es** ese interruptor.

Ese último merece quedar escrito: la salida fácil habría sido cambiar los
fixtures para que dejaran de usar el alcance global y declarar la fase
terminada.

## 6. Lo que casi invalida la fase entera

Las claves se añadieron primero **solo en las migraciones**. Como la base de
pruebas nace de `create_all` sobre el ORM, las pruebas de corrupción corrían
contra un esquema sin restricciones y fallaban con `DID NOT RAISE`.

Fue la forma afortunada de enterarse. Si la base de pruebas se construyera por
migración, habrían pasado en verde con el ORM vacío. De ahí sale
`test_el_orm_y_la_base_dicen_lo_mismo`, que compara columna a columna lo que el
modelo declara con lo que la base tiene.

## 7. Lo que PostgreSQL rechaza ahora por sí solo

Doce pruebas de corrupción por SQL directo, cada una verificando el `SQLSTATE`
concreto: que una inserción falle no significa nada si falla por una columna mal
escrita en vez de por la invariante que se quería demostrar.

| Intento | Código |
|---|---|
| El tenant escrito como empresa | `23503` |
| Empresa inexistente | `23503` |
| Empresa ausente donde es obligatoria | `23502` |
| Código duplicado dentro de una empresa | `23505` |
| Mismo código en dos empresas | **aceptado** |
| Zona de A sobre almacén de B | `23503` |
| Zona sobre su propio almacén | **aceptado** |
| Serie fiscal bajo empresa inexistente | `23503` |
| Documento fiscal bajo el tenant | `23503` |
| Pago bajo empresa inexistente | `23503` |
| Movimiento bajo el tenant | `23503` |

Se incluyen los casos que deben **aceptarse**. Sin ellos, una base que rechazara
todo pasaría la mitad de la tabla.

## 8. Lo que una clave foránea no puede hacer

Una empresa de **otro tenant** existe, así que la referencia la acepta. La base
no sabe quién puede operar dónde: eso lo decide el contexto de empresa.

Hay una prueba escrita expresamente para que nadie confunda las dos garantías.
N7 impide escribir algo que no es una empresa; N5 impide que A opere sobre lo de
B; y que un pago de B no cancele la deuda de A sigue siendo una regla de
servicio, porque ambos objetos existen y lo que está mal es la combinación.

## 9. Instalación limpia y fixture hostil

Sobre PostgreSQL 18.6 vacío: 37 migraciones, 336 claves, head `0037`. El SQL sin
conexión produce 105 sentencias revisables antes de aplicarlas.

Con datos heredados inválidos —un tercero cuya empresa es el identificador del
tenant— la migración **aborta**:

```
violates foreign key constraint "fk_parties_company"
head tras abortar: 0032_mc_expand_tenant_scoped
claves foráneas: 242  (exactamente la línea base)
```

Sin escrituras parciales, sin avanzar la versión. Que falle **es** el resultado
correcto: una instalación con datos inválidos tiene que detenerse y avisar, no
inventarse una empresa para que la migración pase.

El primer intento de este fixture sembró mal —una columna inexistente— así que
la migración pasó y pareció que no había nada que probar. Un fixture hostil que
no llega a insertar datos hostiles habría quedado registrado como evidencia de
aborto sin serlo.

## 10. Índices

**Ninguno añadido.** 102 de 107 columnas de empresa ya tienen uno, y las cinco
restantes no se consultan por empresa. Comprobado con `EXPLAIN` sobre cinco
consultas representativas: las cinco usan índice.

Un índice de más cuesta en cada escritura para no ahorrar nada en ninguna
lectura.

## 11. Las tres rojas de N7 ya no lo son

Dos pasan porque N7 puso las claves que les faltaban. La tercera afirmaba que
una tabla de tenant no puede llevar `company_id`, con una lista de cuatro
excepciones escrita a mano que se quedó corta: seis más lo llevan con pleno
sentido, porque la empresa **estrecha** el alcance en vez de definirlo.

Reescrita para exigir lo que de verdad importa: que la columna admita nulo,
porque el nulo significa «todas», y que referencie a `companies`, porque una
empresa inventada no significa nada.

## 12. Deuda de N7

**Ninguna.** No quedan claves pendientes, ni rutas anulables, ni unicidades sin
revisar, ni coherencias sin proteger.

Queda registrada una limitación del planificador de N4 para la Spec 052: infiere
del modelo vigente, no del catálogo de la base destino, así que contra una
instalación anterior a N7 devolvería vacío. No se cambia aquí porque no hay
ningún destino heredado que leer, y adivinar su forma sería inventar el
requisito.

## 13. Veredicto

**`ARCH-MC-001 — N7 COMPLETE`**

`SPEC 012 APTA_DOCUMENTALMENTE — BLOCKED_BY_ARCH_MC_001`
`REM-046-001 BLOCKED_BY_ARCH_MC_001`
`N4 Real Backfill — NOT_APPLICABLE — NO DEPLOYED LEGACY INSTALLATIONS`

N8, N9 y N10 quedan pendientes y no se inician.
