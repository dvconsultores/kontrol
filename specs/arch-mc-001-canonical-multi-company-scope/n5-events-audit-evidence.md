# EVENTOS Y AUDITORÍA — EVIDENCIA TRANSVERSAL

PostgreSQL 18.6 · **8 pruebas** · Veredicto: **PASS**

## Por qué un barrido aparte

Cada dominio comprueba su propia auditoría, pero eso no basta: un rastro puede
llevar la empresa correcta en las acciones que alguien pensó en probar y estar
en blanco en el resto.

Y así fue. Después de que seis dominios dieran por buena su auditoría, este
barrido encontró que **organización no anotaba la empresa en absoluto**: crear un
almacén en A y crearlo en B dejaban registros indistinguibles. El rastro sabía en
qué instalación había ocurrido algo, no en cuál de las empresas.

Corregido en los 25 puntos del módulo.

## El tenant, deducido en vez de repetido

`record_audit` deduce ahora el tenant a partir de la empresa cuando no se lo
pasan, en lugar de pedir el mismo dato dos veces por vías distintas. Así el
rastro no puede acabar diciendo una empresa de un tenant y un tenant diferente,
que es una contradicción que después nadie sabría resolver.

## Cobertura

| Comprobación | Resultado |
|---|---|
| Hay auditoría de empresa que barrer | PASS |
| Ninguna hacia una empresa inexistente | PASS |
| Ninguna con un tenant guardado bajo `company_id` | PASS |
| Ninguna cuyo tenant contradiga el de su empresa | PASS |
| Una acción de A nunca queda auditada como de B | PASS |
| Ambas empresas dejan rastro | PASS |
| Outbox sin eventos mal atribuidos | PASS |
| Ninguna de las 123 tablas de empresa guarda algo que no sea una empresa | PASS |

## El outbox

`outbox_events` está declarada y migrada, pero **ningún módulo escribe en ella**:
no hay una sola construcción de `OutboxEvent` fuera de su propio modelo.

No se inventa aquí el mecanismo que le falta. Es Spec futura, no deuda de N5.

Lo que sí queda escrito es la regla que tendrá que cumplir cuando exista, en una
prueba que hoy pasa porque la tabla está vacía y que estará esperando al primer
productor que alguien añada.

## Lo que todavía no audita

Los maestros —terceros y catálogo— no registran auditoría de negocio. Se
documenta en lugar de inventarlo: ARCH-MC-001 puede exigir que **el rastro que
existe** lleve la empresa correcta, no crear el que no existe.

## El barrido de las 123 tablas

La última prueba recorre el catálogo de PostgreSQL y pregunta, tabla por tabla,
si alguna fila dice pertenecer a algo que no es una empresa: ni un tenant, ni un
identificador inexistente. Es la medida de la mezcla, y ninguna prueba de dominio
puede hacerla.
