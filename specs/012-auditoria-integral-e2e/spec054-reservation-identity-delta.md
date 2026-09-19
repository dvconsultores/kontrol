# SPEC 054 · Delta dirigida — E2E-031-RESERVAS

**Fecha** 2026-09-17 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) ·
**Apoyo** SPEC031 y SPEC022 (suites consumidoras) · **Observación a SPEC023** (§6) ·
**Base** `f4fb3c0` · **Rama** `develop`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `f4fb3c0` |
| `ACTUAL_HEAD` | `f4fb3c0` — **coincide** |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_F4FB3C0` | **0** |
| Árbol | limpio salvo los dos artefactos de auditoría sin seguimiento, **preservados** |

## 2. El fallo, localizado

`putaway.spec.ts:341`, dentro de `ubicar no cambia lo reservado ni lo disponible del almacén`:

```ts
const reservasAntes = (await get(request, c, "/inventory/reservations")).items as unknown[];
… POST /inventory/putaway …
const reservasDespues = (await get(request, c, "/inventory/reservations")).items as unknown[];
expect(reservasDespues.length).toBe(reservasAntes.length);
```

Manifestación capturada en la suite global del ciclo anterior: **esperaba 298, leyó 299**.

Lo que la prueba **quiere** afirmar es «ubicar no crea ni destruye reservas». Lo que
**escribe** es «nadie más creó una reserva mientras yo ubicaba». Son afirmaciones distintas
y la segunda no depende del código que se está probando.

## 3. Aislado frente a global

| Ejecución | Resultado |
|---|---|
| `putaway` sola | **9 / 9** |
| `putaway` + `picking`, dos trabajadores | 17 / 17 |
| `putaway` + `picking` + `sales-orders` + `dispatch` + `order-confirmation`, cuatro trabajadores | 36 / 36 |
| Suite global completa, en este ciclo | **220 / 220** |

**La manifestación natural no reapareció.** Es intermitente y su propio registro ya lo decía
(«intermitente, solo con navegadores en paralelo»). No se declara reproducida una cosa que
no se ha visto: lo que sí se reprodujo, y de forma determinista, es el **mecanismo**.

### El mecanismo, demostrado sin depender de la suerte

Se ejecutó la secuencia exacta de la prueba ocupando a propósito el hueco entre sus dos
lecturas, con un segundo cliente:

```
lectura 1 · reservas de la empresa: 369
(otro cliente reserva)
lectura 2 · reservas de la empresa: 370

