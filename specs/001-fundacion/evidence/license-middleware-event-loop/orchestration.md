# Orquestación (regla permanente 1)
| Delegación | Modelo | Tokens | Coste | Auditoría | Hallazgos | Aplicado |
|---|---|---|---|---|---|---|
| L02a producto | `deepseek-v4-flash` | 1 713 / 423 | $0,0003 | **PASS** | — | sí, tal cual (+1 import, 1 línea) |
| L02b prueba (intento) | `deepseek-v4-pro` | 5 551 / 6 758 | $0,0082 | **REJECT** | `pytest.skip` y parametrización por motor; `motor_para_hilos` cerrado antes de las pruebas; Parte B sin `create_app()` y con un `_get_mode` propio; retenedora `async` que no retenía la conexión; semáforos desconectados; ruta AST errónea; código muerto; doble que esperaba 10 s en cada escritura; L05 mal planteada; 9 avisos de ruff | no |
| L02b corrección 1 | `pro` | 11 732 / 7 127 | $0,0112 | **REJECT** | L09 leía un atributo que ya no se actualizaba (16/17); función muerta `_generar_motor`; imports sin uso e I001; montaje duplicado; aserción de duración vacía | no |
| L02b corrección 2 | `pro` | 7 973 / 6 049 | $0,0086 | **PASS** salvo una función muerta | `_endpoint` sin uso | sí, tal cual |
| L02c (reclasificación tras 2 reintentos) | `flash` | 658 / 313 | $0,0002 | **PASS** | — | sí, tal cual |
- **Totales.** TASKS 3 (L02a, L02b, L02c) · CLAUDE_BRIEFS 5 · DEEPSEEK_CALLS 5 · RETRIES 2 (L02b) · EGRESS_CHECKS 5 ·
  AUDIT_PASS 3 · AUDIT_FAIL 2 · CHANGES_APPLIED 3 · CHANGES_REJECTED 2 · COST **$0,0285**.
- **Autoría.** Claude no escribió ni retocó código de producto ni de prueba.
- **Desviación de egress de Claude.** El brief de la corrección 1 incluyó, en la salida cruda de pytest, una ruta absoluta con el
  nombre del usuario local (`/home/<usuario>/…`). No contenía credenciales, tokens, URLs autenticadas, datos reales ni
  secretos. El escaneo de egress corrió en paralelo con el envío y no antes. Las corrección 2 y L02c se sanearon, y se
  comprobó el egress antes de enviar (0 coincidencias). La regla queda registrada: sanear siempre y comprobar antes de enviar.
