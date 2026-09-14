# SPEC 049 · REVALIDACIÓN DE PREPARACIÓN — DASHBOARD

> 2026-09-13, después del cierre formal de la Spec 013, del delta de la 048, del
> delta de la 004 y de la programación de las deudas `float`.
> Dueño: `specs/009-reportes-auditoria` (`spec-equivalence-map.md` línea 56).
> **Solo revalidación. No se implementa nada.**

## 1. Veredicto

**`SPEC049 — BLOCKED BY OWNER DEPENDENCY`**

No se reutilizó el dato del máster —«023, 034, 037, 038»— sin verificarlo: se
leyó el alcance que la propia Spec declara y se comparó con el estado actual de
cada dueño.

## 2. Qué pretende consumir, según su propia Spec

`spec.md` §6.1 · FR-009-001: «Dashboard con indicadores agregados (**ventas,
compras, tesorería, fiscal**) y vencimientos». FR-009-010: KPIs por módulo,
también **regulatorio**. §1: dependencia de `001` certificada y de `003-008`
implementadas. §3: indicadores, **tareas, alertas** y vencimientos.

## 3. Estado real de cada fuente

| Dominio | Dueñas | Estado | Consecuencia |
|---|---|---|---|
| Ventas y CxC | 029-037 | `COMPLETE / CONVERGED` | lista |
| Tesorería | 038 · 013 | `COMPLETE / CONVERGED` | lista como autoridad; el dashboard actual **no** la usa (§5) |
| Compras y CxP | 015-017, 027, 028 | `PARTIALLY_IMPLEMENTED` | **bloqueo** |
| Inventario | 023 (capacidad convergida), 024-026 | `PARTIALLY_IMPLEMENTED` | parcial |
| Fiscal | 039-043 | `BLOCKED_BY_LEGAL_VALIDATION` (`D0-07`) | **bloqueo** |
| Regulatorio | 044 | `BLOCKED_BY_EXTERNAL_SERVICE` | **bloqueo** |
| Tareas y alertas | 047 | `NOT_STARTED` | **bloqueo** |
| Tasas para equivalentes | 013 · 048 | 013 lista; proveedor automático detenido (OQ-048-01..03) | ver MD-049-01 |

## 4. Cada KPI con su fuente canónica

| KPI | Dueña | Lectura canónica | Moneda | Fecha | Permiso |
|---|---|---|---|---|---|
| Ventas | 034 | facturas emitidas | por moneda del documento | emisión | `reportes:view` |
| CxC | 037 | `customer_balance` / motor de saldos 028 | por moneda | vencimiento | `reportes:view` |
| Compras | 027 | facturas de proveedor | por moneda | contabilización | `reportes:view` |
| CxP | 028 | `aging(PAYABLE)` | por moneda | vencimiento | `reportes:view` |
| Posición de caja | 038 | `cash_position` — por cuenta y moneda, **sin total** | por moneda | real, no previsión | `reportes:view` + alcance de tesorería |
| Documentos fiscales | 042 | emisión fiscal | — | periodo | bloqueado por `D0-07` |
| Despachos bloqueados | 035 · 044 | evaluación regulatoria | — | — | bloqueado por servicio externo |
| Vencimientos | 028 · 043 · 044 | partidas abiertas, periodos, permisos | — | vencimiento | `reportes:view` |
| Tareas y alertas | 047 | — | — | — | **no existe** |

## 5. El dashboard que ya existe · `PREEXISTING`, dueña 049

`reporting/service.py · dashboard` y `pages/DashboardPage.tsx` ya están en el
repositorio y **son un segundo motor de cálculo**, precisamente lo que el
dashboard no debe ser:

1. **`tesoreria_banco` suma todos los `BankTransaction.amount`, de entrada y de
   salida, y de todas las monedas en un solo número.** Contradice a la 038, que
   da la posición por cuenta y moneda, respeta la dirección y se niega a sumar
   monedas.
