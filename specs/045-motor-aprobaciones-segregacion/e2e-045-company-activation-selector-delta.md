# SPEC 045 · DELTA DIRIGIDO E2E-045 — SELECTOR AMBIGUO «ACTIVAR» EN EL E2E DE APROBACIONES

> Delta dirigido dentro de la Spec 045 ya convergida. No abre Spec nueva, no reabre la
> convergencia previa, no reescribe informes anteriores. Corrige **una** deuda conocida:
> el ayudante de sesión del E2E de aprobaciones selecciona el control equivocado.
>
> **Naturaleza: TEST DEFECT.** El producto no se modifica. Si la evidencia hubiera
> demostrado lo contrario, el delta se habría detenido; §3 documenta por qué no.

## 0. Verificación física

| Hecho | Valor |
|---|---|
| Rama | `develop` |
| HEAD base | `4d88fbd` |
| Árbol al empezar | limpio (salvo `evidence/e2e-045/`, generado por este delta) |
| PostgreSQL | 16.2 (pgserver) — objetivo 18.6 → `ENVIRONMENT_BASELINE_DEVIATION` vigente |
| Backend / Frontend | uvicorn `:8000` (200) · vite `:5173` (200) |

## 1. Ficha de la deuda E2E-045

Recuperada de los registros, no de la memoria:

| Campo | Contenido |
|---|---|
| Identificador | **E2E-045** |
| Dueña | Spec 045 — motor de aprobaciones y segregación |
| Enunciado registrado | El ayudante de sesión del E2E casa «Activar» **por subcadena** y puede pulsar «Desactivar» |
| Síntoma | La sesión de interfaz queda sin empresa activa; las pruebas que operan la UI fallan |
| Clase | `TEST_DEFECT` |
| Estado previo | Abierta |

## 2. Dueña — confirmada

La deuda es de la 045: el símbolo defectuoso vive en
`resources/frontend/e2e/approvals.spec.ts`, fichero de pruebas de esta Spec. No se toca
ningún fichero de producto ni de otra Spec.

## 3. El producto no es la causa — demostrado antes de tocar nada

`resources/frontend/src/pages/EmpresasPage.tsx:55-75` pinta, por fila, controles
**mutuamente excluyentes**:

- fila de la empresa activa → botón `Activa` (deshabilitado, `title="Empresa activa"`) + botón `Desactivar`
- fila de cualquier otra empresa → botón `Activar`

Los tres nombres accesibles son exactos y distintos. Con coincidencia exacta no existe
ambigüedad. La ambigüedad la introduce la prueba, que pide «Activar» por subcadena y
recibe «**Des**activar».

Evidencia registrada antes de la corrección, sobre `4d88fbd` intacto:

| Evidencia | Fichero | Resultado |
|---|---|---|
| Reproducción del fallo | `evidence/e2e-045/reproduccion-pre-fix.txt` | 2 failed / 9 passed |
| Estado de la empresa en base, antes y después | mismo fichero | `D1=ACTIVE` → `D1=ACTIVE` (el producto no se corrompe) |
| Diagnóstico del localizador | `evidence/e2e-045/diagnostico-selector.txt` | `ambiguo=1 exacto=0 desactivar=1 nombres=["Desactivar"]` |

El diagnóstico es concluyente: con la empresa **ya activa**, el localizador ambiguo
encuentra **un** elemento, el exacto encuentra **cero**, y el único nombre casado es
`Desactivar`. La prueba pulsaba el botón contrario y después esperaba ver «Desactivar»,
que ella misma acababa de hacer desaparecer.

## 4. Los dos fallos reproducidos

| # | Localización | Causa raíz | Clase |
|---|---|---|---|
| 1 | `approvals.spec.ts:151` (`uiLogin`) | Coincidencia por subcadena + ausencia de manejo de estado | `TEST_DEFECT` |
| 2 | `approvals.spec.ts:395` (multiempresa) | La prueba afirma algo que el contrato no sostiene | `TEST_DEFECT` |

