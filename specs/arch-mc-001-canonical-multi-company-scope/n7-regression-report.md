# REGRESIÓN — N7

## 1. Lo que la fase rompió, y por qué era correcto que lo rompiera

Al aplicar las claves foráneas, **111 pruebas** fallaron de golpe. La causa no
fue una restricción mal puesta: fue que ocho suites de dominio usaban
`COMPANY = "tenant-1"`, una cadena inventada que no es ni una empresa ni un
tenant.

Pasaban porque `company_id` era texto suelto. Es decir, pasaban **por el mismo
defecto** que ARCH-MC-001 existe para corregir: una prueba que guarda datos bajo
una empresa que no existe no está comprobando el comportamiento multiempresa,
está esquivándolo.

La corrección no relaja nada. Las ocho suites operan ahora sobre dos empresas
reales, con su tenant y su instalación, y `OTRA` es una empresa distinta de
verdad en vez de otra cadena inventada.

## 2. Cuatro clases de causa, resueltas por separado

El encargo pide distinguir entre restricción incorrecta, fixture inválido,
código de servicio incorrecto y requisito contradictorio. Aparecieron tres de
las cuatro.

**Fixture inválido.** Las ocho suites con la cadena inventada, más
`test_approvals`, que daba a un usuario **una empresa como tenant** — el defecto
en miniatura, dentro de una prueba.

**Código de servicio incorrecto.** Los tipos de movimiento de inventario se
buscaban solo por código, ignorando el `company_id` que la función ya recibía.
El tipo «ENTRADA» de una empresa lo consumía la siguiente.

**Restricción incorrecta.** Endurecí `movement_types` y `costing_profiles` a
obligatorias, y rompieron ventas y compras. La primera lectura fue que los
fixtures estaban mal; leyendo el contrato resultó que su API expone
`global_scope`, un interruptor que crea el tipo para toda la instalación. El
nulo **es** ese interruptor, y la restricción sobraba.

Ese es el caso que más merece quedar escrito, porque la salida fácil habría sido
cambiar los fixtures para que dejaran de usar el alcance global y declarar la
fase terminada.

## 3. Un detalle de método que casi invalida la fase

Las claves foráneas se añadieron primero **solo en las migraciones**. Como la
base de pruebas nace de `create_all` sobre el ORM, las pruebas de corrupción se
ejecutaban contra un esquema sin restricciones y fallaban con `DID NOT RAISE`.

Fue la forma afortunada de enterarse. Si la base de pruebas se hubiera
construido por migración, habrían pasado en verde con el ORM vacío, y la
paridad —que es lo que hace que estas pruebas signifiquen algo— habría quedado
rota sin que nadie lo viera.

De ahí sale `test_el_orm_y_la_base_dicen_lo_mismo`.

## 4. El planificador de N4

`planes()` excluye las tablas cuya empresa ya está garantizada por clave
foránea. Antes de N7 eso valía para 17 tablas; ahora vale para todas, así que su
conjunto de trabajo queda **vacío**.

Es el resultado esperado de haber cerrado la ventana a tiempo, y la prueba lo
dice así en vez de seguir afirmando que `parties` necesita reconstrucción.

Queda registrada una limitación para la Spec 052: el planificador infiere del
modelo vigente, no del catálogo de la base destino, así que contra una
instalación heredada anterior a N7 también devolvería vacío. Cuando exista una
actualización real desde una versión previa, tendrá que leer el catálogo del
destino. No se cambia aquí porque no hay ningún destino heredado que leer, y
adivinar su forma sería inventar el requisito.
