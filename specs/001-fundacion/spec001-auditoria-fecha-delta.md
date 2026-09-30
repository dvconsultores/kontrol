# SPEC 001 · DELTA DIRIGIDO AUDITORIA-CREATED-AT — LA COLUMNA FECHA LEE EL CAMPO QUE LLEGA

> Delta de frontend dentro de la Spec 001 (Fundación), dueña del endpoint, del modelo, de
> `AuditoriaPage`, del contrato temporal (`POLICY-CLOCK-LOCAL`) y del contrato de API;
> Spec 012 (QA integral, Master 054) como apoyo. Cierra `AUDITORIA-CREATED-AT`
> (`AUDIT-UI-FECHA-CAMPO-INCORRECTO`). No toca el backend, ni `event_time` persistido, ni
> la búsqueda `q`, ni la paginación, ni el sobre ya corregido.

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` | `0b3d949` / **`0b3d949`** — coinciden |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_0B3D949` | **0** |
| Artefactos preservados | `KONTROL_MASTER_COMPLETENESS_AUDIT.md` · `qa/audits/KONTROL-AUDIT-POLICY-CLOCK-LOCAL-20260917/` — sin seguimiento, intactos |
| `WORKTREE_STATE` | 1.550 cambios **solo de modo**: `WORKTREE_ENVIRONMENT_NOISE`, excluidos con `core.fileMode=false` |

### Entorno

`/tmp` se vació entre sesiones: desaparecieron el clúster PostgreSQL de QA (`kaud`, `ktest`), el
mundo sembrado y el intérprete del scratchpad. Se reaprovisionó todo con el `.venv` del
repositorio, reparado localmente en el ciclo anterior: `qa/pg-provision.sh start`, migración a
`0057`, `qa/e2e-seed.sh`. Ninguna deuda de entorno se absorbe.

## 1. Veredicto, por delante

**Un nombre copiado del mixin de la entidad y no del contrato.** Desde el primer commit
(`342882a`, 2026-08-04) el tipo `AuditEvent` del frontend y la columna «Fecha» decían
`created_at`, mientras el listado publicaba `event_time` en ese mismo commit. Mientras la tabla
no pintó filas (`AUDITORIA-SOBRE-VS-ARRAY`) nadie lo vio. Fix: **el campo del contrato y el
formateador canónico**. Ficheros de producto: **2** (`api/types.ts`, una línea;
`AuditoriaPage.tsx`, tres). Backend, esquema, datos: **0**.

## 2. Dueñas

| Papel | Spec | Evidencia |
|---|---|---|
| **Principal** | **SPEC 001 — Fundación** | `AuditoriaPage.tsx`, `api/types.ts`, `audit/api.py`, `FR-001-070` («timestamp del servidor»), `api-contracts.md` |
| Contrato temporal | **SPEC 001** — `spec001-business-timezone-delta.md` (`POLICY-CLOCK-LOCAL`): instantes técnicos en UTC; formateos de pantalla `PRESENTATION_ONLY` | §6 |
| QA | **SPEC 012** (Master 054) | pruebas de página bajo tres zonas, E2E, matriz |

Master 006 «Auditoría/observabilidad» → `001-fundacion` + `009`. `OWNER_IDENTITY_CONFLICT = 0`.

## 3. La evidencia y el defecto, físicamente

| | |
|---|---|
| `SOURCE_FILE` | `resources/frontend/src/pages/AuditoriaPage.tsx` |
| `COLUMN_DEFINITION` | `columnHelper.accessor("created_at", { header: "Fecha", cell: (info) => new Date(info.getValue()).toLocaleString("es-VE") })` (líneas 16-19) |
| `FIELD_USED` | `created_at` (`api/types.ts:52`: `created_at: string`) |
| `RENDERER` | `new Date(undefined).toLocaleString("es-VE")` → «Invalid Date» |
| `CURRENT_VISIBLE_OUTPUT` | «Invalid Date» en todas las filas (`evidence/auditoria-sobre/reproduccion-ui-post-fix.txt`) |
| Origen (`git blame`) | ambos en `342882a`, el commit fundacional; el backend de ese mismo commit ya publicaba `event_time` (`git show 342882a:…/audit/api.py:50`) |
| Clasificación | **contract drift de origen**: el nombre de la columna del mixin `TimestampMixin` (`created_at`, que sí existe en la tabla) se copió al tipo público en lugar del campo publicado |

### Reproducción, antes de tocar nada (`evidence/auditoria-fecha/reproduccion-pre-fix.txt`)