la aserción de putaway:341 compara 370 con 369: FALLA
identificando la reserva propia por su documento: 0 -> 1
```

La premisa de la aserción es falsa siempre que alguien más reserve; la identificación
exacta funciona en las mismas condiciones. Y el propio total lo dice: entre dos mediciones
de este ciclo la empresa pasó de 330 a 369 reservas sin que nadie tocara `putaway`.

## 4. Inventario de reservas y contrato del endpoint

`GET /api/v1/inventory/reservations` (`app/modules/inventory/api.py:461-471`):

| Aspecto | Realidad medida |
|---|---|
| Alcance | `Reservation.company_id == ctx.company_id` — **acotado a la empresa** |
| Filtros declarados | `status`, `product_id` |
| Paginación | No la hay: devuelve todo, con `total = len(items)` y `page_size = len(items)` |
| Orden | `created_at` descendente |
| Campos publicados | Incluyen `source_document`, `source_type`, **`source_order_id`**, `source_line_id`, `status`, `quantity`, `warehouse_id`, `product_id` (`api.py:764-776`) |

Medición directa contra la base del E2E:

```
sin filtro                                   items 330 · total 330
?status=ACTIVE                               items 204        ← filtra
?product_id=<inexistente>                    items   0        ← filtra
?source_order_id=<inexistente>               items 330        ← NO filtra
```

## 5. Las tres manifestaciones, recontadas

| Lugar | Qué hace | Veredicto |
|---|---|---|
| `putaway.spec.ts:323/340` | Compara el **recuento global** antes y después | **Defecto**: es el fallo observado |
| `picking.spec.ts:300/314` | Envía `?source_order_id=…` —que el servidor ignora— y cuenta las `ACTIVE` de **toda la empresa** | **Defecto**: cree que filtra y no filtra |
| `putaway.spec.ts:412` | Recorre **todas** las reservas de la empresa para comprobar la forma de la respuesta | **Frágil**: no falla por recuento, pero depende del conjunto ajeno |
| `dispatch.spec.ts:252` | Usa `?product_id=` | **Correcto** |
| `sales-orders.spec.ts:159` | Lee todo y **filtra por `source_order_id` en el cliente**, luego afirma sobre *su* reserva | **Correcto — es el patrón a seguir**, y ya existe en el repositorio |

## 6. Lo que NO se hace, y por qué

`?source_order_id=` no se añade al endpoint. El contrato de la 023 dice para esa ruta
«Reservas activas/históricas» (`specs/003-inventario-logistica/contracts/api-contracts.md:40`)
y **no exige** consulta por pedido; ninguna spec la exige. Añadir un parámetro público
porque le conviene a Playwright es inventar semántica, y está prohibido.

Queda registrada una observación aparte, que no se corrige aquí: **el servidor acepta en
silencio un parámetro de consulta que no existe**, de modo que un cliente puede creer que
ha filtrado cuando no ha filtrado nada. Es exactamente lo que le pasa a `picking` hoy.

## 7. Causa raíz

| Clase | ¿Es? |
|---|---|
| `TEST_ASSERTION_DEFECT` | **SÍ** — la afirmación es sobre un conjunto compartido en vez de sobre la reserva del escenario |
| `TEST_ISOLATION_DEFECT` | No: ninguna prueba incumple una limpieza que le corresponda |
| `FIXTURE_CLEANUP_DEFECT` | No: las reservas de un escenario son historia legítima y no se borran |
| `E2E_SHARED_STATE_DEFECT` | Parcialmente, y es **legítimo**: la base es compartida a propósito (§35 del encargo) |
| `API_CONTRACT_DEFECT` | No: el endpoint cumple lo especificado |
| `PRODUCT_RESERVATION_DEFECT` | No: `reservado = 30` se comprueba y pasa; ubicar no toca la reserva |
| `PAGINATION_FILTERING_DEFECT` | No: no hay paginación que confundir |

**Clasificación final: `TEST_ASSERTION_DEFECT`.** Dueña **SPEC054**; apoyo SPEC031 y
SPEC022 como suites consumidoras. `OWNER_IDENTITY_CONFLICT = 0`.

Y hay una prueba directa de que no es de producto: `dispatch` y `sales-orders` hacen lo
mismo **bien**, contra el mismo endpoint y la misma base.

## 8. `/speckit.specify`

| ID | Requisito |
|---|---|
| FR-054-RES-001 | Una prueba E2E identifica la reserva de su escenario por identidad estable, sin suponer que es la única del sistema |
| FR-054-RES-002 | Ninguna prueba afirma sobre el recuento global de reservas de la empresa |
| FR-054-RES-003 | Ninguna prueba envía un parámetro de consulta que el servidor no declara |
| FR-054-RES-004 | El resultado es el mismo aislada que dentro de la suite global, y no depende del orden |
| FR-054-RES-005 | Las aserciones no se debilitan: donde se comprobaba una invariante, se sigue comprobando sobre la reserva propia |
| FR-054-RES-006 | No se modifica el contrato del producto para satisfacer una prueba |
| FR-054-RES-007 | Existe cobertura que falla si se reintroduce la suposición de recuento global |
| FR-054-RES-008 | Hay una sola manera de identificar la reserva de un escenario |

## 9. `/speckit.clarify`

| # | Pregunta | Respuesta medida | ¿Material? |
|---|---|---|---|
| 1 | Dueña | SPEC054; apoyo 031 y 022 | No |
| 2 | Endpoint exacto | `GET /inventory/reservations` | No |
| 3 | Aserción exacta | `reservasDespues.length === reservasAntes.length` sobre el conjunto de la empresa | No |
| 4 | Aislada | 9/9 | No |
| 5 | Global | 220/220 en este ciclo; el fallo es intermitente | No |
| 6 | Quién produce las reservas de más | Cualquier suite que confirme un pedido (`picking`, `dispatch`, `order-confirmation`, `sales-orders`, `returns`…) y la propia `putaway` | No |
| 7 | ¿Empresa/tenant de las extra? | **La misma empresa**: el endpoint filtra por `company_id`. No hay fuga | No |
| 8 | ¿Almacén? | Indistinto: el endpoint no lo filtra ni el contrato lo exige | No |
| 9 | ¿Estado? | Mezcla; `?status=ACTIVE` funciona si hiciera falta | No |
| 10 | Contrato de la API | «Reservas activas/históricas», sin filtro por pedido | No |
| 11 | Filtros soportados | `status`, `product_id`; `source_order_id` **no** | No |
| 12 | Paginación | No hay | No |
| 13 | ¿`count == 1` es contractual? | **No**: nunca lo fue; era una suposición de aislamiento | No |
| 14 | Identidad estable disponible | `product_id` (filtro del servidor) y `source_document` / `source_order_id` (campos publicados) | No |
| 15 | ¿Limpieza? | No corresponde: las reservas son historia | No |
| 16 | ¿Dependencia de orden? | No hay orden que arreglar; hay una premisa falsa que quitar | No |
| 17 | ¿Arreglo de producto? | **No** | No |
| 18 | ¿Cambio de contrato de API? | **No** | No |
| 19 | ¿Esquema? ¿Migración? | **0** y **0** | No |
| 20 | ¿La deuda era solo cobertura ausente? | No: era una aserción mal escrita, en dos suites | No |

**MATERIAL OQ = 0 · UNKNOWN = 0 · PRODUCT FIX REQUIRED = NO.**

## 10. Compuerta constitucional

| Principio | Cumplimiento |
|---|---|
| 1 · 2 | Spec antes que código; autorización expresa con `MATERIAL OQ = 0` |
| 3 | Trazabilidad §16 |
| 10 | R aislada, global y mecanismo determinista; mutaciones §15 |
| 22 | Una sola manera de identificar la reserva del escenario |
| 24 | Medido sobre la base del E2E con historia real (330→369 reservas) |
| 27 | Mutaciones que cambian lo observable; lo que no, se descarta y se explica |

**COMPUERTA: PASA.** `G-031-01`…`G-031-20` satisfechas.

## 11. `/speckit.plan`

`W01` checkpoint · `W02` localizar la aserción · `W03` aislada · `W04` global ·
`W05` mecanismo determinista · `W06` contrato del endpoint · `W07` filtros reales ·
`W08` recuento de manifestaciones · `W09` clasificación · `W10` ayudante de identidad ·
`W11` `putaway` · `W12` `picking` · `W13` regresión de varias reservas · `W14` mutaciones ·
`W15` Chromium · `W16` Firefox · `W17` WebKit · `W18` regresión 030/031/032 ·
`W19` suite global · `W20` clasificación · `W21` analyze · `W22` trazabilidad ·
`W23` convergencia.

### Diseño

```
e2e/helpers/reservas.ts     una sola manera de encontrar la reserva de un escenario:
                            por producto (filtro que el servidor declara) o por pedido
                            (campo que el servidor publica). Falla si no la encuentra.
