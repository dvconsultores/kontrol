# Dueña
`FUNCTIONAL_OWNER`: **Spec 054** (QA, arnés, auditoría; carpeta `specs/012-auditoria-integral-e2e`). Fuente de la
observación: `specs/001-fundacion/evidence/auth-rotacion-sqlite-hilos/OBSERVACIONES.md` (OBS-06: «`tests/conftest.py` los
fija a rutas constantes bajo el tmp del sistema, compartidas entre procesos»), reiterada en el roadmap. Consumidores del
producto (documentos 046, reporting 009) son consumidores, no dueños. Precedente de la misma dueña en el mismo fichero:
TEST-VOLUMEN-DE-INSTALACION-COMPARTIDO (`pytest_configure` + `mkdtemp` por proceso + `pytest_unconfigure` + sondas).
