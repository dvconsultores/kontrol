# Aserción exacta
| Registro | Valor |
|---|---|
| `TARGET_FILE` · `TARGET_CLASS` · `TARGET_TEST` | `tests/test_licensing_central.py` · `TestSincronizacion` · `test_sync_success_records_run_snapshot_and_event` (línea 155) |
| `EXACT_ASSERTION` | `assert state.last_reliable_date.replace(tzinfo=UTC) == SERVER_TIME  # el reloj confiable viene del servidor autenticado` (línea 175) |
| `LEFT_OPERAND` | `state.last_reliable_date` persistido por `sync_license` (columna `DateTime(timezone=True)`; en SQLite vuelve naive y se reetiqueta UTC) |
| `RIGHT_OPERAND` | `SERVER_TIME`, **constante de módulo**: `(datetime.now(UTC) + timedelta(minutes=5)).replace(microsecond=0)` (línea 106), evaluada al **importar** el módulo |
| `COMPARISON_OPERATOR` · `TOLERANCE` | `==` · ninguna |
| `MODULE_LEVEL_TIME_CONSTANTS` | `SERVER_TIME` (usada por `_TransporteFalso` en `server_time` de la respuesta y `expires_at` del desafío, y en esta aserción) |
| `TEST_LEVEL_TIME_CONSTANTS` | ninguna en el objetivo; otras pruebas fijan `last_reliable_date = now − 2 d / − 30 d` |
