# SPEC 028 · DELTA DIRIGIDO — EL SALDO DEJA DE CALCULARSE EN COMA FLOTANTE

> Delta dirigido sobre el **dueño canónico del motor compartido de saldos**,
> ejecutado el 2026-09-11 desde el ciclo de la Spec 037. No reabre la Spec 028:
> corrige la autoridad que CxP, CxC, conciliación y tesorería comparten.

## 0. Identidad del dueño, resuelta

El número `004` es ambiguo en este repositorio y hubo que desambiguarlo antes de
tocar nada:

| | |
|---|---|
| Máster 56 · Spec **004** | **Licenciamiento** (`BLOCKED_BY_BUSINESS_DECISION`, `D0-06`) — **no se toca** |
| Carpeta `004-compras-cuentas-por-pagar` | numeración de **iniciativas**, no del Máster 56 |
| `spec-equivalence-map.md:35` | «**028 CxP y pagos** ↔ `004-compras`» |
| `code-to-specs-map.md:11` | el módulo `purchasing` (tablas `ap_*`) → Máster `015-017, 019, 027, **028**` |
| Máster 56 fila 52 | «**028 · CxP y pagos** · `ap_payments`, `ap_open_items`» |

`open_item_balance` vive en `app/modules/purchasing/service.py` y opera sobre
`ap_open_items`. **Dueño canónico: Máster 56 Spec 028.** Sin conflicto de
identidad: el mapa de equivalencias lo resuelve.

## 1. El defecto

```python
def open_item_balance(item: OpenItem) -> float:
    return round(float(item.original) - float(item.applied), 6)
```

Las columnas son `NUMERIC(18, 2)`; SQLAlchemy las devuelve como `Decimal`. Esta
función las convertía a coma flotante, restaba y redondeaba a seis decimales.

Es exactamente el defecto que `ADR-D0-001` registra con nombre propio:

> `Decimal + float` (**`KQA-100`**, CRITICAL) que SQLite no reveló y que rompió
> factura, pago, cobro…

La Spec 011 lo corrigió en las cantidades y dejó el patrón nombrado —su propio
`_dec` está a sesenta líneas de aquí, con la advertencia en el docstring—. El
motor de saldos nunca lo recibió.

**El `6` no era una política de nadie.** Ninguna fuente lo declara. Era el margen
que la coma flotante necesitaba, y su consecuencia se veía en los llamantes:
`if open_item_balance(target) <= 1e-6: status = "CLOSED"`. Un documento no
cerraba en cero: cerraba «suficientemente cerca de cero».

## 2. La autoridad

| Fuente | Nivel | Qué dice |
|---|---|---|
| `01_Kontrol_Documento_Maestro` | 3 | «**Decimal exacto** — Montos, tasas, porcentajes y cantidades usan precisión controlada» |
| `01_Kontrol_Documento_Maestro` | 3 | «Los saldos **no se editan**; se calculan desde movimientos y aplicaciones» |
| `02_Kontrol_Arquitectura_Funcional` §9 | 3 | «CxC — Saldo = documentos + débitos − cobros − retenciones − créditos» |
| `03_Kontrol_Modelo_de_Datos` §7 | 3 | `Currency: ISO code, name, symbol, **decimals**, active` |
| `ADR-D0-001` | D0 | `KQA-100` como defecto CRÍTICO |

**Precisión**: la fija el maestro de monedas (`Currency.decimal_places`, por
defecto 2), que es la escala de las columnas. No un número escrito a mano.

**Redondeo**: no hace falta decidir ninguno, y por eso no se decide. Los dos
operandos vienen de columnas de escala 2 y su resta es exacta. La única
cuantización que queda existe para que Python y PostgreSQL digan el mismo
número, no para elegir entre dos números posibles.

## 3. Lo que cambia

| Antes | Ahora |
|---|---|
| `open_item_balance → float`, con `round(..., 6)` | `→ Decimal`, resta exacta |
| `_source_available → float` | `→ Decimal` |
| `_reduce_source` sumaba en `float` | suma en `Decimal` |
| `apply_source` mutaba `applied` en `float` | en `Decimal` |
| `<= 1e-6` para cerrar un documento | `<= 0` |
| El aging sumaba en `float` | suma en `Decimal` |
| La varianza de la conciliación triple en `float` | en `Decimal`, con la misma semántica |
| La auditoría guardaba el importe como `float` | como texto exacto |

La semántica no cambia: el saldo sigue siendo «lo que vale menos lo aplicado»,
el cierre sigue ocurriendo cuando no queda nada, y la varianza de la conciliación
sigue significando lo mismo. Lo único que cambia es que ahora es exacto.

### Una cosa que se conserva a propósito

La varianza de impuesto de la conciliación triple se escribía como
`tax_amount − (precio × cantidad × 0.0)`, que es `tax_amount` con más pasos: el
motor espera impuesto **cero** de la orden de compra porque la orden no lo lleva.
Se conserva la cifra y se deja anotado. **Qué impuesto debería esperar la
conciliación triple no lo decide este delta**: es de su dueña.

## 4. Evidencia

| | |
|---|---|
| Pruebas dirigidas | `test_spec028_monetary_balance.py` · **7/7** |
| Guardias estructurales | `test_spec028_architecture.py` · **6/6** |
| Mutación | devolver `float` al saldo hace fallar **5 de 7** |
| CxP · CxC · tesorería · conciliación | **62** pruebas, todas verdes |
| Aritmética monetaria en `float` en el motor | **0** |
| `1e-6` en el motor | **0** |

Las cifras de las pruebas están elegidas a propósito entre las que **no son
representables en binario**: tres aplicaciones de `33.33` sobre `99.99`, y
`0.10 + 0.20` sobre `0.30`. Con `float` no cierran; con `Decimal` sí.

## 5. La invariante, formalizada

> **`MONETARY-BALANCE-INVARIANT`** — todo cálculo monetario canónico de saldos
> usa `Decimal`. Prohibido `float(monto)`, `round(float(...))` y cualquier
> aritmética intermedia binaria. La precisión la fija el maestro de monedas, no
> un número escrito a mano.

Vive en `test_spec028_architecture.py`, que la comprueba sobre las cuatro
funciones que son la autoridad del saldo y sobre la aplicación de notas de CxC.

## 6. Alcance

Delta dirigido. La Spec 028 **no se reabre**: sigue `PARTIALLY_IMPLEMENTED` por
lo que le falta de CxP y pagos, y este delta **no** cambia ese estado. Lo que
cierra es que su motor de saldos —el que comparten cuatro dominios— calcule el
dinero exacto.

`TARGETED DELTA — COMPLETE / CONVERGED`
