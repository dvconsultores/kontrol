# SPEC 001 · DELTA DE HERRAMIENTAS ORQUESTACION-IA — CLAUDE PIENSA, DEEPSEEK PROPONE, Y HAY UNA PRUEBA QUE LO DEMUESTRA

> Delta de herramientas y gobierno dentro de la Spec 001 (Fundación, Master 001: estructura
> del repositorio y entorno de desarrollo); Spec 012 (QA integral, Master 054) como apoyo.
> Certifica el montaje Claude + DeepSeek + Spec Kit que la política
> `docs/governance/ai-orchestration-policy.md` adoptó. **No toca producto, esquema,
> migraciones ni el Master 56.**

## 0. Checkpoint

| Comprobación | Valor |
|---|---|
| `EXPECTED_HEAD` / `ACTUAL_HEAD` | `c8adc0d` / **`c8adc0d`** — coinciden |
| `REMOTE_HEAD` | `c8adc0d` — `develop` al día con `origin/develop` |
| `ACTUAL_BRANCH` | `develop`; no se creó ninguna rama |
| `WORKTREE_STATE` | limpio al empezar |

## 1. Veredicto, por delante

**No convergido. `ORCHESTRATION_STATUS = CONFIGURATION_INCOMPLETE`, a un paso local de
`VERIFIED_END_TO_END`.**

La hipótesis de la dueña era correcta: DeepSeek ya estaba configurado en la máquina. La
clave está en `~/.claude.json`, en la entrada local de otro proyecto suyo. Claude la
localizó sin mostrarla, pero cuando fue a leerla para cablearla a KONTROL **el clasificador
de permisos de Claude Code se lo denegó** («exploración de credenciales»). Una denegación
de ese tipo no se rodea por otra vía, así que la clave no se leyó, no se copió y no hubo
ninguna llamada real a DeepSeek: `DEEPSEEK CALLS = 0`.

Todo lo que no depende de la clave quedó hecho y medido:

- nombres reales de herramientas y modelos, leídos del servidor en marcha;
- versión del MCP fijada (`2.3.0`) y un fallo del montaje corregido que habría dejado el
  MCP desconectado;
- una auditoría del montaje y una sonda ORCH-01..10 ejecutables, con 73 pruebas y 34
  mutantes muertos de 34;
- la sonda corrida hoy en una sesión nueva de Claude Code: **4/10**, y los seis que fallan
  dependen del mismo paso.

## 2. Dueñas

| Pieza | Dueña | Por qué |
|---|---|---|
| Herramientas de desarrollo y gobierno del repositorio | **Spec 001** (`001-fundacion`, Master 001) | es la Spec de fundación: estructura del repositorio y entorno; `docs/roadmap/spec-equivalence-map.md` |
| Método de verificación y evidencia | Spec 012 (`012-auditoria-integral-e2e`, Master 054), apoyo | proceso de QA, no funcional |
| Política | `docs/governance/ai-orchestration-policy.md` | adoptada por la dueña el 2026-10-01 |

No se abre una Spec nueva. Los requisitos conservan los identificadores que dio la dueña
(`FR-ORCH-NNN`): son de herramientas y no entran en la numeración funcional `FR-001-NNN`.

## 3. Lo que había, medido

Sin mostrar ningún valor (`evidence/orquestacion-ia/descubrimiento-local.txt`):

| Fuente, por prioridad | Hallazgo |
|---|---|
| 1. Entorno | `DEEPSEEK_API_KEY`: `PRESENT=NO` |
| 2. `~/.claude.json`, ámbito de usuario | sin servidores MCP |
| 2. `~/.claude.json`, ámbito local de otro proyecto de la dueña | **servidor `deepseek`**: `npx` absoluto de nvm, `-y @arikusi/deepseek-mcp-server` (sin versión), `DEEPSEEK_API_KEY`: `PRESENT=YES NONEMPTY=YES` |
| 2. `~/.claude.json`, KONTROL | el proyecto no tiene entrada |
| 3. `claude mcp list` desde KONTROL | solo los conectores de claude.ai; ningún `deepseek` |
| `.mcp.json` del repositorio | `{"mcpServers": {}}` — correcto: el servidor con clave no va en un fichero versionado |
| Caché de `npx` | `@arikusi/deepseek-mcp-server` **2.3.0**, instalada el 2026-09-21; es también la última publicada |
| Node | `v24.21.0` por nvm (el paquete exige `>=22`); el binario de Claude Code es el de la extensión, `2.1.285` |

No se buscó en ningún otro sitio: la clave apareció en la segunda fuente de la lista.