putaway.spec.ts             deja de comparar recuentos globales
picking.spec.ts             deja de enviar un filtro inerte
e2e/reservas-identidad.spec un escenario identifica lo suyo con otras reservas vivas
```

## 12. `/speckit.checklist` · `/speckit.tasks`

| Compuerta | Comprobación |
|---|---|
| G-031-01..05 | Dueña, fallo localizado, aislada, global y productores identificados |
| G-031-06..08 | Contrato, filtros y paginación leídos y medidos |
| G-031-09..11 | Aislamiento de empresa verificado; almacén y estado resueltos desde el contrato |
| G-031-12 | `count == 1` resuelto: **no es contractual** |
| G-031-13 | Identidad estable definida |
| G-031-14..15 | Causa clasificada y arreglo mínimo identificado |
| G-031-16 | Ninguna aserción se debilita |
| G-031-17..20 | Mutaciones, `MATERIAL OQ = 0`, `UNKNOWN = 0`, trazabilidad 100 % |

| ID | Requisito | Acción | Aceptación | Mutación |
|---|---|---|---|---|
| T01 | FR-008 | `e2e/helpers/reservas.ts` | Encuentra la reserva propia y falla si no está | RES-02 |
| T02 | FR-001/002 | `putaway:341` afirma sobre lo suyo | Pasa con otras reservas vivas | RES-01 |
| T03 | FR-003 | `picking` deja de enviar el filtro inerte | Identifica por el campo publicado | RES-03 |
| T04 | FR-002 | `putaway:412` se acota a su producto | No recorre el conjunto ajeno | RES-01 |
| T05 | FR-007 | `reservas-identidad.spec.ts` | Falla si vuelve el recuento global | RES-01/04 |
| T06 | FR-004 | Órdenes distintos y suite global | Mismo resultado | RES-04 |

## 13. `/speckit.analyze` previo

| Búsqueda | Resultado |
|---|---|
| Suposiciones de recuento global sobre reservas | **3** (`putaway` ×2, `picking` ×2 lecturas) |
| `first()` / `nth()` para elegir reserva | **0** |
| `toHaveLength(1)` sobre el conjunto global | **0** (el de `sales-orders` es sobre el filtrado, y es correcto) |
| Parámetros de consulta inexistentes | **1** (`source_order_id` en `picking`) |
| Limpieza global de reservas | **0** |
| Fuga entre empresas o tenants | **0** — el endpoint filtra por empresa |
| Cambios de producto · esquema · migración | 0 · 0 · 0 |
| `sleeps` · `retries` · `skips` | 0 · 0 · 0 |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

**AUTORIZACIÓN EXPRESA CONSUMIDA.**

## 14. Implementación

| Fichero | Estado | Qué hace |
|---|---|---|
| `resources/frontend/e2e/helpers/reservas.ts` | **nuevo** | Una sola manera de encontrar la reserva de un escenario: `reservasDeProducto` (filtro del servidor), `reservasDePedido` (campo publicado) y `laReservaDe`, que **falla diciendo qué vio** en vez de elegir por posición |
| `resources/frontend/e2e/reservas-identidad.spec.ts` | **nuevo** | Cuatro casos que fijan la diferencia entre «hay las mismas» y «la mía sigue siendo la que era» |
| `putaway.spec.ts` | modificado | Deja de comparar recuentos globales; comprueba id, estado, cantidad y almacén de **su** reserva. La comprobación de forma se acota a su producto |
| `picking.spec.ts` | modificado | Deja de enviar el filtro inerte; identifica por el campo publicado y exige que su escenario deje alguna reserva viva que comprobar |

**Ficheros de producto = 0 · API = 0 · esquema = 0 · migraciones = 0.**

### La aserción, antes y después

```
antes:  expect(reservasDespues.length).toBe(reservasAntes.length)
        — sobre las 330-369 reservas de la empresa

