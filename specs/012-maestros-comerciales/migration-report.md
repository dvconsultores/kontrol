# SPEC 012 — MIGRACIONES

Dos, pequeñas y auditables. Ninguna siembra configuración empresarial.

## `0040_spec012_commercial_masters`

Las once tablas, con sus claves foráneas, su unicidad y sus restricciones de
comprobación. Ocho llevan `company_id` obligatoria con referencia a `companies`;
tres no la llevan.

**No siembra nada.** Ningún porcentaje, plazo, límite, zona ni canal: los
catálogos nacen vacíos (`P8`, `FR-012-022`, `FR-012-032`). Una prueba lo
comprueba después de la instalación limpia.

## `0041_spec012_exclusions`

Lo que la base debe impedir por sí sola, separado a propósito para poder verlo
fallar solo:

- la exclusión de solape entre versiones `ACTIVE` de una lista, con
  `btree_gist`;
- los dos índices únicos parciales de los ítems.

Sobre SQLite no hace nada y lo dice: no hay exclusión ni índices parciales
equivalentes, y fingir que la restricción existe sería peor que no tenerla.

## Backfill

**No aplica.** KONTROL sigue sin instalaciones heredadas desplegadas, y estas
migraciones crean tablas nuevas: no hay dato anterior que trasladar.

## Un hallazgo del marco de migración de legado

Al ejecutar la regresión completa, quince pruebas del clasificador de N4
fallaron con `relation "commercial_zones" does not exist`.

No era un defecto de la Spec 012 ni una regresión de ARCH-MC-001: el
clasificador preguntaba al catálogo del destino por sus **restricciones**, pero
no por la **existencia** de la tabla. Planificaba revisar tablas que una
instalación heredada no tiene, porque son posteriores a ella.

El hueco estaba desde N4. Lo que faltaba para verlo era una tabla de empresa
nueva, y la Spec 012 fue la primera en añadir once de golpe.

Se corrigió en `app/core/mc/runner.py` con `_existentes_en(cx)`, que completa lo
que el propio docstring de `planes()` ya prometía —«se le pregunta al catálogo
de la base que se va a analizar»— sin cambiar ninguna decisión de ARCH-MC-001.
Queda dicho aquí y en el checkpoint, no aplicado en silencio.

Comprobado después: el clasificador sigue produciendo las ocho clases y las
cuatro estrategias de maestro sobre el fixture hostil, que vive en `0032`.
