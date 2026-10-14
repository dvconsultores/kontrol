# Cobertura documental en SQLite (sin analizador)

`test_documents.py` 25 pruebas · `test_documents_security.py` 37 · `test_documents_legacy_import.py` 8 (70; n9 es PG-only).
Hoy en SQLite: 25 pasan, 42 fallan, 3 omitidas. Las que pasan no suben archivos (tipos, metadatos, permisos, rutas,
validaciones). Tras marcar las seis carreras PostgreSQL-only, SQLite conserva **29 pruebas no concurrentes** en
`test_documents_security.py` (AMZ-01…20 salvo las seis y la SVG) y todas las de `test_documents.py`; ninguna se pierde en
silencio: las seis se omiten con razón y siguen corriendo en PostgreSQL. Lo que SQLite **no puede** certificar sin analizador
sigue siendo lo mismo que PostgreSQL: cualquier subida con `scan_required`.
