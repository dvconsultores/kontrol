# Trazabilidad
| Pregunta del encargo | Evidencia |
|---|---|
| ¿Por qué se retiene la conexión? | D1, D4, D5, `root-cause.md` |
| ¿Sesión o conexión? | D1/D2: CONNECTION_CHECKED_OUT_DURING_SCAN = 1 (no solo la sesión) |
| ¿Qué transacción vive y qué protege? | D2 (`pg_stat_activity`, `pg_locks`), D8: solo lectura, nada |
| ¿Qué puede cambiar durante el análisis? | D7a, D7b |
| ¿Hay frontera segura? | D9, D9b, `safe-boundary-and-design.md` |
| ¿Orden de almacenamiento? | D6 |
| ¿Concurrencia? | D3 |
| Invariantes de seguridad | `security-invariants-and-toctou.md` |
Trazabilidad 100 %.
