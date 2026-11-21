# SPEC 001 · DELTA MCP-2-4-0 — SE FIJA `@arikusi/deepseek-mcp-server@2.4.0` Y SE RECERTIFICA LA ORQUESTACIÓN

- **Spec dueña:** `specs/001-fundacion` (herramientas de orquestación; delta padre
  `spec001-orquestacion-ia-delta.md`).
- **Fecha:** 2026-11-20 · **Rama:** `develop` · **Base:** `b726c1da`.
- **Autorización:** la dueña eligió la opción **B** («aceptar 2.4.0 y fijarla en un ciclo propio»)
  tras el diagnóstico de esta sesión.
- **Tipo:** fundamento técnico (herramienta de desarrollo). No toca producto.

## 0. PRODUCT COMPLETENESS GATE

| Campo | Valor |
|---|---|
| `WHERE_IS_IT_IN_MENU` | no aplica: herramienta del puesto de desarrollo |
| `WHAT_CAN_USER_DO` | nada nuevo en KONTROL; Claude puede volver a delegar tareas acotadas en DeepSeek |
| `OWNER_UAT_READY` | NOT_APPLICABLE |
| `PRODUCT_STATUS` | sin cambio de producto |
| `MISSING_GATES` | ninguno del ciclo |
| `WHY_UI_NOT_APPLICABLE` | solo cambian el guion de montaje del MCP, la auditoría del montaje y la política de orquestación |

## 1. Lo que había, medido

| Pieza | Estado de partida |
|---|---|
| `scripts/set_deepseek_key.py` | `PACKAGE_VERSION = "2.3.0"` |
| Servidor que corría | `2.4.0`, instalado a mano el 2026-11-13 en `~/.local/deepseek-mcp` con rango `^2.4.0` y lanzado con `node` directo |
| Ámbito de la entrada | **usuario** (`~/.claude.json › mcpServers`), no el local del proyecto que espera el guion |
| `FALLBACK_ENABLED` | **ausente** en esa entrada: el cambio silencioso de modelo quedaba activado |
| Entrada local del proyecto | ninguna |
| `orchestration_readiness.py --handshake` | **FAIL 8/12**: CLAUDE.md, entrada local, clave y arranque (sin `npx` en el `PATH` del shell) |
| `scripts/tests` | **1 failed, 76 passed**: `test_orch_r10[comprobar_claude_md]` exigía «Solo `develop`», y la norma vigente desde el 2026-11-01 dice «Rama única: solo `develop`» |

Una delegación de prueba sobre una arena de la sesión (ORCH-PROBE-001) funcionó: AUDIT_PASS, prueba verde
y un rechazo negativo correcto. Funcionar no equivalía a cumplir la política.

## 2. Specify · clarify

- **FR-1:** el montaje fija `@arikusi/deepseek-mcp-server@2.4.0` exacta.
- **FR-2:** KONTROL usa una entrada **local del proyecto**, creada por el guion, con `npx` absoluto,
  `PATH` explícito y `FALLBACK_ENABLED=false`.
- **FR-3:** la auditoría del montaje reconoce la norma de rama tal como está redactada.
- **FR-4:** la política documenta la versión vigente y la recertificación.
- **Clarify:** la versión la decidió la dueña (B). `MATERIAL OQ = 0`. La entrada de ámbito de usuario
  **no se toca**: sirve a otros proyectos (§6).

## 3. Revisión de 2.4.0 (antes de fijarla)

Superficie declarada (`evidence/mcp-2-4-0/superficie-2.3.0-a-2.4.0.diff`):

- Siguen las tres herramientas (`deepseek_chat`, `deepseek_fim` y `deepseek_sessions`), con los mismos argumentos
  obligatorios y opcionales.
- El modelo por defecto pasa a `deepseek-flash` (V4.1 Flash). `deepseek-v4-flash` queda como **nombre heredado
  aceptado** y viaja a la API como `deepseek-flash`, el nombre con el que la API ya respondía con la 2.3.0 (`CLAUDE.md`
  lo registraba). El modelo servido no cambia, y tampoco la regla de pedirlo como `deepseek-v4-…`.
- `deepseek_fim` añade el campo de salida `pricing_tier`.

CHANGELOG 2.4.0, leído en el paquete de la caché de `npx`:

- **Seguridad:** GHSA-46jr-4wx8-v453 (alta) limita los argumentos de herramienta a 20 000 elementos.
  El SDK de MCP pasa a 1.32.
- **Costes:** la tabla de precios se corrige (estaba dos revisiones atrasada) y se distingue el
  tramo pico del valle. El `cost_usd` de la 2.3.0 subestimaba el coste.
