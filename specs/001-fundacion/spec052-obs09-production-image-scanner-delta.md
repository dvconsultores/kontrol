# SPEC 052 · Delta dirigida — OBS-09 (enlace cruzado: instalación y composición)
La delta completa vive en `specs/046-gestion-documental/spec046-obs09-production-image-scanner-delta.md`. Para la Spec 052
(instalación y actualización): `compose.yaml` incorpora el servicio `clamd` (imagen `Dockerfile.clamd` = `clamav/clamav:1.4.3`
+ `deploy/clamd/clamd.conf`, red interna, sin puerto publicado, volumen de firmas propio, healthcheck PING→PONG, firmas
actualizadas por `freshclam` dentro del servicio) y el backend recibe `KONTROL_DOCUMENT_SCANNER=clamd`, `KONTROL_CLAMD_HOST`,
`KONTROL_CLAMD_PORT` (`.env.example`). La actualización de firmas no exige reconstruir KONTROL. Pasos de validación en el
servidor con Docker: `docs/evidence/docker-validation-checklist.md` (sección OBS-09).
