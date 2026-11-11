# KONTROL — Política de orquestación de IA: Claude + DeepSeek + Spec Kit

| Campo | Valor |
|---|---|
| Estado | **Adoptada** por la dueña el 2026-10-01 · transversal y permanente hasta indicación en contrario |
| Estado del montaje | **`VERIFIED_END_TO_END`** — certificado el 2026-10-01 con delegación real a DeepSeek: ORCH 10/10 (§9) |
| Reglas operativas | `.claude/CLAUDE.md` (este documento las explica; no las duplica) |
| Agentes | `.claude/agents/deepseek-executor.md` · `.claude/agents/spec-kit-coordinator.md` |
| Herramientas | `scripts/set_deepseek_key.py` (montaje) · `scripts/orchestration_readiness.py` (auditoría) · `scripts/orch_probe.py` (certificación ORCH-01..10) |
| Ciclo Spec Kit | `specs/001-fundacion/spec001-orquestacion-ia-delta.md` |
| Referencia | el montaje de otro proyecto de la dueña, **adaptado, no copiado** (§8) |

## 1. La idea, en una línea

**Claude conserva el juicio; DeepSeek hace el trabajo mecánico de implementación.** Spec Kit
sigue siendo la metodología: la orquestación es el modelo de ejecución de la fase
`implement`, no un atajo alrededor de los gates.

```
ANALYZE → PLAN → CLASSIFY → EXECUTE (DeepSeek propone) → AUDIT (Claude) → APPLY (Claude)
        → TEST (Claude) → RETRY controlado (máx. 2) → CONVERGE (Claude)
```

| | Autoridad |
|---|---|
| Claude | **decide** |
| DeepSeek | **propone** |
| Repositorio, contratos y Specs | **demuestran** |
| Pruebas | **certifican** |

Un código plausible no convierte a quien lo generó en fuente de verdad.

## 2. Precedencia

1. decisiones de la dueña · 2. Constitución · 3. Specs y ADR aprobados · 4. esta política ·
5. instrucciones de la tarea · 6. sugerencias de DeepSeek.

Encaja debajo de la jerarquía de la Constitución (normas oficiales → Constitución →
documentos maestros → Specs → ADR → contratos → código): la política gobierna **cómo se
ejecuta**, nunca **qué se decide**.

## 3. Roles

**Claude** — lee el encargo, reconcilia `HEAD` y árbol, resuelve la Spec dueña, lee la
Constitución, ejecuta Spec Kit de principio a fin, hace arqueología del repositorio, detecta
contradicciones y decisiones materiales, redacta los artefactos, diseña arquitectura e
invariantes, clasifica riesgos y tareas, prepara el contexto mínimo para delegar, audita
**todos** los parches, aplica solo los aprobados, ejecuta pruebas y mutaciones, interpreta
fallos, verifica esquema, migraciones, OpenAPI y seguridad, converge e informa.

**DeepSeek** — recibe una tarea pequeña y explícita, lee solo el contexto que se le da y
propone la implementación en bloques SEARCH/REPLACE. Sirve para código repetitivo, pruebas ya
diseñadas, tipos e interfaces ya decididos, mapeos, cableado de frontend sencillo y
funciones con contrato cerrado. **No decide, no edita, no investiga el repositorio, no
añade dependencias, no crea migraciones, no «mejora» el alcance y no certifica su trabajo.**

## 4. Clasificación de tareas

Se clasifica **tarea por tarea**, nunca una Spec entera. Cada tarea de `tasks` declara:

```
EXECUTOR: CLAUDE | DEEPSEEK      MODEL: deepseek-v4-flash | deepseek-v4-pro | n-a
SECURITY_SENSITIVE: YES | NO     EGRESS_SAFE: YES | NO     RETRY_MAX: 2
FILES · TEST · DONE_WHEN
```

**`DEEPSEEK_ELIGIBLE`** exige todo a la vez: contrato cerrado, `MATERIAL OQ = 0`, sin
incógnitas relevantes, fichero objetivo identificado, cambio local, invariantes definidos,
resultado verificable; y que no requiera decidir arquitectura, seguridad o negocio, migrar,
depurar ni interpretar requisitos ambiguos. Debe poder explicarse en pocas líneas y tocar
uno o pocos ficheros: «implementar el módulo» es demasiado grande y se divide.

**`CLAUDE_ONLY`**, aunque DeepSeek pudiera técnicamente generar el código:

| Familia | Incluye |
|---|---|
| Seguridad | autenticación, control de acceso, permisos, alcances de usuario, aislamiento de tenant, criptografía, secretos, firmas de licencia, MFA, sesiones, incidentes |
| Datos | migraciones, backfills, reparación de datos, operaciones destructivas, restricciones e índices materiales |
| Dinero y fiscal | fórmulas monetarias no fijadas, fórmulas fiscales, reglas tributarias, núcleo fiscal venezolano, redondeo, moneda, semántica contable |
| Arquitectura | idempotencia, concurrencia, refactors grandes, cambios de arquitectura, ADR nuevos, cambios transversales |
| Juicio | depuración, causa raíz, decisiones materiales abiertas, y las fases `specify`, `clarify`, `plan`, gate, `analyze`, `converge` |

Dos precisiones:

- **Depurar es de Claude; el arreglo puede no serlo.** Claude reproduce, mide y establece la
  causa. Si después el cambio queda totalmente definido, su implementación puede
  reclasificarse como delegable. Si el arreglo es inseparable del diagnóstico, lo hace Claude.
- **Dinero y fiscal**: DeepSeek solo escribe código mecánico cuando Claude ya fijó fórmula,
  escala, redondeo, contrato y vectores de prueba.

Las decisiones de la dueña no se delegan a nadie. Hoy están abiertas, entre otras:
`API-QUERY-SILENCIOSA`, `SEED-EMPRESA-CODIGO-NO-UNICO`, `MOVTYPE-GLOBAL-SIN-UNICIDAD`,
`FECHAS-ZONA-DE-PRESENTACION` y `UI-BUSQUEDA-MUERTA` en Auditoría y en Existencias.

## 5. Spec Kit y la orquestación

- El flujo no cambia: `specify → clarify → plan → CONSTITUTION GATE → checklist → tasks →
  analyze → trazabilidad → autorización expresa → implement → pruebas → converge`.
- Las skills de Claude Code usan guion (`/speckit-specify`); los encargos escriben punto
  (`/speckit.specify`). Es una diferencia de sintaxis, no de método.
- DeepSeek entra **solo** con requisitos y tareas cerrados, `analyze` limpio y autorización
  de implementación. Antes del gate, `DEEPSEEK CALLS = 0`.
- La autorización de `implement` no significa «DeepSeek puede hacerlo todo»: significa que
  Claude puede empezar a implementar y, dentro de eso, delegar las tareas `DEEPSEEK_ELIGIBLE`.
- En KONTROL un delta dirigido vive dentro de la Spec dueña
  (`specs/<spec>/specNNN-<slug>-delta.md` + `evidence/<slug>/`); no abre una Spec nueva.

## 6. Delegación, egress, auditoría y reintentos

**Delegación sin memoria.** Cada llamada lleva `TASK`, `GOAL`, `TARGET FILES`, `READ-ONLY
CONTEXT`, `CONTRACT`, `INVARIANTS`, `CONSTRAINTS`, `IMPLEMENTATION STYLE`, `OUTPUT FORMAT`,
`DONE WHEN`, `TESTS EXPECTED`, `MODEL`. Un reintento reenvía el contexto entero, el intento
anterior y el motivo exacto del rechazo. Contexto mínimo suficiente: nunca el repositorio
completo.

**Egress.** DeepSeek es un proveedor externo. Antes de cada llamada:

```
EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0
              REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0
```

Solo con todo en cero se delega. Nunca salen `.env*`, claves, tokens, contraseñas, URLs de
base de datos con credenciales, certificados privados, datos personales, de nómina,
bancarios o fiscales reales, volcados productivos ni logs con secretos. La clave de la API
vive únicamente en `~/.claude.json`; no se imprime, no se registra, no entra en el
repositorio y no se pega en un chat. Clave expuesta → alto y `SECRET_EXPOSURE`.

**DeepSeek no edita.** Devuelve bloques SEARCH/REPLACE; Claude los audita y, si pasan, los
aplica él. Lista de auditoría: tarea exacta, solo ficheros objetivo, sin imports ni
dependencias nuevas, sin esquema ni migración, sin secretos ni PII, sin tocar fronteras de
seguridad, sin deriva de contrato, sin respaldos ocultos, sin `any` injustificado, sin
excepciones amplias, sin compatibilidad silenciosa, sin `sleep`/reintentos/`skip`, sin `TODO`
por implementación, sin código muerto, sin formato ajeno. Resultado: `AUDIT_PASS` o
`AUDIT_REJECT` con motivo. **Un SEARCH que no coincide exactamente se rechaza**; Claude no
retoca el parche en silencio para atribuírselo luego al ejecutor. Claude Code entrega el
informe de un subagente sangrado dos espacios: ese marco, y solo ese, se quita antes de
comparar; no es un retoque del parche.

