# TRE-03 · Registro de intentos de DeepSeek (2026-11-17)

- **Llamadas:** vía el subagente `deepseek-executor`, con `deepseek-v4-pro`, sin `session_id` ni `thinking`, `stream: true` y `max_tokens` 32000.
- **Egreso:** antes de cada llamada, `EGRESS_CHECK` con `herramientas/egress.py`, todo a 0. Solo salieron código y datos sintéticos.
- **Topes (§47):** objetivo de 4 a 6 llamadas, tope duro de 8 y máximo 2 reintentos por subproblema. No se hereda ninguna excepción del ciclo anterior.
- **Autoría:** DeepSeek escribe todo el código y las pruebas. Claude diseña, redacta los encargos, audita, aplica tal cual y verifica.

| N.º | Encargo | Tokens (entrada/salida) | Coste (USD) | Auditoría |
|---|---|---|---|---|
| 1 | C1 · T002: modelos (8 tablas), migración 0124, proyección neutral, BUD-09 (proyección y guarda), CTL-01 TRE-03, permisos, MFA, auditoría y guardas | 24470/18241 | 0,026514 | 2 ficheros nuevos y 21/26 bloques **PASS**. 5 **REJECT**: SEARCH sin coincidencia en `test_audit_catalog_backup` y `test_gov_ctl01_reglas`, porque el ejecutor envió fragmentos reconstruidos a mano. Defectos tras aplicar: una variable local sombrea `pendiente_de_ordenar` (UnboundLocalError en BUD-09) y un `UUID` donde se esperaba `str` (mypy). Todo pasa a C2a, parte E |
| 2 | C2a · T003 parte 1: esquemas, servicio y API de políticas y numeración, más las correcciones E1–E4 de C1 | 16501/913 | 0,007972 | Parcial: solo devolvió el fichero A (esquemas), **PASS** y aplicado. B–E no llegaron; DeepSeek se detuvo tras el primer fichero (`finish_reason` stop). El ejecutor volvió a enviar contexto reconstruido a mano |
| 3 | C2a-r1 · reintento 1 de C2a, con el payload montado por script a partir de cortes exactos | 17320/8850 | 0,015234 | **PASS**: B, C, D y E1–E4 (7/7 bloques). Aplicado. `ruff --fix` F401/I001 (FORMAT_ONLY). Quedan para C2b, parte E: mypy (variable de bucle reutilizada), F841 `act_id`, constantes de competencia duplicadas y, de C1, `DISTINCT` sobre JSON en `ordenes_emitidas_de_causa` (falla en PG) |
| 4 | C2b · T003 parte 2: servicio y API de la orden, más las correcciones E de C1/C2a | 23006/17920 | 0,025598 | Correcciones E (6/6 bloques) **PASS** y aplicadas. Servicio y API **REJECT**: un error de sintaxis (l. 1307), `db` sin definir, una relación inexistente `orden.lineas`, `Document.name` (el campo es `title`), `get_company_context` importado de un módulo que no lo tiene, un control de saldo que compara código con id, `str + None` y unos 25 errores de mypy. Diagnóstico en una copia desechable fuera del árbol |
| 5 | C2b-r1 · reintento 1: servicio y API completos con D1–D12 | 26263/16655 | 0,025914 | **PASS** con reservas, aplicado: la app arranca; BUD-09, OpenAPI y alcance 83/83. Quedan 4 errores de mypy (uno real: `l["cause_id"]` sobre un modelo, l. 1021), E741 y F841, que van con C3 |
| 6 | C3 · T004: 30 pruebas backend + correcciones F1–F5 | 32161/14249 | 0,026387 | Correcciones F 11/12 (bloque 7 con `--todas`, bloque 8 idéntico omitido), aplicadas. Pruebas aplicadas para diagnóstico: **0/30** en PG. Defectos de las pruebas: crean de nuevo `caus_b09`, comprueban `CATALOGO_DE_PERMISOS` como tuplas, `_cdp` con código de partida aleatorio (KeyError), SQL directo a una tabla inventada `government_payment_order_config`. Defectos del servicio: `linea` sin definir (l. 306, introducido por F5), campos de auditoría fuera del catálogo (`tipo_regla`, `estado`), validación de tipo documental de la política que rechaza un tipo válido, y mypy (redefinición de `causa`, `Document | None`). Diagnóstico en una copia desechable fuera del árbol: con 4 parches de diagnóstico, 3/30 |

## TRE-03-RECOVERY-01 (2026-11-17)

