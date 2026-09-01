# LECTURA Y ESCRITURA DOBLE — N8

## 1. Resultado

| Patrón | Encontrados en runtime |
|---|---:|
| Lectura doble de propiedad | **0** |
| Escritura doble de propiedad | **0** |
| Repliegue de empresa a tenant | **1**, retirado |
| Cargas útiles con propiedad heredada | **0** |

## 2. Por qué no hubo transición que desmontar

Una lectura doble aparece cuando un sistema escribe en dos sitios y lee del
nuevo con respaldo en el viejo, mientras migra. KONTROL nunca llegó a esa
situación: las columnas de respaldo se crearon y el backfill que las habría
usado resultó innecesario, porque no existe ninguna instalación desplegada.

La ausencia de lectura doble no es un logro de N8: es la consecuencia de haber
cerrado la ventana a tiempo. Conviene decirlo así en vez de presentarlo como
trabajo realizado.

## 3. Lo que sí había

Un repliegue, tratado en `n8-fallback-removal-report.md`. Funcionaba por
accidente desde N2 y su nombre invitaba a reintroducir la confusión.

## 4. Cómo se buscó

Sobre el código productivo, con los patrones concretos —`coalesce`, `nuevo or
heredado`, asignación simultánea de ambas columnas, `company_id or tenant_id`—
y leyendo la semántica, no solo contando coincidencias. Las apariciones de
`tenant_id` junto a `company_id` que quedan son legítimas: comprobar que una
empresa pertenece a un tenant es exactamente lo que hay que hacer.
