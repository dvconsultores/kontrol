# Recuperación del MCP de DeepSeek (2026-10-24)

Nada de lo que sigue imprime la clave ni el entorno. La configuración se leyó saneada (`DEEPSEEK_API_KEY` = `<oculto 35>`).

| Comprobación | Resultado |
|---|---|
| Configuración efectiva | ámbito local del proyecto; `stdio`; `npx -y @arikusi/deepseek-mcp-server@2.3.0`; `REQUEST_TIMEOUT=120000`, `FALLBACK_ENABLED=false`, PATH de nvm, clave presente |
| Proceso del servidor en la sesión | **ninguno**: la sesión no llegó a arrancarlo (CONNECT_TIMEOUT de 30 s al empezar, unos 4 min después de un reinicio del equipo) |
| `orchestration_readiness.py --handshake` | 12/12 PASS |
| R1: redescubrir la herramienta en la sesión (ToolSearch `deepseek_chat`, `+deepseek`) | ausente; la sesión informa de CONNECT_TIMEOUT y no reintenta |
| R2: arranque independiente por stdio con la orden, los argumentos y el entorno exactos + `initialize` + `tools/list` | `initialize` en **2,23–2,66 s**; herramientas `deepseek_chat`, `deepseek_fim`, `deepseek_sessions` |
| R2: llamada mínima real (EGRESS: solo «Reply exactly MCP_OK»; sin proyecto, sin rutas, sin secretos) | **`MCP_OK` en 1,01 s** (deepseek-v4-flash) |
| R3: `claude mcp get deepseek` (CLI 2.1.309 de la extensión) | **✔ Connected** (comprobación con una conexión nueva) |
| ¿Reconexión de la sesión en marcha desde el CLI o una herramienta? | no existe: `claude mcp` solo tiene `add`, `add-json`, `get`, `list`, `remove`, `login`, `logout`, `reset-project-choices` y `serve`; la reconexión solo está en el panel interactivo `/mcp` |

**MCP_ROOT_CAUSE = SESSION_TRANSPORT_NOT_RECONNECTED.**
- **MEASURED:** la sesión falló al arrancar el servidor (CONNECT_TIMEOUT de 30 s) y no lo reintenta; el servidor, la autenticación y la API funcionan ahora.
- **DERIVED:** el arranque en frío de `npx`, justo después del reinicio (red recién levantada), superó los 30 s; hoy tarda 2,2–2,7 s.
- MCP_ROOT_CAUSE_PROVEN = 1 para el fallo de transporte de la sesión. La duración del arranque en frío no se midió.

**Prevención, sin aplicar** (cambia la configuración de Claude Code, no la de KONTROL): fijar `MCP_TIMEOUT` (p. ej. 120000) en el `env` de los ajustes de Claude Code para las sesiones nuevas.

## Cierre (2026-10-24, tras `/mcp → deepseek → Reconnect` de la dueña)

| Campo | Valor |
|---|---|
| Llamada real por el canal del orquestador (`deepseek-executor` → `mcp__deepseek__deepseek_chat`) | `MCP_OK` (deepseek-v4-flash, 9/3 tokens, $0.000002) |
| DEEPSEEK_CALL_EXECUTABLE | 1 |
| MCP_RECOVERY_STATUS | CLOSED / OPERATIONAL |
| MCP_STARTUP_TIMEOUT_CURRENT | 30000 ms (por defecto; el binario 2.1.309 lee `MCP_TIMEOUT`, valor > 0, tope 2147483647, si no 30000) |
| MCP_TIMEOUT_CONFIGURATION_SUPPORTED | 1 (variable reconocida por el binario de Claude Code, junto a `MCP_TOOL_TIMEOUT` y `MCP_CONNECT_TIMEOUT_MS`) |
| MCP_STARTUP_TIMEOUT_TARGET | 120000 ms |
| MCP_TIMEOUT_CHANGED | 1 — `env.MCP_TIMEOUT = "120000"` en los ajustes de usuario de Claude Code (copia previa guardada fuera del repositorio) |
| MCP_TIMEOUT_SCOPE | LOCAL_DEVELOPER_ENVIRONMENT_CONFIG; fuera del repositorio, no se confirma; vale para sesiones nuevas |
| Reversión | quitar la clave `env.MCP_TIMEOUT` de los ajustes de usuario |
