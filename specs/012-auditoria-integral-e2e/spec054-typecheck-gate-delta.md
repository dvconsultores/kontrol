# SPEC 054 · Delta dirigida — BUILD-TSC-TESORERIA

**Fecha** 2026-09-19 · **Dueña** SPEC054 (`specs/012-auditoria-integral-e2e`) ·
**Apoyo** SPEC038 (dueña del fichero defectuoso) · **Base** `c121f43` · **Rama** `develop`

## 1. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` | `c121f43` |
| `ACTUAL_HEAD` | `c121f43` — **coincide** |
| `ACTUAL_BRANCH` | `develop` |
| `COMMITS_AFTER_C121F43` | **0** |
| Árbol | limpio salvo los dos artefactos de auditoría sin seguimiento, **preservados** |

## 2. El fallo, reproducido antes de tocar nada

```
$ npm run build
> tsc -b && vite build
src/modules/tesoreria/importes-float-c.test.tsx(108,34):
  error TS6133: 'ruta' is declared but its value is never read.
NPM_BUILD_EXIT=2
```

**Un solo error** —confirmado con `tsc -b --force`, sin caché— y el bundler ni siquiera
llega a ejecutarse, porque `&&` corta. La rama no compila.

El símbolo:

```ts
apiFetch.mockImplementation((ruta: string, opciones?: { method?: string }) => {
  if (opciones?.method === "POST") return Promise.resolve({ igft_amount: "37037.04" });
  return Promise.resolve({ items: [] });
});
```

`ruta` no se usa, pero **no se puede borrar**: es el primer parámetro posicional y hace
falta para llegar al segundo.

`git log` del fichero: entró completo en **`e43cf48`**, el delta FLOAT-038-C de esta misma
serie.

## 3. El grafo TypeScript, medido

| Config | Papel | `files` / `include` | Recorre |
|---|---|---|---|
| `tsconfig.json` | **solution** | `files: []`, sin `include`; `references` → app y node | **cero ficheros** |
| `tsconfig.app.json` | proyecto principal | `include: ["src"]` · `strict`, `noUnusedLocals`, `noUnusedParameters`, `noEmit` | 997 ficheros, **193 del repositorio** |
| `tsconfig.node.json` | herramientas | `include: ["vite.config.ts"]` | 1 fichero del repositorio |

**`MAIN TS GRAPH` = `src` + `vite.config.ts`.** `e2e/` **no está en ninguno de los dos**, y
eso es exactamente la deuda `E2E-SIN-TYPECHECK`, que **no se cierra aquí**.

### La medición que lo decide

| Orden | Salida | Ficheros recorridos |
|---|---|---|
| `tsc --noEmit -p tsconfig.json --listFiles` | **0** | **0** |
| `tsc --noEmit -p tsconfig.app.json --listFiles` | **2** | **997** (193 del repo) |
| `npm run typecheck` (`tsc -b --noEmit`) | **2** | el grafo completo |
| `npm run build` (`tsc -b && vite build`) | **2** | ídem |

Un `exit 0` sobre **cero ficheros** no es una validación: es una orden que no hizo nada.
Eso es lo que se aceptó como evidencia en ciclos anteriores de esta serie.

## 4. Qué está bien y qué está mal

Conviene separarlo, porque cambia el arreglo:

| Cosa | Estado |
|---|---|
| `package.json`: `build = tsc -b && vite build` | **correcto** |
| `package.json`: `typecheck = tsc -b --noEmit` | **correcto**, y detecta el error (exit 2) |
| Guía viva del repositorio | **correcta**: `specs/010-licenciamiento-central/plan.md:25` y `docs/auditoria/auditoria-001-011.md:55` ya mandan `npx tsc -b` |
| El fichero de prueba | **defectuoso**: un parámetro sin usar |
| La evidencia de QA de esta serie | **defectuosa**: se ejecutó una orden inventada en vez del script del repositorio |

Es decir: **no hay que arreglar los gates del repositorio; ya eran correctos.** Lo que
falló fue no usarlos. Por eso este ciclo no reescribe `package.json` ni los `tsconfig`: los
deja como están y añade lo que faltaba, que es algo que impida volver a aceptar una
validación vacía.

## 5. Causa raíz

