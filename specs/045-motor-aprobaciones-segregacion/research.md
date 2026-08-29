# INVESTIGACIÓN — SPEC 045

## 1. Estado del código actual

Inventario verificado de las cuatro implementaciones a sustituir:

| Dominio | Archivo | Mecanismo | Qué le falta |
|---|---|---|---|
| Compras | `purchasing/service.py` | `REQUISITION_TRANSITIONS` y `ORDER_TRANSITIONS` con `SUBMITTED → APPROVED/REJECTED`, más `approval_ref` textual | Política, niveles, cuórum, delegación, obsolescencia, segregación |
| Ventas | `sales/service.py:57` | `ORDER_TRANSITIONS` con `CREDIT_PENDING → APPROVED/REJECTED` y campo `credit_decision` | Todo lo anterior; además la aprobación de crédito no distingue nivel |
| Inventario | `inventory/service.py` | Segregación por campos crea/revisa/aprueba en `InventoryAdjustment` y `StockCount` | Política configurable; la segregación está codificada |
| Regulatorio | `regulatory/models.py` | Tabla `approval_requests` con decisión | Niveles, versionado, delegación, cuórum |

Ninguna de las cuatro versiona la regla aplicada. Ninguna guarda qué política autorizó. En una
fiscalización, ninguna puede responder «bajo qué norma interna se aprobó esto».

## 2. Por qué no reutilizar `regulatory.approval_requests`

Evaluado y descartado en `ADR-D0-002` (alternativa A). Esa tabla se diseñó para un caso concreto
—solicitud de aprobación de un permiso regulatorio— y carece de niveles, política versionada,
delegación y cuórum. Extenderla arrastraría un modelo estrecho a toda la plataforma. Se migra hacia
el motor nuevo, no al revés.

## 3. Diseño de la condición: declarativa frente a expresiones

Se evaluaron tres formas de expresar «cuándo se requiere aprobación»:

| Forma | Auditable | Expresiva | Veredicto |
|---|---|---|---|
| Código por dominio | No | Sí | Es la situación actual; produce divergencia |
| DSL de expresiones libres | Difícil | Máxima | Descartada: una expresión arbitraria no se puede explicar a un contador ni verificar exhaustivamente |
| **Predicados tipados combinados con `AND`, y varias reglas para el `OR`** | **Sí** | Suficiente | **Adoptada** |

El mismo criterio se aplicó en `ADR-D0-005` para la precedencia de precios: preferir lo declarativo
verificable sobre lo expresivo opaco.

## 4. Moneda base y comparación de montos

En una plataforma multimoneda, comparar un monto contra un umbral sin normalizar es un error de
diseño: una orden de 1.000 en una moneda y otra de 1.000 en otra no representan el mismo riesgo.

El motor evalúa **siempre** sobre el equivalente en moneda base usando la **tasa snapshot del
documento**, no la tasa del día de la aprobación. De lo contrario, una misma orden podría requerir
niveles distintos según cuándo se mire, y la solicitud dejaría de ser reproducible.

Fuente de la tasa: `exchange_rates` y el snapshot que cada documento ya conserva (Spec 006).

## 5. Obsolescencia: alcance de la huella

Calcular la huella sobre el documento completo haría que cualquier cambio —una observación, una
fecha de entrega— invalidara aprobaciones en curso. El control se volvería molesto y los usuarios
buscarían la forma de evitarlo.

Se calcula sobre **el subconjunto de campos que participan en las condiciones de las reglas
aplicadas**. Si la regla depende del monto y del centro de costo, cambiar el monto invalida; cambiar
una nota interna no. La huella se almacena junto a la lista de campos que la componen, para que la
decisión sea auditable y no dependa de la implementación vigente.

## 6. Concurrencia

Dos escenarios reales:

1. **Dos aprobadores resuelven el mismo paso a la vez.** Se resuelve con bloqueo de la fila del paso
   dentro de la transacción; la segunda transacción recibe 409 (ADR-013).
2. **Se resuelve el último paso mientras el documento cambia.** La comprobación de huella ocurre
   dentro de la misma transacción que la decisión; si la huella difiere, la solicitud pasa a
   `OBSOLETE` y la decisión se rechaza.

Ambos exigen PostgreSQL para probarse (P21): SQLite ignora `SELECT … FOR UPDATE`.

## 7. Referencias comparativas

El Manual Saint (F2, Nivel 8) documenta autorizaciones por monto y usuario, sin versionado ni
delegación. Se usa como referencia de expectativa funcional del mercado venezolano, **no como
diseño**: su modelo no satisface P5 ni P8.

## 8. Riesgo identificado durante la investigación

Migrar las cuatro implementaciones tiene un riesgo que no es técnico sino operativo: si el motor se
despliega antes de que cada empresa configure sus políticas, **ninguna operación requeriría
aprobación** y el sistema pasaría silenciosamente de «cuatro controles débiles» a «ningún control».

Mitigación adoptada (ver `plan.md` §Migración): la migración crea, para cada implementación actual,
una política equivalente que **reproduce el comportamiento vigente**, y el corte solo se ejecuta con
esa política activa. Nunca se deja el proceso sin política.