2. **Ventas y compras suman totales de todas las monedas.**
3. `float` y `round(…, 2)` sobre dinero, contra `MONETARY-BALANCE-INVARIANT`.
4. `GET /reporting/dashboard` exige solo usuario autenticado: **no pide
   `reportes:view`**, que existe en el catálogo.
5. La pantalla pinta cada indicador con `toFixed(2)` y **sin moneda**.

Las pruebas actuales (`test_reporting.py · TestDashboard`) solo comprueban los
totales de ventas y compras y un recuento de vencimientos: **no bendicen** estos
defectos, así que no están sellados. Se corrigen en el ciclo de implementación de
la 049, consumiendo a sus dueñas en vez de recalcular.

El aislamiento entre empresas sí se sostiene: la ruta usa `CompanyContext` y hay
prueba de otra empresa (`test_reporting.py`). Un usuario con acceso a varias
empresas ve la seleccionada; no hay agregación entre empresas.

## 6. Decisiones materiales pendientes

**MD-049-01 · Indicadores en varias monedas.** ¿Se muestran por moneda, o también
en equivalente de moneda funcional? Si hay equivalente, con qué tasa y qué fecha
—y eso depende de **OQ-048-03** (compra o venta; Fecha Operación o Fecha Valor)—.

**MD-049-02 · KPIs fiscales y regulatorios con `D0-07` abierto.** ¿Se ocultan, o
se muestran marcados como no homologados?

## 7. Recuento

| | |
|---|---|
| DEPENDENCY BLOCKERS | **4** — compras (015-017, 027, 028), fiscal (039-043), regulatorio (044), tareas y alertas (047) |
| MATERIAL OQ | **2** — MD-049-01, MD-049-02 |
| UNKNOWN | 0 |
| DATA SOURCE GAPS | **3** — tareas y alertas, libros y cierres fiscales, permisos regulatorios en línea |
| OWNER GAPS | 0 — todo dominio tiene dueña identificada |
| Defectos del código existente | 5 (§5), `PREEXISTING`, dueña 049 |

## 8. Lo que no se hizo

No se ejecutó `/speckit.implement`. No se escribieron rutas, componentes ni
cálculos. El máster se actualiza **solo** en la columna de bloqueo de la 049, con
el alcance verificado.

## 9. Revalidación 2026-09-14 — tras el ciclo de la Spec 047

**Veredicto: `SPEC049 — BLOCKED BY OWNER DEPENDENCY`, sin cambio.**

### Qué cambió

Solo la 047. Recorrió `specify` → `analyze` en `specs/047-notificaciones-tareas`,
**no se implementó** y quedó `BLOCKED BY MATERIAL DECISION` (OQ-047-01 planificador
frente a ADR-009; OQ-047-02 idioma). Definió el contrato que la 049 consumirá
(FR-047-036: no leídas, tareas abiertas, tareas vencidas, alertas activas), pero
ese contrato **no tiene implementación** que leer.

### Qué no cambió

Ningún commit desde `88634a1` toca compras, fiscal, regulatorio, tesorería ni el
dashboard.

### Bloqueos recalculados

| Dominio | Dueñas | Estado | ¿Bloquea? |
|---|---|---|---|
| Compras y CxP | 015-017, 027, 028 | `PARTIALLY_IMPLEMENTED` | Sí |
| Fiscal | 039-043 | `BLOCKED_BY_LEGAL_VALIDATION` (`D0-07`) | Sí |
| Regulatorio | 044 | `BLOCKED_BY_EXTERNAL_SERVICE` | Sí |
| Tareas y alertas | 047 | `BLOCKED_BY_BUSINESS_DECISION` — antes «no iniciada»; ahora espera dos decisiones, no construcción | Sí |

| | |
|---|---|
| DEPENDENCY BLOCKERS | **4** |
| MATERIAL OQ | **2** — MD-049-01 y MD-049-02 (OQ-049-01/02 en el prompt de la 047), sin resolver |
| UNKNOWN | 0 |
| DATA SOURCE GAPS | **3** |
| OWNER GAPS | 0 |
| Defectos del código existente | 5, `PREEXISTING`, sin tocar |

No se implementó nada de la 049 ni se tocó `reportes:view`.