| Clase | ¿Es? |
|---|---|
| `BUILD_TYPESCRIPT_DEFECT` | **SÍ** — un parámetro sin usar rompe `tsc -b` |
| `QA_FALSE_TYPECHECK_EVIDENCE` | **SÍ** — `tsc --noEmit -p tsconfig.json` recorre cero ficheros y sale 0 |
| `CONFIG_DEFECT` | **No** — los `tsconfig` describen el grafo que quieren |
| `SCRIPT_DEFECT` | **No** — los scripts del repositorio son correctos |
| `TEST_DEFECT` | Sí en sentido estricto: el defecto vive en un fichero de prueba |
| `MATERIAL_DECISION_REQUIRED` | **No** |

## 6. `/speckit.specify`

| ID | Requisito |
|---|---|
| FR-054-TSC-001 | `npm run build` termina en 0 sobre el grafo principal |
| FR-054-TSC-002 | La validación de tipos del grafo principal recorre **todos** sus proyectos referenciados |
| FR-054-TSC-003 | Una orden que recorre cero ficheros no vale como evidencia de validación |
| FR-054-TSC-004 | Hay **una** orden canónica para validar el grafo principal, y es la del propio repositorio: `npm run typecheck` |
| FR-054-TSC-005 | `importes-float-c.test.tsx` compila sin relajar ninguna regla |
| FR-054-TSC-006 | La orden canónica **falla** ante un error real introducido en el grafo principal |
| FR-054-TSC-007 | `npm run build` **falla** ante ese mismo error |
| FR-054-TSC-008 | Existe una guarda que detecta si el gate deja de validar el grafo principal: por cambiar la orden, por relajar la severidad o por perder una referencia |
| FR-054-TSC-009 | `E2E-SIN-TYPECHECK` sigue siendo deuda separada y **abierta** |
| FR-054-TSC-010 | Vitest, ESLint y la suite E2E global siguen verdes |
| FR-054-TSC-011 | No cambia el comportamiento funcional de Tesorería ni el contrato monetario de FLOAT-038-C |
| FR-054-TSC-012 | No cambia esquema ni migraciones |

## 7. `/speckit.clarify`

| # | Pregunta | Respuesta medida | ¿Material? |
|---|---|---|---|
| 1 | Dueña primaria · apoyo | SPEC054 · SPEC038 | No |
| 2 | Ruta y símbolo | `src/modules/tesoreria/importes-float-c.test.tsx:108`, parámetro `ruta` | No |
| 3 | Origen | `e43cf48` (FLOAT-038-C) | No |
| 4 | ¿Cuántos errores? | **Uno**, verificado con `--force` | No |
| 5 | Config raíz | *Solution*: `files: []` + `references` | No |
| 6 | ¿Qué valida la orden antigua? | **Nada**: 0 ficheros, exit 0 | No |
| 7 | ¿Qué valida `tsc -b`? | Los dos proyectos; 193 ficheros del repo | No |
| 8 | ¿Existe script canónico? | **Sí**: `typecheck = tsc -b --noEmit`. No hay que inventarlo | No |
| 9 | ¿Hay que cambiar `package.json`? | **No** | No |
| 10 | ¿Hay que cambiar los `tsconfig`? | **No** | No |
| 11 | ¿Hay guía viva que recomiende la orden inválida? | **No**: la guía del repositorio ya manda `tsc -b`. La orden inválida solo aparece en documentos de esta serie | No |
| 12 | ¿Cómo se arregla el parámetro? | Renombrarlo a `_ruta`: es la convención real del repositorio (`eslint.config.js:25` → `argsIgnorePattern: "^_"`, y `(_path, mod)` en `audit-completeness.test.ts:105`), y `noUnusedParameters` la respeta | No |
| 13 | ¿Guarda contra el vacío? | Una prueba de invariantes de configuración, siguiendo el patrón que el repositorio ya usa en `src/tests/` | No |
| 14 | ¿`e2e/` entra? | **No**, y sigue siendo `E2E-SIN-TYPECHECK` | No |
| 15 | Ficheros funcionales de producto | **0** | No |
| 16 | Esquema · migración | **0** · **0** | No |

**MATERIAL OQ = 0 · UNKNOWN = 0 · PRODUCT BEHAVIOR CHANGE = 0.**

## 8. Compuerta constitucional

