# Arquitectura (opción B) y abstracción mínima
```
            red interna kontrol-net (Compose)
  backend  ──── INSTREAM (bytes, trozos de 64 KiB, EOF) ────▶  clamd (kontrol-clamd)
     │           ◀──── stream: OK | stream: <firma> FOUND | … ERROR ──┘   motor ClamAV 1.4.3
     │                                                                   firmas en /var/lib/clamav (volumen kontrol-clamav-db)
     ▼                                                                   freshclam (demonio de la imagen) las actualiza
  almacén documental (/data/storage: solo el backend)
```
| Regla del encargo | Cómo se cumple |
|---|---|
| Servicios distintos | servicio `clamd` propio en `compose.yaml`; imagen `Dockerfile.clamd` (`clamav/clamav:1.4.3` + `deploy/clamd/clamd.conf`) |
| El backend transmite contenido; clamd no recibe rutas | `ClamdScanner.scan(path)` abre el **temporal local** del backend y envía `zINSTREAM\0` + trozos `<longitud><datos>` + `<0>`; la ruta nunca sale del proceso (sonda: la ruta no aparece en lo recibido por el servidor) |
| clamd no monta el almacén | `clamd.volumes = [kontrol-clamav-db:/var/lib/clamav]`, solo firmas |
| Puerto no publicado; DNS interno; sin IP | sin `ports`; `KONTROL_CLAMD_HOST=clamd` |
| Sin secretos nuevos | `KONTROL_DOCUMENT_SCANNER`, `KONTROL_CLAMD_HOST`, `KONTROL_CLAMD_PORT` (no secretos) |
| Sin registrar contenido ni EICAR | `details` lleva `reason` y, si acaso, la **respuesta del demonio** (texto corto del protocolo); la firma se audita como ya hacía `clamscan` |
| Falso seguro | toda rama que no sea `stream: OK` o `stream: … FOUND` es `SCAN_FAILED`; `service.upload_version` rechaza con 422 todo lo que no sea `CLEAN` (sin cambio) |
| Sin alternativa implícita | `get_scanner()` elige por `Settings.document_scanner` (`clamd` o `clamscan`); ninguna rama cae en la otra ni en `DisabledScanner` salvo `KONTROL_DOCUMENT_SCAN=off` explícito (contrato anterior) |
| Abstracción mínima | se conserva `FileSecurityScanner.scan(path) -> ScanResult`; `ClamdScanner` es un tercer adaptador junto a `ClamAVScanner` y `DisabledScanner`; la decisión CLEAN/INFECTED/SCAN_FAILED sigue concentrada en `service.upload_version` |
| Firmas en el dominio del analizador | imagen oficial con base inicial + `freshclam` demonio (`CLAMAV_NO_FRESHCLAMD=false`) + volumen; el backend no tiene `freshclam`, binario ni base |
| Healthcheck material | `printf 'zPING\0' | nc -w 5 127.0.0.1 3310 | grep -q PONG` (contrato real del demonio), `start_period 300s` para la carga inicial |
| Tamaño | KONTROL `GLOBAL_MAX_SIZE` 50 MiB ≤ `StreamMaxLength 60M` = `MaxFileSize 60M` ≤ `MaxScanSize 100M`; `AlertExceedsMax yes` |
| Timeout | 120 s por análisis, el mismo del adaptador anterior (sin cambio) |
