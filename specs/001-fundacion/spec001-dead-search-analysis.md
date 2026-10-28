# SPEC 001 · Delta dirigida — UI-BUSQUEDA-MUERTA · **SE DETIENE EN CLARIFY**

> **Estado posterior (2026-10-28, SHARED-CORE-P0-HARDENING-05):** OQ-2 (Existencias) se resolvió como PDD-API-11. `q` busca por código o nombre del producto (hoy la FK es `catalog_items.id`, un solo salto) y cada fila publica la identidad del producto. UI-BUSQUEDA-MUERTA queda **cerrada**. Ver `spec001-strict-api-input-contract-delta.md`.


**Fecha** 2026-09-24 · **Dueña** SPEC001 — Fundación (`specs/001-fundacion`, dueña de
`FR-001-065` y del contrato transversal de listados) · **Coduelas** SPEC007 (empresas),
SPEC012 (auditoría), SPEC023 (existencias) · **Base** `eaa93fe` · **Rama** `develop`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `eaa93fe` |
| `ACTUAL_HEAD` | `eaa93fe` — **coincide** |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_EAA93FE` | **0** |
| Árbol | limpio salvo los dos artefactos de auditoría sin seguimiento, **preservados** |

## 2. Veredicto, por delante

**Tres pantallas, tres situaciones distintas. Una decidida, dos no.**

| Pantalla | ¿Existe contrato de que haya búsqueda? | ¿Decide el contrato sobre qué campos? | Veredicto |
|---|---|---|---|
| Empresas | **Sí** (`FR-001-065`) | **Sí**, por analogía directa con `FR-002-042` | **LISTA PARA IMPLEMENTAR** |
| Auditoría | **Sí** | **No** — y además el conjunto que buscaría hoy no está autorizado | **MATERIAL** |
| Existencias | **Sí** | **No** — la regla devuelve el conjunto vacío | **MATERIAL** |

Como el encargo ordena detenerse si elegir los campos buscables es en sí una decisión
material, y el gate maestro detiene el ciclo con `MATERIAL OQ > 0`, **no se implementa
nada**: ficheros de producto = 0, esquema = 0, migraciones = 0.

Lo que sí se entrega es el trabajo hecho: las tres búsquedas reproducidas en la API y en
el navegador, el contrato localizado, la regla destilada de los dos buscadores que sí
funcionan, el conjunto de campos de Empresas ya resuelto, y **tres defectos nuevos** que
estaban tapados debajo de la caja de Auditoría, uno de ellos una fuga entre inquilinos.

## 3. Lo que hace hoy cada caja, medido

`evidence/dead-search/comportamiento.txt` · `evidence/dead-search/en-el-navegador.txt`

```
  companies    q=''  -> 1 empresa     q='ZZZNOEXISTE' -> 1 empresa
  audit/events q=''  -> total 18      q='ZZZNOEXISTE' -> total 18
  balances     q=''  -> total 0       q='ZZZNOEXISTE' -> total 0
  terceros     q=''  -> total 1       q='ZZZNOEXISTE' -> total 0   <- el que sí filtra
```

Y en un navegador real, entrando por los enlaces del menú con sesión `admin`/`DEMO`:

```
EMPRESAS     placeholder "Buscar en esta pantalla…"   filas 1 -> 1   la caja NO filtra
AUDITORIA    placeholder "Buscar en esta pantalla…"   filas 0 -> 0   la caja NO filtra
                                                                     y la tabla nunca pinta filas
EXISTENCIAS  placeholder "Buscar por producto…"       filas 0 -> 0   la caja NO filtra
```

Ninguno de los tres endpoints declara `q`; los tres responden 200 y devuelven el conjunto
entero. El usuario no tiene forma de notarlo.

## 4. El contrato, y hasta dónde llega

`evidence/dead-search/contrato-y-precedentes.txt`

Que la búsqueda **exista** es contractual y no admite discusión: `FR-001-065` (P0) exige
«búsqueda general» en los DataTables, `api-contracts.md` declara «Listados con `q`,
`status`, `sort`, `page`, `page_size`», y DOC-08 §10 fija el comportamiento de la caja
—una por pantalla, debounce de 300-500 ms, ejecución en backend—. En esto esta delta se
diferencia de `API-QUERY-SILENCIOSA`, donde no existía contrato ninguno.

Lo que el contrato **no** dice en ninguna parte es sobre qué columnas se busca. Lo más
cercano es DOC-08 §10.1 («Prioridad 1: identificador, nombre, estado y acciones») y un
único FR que nombra campos, y solo para su módulo: `FR-002-042`, «búsqueda general
(RIF/nombre/código)».

## 5. La regla, destilada de lo que ya funciona

Hay dos buscadores implementados y vivos:

| Endpoint | Pinta | Busca |
|---|---|---|
| `master_data/api.py:189-201` terceros | Código, Nombre, RIF, Roles, Estado | `name`, `tax_id`, `code` |
| `inventory/api.py:244-255` kardex | Fecha, Producto, Tipo, Cantidad, Costo, Documento, Estado | `document_ref`, `id` |

> **Regla** — `q` busca los **nombres** y los **identificadores de negocio** propios de la
> entidad que el listado ya publica. Quedan fuera: lo que ya tiene un filtro dedicado, los
> estados y clasificaciones, las cantidades y las fechas.

Que esto es una regla y no una excusa se comprueba sola: aplicada a ciegas reproduce
exactamente los dos conjuntos ya implementados. Y el placeholder de terceros se la declara
al usuario palabra por palabra: «Buscar por nombre, RIF o código…».

## 6. Empresas — **decidida**

`Company` publica `code`, `legal_name`, `trade_name`, `rif`, `status`. La regla da:

```
  EMPRESAS_Q_FIELDS = code, legal_name, trade_name, rif
