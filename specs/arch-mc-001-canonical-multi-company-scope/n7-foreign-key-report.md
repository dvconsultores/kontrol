# CLAVES FORÁNEAS — N7

## 1. De qué se partía

`company_id` existía en 107 tablas desde N3 y N5 lo llenó con la empresa
correcta. Pero era una **columna de texto**: la base no la contrastaba con nada.
Nada impedía escribir ahí el identificador de un tenant, el de una empresa de
otro tenant, o uno que no correspondiera a nada.

| Antes | Después |
|---|---:|
| Claves foráneas totales | 242 → **327** |
| `company_id` con referencia real | 17 → **107** |
| `company_id` **sin** referencia | 90 → **0** |
| `tenant_id` con referencia real | 6 → **10** |
| `tenant_id` **sin** referencia | 4 → **0** |

## 2. Las migraciones

| Migración | Qué añade |
|---|---|
| `0033_n7_company_fk` | 80 claves en tablas de alcance empresa |
| `0034_n7_tenant_fk` | 4 claves de tenant, más la empresa de la auditoría |
| `0037_n7_tenant_company_fk` | 9 claves en tablas de tenant con empresa opcional |

## 3. La tanda que casi se queda fuera

Las nueve de `0037` no estaban en el plan inicial. La primera pasada clasificó
por alcance declarado del modelo, y estas nueve son de **tenant** con
`company_id` como estrechamiento opcional: un rol puede valer en todo el tenant
o solo en una empresa, una moneda puede ser nacional o propia.

Que la columna admita nulo no la exime de referenciar a alguien real. Una
empresa nula significa «todas»; una empresa inventada no significa nada.

Lo descubrió una consulta al catálogo después de dar la fase por avanzada, y por
eso la prueba de arquitectura se reescribió para recorrer **toda** columna
llamada `company_id`, no solo las de tablas de empresa. La versión anterior
habría seguido dando verde con las nueve sueltas.

## 4. Sin cascada

Ninguna clave borra en cascada. Borrar una empresa con datos debe fallar: es una
persona jurídica con histórico fiscal, y que su borrado arrastre asientos,
documentos y libros sería lo contrario de lo que la ley obliga a conservar (P5).

## 5. Lo que una clave foránea no hace

Una empresa de **otro tenant** existe, así que la referencia la acepta: la base
no sabe quién puede operar dónde. Eso lo decide el contexto de empresa, y su
prueba está en la suite de aislamiento de N5.

N7 impide escribir algo que **no es una empresa**. No sustituye a N5, y la
prueba que lo documenta está escrita expresamente para que nadie confunda las
dos garantías.
