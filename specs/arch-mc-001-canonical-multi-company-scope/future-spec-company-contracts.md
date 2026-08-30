# CONTRATOS DE EMPRESA PARA LAS SPECS FUTURAS — ARCH-MC-001

## 1. Regla general

> Toda entidad nueva declara su alcance, su autoridad y su ruta antes de existir
> (`FR-MC-080`), y toda Spec que cree datos de empresa prueba con **dos empresas
> del mismo tenant** (`FR-MC-081`).

## 2. Spec 012 · Maestros comerciales — bloqueada

`SPEC 012 APTA_DOCUMENTALMENTE — BLOCKED_BY_ARCH_MC_001`.

Sus nueve entidades, con el alcance que les corresponde:

| Entidad | Alcance | Nota |
|---|---|---|
| `PriceList` | `COMPANY_SCOPE` | Dos empresas del grupo tienen precios distintos: es su razón de ser |
| `PriceListVersion` | `DERIVED` → `price_lists` | — |
| `PriceListItem` | `DERIVED` → `price_list_versions` | — |
| `PricePrecedence` | `COMPANY_SCOPE` | La Spec 012 ya lo dice: la precedencia es **por empresa** |
| `DiscountPolicy` | `COMPANY_SCOPE` | El límite lo fija cada empresa |
| `CreditPolicy` | `COMPANY_SCOPE` | El riesgo es de quien vende |
| `CommercialZone` | `COMPANY_SCOPE` | Territorio de ventas de una empresa |
| `SalesChannel` | **Requiere decisión** | Puede ser del tenant si el grupo comparte canales |
| `PaymentTerm` | **Requiere decisión** | «30 días» puede ser del grupo o de cada empresa |
| `CustomerCommercialTerms` | `COMPANY_SCOPE` | **El punto clave**: ver §3 |

## 3. El contrato que 012 necesitaba y no podía tener

`CustomerCommercialTerms` es la prueba de que el orden es el correcto.

Un mismo tercero puede ser cliente de la empresa A y de la B con **límite de
crédito, lista de precios, condición de pago, vendedor y política de descuento
distintos**. Eso solo se puede modelar si `Party` es identidad compartida y la
relación comercial es de empresa.

Con el modelo actual —donde `parties.company_id` guarda el tenant— la distinción
es imposible: las dos empresas verían la misma relación comercial. La Spec 012
habría nacido con el defecto incorporado en su entidad central.

## 4. Revalidación de 012 tras ARCH-MC-001

Corta y acotada:

1. Confirmar el alcance de las nueve entidades.
2. Resolver el alcance de `SalesChannel` y `PaymentTerm`.
3. Confirmar `Party` compartida frente a relación comercial de empresa.
4. Añadir dos empresas a su matriz de aceptación (`FR-MC-081`).
5. Reejecutar `/speckit.analyze 012`.

**No** se rehace su ciclo documental: 47 FR, 45 criterios y 83 tareas siguen
siendo válidos.

## 5. Otras Specs futuras

| Spec | Alcance previsible |
|---|---|
| 018 Importaciones | Empresa: el expediente es de quien importa |
| 019 Recepción · 020 Incidencias | Derivadas de almacén o de la orden |
| 028 CxP · 037 CxC | Empresa: el saldo es de quien debe o cobra |
| 038 Tesorería | Empresa por cuenta o caja |
| 047 Notificaciones | Del tenant; el evento transporta la empresa |
| 050 Reportes | Debe permitir por empresa **y** consolidado del tenant sumando empresas explícitas |

> El consolidado se construye **sumando empresas**, nunca obteniendo datos
> mezclados sin propiedad (`§167`).