- **`FALLBACK_ENABLED`:** se sigue respetando (`config.js`: `fallbackEnabled = FALLBACK_ENABLED !== 'false'`).

Veredicto: sin deriva de contrato para el ejecutor. La versión es aceptable.

## 4. Plan · CONSTITUTION GATE

Cambios: `PACKAGE_VERSION`, el texto exigido en `comprobar_claude_md` y la política §8–§10. Sin
dependencias, esquema, migraciones ni producto. Sin secretos: la clave pasó del ámbito de usuario
al local por variable de entorno del proceso y no se imprimió en ninguna salida.

`BLOCKER = CRITICAL = CONTRADICTIONS = OWNER CONFLICT = 0` · `UNKNOWN = 0` · gate **PASS**.

## 5. Tasks

| ID | Tarea | EXECUTOR | MODEL | SECURITY_SENSITIVE | EGRESS_SAFE | RETRY_MAX | FILES | TEST | DONE_WHEN |
|---|---|---|---|---|---|---|---|---|---|
| T001 | Fijar `2.4.0` | CLAUDE | n-a | sí (paquete que recibe la clave) | n-a | 2 | `scripts/set_deepseek_key.py` | handshake | servidor declara 2.4.0 = fijada |
| T002 | Texto exigido de la norma de rama | CLAUDE | n-a | no | n-a | 2 | `scripts/orchestration_readiness.py` | `test_orch_r10` + M1 | 77 passed; M1 muere |
| T003 | Volver a montar la entrada local | CLAUDE | n-a | sí (clave) | n-a | 2 | `~/.claude.json` (fuera de Git) | `set_deepseek_key.py --status` | fijada, con clave, `FALLBACK_ENABLED=false` |
| T004 | Recertificar ORCH-01..10 | CLAUDE | n-a | no | sí | 2 | arena `/tmp` | `orch_probe.py` | 10/10 |
| T005 | Política y evidencia | CLAUDE | n-a | no | n-a | 2 | `docs/governance/ai-orchestration-policy.md`, este delta, `evidence/mcp-2-4-0/` | revisión | versión y recertificación documentadas |

Ninguna tarea es `DEEPSEEK_ELIGIBLE`. T001 y T003 tocan el montaje que recibe la clave (seguridad). T002 es
de una línea y más barata de hacer que de encargar. T004 y T005 son certificación y gobierno. Claude
hizo el ciclo entero. `DEEPSEEK CALLS` del ciclo: 1 en ORCH-PROBE-001 (diagnóstico previo, $0.000266) y 1 dentro de
la sonda ORCH ($0.000209).

## 6. Evidencia — `evidence/mcp-2-4-0/`

| Fichero | Contenido |
|---|---|
| `readiness.txt` | `READINESS = PASS (12/12)`, RC 0, handshake v2.4.0 |
| `mcp-declarado.json` | lo que declara el servidor 2.4.0 |
| `superficie-2.3.0-a-2.4.0.diff` | diferencia con lo que declaraba la 2.3.0 |
| `orch-certificacion.txt` | `ORCH = 10/10`, `ORCHESTRATION_STATUS = VERIFIED_END_TO_END`, `SANDBOX_RESIDUAL = 0` |
| `pruebas.txt` | `scripts/tests`: 77 passed |
| `mutaciones.txt` | línea base (1 failed), M1 muere, restauración |

ORCH-09 sobre la 2.4.0: se pidió `deepseek-v4-flash` y se sirvió `deepseek-flash`, sin fallback, `stop`, con 661/215 tokens
y un coste de $0.000209.

## 7. Observaciones

- **`ENTRADA-DE-USUARIO-SIN-FALLBACK`** (abierta, fuera de KONTROL). La entrada `deepseek` de ámbito
  de usuario sigue apuntando a `~/.local/deepseek-mcp` sin `FALLBACK_ENABLED=false`. En KONTROL
  prevalece la entrada local del proyecto. Retirarla o fijarla lo decide la dueña.
- **Sesión interactiva:** la sesión que hizo este ciclo arrancó con la entrada de usuario. Hasta que
  se reinicie Claude Code, el MCP que ve es ese. La sonda corrió en una sesión nueva, ya con la entrada local.
- **`.venv` del backend ausente en este puesto:** las pruebas de `scripts/tests` se corrieron con el
  `python3` del sistema (pytest 8.3.5).

## 8. Converge

FR-1..FR-4 cumplidos; T001..T005 COMPLETE; sin tareas ni requisitos huérfanos. Estado: **CONVERGED**.
