# SPEC 013 · MAESTROS FINANCIEROS — PLAN, COMPUERTAS Y TAREAS

> Sobre `f5ddc8d`. Dueño: `specs/006-tesoreria` (ver `spec013-clarifications.md` §0).

## 1. Qué construye este ciclo

Convertir los maestros financieros en **la autoridad canónica de la tasa**: qué
monedas existen, de qué fuentes vienen las tasas, qué significan exactamente, y
cómo se resuelve una tasa para una fecha —incluida la respuesta «no la hay»—.

La 038 dejó de inventar tasas y con eso dejó al descubierto que **nadie las
registra**. Este ciclo cierra ese hueco y, de paso, los siete defectos que la
investigación encontró en lo que ya existía.

## 2. Decisión de diseño: extender, no duplicar

`treasury_rate_snapshots.exchange_rate_id` es una clave foránea a
`exchange_rates`. Crear una tabla nueva de observaciones dejaría esa clave
apuntando a un modelo muerto y rompería la reproducibilidad histórica que la
038 certificó.

Por tanto: **`exchange_rates` se extiende en su sitio**, de forma aditiva, y se
convierte en la observación canónica. Las filas existentes se rellenan con el
par que su propio código ya implicaba —base = la moneda de la fila, cotizada =
la funcional de su empresa— y con una fuente y un tipo derivados de lo que ya
tenían.

## 3. Semántica del par — canónica

```
base_currency_id
quote_currency_id
rate  (Decimal)
```

significa:

> **1 unidad de `base` = `rate` unidades de `quote`.**

Con `base = USD`, `quote = VES` y `rate = 100`: 1 USD son 100 VES.

Esta frase se escribe en el modelo, en el contrato y en la pantalla. `USD/VES`
a secas deja de ser autoridad de nada.

## 4. Modelo de datos

### 4.1 · `currencies` — extensión

| Cambio | Motivo |
|---|---|
| único `(company_id, code)` | Defecto §2.1. Dos «USD» hacían la resolución aleatoria |

### 4.2 · `exchange_rate_sources` — nueva

`id`, `company_id`, `code`, `name`, `source_type`, `authority_reference`,
`provider_code`, `allows_manual`, `priority`, `status`, `effective_from`,
`effective_to`, marcas de tiempo y autor.

Sin tipos cableados: `source_type` es texto del maestro, no un `enum` del código.

### 4.3 · `exchange_rate_policies` — nueva

La política de **resolución**, que es de la 013. Distinta de
`treasury_fx_policies`, que es la de **operación** y es de la 038: aquélla
decide si se puede convertir; ésta, cómo se obtiene la tasa.

`allow_inversion`, `allow_triangulation`, `triangulation_currency`,
`max_age_days` (nulo = sin tope), `carry_forward`, `require_rate_approval`,
`rate_scale`, `version`, `status`, `effective_from`, `effective_to`.

Nace con inversión y triangulación **denegadas**: `FR-013-034` y `FR-013-035`
dicen que no son automáticas, y ninguna prueba ni pantalla depende hoy de ellas.

### 4.4 · `exchange_rates` — extensión

`base_currency_id`, `quote_currency_id`, `source_id`, `rate_type`,
`effective_at`, `published_at`, `observed_at`, `status`, `version`,
`supersedes_id`, `provider_observation_id`, `import_batch_id`,
`source_reference`, `authority_reference`, `entered_by`, `approved_by`,
`reason`.

Restricciones: `rate > 0`, `base != quote`, y único sobre
`(company_id, base_currency_id, quote_currency_id, source_id, rate_type,
effective_at, version)`.

`currency_id` y `rate_date` **se conservan**: son la clave foránea viva de la
038 y el camino de lectura de lo ya escrito.

### 4.5 · `exchange_rate_import_batches` — nueva

`id`, `company_id`, `source_id`, `rate_type`, `filename`, `content_hash`,
`row_count`, `imported_count`, `rejected_count`, `status`, `actor`, marcas.

El `content_hash` es lo que hace idempotente reimportar el mismo fichero.

## 5. Contrato de resolución

```
resolve_rate(company, base, quote, effective_at, rate_type=None, source=None)
  → RateResolution | MISSING_RATE | STALE_RATE
```

Devuelve: `observation_id`, `base`, `quote`, `rate` (`Decimal`), `source`,
`rate_type`, `effective_at`, `published_at`, `observed_at`, `version`,
`status`, `derived` (`false` | `INVERSE` | `TRIANGULATION`), y la procedencia
de cada pata cuando es derivada.

`base == quote` devuelve `Decimal("1")` marcado como `SAME_CURRENCY_IDENTITY`,
sin fila de mercado.

## 6. Compuerta constitucional

| Principio | Cumplimiento |
|---|---|
| No inventar tasas | Reforzado: `MISSING_RATE` explícito, sin `1,0` |
| No cablear Venezuela | `funcional = ("VED","VES")` desaparece; la moneda funcional sale de la empresa |
| No decidir estrategia económica | Inversión y triangulación denegadas salvo política, y marcadas cuando se usan |
| `Decimal` en dinero y tasa | Borde, servicio y modelo |
| No inventar permisos | `tesoreria: view/create/approve` |
| No duplicar dueño | `PaymentMethod`, `Bank`, `RateSnapshot` siguen en la 038 |
| No integración externa aquí | Contrato de proveedor definido, implementación en la 048 |
| Migraciones aditivas | `exchange_rates` se extiende; nada se reescribe |
| `D0-07` abierto | Nada de este ciclo afirma homologación |
| Una regresión completa | Al final, con las fuentes congeladas |

## 7. Lista de verificación

- [x] Único `(company_id, code)` en monedas, con los duplicados existentes resueltos antes
- [x] Par explícito en toda observación, y relleno de lo histórico con su autoridad
- [x] `rate` `Decimal` de punta a punta
- [x] Resolución con fecha, sin «la más reciente»
- [x] Inversión y triangulación solo con política, y marcadas
- [x] Caducidad por política, sin número cableado
- [x] Identidad de misma moneda sin fila falsa
- [x] Corrección por sucesión, sin reescribir historia
- [x] Fuente desactivada fuera de la resolución, presente en el histórico
- [x] Prioridad de fuente configurada, sin orden de base de datos
- [x] Importación validada, idempotente y con informe de errores
- [x] Aislamiento por empresa y por tenant
- [x] La 038 obtiene su tasa real y conserva sus instantáneas antiguas
- [x] Doce mutaciones: once muerden y una se midió como no detectable (sustituida por M013-02b); más once de la reanudación, todas muerden
- [x] Selector paginado según el contrato real, nunca `limit`

## 8. Tareas

1. Migración: unicidad de monedas, fuentes, políticas, extensión de tasas, lotes
2. Modelos y relleno histórico
3. Servicio de resolución en su dueña, con política
4. Alta manual, corrección por sucesión, importación CSV
5. API y OpenAPI
6. Pantallas: monedas, fuentes, tasas, alta manual, importación
7. Pruebas dirigidas, hostiles, de concurrencia y las doce mutaciones
8. e2e en tres navegadores
9. Regresión completa, trazabilidad y convergencia
- [x] **Añadido en la reanudación:** perder una carrera de alta es un error de dominio, nunca un 500
- [x] **Añadido en la reanudación:** la unicidad declarada en los modelos con los mismos nombres que la migración, y guardada
- [ ] **No cumplido para el esquema entero:** deriva ORM ↔ migración cero. Cumplido en la 013; quedan 21 operaciones heredadas de otras Specs, registradas con dueño
