# Convergencia · `OBS-10 — CLOSED / CONVERGED` (2026-10-15)
Siete nodos clasificados con una sola causa demostrada (HARNESS_SHARED_CONNECTION_PLUS_LIFECYCLE) y corregidos en el arnés y
en el ciclo de vida de las pruebas, sin tocar aserciones, producto, migraciones, esquema ni analizador; 12/12 mutaciones;
dirigidas 34/34; SQLite 1692/1/1046 ×2 y PostgreSQL 2712/1/26 (solo OBS-11); E2E 284/0/0 con analizador; OpenAPI sin cambio;
0 bases, 0 schemas, 0 dirs. Líneas base nuevas: SQLite 1692/1/1046 · PostgreSQL 2712/1/26 · E2E 284/0/0.
Observación nueva, no absorbida (OBS-12): la segunda SQLite completa tardó 2946 s frente a 587 s con resultados idénticos:
carga de la máquina; conviene medir en un ciclo propio si alguna prueba queda sensible al tiempo (familia OBS-11).
Cierre por delta: tareas 9 · CLAUDE_ONLY 9 · DeepSeek 0 · ficheros: 1 modificado (`test_documents_legacy_import.py`), 1 nuevo
(`test_documents_legacy_import_contrato.py`).
