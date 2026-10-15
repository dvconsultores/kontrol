# Precisión por motor
| Motor | `last_reliable_date` leído | Zona | µs |
|---|---|---|---|
| SQLite | `datetime(2026,10,14,23,22,56,365601)` naive (hora de pared UTC) | se reetiqueta con `.replace(tzinfo=UTC)` | conservados |
| PostgreSQL | `datetime(..., 492321, tzinfo=utc)` | conservada | conservados |
Con referencia válida (activación < servidor) el valor persistido es **exactamente** el enviado por el servidor (sin µs) y la
igualdad se cumple en los dos motores sin tolerancia. `PRECISION_IS_CAUSE = NO`; `TIMEZONE_IS_CAUSE = NO`;
`ENGINE_DIFFERENCE = NONE` (matriz idéntica en SQLite y PostgreSQL).