Antes de cada llamada: las 30 pruebas en PG sobre el árbol real, y capas descubiertas en una copia desechable fuera del árbol con parches de diagnóstico registrados (nunca aplicados). Payload montado por script con cortes exactos.

| N.º | Encargo | Tokens (entrada/salida) | Coste (USD) | Auditoría |
|---|---|---|---|---|
| — | C7, primer envío | — | — | No llegó al MCP: argumento JSON mal formado por el ejecutor. No consume llamada |
| 7 | C7: reparación integral (6 PRODUCT y 11 TEST/FIXTURE clasificados) | 22044/16492 | 0,023937 | 11/12 bloques **PASS**. Bloque 1: la primera línea de contexto del SEARCH traía 8 espacios en lugar de 4. Esa línea era idéntica en SEARCH y REPLACE y se recortó (FORMAT_ONLY); el cambio real quedó intacto. Fichero de pruebas aplicado y `ruff --fix` I001/F401 (FORMAT_ONLY). Resultado: **7/30**. Introdujo el atributo inexistente `orden.lines` (21 rojas) y quedaron 4 defectos de prueba. En la copia, con esos 6 defectos neutralizados: 30/30 |
| 8 | C8: 6 defectos exactos (Q1 `orden.lines`, Q2 límite con None, R1–R4 de pruebas) + F841 | 5043/2773 | 0,004606 | 10/11 bloques **PASS**. Bloque 5 **REJECT**: su SEARCH ya lo había alterado el bloque 4; solo era limpieza F841. Resultado: **TRE-03 30/30 en aislamiento** y BUD-09 25/25 en aislamiento. **Juntos, en cualquier orden, fallan**: `mundo` tiene `scope="module"`, pero `tests.test_gov_bud08._ESTADO` cachea el mundo a nivel de módulo y TRE-03 comparte esos módulos ayudantes con BUD-09, así que el segundo módulo recibe un mundo inexistente (`assert documento is not None`, `test_gov_bud09_causado.py:288`). TEST_DEFECT de aislamiento del fichero de TRE-03. Sin llamada 9, queda abierto |

**Cierre del microciclo:** 8/8 llamadas, `OWNER_EXCEPTION_USED=0`. Coste del microciclo: 0,028543 USD. Coste de TRE-03 hasta hoy: 0,156162 USD.

**Defecto abierto exacto (TEST_DEFECT, aislamiento):** `tests/test_gov_tre03_orden_pago.py` reutiliza `_preparar` (BUD-08, vía BUD-09), que guarda `_ESTADO["s"]` sin clave de mundo, junto con `_CUENTAS`, `_TIPO_SOPORTE` y `_CUENTAS_T03`, indexados por `id(mundo)` o globales. Hace falta que el módulo de TRE-03 aísle esos estados al empezar y al terminar (fixture de módulo que los vacíe), o un ayudante de mundo propio. Sin ese cambio, la PG completa fallará en BUD-09 o en TRE-03.

## TRE-03-COMPLETION-02 (2026-11-17), ciclo nuevo sobre `9a18d5a`

Fusión ordinaria de `origin/develop` (`9a18d5a`, GOV-SOD-COVERAGE-01 de P2) por avance rápido. No hubo ficheros en común con el WIP, que se respaldó antes en `~/.cache/kontrol-qa/tre03/wip-v2/`. Tope nuevo: 8 llamadas, `deepseek-v4-pro`, sin excepción heredada. Payloads montados por script, de 40.000 caracteres como máximo.

