# DEEPSEEK_BRIDGE_INCIDENT_CTL05 · 2026-11-11

## Llamadas a DeepSeek

| Intento | ¿Llegó a DeepSeek? | Consumo | Hecho |
|---|---|---|---|
| C1 | Sí | 1 llamada, $0,027 | Carga idéntica al encargo |
| C2 | Sí | 1 llamada, $0,025 | Carga idéntica al encargo |
| C3 | Sí | 1 llamada, $0,006 | Carga idéntica al encargo |
| C4, intento 1 | **No** | 0 | El subagente puente dijo buscar `/mnt/data/a.txt`, una ruta que no existía ni se le había dado. No usó herramientas. |
| C4, intento 2 | **No** | 0 | El puente fabricó el contenido de una supuesta lectura («C4 Design Notes — Cached Content») sin haber llamado a Read ni a DeepSeek. |
| C4, intento 3 | **No** | 0 | Las salvaguardas de la API (Sonnet 5.5, `reasoning_extraction`, req_011Cgw2ib89iiDmk7m96QWQ4) cortaron el subagente antes de cualquier llamada. Su salida degeneró en un bucle de «Done/Final». |

- **Total:** `DEEPSEEK_CALLS_CONSUMED = 3`, con un coste aproximado de $0,058.
- **Validez:** ninguna salida de los intentos 1 a 3 de C4 es evidencia, ni se aplicó nada de ellas al producto.
- **Detección:** se comprobó leyendo la traza de cada subagente, que no contiene ninguna llamada `tool_use` a `deepseek_chat`.

## Verificación del canal (ciclo de reconciliación)

`scripts/orchestration_readiness.py --handshake`:
- servidor MCP `@arikusi/deepseek-mcp-server@2.3.0`, con apretón de manos correcto;
- herramientas `deepseek_chat`, `deepseek_fim` y `deepseek_sessions`;
- modelos `deepseek-v4-flash` y `deepseek-v4-pro`;
- clave presente (no se lee ni se imprime).

El único FAIL es una comprobación de redacción de CLAUDE.md («Solo `develop`»). Es anterior al ciclo y ajena al canal.

**Conclusión:** `DEEPSEEK_AVAILABLE = 1`. El fallo estuvo en el subagente puente, no en DeepSeek. No se intentó evadir ninguna salvaguarda, y el encargo C4 anterior no se reformuló para pasar un filtro. Queda obsoleto y se sustituye por `C4_REBASED.md`, generado contra `b73c171`.
