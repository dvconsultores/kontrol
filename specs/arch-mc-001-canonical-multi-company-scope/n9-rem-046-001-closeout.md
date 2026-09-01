# CIERRE DE REM-046-001

## 1. Qué decía la remediación

Que la Spec 046 se declaró `COMPLETE_100` con una capacidad rota: **19 tipos
registrados y uno probado**. Y que faltaban cuatro entradas —`Payment`,
`BankTransaction`, `CashSession`, `Reconciliation`— por las que las Specs 028 y
038 quedaban marcadas `STILL_BLOCKED_BY_046`.

Su frase de cierre resume la fase mejor que cualquier resumen: *el registro
existía; la capacidad, no*.

## 2. Su premisa se resolvió en otro sitio

El documento concluía que 16 de los 19 no eran vinculables porque cinco módulos
guardaban el `tenant_id` en una columna llamada `company_id`. Ofrecía dos
caminos:

- **A** — normalizar los cinco módulos. «Es lo correcto a largo plazo y es
  enorme […] no cabe en una remediación puntual y no es de 046.»
- **B** — que el registro declarara el ámbito de cada consumidor. «Del orden de
  quince líneas más pruebas.»

Recomendaba B por tamaño.

**Se hizo A.** No como remediación de 046, sino como ARCH-MC-001 entera: N5
corrigió los escritores en los cinco módulos, N7 puso las claves foráneas.
Medido hoy en el catálogo, `parties`, `purchase_orders`, `sales_orders`,
`permit_instances`, `stock_counts` y `catalog_items` tienen `company_id` con
referencia real a `companies`.

El supuesto del registro cerrado —que `company_id` significa empresa— **ahora es
cierto**. El camino B no se implementa, y conviene decir por qué: no se descartó,
se quedó sin causa. Añadir hoy un campo que distinga empresa de tenant
describiría una ambigüedad que ya no existe, y sería deuda nueva el día que
alguien lo leyera y creyera que aún hace falta.

## 3. Las cuatro entradas

Verificadas contra el modelo vigente, no contra el informe histórico:

| Modelo | Tabla | PK | Empresa | Clave foránea | Registrado | Probado |
|---|---|---|---|---|---|---|
| `Payment` | `ap_payments` | `id` | `company_id` | sí | ✅ | ✅ |
| `BankTransaction` | `bank_transactions` | `id` | `company_id` | sí | ✅ | ✅ |
| `CashSession` | `cash_sessions` | `id` | `company_id` | sí | ✅ | ✅ |
| `Reconciliation` | `reconciliations` | `id` | `company_id` | sí | ✅ | ✅ |

## 4. La cardinalidad

| | |
|---|---:|
| Registrados antes de N9 | 19 |
| Añadidos | 4 |
| **Total** | **23** |
| Probados con entidad real | **23** |

El «19/19» del encargo y las «cuatro entradas nuevas» de la remediación no se
contradicen: responden a preguntas distintas. Cuántos hay hoy y cuántos debe
haber al terminar.

## 5. Criterio de cierre, cumplido

La remediación no se cierra porque se añadieran cuatro entradas. Se cierra
porque:

| Condición | Estado |
|---|---|
| `Payment` registrado **y** con comportamiento probado | ✅ |
| `BankTransaction` ídem | ✅ |
| `CashSession` ídem | ✅ |
| `Reconciliation` ídem | ✅ |
| Los 23 con entidad real persistida | ✅ |
| Los 23 con aislamiento entre empresas | ✅ |
| Los 22 con empresa, con aislamiento entre tenants | ✅ |
| Registro cerrado ante tipos inventados | ✅ |
| `STILL_BLOCKED_BY_046` | **0** |

## 6. Estado

**`REM-046-001 CLOSED`**

Cerrada dentro de la fase N9 de ARCH-MC-001, como el propio documento previó.
