# Implementación (solo pruebas; Claude, CLAUDE_ONLY; DEEPSEEK CALLS = 0)
## `tests/test_licensing_central.py` (−4/+6 líneas aprox.)
- Se elimina la constante de módulo `SERVER_TIME = (datetime.now(UTC) + timedelta(minutes=5)).replace(microsecond=0)`.
- `_TransporteFalso.__init__` captura **primero** `self.server_time = (datetime.now(UTC) + timedelta(minutes=5)).replace(microsecond=0)`
  (frontera de la operación; el servidor va cinco minutos por delante del reloj local) y lo usa en `server_time` de la
  respuesta por defecto y en `expires_at` del desafío. Docstring ampliado con el porqué (OBS-11).
- Prueba objetivo: `transporte = _fake_sync_client()` → `sync_license(..., transport=transporte, ...)` →
  `assert state.last_reliable_date.replace(tzinfo=UTC) == transporte.server_time`. Ninguna otra aserción cambia.
- Las demás pruebas del módulo usan `_fake_sync_client()` sin leer la referencia: sin cambio funcional (cada transporte
  trae su propio reloj, siempre posterior a la activación de su operación).
## `tests/test_licensing_sync_time_anchor.py` (nuevo, O11-01…06)
| Id | Qué fija | Tipo |
|---|---|---|
| O11-01 | activación < reloj del transporte (orden causal) y adopción **exacta** del servidor | comportamiento, dos motores |
| O11-02 | referencia envejecida (servidor 1 min detrás de la activación) → el reloj confiable **conserva la activación** (verdadero negativo determinista, sin sleep: el escenario que la prueba antigua etiquetaba como fallo) | comportamiento |
| O11-03 | dos syncs sucesivos: el segundo con reloj anterior no retrocede el máximo | comportamiento |
| O11-04 | el transporte falso captura su reloj al construirse (+5 min, sin µs, con zona) y lo usa en respuesta y desafío | unidad |
| O11-05 | contrato estático del módulo objetivo: ninguna asignación de módulo con `now/utcnow/today`, sin `SERVER_TIME`, primera sentencia de `__init__` = `self.server_time` con `datetime.now(UTC)` y `microsecond=0`, aserción exacta contra `transporte.server_time`, sin `approx/abs/timedelta` en la prueba objetivo, prohibiciones (`sleep(`, `retry`, `skip`, `xfail`, `flaky`, `reruns`, `approx`, `utcnow(`, `datetime.now()`) en el módulo y en estas regresiones | estático |
| O11-06 | centinela del reloj canónico del producto: `_now()` con zona UTC; regla monótona literal del servicio (849–852) y `last_reliable_date = _utc(last_reliable or _now())` en la activación | tripwire |
`ruff check`: limpio. (`ruff format --check` ya señalaba el módulo en `HEAD`; no se reformatea código ajeno al cambio.)
Sin producto, sin reloj canónico, sin migración, sin esquema, sin tolerancia, sin sleep/retry/skip/xfail, sin orden de pruebas.