El segundo apareció en la misma reproducción y es de la misma naturaleza, así que entra
en este delta. `GET /approvals/inbox` (`app/modules/approvals/api.py:368`) **no declara**
parámetro `company_id`: FastAPI lo descarta y el servicio delimita por `ctx.company_id`.
La prueba pasaba `company_id=empresa-inexistente` y exigía `total == 0`; obtenía 2. El
producto es correcto —delimita por contexto, que es la autoridad—; la afirmación era
falsa y, además, **tapaba un hueco real de cobertura** (§14, deuda no absorbida).

## 5. `/speckit.specify` — delta dirigido

Requisitos nuevos, numerados tras el máximo real de la Spec (`FR-045-075`):

| ID | Requisito | Prioridad |
|---|---|---|
| FR-045-076 | El ayudante de sesión del E2E identifica los controles de empresa por **nombre accesible exacto**; ninguna coincidencia por subcadena, regex amplia ni filtro de texto puede resolver a un control distinto del pretendido | P0 |
| FR-045-077 | El ayudante es **idempotente**: si la empresa ya está activa la deja activa sin pulsar nada; si no lo está la activa una sola vez; ejecutarlo dos veces seguidas deja el mismo estado final | P0 |
| FR-045-078 | Si el estado de la empresa **no es determinable**, el ayudante falla de forma explícita con mensaje diagnóstico; nunca continúa a ciegas ni deja la sesión sin empresa | P0 |
| FR-045-079 | El E2E conserva una **aserción de regresión permanente** que falla si el control equivocado vuelve a ser alcanzable por el localizador del ayudante | P0 |
| FR-045-080 | Ninguna prueba del E2E de aprobaciones afirma comportamientos que el contrato no sostiene; la delimitación de la bandeja se comprueba por **contexto**, y la prueba declara que el parámetro de consulta no es autoridad | P0 |

Criterios de aceptación nuevos, numerados tras `AC-24`:

| ID | Criterio |
|---|---|
| AC-25 | **Dado** una empresa ya activa, **cuando** se ejecuta el ayudante, **entonces** no pulsa ningún control y la empresa sigue activa |
| AC-26 | **Dado** ninguna empresa activa, **cuando** se ejecuta el ayudante, **entonces** activa exactamente una y lo verifica por el estado exacto |
| AC-27 | **Dado** el ayudante ejecutado dos veces seguidas, **entonces** el estado final es «activa» en ambos casos |
| AC-28 | **Dado** el localizador exacto de «Activar», **entonces** nunca casa con «Desactivar», y a la inversa |
| AC-29 | **Dado** un `company_id` arbitrario en la consulta de la bandeja, **entonces** la respuesta es la del **contexto**, no la del parámetro |

## 6. `/speckit.clarify`

| # | Pregunta | Resolución | Material |
|---|---|---|---|
| 1 | ¿Es defecto de producto o de prueba? | De prueba: §3 lo demuestra con el producto intacto | No |
| 2 | ¿Se renombra algún botón del producto? | No. Prohibido y además innecesario | No |
| 3 | ¿Se oculta «Desactivar»? | No | No |
| 4 | ¿`data-testid`? | No: no es política canónica del repositorio y el nombre accesible ya basta | No |
| 5 | ¿`.first()` sobre el localizador de decisión? | No. El localizador exacto debe resolver a **uno o cero** | No |
| 6 | ¿CSS/XPath posicional? | No | No |
| 7 | ¿Regex? | No: `exact: true` sobre el nombre accesible | No |
| 8 | ¿`filter({ hasText })`? | No: casaría «Desactivar» | No |
| 9 | ¿Esperas por tiempo, reintentos, `force: true`? | No. Solo esperas por condición de estado | No |
| 10 | ¿Se relaja alguna aserción? | No. Se endurecen | No |
| 11 | ¿Cómo se detecta «ya activa»? | Por el estado exacto de la fila: botón `Activa` deshabilitado y `Desactivar` presentes | No |
| 12 | ¿Qué es «no determinable»? | Ni «Activar» exacto ni el par «Activa»+«Desactivar» presentes tras cargar la pantalla | No |
| 13 | ¿Falla explícita cómo? | `expect(...).toBe(...)` con mensaje que enumera los nombres accesibles hallados | No |
| 14 | ¿La línea 196 («Activar» de la política) entra? | No: esa pantalla no tiene «Desactivar», el nombre es inequívoco. Fuera de alcance | No |
| 15 | ¿Se corrigen las copias del ayudante en otras Specs? | No: son de otras dueñas. Se registran como deuda (§14) | No |
| 16 | ¿Qué se hace con la aserción multiempresa falsa? | Se reescribe para afirmar lo que el contrato sostiene (FR-045-080) | No |
| 17 | ¿Se añade cobertura de aislamiento de bandeja en backend? | No en este delta: excede el alcance dirigido. Se registra como deuda con dueña | No |
| 18 | ¿Se toca la deuda de paginación de la bandeja (045)? | No. Explícitamente fuera | No |

