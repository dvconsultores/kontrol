# SPEC 012 — RESOLUCIÓN DE PRECIO Y DE DESCUENTO

## `resolve_price` es la única autoridad de precio

`FR-012-014`. Entradas: empresa —del contexto, nunca del cuerpo—, artículo,
cliente, presentación, cantidad y fecha.

## Determinismo

Comprobado ejecutándolo dos veces y comparando la respuesta entera, incluida la
versión que produjo el precio. Si dos usuarios vieran precios distintos para la
misma venta, ninguno de los dos estaría equivocado, que es la peor forma de
estarlo.

## Devuelve el precio **y** su origen

```json
{
  "resolved": true,
  "unit_price": "125.4000",
  "price_list_id": "…",
  "price_list_version_id": "…",
  "price_list_item_id": "…",
  "source_kind": "COMPANY_LIST",
  "precedence_configured": false
}
```

`price_list_version_id` es lo que hace reconstruible una cotización: sin él, un
precio emitido es un número que alguien escribió. Es la deuda que esta Spec
existe para cerrar.

`precedence_configured` dice si la empresa configuró su orden o si se usó el de
`ADR-D0-005`. Que el sistema use un valor por defecto no es lo mismo que
ocultarlo.

## Ausencia no es cero

```json
{ "resolved": false, "reason": "NO_APPLICABLE_PRICE_LIST" }
```

Sin lista aplicable la respuesta **no trae `unit_price`**. Un cero es un precio;
la ausencia de precio no lo es (`FR-012-016`). La prueba comprueba que la clave
no está, no que valga cero.

## Empates

Vigencia más reciente y, a igualdad, menor precio (`FR-012-012`). Un empate que
ni así se resuelve se reporta como **error de configuración** con los candidatos
en el detalle (`FR-012-013`); jamás se resuelve al azar.

## Precedencia: dato, no código

`price_precedence` guarda el orden por empresa. La prueba lo demuestra haciendo
que A configure el suyo y B no: si estuviera codificado, no podrían diferir.

Sembrar el orden por defecto en una tabla no viola `P8`. Codificarlo sí.

## Validación de descuento

| Situación | Respuesta |
|---|---|
| Sin política declarada | `allowed: true`, `max_percent: null`, `NO_POLICY_DECLARED` |
| Bajo el umbral | `allowed: true`, `requires_approval: false` |
| Sobre el umbral | `allowed: true`, **`requires_approval: true`** |
| Sobre el máximo | `allowed: false` |

Superar el umbral **no bloquea**: abre solicitud (`FR-012-023`). Y la abre el
consumidor con el motor de la Spec 045; la 012 no crea aprobaciones.

Sin política declarada no se inventa un límite. El catálogo nace vacío, y un
catálogo vacío significa «no hay límite declarado», no «el límite es cero».

## La política más específica manda

Artículo, luego rol, luego categoría, luego todas; a igualdad, la versión mayor.
Es determinista y está en el código de una sola función, no repartido.
