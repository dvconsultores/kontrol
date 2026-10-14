# SQLite completas con analizador real · #1 1679 passed · 8 failed · 1046 skipped (681,7 s) · #2 1679 / 8 / 1046 (692,1 s)
Referencia 1637/33/1049. Fallos 33 → **8**: los 26 del analizador **desaparecen** (todas las subidas analizan de verdad);
quedan los 7 de OBS-10 (`test_documents_legacy_import.py`, conexión compartida, no absorbidos) + 1 KNOWN_INTERMITTENT
(`test_licensing_central::TestSincronizacion::test_sync_success_records_run_snapshot_and_event`: compara un instante con el
de inicio del módulo y falla cuando el módulo tarda minutos; pasa 8/8 sola en los dos motores, con y sin analizador; ya
registrado en ciclos anteriores; OBS-11 con la firma exacta). Las dos corridas idénticas prueba por prueba; +42 pasadas.
SCANNER_FAILURES 0 · TARGET_REGRESSION 0 · UNKNOWN 0 · 0 dirs temporales.