## 4. `/speckit.specify`

| ID | Requisito | Cómo se demuestra |
|---|---|---|
| FR-ORCH-001 | Claude es la autoridad de razonamiento y auditoría | `CLAUDE.md`; `readiness` «Claude configuration» |
| FR-ORCH-002 | DeepSeek es un ejecutor acotado | `deepseek-executor.md`; `readiness` «Executor patch-only» |
| FR-ORCH-003 | DeepSeek se conecta por un MCP local | `readiness` «DeepSeek MCP local entry»; ORCH-02 |
| FR-ORCH-004 | El secreto nunca entra en el repositorio | `readiness` «No key in repository», «Repo .mcp.json»; ORCH-R05, R06 |
| FR-ORCH-005 | El secreto nunca aparece en salidas ni informes | KEY-03, ORCH-R09; mutantes M01, M16 |
| FR-ORCH-006 | Los nombres de herramienta se descubren, no se suponen | `readiness --handshake`; `mcp-declarado.json` |
| FR-ORCH-007 | Los nombres de modelo se descubren, no se suponen | ídem; «Model names documented» |
| FR-ORCH-008 | Existe al menos una delegación real | ORCH-02 (`DEEPSEEK CALLS ≥ 1`) |
| FR-ORCH-009 | Claude audita antes de aplicar | ORCH-05; PROBE-02, PROBE-03 |
| FR-ORCH-010 | El ejecutor no edita | «Executor patch-only»; ORCH-R01..R03; mutantes M11..M13 |
| FR-ORCH-011 | Reintentos: dos como máximo | ORCH-10; ORCH-R04; mutantes M14, M15 |
| FR-ORCH-012 | Las delegaciones no tienen memoria | ORCH-03 (sin `session_id`); PROBE-08; mutante M30 |
| FR-ORCH-013 | Control de egress antes de cada llamada | ORCH-03; PROBE-08, PROBE-11; mutante M31 |
| FR-ORCH-014 | Existe la prueba ORCH-01..ORCH-10 | `scripts/orch_probe.py` |
| FR-ORCH-015 | El producto no cambia | `git diff --stat`: 0 ficheros bajo `resources/` |
| FR-ORCH-016 | La orquestación sobrevive a un arranque nuevo | la sonda abre siempre una sesión nueva; `sesion-nueva.txt` |

## 5. `/speckit.clarify`

| # | Pregunta | Respuesta, medida |
|---|---|---|
| 1 | Dueña | Spec 001; Spec 012 como apoyo (§2) |
| 2 | Ámbito del MCP | **local**: `projects[<ruta>].mcpServers` de `~/.claude.json`. No el de usuario (no se impone a otros proyectos) ni el del repositorio (lleva clave) |
| 3 | Fuente de la clave | la entrada local que otro proyecto de la dueña ya tiene en el mismo fichero |
| 4 | Orden del MCP | `npx` por ruta absoluta, **sin resolver el enlace** (§9, hallazgo 1) |
| 5 | Paquete | `@arikusi/deepseek-mcp-server` |
| 6 | Versión | **`2.3.0`**: la que la máquina usaba, la última publicada y la que arranca en la prueba |
| 7 | Ruta de node | `~/.nvm/versions/node/v24.21.0/bin/node` |
| 8 | Ruta de npx | `~/.nvm/versions/node/v24.21.0/bin/npx` |
| 9 | `PATH` | explícito en la entrada, empezando por el directorio de node: Claude Code lanzado desde VS Code no hereda el de nvm |
| 10 | Herramientas reales | `deepseek_chat`, `deepseek_fim`, `deepseek_sessions`. En Claude Code: `mcp__deepseek__deepseek_chat` |
| 11 | Modelos reales | `deepseek-v4-flash` (por defecto) y `deepseek-v4-pro`; `deepseek-chat` y `deepseek-reasoner` son alias obsoletos. `flash` y `pro` a secas **no existen** |
| 12 | Cómo se invoca al ejecutor | herramienta `Agent` con `subagent_type: deepseek-executor` |
| 13 | Formato del parche | `ruta` + `<<<<<<< SEARCH` / `=======` / `>>>>>>> REPLACE` |
| 14 | Reintentos | los decide Claude, dos como máximo; el ejecutor hace una llamada por encargo. `MAX_RETRIES` del servidor (2) son reintentos de red de una misma llamada, otra cosa |
| 15 | Cómo carga el MCP una sesión nueva | al arrancar; `claude -p` abre una sesión nueva sin intervención, y carga agentes y skills del repositorio (`sesion-nueva.txt`) |
| 16 | Evidencia | la **traza de eventos** de la sesión (`stream-json`), no el texto del modelo |
| 17 | Arena | `/tmp/kontrol-orchestration-probe/`, creada y borrada por la sonda |
| 18 | Commit | solo ficheros de herramientas y gobierno, en `develop` |