después: la reserva del escenario, identificada por su producto:
        mismo id · mismo estado · misma cantidad · mismo almacén
```

No se debilita nada: donde había **una** comparación de tamaños hay ahora **cuatro**
comprobaciones sobre la reserva concreta. `picking` gana además una: que su escenario haya
dejado alguna reserva viva, porque contar cero contra cero también «pasaba».

### Dos errores míos que encontraron las propias pruebas

- La primera versión del caso de identidad afirmaba `despues === antes + 1`, que es **la
  misma suposición de recuento global** que esta delta quita. Falló en la primera
  ejecución porque mis tres casos corrían en paralelo y el conjunto creció en dos. Lo que
  la prueba quiere decir es que el conjunto **se mueve**, y eso es lo que dice ahora.
- La segunda versión elegía productos existentes con saldo, y dos casos eligieron el
  mismo. Ahora cada caso crea **su** producto y su almacén, como ya hacía `putaway`.

Ninguno de los dos se descubrió leyendo: los descubrió el mensaje de diagnóstico del
ayudante, que nombra las reservas que encontró.

## 15. Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| RES-01 | Razonar sobre el conjunto entero: el filtro del servidor se ignora | **muere** — 5 fallos, incluido `putaway` |
| RES-02 | Elegir por posición en vez de exigir identidad | **muere** — el caso de las dos reservas del mismo producto |
| RES-03 | Dejar de filtrar por pedido en el cliente | **muere** — el caso de la reserva manual |
| RES-04 | Identificar el pedido por el campo equivocado | **muere** — `picking` |

**4/4 significativas**, cada una en un camino distinto de la corrección. Restauración
verificada con `cmp` en las cuatro.

## 16. Resultados

| Medición | Antes | Después |
|---|---|---|
| Dirigida Chromium (`reservas-identidad` + `putaway` + `picking`) | — | **21 / 21** |
| Dirigida + relacionadas (030/031/032) | — | **42 / 42** |
| Firefox · WebKit | — | **20 / 20** · **20 / 20** |
| **Suite global** | 29 ficheros · 220 pruebas · 219 · 1 | **30 ficheros · 224 pruebas · 224 pasan · 0 fallan** |
| Deriva de esquema | 21 | **21** — `NEW_DRIFT = 0` |
| Cabeza Alembic | `0057_spec047_notifications` | igual |

### Clasificación de residuales

| Clase | N.º |
|---|---|
| `E2E_031_RESERVAS` · `E2E_046_TIPOS` · `E2E_SEED_EMPRESA_UNICA` | **0** · **0** · **0** |
| `N6_MULTICOMPANY_STARTUP` · `E2E_HELPER_EMPRESA_AMBIGUO` | **0** · **0** |
| `INBOX_045_AISLAMIENTO` · `AUTH_MC_INTERMITTENT` · `TEST_DEFECT_OTHER` | **0** · **0** · **0** |
| `PRODUCT_DEFECT_DISCOVERED` · `EXTERNAL_ENVIRONMENT` · `PREEXISTING_SEALED` | **0** · **0** · **0** |
| `NEW_REGRESSION_E2E031` · `UNKNOWN` | **0** · **0** |

**Suite global sin un solo fallo.** Conviene decir qué prueba y qué no: el verde de una
ejecución nunca fue la prueba, porque este fallo era intermitente y ya hubo ejecuciones
verdes con el defecto dentro. Lo que sí prueba el cierre es que **la premisa frágil ya no
está** y que hay cobertura que muere si vuelve (§15).

## 17. `/speckit.analyze` final

| Búsqueda | Resultado |
|---|---|
| Suposiciones de recuento global de reservas | **0** |
| `first()` / `nth()` para elegir una reserva | **0** |
| Parámetros de consulta que el servidor no declara | **0** |
| Limpieza global de reservas · `DELETE` encubierto | **0** · **0** |
| Filtro añadido al producto por conveniencia de la prueba | **0** |
| Fuga entre empresas · entre tenants | **0** · **0** |
| Dependencia del orden de ejecución | **0** |
| Aserciones debilitadas · `sleeps` · `retries` · `skips` | **0** · 0 · 0 · 0 |
| Cambios de producto · esquema · migraciones | 0 · 0 · 0 |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

## 18. Trazabilidad

| Requisito | Evidencia | Mutación |
|---|---|---|
| FR-054-RES-001 | `laReservaDe` + los cuatro casos de identidad | RES-02 |
| FR-054-RES-002 | `putaway` y `picking` ya no cuentan el conjunto | RES-01 |
| FR-054-RES-003 | `picking` no envía `source_order_id`; medido que el servidor lo ignora | RES-03 |
| FR-054-RES-004 | 21/21 dirigida, 42/42 con relacionadas, 224/224 global | RES-04 |
| FR-054-RES-005 | Una comparación de tamaños → cuatro comprobaciones de identidad | RES-01 |
| FR-054-RES-006 | `git status`: nada bajo `app/` ni `src/`; contrato de la 023 sin tocar | — |
| FR-054-RES-007 | `reservas-identidad.spec.ts`, 4 casos | RES-01/02 |
| FR-054-RES-008 | `helpers/reservas.ts` es la única manera | RES-01 |

Cobertura **100 %**, huérfanos **0**.

## 19. Observaciones registradas, no corregidas

- **`API-QUERY-SILENCIOSA`** (nueva): `GET /inventory/reservations` acepta sin protestar un
  parámetro de consulta que no declara —medido: `?source_order_id=<inexistente>` devuelve
  las 330 reservas—, de modo que un cliente puede creer que filtró cuando no filtró nada.
  Es lo que le pasaba a `picking`. Cambiar eso es semántica pública: fuera de alcance.
- **`E2E-SIN-TYPECHECK`** (nueva): el grafo TypeScript del proyecto cubre `src` y
  `vite.config.ts` —`tsconfig.app.json` y `tsconfig.node.json`—, así que **`e2e/` no se
  comprueba de tipos** en el flujo del proyecto y un error de tipos solo aparece como fallo
  en ejecución. *(Precisión añadida el 2026-09-19: aquí se escribió que «`tsc -p
  tsconfig.json` solo cubre `src`», y es más grave que eso: esa orden no cubre **nada**,
  porque la raíz es un* solution config *con `files: []`. Quien cubre `src` es
  `tsconfig.app.json`. Medido en `BUILD-TSC-TESORERIA`.)* Se verificó a mano con un typecheck explícito sobre `e2e/`: sin hallazgos.
  Corregida además la afirmación equivocada que quedó escrita en la delta anterior.

## 20. Convergencia

| Criterio | Estado |
|---|---|
| Causa raíz | **PROBADA** — `TEST_ASSERTION_DEFECT`, mecanismo demostrado de forma determinista |
| Dueña | **RESUELTA** — 054, apoyo 031 y 022 |
| Resultado aislado y global | **EXPLICADOS**: el fallo es intermitente y no reapareció; el mecanismo sí se reprodujo |
| Reservas de más | **IDENTIFICADAS**: misma empresa, creadas por cualquier suite que reserve |
| Contrato del endpoint | **VERIFICADO**: cumple lo especificado |
| Aserción | **CONFORME AL CONTRATO**, y más fuerte que antes |
| Dependencia de orden · fuga de empresa · de tenant | 0 · 0 · 0 |
| `E2E_031_RESERVAS` | **0 fallos** |
| Chromium · Firefox · WebKit | PASAN |
| Regresión 030/031/032 y `putaway` | PASAN |
| Mutaciones | **4/4 mueren**, restauradas |
| Suite global | **224 / 224**, sin residuales |
| Producto · esquema · migraciones · deriva nueva | 0 · 0 · 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

**VEREDICTO: CASO A — `E2E-031-RESERVAS` COMPLETE / CONVERGED.**