**Reintentos: dos como máximo.** Tras el segundo fallo se detiene la delegación automática
y Claude reclasifica: dividir, subir a `deepseek-v4-pro` o implementar él. El ejecutor hace
**una** llamada por encargo y no reintenta por su cuenta; el `MAX_RETRIES` del servidor MCP
es otra cosa (reintentos de red de una misma llamada) y no cuenta como reintento de delegación.

**Tope global por ciclo: 8 llamadas** (orden de la dueña, 2026-11-11, tras OBS-CTL05-ORCH-01).
Son dos controles distintos y ambos se cumplen:

- **Regla A:** como máximo 2 reintentos semánticos por subproblema real.
- **Regla B:** como máximo **8 llamadas a DeepSeek en total por ciclo**. El objetivo normal es de 2 a 4.

Una causa raíz nueva o una frontera técnica nueva justifican una subtarea, pero **no** reinician el contador
global.

Al llegar a 8 llamadas:
- se hace un alto semántico, se diagnostica y se informa;
- no se crean micro-subproblemas para obtener más llamadas;
- superar 8 exige una decisión explícita de la dueña.

Todo informe registra: `DEEPSEEK_CALL_1..N`, `TOTAL_CALLS`, `TOTAL_RETRIES`, `SUBPROBLEMS`,
`MAX_RETRIES_SINGLE_SUBPROBLEM` y `GLOBAL_CAP_REACHED`.

**Probar tras cada tarea.** Se ejecuta la prueba más pequeña que demuestra el cambio antes
de seguir. Claude diseña las pruebas —qué, por qué, fixture, esperado, mutante que mata— y
DeepSeek puede escribirlas; Claude verifica después que matan el defecto y busca verdes
falsos. Las mutaciones las diseña e interpreta Claude.

**Modelos**, con los nombres que el servidor declara (no los alias `flash`/`pro`):
`deepseek-v4-flash` para lo pequeño y mecánico, y es el valor por defecto;
`deepseek-v4-pro` solo para tareas que siguen siendo delegables pero tienen lógica local
más compleja o ficheros grandes, nunca para saltarse `CLAUDE_ONLY`. `deepseek-chat` y
`deepseek-reasoner` son alias obsoletos y no se usan. Sin `thinking`: razonar es de Claude.
Sin `session_id`: cada delegación empieza de cero. El montaje desactiva el cambio
silencioso de modelo (`FALLBACK_ENABLED=false`): qué modelo ejecuta lo decide Claude, y el
ejecutor informa el modelo realmente servido (`request.wire_model`). La API de DeepSeek
llama `deepseek-flash` al primero en sus respuestas; a la herramienta se le pide como
`deepseek-v4-flash`.

**Coste.** Por delegación se anota modelo, tokens de entrada y salida, coste y reintentos,
si la herramienta los da. El objetivo es coste y velocidad **sin** rebajar seguridad,
calidad, pruebas, trazabilidad ni gates.

## 7. Informes y Git

Por tarea: `[ANALYZE] [PLAN] [CLASSIFY] [EXECUTE] [AUDIT] [TEST] [STATUS]`. Por delta:
tareas totales, `CLAUDE_ONLY`, `DEEPSEEK_ELIGIBLE`, ejecutadas por DeepSeek, reintentos,
parches rechazados y aceptados, implementadas por Claude, pruebas, mutaciones, regresiones y
coste. Siempre se dice quién hizo qué.

Git lo controla Claude: **rama única `develop`** (norma vinculante 2026-11-01, `git-governance.md` §0): ninguna
otra rama local ni remota, sin PR entre ramas, sin commits de DeepSeek. Un ciclo se cierra, tras converger, con commit y push a
`origin/develop` y el árbol limpio: es la autorización permanente que la dueña dio el
2026-09-30 para los cierres, y satisface la regla de no subir sin autorización expresa.

## 8. Lo que KONTROL toma de la referencia y lo que cambia

