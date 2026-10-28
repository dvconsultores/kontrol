# INSTANT_INPUT_INVENTORY — línea base en 49540a6 (2026-10-28)

Lo generó Claude recorriendo `create_app().routes` con `get_flat_dependant`: parámetros de consulta, ruta, cabecera y cuerpo, más los modelos Pydantic anidados en listas, uniones y diccionarios. No hay entradas `Form` con fecha: la única `Form` es `replacement_reason`, un `str`.

## Clasificación (ADR-020)

Columnas comunes a las 16 entradas INSTANT:
- CURRENT_ACCEPTS_NAIVE: sí. El instante sin zona se lee como UTC (ADR-020 (e), vigente).
- EXPECTED_BEHAVIOR: con zona → aceptado y normalizado a UTC; sin zona → 422 `NAIVE_DATETIME`.
- VALIDATOR: `InstanteDeEntrada` (AD-4).
- OPENAPI: `format: date-time`, sin cambios.
- TEST: DT-I-01..16.

| # | Campo | Modelo / firma | Ruta | Ubicación | Módulo |
|---|---|---|---|---|---|
| 1 | `effective_from` | `master_data/api.py` modelo de perfil | `POST /maestros/perfiles` | cuerpo | master_data |
| 2 | `effective_to` | ídem | `POST /maestros/perfiles` | cuerpo | master_data |
| 3 | `valid_from` | `uom_api.py` presentación | `POST /maestros/productos/{product_id}/presentaciones` | cuerpo | master_data (UoM) |
| 4 | `valid_from` | `uom_api.py` versión | `POST /maestros/presentaciones/{presentation_id}/versiones` | cuerpo | master_data (UoM) |
| 5 | `date` | `uom_api.py` vista previa | `POST /maestros/conversion/preview` | cuerpo | master_data (UoM) |
| 6 | `unloading_scheduled_at` | `purchasing/api.py` | `POST /purchasing/receipts` | cuerpo | purchasing |
| 7 | `arrival_at` | `purchasing/api.py` | `POST /purchasing/receipts/{receipt_id}/arrival` | cuerpo | purchasing |
| 8 | `effective_at` | `treasury/api.py` observación | `POST /treasury/exchange-rates/observations` | cuerpo | treasury |
| 9 | `published_at` | ídem | `POST /treasury/exchange-rates/observations` | cuerpo | treasury |
| 10 | `effective_at` | `resolve_exchange_rate` | `GET /treasury/exchange-rates/resolve` | consulta | treasury |
| 11 | `valid_from` | `approvals/api.py` delegación | `POST /approvals/delegations` | cuerpo | approvals |
| 12 | `valid_to` | ídem | `POST /approvals/delegations` | cuerpo | approvals |
| 13 | `created_from` | `list_notifications` | `GET /notifications` | consulta | notifications |
| 14 | `created_to` | ídem | `GET /notifications` | consulta | notifications |
| 15 | `due_from` | `list_tasks` | `GET /tasks` | consulta | notifications |
| 16 | `due_to` | ídem | `GET /tasks` | consulta | notifications |

**INSTANT por ubicación:** 11 en cuerpo y 5 en consulta. En ruta y en cabecera, 0. En `Form`, 0.

## Lo que no es INSTANT y no cambia

| Valor | Clase | Por qué no cambia |
|---|---|---|
| `desde`, `hasta` (`/audit/events`), `date_from`, `date_to` (observaciones de tasas), `expiry_before` (lotes), `expiring_before` (documentos) | BUSINESS_DATE (`date`) | AAAA-MM-DD sin zona (§26) |
| `effective_from` y `effective_to` de fiscal, tesorería, inventario y documentos; `valid_from` y `valid_to` de listas de precio | BUSINESS_DATE (`date`) | Tipadas `date` |
| `period` (reportes y libros) | PERIOD | «AAAA-MM» validado por `clock` (422 `INVALID_PERIOD`) |
| `effective_at` de una fila CSV de tasas | Hora de pared de Caracas | Regla documentada de importación (ADR-020 (e), §29). Se lee del fichero con `_fecha` y no pasa por Pydantic |
| Fechas dentro del fichero de licencia firmado | Formato de artefacto firmado (`license_contract.py`) | No es una entrada JSON de la API: es el contenido verificado de un documento firmado con su propio contrato. Fuera de alcance, sin cambios |
| Sellos internos (`created_at`, `event_time`, `last_rebuilt_at`…) | TECHNICAL_STAMP / INSTANT generado | Los genera el sistema (§28) |

**UNCLASSIFIED_DATETIME_INPUTS = 0 · INSTANT_FIELDS_CLASSIFIED = 1.**

## Clientes que envían estos campos

La UI siempre manda el instante con zona: `instanteDesdeHoraDeCaracas` y `finDelDiaDeNegocio` terminan en `toISOString()`, que da `Z`.

| Campo | Pantalla | Cómo lo envía |
|---|---|---|
| `effective_at` (tasas) | Tesorería › Tasas | `instanteDesdeHoraDeCaracas(vigencia)` |
| `unloading_scheduled_at` | Compras › Recepciones | `instanteDesdeHoraDeCaracas(...)` |
| `valid_to` (delegación) | Aprobaciones › Delegaciones | `finDelDiaDeNegocio(validTo)` |
| `effective_from` y `effective_to` (perfil) | Maestros › Perfiles | `null` |

Las pruebas del backend que envíen instantes sin zona se miden con la suite completa después de aplicar el cambio. Se corrigen: no se conserva una petición inválida por el solo hecho de que una prueba la envíe (§56).