| Principio | Cumplimiento |
|---|---|
| 1 · 2 | Spec antes que código; autorización expresa con `MATERIAL OQ = 0` |
| 3 | Trazabilidad §16 |
| 10 — Calidad demostrable | La orden antigua se mide, no se supone: 0 ficheros |
| 22 — Autoridad única | Una sola orden canónica, la del repositorio |
| 27 | Mutaciones que cambian lo observable |

**COMPUERTA: PASA.** `G-TSC-01`…`G-TSC-20` satisfechas.

## 9. `/speckit.plan` · `/speckit.tasks`

`W01` checkpoint · `W02` dueña · `W03` reproducir · `W04` todos los errores ·
`W05` el símbolo · `W06` origen · `W07` grafo · `W08` medir la orden antigua ·
`W09` medir `tsc -b` · `W10` inventario de órdenes · `W11` orden canónica ·
`W12` guarda · `W13` arreglo · `W14` controles negativos · `W15` mutaciones ·
`W16` vitest · `W17` regresión FLOAT-038-C · `W18` ESLint · `W19` build ·
`W20` E2E global · `W21` esquema · `W22` analyze · `W23` trazabilidad · `W24` convergencia.

| ID | Requisito | Acción | Aceptación | Mutación |
|---|---|---|---|---|
| T01 | FR-005 | `ruta` → `_ruta` | `npm run typecheck` en 0 | BUILD-01 |
| T02 | FR-001 | — | `npm run build` en 0, con bundler | BUILD-01 |
| T03 | FR-008 | Guarda de invariantes del gate en `src/tests/` | Detecta orden inválida, severidad relajada y referencia perdida | BUILD-02·03·04·05 |
| T04 | FR-006/007 | Control negativo con error real inyectado | Canónica y build fallan; la antigua **no** | — |
| T05 | FR-009 | `e2e/` sigue fuera | La deuda sigue abierta | — |

## 10. `/speckit.analyze` previo

| Búsqueda | Resultado |
|---|---|
| Errores TypeScript en el grafo principal | **1** |
| `@ts-ignore` · `@ts-expect-error` · `eslint-disable` como remedio | 0 · 0 · 0 |
| `strict` · `noUnusedLocals` · `noUnusedParameters` relajados | 0 · 0 · 0 |
| Exclusión de pruebas del grafo | **0** |
| Referencias de proyecto retiradas | **0** |
| Guía viva que recomiende la orden inválida | **0** |
| Cambios en producto · esquema · migraciones | 0 · 0 · 0 |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

**AUTORIZACIÓN EXPRESA CONSUMIDA.**

## 11. Implementación

| Fichero | Estado | Qué hace |
|---|---|---|
| `src/modules/tesoreria/importes-float-c.test.tsx` | modificado | `ruta` → `_ruta`. **Un solo carácter**; el `git diff` completo son dos líneas |
| `src/tests/typecheck-gate.test.ts` | **nuevo** | Seis invariantes del gate: la raíz es una solución, las órdenes usan `-b` y no `-p`, el build encadena la validación antes del empaquetado, las referencias cubren el grafo, las pruebas no quedan fuera, y la severidad que detectó el defecto sigue encendida |

**`package.json` = sin tocar · `tsconfig.*` = sin tocar · producto funcional = 0 · esquema = 0 · migraciones = 0.**

### Por qué no se toca ninguna configuración

Porque ya eran correctas. `build` y `typecheck` usan `tsc -b` desde antes de esta serie, y
la guía del repositorio también. Cambiarlas para «arreglar» esto habría sido tratar el
síntoma en el sitio equivocado: lo que falló fue **no ejecutarlas**, y contra eso una
configuración distinta no protege. Lo que protege es una prueba que se rompa si el gate
deja de ser un gate.

### Por qué `_ruta` y no otra cosa

Es la convención del propio repositorio: `eslint.config.js:25` declara
`argsIgnorePattern: "^_"`, `audit-completeness.test.ts:105` ya usa `(_path, mod)`, y
`noUnusedParameters` de TypeScript respeta el guion bajo. Borrar el parámetro no era
posible —es posicional y hace falta para llegar al segundo— y suprimir el aviso con
`@ts-ignore` habría dejado el gate mintiendo otra vez, que es justo lo que este ciclo
viene a cerrar.

## 12. Control negativo — la prueba de que la orden antigua no validaba

Con un error de tipos inequívoco inyectado en `src/lib/format.ts`, que pertenece al grafo
principal:

