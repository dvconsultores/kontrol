# Contrato del reloj canónico (intacto)
| Elemento | Dónde | Estado |
|---|---|---|
| `_now()` del servicio de licenciamiento | `app/modules/licensing/service.py:46` → `datetime.now(UTC)` | sin cambio; centinela O11-06 |
| `_utc()` / `_dt_from()` / `license_contract._as_utc` | servicio 190 / `app/core/license_contract.py` | sin cambio |
| regla monótona del reloj confiable | servicio 849–852 | sin cambio; literal fijado por O11-06 |
| fecha fiable en la activación | servicio 376 `_utc(last_reliable or _now())` | sin cambio; literal fijado por O11-06 |
| reloj de negocio (`app/shared/clock.py`, America/Caracas) | — | no interviene en el sync |
| columnas `DateTime(timezone=True)` | modelos | sin cambio (SQLite devuelve hora de pared naive; la prueba reetiqueta UTC) |
Las pruebas no fijan ni simulan el reloj del producto (`monkeypatch` 0 sobre `_now`); solo el transporte falso elige su
propio `server_time`, como haría un servidor real.