**Ninguna OQ Material. El ciclo continúa sin detenerse.**

### Fuera de alcance, registrado y no tocado

Paginación/`limit-offset` de la bandeja (045) · decisión de `EXPIRED` · CLOCK-013 ·
E2E-031-RESERVAS · los seis bordes float restantes de tesorería · E2E-046-TIPOS ·
ORPHAN-046-SINGLE · IDEM-046-TRUNC · implementación de la Spec 049 · deriva global de
esquema (21 operaciones / 10 Specs).

## 7. `/speckit.plan`

| # | Paso |
|---|---|
| W01 | Reproducir el fallo sobre `4d88fbd` sin tocar nada — **hecho** |
| W02 | Probar que el producto no es la causa — **hecho** |
| W03 | Diagnosticar el localizador con la empresa ya activa — **hecho** |
| W04 | Redactar el delta, requisitos y criterios |
| W05 | Sustituir el localizador ambiguo por nombre accesible **exacto** |
| W06 | Hacer el estado explícito: activa / inactiva / no determinable |
| W07 | Idempotencia real: no pulsar si ya está activa |
| W08 | Fallo explícito y diagnóstico en el caso no determinable |
| W09 | Aserción de regresión permanente sobre la exactitud del localizador |
| W10 | Reescribir la prueba multiempresa para que afirme el contrato real |
| W11 | Pruebas dirigidas del ayudante y del localizador |
| W12 | Mutaciones E2E-045-01..03 con copia y restauración verificada |
| W13 | Chromium aislado, 3 ejecuciones consecutivas |
| W14 | Suite E2E completa de la Spec 045 |
| W15 | Tres navegadores |
| W16 | Clasificar todo fallo; recuento de Master56 desde las filas |
| W17 | Convergencia, decisión de siguiente Spec, un commit, árbol limpio |

## 8. CONSTITUTION GATE

| # | Puerta | Veredicto |
|---|---|---|
| G045-E2E-01 | No se modifica producto para que pase una prueba | **PASA** — 0 ficheros de producto |
| G045-E2E-02 | La prueba sigue probando lo mismo o más | **PASA** — se añaden aserciones, no se quitan |
| G045-E2E-03 | Selectores semánticos, no posicionales | **PASA** — rol + nombre accesible exacto |
| G045-E2E-04 | Sin esperas por tiempo | **PASA** |
| G045-E2E-05 | Sin `force`, sin reintento arbitrario, sin `skip` | **PASA** |
| G045-E2E-06 | Determinismo: mismo estado inicial → mismo resultado | **PASA** — idempotencia explícita |
| G045-E2E-07 | Fallo ruidoso, nunca silencioso | **PASA** — FR-045-078 |
| G045-E2E-08 | Ninguna aserción afirma lo que el contrato no sostiene | **PASA** — FR-045-080 |
| G045-E2E-09 | Multiempresa/multitenant preservado | **PASA** — la delimitación por contexto se comprueba, no se elude |
| G045-E2E-10 | PostgreSQL real, sin simulacros | **PASA** |
| G045-E2E-11 | Accesibilidad: el nombre accesible es el contrato de la UI | **PASA** |
| G045-E2E-12 | Deudas ajenas no absorbidas | **PASA** — §14 |
| G045-E2E-13 | Un commit coherente, árbol limpio | **PASA** |
| G045-E2E-14 | Trazabilidad 100 % requisito → prueba → evidencia | **PASA** — §15 |

## 9. `/speckit.checklist`

