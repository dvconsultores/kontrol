# SPEC 054 · DELTA DIRIGIDO E2E-HELPER-EMPRESA-AMBIGUO

> Delta de **infraestructura de pruebas**, dentro de la Spec 054 (QA integral), cuyos
> artefactos viven en `specs/012-auditoria-integral-e2e`. Corrige el ayudante de empresa
> que contamina la señal de la suite E2E. **No toca producto.**

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` | `0c47f61` / `0c47f61` — coinciden |
| `COMMITS_AFTER_0C47F61` | **0** |
| `ACTUAL_BRANCH` | `develop` |
| `WORKTREE_STATE` | dos informes de auditoría sin confirmar, preservados: `KONTROL_MASTER_COMPLETENESS_AUDIT.md` y `qa/audits/KONTROL-AUDIT-POLICY-CLOCK-LOCAL-20260917/`. Ajenos a este delta: no se borran, no se mueven, no se incorporan |

## 1. Dueña canónica

| Papel | Spec | Evidencia |
|---|---|---|
| **Principal** | **SPEC 054 — QA integral** | `spec-equivalence-map.md:61` → «054 QA integral ↔ `012-auditoria-integral-e2e` … Spec de proceso QA, no funcional». La deuda está en la infraestructura de pruebas, no en la funcionalidad de ninguna empresa |
| Apoyo | Specs de almacén y de unidades de medida | Sus E2E son quienes reutilizan el ayudante roto |

`OWNER_IDENTITY_CONFLICT = 0`. Nota de convención: la 054 no numera requisitos con
`FR-…`; usa tareas `T-…`. Para este delta se adoptan identificadores propios
`FR-054-E2E-HELPER-00N`, declarados aquí para que la trazabilidad no dependa de una
convención inexistente.

## 2. Precedente: E2E-045

El ciclo `E2E-045` (`cf11639`, CASO A) ya demostró el mecanismo en `approvals.spec.ts`:
`getByRole("button", { name: "Activar" })` casa **por subcadena** con «Des**activar**», de
modo que el ayudante pulsaba el control contrario y después esperaba el botón que él
mismo acababa de hacer desaparecer. La corrección fue: nombre accesible **exacto**,
estado explícito, idempotencia y **cero cambios de producto**.

Aquel ciclo dejó registradas, sin absorberlas, las copias del ayudante defectuoso en
cuatro ficheros. Este delta las cierra. **No se copia su implementación sin recon**: se
verifica primero, y de hecho el producto ha cambiado desde entonces (ahora hay una
compuerta de selección de empresa).

## 3. Inventario físico de los ayudantes de empresa

| Fichero | Línea | Localizador | Veredicto |
|---|---:|---|---|
| `uom-a11y.spec.ts` | 28, 31 | `{ name: "Activar" }.first()` / `{ name: "Desactivar" }.first()` | **AMBIGUO** |
| `uom-conversion.spec.ts` | 44, 47 | ídem | **AMBIGUO** |
| `warehouse-a11y.spec.ts` | 30, 33 | ídem | **AMBIGUO** |
| `warehouse-structure.spec.ts` | 51, 54 | ídem | **AMBIGUO** |
| `approvals.spec.ts` | 57-58, 92 | `exact: true` + `data-testid` canónico + idempotencia | correcto (E2E-045) |
| `documents.spec.ts` | 72, 75 | `exact: true` | correcto |
| `documents-a11y.spec.ts` | 32, 35 | `exact: true` | correcto |
| `n6-multicompany.spec.ts`, `n6-a11y-responsive.spec.ts`, `notifications.spec.ts` | varias | `getByTestId("elegir-empresa-D1/D2")` | correcto, sin ambigüedad |
| `rates.spec.ts` | 427 | `fila.getByRole("button", { name: "Desactivar" })` | **no es empresa**: desactiva una *fuente de tasas*, y está acotado a su fila |
| `approvals.spec.ts` | 259 | «Activar» de una **política** | pantalla sin «Desactivar»: inequívoco |

**Ayudantes defectuosos: 4. Copias: 4, una por fichero. No hay ayudante compartido.**

## 4. Reproducción, antes de tocar nada

Ejecutados los cuatro ficheros en Chromium (`TZ=Europe/Amsterdam`):

```
12 failed · 6 passed
Locator: getByRole('button', { name: 'Desactivar' }).first()
Error: element(s) not found
```

Y el diagnóstico de los nombres accesibles reales, tomado en este mismo delta:

```
DIAGNOSTICO ambiguo=1 exacto=0 desactivar=1 activa=1
            nombres_del_ambiguo=["Desactivar"]
            botones=["","Salir","Activa","Desactivar",""]
