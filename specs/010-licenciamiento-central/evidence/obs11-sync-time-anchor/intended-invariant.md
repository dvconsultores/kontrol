# Invariante pretendida
`INTENDED_INVARIANT`: tras un sync con éxito, el reloj confiable toma el instante **autenticado por el servidor** cuando
este es posterior al reloj confiable vigente; nunca retrocede («reloj confiable (`server_time`, monótono)», docstring de
`sync_license`; FR-010-003). `AUTHORITY_SOURCE`: Spec 010 FR-010-003, servicio 849–852, comentario de la propia aserción.
`WHY_TIMESTAMP_COMPARISON_EXISTS`: probar que el valor persistido es exactamente el del servidor (no el local).
`MINIMUM_REQUIRED_ORDERING`: `server_time > last_reliable_date` previa (activación) para que la igualdad sea exigible.
`MAXIMUM_REQUIRED_ORDERING`: ninguna. `IDENTITY_CORRELATION_AVAILABLE`: el valor exacto enviado por el transporte falso es la
identidad del instante: basta compararlo con lo que el transporte envió **en esta operación**. Precondición oculta de la
prueba actual: la activación debe ocurrir **antes** de `SERVER_TIME` (importación + 5 min); se cumple sola, pero deja de
cumplirse cuando entre la importación del módulo y la prueba pasan más de 5 minutos.
