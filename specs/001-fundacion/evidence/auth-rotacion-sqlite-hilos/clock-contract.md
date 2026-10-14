# Reloj

`CLOCK_SOURCE` = `identity_service._now()` → `datetime.now(UTC)`: el reloj canónico del propio servicio de identidad
(`lockout_until`, `last_login`, `expires_at`, la revocación anterior). `TIMESTAMP_SEMANTICS`: instante UTC con zona,
columnas `DateTime(timezone=True)`; `updated_at` recibe el mismo instante que `revoked_at` (el `onupdate=utcnow` del mixin
solo actúa en flush ORM, no en un UPDATE de Core, por eso se fija explícito). No se introduce `datetime.utcnow()` ni
reloj local; la zona de negocio (`app/shared/clock.py`) no interviene. SA-16 fija estáticamente `ahora = _now()`.