```ts
const kontrolControlNegativo: number = "no soy un número";
```

| Orden | Resultado |
|---|---|
| `tsc --noEmit -p tsconfig.json` *(la que se usó como evidencia)* | **exit 0** · **cero líneas de salida** |
| `npm run typecheck` | **exit 2** · `src/lib/format.ts(30,7): error TS2322: Type 'string' is not assignable to type 'number'` |
| `npm run build` | **exit 2** · el mismo error |

Restaurado y verificado con `cmp`; `git diff` de `src/lib/` vacío.

No hace falta más para clasificar: una orden que declara éxito sobre un fichero con
`const x: number = "texto"` no estaba comprobando tipos.

## 13. Resultados

| Gate | Antes | Después |
|---|---|---|
| `npm run build` | **exit 2**, el bundler ni se ejecuta | **exit 0**, `✓ built in 3.20s` |
| `npm run typecheck` | **exit 2** | **exit 0** |
| Guarda del gate | no existía | **6 / 6** |
| Vitest completo | 379 | **385** (379 + 6) |
| Regresión dirigida de tesorería | — | **17 / 17** |
| ESLint | limpio | **limpio** |
| Typecheck explícito de `e2e/` | sin hallazgos | **sin hallazgos** (regresión; la deuda sigue abierta) |
| Deriva de esquema · cabeza Alembic | 21 · `0057_spec047_notifications` | **21** · igual |

## 14. Mutaciones

| Mutación | Qué reintroduce | Resultado |
|---|---|---|
| BUILD-01 | El parámetro sin usar | **muere** — `typecheck` y `build` en 2, con el error original |
| BUILD-02 | El gate vuelve a `tsc --noEmit -p tsconfig.json` | **muere** — «las órdenes del repositorio recorren las referencias» |
| BUILD-03 | `noUnusedParameters: false` | **muere** — «sigue encendida la severidad que detectó el defecto» |
| BUILD-04 | Las pruebas se excluyen del proyecto | **muere** — «las pruebas del proyecto entran en el grafo» |
| BUILD-05 | Se pierde una referencia de la solución | **muere** — «las referencias cubren el grafo principal» |

**5/5 significativas**, cada una en una aserción distinta. Restauración verificada con
`cmp` en las cinco, y árbol sin residuos.

## 15. Dos afirmaciones mías, corregidas

Este ciclo obliga a revisar lo que quedó escrito, porque la evidencia falsa no se corrige
sola:

- `specs/001-fundacion/spec001-business-timezone-delta.md` daba el `tsc` por limpio en un
  momento en que la rama **ya no compilaba** —`e43cf48` es anterior—. Se corrige.
- `specs/012-auditoria-integral-e2e/spec054-reservation-identity-delta.md` decía que
  `tsc -p tsconfig.json` «solo cubre `src`». Es impreciso: no cubre nada; es
  `tsconfig.app.json` el que cubre `src`. Se corrige.

La delta que introdujo el defecto, `spec038-remaining-float-boundaries-delta.md`, **no
afirmó nada** sobre `tsc`: no hay nada que corregir ahí.

## 16. Suite E2E global

| Medida | Valor |
|---|---|
| Ficheros · pruebas ejecutadas | 30 · **224** |
| Pasan · fallan | **224** · **0** |
| Omitidas · sin ejecutar | 0 · 0 |
| Salida de Playwright | **0** |

| Clase | N.º |
|---|---|
| `BUILD_TYPESCRIPT_DEFECT` | **0** |
| `QA_FALSE_TYPECHECK_EVIDENCE` en el gate activo | **0** |
| `CONFIG_DEFECT` · `SCRIPT_DEFECT` | **0** · **0** |
| `NEW_REGRESSION_BUILD` | **0** |
| `E2E_SIN_TYPECHECK` | **1** — deuda separada, **OPEN**, no absorbida |
| `EXTERNAL_ENVIRONMENT` · `PREEXISTING_SEALED` · `MATERIAL_DECISION_REQUIRED` | 0 · 0 · 0 |
| `OWNER_IDENTITY_CONFLICT` · `UNKNOWN` | **0** · **0** |

## 17. `/speckit.analyze` final

