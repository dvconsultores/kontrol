# SPEC 054 · Delta dirigida — E2E-046-TIPOS

**Fecha** 2026-09-18 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) ·
**Apoyo** SPEC046 (pantalla de tipos documentales) · **Requisito de origen** `FR-001-065` ·
**Base** `ce71cc7` · **Rama** `develop`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `ce71cc7` |
| `ACTUAL_HEAD` | `ce71cc7` — **coincide** |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_CE71CC7` | **0** |
| Árbol | limpio salvo los dos artefactos de auditoría sin seguimiento, **preservados** |

## 2. El fallo, localizado

`documents.spec.ts:309`, prueba «los tipos documentales declaran la política sin código»:

```ts
const next = page.getByRole("button", { name: "Página siguiente" });
for (let i = 0; i < 20 && await next.isEnabled(); i += 1) {
  if (await page.getByRole("cell", { name: code }).count()) break;
  await next.click();
  await page.waitForTimeout(150);
}
await expect(page.getByRole("cell", { name: code })).toBeVisible();
```

El síntoma no es una aserción que falla: es una **espera que no termina**. `isEnabled()`
sobre un control que no existe espera hasta agotar la prueba —30 s—, y por eso el error es
`Test timeout ... waiting for getByRole('button', { name: 'Página siguiente' })` y no un
«esperaba X, había Y».

## 3. Los datos, contados

| Medida | Valor |
|---|---|
| Tipos documentales en la base del E2E | **10** |
| Empresa | **todos de `D1`**; ninguno global ni de otra empresa |
| Estado | **10 `ACTIVE`**, 0 inactivos |
| De dónde salen | **ninguno es semilla**: los diez los crean las propias suites. Dos con prefijo `UI…` son de esta misma prueba en ejecuciones anteriores; el resto, `E2E…`, `A11Y…`, `K…`, de `documents` y `documents-a11y` |

Ese último dato importa: el número no lo fija una semilla estable, lo fija **cuántas veces
se ha ejecutado la suite**. Con nueve tipos previos, la prueba crea el décimo y se queda
exactamente en el borde.

## 4. El contrato de paginación

| Capa | Realidad verificada |
|---|---|
| Backend | `GET /documentos/tipos` devuelve **una lista entera**, sin `limit` ni `offset`: la pantalla la pide sin parámetros y recibe `DocumentTypeInfo[]` |
| Frontend | La paginación es **de cliente**, dentro de `DataTable` |
| Regla | `components/DataTable.tsx:112`: `{total > 10 ? <Pagination …/> : null}` |
| Declaración | `components/Pagination.tsx:1`: «Pagination — solo si total > 10 (FR-019)» |
| Requisito | `specs/001-fundacion/spec.md:167` · `FR-001-065`: «DataTables sin scroll horizontal, búsqueda general, filtro de estado, **paginación >10**, acciones a la derecha». Repetido en `FR-002-042` y `AC-002-005` |
| Tamaño de página | 10 por defecto; el selector ofrece 10 · 25 · 50 · 100 |
| Con `total = 10` | **No se pinta ningún paginador**: ni «Página siguiente» ni «Página anterior» ni el selector de tamaño |

**El producto hace exactamente lo que su requisito manda.** Con diez registros no hay
segunda página, y no pintar un control inútil es la conducta especificada.

## 5. Qué quería probar la prueba

Leída entera: entra por la interfaz, rellena código, nombre y formatos MIME admitidos,
pulsa «Crear tipo», confirma el aviso de creación y **comprueba que el tipo aparece en la
tabla**. El nombre de la prueba lo dice: *los tipos documentales declaran la política sin
código*.

El paseo por páginas es **incidental**: un medio para encontrar la fila porque «el tipo
recién creado ordena al final», según su propio comentario. No es el objetivo, y no hay
ninguna aserción sobre paginación en toda la prueba.

## 6. Causa raíz

| Clase | ¿Es? |
|---|---|
| `TEST_PAGINATION_ASSERTION_DEFECT` | **SÍ** — da por hecho un control que el contrato dice que no debe existir con diez registros |
| `TEST_DATA_ASSUMPTION_DEFECT` | **SÍ**, en su forma: supone que siempre habrá más de una página, cuando el número de tipos depende de cuántas veces haya corrido la suite |
| `E2E_FIXTURE_DEFECT` | No: no falta ningún dato; sobra una premisa |
| `PAGINATION_CONTRACT_DEFECT` | **No**: el contrato es claro y está en la spec |
| `PRODUCT_PAGINATION_DEFECT` | **No**: `total > 10` es lo especificado y lo implementado |

**Clasificación final: `TEST_PAGINATION_ASSERTION_DEFECT`.** `PRODUCT FIX REQUIRED = NO`.

Hay además una prueba directa de que el producto no es el problema: la cobertura unitaria
de `DataTable` **ya** fija las dos mitades del contrato —sin paginador con ≤ 10, con
paginador con > 10— y pasa. Lo que no cubre es el **borde exacto**, que es justo el caso
que rompió el E2E.

## 7. `/speckit.specify`

| ID | Requisito |
|---|---|
| FR-054-TIPOS-001 | Ninguna prueba supone que existe «Página siguiente» cuando el total no supera el tamaño de página |
| FR-054-TIPOS-002 | La prueba encuentra el tipo que acaba de crear sea cual sea el número de tipos de la base |
| FR-054-TIPOS-003 | El borde exacto `total == 10` tiene cobertura propia: una sola página, sin paginador |
| FR-054-TIPOS-004 | El caso `total == 11` tiene cobertura propia: paginador, «Página siguiente» utilizable y segunda página con un registro |
| FR-054-TIPOS-005 | Esa cobertura no depende de datos globales ni los crea: vive donde el contrato vive |
| FR-054-TIPOS-006 | No se modifica el producto: ni el tamaño de página, ni la regla del paginador, ni la pantalla |
| FR-054-TIPOS-007 | No se añade un tipo documental permanente a ninguna semilla para forzar una segunda página |
| FR-054-TIPOS-008 | Ninguna aserción se debilita: la prueba sigue exigiendo ver el tipo creado |
| FR-054-TIPOS-009 | La suite global vuelve a verde y todo residual queda clasificado |

## 8. `/speckit.clarify`

| # | Pregunta | Respuesta medida | ¿Material? |
|---|---|---|---|
| 1 | Dueña | SPEC054; apoyo SPEC046 | No |
| 2 | Propósito del test | Crear un tipo por la interfaz y verlo listado | No |
| 3 | Total real de tipos | **10**, todos de `D1`, todos activos | No |
| 4 | Origen de los diez | Las propias suites; **ninguna semilla** los fija | No |
| 5 | Tamaño de página | 10 por defecto (10/25/50/100 en el selector) | No |
| 6 | Contrato del backend | Lista entera, sin paginar | No |
| 7 | Contrato del frontend | Paginación de cliente; paginador solo si `total > 10` | No |
| 8 | Conducta con 10 | Una página, **ningún control de paginación** | No |
| 9 | Conducta con 11 | Paginador con «Página siguiente» utilizable | No |
| 10 | ¿Ausente o deshabilitado? | **Ausente**: el bloque entero no se pinta | No |
| 11 | ¿El producto es correcto? | **Sí**, `FR-001-065` | No |
| 12 | ¿Hace falta fixture local? | **No** para el E2E; el borde se cubre donde vive el contrato | No |
| 13 | ¿Limpieza? | No se crean datos nuevos, así que no hay nada que limpiar | No |
| 14 | Alcance de los tipos | Por empresa (`company_id`) | No |
| 15 | Orden | Por creación: el nuevo queda al final, de ahí el paseo original | No |
| 16 | Idioma / nombre accesible | «Página siguiente» es el `aria-label` real; no hay problema de traducción | No |
| 17 | ¿Búsqueda en la pantalla? | **No la hay**: las únicas palancas son el selector de tamaño y los botones, y ambos solo existen por encima de 10 | No |
| 18 | Ficheros de producto | **0** | No |
| 19 | Esquema · migración | **0** · **0** | No |

**MATERIAL OQ = 0 · UNKNOWN = 0 · PRODUCT FIX REQUIRED = NO.**

## 9. Compuerta constitucional

| Principio | Cumplimiento |
|---|---|
| 1 · 2 | Spec antes que código; autorización expresa con `MATERIAL OQ = 0` |
| 3 | Trazabilidad §15 |
| 10 | Reproducido y medido antes de tocar |
| 11 — Accesibilidad | La prueba sigue usando el nombre accesible real, no un selector posicional |
| 22 | El contrato de paginación tiene una sola autoridad: `DataTable` |
| 27 | Mutaciones que cambian lo observable |

**COMPUERTA: PASA.** `G-TIPOS-01`…`G-TIPOS-19` satisfechas.

## 10. `/speckit.plan` · `/speckit.tasks`

`W01` checkpoint · `W02` dueña · `W03` reproducir · `W04` contar tipos · `W05` origen ·
`W06` contrato del backend · `W07` contrato del frontend · `W08` intención de la prueba ·
`W09` clasificar · `W10` diseño · `W11` implementar · `W12` bordes 9/10/11 ·
`W13` Chromium · `W14` Firefox · `W15` WebKit · `W16` repetibilidad · `W17` mutaciones ·
`W18` suite de documentos · `W19` typecheck explícito de E2E · `W20` vitest ·
`W21` E2E global · `W22` clasificación · `W23` analyze · `W24` trazabilidad ·
`W25` convergencia.

| ID | Requisito | Acción | Aceptación | Mutación |
|---|---|---|---|---|
| T01 | FR-001/002/008 | `documents.spec.ts:309` deja de suponer el paginador y usa la palanca que el producto ofrece cuando la ofrece | Pasa con 10 y con más de 10 | TIPOS-01 |
| T02 | FR-003 | Borde `total == 10` en `DataTable.test.tsx` | Sin paginador | TIPOS-02 |
| T03 | FR-004 | Borde `total == 11` y navegación a la página 2 | Paginador, siguiente utilizable, 1 fila en la 2ª | TIPOS-03 · TIPOS-04 |
| T04 | FR-005/007 | Sin datos nuevos en semillas | `git diff` de `qa/` vacío | — |
| T05 | FR-009 | Suite global re-medida | `UNKNOWN = 0` | — |

### Diseño

La pantalla no tiene búsqueda, así que para encontrar una fila cuando la tabla pagina solo
queda el selector «Registros por página» —que el producto expone exactamente cuando hay
más de una página—. La prueba lo usa **si está**, y si no está es porque todo cabe en una
página. En los dos casos la aserción final es la misma y no se toca: el tipo creado tiene
que verse.

El borde `10` y el caso `11` **no se cubren en E2E**: se cubren donde vive el contrato, en
la prueba unitaria de `DataTable`, que ya fija las dos mitades con 5 y 15 registros. Llevar
ese borde al E2E obligaría a crear once tipos documentales en una base compartida —datos
permanentes, maestros, que además harían pasar esta misma prueba por el motivo equivocado—.

## 11. `/speckit.analyze` previo

| Búsqueda | Resultado |
|---|---|
| Suposiciones de «hay página siguiente» | **1** (la corregida) |
| Dependencias del volumen global de datos | **1** (la misma) |
| `first()` / `nth()` sobre el paginador | **0** |
| Semilla modificada para forzar una página 2 | **0** |
| Cambio de tamaño de página | **0** |
| `sleeps` · `retries` · `skips` · aserciones debilitadas | 0 · 0 · 0 · 0 |
| Cambios de producto · esquema · migración | 0 · 0 · 0 |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

**AUTORIZACIÓN EXPRESA CONSUMIDA.**

## 12. Implementación

| Fichero | Estado | Qué hace |
|---|---|---|
| `resources/frontend/e2e/documents.spec.ts` | modificado | Deja de suponer «Página siguiente». Usa el selector de tamaño **si el producto lo pinta**, y si no lo pinta es que todo cabía. La aserción final no cambia |
| `resources/frontend/src/components/DataTable.test.tsx` | ampliado | Tres casos nuevos: `total = 10` sin paginador, `total = 9` sin paginador, y `total = 11` con navegación real a la segunda página |

**Ficheros de producto = 0 · configuración = 0 · esquema = 0 · migraciones = 0 · semillas = 0.**

### Dónde se cubre cada cosa, y por qué

El borde vive en `DataTable`, así que la cobertura del borde vive ahí: con once filas la
prueba pulsa «Página siguiente» de verdad, comprueba que la segunda página trae la que
sobra y que los dos controles cambian de estado. Llevar eso al E2E habría exigido crear
once tipos documentales **permanentes** en una base compartida —son maestros, no hay
limpieza— y, de paso, habría hecho pasar la prueba de documentos por el motivo equivocado:
con once tipos el paginador aparece y el bucle antiguo también habría funcionado.

## 13. Verificación en los tres estados del borde

La base tenía diez tipos y dos eran de esta misma prueba en ejecuciones anteriores. Se
retiraron **solo esos dos** —datos que la prueba había creado, sin documentos colgando— y
se ejecutó tres veces seguidas, de modo que el recuento pasara por 9, 10 y 11:

| Vuelta | Tipos antes → después | Resultado |
|---|---|---|
| 1 | 8 → 9 | **pasa** |
| 2 | 9 → **10** | **pasa** ← el borde exacto que fallaba |
| 3 | 10 → 11 | **pasa** |

Con eso quedan cubiertos de un tiro la repetibilidad (§53) y la independencia del volumen:
la prueba ya no depende de cuántas veces se haya ejecutado la suite.

## 14. Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| TIPOS-01 | El paginador aparece con exactamente diez (`total >= 10`) | **muere** — el borde nuevo. Y la prueba preexistente de «≤ 10», que usa cinco filas, **sobrevive**: prueba de que el borde estaba sin cubrir |
| TIPOS-02 | «Página siguiente» sigue habilitada en la última página | **muere** — la navegación de once |
| TIPOS-03 | La suposición original de que el paginador siempre está, con la base en el borde | **muere**, y con el síntoma exacto de la deuda: `Test timeout … locator.isEnabled` |
| TIPOS-04 | Se pide diez por página en vez de cien: la fila queda en la segunda | **muere** |

**4/4 significativas.** Restauración verificada con `cmp` en las cuatro.

Se intentó y **se descarta** una quinta: elegir el control de tamaño por posición
(`locator("select").first()`) en vez de por su nombre accesible. **No muere**, y el motivo
es comprobable: esa pantalla tiene un solo `<select>`, así que la posición y el nombre
apuntan al mismo elemento. Se deja escrito en vez de contarla.

## 15. Regresión

| Suite | Resultado |
|---|---|
| `documents` + `documents-a11y`, Chromium | **12 / 12** |
| Ídem, WebKit | **12 / 12** |
| Ídem, Firefox | 1 fallo en la primera vuelta; **12/12** en las dos siguientes (§16) |
| `vitest` completo | **20 ficheros · 379 pruebas** (376 + las 3 nuevas), 0 fallos |
| `eslint` | sin hallazgos |
| Typecheck **explícito** de `e2e/` | sin hallazgos |
| Deriva de esquema · migraciones | 21 → 21 · 0 |

### Un fallo intermitente, observado una vez y no absorbido

En la primera vuelta de Firefox falló `documents.spec.ts:159`, y no en la parte que esta
delta toca sino en el ayudante `createDocument`: «Documento creado» no apareció en 15 s.
Aislada pasa, y el mismo conjunto pasa **12/12 dos veces seguidas** después. Es
intermitencia bajo carga con un antivirus real de por medio, en una prueba que esta delta
no modifica. Se clasifica `TEST_DEFECT_OTHER`, se deja registrada y **no se absorbe**.

## 16. Un hallazgo serio, ajeno a esta delta

**El `build` del frontend está roto en `HEAD`.** `npm run build` encadena `tsc -b && vite
build`, y `tsc -b --noEmit` sale con **código 2**:

```
src/modules/tesoreria/importes-float-c.test.tsx(108,34):
  error TS6133: 'ruta' is declared but its value is never read.