| N.º | Encargo | Tokens (entrada/salida) | Coste (USD) | Auditoría |
|---|---|---|---|---|
| 1 | C1 · aislamiento de cachés heredadas (fixture de módulo autouse) + 5 avisos de ruff | 4587/1152 | 0,002887 | 5/5 **PASS**. `ruff --fix --select I001` (FORMAT_ONLY). **TRE-03 30/30, BUD-09 25/25, BUD-09→TRE-03 55/55 y TRE-03→BUD-09 55/55**. Trío BUD-08+BUD-09+TRE-03 68/68. PG dirigida 646/646 (ORG-03/04/06, CTL-01/02/07, REP-10, cobertura SoD de P2, TRE-01/02, auditoría, MFA, delegación, fixtures, OpenAPI, alcance, spec018). Migración: ida, vuelta e ida PASS; cabeza única 0124 |
| — | C2 (3 mensajes, unos 78.000 caracteres) | — | — | No llegó a DeepSeek: el puente no pudo retransmitir el argumento. No consume llamada. Se dividió en 2a y 2b |
| 2 | C2a · B1 `monto_ordenado` de la línea desde la proyección (PRODUCT_DEFECT: un borrador aparentaba consumir), B3 control LIMITE previo sin efectos, pruebas B2/B4, `api.ts`, rutas, pantallas y menú | 10627/6299 | 0,009992 | 8/8 **PASS**. Backend 55/55 combinado |
| 3 | C2b · lista y detalle | 11312/9292 | 0,013005 | 2/2 aplicados. Defectos D1–D4 (import, ruta de opciones, CSV, cast de requestId) |
| 4 | C4 · nueva y edición de la orden | 10851/7221 | 0,011002 | 1/1 aplicado. Defectos D5–D7 |
| 5 | C5 · políticas y numeración | 9238/10549 | 0,013196 | 2/2 aplicados. 23 × TS18048 y otros defectos |
| 6 | C6 · 13 correcciones | 7690/4783 | 0,007506 | 22/22 **PASS**. Queda TS2448 (`useEffect` antes de `configuracion`) |
| 7 | C7 · Vitest de detalle y nueva orden + C0 (TS2448) | 12024/8704 | 0,012803 | 3/3 aplicados. Producto: tsc 0 errores. Vitest **8/19**; 22 errores de tsc en las fábricas de prueba |
| 8 | C8 · corrección de las dos pruebas | 10887/3796 | 0,008038 | **Formato incumplido**: devolvió `OrdenPagoPage.test.tsx` completo en una valla, sin SEARCH/REPLACE, y no tocó `NuevaOrdenPagoPage.test.tsx`. Se aplicó tal cual como sustitución del fichero (FORMAT_ONLY, registrado; la versión de C7 se guardó en el scratchpad). Vitest **12/19** |

**Cierre:** 8/8 llamadas, `OWNER_EXCEPTION_USED=0`, sin llamada 9. Coste del ciclo: 0,078429 USD. TRE-03 acumulado: 0,234591 USD. `PRODUCT_STATUS=BLOCKED` (§45).

**Defectos de Claude (encargos):**
- `CONSULTA_ORDENES` definida como cadena.
- Código SoD `GOV_SOD_CONFLICT_BLOCKED` en lugar de `GOV_SOD_CONFLICT`.
- No se avisó de que el rótulo obligatorio añade «(obligatorio)».

**Pendiente exacto:**
- **TEST_DEFECT:**
  - `NuevaOrdenPagoPage.test.tsx`:
    - `getByLabelText("Concepto")` debe ser `getByRole("textbox", {name: /^Concepto/})`;
    - las fábricas `ObligacionElegible`, `documentos` (`document_type_id`), `numero` y `autoridad` no respetan los tipos;
    - `within` y `RUTA_ORDENES` no se usan;
    - falta el `Route` de destino `/:ordenId`.
  - `OrdenPagoPage.test.tsx`:
    - `numero` (l. 54);
    - «Cumple», «Falta» y «Bloqueado» están partidos entre elementos;
    - el `h1` tras emitir no se encuentra (probablemente el GET simulado sigue devolviendo BORRADOR tras la invalidación).
- **Sin empezar:** Vitest de `OrdenesPagoPage` y de políticas, E2E principal y multicausado, humo UAT, axe en 1280, 390 y 320 px, mutaciones, PG completa y tarjeta de la dueña.

## TRE-03-COMPLETION-03 (2026-11-17) · tope 5, `deepseek-v4-pro`

**WIP canónico.** `~/.cache/kontrol-qa/ctl05` (árbol vivo, HEAD 9a18d5a, 31 entradas). `tre03/wip-v3/` es su instantánea: `tracked.patch` es idéntico byte a byte y los ficheros sin seguimiento son idénticos. `tre03/wip-v2/` es la instantánea anterior a la fusión (BASE 7ef0c21), obsoleta, y no se mezcla. No hay contradicción. Las rutas `tre03/wip-*` son copias de seguridad (`BASE`, `tracked.patch`, `untracked.tgz`), no árboles de trabajo. `origin/develop` sigue en 9a18d5a, así que P2 no avanzó.

**Diagnóstico de los 7 rojos heredados (§39):** todos TEST_DEFECT.
- La línea de control es un `<li>` con texto plano compuesto.
- El mock iba por secuencia, frente a dos GET y un refetch tras `invalidateQueries`. El producto refresca bien (`setQueryData` + invalidación).
- Las fábricas no seguían los tipos.
- El rótulo `required` añade «(obligatorio)».
- La ruta de destino estaba mal.

