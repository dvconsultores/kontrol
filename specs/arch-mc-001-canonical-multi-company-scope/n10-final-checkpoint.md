# ARCH-MC-001 — N10 · CHECKPOINT FINAL

## Veredicto

**`ARCH-MC-001 — COMPLETE / GLOBALLY CONVERGED`**

## Qué demostró N10

N10 debía comprobar que diez fases describen un solo sistema. La comprobación
encontró que no lo describían, en doce sitios.

No eran regresiones de fases anteriores ni deuda conocida. Eran rutas que nunca
se habían mirado desde el ángulo correcto: N5 buscó el defecto donde la petición
**declara** la empresa —un id cargado con `db.get`, una empresa impuesta desde el
cuerpo— y esas rutas no declaran nada. Reciben el identificador del padre por la
URL, no piden contexto, y llaman al servicio con ese id tal cual.

El permiso no las salvaba. `compras:create` dice que el usuario puede crear
líneas de compra; no dice en qué empresa.

## Los doce

Nueve escrituras entre empresas, una lectura entre empresas, cuatro cruces de
tenant en identidad y una autorización que ignoraba la empresa que se le pasaba.
Cada una reproducida con una petición que devolvió `200` antes de la corrección.

La más instructiva: `resolve_actors` **recibe** `company_id` y no lo usaba.
Resolvía los aprobadores de una política de la empresa A entre los usuarios de
B, y de otro tenant. Un usuario de B aprobó un paso de A en la prueba.

## Y cinco columnas que no eran de nadie

La migración `0032` añadió `tenant_id` a cinco tablas afirmando que eran del
tenant. N7 revisó esa clasificación y **la corrigió**: tres son de empresa. La
corrección quedó escrita en `canonical-scope-matrix.md` con su motivo.

Lo que nunca ocurrió fue que la corrección llegara al esquema. Quedaron cinco
columnas con clave foránea real, vacías, que ningún código escribe ni lee y que
el ORM nunca declaró.

Es la forma más silenciosa de contradicción: ningún documento miente, y el
sistema conserva la estructura de la decisión anterior.

## Estado final

| Fase | Estado |
|---|---|
| N0–N3 | COMPLETE |
| N4 Framework | COMPLETE |
| N4 Backfill real | NOT_APPLICABLE — sin instalaciones heredadas |
| N5–N9 | COMPLETE / CONVERGED |
| **N10** | **COMPLETE / GLOBALLY CONVERGED** |

`REM-046-001` CLOSED · Spec 046 RECONVERGED ·
Spec 012 `DOCUMENT UPDATE REQUIRED BEFORE IMPLEMENTATION`, sin autorizar.

## Cifras vigentes

`n10-final-authoritative-baseline.md` es la única baseline. Toda cifra anterior
que discrepe está marcada como superada, con su motivo, en
`n10-historical-baseline-reconciliation.md`.

## Regresión

Backend **0 fallos, 8 saltos** —todos S3— sobre PostgreSQL 18.6, con la base
legada sembrada y ClamAV real. Frontend 278/278, `tsc`, ESLint y build limpios.

Los 16 saltos de `test_mc_preflight` que apareció en una pasada intermedia no
eran de diseño: el entorno efímero había perdido la base legada, y las pruebas
que verifican N4 no se estaban ejecutando. Se sembró y pasan las 16.

## Deuda

Cero P0. S3 (`IMPLEMENTED_NOT_VERIFIED`, P1 externa), planificador de retención
(Spec 052), productores del outbox, roles propios por tenant y unificación de
las dos rutas de conversión: todas con responsable, en `n10-debt-register.md`.

## Lo que impide que vuelva

Cuatro pruebas de arquitectura nuevas, que fallan en construcción:

- una ruta de módulo de empresa que reciba un id sin ver el contexto;
- una excepción a esa regla que sobreviva a la ruta que la justificaba;
- un modelo de tenant sin columna ni ruta declarada;
- cualquier diferencia entre el ORM y el esquema que producen las migraciones.

La última construye su propia base **con Alembic**. El resto de las suites la
levanta desde el ORM, y comparar el ORM contra eso sería preguntarle a alguien si
está de acuerdo consigo mismo.