```

`status` queda fuera por ser estado, igual que en terceros. Es **la misma terna que
`FR-002-042` ya decidió** —RIF, nombre, código— sobre una entidad de la misma forma, con
el segundo nombre que la entidad tiene. No hay nada que inventar aquí.

Queda preparado, para ejecutarlo en una sola pasada en cuanto se autorice: `q` en
`list_companies` aplicado **después** del filtro de `accessible_company_ids` y **antes** de
cualquier recorte; el placeholder pasa a nombrar los campos, como en terceros; y la
pantalla necesita además el sobre paginado que el contrato de listados declara, porque hoy
`list_companies` devuelve un array plano sin `total` ni `page`.

## 7. Auditoría — **material**, y con tres defectos debajo

`AuditEvent` no tiene nombre, y de sus identificadores `action`, `entity_type` y
`entity_id` **ya tienen filtro dedicado**, así que la regla los excluye igual que excluye
`status` en terceros. Queda `request_id` —el identificador que DOC-08 §11 manda enseñar al
usuario ante un error— y luego un borde que ningún precedente cubre: `user_id` y `source`
son identificadores ajenos y clasificaciones sin filtro propio, e `id` entra en kardex pero
no en terceros.

```
  AUDITORIA_Q_FIELDS = {request_id}  ó  {request_id, user_id, source, id}
```

La regla no lo decide, y las dos respuestas dan cajas que significan cosas distintas.

Y al reproducir esta pantalla apareció lo que la caja muerta tapaba
(`evidence/dead-search/auditoria-lo-que-habia-debajo.txt`):

1. **La tabla no pinta nunca ninguna fila.** El servidor devuelve un sobre
   `{items, total, page, page_size}`; `AuditoriaPage.tsx:30` lo pide como `AuditEvent[]` y
   `:46` se lo pasa tal cual a `DataTable`. Comprobado con un render real: no lanza, no
   pinta. En el navegador, `/audit/events?q=` responde 200 con 20 eventos y la tabla
   muestra 0 filas. `tsc` no puede verlo: `apiFetch` es genérico y quien llama afirma el
   tipo.
2. **La columna «Fecha» lee un campo que no llega.** El evento publica `event_time`;
   la pantalla y `api/types.ts:52` declaran `created_at`.
3. **El listado no filtra por tenant.** `audit/api.py:18-55` solo exige
   `require_permission("audit","view")`. Medido: de los 20 eventos de la base, 1 es del
   tenant `DEMO2`, y **se le devuelve a un administrador de `DEMO`**. Contradice
   `FR-001-032` y `FR-001-033`.

El tercero importa para esta delta por una razón concreta: el orden que el propio encargo
fija es RequestContext → alcance → permisos → filtros → `q` → orden → paginación. Poner
`q` aquí sería filtrar un conjunto que **antes de `q` ya está mal**. Corregir el alcance
decide quién ve qué, y eso no lo decide esta delta.

## 8. Existencias — **material**: no hay ni una columna que buscar

`InventoryBalance` publica `id`, `company_id`, `warehouse_id`, `location_id`,
`product_id`, `lot_id`, `serial_id`, `state`, `qty_on_hand`, `qty_reserved`,
`qty_available`, `last_rebuilt_at`. Todo es UUID con filtro dedicado, un enum con filtro
dedicado, tres cantidades y una fecha. **Nombres: ninguno. Identificadores de negocio:
ninguno.** La regla devuelve el conjunto vacío.

La caja, mientras tanto, promete «Buscar por producto…», y la columna «Producto» enseña
hoy un UUID crudo. El texto del producto no está en el listado ni a un salto de él:

```
  inventory_balances.product_id -> products.item_id -> catalog_items.code / .name