| # | Encargo | in/out | USD | Resultado |
|---|---|---|---|---|
| 1 | C3-1 · reescritura de `OrdenPagoPage.test.tsx` + 10 bloques sobre `NuevaOrdenPagoPage.test.tsx` | 12915/8060 | 0,012630 | 11/11 aplicados. **Incidente de formato:** el bloque 10 casaba en 2 sitios. Se aplicó el 11 antes que el 10, sin tocar el contenido, y el 10 quedó único |
| 2 | C3-2 · Vitest de lista y políticas (ficheros nuevos) | 10081/8195 | 0,011515 | 2/2 aplicados |
| — | C3-3 · Vitest de la ficha de política | — | — | No llegó a DeepSeek: un clasificador de seguridad detuvo la retransmisión. El reintento lo denegó el modo automático. **No enviado** |
| 3 | C3-4 · E2E (helper + principal + multicausado) | — | 0 (sin respuesta) | Llegó a la API: `Streaming API Error: terminated`. Se cuenta como llamada. El reintento lo cortó un clasificador antes de enviar (no llegó). **E2E no escrita** |
| 4 | C3-5 · P1 producto + T1–T7 | 6211/1382 | 0,003904 | 7/7 aplicados. **PRODUCT_DEFECT** en la lista: sin estado de carga, error ni vacío para los ejercicios (página en blanco sin ejercicio aprobado). Vitest 38/40 |
| 5 | C3-6 · `exact` inválido en `getByRole` (error de Claude en los encargos), fila con dos «10.00», fábrica | 2201/1348 | 0,002130 | 5/5 aplicados. **Vitest 40/40**, tsc 0, eslint 0, build PASS |

**Cierre:** 5/5 llamadas (C3-4 se cuenta aunque no devolvió nada), `OWNER_EXCEPTION_USED=0`. Coste del ciclo: 0,030179 USD. TRE-03 acumulado: 0,264770 USD. `PRODUCT_STATUS=BLOCKED`.

**Mutaciones (PostgreSQL, base propia `ktest_mut_t03c3`, ya borrada; TRE-03 + BUD-09, 55 pruebas):**
- Muertas: M1 (borrador consume), M2a (sobreorden en borrador), M2b (sobreorden en emisión), M3 (anulación no restaura), M5 (autoridad), M6 (documento), M7 (SoD) y M8 (suma multicausado).
- **M4 SOBREVIVE:** quitar el filtro de empresa de `_orden_por_id` no cambia el 404 entre empresas. La serialización vuelve a resolver ejercicio y política por empresa. Es una segunda capa, pero no hay prueba de escritura cruzada que lo demuestre.
- Tras restaurar: 55/55.

**Defectos de Claude (encargos):** pidió `exact: true` en `getByRole` de Testing Library (opción de Playwright).

**Pendiente exacto:**
- `PoliticaOrdenPagoPage.test.tsx` sin escribir (encargo bloqueado).
- **PRODUCT_DEFECT QC-02:** la guarda FR-001-271 no resuelve la ruta del CSV en `OrdenesPagoPage.tsx:138`, construida con `split("?")`. Falta un helper de ruta explícito en `api.ts`.
- E2E principal y multicausado, axe 1280/390/320 y humo UAT.
- Prueba de escritura cruzada entre empresas (M4).
- Tarjeta de la dueña.

## TRE-03-COMPLETION-04 (2026-11-18) · tope 6, `deepseek-v4-pro`, encargos troceados (≤29k)

`origin/develop` = 9a18d5a al entrar (P2 sin avance). Ningún envío bloqueado en este ciclo.