| Pieza | Referencia | KONTROL |
|---|---|---|
| Quién aplica las ediciones | el subagente, literalmente | **Claude, tras auditar**: el subagente no tiene `Edit`, `Write` ni `Bash` |
| Reintentos | hasta quedar conforme | **máximo 2** |
| Ramas | `master` y `develop` | **solo `develop`** |
| Unidad de trabajo | lote de tareas | **una tarea** por delegación |
| Artefactos de Spec Kit | `specs/<NNN>-<slug>/` | deltas dentro de la Spec dueña |
| Permisos del proyecto | lista `allow` amplia y herramienta de DeepSeek preaprobada | **sin `allow` añadido**: solo `deny` de `.env` y de `psql` productivo; preaprobar la herramienta es decisión de la dueña |
| MCP | `@arikusi/deepseek-mcp-server` por `npx` absoluto y `PATH` explícito, **sin versión** | el mismo, **fijado a `2.3.0`** y sin cambio silencioso de modelo, creado por `scripts/set_deepseek_key.py` |

## 9. Estado del montaje, certificado el 2026-10-01

Se audita con `python scripts/orchestration_readiness.py --handshake` (no lee ni muestra la
clave) y se certifica con `python scripts/orch_probe.py`. Evidencia en
`specs/001-fundacion/evidence/orquestacion-ia/`; ciclo completo en
`specs/001-fundacion/spec001-orquestacion-ia-delta.md`.

| Comprobación | Resultado |
|---|---|
| Configuración de Claude (`.claude/CLAUDE.md`) | **PASS** |
| Spec Kit: integración `claude`, diez skills `speckit-*`, Constitución | **PASS** — una sesión nueva las carga |
| Agentes `deepseek-executor` y `spec-kit-coordinator` | **PASS** — una sesión nueva los carga; el ejecutor solo tiene `Read`, `Glob`, `Grep` y la herramienta de DeepSeek |
| Tope de reintentos | **PASS** — `RETRY_MAX: 2` en `CLAUDE.md`, en los dos agentes y aquí |
| `settings.json` | **PASS** — los seis `deny` siguen; la herramienta de DeepSeek no está preaprobada |
| `.mcp.json` del repositorio | **PASS** — válido y sin servidores: el de DeepSeek lleva clave y es local |
| Claves en el repositorio | **PASS** — ninguna en los ficheros versionados, en la evidencia ni en las trazas |
| Clave de DeepSeek | **PASS** — reutilizada de la entrada local que otro proyecto de la dueña ya tenía; DeepSeek la aceptó; nunca se mostró |
| Entrada local del MCP para KONTROL | **PASS** — `~/.claude.json`, ámbito local del proyecto, modo `600` |
| Paquete y versión | **PASS** — `@arikusi/deepseek-mcp-server@2.3.0`, fijada |
| Orden | **PASS** — `npx` absoluto de nvm (`node v24.21.0`; el paquete exige `>=22`) y `PATH` explícito |
| MCP conectado | **PASS** — `claude mcp list`: `deepseek … ✔ Connected` |
| Herramientas reales | **PASS** — `deepseek_chat`, `deepseek_fim`, `deepseek_sessions`; el ejecutor solo usa `mcp__deepseek__deepseek_chat` |
| Modelos reales | **PASS** — la herramienta acepta `deepseek-v4-flash` (por defecto) y `deepseek-v4-pro`; la API lista `deepseek-flash` y `deepseek-v4-pro` |
| Delegación real | **PASS** — `DEEPSEEK CALLS = 3`, las tres sin `session_id` |
| ORCH-01..ORCH-10 | **PASS — 10/10** |

`ORCHESTRATION_STATUS = VERIFIED_END_TO_END`

### Cómo se cableó la clave

Claude localizó la clave sin mostrarla. Su primer intento de leerla con un guion propio lo
denegó el clasificador de permisos de Claude Code; la dueña ordenó entonces ejecutar el
guion del proyecto, `scripts/set_deepseek_key.py --reuse-from <otro proyecto> --check`, que
copió la clave en memoria de una entrada local a la otra, la validó contra DeepSeek, fijó
la versión y respaldó `~/.claude.json`. La clave no apareció en ninguna salida.

### Prueba de extremo a extremo

`scripts/orch_probe.py` abre una **sesión nueva** de Claude Code, trabaja sobre
`/tmp/kontrol-orchestration-probe/` —fuera del producto— y lo borra al terminar. Decide
sobre la **traza de eventos** de la sesión, no sobre lo que el modelo afirme.

