# N10 — REVALIDACIÓN DOCUMENTAL DE LA SPEC 012

> Solo revalidación. **No se implementó nada de la Spec 012** y no se ejecutó
> `/speckit.implement 012`.

## Veredicto

**`SPEC 012 — DOCUMENT UPDATE REQUIRED BEFORE IMPLEMENTATION`**

No está bloqueada y no está lista. Son dos cosas distintas y conviene no
juntarlas.

## 1. El motivo del bloqueo ya no existe

La Spec 012 se bloqueó con un motivo concreto y verificable:

> «Sobre el modelo actual —donde `parties.company_id` guarda el tenant—
> `CustomerCommercialTerms` no podría distinguir la relación comercial de la
> empresa A de la de la B. Nacería con el defecto en su entidad central.»

Medido hoy:

| Entidad | Alcance | `company_id` | Referencia |
|---|---|---|---|
| `parties` | COMPANY | obligatoria | `companies.id` |
| `customers` | COMPANY | por ruta `party_id → parties` | — |
| `suppliers` | COMPANY | por ruta `party_id → parties` | — |
| `catalog_items` | COMPANY | obligatoria | `companies.id` |

`CustomerCommercialTerms` **sí** puede distinguir hoy la relación de A de la de
B. La causa del bloqueo está resuelta en origen.

## 2. La auditoría original sigue siendo exacta

Se reverificó contra el código, no contra el informe. Ninguna de las nueve
entidades existe: `PriceList`, `PriceListVersion`, `PriceListItem`, `PriceRule`,
`PaymentTerm`, `CommercialZone`, `SalesChannel`, `DiscountPolicy`,
`CreditPolicy`. Ninguna tabla, ninguna clave foránea, ninguna vigencia.

Y sigue sin haber `price_1`..`price_5`: el problema nunca fue un maestro mal
modelado sino la ausencia de maestro. El precio y el descuento se siguen
tecleando en `Numeric(18,2)` sin origen ni regla.

## 3. Lo que sí hay que actualizar antes de implementar

**a) La cabecera de bloqueo es falsa a partir de ahora** y nombra un estado que
la gobernanza ya no usa: exige `ARCH-MC-001 COMPLETE_100`, y el artefacto final
dice `COMPLETE / GLOBALLY CONVERGED`. Se actualiza.

**b) `data-model.md` es anterior al contrato de ARCH-MC-001.** Menciona
`company_id` siete veces y no menciona ni una vez `__scope__`,
`__scope_authority__`, `CompanyContext`, `X-Kontrol-Company` ni
`UniqueConstraint`. Sus nueve entidades tienen que nacer declarando:

- `__scope__ = Scope.COMPANY` en las nueve;
- `company_id` con clave foránea real a `companies` y **no anulable**, salvo que
  alguna admita una versión de plataforma, en cuyo caso el nulo es un
  estrechamiento y hay que decirlo;
- las derivadas —líneas de lista, ítems de precio— con `__scope_authority__` y
  una ruta obligatoria, no anulable;
- unicidad **por empresa**: el código de una lista de precios se repite entre
  empresas del mismo grupo, y una unicidad global lo impediría.

**c) `contracts/` tiene que declarar la cabecera de empresa** en toda operación
de estos maestros, que es lo que hace `get_company_context`.

**d) Toda ruta que reciba un identificador por la URL tiene que ver el
contexto.** Es el hallazgo principal de N10 y afecta directamente a la forma de
la 012: una lista de precios con ítems y versiones genera exactamente el patrón
`POST /price-lists/{id}/items` que produjo nueve de los doce defectos.
`test_ninguna_ruta_recibe_un_id_de_empresa_sin_ver_el_contexto` lo hará fallar
en construcción, que es donde debe fallar.

**e) `test-plan.md` debe incluir el par A/B por entidad**, con `mundo` como
arnés: crear en A, intentar desde B, exigir bloqueo. No basta con probar que la
lista de precios funciona.

## 4. Lo que NO hay que cambiar

El alcance funcional, las nueve entidades, sus relaciones y los criterios de
aceptación siguen siendo válidos. La revalidación no encontró ningún blocker
material ni ninguna contradicción con la arquitectura final.

## 5. Estado resultante

`SPEC 012 — DOCUMENT UPDATE REQUIRED BEFORE IMPLEMENTATION`

No se autoriza la implementación. Esa decisión es del usuario y corresponde al
siguiente ciclo.
