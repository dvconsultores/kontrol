# SPEC 054 · Delta dirigida — OBS-10 · DOCUMENTS-LEGACY-IMPORT-SQLITE (enlace cruzado)
La delta completa vive en `specs/046-gestion-documental/spec046-obs10-legacy-import-sqlite-delta.md` con evidencia en
`specs/046-gestion-documental/evidence/obs10-legacy-import-sqlite/`. Lo que atañe al arnés: `motor_para_hilos` se reutiliza
sin cambio (quinto módulo que lo adopta); la familia «conexión pysqlite compartida + HTTP o sesión auxiliar con la
transacción de la prueba abierta» ya cuenta tres casos corregidos en origen (UoM `test_el_historico…`, auth, legado):
el patrón es resolver identificadores por la API **antes** de abrir la sesión de escritura. `motor_para_hilos` no cambia.