Chromium, sesión `admin`/DEMO, menú → Auditoría. Un inicio de sesión por API cuyo
`X-Request-ID` devuelve el servidor, localizado en la bitácora por API y en la tabla por su
Request ID:

| | |
|---|---|
| `EVENT_ID` | `3940a33b-9e5b-4eeb-9383-39441d8dfc4b` |
| `REQUEST_ID` | `a82a5b60607e404f86a0cf03941e8fc9` |
| `EVENT_TIME_RAW` | `2026-09-30T21:54:06.507259+00:00` (`string`) |
| `created_at` en el item | **no** |
| `UI_DATE_TEXT` | **«Invalid Date»** |
| Convención del producto en ese navegador (`toLocaleString("es-VE")`, zona `America/Caracas`) | «30/9/2026, 5:54:06 p. m.» |

## 4. El contrato de `event_time`

| | |
|---|---|
| `BACKEND_FIELD` | `event_time` — `audit/models.py:34`: `DateTime(timezone=True), nullable=False`; `shared/audit.py:64`: `event_time=datetime.now(UTC)`; `audit/api.py:68`: `e.event_time.isoformat()` |
| `DB_TYPE` | `timestamp with time zone`, `NOT NULL` (`evidence/audit-tenant-isolation/esquema-postgresql.txt`) |
| `ORM_TYPE` / `SERIALIZER_TYPE` | `datetime` con zona / `str` ISO 8601 |
| `EVENT_TIME_SERIALIZATION` | `YYYY-MM-DDTHH:MM:SS.ffffff+00:00` — con microsegundos y desplazamiento `+00:00`; nunca `Z`, nunca naive |
| `NULLABLE` | **no** |
| `CREATED_AT_SOURCE` | **B**: existe en la tabla (mixin `TimestampMixin`) y **no** en la API; el frontend lo heredó del nombre de la columna, no del contrato |

## 5. Inventario de `created_at` y de `event_time` en el frontend

`created_at` aparece en 25 sitios de `src/`: **24 son correctos** (documentos, notificaciones,
sesiones, licenciamiento, homologación, cuyos endpoints sí lo publican) y **1 es el defecto**
(`api/types.ts:52` + `AuditoriaPage.tsx:16`). No se reemplaza nada más. `event_time` existía en
el frontend solo en `AuditTimelineItem` (`types.ts:1716`, `string | null`, porque el timeline de
reportes sí puede devolver nulo) y en `ReportesAuditoriaPage`, que lo pinta **crudo**, sin
formatear (`AUDITORIA-TIMELINE-FECHA-CRUDA`, §14).

## 6. Formateador y zona de presentación

| Pregunta | Respuesta medida |
|---|---|
| `CANONICAL_DATETIME_FORMATTER` | **`formatearFecha(iso)`** en `src/i18n/index.ts:35`: `new Date(iso).toLocaleString("es-VE")`, y «—» para nulo. Lo usan las cinco pantallas de notificaciones; las otras ocho pantallas con instantes (kardex, movimientos, eventos y renovación de licencia, entitlements, timeline y versiones de homologación, sesiones) escriben exactamente la misma expresión a mano |
| `lib/format.ts::formatDate` | solo fecha (`dd/MM/yyyy`, date-fns): para fechas civiles, no para instantes |
| `lib/fecha-de-negocio.ts` | **no aplica**: da el **día civil de negocio** en `America/Caracas` para reglas funcionales (`POLICY-CLOCK-LOCAL`); un evento de auditoría es un instante técnico |
| Zona de presentación | **no está fijada en el producto**: la convención canónica es la zona del navegador. `frontend-foundation.md:54` («fechas: zona horaria controlada; servidor como autoridad») es un principio sin implementación de pantalla, y el delta `POLICY-CLOCK-LOCAL` clasificó los formateos de presentación como `PRESENTATION_ONLY` y los dejó intactos a propósito |
| Formato / segundos | el de `toLocaleString("es-VE")`: `30/9/2026, 2:30:00 p. m.` — con segundos, como las ocho pantallas hermanas |
| Nulo | no puede ocurrir (`NOT NULL`); `formatearFecha` devolvería «—» |
| Inválido | la convención devuelve «Invalid Date» y **no se normaliza**: ni «ahora», ni 1970, ni «—» |
| Independencia del anfitrión | la presentación **depende por diseño** de la zona del navegador de quien mira; lo que no puede depender es el instante: bajo UTC, Caracas y Ámsterdam el mismo `event_time` produce el texto que la convención dicta para esa zona, y ese literal queda fijado por zona en la prueba |