```

`products` no tiene ni `code` ni `name`: están dos saltos más allá. Hacer que la caja
cumpla lo que promete exige decidir dos cosas que hoy nadie ha decidido: **(a)** que la
búsqueda general alcanza el texto de una entidad *relacionada* —algo que no hace ningún
endpoint de KONTROL— y **(b)** publicar la identidad del producto en cada fila, porque si
no el usuario no puede leer por qué una fila coincidió. (b) es un cambio de payload en un
listado P0.

Y el contrato del módulo describe esta consulta **por filtros**, no por texto:
`FR-003-012` (P0) y `US-003-001` enumeran producto, almacén, ubicación, lote, serial,
estado y vencimiento. Frente a ellos, `FR-001-065` exige una búsqueda general en todo
DataTable. Los dos son P0 y son de dueñas distintas.

## 9. `/speckit.clarify` — las dos preguntas que detienen el ciclo

> **OQ-1 · Auditoría.** ¿Sobre qué campos busca la caja de `/audit/events`: solo
> `request_id`, o también `user_id`, `source` e `id`? Y antes de eso: ¿sobre qué conjunto
> busca, si hoy el listado no filtra por tenant?

> **OQ-2 · Existencias.** ¿Qué significa «búsqueda general» en un listado cuyo contrato
> define la consulta por filtros dedicados y que no publica ni una columna de texto?
> ¿Alcanza `q` el texto de la entidad relacionada —con la identidad del producto publicada
> en la fila— o esta pantalla no tiene búsqueda general y lo que sobra es la caja?

| Matriz del encargo | Empresas | Auditoría | Existencias |
|---|---|---|---|
| El contrato exige la búsqueda | sí | sí | sí |
| El contrato decide los campos | **sí** | no | no |
| La regla de los precedentes decide | **sí** | parcialmente | **no: conjunto vacío** |
| ¿Decisión material? | **no** | **sí** | **sí** |

## 10. Hallazgos nuevos, registrados y no absorbidos

- **`AUDIT-EVENTS-SIN-TENANT`** (nueva, **grave**): `list_events` no filtra por tenant ni
  por empresa. Medido: un evento de `DEMO2` devuelto a un administrador de `DEMO`.
  Contradice `FR-001-032` y `FR-001-033`. Dueña SPEC001.
- **`AUDITORIA-SOBRE-VS-ARRAY`** (nueva): la pantalla de auditoría no pinta ninguna fila
  nunca, porque trata un sobre paginado como un array. La caja muerta lo tapaba.
- **`AUDITORIA-CREATED-AT`** (nueva, menor): la columna «Fecha» y `api/types.ts:52` leen
  `created_at`; el servidor publica `event_time`.
- **`EMPRESAS-SIN-SOBRE`** (nueva, menor): `list_companies` devuelve un array plano, sin
  `total` ni `page`, contra el contrato de listados de `api-contracts.md`.
- **`AUDITORIA-PANTALLA-DUPLICADA`** (nueva, menor): el menú tiene dos entradas
  «Auditoría» —`/auditoria` (`/audit/events`) y `/reportes/auditoria`
  (`/reporting/audit/timeline`)— con contratos y filtros distintos.

## 11. Lo que NO se ha hecho, a propósito

- No se ha añadido `q` a ningún handler, ni se ha tocado un `select`, ni se ha escrito un
  `ilike`: **ficheros de producto = 0**.
- No se ha implementado la búsqueda de Empresas, aunque está decidida: el gate detiene el
  ciclo completo con `MATERIAL OQ > 0`, y un gate que se salta cuando conviene no es un gate.
- No se ha filtrado en el frontend sobre lo ya cargado, ni se ha tocado `DataTable`.
- No se ha corregido la fuga de tenant de auditoría: decide quién ve qué.
- No se ha creado ningún índice, ni cambiado esquema, ni añadido migración.
- No se ha tocado la semántica de `Company.code`, ni la política de parámetros no
  declarados, ni `API-COMPANY-ID-EN-CONSULTA`.

## 12. Estado

| Cosa | Estado |
|---|---|
| `UI-BUSQUEDA-MUERTA` | **OPEN** → reclasificada: Empresas **decidida**, Auditoría y Existencias `MATERIAL_DECISION_REQUIRED` |
| Producto · esquema · migraciones | 0 · sin cambios · 0 |
| `MATERIAL OQ` | **2** (OQ-1 Auditoría, OQ-2 Existencias), y son el bloqueo |
| `UNKNOWN` | **0** |
| Deudas nuevas | 5, una de ellas una fuga entre inquilinos |

**VEREDICTO: CASO D — `UI-BUSQUEDA-MUERTA` BLOCKED BY NEW MATERIAL DECISION (2).**