| # | Encargo | in/out | USD | Resultado |
|---|---|---|---|---|
| 1 | C4-1 · CSV por `URLSearchParams` (QC-02), ejemplo `USD, VES…`, Vitest del CSV con filtros, prueba backend sin escritura entre empresas | 3740/3443 | 0,004512 | 4/6 aplicados. **AUDIT_REJECT** de los 2 bloques del backend: buscaban la obligación por `causado_id` (la clave real es `id`; el encargo no lo decía, defecto de Claude). QC-02 PASS, Vitest 41 |
| 2 | C4-2 · Vitest de la ficha de política (página compacta, 28,5k) | 8820/6737 | 0,009698 | 1/1 aplicado. 9/13: TEST_DEFECT `mockImplementationOnce`, texto dentro de una frase, GET sin `method`, interfaz sin usar |
| 3 | C4-3 · helper E2E `e2e/helpers/ordenes-pago.ts` | 7363/7520 | 0,009745 | 1/1 aplicado. La sonda contra el backend real destapó 3 defectos de los encargos de Claude: política de causado sin documento con disparador DOCUMENTARY, forma de las opciones del causado y evidencia |
| 4 | C4-4 · correcciones (helper H1–H3, ficha P1–P4, backend reemitido con `id`) | 3713/2258 | 0,003580 | 8/10 aplicados. **AUDIT_REJECT** del bloque P1, cuyo SEARCH no casaba (el tramo enviado cortaba la interfaz). **Incidente de formato:** P4 llegó en 2 bloques con el mismo SEARCH para dos apariciones idénticas; se aplicó uno con sustitución de ambas (`--todas`) y se omitió el duplicado. La sonda del helper pasa (borrador 0,00; emitida 40,00/60,00). Backend t03_11 + t03_11b 2/2 |
| 5 | C4-5 · suites E2E principal y multicausado (21k) | 7013/7114 | 0,009240 | 2/2 aplicados. Defectos: rutas de PUT, `selectOption` con RegExp, política vacía, duplicada por ancho, borrador de 0,00, `textContent` sin `await` |
| 6 | C4-6 · correcciones de las suites + V1 | 8948/3729 | 0,007137 | 20/21 aplicados. **AUDIT_REJECT** del bloque 20: quitaba el import `CausadoListo`, que sigue en uso. tsc 0, eslint 0, Vitest 540/540 |

**Cierre:** 6/6 llamadas. 0 envíos bloqueados. Reintentos: 2 (C4-4 y C4-6 corrigen subproblemas anteriores). `OWNER_EXCEPTION_USED=0`. Coste del ciclo: 0,043912 USD. TRE-03 acumulado: 0,308682 USD. `PRODUCT_STATUS=BLOCKED`.

**Mutaciones:** M4 (filtro de empresa en `_orden_por_id`) queda **muerto** con `test_t03_11b`. La anulación desde otra empresa alcanza la orden (409 en lugar de 404), así que ese filtro es la defensa efectiva. 9/9 efectivas, sin redefinir M4 ni quitar defensa en profundidad.

**E2E (`qa/e2e-run.py --con-analizador`, puertos 18000/15173/18010), corrida r20261118t002116:** 0/2. Ambas suites se paran en su primera aserción de UI, las dos por TEST_DEFECT:
- **Principal (l. 19):** el estado vacío de políticas pinta el título «Aún no hay políticas de orden de pago» y la descripción por separado. La prueba busca la frase unida, citada así en el encargo de Claude.
- **Multicausado (l. 54-55):** `getByLabel(/^Política/)` casa a la vez con la región «Política aplicable» y con el select. Debe ser `getByLabel("Política", { exact: true })`.

Lo que sigue a esos puntos (emisión, consumo, multicausado, varias órdenes, sobreorden, axe y SoD) **no llegó a ejecutarse**.

**Pendiente exacto:**
- esas 2 líneas;
- volver a correr las dos suites (y corregir lo que aparezca detrás);
- PG dirigida y PG completa sobre el árbol final;
- publicación y build-dev.

## TRE-03-COMPLETION-05 (2026-11-18) · tope 3 + excepción de la dueña (1 + 1 reserva, 1 más para OpenAPI y 1 más para integrar P2), `deepseek-v4-pro`

`origin/develop` = 9a18d5a al entrar; en el `git fetch` final, `a51816b` (P2 avanzó, ver «Integración con P2»). Ningún envío bloqueado.

