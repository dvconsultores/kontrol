# Contrato de imagen y composición (verificado estáticamente por `qa/clamd_qa.py estatico`; la construcción y el arranque en contenedores quedan para un equipo con runtime, ver `implementation-decision.md`)
| Campo | Valor |
|---|---|
| `BACKEND_IMAGE_HAS_CLAMSCAN` | NO (NOT REQUIRED): `Dockerfile.backend` sin ClamAV |
| `BACKEND_IMAGE_HAS_SIGNATURE_DATABASE` · `BACKEND_MOUNTS_SIGNATURES` | NO · NO |
| `CLAMD_SERVICE_PRESENT` | YES (`kontrol-clamd`, imagen `<registry>/kontrol-clamd:<tag>` construida con `Dockerfile.clamd` FROM `clamav/clamav:1.4.3`) |
| `CLAMD_INTERNAL_ONLY` · `CLAMD_HOST_PORT_PUBLISHED` | YES (solo `kontrol-net`) · NO (sin `ports`) |
| `DOCUMENT_STORAGE_MOUNTED_IN_CLAMD` | NO (`volumes: kontrol-clamav-db:/var/lib/clamav` únicamente) |
| `SHARED_FILE_PATH_REQUIRED` | NO (INSTREAM) |
| `CLAMD_HEALTHCHECK_PRESENT` · `_MEANINGFUL` | YES · YES (PING → PONG por el puerto; `start_period 300s`) |
| Firmas | imagen con base inicial; `freshclam` demonio dentro del servicio (`CLAMAV_NO_FRESHCLAMD=false`); volumen persistente; **ninguna** reconstrucción de KONTROL para actualizarlas |
| `depends_on` | solo orden de arranque; con clamd caído el backend sigue fallando cerrado (`SCAN_FAILED`) |
| Selección explícita | `KONTROL_DOCUMENT_SCANNER=clamd`, `KONTROL_CLAMD_HOST=clamd`, `KONTROL_CLAMD_PORT=3310` en el backend; `.env.example` documenta las tres |
| Límites | `StreamMaxLength 60M`, `MaxFileSize 60M`, `MaxScanSize 100M`, `AlertExceedsMax yes` ≥ 50 MiB documentales |
| Watchtower | el servicio lleva la etiqueta de actualización como los demás |
Medidas que exigen runtime (`docker build`, tamaño de imagen, `compose up`, healthcheck real, `docker inspect`): **no
realizadas** en este equipo (`COMPOSE_RUNTIME_UNAVAILABLE`); pasos exactos en `docs/evidence/docker-validation-checklist.md`.
