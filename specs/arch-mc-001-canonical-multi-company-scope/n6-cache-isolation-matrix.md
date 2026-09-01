# AISLAMIENTO DE CACHÉ POR MÓDULO — N6

## 1. Cómo se consigue

No módulo por módulo: en el único punto donde no se puede olvidar. La función
que convierte una clave de consulta en su identidad incorpora la empresa activa,
salvo un puñado de raíces declaradas que no dependen de ella.

Con **271 consultas** repartidas por la aplicación, confiar en que cada una
recuerde añadir la empresa sería confiar en que ninguna se olvide. Y la que se
olvidara sería precisamente la que muestra los datos de otra empresa.

La lista de excepciones es corta a propósito —autenticación, licencia, salud,
diagnóstico, la propia lista de empresas— porque en KONTROL casi todo es de
empresa: 123 de 153 modelos. Lo que se enumera es la excepción, así que una
consulta nueva que nadie clasifique queda separada por empresa, que es el lado
seguro de equivocarse.

## 2. Por módulo

| Módulo | Consultas de empresa | Separadas | Descartadas al cambiar | Contaminación |
|---|---|---|---|---|
| Organización | sí | por identidad | sí | **0** |
| Maestros | sí | por identidad | sí | **0** |
| Compras | sí | por identidad | sí | **0** |
| Inventario | sí | por identidad | sí | **0** |
| Ventas | sí | por identidad | sí | **0** |
| CxC / CxP | sí | por identidad | sí | **0** |
| Tesorería | sí | por identidad | sí | **0** |
| Fiscal | sí | por identidad | sí | **0** |
| Regulatorio | sí | por identidad | sí | **0** |
| Aprobaciones | sí | por identidad | sí | **0** |
| Documental | sí | por identidad | sí | **0** |
| Licencia / salud / diagnóstico | no | compartidas | no | n/a |

## 3. Invalidar no basta

Invalidar marca lo viejo como caducado; separar hace que lo de A y lo de B nunca
hayan sido la misma entrada. La diferencia se nota en el instante entre el
cambio de empresa y la llegada de la respuesta nueva: con una sola entrada
compartida, ahí se ven los datos de A bajo el rótulo de B, y si la consulta
estuviera fresca no se refrescarían nunca.

Además del cambio de identidad, al cambiar de empresa se cancelan y se retiran
las consultas de la anterior, y el contenido se remonta. Eso resuelve de paso lo
que ninguna clave arregla: un detalle de A que seguiría en pantalla bajo B, y
las selecciones locales —sucursal, almacén, cuenta bancaria, filas marcadas— que
sobrevivirían apuntando a entidades de otra empresa.

## 4. Comprobación

Cada empresa tiene un tercero propio sembrado en el arranque de pruebas. Bajo A
se ve el suyo y no el de B; al cambiar a B ocurre lo contrario, y el de A
desaparece de la pantalla.

Sin datos distintos en cada empresa, dos listas vacías tampoco se contaminan y el
aislamiento habría quedado «demostrado» por no haber nada que mezclar.
