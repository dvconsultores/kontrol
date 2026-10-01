# KONTROL — Política de orquestación de IA: Claude + DeepSeek + Spec Kit

| Campo | Valor |
|---|---|
| Estado | **Adoptada** por la dueña el 2026-10-01 · transversal y permanente hasta indicación en contrario |
| Estado del montaje | **`CONFIGURATION_INCOMPLETE`** — falta la entrada local del MCP y la clave (§9) |
| Reglas operativas | `.claude/CLAUDE.md` (este documento las explica; no las duplica) |
| Agentes | `.claude/agents/deepseek-executor.md` · `.claude/agents/spec-kit-coordinator.md` |
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
EXECUTOR: CLAUDE | DEEPSEEK      MODEL: flash | pro | n-a
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
retoca el parche en silencio para atribuírselo luego al ejecutor.

**Reintentos: dos como máximo.** Tras el segundo fallo se detiene la delegación automática
y Claude reclasifica: dividir, subir a `pro` o implementar él.

**Probar tras cada tarea.** Se ejecuta la prueba más pequeña que demuestra el cambio antes
de seguir. Claude diseña las pruebas —qué, por qué, fixture, esperado, mutante que mata— y
DeepSeek puede escribirlas; Claude verifica después que matan el defecto y busca verdes
falsos. Las mutaciones las diseña e interpreta Claude.

**Modelos.** El rápido para lo pequeño y mecánico; el fuerte solo para tareas que siguen
siendo delegables pero tienen lógica local más compleja o ficheros grandes, nunca para
saltarse `CLAUDE_ONLY`. Sin razonamiento extendido por defecto: razonar es de Claude. Los
identificadores exactos se toman del esquema de la herramienta, no de memoria (§9).

**Coste.** Por delegación se anota modelo, tokens de entrada y salida, coste y reintentos,
si la herramienta los da. El objetivo es coste y velocidad **sin** rebajar seguridad,
calidad, pruebas, trazabilidad ni gates.

## 7. Informes y Git

Por tarea: `[ANALYZE] [PLAN] [CLASSIFY] [EXECUTE] [AUDIT] [TEST] [STATUS]`. Por delta:
tareas totales, `CLAUDE_ONLY`, `DEEPSEEK_ELIGIBLE`, ejecutadas por DeepSeek, reintentos,
parches rechazados y aceptados, implementadas por Claude, pruebas, mutaciones, regresiones y
coste. Siempre se dice quién hizo qué.

Git lo controla Claude: **solo `develop`**, sin ramas nuevas sin autorización expresa, sin
commits de DeepSeek. Un ciclo se cierra, tras converger, con commit y push a
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
| MCP | `@arikusi/deepseek-mcp-server` por `npx` absoluto y `PATH` explícito | el mismo, creado por `scripts/set_deepseek_key.py` |

## 9. Estado del montaje, medido el 2026-10-01

