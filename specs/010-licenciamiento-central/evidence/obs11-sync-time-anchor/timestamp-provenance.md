# Procedencia de los instantes
| Instante | Dónde nace | Reloj | Con zona | Semántica | Vida | Orden esperado |
|---|---|---|---|---|---|---|
| importación del módulo (`SERVER_TIME` − 5 min) | `import tests.test_licensing_central` | `datetime.now(UTC)` | sí | «ahora» de la importación | todo el proceso de pytest | antes de todo |
| `SERVER_TIME` | línea 106 | importación + 5 min, sin microsegundos | sí | reloj que la autoridad falsa dirá tener | todo el proceso | debería ser **posterior** a la activación de la prueba |
| activación (`import_license`) | `_activate_license` → servicio línea 376 `state.last_reliable_date = _utc(last_reliable or _now())` | `_now()` = `datetime.now(UTC)` del servicio (reloj técnico UTC) | sí | fecha fiable inicial = instante de activación | fila de estado | justo antes del sync |
| `requested_at` / `ran_at` | servicio 751/840 | `_now()` | sí | instantes de la corrida de sync | fila `license_sync_runs` | ≥ activación |
| `server_time` recibido | respuesta del transporte falso = `SERVER_TIME.isoformat()` | — | sí | reloj autenticado del servidor | respuesta | — |
| `last_reliable_date` tras el sync | servicio 849–852: `recibido` si `actual is None or actual < recibido`, **si no se conserva `actual`** (monótono) | — | sí (UTC) | reloj confiable | fila de estado | ≥ activación, ≥ anterior |
| `verified_at` | servicio 853 | `_now()` | sí | — | fila | — |
Precisión: Python µs; `SERVER_TIME` sin µs; columna `DateTime(timezone=True)`: PostgreSQL µs con zona, SQLite hora de pared
naive (de ahí el `.replace(tzinfo=UTC)` de la aserción). La aserción no necesita tolerancia: compara el valor exacto que el
servidor falso envió (sin µs) con lo persistido.
