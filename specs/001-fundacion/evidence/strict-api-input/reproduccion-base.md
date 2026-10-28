# Reproducción de línea base (49540a6, 2026-10-28)

Barrido de Claude en el scratchpad, sin confirmar: mundo MFA sintético en SQLite, usuario sintético con FUNCIONAL_COMPLETO, alta TOTP y cabecera `X-Kontrol-Company`. Cada GET de `/api/v1/**` se llama sin y con `zz_no_declarado=1`, rellenando los parámetros de ruta con UUID aleatorios.

## Barrido GET

| Clase | Rutas |
|---|---|
| ACCEPTED_SILENTLY | 189 |
| AUTH_PRECEDES_QUERY_VALIDATION | 37 |
| ROUTE_NOT_SAFELY_PROBEABLE | 1 |

**UNDECLARED_ACCEPTED_BEFORE (GET medido) = 189**.

- **AUTH_PRECEDES_QUERY_VALIDATION = 37:** responden 401, 403 o 423 con y sin el parámetro, porque la autorización de la ruta va antes.
- **ROUTE_NOT_SAFELY_PROBEABLE = 1:** `GET /notifications/preferences` usa `bool_or`, que no existe en SQLite. En PostgreSQL funciona y la ruta queda cubierta por la guarda estructural.
- **Escrituras (POST, PUT, PATCH y DELETE):** no tienen mecanismo, así que el framework ignora la consulta igual que en GET. Lo prueban RQ-07 y la ausencia de lectores manuales.

## RQ / DT / UI

| Caso | HTTP | code | field_errors |
|---|---|---|---|
| RQ-01 desconocido | 200 | — | — |
| RQ-02 desconocido vacío | 200 | — | — |
| RQ-03 parecido pagesize | 200 | — | — |
| RQ-03b mayúsculas Page_Size | 200 | — | — |
| RQ-04 varios | 200 | — | — |
| RQ-05 repetido | 200 | — | — |
| RQ-06 declarado page_size | 200 | — | — |
| RQ-06b declarado valor inválido | 422 | VALIDATION_ERROR | query.page_size |
| RQ-07 POST + desconocido (cuerpo vacío) | 422 | VALIDATION_ERROR | code, name |
| RQ-07b PATCH + desconocido | 405 | METHOD_NOT_ALLOWED | — |
| UI-01 existencias q | 200 | — | — |
| UI-01b company_id branches | 403 | PERMISSION_DENIED | — |
| DT-02 consulta naive notifications | 200 | — | — |
| DT-02b consulta Z notifications | 200 | — | — |
| DT-02c consulta -04:00 | 200 | — | — |
| DT-02d resolve naive | 409 | CURRENCY_INACTIVE | — |
| DT-01 cuerpo naive delegación | 422 | VALIDATION_ERROR | grantor_id, grantee_id |
| DT-06 fecha de negocio audit desde | 403 | PERMISSION_DENIED | — |
| DT-07 período | 404 | UNKNOWN_BOOK | — |
| DT-08 sintaxis inválida | 422 | VALIDATION_ERROR | query.created_from |

## Lectura

- **RQ-01..05:** todo desconocido —vacío, parecido, en mayúsculas, varios o repetido— da 200 y se ignora.
- **RQ-06:** lo declarado se acepta. Un valor inválido de un parámetro declarado ya da 422 `VALIDATION_ERROR` (`query.page_size`).
- **RQ-07:** en POST, el desconocido de la consulta no se menciona; solo falla el cuerpo. El PATCH de la sonda pegó en una ruta sin PATCH (405), así que RQ-07 se rehace en rojo sobre una ruta PATCH real.
- **UI-01:** `/inventory/balances?q=ZZZ-NO-EXISTE` da 200 con el conjunto entero: la caja no filtra.
- **DT-02:** `created_from` sin zona da 200 y se lee como UTC. Con `Z` y con `-04:00` también da 200.
- **DT-02d** (`resolve` sin zona) da 409 `CURRENCY_INACTIVE`: llega a la regla de negocio, así que el valor sin zona se aceptó.
- **DT-01, DT-06 y DT-07:** la sonda no tenía el contexto correcto (campos requeridos de la delegación, `audit:view` y nombre del libro). El rojo atribuible se rehace en las pruebas dirigidas.
- **DT-08:** una sintaxis inválida ya da 422 `VALIDATION_ERROR`.
