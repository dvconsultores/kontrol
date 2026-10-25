# KONTROL — Claude (piensa, audita, integra) + DeepSeek (ejecuta lo acotado)

Este archivo guía a los agentes en este repositorio. **La Constitución
(`.specify/memory/constitution.md`) prevalece sobre él.** La política completa, con su
porqué y el estado del montaje, está en `docs/governance/ai-orchestration-policy.md`.

## Precedencia

1. Decisiones de la dueña · 2. Constitución de KONTROL · 3. Specs y ADR aprobados ·
4. esta política de orquestación · 5. instrucciones de la tarea · 6. sugerencias de DeepSeek.

Una sugerencia de DeepSeek nunca contradice nada de lo anterior, y una decisión abierta
(`MATERIAL_DECISION_REQUIRED`) no se resuelve en silencio: se escala a la dueña.

## Rama y Git

- **Solo `develop`.** No se crea ninguna otra rama (`spec/*`, `feature/*`, `fix/*`, `temp/*`…)
  sin autorización expresa de la dueña; ninguna herramienta debe crearlas por su cuenta.
- Git lo controla Claude. DeepSeek y los subagentes no hacen `commit`, `push`, `reset`,
  `checkout`, `rebase`, `clean` ni `branch`.
- Un ciclo se cierra con **commit y push a `origin/develop`** (instrucción vigente de la
  dueña, 2026-09-30) y con `git status` vacío. Solo entran los ficheros del ciclo.

## Metodología: Spec Kit, siempre

`specify → clarify → plan → CONSTITUTION GATE → checklist → tasks → analyze → trazabilidad →
autorización expresa → implement → pruebas y evidencia → converge`.

- Las skills instaladas se invocan con guion (`/speckit-specify`, `/speckit-plan`…); la
  notación con punto de los encargos (`/speckit.specify`) es el mismo flujo.
- No se editan a mano `.claude/skills/speckit-*`: se actualizan con `specify integration upgrade`.
- **Un delta dirigido vive dentro de la Spec dueña**, como
  `specs/<spec>/specNNN-<slug>-delta.md` con su `evidence/<slug>/`. No se crea una Spec
  maestra nueva para cerrar una deuda.
- La autorización de `implement` es la del encargo y nombra la iniciativa (Constitución P2).

## Quién hace qué

**Claude** conserva el juicio: lee el encargo, reconcilia `HEAD` y árbol, resuelve la Spec
dueña, ejecuta Spec Kit, hace arqueología del repositorio, detecta contradicciones y
decisiones materiales, diseña, clasifica tareas, prepara el contexto mínimo, **audita todo
parche**, aplica solo lo aprobado, ejecuta pruebas y mutaciones, interpreta fallos,
verifica esquema, OpenAPI y seguridad, converge e informa.

**DeepSeek** ejecuta tareas de implementación pequeñas, explícitas y cerradas. **Propone;
no edita, no decide, no certifica.** Devuelve bloques SEARCH/REPLACE que Claude audita.

### Clasificación, tarea por tarea

Cada tarea de `tasks.md` lleva: `EXECUTOR` (`CLAUDE` | `DEEPSEEK`), `MODEL`
(`deepseek-v4-flash` | `deepseek-v4-pro` | `n-a`), `SECURITY_SENSITIVE`, `EGRESS_SAFE`, `RETRY_MAX: 2`, `FILES`,
`TEST`, `DONE_WHEN`. Nunca se clasifica una Spec entera.

`DEEPSEEK_ELIGIBLE` exige **todo** esto: contrato cerrado, `MATERIAL OQ = 0`, sin incógnitas
relevantes, fichero objetivo identificado, cambio local, invariantes definidos, resultado
verificable, y que no pida decidir arquitectura, seguridad ni negocio, ni migrar, ni
depurar, ni interpretar requisitos ambiguos.

`CLAUDE_ONLY`, aunque DeepSeek pudiera generar el código: autenticación, control de acceso,
permisos, alcances de usuario, **aislamiento de tenant**, criptografía, secretos, firmas de
licencia, MFA, seguridad de sesión, **migraciones, backfills y reparación de datos**,
operaciones destructivas, fórmulas monetarias o **fiscales** no fijadas al detalle, reglas
tributarias, redondeo, moneda, semántica contable, arquitectura de idempotencia, diseño de
concurrencia, refactors grandes, cambios de arquitectura, ADR nuevos, **depuración y
búsqueda de causa raíz**, incidentes de seguridad, cambios transversales y cualquier
decisión material abierta. `specify`, `clarify`, `plan`, el gate, `analyze` y `converge`
son siempre de Claude.

Dinero y fiscal: DeepSeek solo escribe código mecánico **después** de que Claude fije
fórmula, escala, redondeo, contrato y vectores de prueba.