| Búsqueda | Resultado |
|---|---|
| `npm run build` falla | **0** |
| Falso PASS del typecheck canónico | **0** — demostrado con control negativo |
| Errores TypeScript en el grafo principal | **0** |
| `@ts-ignore` · `@ts-expect-error` · `eslint-disable` como remedio | 0 · 0 · 0 |
| `strict` · `noUnusedLocals` · `noUnusedParameters` relajados | 0 · 0 · 0 |
| Pruebas excluidas del grafo | **0** |
| Referencias de proyecto perdidas | **0** |
| `E2E-SIN-TYPECHECK` cerrada por accidente | **0** |
| Cambios en `package.json` o en los `tsconfig` | **0** |
| Cambios en producto funcional · esquema · migraciones | 0 · 0 · 0 |
| `BLOCKER` · `CRITICAL` · contradicciones · conflicto de dueña | 0 · 0 · 0 · 0 |
| Requisitos huérfanos · tareas huérfanas | 0 · 0 |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

## 18. Trazabilidad

**Defecto de compilación:** `npm run build` exit 2 → `TS6133` → `importes-float-c.test.tsx:108`
→ dueña SPEC038 → FR-054-TSC-005 → `ruta` → `_ruta` → `npm run typecheck` exit 0 →
`npm run build` exit 0 → mutación **BUILD-01** → evidencia.

**Evidencia falsa de QA:** `tsc --noEmit -p tsconfig.json` exit 0 → `tsconfig.json` es
*solution* con `files: []` → medido: **0 ficheros** frente a 997 → control negativo: la
antigua sale 0 sobre un error evidente, la canónica sale 2 → FR-054-TSC-003/004/008 →
guarda `typecheck-gate.test.ts` → mutaciones **BUILD-02·03·04·05** → evidencia.

| Requisito | Evidencia | Mutación |
|---|---|---|
| FR-054-TSC-001 | `npm run build` exit 0 con bundler | BUILD-01 |
| FR-054-TSC-002 | 997 ficheros recorridos frente a 0 | BUILD-05 |
| FR-054-TSC-003 | Control negativo §12 | BUILD-02 |
| FR-054-TSC-004 | `npm run typecheck`, del propio repositorio | BUILD-02 |
| FR-054-TSC-005 | `_ruta`, sin relajar nada | BUILD-01 · BUILD-03 |
| FR-054-TSC-006 | Canónica exit 2 con error inyectado | — |
| FR-054-TSC-007 | Build exit 2 con error inyectado | — |
| FR-054-TSC-008 | Guarda, 6 invariantes | BUILD-02·03·04·05 |
| FR-054-TSC-009 | `e2e/` fuera del grafo; deuda abierta | — |
| FR-054-TSC-010 | Vitest 385 · ESLint 0 · E2E 224/224 | — |
| FR-054-TSC-011 | `git diff` de tesorería: **un carácter** | — |
| FR-054-TSC-012 | Deriva 21 → 21; 57 migraciones | — |

Cobertura **100 %**, huérfanos **0**.

## 19. Convergencia

| Criterio | Estado |
|---|---|
| Dueña | **RESUELTA** — 054, apoyo 038 |
| Fallo de build | **REPRODUCIDO** y corregido |
| Todos los errores TypeScript | **CLASIFICADOS** (uno) |
| Grafo TypeScript | **MAPEADO** y medido |
| Conducta de la orden antigua | **PROBADA**: 0 ficheros, falso PASS |
| Orden canónica | **DEFINIDA** (ya existía) · **PASA** · **FALLA** ante error inyectado |
| `npm run build` | **PASA** · **FALLA** ante error inyectado |
| Severidad · exclusión de pruebas · referencias | preservadas · ninguna · completas |
| Vitest · ESLint · E2E global | 385 · limpio · **224/224** |
| Regresión dirigida FLOAT-038-C | **17/17**; contrato monetario intacto |
| `E2E-SIN-TYPECHECK` | **OPEN**, no absorbida |
| Producto funcional · esquema · migraciones · deriva | 0 · sin cambios · 0 · 21 → 21 |
| Mutaciones | **5/5 mueren**, restauradas |
| `MATERIAL OQ` · `UNKNOWN` | 0 · 0 |

**VEREDICTO: CASO A — `BUILD-TSC-TESORERIA` COMPLETE / CONVERGED.**

SPEC054 sigue `PARTIALLY_IMPLEMENTED`; SPEC038 y FLOAT-038-C conservan
`COMPLETE / CONVERGED`.