Fijar `America/Caracas` como zona de presentación sería una decisión nueva que alcanza a las
nueve pantallas que hoy enseñan instantes: se registra (`FECHAS-ZONA-DE-PRESENTACION`, §14), no
se toma aquí. **No es OQ material para este delta**: la convención canónica existe, tiene
nombre y nueve consumidores.

## 7. Ordenación, filtros y paginación

`DataTable` no ordena (sin `getSortedRowModel`); el orden lo da el servidor (`event_time desc`).
`q` sigue viajando sin efecto (decisión pendiente). La tabla pagina en cliente sobre la página 1
de 20 (`AUDITORIA-PAGINACION-CLIENTE`, abierta). Nada de esto cambia.

## 8. `/speckit.specify`

Tras `FR-001-162`:

| ID | Requisito | Prioridad |
|---|---|---|
| FR-001-163 | La columna «Fecha» de Auditoría representa `event_time` | P0 |
| FR-001-164 | El frontend no consume `created_at` como instante de `AuditEvent`: no pertenece al contrato público | P0 |
| FR-001-165 | El tipo `AuditEvent` declara `event_time: string` (ISO 8601 con zona, no nulo) y no declara `created_at` | P0 |
| FR-001-166 | La representación usa el formateador canónico de instantes del producto (`formatearFecha`) | P0 |
| FR-001-167 | La presentación sigue la convención canónica (zona del navegador); el instante representado es el mismo bajo cualquier zona del proceso | P0 |
| FR-001-168 | No se modifica `event_time` persistido ni se reinterpreta ningún evento | P0 |
| FR-001-169 | El backend no cambia su forma de respuesta ni vuelve a publicar `created_at` | P0 |
| FR-001-170 | `AUDITORIA-SOBRE-VS-ARRAY` y `AUDIT-EVENTS-SIN-TENANT` siguen cerrados y sin regresión | P0 |
| FR-001-171 | Ni `q` ni la paginación de Auditoría se tocan | P0 |
| FR-001-172 | La columna no muestra «Invalid Date» para un `event_time` contractual | P0 |
| FR-001-173 | Pruebas de página y E2E con instante conocido verifican el texto visible | P0 |
| FR-001-174 | Reintroducir `created_at` en el camino tipado de `AuditEvent` no compila | P0 |
| FR-001-175 | Sin esquema, migración ni índice | P0 |

| ID | Criterio |
|---|---|
| AC-038 | **Dado** `event_time = 2026-09-30T18:30:00+00:00`, **entonces** la celda dice «30/9/2026, 6:30:00 p. m.» bajo UTC, «30/9/2026, 2:30:00 p. m.» bajo Caracas y «30/9/2026, 8:30:00 p. m.» bajo Ámsterdam |
| AC-039 | **Dado** `2026-10-01T02:30:00+00:00`, **entonces** bajo Caracas la celda dice «30/9/2026, 10:30:00 p. m.»: la fecha civil cambia con la zona, el instante no |
| AC-040 | **Dado** dos eventos con instantes distintos, **entonces** cada fila muestra el suyo |
| AC-041 | **Dado** un valor que no es un instante, **entonces** no se muestra «ahora» ni «—» |
| AC-042 | **Dado** un login por API con `X-Request-ID`, **entonces** en un navegador real su fila muestra `event_time` con la convención del navegador y ninguna fila dice «Invalid Date» |

## 9. `/speckit.clarify`

| # | Pregunta | Respuesta |
|---|---|---|
| 1–3 | dueñas | 001 · 001 (`POLICY-CLOCK-LOCAL`) · 012 |
| 4–6 | página · columna · campo actual | `src/pages/AuditoriaPage.tsx` · líneas 16-19 · `created_at` |
| 7–11 | campo, tipo, JSON, DB, nulabilidad | `event_time` · `datetime` con zona · ISO con microsegundos y `+00:00` · `timestamptz NOT NULL` · no nulo |
| 12–13 | `created_at` en backend · origen | en la tabla, no en la API (B) · commit fundacional `342882a` |
| 14–16 | tipo TS · usos de `created_at` · usos de `AuditEvent` | `created_at: string` (estático, sin `any`) · 25, 1 incorrecto · 1 (la página) |
| 17–20 | formateador · zona · formato · segundos | `formatearFecha` · la del navegador (convención) · `toLocaleString("es-VE")` · sí |
| 21 | independencia del anfitrión | el instante sí; el texto sigue la zona del navegador por convención |
| 22–23 | inválido · nulo | «Invalid Date», sin normalizar · no ocurre; «—» |
| 24 | ordenación | no hay en cliente; servidor `event_time desc` |
| 25–27 | backend · frontend · helper compartido | no · sí (2 ficheros) · no (se reutiliza) |
| 28–32 | sobre · tenant · `q` · paginación · OpenAPI | intactos |
| 33–34 | esquema · migración | 0 · 0 |
| 35–39 | pruebas · zonas · mutaciones · E2E · regresión | §12–§13 |