`MATERIAL OQ = 0`. Decisión de configuración tomada y reversible: `FALLBACK_ENABLED=false`
en la entrada. El servidor, por defecto, cambia de modelo en silencio si el pedido falla;
la política dice que el modelo lo elige Claude, así que un fallo debe verse como fallo.

## 6. `/speckit.plan`

| Paso | Estado |
|---|---|
| W01 reconciliación · W02 auditoría de gobierno | hecho |
| W03 entorno · W04 `~/.claude.json` · W05 descubrimiento del MCP | hecho, sin valores |
| W06 presencia del secreto | hecho: existe, en otra entrada local |
| W07 cablear el MCP a KONTROL | **bloqueado** por el clasificador de permisos (§9) |
| W08 paquete y versión · W09 fijar versión · W10 node/npx | hecho |
| W11 conectar el MCP | arranque del servidor fijado: hecho, sin clave. Conexión con clave: **pendiente de W07** |
| W12 herramientas · W13 modelos · W14 metadatos del ejecutor | hecho |
| W15 sonda | hecha y probada |
| W16 delegación real · W17 auditar · W18 aplicar · W19 probar | **pendiente de W07**; la sonda las ejecuta |
| W20 camino de rechazo · W21 tope de reintentos · W22 sin memoria | hecho (ORCH-06, ORCH-10, ORCH-03) |
| W23 limpiar la arena | hecho: `SANDBOX_RESIDUAL = 0` |
| W24 repetir la auditoría · W25 documentos | hecho |
| W26 `analyze` final · W27 trazabilidad | hecho, con los `FAIL` a la vista |
| W28 converger | **no**: faltan W07 y W16..W19 |
| W29 commit y push | de lo verificado, sin declararlo convergido |

## 7. CONSTITUTION GATE

| Principio | Lectura | |
|---|---|---|
| 1 — Spec antes que código | las herramientas nacen de este delta | cumple |
| 2 — Autorización expresa | el encargo autoriza `implement` y nombra la iniciativa | cumple |
| 3 — Trazabilidad completa | §4 y §11 | cumple |
| 10 — Calidad demostrable | 73 pruebas, 34 mutantes, sonda sobre traza real | cumple |
| 12 — Decisiones documentadas | política, este delta, `CLAUDE.md` | cumple |
| 14 — Infraestructura reproducible | versión fijada; montaje y auditoría por guion | cumple |
| 15 — Datos del cliente protegidos | regla de egress; ningún dato real sale | cumple |
| 22 — Autoridad única por capacidad transversal | un solo montaje, una sola auditoría, una sola sonda | cumple |
| 27 — Una mutación solo cuenta si cambia lo observable | cada mutante cambia un resultado que una prueba observa | cumple |

Producto, esquema, migraciones: **0**. Rama: `develop`. **Gate: PASS** para implementar.

## 8. `/speckit.checklist`

| | |
|---|---|
| ✅ | repositorio reconciliado · `develop` · producto intacto |
| ✅ | `CLAUDE.md`, ejecutor, coordinador y Spec Kit válidos |
| ✅ | política de egress válida |
| ✅ | entorno y `~/.claude.json` inspeccionados sin valores |
| ✅ | clave de DeepSeek localizada · ninguna clave impresa |
| ❌ | entrada del MCP creada para KONTROL |
| ✅ | paquete y versión verificados · versión fijada · node y npx válidos |
| ❌ | MCP conectado con clave |
| ✅ | nombres y esquemas de herramientas verificados · modelos verificados en el esquema |
| ✅ | delegación preparada · arena preparada · auditoría preparada |
| ✅ | camino de rechazo y tope de reintentos verificados · limpieza de la arena |
| ✅ | `MATERIAL OQ = 0` |
| ❌ | `UNKNOWN = 0` — una incógnita: los modelos según la API, que exige la clave |

## 9. `/speckit.tasks`, `/speckit.analyze` previo e `/speckit.implement`