| ID | Qué demuestra | Resultado |
|---|---|---|
| ORCH-01 | Claude invoca `deepseek-executor` en una sesión nueva | **PASS** |
| ORCH-02 | el ejecutor llama al MCP y DeepSeek responde; el orquestador no lo llama directamente | **PASS** — 1 llamada, 0 directas |
| ORCH-03 | la carga no lleva secretos, `.env` ni `session_id` | **PASS** — 2 279 caracteres: encargo y contenido de la arena |
| ORCH-04 | DeepSeek devuelve SEARCH/REPLACE y el ejecutor lo entrega **idéntico** | **PASS** |
| ORCH-05 | Claude audita antes de aplicar | **PASS** — `AUDIT_PASS` |
| ORCH-06 | Claude rechaza un parche no conforme (`alpha=999`) sin aplicarlo | **PASS** — `AUDIT_REJECT · UNAUTHORIZED_EXTRA_CHANGE` |
| ORCH-07 | Claude aplica solo el parche aprobado | **PASS** |
| ORCH-08 | `alpha == 1`, `beta == 20`, `gamma == 3` | **PASS** |
| ORCH-09 | servidor, herramienta, modelo y uso, tal como los devuelve la herramienta | **PASS** — pedido `deepseek-v4-flash`; servido `deepseek-v4-flash` (`model: deepseek-flash`), sin fallback, 654/196 tokens, $0.000076 |
| ORCH-10 | tope de dos reintentos en los cuatro documentos; el ejecutor no reintenta | **PASS** — 1 llamada por encargo |

Hubo tres corridas con llamada real: 10/10, **6/10** y 10/10. En la segunda DeepSeek
respondió bien; falló la sonda, que leía el parche del texto retransmitido y no contaba con
el sangrado de dos espacios del informe del subagente. Corregida, las tres trazas dan 10/10.

**Repetir la certificación** tras subir la versión del MCP, cambiar un agente o mover de
máquina: `python scripts/orch_probe.py`. No exige reiniciar nada. La sesión interactiva
que ya estuviera abierta sí necesita reiniciarse para ver el MCP.

## 10. Observaciones registradas

- **`MCP-DEEPSEEK-SIN-VERSION-FIJADA`** — **CERRADA**. El montaje crea la entrada con
  `@arikusi/deepseek-mcp-server@2.3.0`, lleva a esa versión una entrada antigua sin tocar
  su clave, la auditoría falla si la entrada local no está fijada, y ORCH-01..10 pasó sobre
  esa versión. Subir de versión es deliberado: cambiar `PACKAGE_VERSION`, volver a montar y
  repetir la sonda.
- **`NPX-RESUELTO-ROMPE-EL-MCP`** — corregida. El montaje del ciclo anterior resolvía el
  enlace `bin/npx` hasta `lib/node_modules/npm/bin/`, y desde ahí npx no encuentra `node`:
  la entrada habría quedado «not connected». Lo destapó el arranque real del servidor; hay
  prueba y mutante que lo vigilan.
- **`MARCO-DE-DOS-ESPACIOS`** — el informe de un subagente llega sangrado dos espacios.
  Quien audita quita ese marco antes de comparar un SEARCH; está en `CLAUDE.md` y la sonda
  lo prueba.
- **`OTROS-PROYECTOS-SIN-VERSION-FIJADA`** — la entrada `deepseek` del otro proyecto de la
  dueña sigue sin versión. No se tocó: no es de KONTROL. Se fija ejecutando allí el mismo
  guion.
- **`SPECKIT-SKILLS-VS-DELTAS`** — las skills trabajan sobre `specs/<feature>/spec.md`,
  `plan.md` y `tasks.md`, y `speckit-specify` abre una carpeta de Spec nueva; los deltas de
  KONTROL son un único documento dentro de la Spec dueña. Las fases se siguen ejecutando; la
  forma del artefacto la fija `CLAUDE.md`.
- **`CLASIFICADOR-VS-AUTORIZACION-DE-LA-DUENA`** — el clasificador de permisos de Claude
  Code denegó a Claude leer la clave con un guion propio aunque el encargo lo autorizaba.
  El camino que funcionó: que la dueña ordene ejecutar el guion del proyecto, que nunca
  muestra el valor.
