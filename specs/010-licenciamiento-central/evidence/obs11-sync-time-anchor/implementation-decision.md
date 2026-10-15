# Decisión de implementación
`IMPLEMENTATION_ALLOWED = YES` (ROOT_CAUSE_CLASS = TEST_TIME_ANCHOR_DEFECT; producto, reloj canónico y protocolo intactos).
Corrección semántica, no numérica: el transporte falso captura **su** reloj de servidor al construirse (frontera de la
operación: `self.server_time = ahora + 5 min`, sin µs) y responde y desafía con él; la prueba objetivo compara con
`transporte.server_time`. Desaparece la constante de módulo `SERVER_TIME`. Rechazado: tolerancia, `approx`, sleep, retry,
skip/xfail, mover la activación, cambiar `sync_license` o `_now()`, o fijar el reloj del producto por `monkeypatch`.
Regresiones nuevas (`tests/test_licensing_sync_time_anchor.py`, O11-01…06): orden causal activación < servidor y
adopción exacta; referencia envejecida (servidor anterior a la activación) → conservación monótona (verdadero negativo
determinista, sin sleep); contrato estático del módulo (sin referencia de importación, aserción contra el transporte, sin
tolerancias ni esperas, reloj con zona); centinela del reloj del producto (`_now()` UTC con zona y regla monótona en el
servicio). `DEEPSEEK CALLS = 0` (CLAUDE_ONLY: reloj/transacciones).
