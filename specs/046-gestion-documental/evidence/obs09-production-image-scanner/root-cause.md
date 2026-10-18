# Causa raíz
`ROOT_CAUSE = PRODUCTION_COMPOSITION_MISSING_SCANNER` + `BACKEND_SCANNER_CONTRACT_DEPLOYMENT_MISMATCH` (demostradas por
inventario, no por inferencia): el producto exige por defecto un analizador (`ClamAVScanner`, falso seguro) y la composición
de producción (`compose.yaml`, `Dockerfile.backend`) no proporciona ni el binario ni las firmas ni variable alguna del
analizador; sin ellos toda subida con `scan_required` termina en 422 `SCAN_FAILED` (comportamiento observado en el ciclo
ENTORNO-SIN-CLAMSCAN: 35 pruebas documentales fallaban exactamente así). `IMAGE_CONTRACT_GAP`: no existía ningún contrato
verificable de imagen/composición respecto al analizador. `QA_IMAGE_COVERAGE_GAP`: el QA certifica con `clamscan` local, no
la composición. UNKNOWN 0.
