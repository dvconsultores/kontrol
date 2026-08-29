# POLÍTICA DE MIGRACIÓN `0018` — CLASIFICACIÓN DE REFERENCIAS HUÉRFANAS

**Spec 008 · Control 1 del Gate pre-implementación · Normativo**

Esta política es vinculante para la migración `0018_location_fk_and_legacy` y para
cualquier migración futura de KONTROL que imponga integridad referencial sobre
columnas que ya contienen datos.

---

## 1. Regla raíz

> **R-008-4.** Está **prohibido** convertir `location_id` inválido a `NULL` de
> forma automática o indiscriminada con el único fin de que la migración termine.
> Toda referencia inválida debe **clasificarse** antes de tocarse, y la acción
> aplicada se deriva de su clase, nunca de la conveniencia de la ejecución.

Anular una referencia es una **decisión sobre el dato histórico**, no un detalle
de implementación. El Principio 5 la somete a justificación explícita; el
Principio 23 obliga a preservar lo que no puede reconstruirse.

---

## 2. Las cuatro clases

Cada fila de `inventory_balances` y `stock_count_lines` con
`location_id` no nulo se clasifica en exactamente una clase.

### A · `VALID_REFERENCE`

La ubicación referida existe y pertenece a la misma empresa.

| | |
|---|---|
| **Acción** | Conservar sin cambios |
| **Escribe** | Nada |
| **Reporta** | Solo el recuento agregado |

### B · `RECONSTRUCTIBLE_ORPHAN`

La referencia es técnicamente inválida pero puede reconstruirse de forma
**determinista y demostrable** con información ya presente en la base.

Una reconstrucción es admisible **solo** si cumple las tres condiciones:

1. **Determinista** — el mismo estado de base produce siempre el mismo resultado.
2. **Unívoca** — resuelve a exactamente **una** ubicación candidata. Dos o más
   candidatas degradan la fila a la clase C o D según su criticidad; **nunca se
   elige "la más probable"**.
3. **Demostrable** — la regla que la resuelve se puede enunciar y auditar.

Fuentes admitidas para reconstruir, en este orden:

| Orden | Fuente | Condición |
|---|---|---|
| 1 | El `location_id` existe pero fue **renombrado/reemitido** y hay rastro directo en el propio registro de migración de la fila | Traza explícita, no inferencia |
| 2 | `inventory_movements.location_id` del mismo documento origen (es FK real desde el inicio, luego es un dato íntegro) | Un único `location_id` distinto para ese documento |
| 3 | La ubicación existe en otro almacén de **la misma empresa** y el registro no tiene almacén contradictorio | Unívoca |

**No es fuente admisible** ningún texto libre de `zone`, `aisle` o `rack`: eso es
inventar jerarquía (§4).

| | |
|---|---|
| **Acción** | Reparar la referencia |
| **Escribe** | `location_id` nuevo; `legacy_location_id` con el valor anterior |
| **Reporta** | Fila, tabla, valor anterior, valor nuevo, regla aplicada |

### C · `NON_RECONSTRUCTIBLE_BUT_NULL_ALLOWED`

No puede reconstruirse, **y** el modelo histórico admite legítimamente la
ausencia de ubicación para esa fila.

Se admite anular **solo si se cumplen todas**:

1. La columna es `NULL`-able en el modelo actual y lo era cuando la fila se creó.
2. El registro pertenece a un almacén con `location_managed = false`, **o** es
   anterior a que ese almacén gestionara ubicaciones, **o** su saldo es cero y no
   tiene movimientos asociados.
3. Anular **no** altera ningún total, ni el Kardex, ni un conteo cerrado, ni una
   cifra ya reportada.

Si alguna de las tres no se cumple, la fila **no** es clase C: es clase D.

| | |
|---|---|
| **Acción** | `location_id → NULL` |
| **Escribe** | `NULL`; `legacy_location_id` conserva el valor original **siempre** |
| **Reporta** | Fila, tabla, valor legacy, las tres condiciones evaluadas, motivo |

> El valor legacy **nunca** se pierde. Anular la FK no es borrar el dato: es
> retirarlo de la integridad referencial conservando su rastro.

### D · `CRITICAL_NON_RECONSTRUCTIBLE`

No puede reconstruirse **y** perderla alteraría semántica histórica, inventario,
trazabilidad o integridad.

Indicadores suficientes (basta uno):

- La fila tiene saldo distinto de cero.
- Pertenece a un conteo cerrado o a un ajuste aprobado.
- Está referida por un movimiento, un documento fiscal o un cierre.
- Pertenece a un almacén con `location_managed = true` y ubicación obligatoria.
- Cae en clase B pero con **más de una** candidata (ambigüedad sobre dato vivo).

| | |
|---|---|
| **Acción** | **`BLOCK_MIGRATION`** |
| **Escribe** | Nada — la transacción revierte |
| **Reporta** | Reporte completo antes de abortar, con las filas críticas identificadas |

