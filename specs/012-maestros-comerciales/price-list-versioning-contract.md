# SPEC 012 — CONTRATO DE VERSIONADO Y VIGENCIA

## El principio

Una lista de precios **no se edita**. Se versiona.

Es la misma decisión que la Spec 011 tomó con las presentaciones y por el mismo
motivo: una factura emitida en marzo no puede cambiar porque en abril alguien
corrigió un precio.

## Estados

| Estado | Puede editarse | Puede resolver precio | Transiciones |
|---|---|---|---|
| `DRAFT` | **Sí** — es el único estado que admite ítems nuevos | No | → `ACTIVE` |
| `ACTIVE` | No | **Sí** | → `SUPERSEDED`, → `ARCHIVED` |
| `SUPERSEDED` | No | No, salvo reconstrucción histórica | → `ARCHIVED` |
| `ARCHIVED` | No | No | — |

Publicar es irreversible. Una versión `ACTIVE` que resultó equivocada no se
corrige: se supera con otra.

## Vigencia

`valid_from` obligatoria. `valid_to` anulable, y el nulo significa **abierta**,
no «desconocida».

**Dos versiones `ACTIVE` de la misma lista no pueden solapar vigencia.** Es
`FR-012-005` y es una restricción de base de datos, no una validación de
servicio: una comprobación en Python pierde ante dos peticiones simultáneas, y
esta Spec ya sabe —por la Spec 046— que dos subidas concurrentes producen dos
versiones si nada en la base lo impide.

PostgreSQL lo resuelve con una restricción de exclusión sobre el rango:

```sql
EXCLUDE USING gist (
    price_list_id WITH =,
    daterange(valid_from, valid_to, '[)') WITH &&
) WHERE (status = 'ACTIVE')
```

El `WHERE` es esencial: los borradores **sí** pueden solapar, porque un borrador
todavía no compite con nadie.

Requiere la extensión `btree_gist`. Si el contrato de instalación no la admite,
la alternativa es un disparador — y entonces hay que decirlo, porque sería
lógica escondida en la base para algo que el modelo relacional expresa solo.
Queda como decisión de la ola 1 de implementación, con la exclusión como opción
preferida.

## Superposición no es empate

Dos versiones que solapan es un **error de configuración**, y se impide.

Dos listas distintas que aplican al mismo caso es un **empate de precedencia**, y
se resuelve por `price_precedence` — vigencia más reciente y, a igualdad, menor
precio (`FR-012-012`). Un empate que ni así se resuelve se **reporta como error**;
jamás se resuelve al azar (`FR-012-013`).

Son dos problemas distintos y conviene no confundirlos: el primero no debe poder
existir, el segundo existe legítimamente y tiene algoritmo.

## Determinismo

Dadas la misma empresa, cliente, artículo, presentación, cantidad, fecha y
moneda, `resolve_price` devuelve **siempre** el mismo resultado.

Si no lo hiciera, dos usuarios verían precios distintos para la misma venta y
ninguno de los dos estaría equivocado, que es la peor forma de estarlo.

El determinismo no es una aspiración de rendimiento: es un requisito verificable,
y su prueba es ejecutar la resolución dos veces y comparar, incluida la versión
que la produjo.

## Ausencia no es cero

Sin lista aplicable, la resolución **declara el precio ausente** (`FR-012-016`).
No devuelve `0`, ni `null` interpretable como cero, ni el último precio conocido.

Un cero es un precio. La ausencia de precio no lo es.

## El congelado, y qué se congela

Al aprobarse un documento se congela en la línea:

| Qué | Por qué |
|---|---|
| `price_source_version_id` | La versión que produjo el precio, no la lista |
| `price_source_item_id` | El ítem concreto de esa versión |
| `pricing_source` | `RESOLVED`, `MANUAL_JUSTIFIED` o `LEGACY_FREETEXT` |
| `discount_policy_id` + versión | Qué política autorizó el descuento |
| `discount_approval_request_id` | Si hizo falta aprobación (Spec 045) |
| `payment_term_snapshot` | La condición entera, no su identificador |
| Presentación y factor | Como los congela la Spec 011 |
| Moneda y tasa | La tasa se congela **en la transacción**, nunca en el maestro |

La reconstrucción histórica se hace **desde el snapshot**, jamás recalculando
(`FR-012-062`). Es la diferencia entre saber qué se facturó y adivinar qué se
habría facturado hoy.

## La tasa de cambio no vive en el maestro

`exchange_rates` es de empresa y cambia a diario. Congelar la tasa en la lista
de precios la convertiría en histórica el día siguiente.

La tasa se resuelve al emitir y se guarda en la línea. El maestro dice cuál es
hoy; la línea dice cuál fue.

## Borrado

Ninguna versión referenciada por un documento aprobado se borra ni se altera
(`FR-012-006`). `DELETE` sobre una versión referenciada responde `409`, no la
oculta ni la marca borrada en silencio.

Mismo criterio que 008, 011 y 046: la historia no se borra.