```

Es idéntico antes y después de esta delta, así que no lo introduce. Lo introdujo `e43cf48`
—el delta FLOAT-038-C, de esta misma sesión—, y conviene decir por qué no se detectó
entonces: aquellos ciclos ejecutaron `tsc --noEmit -p tsconfig.json`, y ese `tsconfig.json`
es de tipo *solution* —`"files": []` más `references`—, de modo que **sin `-b` no compila
nada y sale limpio siempre**. La orden correcta es la que el propio `package.json` usa en
`typecheck` y en `build`: `tsc -b`.

Es la segunda vez en esta sesión que una afirmación mía sobre `tsc` resulta vacía; la
primera fue el `e2e/` fuera del proyecto, ya corregida en su documento. Se registra como
deuda **`BUILD-TSC-TESORERIA`** y **no se corrige aquí**: el alcance de esta delta es
`E2E-046-TIPOS`. Va primera en la cola siguiente, porque una rama que no compila es peor
que cualquiera de las deudas que quedan.

## 17. Suite E2E global

| Medida | Valor |
|---|---|
| Ficheros | 30 |
| Pruebas ejecutadas (Chromium) | **224** |
| Pasan | **224** |
| Fallan | **0** |
| Omitidas · sin ejecutar | 0 · 0 |
| Salida de Playwright | **0** |

| Clase | N.º |
|---|---|
| `E2E_046_TIPOS` | **0** |
| `E2E_031_RESERVAS` · `E2E_SEED_EMPRESA_UNICA` | **0** · **0** |
| `N6_MULTICOMPANY_STARTUP` · `E2E_HELPER_EMPRESA_AMBIGUO` | **0** · **0** |
| `INBOX_045_AISLAMIENTO` · `AUTH_MC_INTERMITTENT` | **0** · **0** |
| `PRODUCT_DEFECT_DISCOVERED` · `EXTERNAL_ENVIRONMENT` · `PREEXISTING_SEALED` | **0** · **0** · **0** |
| `TEST_DEFECT_OTHER` | **0** en esta ejecución; 1 observado en Firefox (§15), registrado |
| `NEW_REGRESSION_E2E046` · `UNKNOWN` | **0** · **0** |

## 18. `/speckit.analyze` final

| Búsqueda | Resultado |
|---|---|
| Suposiciones de «hay página siguiente» | **0** |
| Dependencias del volumen global de datos | **0** — verificado en 9, 10 y 11 |
| Semilla modificada · tipo once permanente | **0** · **0** |
| Cambio de tamaño de página · de la regla del paginador | **0** · **0** |
| `first()` / `nth()` sobre controles de paginación | **0** |
| Aserciones debilitadas | **0** — la final es la misma de antes |
| `sleeps` · `retries` · `skips` | 0 · 0 · 0 |
| Datos creados sin limpiar por el arreglo | **0** — el arreglo no crea nada |
| Cambios de producto · esquema · migraciones | 0 · 0 · 0 |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

## 19. Trazabilidad

| Requisito | Evidencia | Mutación |
|---|---|---|
| FR-054-TIPOS-001 | La prueba ya no consulta «Página siguiente» | TIPOS-03 |
| FR-054-TIPOS-002 | Pasa con 9, 10 y 11 tipos | TIPOS-04 |
| FR-054-TIPOS-003 | `no muestra paginación con exactamente 10 registros` | TIPOS-01 |
| FR-054-TIPOS-004 | `con 11 registros la segunda página trae el que sobra` | TIPOS-02 |
| FR-054-TIPOS-005 | La cobertura del borde vive en `DataTable.test.tsx`; `git diff` de `qa/` vacío | — |
| FR-054-TIPOS-006 | `git status`: ningún fichero de producto | — |
| FR-054-TIPOS-007 | Ninguna semilla tocada; los tipos retirados eran de la propia prueba | — |
| FR-054-TIPOS-008 | La aserción final es idéntica a la original | TIPOS-04 |
| FR-054-TIPOS-009 | 224 / 224 | — |

Cobertura **100 %**, huérfanos **0**.

## 20. Convergencia

| Criterio | Estado |
|---|---|
| Dueña | **RESUELTA** — 054, apoyo 046 |
| Causa raíz | **PROBADA** — `TEST_PAGINATION_ASSERTION_DEFECT` |
| Total y tamaño de página | **MEDIDOS** — 10 y 10 |
| Paginación del producto | **CONFORME AL CONTRATO** (`FR-001-065`) |
| `total == 10` · `total > 10` | **PASAN**, en unitarias y en E2E |
| Aislamiento del fixture | **PASA**: el arreglo no crea datos |
| Chromium · Firefox · WebKit | PASAN |
| Repetibilidad | **3 vueltas** por los tres estados del borde |
| Typecheck explícito de `e2e/` | **PASA**; la deuda `E2E-SIN-TYPECHECK` sigue **OPEN** |
| `E2E_046_TIPOS` | **0** |
| Suite global | **224 / 224**, sin residuales |
| Producto · esquema · migraciones · deriva nueva | 0 · 0 · 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

**VEREDICTO: CASO A — `E2E-046-TIPOS` COMPLETE / CONVERGED.**

SPEC054 sigue `PARTIALLY_IMPLEMENTED`; SPEC046 conserva su estado.