```

Con la empresa ya activa, el localizador exacto de «Activar» encuentra **cero**
elementos y el ambiguo encuentra **uno**, que se llama «Desactivar». El producto expone
nombres exactos, únicos y distintos —`Activa` (deshabilitado), `Desactivar`, `Activar`—:
la ambigüedad la pone la prueba.

**`TEST_DEFECT`. `PRODUCT_DEFECT` = 0.**

## 5. Recuento físico de la suite completa, antes del arreglo

No se reutiliza el «163/39» del ciclo anterior. Medido de nuevo sobre `0c47f61`, Chromium:

| Métrica | Valor |
|---|---:|
| Pruebas ejecutadas | **208** |
| Pasadas | **164** |
| Fallidas | **38** |
| Sin ejecutar (cascada) | **6** |

### Clasificación de los 38

| Clase | Nº | Cuáles |
|---|---:|---|
| **`E2E_HELPER_EMPRESA_AMBIGUO`** | **12** | `warehouse-structure` 4 · `uom-a11y` 4 · `warehouse-a11y` 3 · `uom-conversion` 1 |
| `N6_MULTICOMPANY_STARTUP` | **25** | `n6-multicompany` 13 · `n6-a11y-responsive` 12. La sesión no arranca: esas suites usan los usuarios `ua`/`ub`/`uab` que crea su propio arranque en **otra base**, no en la del E2E |
| `EXTERNAL_ENVIRONMENT` | **1** (+6 en cascada) | `notifications.spec.ts` exigía `KONTROL_E2E_DB_URL` y la segunda empresa. Resuelto **en el entorno**, sin tocar el repositorio: 7/7 tras completar el lanzador y ejecutar `qa/spec047-e2e-seed.py` |
| `E2E_046_TIPOS` | **0** | No se manifestó en esta ejecución |
| `PRODUCT_DEFECT_DISCOVERED` | **0** | — |
| `UNKNOWN` | **0** | — |

**Los 38 no comparten raíz.** El ayudante explica 12; el resto, no.

## 6. `/speckit.specify`

| ID | Requisito | Prioridad |
|---|---|---|
| FR-054-E2E-HELPER-001 | Los ayudantes de selección de empresa identifican los controles por **semántica accesible no ambigua** | P0 |
| FR-054-E2E-HELPER-002 | No dependen de coincidencia parcial cuando existe más de un control compatible | P0 |
| FR-054-E2E-HELPER-003 | El ayudante es **idempotente**: si la empresa pedida ya está activa, no toca nada | P0 |
| FR-054-E2E-HELPER-004 | El ayudante **verifica la postcondición**: la empresa activa final es la solicitada | P0 |
| FR-054-E2E-HELPER-005 | La corrección **no modifica producto** | P0 |
| FR-054-E2E-HELPER-006 | Los ficheros afectados pasan en Chromium antes de ampliar navegadores | P0 |
| FR-054-E2E-HELPER-007 | Y después en Firefox y WebKit | P0 |
| FR-054-E2E-HELPER-008 | La suite E2E completa se ejecuta tras el arreglo y **todo** fallo restante queda clasificado | P0 |
| FR-054-E2E-HELPER-009 | Ninguna deuda independiente se absorbe ni se declara resuelta sin evidencia | P0 |
| FR-054-E2E-HELPER-010 | Existe cobertura que **mata** la reintroducción del selector ambiguo | P0 |

## 7. `/speckit.clarify`

| # | Pregunta | Resolución | Material |
|---|---|---|---|
| 1 | Dueña real | 054, con artefactos en `012-auditoria-integral-e2e` | No |
| 2 | Ayudante real | Cuatro copias locales de `uiLogin`; **no hay ayudante compartido** | No |
| 3 | Nº de consumidores | Cada copia sirve a su propio fichero | No |
| 4 | Pruebas afectadas | 12 fallidas + 6 sin ejecutar, en 4 ficheros | No |
| 5 | Navegadores afectados | Reproducido en Chromium; el defecto es de selector, no de motor | No |
| 6 | Nombres accesibles reales | `Activa` (deshabilitado), `Desactivar`, `Activar`, y la compuerta con `data-testid` canónico | No |
| 7 | ¿Basta la coincidencia exacta? | Sí para los tres botones; la compuerta usa el identificador que el producto ya trae | No |
| 8 | ¿Hay dos controles legítimos? | Sí: la fila activa muestra `Activa` **y** `Desactivar`. Por eso la subcadena sobra | No |
| 9 | ¿Hace falta idempotencia? | Sí: en este entorno la empresa llega **ya activa**, que es justo el caso que rompía | No |
| 10 | Postcondición fiable | Exactamente una `Desactivar` y una `Activa`, y cero `Activar` exactos | No |
| 11 | ¿Depende de traducción? | Sí, del castellano, como toda la suite. No se amplía a auditoría de idiomas | No |
| 12 | ES/EN | Los fixtures E2E operan en castellano; no hay conmutador de idioma en juego | No |
| 13 | ¿Está duplicado? | Sí, cuatro veces | No |
| 14 | ¿Existe ya uno corregido? | Sí, en `approvals.spec.ts` (E2E-045). Se toma como referencia | No |
| 15 | ¿Copias locales? | Las cuatro | No |
| 16 | ¿Los 38 comparten raíz? | **No**: 12 del ayudante, 25 del arranque N6, 1 de entorno | No |
| 17 | ¿Cuáles son de E2E-046-TIPOS? | Ninguno en esta ejecución | No |
| 18 | ¿Cuáles de n6? | 25, aislados y no absorbidos | No |
| 19 | ¿Defecto de producto? | **No**: los nombres accesibles son exactos y únicos | No |
| 20 | ¿Ficheros de producto = 0? | Sí | No |

**MATERIAL OQ = 0 · UNKNOWN = 0 · PRODUCT FIX REQUIRED = NO.**

### Cobertura que este entorno no permite, declarada

Las transiciones **A→B** y **B→A** exigen un usuario con dos empresas. En la base del
E2E no existe: `qa/spec047-e2e-seed.py` deja al administrador **a propósito** con acceso
solo a `D1`, porque su objetivo es demostrar aislamiento. La suite que cubre el cambio
entre empresas es `n6-multicompany.spec.ts`, cuyos usuarios viven en su propio arranque.
Por tanto este delta cubre **A→A** y la ambigüedad; **A→B no se finge**, y el ayudante se
escribe aceptando la empresa objetivo para que esa cobertura sea posible cuando exista.

## 8. `/speckit.plan`

`W01` checkpoint · `W02` dueña · `W03` reproducir la ambigüedad · `W04` inventario de
ayudantes · `W05` consumidores · `W06` recuento global · `W07` clasificación ·
`W08` estrategia de selectores exactos · `W09` idempotencia · `W10` postcondición ·
`W11` ayudante canónico · `W12` los cuatro ficheros · `W13` Chromium ·
`W14` Firefox · `W15` WebKit · `W16` mutaciones · `W17` suites relacionadas ·
`W18` E2E completa · `W19` clasificación final · `W20` analyze · `W21` trazabilidad ·
`W22` convergencia.

### Diseño

Un **ayudante canónico** en `e2e/helpers/empresa.ts`, consumido por los cuatro ficheros:

```
activarEmpresa(page, codigo?)
  → navega a la pantalla de empresas
  → guarda de regresión: todo lo que alcance el localizador exacto se llama «Activar»
  → si ya está activa (Desactivar + Activa)  → no toca nada
  → si aparece la compuerta «Seleccione una empresa» → elige por el testid canónico
  → si hay exactamente una candidata → la activa
  → en cualquier otro caso → falla en el acto, enumerando lo que encontró
  → postcondición: exactamente una Desactivar y una Activa, y cero Activar exactos
