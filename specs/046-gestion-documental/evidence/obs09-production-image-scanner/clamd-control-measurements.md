# Control local con el demonio real (etapa 1; `clamd` 1.4.3 del paquete Debian extraído en `<qa-cache>`, solo TCP en 127.0.0.1, sin privilegios)
| Medida | Valor |
|---|---|
| Arranque hasta `PING → PONG` | 6,3 s (carga de firmas) |
| `VERSION` | `ClamAV 1.4.3/28153/Wed Oct 14 08:24:15 2026` (motor / versión de `daily` / fecha de la base) |
| INSTREAM PDF limpio (59 B) | `stream: OK` · 0,010 s |
| INSTREAM EICAR | `stream: Eicar-Test-Signature FOUND` · 0,003 s |
| INSTREAM 3 MiB en trozos de 64 KiB (48 trozos) | `stream: OK` · 0,218 s |
| INSTREAM 50 MiB (máximo de KONTROL, 800 trozos) con `StreamMaxLength 60M` | `stream: OK` · 1,73 s |
| INSTREAM 50 MiB + 1 B con 60M | `stream: OK` · 1,78 s |
| INSTREAM 61 MiB con `StreamMaxLength 60M` | `INSTREAM size limit exceeded. ERROR` · 0,19 s (y `WARNING … Size limit reached` en el registro) |
| Con los **valores por defecto** de clamd (`StreamMaxLength 25M`, `MaxFileSize 25M`) | 25 MiB exactos → `OK`; 25 MiB + 1 → `INSTREAM size limit exceeded. ERROR`; 50 MiB → el demonio cierra la conexión (`BrokenPipeError` al enviar) |
| Orden desconocida (`zXYZZY`) | `UNKNOWN COMMAND` |
| Comparación con `clamscan` por proceso (OBS-12) | 6,39 s por análisis → 3–220 ms por análisis con el demonio (la carga de firmas se hace una vez) |
Conclusiones para el contrato: (1) INSTREAM funciona con trozos parciales y EOF explícito (longitud 0); (2) los límites por
defecto de clamd (25M) son **inferiores** al máximo documental de KONTROL (50 MiB): la configuración del servicio debe
fijar `StreamMaxLength` y `MaxFileSize` ≥ 50 MiB (se fija 60M, `MaxScanSize 100M`, `AlertExceedsMax yes`); (3) la
respuesta de límite es un `ERROR` reconocible y el cierre abrupto se manifiesta como `BrokenPipe`/`ConnectionReset`: ambos
deben traducirse a `SCAN_FAILED`. Guion y configuración de control en `<scratch>/o9/` (fuera del repositorio).
