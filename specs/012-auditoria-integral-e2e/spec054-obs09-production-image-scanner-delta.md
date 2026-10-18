# SPEC 054 · Delta dirigida — OBS-09 (enlace cruzado: QA)
La delta completa vive en `specs/046-gestion-documental/spec046-obs09-production-image-scanner-delta.md`. Para el QA:
`qa/clamd_qa.py provisionar|certificar|estatico` deja el demonio real (paquete oficial `clamav-daemon` 1.4.3, sin privilegios,
en el prefijo de `qa/clamav_qa.py`), lo arranca con la configuración del despliegue adaptada y certifica con el adaptador
del producto CLEAN, EICAR, varios trozos, el máximo documental, demonio caído, tiempo agotado, protocolo, respuesta truncada,
flujo cortado y la ausencia de rutas en el flujo; además verifica el contrato estático de imagen y composición y declara el
runtime de contenedores disponible. Pruebas: `tests/test_documents_clamd.py` (O09-01…25) y `tests/test_clamd_qa.py`
(CLAMD-QA-01…11). La certificación canónica (`suite_tiempos.py`, `e2e-run.py`) sigue con `clamscan` (decisión A + A2).
