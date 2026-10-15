# Gate material y decisión de implementación
| Pregunta | Respuesta |
|---|---|
| ¿Defecto de rendimiento del producto? (salida D) | **NO**: ninguna operación del producto consume tiempo patológico; el coste dominante es el analizador por proceso (seguridad, decisión de la dueña) y los procesos reales de las pruebas de arnés |
| ¿Espera del arnés defectuosa? (salida C) | **NO**: todas las esperas son techos no consumidos o sondeos cortos; `busy_timeout` no se consume |
| ¿Coste estable del analizador? (salida E) | **SÍ**: 6,39 s por análisis, 55 % (SQLite) / 39 % (PG): legítimo; se registra, no se optimiza |
| ¿Atípico explicado? (salida A) | `HISTORICAL_OUTLIER_WITH_INSUFFICIENT_HOST_TELEMETRY`; no reproducido; sin causa inventada |
| ¿Brecha de observabilidad? (salida B) | **SÍ**: el QA no registraba duración monotónica, perfil, carga ni memoria; no puede distinguir anomalía de anfitrión de defecto |
| `PRODUCT_CHANGE_REQUIRED` · `TEST_SEMANTICS_CHANGE_REQUIRED` · `TIMEOUT_CHANGE_REQUIRED` · `SCANNER_SECURITY_CHANGE_REQUIRED` · `PARALLELIZATION_DECISION_REQUIRED` | NO · NO · NO · NO · NO |
| **AUTORIZACIÓN EXPRESA — ETAPA 2** | consumida: implementación limitada a **observabilidad del QA** (contrato de medición), documentación y evidencia |
Diseño (CLAUDE_ONLY; DeepSeek 0): un módulo `qa/suite_tiempos.py` que **envuelve la orden canónica sin cambiar su colección
ni su orden** (`-o addopts= -q --durations=0 -p no:cacheprovider`) y escribe en `qa/backend-runs/<run_id>/` (ignorado por Git,
como `qa/e2e-runs/`) `manifest.json` + `pytest.txt` + `host.csv`, con: duración monotónica y desvío de reloj
(`e2e_corrida.desvio_de_reloj`), recuentos del resumen de pytest, metadatos del analizador (`clamav_qa`), top N por prueba,
muestras de anfitrión saneadas cada 30 s (`/proc`: load, MemAvailable, swap usada y paginación, CPU, E/S de disco),
`getrusage` del árbol, residuos efímeros (sin contar `kontrol-test-storage`) y un **indicador de anomalía no bloqueante**
(razón entre la duración y la mediana de las corridas anteriores del mismo motor registradas en `qa/backend-runs/`; sin
referencia hasta tener 3; `HARD_THRESHOLD = NONE`). El código de salida es el de pytest. Pruebas O12-01…20 con dobles de
`/proc` y de la salida de pytest; mutaciones M-01…M-12. Rechazado: cambiar `pytest`/`conftest`/pruebas de producto,
`xdist`, reordenar, umbral duro, medir con el analizador apagado.