| Comprobación | Resultado |
|---|---|
| `.claude/CLAUDE.md` | **creado** (no existía; `.claude/` estaba vacío) |
| `.claude/agents/deepseek-executor.md` | **creado**, solo propone |
| `.claude/agents/spec-kit-coordinator.md` | **creado**, clasifica y no decide |
| `.claude/settings.json` | **creado**, solo `deny` |
| Integración Spec Kit `claude` | **instalada** con `specify integration install claude` (CLI 1.0.10.dev0): estado `OK`, diez skills `speckit-*`, plantillas y guiones; Constitución y `README` intactos (misma huella antes y después); ningún guion crea ramas |
| Integración `copilot` | no estaba instalada; nada que preservar |
| `.mcp.json` del repositorio | era un fichero vacío (JSON inválido); queda `{"mcpServers": {}}`. El servidor de DeepSeek **no** va aquí: lleva clave y es local |
| `scripts/set_deepseek_key.py` | **creado**: `--status`, alta de la entrada y clave por aviso oculto, `--check` |
| MCP `deepseek` configurado para KONTROL | **NO** — `~/.claude.json` no registra este proyecto ni la entrada |
| MCP conectado en la sesión | **NO** — la sesión no expone ninguna herramienta `mcp__deepseek__*` |
| Nombres exactos de herramientas y modelos | **sin verificar**: en la referencia, `mcp__deepseek__deepseek_chat`; se comprobarán contra el esquema real al conectar |
| Clave de API para KONTROL | **NO configurada** (no se buscó ni se copió la de otro proyecto) |
| Node para el MCP | `npx` por ruta absoluta de nvm (`v24.21.0`), para no depender del `PATH` de VS Code |
| Paquete del MCP | `@arikusi/deepseek-mcp-server`, publicado `2.3.0`; la referencia lo lanza **sin versión fijada** (observación, §10) |
| Regla solo-`develop`, tope de reintentos, exclusiones, egress | escritas en `CLAUDE.md` y en los agentes |
| Base de datos productiva | no expuesta: no hay credenciales productivas en el repositorio; `deny` de lectura de `.env` y de `psql` productivo |

`ORCHESTRATION_STATUS = CONFIGURATION_INCOMPLETE`

### Lo que falta, exactamente, y quién puede hacerlo

1. **La dueña**, en su terminal, fuera de cualquier chat:
   `python scripts/set_deepseek_key.py --check` — crea la entrada local del MCP para este
   proyecto y pide la clave sin mostrarla.
2. **Reiniciar Claude Code** y comprobar con `/mcp` que `deepseek` aparece conectado.
3. **Claude**, en la sesión siguiente: la prueba de extremo a extremo de abajo. Hasta
   entonces DeepSeek **no se da por operativo** y ningún ciclo de producto lo usa.

### Prueba de extremo a extremo, pendiente

Sobre un fichero de arena fuera del producto, que se elimina al terminar; sin tocar
autenticación, tenant, dinero, fiscal, migraciones, Specs ni el Master 56.

| ID | Debe demostrar | Estado |
|---|---|---|
| ORCH-01 | Claude invoca `deepseek-executor` | pendiente |
| ORCH-02 | el ejecutor llama al MCP y se verifican nombres de herramienta y modelo | pendiente |
| ORCH-03 | el control de egress se declara y no hay secretos en la carga | pendiente |
| ORCH-04 | DeepSeek devuelve bloques SEARCH/REPLACE | pendiente |
| ORCH-05 | Claude audita | pendiente |
| ORCH-06 | Claude rechaza un parche (se provoca uno fuera de alcance) | pendiente |
| ORCH-07 | Claude aplica un parche aprobado | pendiente |
| ORCH-08 | la prueba dirigida se ejecuta | pendiente |
| ORCH-09 | el resultado se registra con tokens y coste | pendiente |
| ORCH-10 | el tope de dos reintentos detiene la delegación | pendiente |

## 10. Observaciones registradas

- **`MCP-DEEPSEEK-SIN-VERSION-FIJADA`** — el servidor se lanza con `npx -y` sin versión:
  cada arranque puede traer una versión nueva de un paquete que recibe la clave y el código
  enviado. Fijar la versión (`@2.3.0` hoy) es una decisión de la dueña.
- **`SPECKIT-SKILLS-VS-DELTAS`** — las skills trabajan sobre `specs/<feature>/spec.md`,
  `plan.md` y `tasks.md`; los deltas de KONTROL son un único documento dentro de la Spec
  dueña. Las fases se siguen ejecutando; la forma del artefacto la fija `CLAUDE.md`.
- **Checkpoint del encargo** — el encargo daba `8b845a1` y `EMPRESAS-SIN-SOBRE` sin iniciar.
  El repositorio dice `e813e6f`: esa deuda está **CLOSED / CONVERGED** y subida desde el
  2026-09-30, ejecutada entera por Claude antes de esta política. La evidencia del
  repositorio manda; no se rehace.
