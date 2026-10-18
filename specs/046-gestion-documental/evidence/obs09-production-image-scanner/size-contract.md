# Contrato de tamaño
| Registro | Valor |
|---|---|
| `KONTROL_DOCUMENT_MAX_SIZE` | `GLOBAL_MAX_SIZE = 50 MiB` (`documents/service.py:48`; por tipo documental puede ser menor); el servicio corta a 413 `FILE_TOO_LARGE` **antes** del análisis |
| clamd por defecto | `StreamMaxLength 25M`, `MaxFileSize 25M`, `MaxScanSize 100M` → **insuficiente**: 25 MiB + 1 B → `INSTREAM size limit exceeded. ERROR`; 50 MiB → el demonio cierra la conexión (medido) |
| `deploy/clamd/clamd.conf` | `StreamMaxLength 60M` · `MaxFileSize 60M` · `MaxScanSize 100M` · `AlertExceedsMax yes` → KONTROL_MAX (52 428 800 B) ≤ 62 914 560 B |
| Pruebas de frontera (demonio real 1.4.3, adaptador del producto) | 59 B PDF → CLEAN · EICAR → INFECTED `Eicar-Test-Signature` · 3 MiB (48 trozos) → CLEAN 0,16 s · **50 MiB → CLEAN 1,6 s** · 50 MiB + 1 B → CLEAN (el demonio lo admite; KONTROL lo rechaza antes, 413) · 60 MiB + 1 B → `SCAN_FAILED` (`scanner_error`, `INSTREAM size limit exceeded. ERROR`) · flujo cortado a mitad → `SCAN_FAILED` |
| Política funcional | **sin cambio**: no se reduce el máximo documental; el servicio se configura para soportarlo (`MATERIAL OQ = 0`) |