```

`approvals.spec.ts`, `documents.spec.ts` y `documents-a11y.spec.ts` **no se migran**: ya
son correctos, pertenecen a deltas convergidos y moverlos sería un refactor ajeno. Queda
declarada la duplicación restante como observación, no como defecto.

## 9. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G-E2E-01 | Dueña resuelta | **PASA** |
| G-E2E-02 | Ambigüedad reproducida | **PASA** — §4 |
| G-E2E-03 | Causa raíz exacta | **PASA** |
| G-E2E-04 | Inventario de ayudantes completo | **PASA** — 4 |
| G-E2E-05 | Inventario de consumidores completo | **PASA** |
| G-E2E-06 | Pruebas afectadas identificadas | **PASA** — 12 + 6 |
| G-E2E-07 | Defectos de producto conocidos | **PASA** — 0 |
| G-E2E-08 | Ficheros de producto esperados = 0 | **PASA** |
| G-E2E-09 | Estrategia de selector exacto definida | **PASA** |
| G-E2E-10 | Idempotencia definida | **PASA** |
| G-E2E-11 | Postcondición definida | **PASA** |
| G-E2E-12 | Sin `first()` como parche | **PASA** |
| G-E2E-13 | Sin aumentar tiempos de espera | **PASA** |
| G-E2E-14 | Sin `skip` ni `fixme` | **PASA** |
| G-E2E-15 | Plan de clasificación global definido | **PASA** |
| G-E2E-16 | Mutaciones significativas | **PASA** — 5 |
| G-E2E-17 | Material OQ = 0 | **PASA** |
| G-E2E-18 | UNKNOWN = 0 | **PASA** |
| G-E2E-19 | Trazabilidad 100 % | **PASA** |

## 10. `/speckit.checklist`

- [ ] HEAD verificado · árbol clasificado · dueña verificada · precedente revisado
- [ ] Ambigüedad reproducida · error de Playwright y nombres accesibles capturados
- [ ] Ayudantes y duplicados inventariados · consumidores inventariados
- [ ] Los 38 fallos reconciliados y separados por causa
- [ ] Selector exacto, idempotencia y postcondición diseñados
- [ ] Sin `first()`, sin `nth()`, sin esperas arbitrarias, sin `skip`
- [ ] Sin ficheros de producto · Chromium, Firefox y WebKit planificados
- [ ] Suite completa planificada · mutaciones planificadas
- [ ] Material OQ = 0 · UNKNOWN = 0 · trazabilidad 100 %

## 11. `/speckit.tasks`

| ID | Tarea | Fichero | Requisito | Mutación |
|---|---|---|---|---|
| T-01 | Ayudante canónico de empresa | `e2e/helpers/empresa.ts` | 001-004 | 01, 02, 03, 04, 05 |
| T-02 | `warehouse-a11y` consume el ayudante | su `uiLogin` | 001, 005 | 01 |
| T-03 | `warehouse-structure`, ídem | ídem | 001, 005 | 01 |
| T-04 | `uom-conversion`, ídem | ídem | 001, 005 | 01 |
| T-05 | `uom-a11y`, ídem | ídem | 001, 005 | 01 |
| T-06 | Pruebas dirigidas: ambigüedad, idempotencia y postcondición | `e2e/empresa-helper.spec.ts` | 003, 004, 010 | todas |
| T-07 | Matriz de navegadores y suite completa | — | 006-008 | — |

**Requisitos huérfanos: 0. Tareas huérfanas: 0.**

## 12. `/speckit.analyze` previo a implementar

| Contador | Valor |
|---|---:|
| BLOCKER / CRITICAL / CONTRADICTIONS | 0 / 0 / 0 |
| OWNER CONFLICT | 0 |
| ORPHAN REQUIREMENTS / TASKS | 0 / 0 |
| MATERIAL OQ / UNKNOWN | 0 / 0 |
| PRODUCT FIX REQUIRED | **NO** |
| TRACEABILITY | 100 % |

Se consume la autorización expresa y se implementa.

## 13. `/speckit.implement`

| Fichero | Cambio |
|---|---|
| `e2e/helpers/empresa.ts` | **Nuevo.** `controlesDeEmpresa()` y `activarEmpresa(page, codigo?)`: nombre accesible exacto, guarda de regresión permanente, idempotencia, compuerta por identificador canónico, fallo explícito y **postcondición verificada** |
| `warehouse-a11y`, `warehouse-structure`, `uom-conversion`, `uom-a11y` | Sus `uiLogin` dejan de tener copia propia y llaman al ayudante |
| `e2e/empresa-helper.spec.ts` | **Nuevo.** 4 pruebas dirigidas sobre el propio ayudante |

**Ficheros de producto: 0.** Verificado con `git status`: solo cambian ficheros de `e2e/`.

### Lo que no se migra, y por qué

`approvals.spec.ts`, `documents.spec.ts` y `documents-a11y.spec.ts` ya resolvieron esto
en sus ciclos y son correctos. Migrarlos sería refactor de deltas convergidos sin ganar
corrección. Queda **declarada** la duplicación restante como observación —tres copias
correctas— y no como defecto.

## 14. Evidencia — `evidence/e2e-helper-empresa/`

| Fichero | Contenido |
|---|---|
| `reproduccion-pre-fix.txt` | Los 12 fallos, el error literal, el diagnóstico de nombres accesibles y la clasificación de los 38 |
| `ejecuciones.txt` | Dirigidas, tres navegadores, regresiones y las tres mediciones globales |
| `mutaciones.txt` | Las mutaciones, incluidas las descartadas con su motivo |

### Señal recuperada

| Medición | Ejecutadas | Pasadas | Fallidas | Sin ejecutar |
|---|---:|---:|---:|---:|
| Antes | 208 | 164 | **38** | 6 |
| Después (1ª) | 212 | 183 | 28 | 1 |
| **Después (2ª)** | **212** | **185** | **26** | 1 |

`E2E_HELPER_EMPRESA_AMBIGUO` restantes: **0**.

### Los 26 restantes, clasificados

| Clase | Nº | Detalle |
|---|---:|---|
| `N6_MULTICOMPANY_STARTUP` | **25** | Usan `ua`/`ub`/`uab`, que su propio arranque crea en **otra base**. La sesión no llega a abrirse. **No absorbido** |
| `E2E_SEED_EMPRESA_UNICA` | **1** | `notifications:243` exige la segunda empresa; con ella activa, las suites cuyos usuarios no están acotados caen en la compuerta. **Deuda nueva**, registrada, **no absorbida** |
| cascada | 1 | Consecuencia del anterior |
| `E2E_HELPER_EMPRESA_AMBIGUO` | **0** | — |
| `NEW_REGRESSION_E2E_HELPER` | **0** | — |
| `E2E_046_TIPOS` | **0** | No se manifestó |
| `PRODUCT_DEFECT_DISCOVERED` | **0** | — |
| `UNKNOWN` | **0** | — |

### La deuda nueva, demostrada

Con `D2` en `INACTIVE`, `order-confirmation` y `putaway` pasan **16/16**; con `D2` activa
fallaban. Es prueba directa de que el conflicto entre `qa/pg-e2e-seed.py` (una empresa) y
`qa/spec047-e2e-seed.py` (añade la segunda) —y no el ayudante— los tumbaba. Se registra
como **`E2E-SEED-EMPRESA-UNICA`**, dueña 054.

### Intermitencia observada y descartada

En la primera medición fallaron además `approvals:214` y `approvals:391`. Aislados pasan
13/13 y en la segunda medición pasaron. No consumen el ayudante corregido:
`TEST_DEFECT_OTHER`, intermitente bajo carga. Registrado, no absorbido.

### Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| E2E-HLP-01 | La coincidencia parcial en «Activar» | **muere** — la guarda de regresión lo detecta en la causa |
| E2E-HLP-02 | La compuerta se resuelve por posición (`getByRole("button").first()`) | **muere** |
| E2E-HLP-03 | `.first()` en lugar del selector semántico | **muere** |
| E2E-HLP-04 | Se rompe la idempotencia | **muere** |

**4/4 efectivas**, restauración `cmp` idéntica en todas.

Se intentaron y **se descartan** tres más, en vez de contarlas:

- retirar `exact` de «Desactivar» y de «Activa»: **sin efecto observable**, porque con una
  sola empresa ningún otro control contiene esos nombres;
- eliminar la postcondición: **sin efecto**, porque solo retira una comprobación sin
  alterar la conducta, y el entorno no permite construir un caso donde el clic no cambie
  el estado;
- invertir la postcondición a `toHaveCount(0)`: **se satisface trivialmente** justo tras
  el clic, antes de que la tabla se repinte.

Y una observación que salió de intentarlo: retirando **a la vez** la guarda y el `exact`,
la suite **sigue pasando**, porque la idempotencia corta antes de pulsar. Es defensa en
profundidad —la idempotencia es lo que salva los doce fallos y la exactitud es la segunda
línea—, y se deja escrito porque explica por qué esas mutaciones no mueren.

## 15. Cobertura que este entorno no permite

**A→B y B→A no se cubren.** Exigen un usuario con dos empresas y en la base del E2E no
existe: `qa/spec047-e2e-seed.py` deja al administrador acotado a `D1` **a propósito**,
porque su objetivo es demostrar aislamiento. La suite que cubre el cambio entre empresas
es `n6-multicompany.spec.ts`, cuyos usuarios viven en su propio arranque —y que hoy no
arranca (§14). El ayudante acepta la empresa objetivo para que esa cobertura sea posible
cuando exista; **no se finge**.

## 16. `/speckit.analyze` final y trazabilidad

| Requisito | Prueba | Mutación |
|---|---|---|
| FR-054-E2E-HELPER-001 | `el localizador de «Activar» nunca alcanza «Desactivar»` | 01 |
| FR-054-E2E-HELPER-002 | ídem + guarda dentro del ayudante | 01, 03 |
| FR-054-E2E-HELPER-003 | `es idempotente: pedir la empresa que ya está activa no la apaga` | 04 |
| FR-054-E2E-HELPER-004 | `desde el estado contrario converge y verifica la postcondición` + `la empresa activa es la que el contexto usa de verdad` | 02 |
| FR-054-E2E-HELPER-005 | 0 ficheros de producto | — |
| FR-054-E2E-HELPER-006 | Chromium 22/22 | todas |
| FR-054-E2E-HELPER-007 | Firefox 22/22 · WebKit 22/22 | — |
| FR-054-E2E-HELPER-008 | Dos mediciones globales y clasificación completa | — |
| FR-054-E2E-HELPER-009 | N6, semillas y aprobaciones intermitentes: registrados, no absorbidos | — |
| FR-054-E2E-HELPER-010 | La guarda permanente dentro del ayudante | 01 |

| Contador final | Valor |
|---|---:|
| Ayudantes de empresa ambiguos | **0** |
| `.first()` o `.nth()` injustificados en el objetivo | **0** |
| Postcondiciones débiles | **0** |
| Ficheros de producto modificados | **0** |
| `NEW_REGRESSION_E2E_HELPER` | **0** |
| BLOCKER / CRITICAL / CONTRADICTIONS | 0 / 0 / 0 |
| OWNER CONFLICT | 0 |
| ORPHAN REQUIREMENTS / TASKS | 0 / 0 |
| MATERIAL OQ / UNKNOWN | 0 / 0 |
| **TRACEABILITY** | **100 %** |

## 17. Deudas no absorbidas

E2E-031-RESERVAS · E2E-046-TIPOS · INBOX-045-AISLAMIENTO · ORPHAN-046-SINGLE ·
IDEM-046-TRUNC · paginación de la bandeja · AUTH-MC-INTERMITENTE · D0-06 · D0-07 ·
OQ-048 · MD-049 · camino tras `EXPIRED` · Spec 018 · certificación de compras ·
Spec 053 · deriva heredada de 21 operaciones · DT-03/04/06/07/10..18 ·
`license_timezone`. Y las dos que este delta **descubre y registra**:
**`E2E-SEED-EMPRESA-UNICA`** y el arranque de **`n6-multicompany`**.

## 18. Estado resultante

| | |
|---|---|
| **E2E-HELPER-EMPRESA-AMBIGUO** | **CLOSED / CONVERGED** |
| Spec 054 | sigue `PARTIALLY_IMPLEMENTED`: cerrar esta deuda no la completa |
| Specs de almacén y de unidades | sin cambio de estado; solo su E2E deja de mentir |
| Producto | intacto |