- [ ] Localizador exacto en las tres decisiones del ayudante
- [ ] Ninguna subcadena, regex ni `hasText` puede resolver a «Desactivar»
- [ ] Estado clasificado en tres casos exhaustivos
- [ ] Idempotencia verificada ejecutando dos veces
- [ ] Fallo explícito con diagnóstico
- [ ] Aserción de regresión permanente
- [ ] Prueba multiempresa veraz
- [ ] Mutaciones que demuestran que las pruebas detectan la regresión
- [ ] 0 ficheros de producto tocados
- [ ] Deudas ajenas registradas, no absorbidas

## 10. `/speckit.tasks`

| ID | Tarea | Requisito |
|---|---|---|
| T-01 | `uiLogin`: localizadores exactos y estado explícito | FR-045-076, 077, 078 |
| T-02 | Aserción de regresión permanente del localizador | FR-045-079 |
| T-03 | Prueba dirigida: idempotencia del ayudante | FR-045-077 |
| T-04 | Prueba dirigida: exactitud del localizador en ambos sentidos | FR-045-076, AC-28 |
| T-05 | Reescritura de la prueba multiempresa | FR-045-080, AC-29 |
| T-06 | Mutaciones E2E-045-01..03 | todos |

## 11. `/speckit.analyze` previo a implementar

| Contador | Valor |
|---|---|
| Requisitos sin tarea | 0 |
| Tareas sin requisito | 0 |
| Criterios sin prueba | 0 |
| Contradicciones con la Constitución | 0 |
| OQ Material abiertas | 0 |
| Ficheros de producto en el plan | 0 |

Trazabilidad previa: **100 %**. Se consume la autorización expresa y se implementa.

## 12. `/speckit.implement`

Un solo fichero, y es de pruebas: `resources/frontend/e2e/approvals.spec.ts` (+152 / −16).
**0 ficheros de producto.**

| Cambio | Qué hace |
|---|---|
| `controlesDeEmpresa(page)` | Los tres controles por nombre accesible **exacto**: `Activar`, `Desactivar`, `Activa` |
| `activarEmpresa(page)` | Sustituye al bloque condicional anterior: regresión permanente, salida temprana idempotente, compuerta de selección, fallo explícito |
| `uiLogin(page)` | Delega la activación; su cuerpo ya no decide nada sobre empresas |
| `empresa(request, token)` | Devuelve `{id, code}`; `companyId` pasa a apoyarse en ella. El código es el que necesita el identificador canónico de la compuerta |
| prueba multiempresa | Reescrita: siembra su propio proceso y compara contexto contra parámetro |
| dos pruebas dirigidas nuevas | Exactitud del localizador e idempotencia del ayudante |

Tres decisiones que conviene dejar por escrito:

1. **La compuerta de selección.** Al desactivar, el producto retira la tabla y muestra
   «Seleccione una empresa». Es decir: el estado «sin empresa activa» **no** se ve como
   una fila con «Activar», sino como una pantalla distinta. El ayudante anterior nunca lo
   supo porque nunca llegó a ese estado. Se resuelve por `data-testid="elegir-empresa-<código>"`,
   identificador **canónico y preexistente** del propio producto
   (`src/components/company/EstadoDeEmpresa.tsx:72`); no se añade ninguno nuevo.
2. **El código de empresa se pregunta, no se supone.** El ayudante lo obtiene de la API,
   la misma fuente que resuelve el contexto del backend. Sin prefijos ni posiciones.
3. **La prueba multiempresa siembra su propio proceso.** La bandeja es transversal y las
   demás pruebas —y los otros dos navegadores— crean solicitudes mientras ésta corre.
   Comparar la bandeja entera entre dos lecturas sucesivas medía la concurrencia, no la
   delimitación: se detectó en la tanda de tres navegadores (`21` frente a `20`) y se
   corrigió acotando a un `process_type` propio, no relajando la aserción.

## 13. Evidencia

### Antes de corregir — `evidence/e2e-045/`

| Fichero | Contenido |
|---|---|
| `reproduccion-pre-fix.txt` | 2 failed / 9 passed sobre `4d88fbd` intacto; empresa `D1=ACTIVE` antes y después |
| `diagnostico-selector.txt` | `ambiguo=1 exacto=0 desactivar=1 nombres=["Desactivar"]` |

