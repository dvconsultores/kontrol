# SPEC 054 · Delta dirigida — OBS-08 + ENTORNO-SIN-CLAMSCAN (enlace cruzado)

La delta completa vive en **`specs/046-gestion-documental/spec046-document-security-clamav-pg-contract-delta.md`** con su
evidencia en `specs/046-gestion-documental/evidence/document-security-clamav-pg-contract/`. Lo que atañe al arnés y al
entorno de certificación (054):

| | |
|---|---|
| OBS-08 | las siete carreras documentales llevan el marcador canónico PostgreSQL-only (`skipif(not PG, reason=… (P21))`), como `test_license_import_race.py`; contrato estático nuevo `tests/test_documents_carreras_contrato.py`; en SQLite se omiten 9 nodos con razón; cobertura no concurrente intacta |
| ENTORNO-SIN-CLAMSCAN | **BLOCKED BY OWNER DECISION**: proveer ClamAV real en el QA canónico (A, recomendada) o seguir declarando (B); matriz y viabilidad en la evidencia. Nada cambia en el runner E2E ni en los skips hasta la decisión |
| Inventario corregido | los 7 fallos SQLite de `test_documents_legacy_import.py` **no** son del analizador: conexión pysqlite compartida + petición HTTP con la sesión abierta (OBS-10, misma familia que OBS-02; candidato de arnés) |
| Observaciones nuevas | OBS-09: `Dockerfile.backend` no instala el analizador que el producto usa por defecto (decisión de despliegue, 046) |