`analyze` previo: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`,
`MATERIAL OQ = 0`, trazabilidad 100 %. Autorización: la del encargo.

| ID | Tarea | EXECUTOR | SEC | EGRESS | Ficheros | Prueba | Estado |
|---|---|---|---|---|---|---|---|
| T01 | Descubrimiento local sin valores | CLAUDE | YES | n-a | — | `descubrimiento-local.txt` | hecho |
| T02 | Montaje: versión fijada, `--reuse-from`, conservar lo ajeno, 600 | CLAUDE | YES | n-a | `scripts/set_deepseek_key.py` | KEY-01..12 | hecho |
| T03 | Auditoría del montaje | CLAUDE | YES | n-a | `scripts/orchestration_readiness.py` | ORCH-R01..R10 | hecho |
| T04 | Nombres reales en el ejecutor, el coordinador y `CLAUDE.md` | CLAUDE | NO | n-a | `.claude/…` | `readiness` | hecho |
| T05 | Sonda ORCH-01..10 | CLAUDE | YES | n-a | `scripts/orch_probe.py` | PROBE-01..11 | hecho |
| T06 | Cablear la clave a KONTROL | **MANUAL/OWNER** | YES | n-a | `~/.claude.json` | `readiness` 12/12 | **pendiente** |
| T07 | ORCH-PROBE-001: `beta=2` → `beta=20` en la arena | **DEEPSEEK** `deepseek-v4-flash` | NO | YES | arena | ORCH-08 | **pendiente de T06** |
| T08 | Auditar, rechazar el sintético, aplicar, probar | CLAUDE | NO | n-a | arena | ORCH-05..08 | rechazo hecho; el resto, pendiente de T07 |
| T09 | Política y delta | CLAUDE | NO | n-a | `docs/governance/…`, este fichero | — | hecho |

`RETRY_MAX: 2` en todas. T02..T05 son de Claude porque manejan un secreto o definen el
criterio de auditoría: `CLAUDE_ONLY` por política. T06 pasó de `CLAUDE` a `MANUAL/OWNER`
al denegarlo el clasificador.

### Hallazgos de la implementación

1. **`NPX-RESUELTO-ROMPE-EL-MCP`.** El montaje del ciclo anterior calculaba la orden con
   `Path(which("npx")).resolve().parent / "npx"`. `bin/npx` es un enlace a
   `lib/node_modules/npm/bin/npx-cli.js`: resuelto, la orden apuntaba a un directorio donde
   no hay `node`, y npx termina con «Could not determine Node.js install directory». La
   entrada que la dueña habría creado no habría conectado nunca. Lo destapó arrancar el
   servidor de verdad. Corregido (`os.path.abspath`), con prueba (KEY-01) y mutante (M03).
2. **Los alias `flash` y `pro` no existen.** El servidor declara `deepseek-v4-flash` y
   `deepseek-v4-pro`. Corregido en `CLAUDE.md`, en los dos agentes y en la política.
3. **Cambio silencioso de modelo.** El servidor trae `FALLBACK_ENABLED=true`. El montaje lo
   apaga y el ejecutor informa `request.wire_model` y `fallback_used` (KEY-01, mutante M09).
4. **El ejecutor no inventa.** Sin MCP, devolvió `STATUS: MCP_UNAVAILABLE` con el error
   textual, intentó una sola llamada y no fabricó ningún parche (`orch-negativo.txt`).
5. **El clasificador de permisos manda sobre la autorización del encargo.** Registrado como
   `CLASIFICADOR-VS-AUTORIZACION-DE-LA-DUENA` en la política.

## 10. Evidencia — `evidence/orquestacion-ia/`

| Fichero | Qué demuestra |
|---|---|
| `descubrimiento-local.txt` | dónde está configurado DeepSeek, sin ningún valor |
| `readiness.txt` | auditoría del montaje: **10/12**; fallan «entrada local» y «clave» |
| `mcp-declarado.json` | lo que el servidor `2.3.0` declara: herramientas, argumentos, modelos, campos de salida |
| `sesion-nueva.txt` | una sesión nueva carga los dos agentes y las diez skills; `claude mcp list` |
| `orch-negativo.txt` | la sonda de hoy: **ORCH 4/10**, y la respuesta literal del ejecutor |
| `pruebas.txt` | 73 pruebas en verde; `ruff` limpio |
| `mutaciones.txt` | **34 mutantes, 34 muertos** |

### Lo que el servidor declara

| Herramienta | Para qué | Obligatorios | Opcionales relevantes | Modelo | Devuelve |
|---|---|---|---|---|---|
| `deepseek_chat` | conversación; **la única que usa el ejecutor** | `messages` | `model`, `session_id`, `thinking`, `max_tokens`, `temperature` | por defecto `deepseek-v4-flash` | `content`, `model`, `usage`, `cost_usd`, `finish_reason`, `request` (`wire_model`, `fallback_used`, tokens, coste) |
| `deepseek_fim` | completar entre prefijo y sufijo | `prompt` | `suffix`, `model`, `max_tokens` | ídem | `text`, `usage`, `cost_usd` |
| `deepseek_sessions` | listar o borrar sesiones | `action` | `session_id` | — | — |

El ejecutor no usa `deepseek_fim` ni `deepseek_sessions`, ni pasa `session_id` ni `thinking`.

### Mutaciones

34 de 34 muertos. Cuatro sobrevivieron en la primera pasada y delataron tres pruebas
flojas, ya corregidas: una leía de la propia auditoría la lista de herramientas prohibidas (M11, M12),
otra pasaba por un motivo distinto del que decía (M22) y otra no aislaba la versión sin
fijar (M08).

## 11. Trazabilidad

| Eslabón | Dónde | Estado |
|---|---|---|
| instrucción de la dueña → política | `docs/governance/ai-orchestration-policy.md` | ✅ |
| política → `CLAUDE.md` → ejecutor → coordinador | `.claude/` | ✅ |
| → MCP local | `scripts/set_deepseek_key.py` | ❌ sin entrada para KONTROL |
| → clave local | entrada local de otro proyecto | ❌ sin cablear |
| → conexión del MCP | `claude mcp list`, ORCH-02 | ❌ |
| → herramientas y modelos descubiertos | `mcp-declarado.json` | ✅ (modelos: en el esquema) |
| → delegación real | ORCH-01, ORCH-02 | ORCH-01 ✅ · ORCH-02 ❌ |
| → auditoría, aplicación, prueba | ORCH-05, 07, 08 | ❌ |
| → camino de rechazo · tope de reintentos | ORCH-06 · ORCH-10 | ✅ |
| → convergencia | — | ❌ |

Cobertura de requisitos por pruebas: **16/16** tienen prueba o comprobación. Requisitos
**demostrados hoy**: 12/16. Sin demostrar: FR-ORCH-003, 008, 009 (sobre un parche real) y
016 con el MCP.

## 12. `/speckit.analyze` final y CONVERGENCE GATE

| Contador | Exigido | Medido |
|---|---|---|
| `CONFIGURATION_INCOMPLETE` | 0 | **1** |
| `MCP_PENDING` · `KEY_PENDING` · `REAL_DELEGATION_PENDING` | 0 | **1 · 1 · 1** |
| `TOOL_NAMES_PENDING` | 0 | 0 |
| `MODEL_NAMES_PENDING` | 0 | 0 en el esquema; sin confirmar contra la API |
| `SECRET_EXPOSURE` | 0 | **0** — ni en el repositorio, ni en la evidencia, ni en las salidas |
| `PRODUCT_CHANGE` · `SCHEMA_CHANGE` · `MIGRATION` | 0 | **0 · 0 · 0** |
| ramas creadas | 0 | 0 |
| ejecutor con `Edit`, `Write`, `Bash` o Git | 0 | 0 |
| reintentos > 2 · dependencia de memoria · residuo de la arena | 0 | 0 · 0 · 0 |
| `MATERIAL OQ` | 0 | 0 |
| `UNKNOWN` | 0 | **1** |
| Master 56 | sin cambios | sin cambios |

**Gate de convergencia: NO PASA.** No se ejecuta `/speckit.converge` y no se declara
`VERIFIED_END_TO_END`.

Sobre las skills: `speckit-specify` abre una carpeta `specs/<NNN>-<slug>/` nueva, que es
justo lo que este proyecto no hace para un delta. Las fases se ejecutaron en este
documento, como en los deltas anteriores (`SPECKIT-SKILLS-VS-DELTAS`).

## 13. Lo que falta para cerrar

1. **T06**, por una de dos vías:
   - la dueña, en su terminal:
     `python scripts/set_deepseek_key.py --reuse-from <ruta del otro proyecto> --check`
     (no hay que volver a escribir la clave; se valida contra DeepSeek y no se muestra);
   - o la dueña concede a Claude el permiso y lo ejecuta él.
2. `python scripts/orchestration_readiness.py --handshake` → debe dar 12/12.
3. `python scripts/orch_probe.py --report specs/001-fundacion/evidence/orquestacion-ia/orch-certificacion.txt`
   → debe dar `ORCH = 10/10`. Abre una sesión nueva: **no exige reiniciar nada**.
4. Si pasa: estado a `VERIFIED_END_TO_END` en la política y aquí, cierre de
   `MCP-DEEPSEEK-SIN-VERSION-FIJADA`, convergencia, commit y push.

Siguiente objetivo funcional, **no iniciado**: `AUDITORIA-PAGINACION-CLIENTE`.
