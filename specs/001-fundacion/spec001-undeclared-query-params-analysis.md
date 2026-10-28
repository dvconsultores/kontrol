# SPEC 001 · Delta dirigida — API-QUERY-SILENCIOSA · **SE DETIENE EN CLARIFY**

> **Estado posterior (2026-10-28, SHARED-CORE-P0-HARDENING-05):** la OQ de este análisis la resolvieron OD-API-01..07 (rechazar con 422, sin ventana de compatibilidad). API-QUERY-SILENCIOSA y API-COMPANY-ID-EN-CONSULTA están **cerradas**. Ver `spec001-strict-api-input-contract-delta.md`. El texto de abajo se conserva tal como se escribió.


**Fecha** 2026-09-20 · **Dueña** SPEC001 — Fundación (`specs/001-fundacion`, dueña del
contrato transversal de API) · **Apoyo** SPEC023 (donde se detectó) y SPEC054 (QA) ·
**Base** `2128878` · **Rama** `develop`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `2128878` |
| `ACTUAL_HEAD` | `2128878` — **coincide** |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_2128878` | **0** |
| Árbol | limpio salvo los dos artefactos de auditoría sin seguimiento, **preservados** |

## 2. Veredicto, por delante

**`API-QUERY-SILENCIOSA` — BLOCKED BY NEW MATERIAL DECISION.**

No se implementa estrictez. El motivo no es que dé igual: es que **no existe contrato** que
diga si un parámetro de consulta no declarado debe rechazarse o puede ignorarse, y
cambiarlo hoy rompería **27 de 224** pruebas E2E — medido, no estimado.

Lo que sí trae este ciclo es aquello que convierte la pregunta en urgente: **el silencio
está escondiendo tres buscadores del producto que no buscan nada.**

## 3. Dueña

La deuda se registró con dueña preliminar **SPEC023**, porque se detectó sobre el endpoint
de reservas. La evidencia dice otra cosa: el comportamiento es **uniforme en toda la API**
—diez endpoints muestreados de siete módulos, todos idénticos— y las llamadas afectadas
viven en organización, inventario, auditoría y aprobaciones. No es una cuestión del
endpoint de reservas: es del **contrato transversal de la API**, que vive en
`specs/001-fundacion/contracts/api-contracts.md`.

**Dueña: SPEC001.** Apoyo: SPEC023 (origen del hallazgo) y SPEC054 (QA).
`OWNER_IDENTITY_CONFLICT = 0`.

## 4. El comportamiento actual, medido

Contra PostgreSQL y API reales.

### El endpoint del hallazgo

| Petición | HTTP | Resultado |
|---|---|---|
| `/inventory/reservations` | 200 | referencia |
| `?source_order_id=<inexistente>` | 200 | **idéntico** |
| `?__kontrol_unknown_query_probe__=1` | 200 | **idéntico** |

Se usó además un nombre inequívocamente inexistente, y no solo `source_order_id`, para que
la conclusión no dependiera de que ese nombre aparezca en el modelo.

### El riesgo, con datos

Sobre `/maestros/terceros`, que **sí** declara `q` y `status`:

| Petición | HTTP | Resultado |
|---|---|---|
| `?status=INACTIVE` | 200 | **0 elementos** — el filtro funciona |
| `?sttaus=INACTIVE` *(errata)* | 200 | **1 elemento** — devuelve lo no filtrado |
| `?q=SOLO-DE-A` | 200 | filtra |
| `?qq=SOLO-DE-A` *(errata)* | 200 | no filtra |

Quien pide inactivos por una errata de una letra recibe un activo, y nada se lo dice.

### Lo que sí valida

| Petición | HTTP | Cuerpo |
|---|---|---|
| `?page_size=abc` *(declarado, valor inválido)* | **422** | `VALIDATION_ERROR` |

La validación de los parámetros **declarados** funciona y tiene envoltorio canónico. Lo que
no existe es una opinión sobre los **no declarados**.

### Uniformidad

Diez endpoints de siete módulos —terceros, catálogo, reservas, tipos de movimiento, tipos
documentales, almacenes, usuarios, roles, pedidos, compras—: en todos, con y sin parámetro
desconocido, **la respuesta es idéntica**. KONTROL es coherente: ignora en todas partes.

## 5. El contrato, buscado donde tenía que estar

| Dónde | Qué dice sobre parámetros no declarados |
|---|---|
| Constitución | Nada |
| `specs/001-fundacion/contracts/api-contracts.md` | Declara las convenciones de listado —«Listados con `q`, `status`, `sort`, `page`, `page_size`»— y **no dice nada** sobre parámetros ajenos |
| Los 15 ADR de fundación | Ninguno trata la frontera HTTP de la API |
| Specs 023 · 030 · 031 · 048 · 054 | Nada |
| OpenAPI | Declara `status`, `product_id` y la cabecera de empresa para reservas. Respuestas documentadas: 200 y 422. **`source_order_id` no está declarado** |

### Lo que sí existe, y no es esto

`ConfigDict(extra="forbid")` aparece en **16 modelos**, y su intención está escrita:

> «El cuerpo es estricto: `company_id` u otro campo ajeno responde 422, nunca se lee»
> — `app/modules/sales/api.py:99-101`

Es una decisión real y motivada —impedir que un campo del cuerpo secuestre el alcance de
empresa— pero es **de cuerpo**, se aplica a mano modelo por modelo, y su identificador
`IMP-030-035` solo existe en comentarios del código: no está en `specs/`, y ninguna prueba
la fija.

De parámetros de consulta no dice nada nadie.

## 6. `source_order_id` — ¿era un filtro contractual?

**No.** Registro completo de sus apariciones hoy:

| Dónde | Qué es |
|---|---|
| `models.py`, `service.py`, migración `0043` | **Campo del modelo** y filtro **interno** del servicio |
| `api.py:771` | **Campo de la respuesta** |
| `types.ts:243` | Tipo del campo de respuesta en el frontend |
| `sales-orders.spec.ts:160`, `reservas-identidad.spec.ts:134` | Filtrado **en cliente** sobre el campo publicado |
| `picking.spec.ts:302`, `helpers/reservas.ts:20` | **Comentarios** que explican que no es un filtro |

**Ningún cliente lo envía ya como parámetro** —lo retiró `E2E-031-RESERVAS`— y ninguna
Spec lo exige. No se añade. `CASO C` descartado para este parámetro.

## 7. Lo que el silencio estaba escondiendo

Cruzando **todas** las llamadas con query string del frontend contra el OpenAPI vivo:
**10 llamadas de producto envían parámetros que el servidor no declara.**

### Familia A — buscadores que no buscan (3)

| Pantalla | Llamada | El servidor declara |
|---|---|---|
| `pages/EmpresasPage.tsx:25` | `/organization/companies?q=` | **nada** |
| `pages/AuditoriaPage.tsx` | `/audit/events?q=` | `action`, `entity_id`, `entity_type`, `page`, `page_size` |
| `modules/inventario/existencias/ExistenciasPage.tsx` | `/inventory/balances?q=` | `location_id`, `lot_id`, `page`, `page_size`, `product_id`, `serial_id`, `state`, `warehouse_id` |

Demostrado lado a lado:

```
/maestros/terceros?q=ZZZ-NO-EXISTE        -> 0 terceros     ← el filtro existe
/organization/companies?q=ZZZ-NO-EXISTE   -> 1 empresa      ← el filtro no existe
```

Son **tres cajas de búsqueda visibles que no filtran nada**, y el usuario no tiene forma de
saberlo: el servidor responde 200 y devuelve la lista entera. Y no es una libertad del
producto: el contrato de la propia Fundación dice «Listados con `q`, `status`, `sort`,
`page`, `page_size`», y `FR-001-065` exige «búsqueda general» en los listados.

### Familia B — `company_id` en la consulta (7)

`organization/branches` ×3 y aprobaciones ×4 envían `company_id` como parámetro. Hoy es
inofensivo —la empresa la decide `X-Kontrol-Company`, que sí se valida— pero conviene ver
la asimetría: **el mismo campo está prohibido en el cuerpo con un 422 explícito y aceptado
en silencio en la consulta.**

## 8. El coste de cambiar, medido

Se instaló una **sonda estricta temporal** —rechazo con 422 de todo parámetro no declarado,
resolviendo la ruta y sus dependencias con `get_flat_params`— y se ejecutó la suite E2E
completa:

| Con la sonda activa | Valor |
|---|---|
| Pruebas | 224 |
| Pasan | **197** |
| Fallan | **27** (12 %) |
| Ficheros afectados | 8 (`approvals` 7, `warehouse-structure` 4, `uom-a11y` 4, `empresa-helper` 4, `warehouse-a11y` 3, `documents` 3, `uom-conversion` 1, `documents-a11y` 1) |

La sonda se retiró y `main.py` quedó **idéntico** (`cmp`), con `git diff` vacío en
`resources/backend/`. Y se comprobó que no quedó residuo: la suite completa vuelve a
**224 / 224**, salida 0.

Entre medias hubo una ejecución con **4 fallos**, todos de `documents`. No era residuo:
el lanzador que reconstruí hoy no exportaba las variables de ClamAV. Reinstalado el
antivirus y rehecha su firma de prueba, la suite quedó limpia. Se cuenta porque la
diferencia entre «residuo de la sonda» y «falta el antivirus» solo se ve si uno la mira.

**Una primera medición se descartó**: Vite no estaba levantado y dio 112 fallos. No se
reporta como dato; se dice que existió y por qué no vale.

## 9. `/speckit.clarify` — la pregunta que detiene el ciclo

> **¿KONTROL debe rechazar los parámetros de consulta que un endpoint no declara, o puede
> ignorarlos?**

| Matriz del encargo | ¿Aplica? |
|---|---|
| CASO A — la Spec exige rechazar | **No**: no existe |
| CASO B — la Spec permite ignorar | **No**: tampoco existe. El comportamiento es del framework, no una decisión |
| CASO C — `source_order_id` era contractual | **No** (§6) |
| **CASO D — no existe política** | **SÍ** |

Las dos respuestas tienen coste, y conviene que se vean juntos:

**Rechazar** pone a la vista los diez usos actuales y convierte cada errata futura en un
error inmediato. Precio: es un cambio incompatible; hoy rompería 27 pruebas y, con ellas,
tres pantallas de aprobaciones, la de almacenes y la de unidades. Habría que arreglar esas
diez llamadas antes o a la vez, decidir el alcance —un endpoint, un módulo o toda la API— y
tener en cuenta que un proxy o una integración pueden añadir parámetros por su cuenta.

**Ignorar**, ratificado por escrito, no cuesta nada hoy y deja el riesgo donde está: una
errata de una letra sigue devolviendo el conjunto entero con un 200. Si se elige esto, lo
mínimo honesto es escribirlo en el contrato y añadir una prueba que lo fije, para que deje
de ser «lo que hace FastAPI» y pase a ser «lo que KONTROL decidió».

## 10. Hallazgos nuevos, registrados y no absorbidos

- **`UI-BUSQUEDA-MUERTA`** (nueva): tres listados del producto envían `q` a endpoints que no
  lo declaran, así que su caja de búsqueda no filtra. Es un defecto real y **visible para el
  usuario**, y existe con independencia de la política de parámetros desconocidos. No se
  corrige aquí: son tres endpoints de tres dueñas distintas, y el contrato de listados
  (`api-contracts.md`, `FR-001-065`) debe guiar cada uno.
- **`API-COMPANY-ID-EN-CONSULTA`** (nueva, menor): siete llamadas envían `company_id` como
  parámetro donde la empresa ya la decide la cabecera validada. Hoy es inocuo; documentado
  para que no se confunda con un selector de alcance.

## 11. Lo que NO se ha hecho, a propósito

- No se ha añadido `source_order_id` ni ningún otro filtro.
- No se ha implementado estrictez, ni local ni global: **ficheros de producto = 0**.
- No se han tocado los modelos con `extra="forbid"`.
- No se han corregido los tres buscadores muertos: es otra deuda, con otras dueñas.
- No se ha absorbido `E2E-SIN-TYPECHECK`, ni las dos deudas que esperan decisión.
- La sonda temporal se retiró y se verificó con `cmp`.

## 12. Estado

| Cosa | Estado |
|---|---|
| `API-QUERY-SILENCIOSA` | **OPEN** → reclasificada `MATERIAL_DECISION_REQUIRED`, dueña **SPEC001** |
| Producto · esquema · migraciones | 0 · sin cambios · 0 |
| `MATERIAL OQ` | **1**, y es el bloqueo |
| `UNKNOWN` | **0** |

**VEREDICTO: CASO D — `API-QUERY-SILENCIOSA` BLOCKED BY NEW MATERIAL DECISION.**