| # | Encargo | in/out | USD | Clasificación del fallo | Resultado |
|---|---|---|---|---|---|
| 1 | C5-1 · estado vacío en dos aserciones; `getByLabel("Política", { exact: true })` en ambas suites | 1084/702 | 0,000972 | TEST_DEFECT ×2 (conocidos) | 3/3 PASS, aplicados |
| 2 | C5-2 · `setEditando(false)` antes de navegar tras el alta de política + Vitest de regresión; cargos por `cargoOrdenarId` | 1359/984 | 0,001337 | **PRODUCT_DEFECT** (la ficha recién creada seguía en el formulario: React Router reutiliza el componente entre `/nueva` y `/:politicaId`; sin «Activar») + TEST_DEFECT (opción «código · nombre») | 6/6 PASS. RED verificado: la prueba nueva falla sin la corrección (1/13) y pasa con ella (13/13) |
| 3 | C5-3 · `exact: true` en el ejemplo de numeración; `.first()` en el enlace duplicado (miga y menú); código emitido por el patrón por defecto del ente; esperar el `h1` antes de axe | 928/592 | 0,000919 | TEST_DEFECT ×2 observados + 2 anticipados por revisión | 5/5 PASS |
| 4 | C5-4 · sobreorden: un causado ordenado al 100 % sale de las opciones (el producto lo excluye, `pendiente <= 0`) | 585/202 | 0,000430 | TEST_DEFECT | 1/1 PASS. Excepción de la dueña |
| 5 | C5-5 · `tabIndex={0}`, `role="region"` y `aria-label` en 5 contenedores con desplazamiento (ficha ×3, nueva, lista) | 1315/1104 | 0,001422 | **PRODUCT_DEFECT** de accesibilidad: axe `scrollable-region-focusable` (serio) en la ficha | 5/5 PASS. Reserva de la excepción |
| 6 | C5-6 · renombrar 4 esquemas Pydantic repetidos con BUD-09 (`PoliticaOrdenPago{DocumentoIn,Create,Update}`, `ConfiguracionOrdenPagoIn`) | 1350/1443 | 0,001843 | **PRODUCT_DEFECT** de contrato: los nombres repetidos hacían que FastAPI renombrara también los esquemas publicados de BUD-09 (3 operaciones). Los ciclos anteriores lo habían dado por bueno | 6/6 PASS. Excepción de la dueña |

| 7 | C5-7 · integración con P2: migración reencadenada como `0125` tras `0124_gov_commission_policy`; fijaciones sumadas (auditoría 608, permisos 183, MFA estándar 83; cabeza `0125` en 3 pruebas) | 1041/544 | 0,000926 | INTEGRATION (P2 publicó `0124_gov_commission_policy` durante el ciclo) | 7/7 PASS. Excepción de la dueña |

**Cierre:** 7 llamadas (3 del tope + 4 por excepción de la dueña). 0 reintentos, 0 AUDIT_REJECT, 0 envíos bloqueados. Coste del ciclo: 0,007849 USD. TRE-03 acumulado: 0,316531 USD.

**Integración con P2.** El `git fetch` final encontró GOV-PROC-COMMISSION-POLICY (`dd1021c` + `a51816b`) publicado en `origin/develop`.
- Se confirmó TRE-03 en local (`3d09a6f`), se fusionó `origin/develop` de forma ordinaria (`f0e2b0b`) y se resolvió así:
  - Claude: `git checkout --ours` en las 6 fijaciones en conflicto y `git mv` de la migración, sin escribir contenido.
  - DeepSeek: el contenido (C5-7).
- Respaldo previo: `tre03/wip-v6/`.
- **Incidente de entorno:** la PG completa del árbol anterior a la fusión se perdió en un reinicio del equipo (el scratchpad es tmpfs); su repetición se detuvo al detectar el avance de P2.

**Evidencia:**
- **E2E** (r20261118t024450, árbol final): 2/2. El recorrido completo cubre política, numeración, borrador sin consumo, controles, documentos, emisión con consumo, historia, frontera TRE-04, anulación con restauración, lista y CSV; también multicausado, dos órdenes sobre el mismo causado, sobreorden (409 `GOV_PAYMENT_ORDER_OVER_ORDER` y «Saldo insuficiente»), axe y responsive en 1280/390/320 con el diálogo dentro del viewport en 320, y SoD CTL-01 real (409 `GOV_SOD_CONFLICT`, «Bloqueado»).
- **Pruebas:** Vitest 2420/2420. PG dirigida amplia 681/681. Trío + guardas OpenAPI 115/115 tras el renombrado.
- **OpenAPI:** 12 rutas TRE-03 y 8 esquemas nuevos. Los únicos esquemas cambiados son los SoD por `ProcesoSod += "TRE-03"`. BUD-09 queda intacto.
- **Tarjeta de la dueña:** contrastada con la UI. Montos con punto; competencia como campo deshabilitado; estado vacío en dos textos.

**Pendiente fuera de este ciclo:** `uat-humo-gobierno.spec.ts` (`PANTALLAS`) no incluye las 2 pantallas de TRE-03. Es un gate del estado ACCESSIBLE (OD-QA-UAT-01), no de READY.
