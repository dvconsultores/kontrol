# Protocolo con el demonio
`CLAMD_STREAMING_USED = 1` · `SHARED_FILE_PATH_REQUIRED = 0` · `DOCUMENT_STORAGE_MOUNTED_IN_CLAMD = 0`.
Secuencia: `zINSTREAM\0` → (`!I longitud` + datos) × n, trozos de 64 KiB → `!I 0` → respuesta terminada en `\0`.
| Situación | Comportamiento del adaptador | Evidencia |
|---|---|---|
| trozos parciales / EOF | longitud prefijada por trozo y trozo final de longitud cero; 3 MiB = 48 trozos, 50 MiB = 800 | O09-08/09/10; demonio real (`clamd-qa-report.json`) |
| conexión cerrada por el demonio sin responder | `truncated_response` o `stream_interrupted` → SCAN_FAILED | O09-04/15; sonda `flujo_interrumpido` |
| respuesta truncada (sin `\0`) o desbordada (> 4096 B) | `truncated_response` | O09-07; sonda `respuesta_truncada` |
| respuesta inválida (`UNKNOWN COMMAND`, basura) | `protocol_error` (respuesta recortada a 200 caracteres) | O09-06/22; sonda `error_de_protocolo` |
| timeout | `timeout` en el plazo del adaptador (120 s en producto; 1–2 s en pruebas) | O09-05; sonda `tiempo_agotado` |
| conexión rechazada / demonio no disponible (también tras arrancar) | `connection_refused` | O09-03/25; sonda `demonio_caido` |
| `stream: OK` exacto | CLEAN (ni `OKAY`, ni `ok`, ni vacío) | O09-01/21 |
| `stream: <firma> FOUND` | INFECTED con la firma (incluido `Heuristics.Limits.Exceeded` de `AlertExceedsMax`) | O09-02/20; demonio real: `Eicar-Test-Signature` |
| `… ERROR` (p. ej. límite de tamaño) | `scanner_error` → SCAN_FAILED | O09-22; demonio real: 60 MiB + 1 B |
Nada del contenido ni la ruta sale en `details`; solo la razón y el texto corto del protocolo (O09-19; sondas: la ruta del
temporal no aparece en lo recibido por el servidor).
