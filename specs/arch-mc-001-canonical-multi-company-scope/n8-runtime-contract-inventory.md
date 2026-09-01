# INVENTARIO DE CONTRATO EN RUNTIME — N8

## 1. Cargas útiles

Ningún esquema de petición permite que el cuerpo defina la propiedad. N5 cerró
el último caso —la Spec 045, donde el cuerpo imponía la empresa— y la familia de
pruebas de arquitectura de N5 lo vigila: detecta cualquier ruta que pase
`body.company_id` a un servicio sin contrastarlo con el contexto validado.

El campo se conserva en algunos cuerpos por compatibilidad, pero contradecir el
contexto es un error, no una preferencia.

## 2. Respuestas

Ninguna respuesta expone `legacy_scope_id` ni `scope_backfill_class`. No podían
exponerlos: nunca estuvieron en el ORM.

## 3. Variables de entorno y configuración

No existe ninguna bandera de transición multiempresa. Se revisaron las variables
de configuración y las banderas de característica: las que hay son de negocio o
de entorno —modo de licencia, ruta del antivirus, seguridad de cookies— y
ninguna condiciona el alcance.

## 4. Frontend

N6 dejó la cabecera centralizada en un único punto. N8 retiró el último resto:
`setActiveCompany`, marcado como «compatibilidad con el código anterior»,
aceptaba tanto una empresa como `null` y dejaba dos formas de hacer lo mismo.

Elegir empresa y soltar el contexto son operaciones distintas, y ahora se llaman
distinto: `selectCompany` y `clearCompany`.

## 5. Documentación con semántica obsoleta

`canonical-scope-matrix.md` clasificaba `currencies`, `exchange_rates` y
`report_definitions` como de tenant. N7 demostró que son de empresa: el código
las crea con la empresa activa, las lista por empresa, y N5 ya había probado su
aislamiento A/B.

Corregido en la matriz. Los informes históricos conservan su texto: describen lo
que se sabía entonces, y reescribirlos borraría la evidencia de cómo se
descubrió.