**MATERIAL OQ = 0. UNKNOWN = 0.**

## 10. `/speckit.plan` y diseño

W01–W38 ejecutados en el orden del encargo (W05 y W06 con un evento controlado; W22 con la
suite entera bajo tres zonas; W32 con tres navegadores).

```
api/types.ts        AuditEvent.event_time: string            ← antes created_at: string
AuditoriaPage.tsx   accessor("event_time") · cell: formatearFecha(valor)
```

Descartado: `created_at ?? event_time`, `String(valor)`, `new Date()` de respaldo, zona
explícita (`timeZone: "America/Caracas"`: decisión no tomada, afectaría a nueve pantallas),
`fecha-de-negocio` (día civil, no instante), cambiar el backend.

## 11. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G-AUDDATE-01..02 | checkpoint · dueñas | **PASA** |
| G-AUDDATE-03..05 | «Invalid Date» reproducido · `event_time` conocido · contrato demostrado | **PASA** — §3, §4 |
| G-AUDDATE-06..09 | uso de `created_at` · su estado en backend · tipo TS · inventario | **PASA** — §3, §5 |
| G-AUDDATE-10..13 | formateador · zona · formato · anfitrión | **PASA** — §6 |
| G-AUDDATE-14..15 | nulabilidad · ordenación | **PASA** — `NOT NULL`; sin ordenación en cliente |
| G-AUDDATE-16..18 | backend 0 · esquema 0 · migración 0 | **PASA** |
| G-AUDDATE-19..22 | sobre · tenant · `q` · paginación intactos | **PASA** |
| G-AUDDATE-23..25 | mutaciones · zonas · regresión | **PASA** — §13 |
| G-AUDDATE-26..28 | MATERIAL OQ 0 · UNKNOWN 0 · trazabilidad 100 % | **PASA** |

## 12. `/speckit.tasks`, `/speckit.analyze` previo e `/speckit.implement`

| ID | Tarea | Ficheros | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | Checkpoint, artefactos, ruido, entorno reaprovisionado | — | — | — |
| T-02 | Evidencia previa, dueñas, origen (`git blame`) | — | 164 | — |
| T-03 | Reproducción con evento controlado | `evidence/…/reproduccion-*` | 172 | — |
| T-04 | Contrato de `event_time` (ORM, API, DB, JSON) | — | 163, 169 | — |
| T-05 | Inventario de `created_at`/`event_time` y del formateador | — | 164, 166 | — |
| T-06 | Tipo `AuditEvent` | `src/api/types.ts` | 165, 174 | M1, M8 |
| T-07 | Columna «Fecha» | `src/pages/AuditoriaPage.tsx` | 163, 166, 167, 172 | M1–M6 |
| T-08 | Pruebas de página bajo tres zonas | `src/pages/AuditoriaPage.fecha.test.tsx` (+ fixture de `AuditoriaPage.test.tsx`) | 173 | M1–M8 |
| T-09 | E2E con evento controlado | `e2e/auditoria-fecha.spec.ts` | 173 | — |
| T-10 | Regresión: sobre, tenant, puertas, E2E global | — | 170, 171 | M7 |
| T-11 | Documentación, roadmap, convergencia | — | — | — |

**Huérfanos: 0 / 0.** Análisis previo sobre `0b3d949`: `created_at` en el camino de
`AuditEvent`: 2 sitios (los del fix); `any`/`as` en la página: 0; `Date.now`/`new Date()` de
respaldo: 0; `fecha-de-negocio` en la página: 0; cambios de backend: 0; `sleep`/`skip`: 0.
BLOCKER 0 · CRITICAL 0 · CONTRADICTIONS 0 · OWNER CONFLICT 0.

**Implementado**: `api/types.ts` (`created_at` → `event_time`, con comentario),
`AuditoriaPage.tsx` (accessor, celda, importación de `formatearFecha`), fixture de
`AuditoriaPage.test.tsx` (el tipo lo exige). Post-fix en Chromium: la fila del evento controlado
dice «30/9/2026, 5:56:33 p. m.» para `2026-09-30T21:56:33.116360+00:00` con el navegador en
`America/Caracas` — exactamente la convención (`reproduccion-post-fix.txt`).

## 13. Evidencia — `evidence/auditoria-fecha/`

