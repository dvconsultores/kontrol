# Recomendación

1. **OBS-08** (hecho en este ciclo, con autoridad existente): las seis carreras llevan el marcador canónico PostgreSQL-only con
   razón que cita FR-046-115 / conc-046 / P21; contrato estático `tests/test_documents_carreras_contrato.py`; cobertura no
   concurrente intacta en SQLite. No cambia nada del analizador.
2. **ENTORNO-SIN-CLAMSCAN → decisión de la dueña, recomendación A**: proveer ClamAV real en el QA canónico (PostgreSQL + E2E):
   paquete Debian 1.4.3 (con privilegios) o extracción a prefijo de usuario documentada en `qa/` con `KONTROL_CLAMSCAN_PATH`
   y `KONTROL_CLAMAV_DB`, juego de firmas versionado con fecha fijada y política de refresco; preflight de disponibilidad en
   `qa/e2e-run.py` y en la suite PostgreSQL; después, remedir: 35 fallos PostgreSQL, 4 omitidas E2E y las seis carreras
   deberían pasar a verde y cada rojo nuevo se clasifica. Razones: la Spec 046 se certificó así (ESC-046-01), la suite de
   seguridad rechaza dobles, y hoy la seguridad documental **no se certifica** en esta máquina (35+4 sin ejecutar de verdad).
   Alternativa mínima B (seguir declarando): honesta, pero deja sin certificar el camino principal de 046.
3. **No** C (falso `CLEAN`): contradice §159 y el closeout; **no** D.
4. Registrar, no absorber: OBS-09 (la imagen de producción no instala el analizador que el producto usa por defecto) y OBS-10
   (`test_documents_legacy_import.py`: 7 fallos SQLite por la conexión compartida + petición HTTP en medio de la sesión,
   mal atribuidos al analizador; candidato a ciclo de arnés con `motor_para_hilos`/ciclo de vida, misma familia que OBS-02).