## Delegar a DeepSeek

Solo tras el gate: `BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0`, sin
requisitos ni tareas huérfanas, `MATERIAL OQ = 0`, `UNKNOWN = 0`, trazabilidad 100 %. Si no,
`DEEPSEEK CALLS = 0`.

Cada delegación es **autocontenida** (sin memoria de la anterior) y usa el subagente
`deepseek-executor` con este formato:

```
TASK:            T0XX
GOAL:            un objetivo concreto
TARGET FILES:    rutas exactas (lista cerrada)
READ-ONLY CONTEXT: rutas exactas que puede leer
CONTRACT:        FR / AC / interfaces exactas
INVARIANTS:      lo que no puede romperse
CONSTRAINTS:     lo que no puede tocarse
IMPLEMENTATION STYLE: patrón existente que debe imitar
OUTPUT FORMAT:   solo bloques SEARCH/REPLACE
DONE WHEN:       condiciones exactas
TESTS EXPECTED:  las pruebas diseñadas por Claude
MODEL:           deepseek-v4-flash | deepseek-v4-pro
```

Contexto mínimo suficiente: ficheros objetivo, interfaces, función hermana, prueba
relacionada, requisito concreto. Nunca el repositorio entero ni «investiga y arréglalo».

### Egress: antes de cada llamada

DeepSeek es un proveedor externo. Se delega solo si todo esto es cero:

```
EGRESS_CHECK: ENV_FILES=0 SECRETS=0 PROD_URLS=0 TOKENS=0 PRIVATE_KEYS=0
              REAL_PII=0 REAL_PAYROLL=0 BANK_DATA=0
```

Nunca salen `.env*`, claves, tokens, contraseñas, URLs de base de datos con credenciales,
certificados privados, datos personales, bancarios o fiscales reales, volcados productivos
ni logs con secretos. La clave de DeepSeek vive solo en `~/.claude.json` (entrada local
del MCP de este proyecto); no se imprime, no se registra y no entra en el repositorio. Una
clave expuesta detiene el trabajo: `SECRET_EXPOSURE`.

### El MCP, tal como es

Servidor `deepseek`, paquete `@arikusi/deepseek-mcp-server` **con versión fijada** (la que
declara `scripts/set_deepseek_key.py`). Herramienta de delegación:
`mcp__deepseek__deepseek_chat`, sin `session_id` y sin `thinking`. Modelos:
`deepseek-v4-flash` (por defecto: lo pequeño y mecánico) y `deepseek-v4-pro` (lógica local
más compleja); un modelo más fuerte nunca convierte en delegable una tarea `CLAUDE_ONLY`.
La API responde `deepseek-flash` como nombre del primero: es el mismo modelo; a la
herramienta se le pide siempre con el nombre `deepseek-v4-…`.
Montaje: `python scripts/set_deepseek_key.py`; auditoría del montaje:
`python scripts/orchestration_readiness.py --handshake`; certificación de extremo a extremo
(ORCH-01..10, en una sesión nueva): `python scripts/orch_probe.py`.

### Auditoría del parche (Claude, antes de aplicar)

Tarea exacta · solo ficheros objetivo · sin imports ni dependencias nuevas · sin cambio de
esquema ni migración · sin secretos ni PII · sin tocar fronteras de seguridad · sin deriva
de contrato · sin respaldos ocultos · sin `any` injustificado · sin excepciones amplias ·
sin compatibilidad silenciosa · sin `sleep`, reintentos ni `skip` · sin `TODO` por
implementación · sin código muerto · sin formato ajeno.

Resultado: `AUDIT_PASS` (Claude aplica) o `AUDIT_REJECT` con motivo concreto. **Un bloque
SEARCH que no coincide exactamente se rechaza**; Claude no arregla a mano el parche para
atribuírselo después al ejecutor.

Claude Code entrega el informe de un subagente **sangrado dos espacios**. Ese marco —y solo
ese— se quita antes de comparar el SEARCH: no es parte del parche ni un retoque.

### Reintentos: máximo 2

Intento → rechazo → reintento 1 → rechazo → reintento 2 → **alto**. Cada reintento reenvía
el contexto completo, el intento anterior y el motivo exacto del rechazo. Tras dos
reintentos Claude reclasifica: dividir la tarea, pasar a `deepseek-v4-pro` o implementarla él.

### Probar tras cada tarea

Después de aplicar una tarea se ejecuta la prueba más pequeña que demuestra el cambio. No
se apila trabajo sobre una tarea rota. Un «debería funcionar» de DeepSeek no es evidencia:
la evidencia la produce o la verifica Claude, que además audita los verdes falsos (mocks
equivocados, aserciones vacías, selectores demasiado amplios, `skip`, `sleep`).

## Informes

Por tarea:

```
[ANALYZE]  contrato e invariantes verificados
[PLAN]     cambio esperado
[CLASSIFY] CLAUDE_ONLY | DEEPSEEK_ELIGIBLE
[EXECUTE]  Claude | DeepSeek <modelo> (<in>/<out> tokens, $<coste>)
[AUDIT]    PASS | REJECT (<motivo>)
[TEST]     <comando> — <resultado>
[STATUS]   COMPLETE | RETRY <n> | BLOCKED
```

Por delta, al cierre: tareas totales, `CLAUDE_ONLY`, `DEEPSEEK_ELIGIBLE`, ejecutadas por
DeepSeek, reintentos, parches rechazados y aceptados, implementadas por Claude, pruebas,
mutaciones, regresiones y coste. Si Claude hizo la tarea entera, se dice.

## Comandos canónicos

- Backend (desde `resources/backend/`): `.venv/bin/python -m pytest tests`; sobre PostgreSQL,
  `KONTROL_TEST_DB_URL=postgresql+psycopg2://postgres@localhost:55432/ktest`; `.venv/bin/ruff
  check`; `.venv/bin/mypy`.
- Frontend (desde `resources/frontend/`): `npm run typecheck` (recorre `src`, las herramientas y
  `e2e/` por referencias) · `npm run lint` · `npm test` · `npm run build` · `npm run test:e2e`.
- PostgreSQL de QA: `bash qa/pg-provision.sh start`; siembra E2E: `bash qa/e2e-seed.sh <url>`.
- Analizador real (ClamAV, sin privilegios, Spec 046): `python qa/clamav_qa.py provisionar` una vez; antes de
  certificar, `eval "$(python qa/clamav_qa.py entorno)"` (exporta `KONTROL_CLAMSCAN_PATH` y `KONTROL_CLAMAV_DB`); la
  E2E canónica con analizador es `qa/e2e-run.py --con-analizador`. Sin él, las cargas documentales se rechazan (falso seguro).
- **Certificación backend con telemetría** (Spec 054, OBS-12): `python qa/suite_tiempos.py --motor sqlite|postgres
  --con-analizador` (desde la raíz) corre la orden canónica con `--durations=0`, duración monotónica, telemetría del
  anfitrión saneada y un indicador de anomalía no bloqueante; evidencia en `qa/backend-runs/<run_id>/` (fuera de Git).
- **Certificación E2E completa**: `resources/backend/.venv/bin/python qa/e2e-run.py` (desde la
  raíz; `-- <args de Playwright>` para dirigirla). Cada corrida crea una base PostgreSQL efímera
  nueva, la migra a la cabeza, la siembra, levanta backend y Vite contra ella, corre Playwright y
  lo elimina todo al terminar; `kaud` es solo QA manual. Huérfanas tras una muerte a la fuerza:
  `qa/e2e-bases.py listar | purgar --confirmar`.

- **Certificación de release (canónica, Spec 054)**: `python3 qa/certificar-release.py` (desde la raíz,
  con el `python3` del sistema) es la única orden de certificación: reconstruye V6R (rootfs de
  `python:3.13.16-slim-trixie` por digest más `requirements.lock`) y V6C (V6R más `requirements-test.lock`)
  y ejecuta en etapas preflight, entorno, locks, V6R, V6C, subconjunto runtime, PostgreSQL/SQLite, E2E,
  OpenAPI, pip-audit, residuos, manifiesto y veredicto. Opciones: `--incluir-v0-historico` (control V0,
  nunca por defecto), `--espera-salud-min N`, `--conservar-espacio`, `--solo-preflight` (diagnóstico, no
  certifica). RC: 0 pasa, 1 fallo, 3 INVALID_ENVIRONMENT, 4 preflight correcto, 70 preflight/interno;
  nunca a través de tubería. Evidencia en `qa/certificaciones/<run_id>/manifest.json` (fuera de Git).
  E2E canónica con 6 workers y 0 reintentos fijos (`--workers=6 --retries=0`), sin importar CPU ni `CI`.
  Política de entorno v1: preflight RC 70 ante variables heredadas prohibidas; el manifiesto solo registra nombres.
  PostgreSQL de QA fijado en `qa/postgres_qa.json` (sin `.venv` ni compilador); árbol certificado en `CANONICAL_RUN_INPUT_HASH` v2.
  Certificación oficial en anfitrión dedicado (OD-CERT-27), requisitos en la evidencia de specs/012.

Delegar no rebaja ningún gate: backend, frontend, build, E2E, mutaciones y regresiones de
seguridad se ejecutan cuando el ciclo los exige.

## Producción

Ni DeepSeek ni Claude ejecutan nada contra producción —`psql`, guiones destructivos,
migraciones reales— sin autorización expresa de la dueña.
