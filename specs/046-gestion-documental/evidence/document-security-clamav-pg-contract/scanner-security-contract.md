# Contrato de seguridad del analizador

- Ausencia del binario = `SCAN_FAILED`, **nunca** `CLEAN` (§26; closeout §7). Con `scan_required` (defecto) la subida se rechaza con
  **422 `SCAN_FAILED`**; es el comportamiento vigente y correcto («falso seguro»). No es un 503: la Spec lo modela como rechazo de dominio.
- Desactivación explícita (`KONTROL_DOCUMENT_SCAN=off`) = `SKIPPED` declarado al cliente; solo un `DocumentType` con `scan_required=false`
  lo acepta (FR-046-072, AC-046-28). Un archivo `SKIPPED`/`SCAN_FAILED` no se entrega (`FILE_NOT_SCANNED`).
- Naturaleza de la ausencia: **capacidad de despliegue configurable** (CL-046-09), no un error de arranque; QA la trata como condición
  de entorno declarada (`ENTORNO-SIN-CLAMSCAN` en el runner E2E, `skipif(not KONTROL_CLAMSCAN_PATH)` en las dos pruebas EICAR).
- Lo que la evidencia de cierre exige: la Spec 046 se certificó con analizador real (ESC-046-01), y la suite de seguridad declara
  que un doble no vale como evidencia de cierre. No hay autoridad que diga que **QA debe tener** ClamAV de forma permanente, ni cómo
  provisionarlo (el closeout lo extrajo «del `.deb` sin privilegios», sin guion en el repositorio).
- `FR-DOCENV-018`: el falso seguro se conserva; este ciclo no toca producto.
