# RUTAS DERIVADAS — N7

## 1. El recuento real

**35**, no 36. La matriz canónica arrastraba el número de una medición anterior;
comprobado contra los modelos vigentes son 35.

Es la clase de dato que §19 del encargo pedía verificar en vez de asumir, y la
verificación cambió el número.

## 2. Estado

| Medida | Valor |
|---|---:|
| Total | 35 |
| Válidas: clave foránea real y obligatoria | **35** |
| Con autoridad anulable | **0** |
| Ambiguas | **0** |
| Rotas | **0** |

## 3. Ya estaban bien

Conviene decirlo porque cambia el tamaño de la fase: N3 creó las 35 con su clave
real y no anulable. Las líneas de documento, los movimientos de sesión de caja y
las líneas de conteo nunca perdieron a su padre.

N7 no las arregla. Añade la prueba que impide que dejen de estarlo, y esa prueba
exige revisar más de treinta para que un barrido vacío no cuente como verde.

## 4. Un hueco que sí apareció

`establishments` está declarada de alcance empresa, no lleva `company_id` propio
—deriva de su sucursal— y **no declaraba su autoridad**. La ruta funcionaba: la
clave a `branches` es real y obligatoria. Lo que faltaba era decirlo, y sin eso
ninguna prueba estructural podía comprobarla.

Corregido con `__scope_authority__ = "branch_id → branches"`.

## 5. Qué se comprueba

Para cada derivada: que declare su autoridad, que la columna exista, que sea
NOT NULL y que tenga clave foránea. Una ruta que puede ser nula no es una ruta.
