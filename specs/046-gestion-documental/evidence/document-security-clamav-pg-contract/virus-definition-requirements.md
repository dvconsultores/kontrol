# Base de firmas

`VIRUS_DB_REQUIRED = sí` (sin base, `clamscan` devuelve 2 → `SCAN_FAILED`). `TEST_SIGNATURE = EICAR` (cadena estándar, no malware; en
`test_documents.py::test_archivo_infectado_se_rechaza_y_no_se_almacena` y `test_documents_security.py::test_amz_10`; la segunda
acepta `FILE_INFECTED` o `SCAN_FAILED`, así que hoy pasa sin analizador por el camino del falso seguro). La mayoría de las
pruebas usan el camino «archivo limpio → CLEAN». `UPDATE_REQUIRED = sí` (firmas con fecha). `NETWORK_REQUIRED = sí` para
`freshclam`. `DETERMINISTIC_QA_SUPPORT`: versionar un juego de `.cvd` con fecha fijada y `KONTROL_CLAMAV_DB` apuntando a él.