> **R-008-5.** Ante una sola referencia de clase D, `0018` **aborta de forma
> controlada** antes de introducir cualquier pérdida. La migración no decide
> sobre dato crítico irrecuperable: lo eleva a una persona.

---

## 3. Orden de ejecución obligatorio

`0018` ejecuta en este orden, dentro de una única transacción:

1. **Inventariar** — recorrer las dos tablas y clasificar cada fila. Sin escribir.
2. **Evaluar el bloqueo** — si `critical_orphans > 0`: emitir el reporte completo
   y **abortar**. Nada se ha escrito todavía.
3. **Reparar** las clase B.
4. **Anular** las clase C, preservando `legacy_location_id`.
5. **Copiar** `zone`/`aisle`/`rack` a `legacy_path` (§4).
6. **Imponer** las dos claves foráneas.
7. **Persistir** el reporte y confirmar.

La clasificación precede a toda escritura. Es lo que permite abortar sin daño.

---

## 4. `legacy_path` — sin invención de jerarquía

Se mantiene sin cambios la decisión CL-008-15:

> Los textos libres `zone`, `aisle` y `rack` **no** se transforman
> automáticamente en `WarehouseZone`, `WarehouseAisle`, `WarehouseRack` ni
> `WarehouseLevel`. Se conservan literalmente en `legacy_path`.

Derivar entidades estructurales de texto ambiguo **inventaría datos**: `"A"`,
`"a"`, `"Zona A"` y `"A "` no son demostrablemente la misma zona, y decidir que
lo son es una afirmación de negocio que la migración no tiene autoridad para
hacer. Crear la jerarquía estructurada es una decisión explícita del cliente,
posterior y auditada.

Corolario ya enunciado y aquí reforzado: **`legacy_path` tampoco es fuente
admisible para reconstruir una referencia de clase B.**

---

## 5. Reporte de migración

`0018` produce un reporte persistido y auditable. Estructura mínima:

### Cabecera

| Campo | Tipo |
|---|---|
| `migration_id` | `0018_location_fk_and_legacy` |
| `executed_at` | `timestamptz` |
| `database_version` | Versión del motor |
| `total_rows_checked` | Entero |
| `valid_references` | Entero |
| `orphan_references` | Entero |
| `reconstructed_references` | Entero |
| `nulled_with_justification` | Entero |
| `critical_orphans` | Entero |
| `migration_blocked` | Booleano |

Invariante verificable: `valid + reconstructed + nulled + critical = total`.

### Detalle — una fila por referencia modificada o crítica

| Campo | Contenido |
|---|---|
| `table_name` | `inventory_balances` · `stock_count_lines` |
| `column_name` | `location_id` |
| `row_id` | Identificador de la fila afectada |
| `company_id` | Empresa, para acotar la revisión |
| `legacy_value` | `location_id` original |
| `new_value` | Valor resultante, o `NULL` |
| `classification` | `A` · `B` · `C` · `D` |
| `action_applied` | `KEPT` · `RECONSTRUCTED` · `NULLED` · `BLOCKED` |
| `justification` | Regla concreta que produjo la decisión |

Las clase A **no** generan detalle: solo cuentan en el agregado. El reporte
registra lo que cambió y lo que bloqueó, no lo que quedó intacto.

### Minimización

El reporte contiene **solo** identificadores técnicos y la justificación. No
incluye nombres de producto, cantidades, importes, datos de tercero ni ningún
otro dato personal o comercial: no son necesarios para auditar qué ocurrió con
una referencia.

### Auditabilidad posterior

Debe ser posible responder, para cualquier fila modificada y en cualquier momento
posterior: **qué valor tenía, qué valor tiene, por qué cambió y bajo qué clase.**
`legacy_location_id` en la propia fila y el detalle del reporte lo garantizan por
duplicado.

---

## 6. Idempotencia y reversión

- Una segunda ejecución de `0018` sobre una base ya migrada **no** reclasifica ni
  reescribe: las FK ya existen y `legacy_location_id` ya está poblado.
- El `downgrade` retira las FK y conserva `legacy_path` y `legacy_location_id`.
  **No** restaura los valores anulados automáticamente: quedan disponibles en
  `legacy_location_id` para una restauración explícita y decidida por una persona.
- La migración **no** se ejecuta nunca en modo `--sql` como evidencia: el modo
  offline no puede clasificar filas porque no lee datos.

---

## 7. Qué se prueba

Los seis casos del Control 1, todos sobre PostgreSQL real, están en
`test-plan.md` §4.

| Qué | Dónde |
|---|---|
| Implementación del clasificador y del reporte | T-008-024, 024a..024f (F2) |
| Pruebas de los seis casos | T-008-062..067 (F5) |
| Criterios de aceptación | AC-008-25 a AC-008-30 |
