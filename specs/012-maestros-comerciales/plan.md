# PLAN — SPEC 012

## 1. Orden de construcción, y por qué

| Fase | Contenido | Por qué va aquí |
|---|---|---|
| **F1** | Maestros base: `PaymentTerm`, `CommercialZone`, `SalesChannel` | Son independientes entre sí y de todo lo demás; sin ellos el cliente no puede referenciar nada |
| **F2** | `PriceList` · `PriceListVersion` · `PriceListItem` | El núcleo. La versión antes que el ítem: sin vigencia, un precio no significa nada |
| **F3** | **Resolución de precio** — autoridad única | **Antes que la API**, como 046 puso la autorización antes que sus endpoints. Un endpoint de precio sin precedencia declarada sería un precio arbitrario con URL |
| **F4** | `DiscountPolicy` + integración con el motor 045 | Depende de F3: el límite se mide contra un precio resuelto |
| **F5** | `CreditPolicy` y condiciones comerciales del cliente | Depende de F1; sustituye los cuatro textos libres por FK |
| **F6** | **Snapshot comercial** en las líneas transaccionales | `P23`: cuanto más tarde, más documentos emitidos sin origen. Va **antes** que la API, igual que F4 fue antes que F6 en la Spec 011 |
| **F7** | API | Cuando ya hay autoridad, política y snapshot que exponer |
| **F8** | Pruebas de backend | Precedencia, empates, inmutabilidad, concurrencia, multiempresa |
| **F9** | Frontend | Cinco pantallas de maestro |
| **F10** | Legado, E2E y cierre | Anotación, revisión manual, E2E, convergencia |

> **F6 antes que F7 no es una preferencia.** Es la lección de la Spec 011: cada
> día que una línea se escribe sin su origen amplía una deuda que ninguna
> migración repara.

## 2. Módulo

Nuevo: `app/modules/commercial/`.

```
commercial/
  models.py     — 9 entidades
  pricing.py    — autoridad única de resolución (equivale a uom.py en la Spec 011)
  policies.py   — descuento y crédito
  api.py        — endpoints de maestro
```

**No** se mete en `master_data` ni en `sales`: el precio no es un atributo del
producto ni un paso de la venta; es una capacidad transversal con dueño propio.

## 3. Lo que se toca de otras Specs, y con qué límite

| Módulo | Cambio | Límite |
|---|---|---|
| `master_data.Customer` | + 5 FK, + `legacy_*` conservando el texto | **No** se crea entidad paralela |
| `master_data.Supplier` | + FK de condición de pago | ídem |
| `sales.SalesQuote` / `SalesOrder` | + FK de lista, + campos de snapshot | **No** se toca su flujo |
| `sales.*_lines` / `purchasing.*_lines` | + snapshot de origen del precio | **No** se cambia `unit_price` existente |
| `approvals` | **Ningún cambio** | Se consume su API, como hizo 046 |

## 4. Migraciones previstas

| Migración | Qué hace | Riesgo |
|---|---|---|
| `00XX_commercial_model` | Crea las 9 tablas | Bajo |
| `00XX_commercial_customer_fk` | Añade FK a `customers` / `suppliers`, **conservando** el texto en `legacy_value` | Medio — no se borra nada |
| `00XX_commercial_snapshot_columns` | Añade columnas de snapshot a las líneas | Medio — todas anulables |
| `00XX_commercial_legacy_annotation` | **Anota** las cadenas y las clasifica. **No crea maestros** | Alto si se hiciera mal; por eso solo anota |

La última sigue el patrón de `0024` (Spec 046): lee datos, reporta, comprueba
sus invariantes y **aborta** si creara algo que no debía.

## 5. Decisiones de modelado ya cerradas por el ADR

| Decisión | Fuente |
|---|---|
| Versionado, no edición en sitio | `R-D0-05-6` |
| Precedencia como dato | `R-D0-05-1` |
| Empate determinista o error | `R-D0-05-2` |
| `PaymentTerm` maestro, no cadena | `R-D0-05-3` |
| Condición ≠ política de crédito | `R-D0-05-4` |
| Snapshot con la versión que produjo el precio | `R-D0-05-5` |
| Comisiones reservadas | `ADR-D0-005 §Comisiones` |

Esta Spec **no vuelve a decidirlas**.

## 6. Riesgo principal y cómo se contiene

El riesgo no es técnico: es que 012 se convierta en un CRUD y el precio siga
tecleándose. Se contiene con `FR-012-014` (autoridad única) y con
`AC-012-*`, que exigen que una cotización tome el precio del maestro y que
cambiar el maestro no altere lo aprobado.

Si al terminar sigue siendo posible emitir una línea con precio libre sin
`pricing_source` justificado, la Spec habrá fallado aunque todas las tablas
existan.

---

# PLAN DE IMPLEMENTACIÓN — POSTERIOR A ARCH-MC-001

**Este plan no se ejecuta en este ciclo.** Describe el trabajo que la
autorización futura habilitaría.

| Ola | Qué | Nota |
|---|---|---|
| 1 | Esquema y alcances | Los once modelos con `__scope__` y `__scope_authority__` desde el primer commit, no añadidos después |
| 2 | `CompanyContext` y permisos | Se **consume** la autoridad canónica; no se crea una nueva |
| 3 | Listas de precios | Maestro directo de empresa |
| 4 | Versiones | Exclusión de solape en la base, no en el servicio |
| 5 | Ítems | La derivada de más riesgo: tres niveles |
| 6 | Políticas de descuento | Nacen vacías |
| 7 | Condiciones comerciales del cliente | Extiende `customers` por FK |
| 8 | Condiciones de pago y crédito | Comisiones quedan reservadas |
| 9 | Unidades y presentación | Se respeta la Spec 011; no se redefine el factor |
| 10 | Moneda y tasa | La tasa se congela en la transacción |
| 11 | Aprobación | Spec 045; no se crea un segundo motor |
| 12 | API y OpenAPI | `X-Kontrol-Company` en las 100% de las operaciones |
| 13 | Frontend | Estándar de maestros vigente |
| 14 | Seguridad de rutas hijas | Casos N-01 a N-09 |
| 15 | Auditoría | Actor, tenant y empresa |
| 16 | Migraciones | A partir de `0039` |
| 17 | Integridad en PostgreSQL | Casos B-01 a B-10 |
| 18 | A/B multiempresa | Casos C-01 a C-04 por maestro |
| 19 | Regresión | Fallos inesperados 0; saltos con responsable |
| 20 | Convergencia de la 012 | — |

## El orden no es negociable en un punto

La ola 1 pone el alcance **antes** que cualquier ruta. Al revés —tablas primero,
alcance después— es como llegó KONTROL a tener 90 columnas llamadas `company_id`
que guardaban el tenant.

Y la ola 14 no es la última defensa sino una comprobación: si las olas 3 a 8 se
escriben con el contrato de `nested-resource-security-contract.md`, la 14 no debe
encontrar nada. Si encuentra algo, el fallo está en las anteriores.