### Después — `evidence/e2e-045/ejecuciones-post-fix.txt`

| Tanda | Resultado |
|---|---|
| Chromium aislado × 3, suite completa de la Spec 045 | **13/13, 13/13, 13/13** |
| Tres navegadores (chromium · firefox · webkit) | **39/39** |
| Vitest de frontend | 18 ficheros, **368/368** |

El flujo principal, que antes agotaba 16,9 s hasta fallar, pasa ahora en 3,7 s.

### Mutaciones — `evidence/e2e-045/mutaciones.txt`

| Mutación | Qué altera | Resultado |
|---|---|---|
| E2E-045-01 | Retira `exact` del localizador de decisión | **3 pruebas muertas**, incluida la del flujo principal |
| E2E-045-02 | Elimina la salida temprana idempotente | **1 prueba muerta** (fallo explícito, con diagnóstico) |
| E2E-045-03 | Restaura la afirmación falsa `total === 0` | **1 prueba muerta** |

Copia y restauración verificadas con `cmp` en las tres: fichero idéntico al original.

## 14. Clasificación de lo encontrado

| Hallazgo | Clase | Destino |
|---|---|---|
| Selector ambiguo en el ayudante | `TEST_DEFECT` | **Corregido** en este delta |
| Aserción multiempresa falsa | `TEST_DEFECT` | **Corregido** en este delta |
| Comparación de bandeja sensible a la concurrencia | `TEST_DEFECT` (introducido y detectado dentro del delta) | **Corregido** antes de cerrar |
| PostgreSQL 16.2 frente al objetivo 18.6 | `ENVIRONMENT_BASELINE_DEVIATION` | Vigente, ya registrado |

### Deudas identificadas y **no** absorbidas

| Deuda | Dueña | Por qué no se toca aquí |
|---|---|---|
| **E2E-HELPER-EMPRESA-AMBIGUO** — cuatro ficheros conservan copia del mismo ayudante defectuoso: `warehouse-a11y.spec.ts:11`, `warehouse-structure.spec.ts:51`, `uom-conversion.spec.ts:44`, `uom-a11y.spec.ts:28` | Specs de almacén y de unidades de medida | Son de otras dueñas; absorberlas rompería la disciplina de un delta por deuda y el alcance del commit |
| **INBOX-045-AISLAMIENTO** — el aislamiento de la bandeja **entre empresas distintas** no está probado en ningún sitio: `test_mc_security_045_046.py` cubre políticas y documentos, no la bandeja; el entorno E2E tiene una sola empresa | Spec 045 | Excede el delta dirigido. La aserción anterior **fingía** esta cobertura; ahora el hueco queda declarado en vez de tapado |
| Paginación `limit/offset` de la bandeja | Spec 045 | Fuera de alcance por instrucción expresa |

## 15. `/speckit.analyze` final y trazabilidad

| Requisito | Prueba | Evidencia |
|---|---|---|
| FR-045-076 | regresión permanente en `activarEmpresa` + «el localizador nunca alcanza Desactivar» | mutación 01 |
| FR-045-077 | «el ayudante de empresa es idempotente» | mutación 02 |
| FR-045-078 | `expect(candidatas + puerta, diagnostico).toBe(1)` | mutación 02 |
| FR-045-079 | aserción permanente dentro del ayudante | mutación 01 |
| FR-045-080 | «la bandeja la delimita el contexto, no el parámetro» | mutación 03 |

| Contador | Valor |
|---|---:|
| Requisitos sin prueba | 0 |
| Criterios (AC-25..29) sin prueba | 0 |
| Mutaciones supervivientes | 0 |
| Ficheros de producto modificados | 0 |
| Pruebas debilitadas, omitidas o marcadas | 0 |
| Fallos sin clasificar | 0 |

**Trazabilidad: 100 %. E2E-045 queda CERRADA.**

## 16. Contrato

El contrato público **no cambia**: ninguna ruta, esquema ni respuesta se ha tocado. Queda
documentado un hecho del contrato que la prueba anterior ignoraba: `GET /approvals/inbox`
no declara `company_id`; la empresa la fija el contexto (`app/modules/approvals/api.py:368`).