| Fichero | Qué demuestra |
|---|---|
| `reproduccion-pre-fix.txt` / `-post-fix.txt` | «Invalid Date» → el instante formateado, con `event_time` de la API y el texto esperado por la convención en ese navegador |
| `mutaciones.txt` | 7/7 mutantes muertos, control negativo de tipos |
| `frontend-gates.txt` | `tsc -b` 0 · ESLint 0 · Vitest **400/400 bajo UTC, America/Caracas y Europe/Amsterdam** (395 + 5) · `vite build` 0 |
| `backend-dirigido.txt` | aislamiento (11) + búsqueda de empresas (17): 28/28 en SQLite y PostgreSQL; líneas del contrato `event_time` |
| `e2e-matriz.txt` | `auditoria-fecha` + `auditoria-sobre` en Chromium, Firefox y WebKit |
| `e2e-global.txt` | E2E completa en Chromium |

### Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| DATE-M1 | la columna vuelve a `created_at` | **muere** — `tsc` (TS2345) y 4 pruebas |
| DATE-M2 | el ISO crudo, sin formateador | **muere** — `tsc` (importación sin uso) y 3 pruebas |
| DATE-M3 | zona forzada a UTC en vez de la convención | **muere bajo Ámsterdam** (2 pruebas) y `tsc`; bajo UTC es equivalente por construcción |
| DATE-M5 | un valor inválido se disfraza de «ahora» | **muere** — DATE-13 |
| DATE-M6 | solo fecha, sin hora | **muere** — `tsc` y 2 pruebas |
| DATE-M7 | el sobre entero como filas (regresión del envelope) | **muere** — `tsc` (TS2322) y 9 pruebas |
| DATE-M8 | `event_time` desaparece del tipo | **muere** — `tsc` (TS2353) |
| DATE-M4 (zona del anfitrión) | **no aplica**: la convención canónica es precisamente la zona del navegador |

Control negativo de tipos: `info.row.original.created_at` → `tsc` **falla** con
`TS2339: Property 'created_at' does not exist on type 'AuditEvent'`; restaurado y verificado.

### Regresión y comprobaciones

| Suite | Resultado |
|---|---|
| `AuditoriaPage.fecha.test.tsx` + `AuditoriaPage.test.tsx` | **12/12** bajo UTC, America/Caracas y Europe/Amsterdam |
| Vitest completo | **400/400** bajo las tres zonas |
| `tsc -b`, ESLint, `vite build` | 0 · 0 · 0 |
| Aislamiento de auditoría + búsqueda de empresas (backend) | **28/28** en SQLite y PostgreSQL |
| Backend completo | no ejecutado a propósito: 0 ficheros de producto backend (`TEST-SCHEMAS-PG-SIN-LIMPIEZA`) |
| E2E dirigido, tres navegadores | **9/9**: `auditoria-fecha` y `auditoria-sobre` en Chromium, Firefox y WebKit |
| E2E global (Chromium) | **192 pasadas · 0 fallos · 40 saltadas · exit 0** (191 + 1 nueva; las 40 saltadas son las que la suite salta en Chromium, sin cambio) |

## 14. Deudas y hallazgos, registrados y no absorbidos

| ID | Estado |
|---|---|
| `FECHAS-ZONA-DE-PRESENTACION` (nuevo, decisión) | el producto presenta los instantes en la zona del navegador (nueve pantallas, `formatearFecha`); `frontend-foundation.md:54` enuncia «zona horaria controlada» sin implementación. Fijar una zona de presentación es una decisión transversal de la dueña |
| `AUDITORIA-TIMELINE-FECHA-CRUDA` (nuevo, menor) | `ReportesAuditoriaPage` pinta `event_time` sin formatear (ISO crudo) |
| `FECHAS-FORMATO-A-MANO` (nuevo, observación) | ocho pantallas repiten `new Date(v).toLocaleString("es-VE")` en lugar de usar `formatearFecha` |
| `UI-BUSQUEDA-MUERTA` · Auditoría, `AUDITORIA-PAGINACION-CLIENTE`, `AUDIT-OPENAPI-SIN-RESPONSE-MODEL`, `AUDITORIA-PANTALLA-DUPLICADA` | sin cambio |

## 15. Estado resultante

| Cosa | Estado |
|---|---|
| `AUDITORIA-CREATED-AT` | **CLOSED / CONVERGED** |
| Ficheros de producto | 2 (frontend) · backend 0 |
| Pruebas nuevas | 5 de página (×3 zonas) · 1 E2E × 3 navegadores · mutaciones 7/7 (+1 no aplicable) |
| Forma pública de la API · datos | sin cambio · sin cambio |
| Decisiones nuevas de la dueña | ninguna |
