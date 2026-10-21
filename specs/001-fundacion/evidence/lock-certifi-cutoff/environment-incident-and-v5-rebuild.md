# Incidente de entorno y reconstrucción de V5 (2026-10-21)

## Reinicio del equipo
- El equipo arrancó a las **15:30** (hora local), con la cadena de certificación ya lanzada.
- `/tmp` se vació: el scratchpad, V5 y el clúster PostgreSQL de QA (`/tmp/kontrol-pgdata-045`) desaparecieron.
- El repositorio quedó intacto: lock regenerado, pruebas, `cve-review`, delta y evidencia ya escrita.
- **Recuperación sin tocar nada versionado:**
  - `bash qa/pg-provision.sh start` y `bash qa/pg-provision.sh mkdb ktest`; `qa/e2e-bases.py listar` da 0 huérfanas.
  - Venv de pip-audit (2.10.1) con el intérprete del sistema y sonda de humo desechable recreada con los mismos pasos y
    contadores (V0: 544/533/11).
  - **V5 reconstruido con el método documentado**, a partir del **digest fijado** (no de la etiqueta):
    - índice `70729b46…`, recuperable por digest, y amd64 `8fb4cfa1…`, ambos verificados por sha256;
    - `InRelease` de trixie-security y de trixie main con firmas correctas;
    - `Packages.xz` verificados y `.deb` verificados;
    - borrado de dpkg, que retira `Comodo_AAA_Services_root.crt` y `emSign_ECC_Root_CA_-_G3.crt`;
    - `update-ca-certificates --sysroot`: 148 CA.
  - Resultado: `pip install --no-deps` del lock nuevo, `pip check` PASS, freeze = lock (certifi 2026.10.19) y pip-audit
    0 en PyPI y OSV.
- La cadena de certificación (dirigidas, V0, V5 y E2E) se lanzó de nuevo completa. No se reaprovecha ninguna corrida
  interrumpida.

## Observación: la etiqueta upstream se reconstruyó
- `python:3.13.16-slim-trixie` resuelve ahora a `sha256:cf50a4f6…`, con amd64 `08b493e9…`, creado
  2026-10-21T01:11:16Z.
- El índice anterior era `70729b46…`.
- La nueva construcción trae CPython 3.13.16, `ca-certificates 20250419+deb13u1`, `liblzma5 5.8.1-1+deb13u2`,
  `libssl3t64 3.5.7-1~deb13u3` y `libc6 2.41-12+deb13u4` (`upstream-tag-rebuild-observation.json`).
- **El pin por digest evitó que este cambio llegara al build sin revisión.** El Dockerfile sigue en `70729b46…`, que
  sigue siendo recuperable.
- Hay una oportunidad para un ciclo futuro, siguiendo la política de actualización: volver a fijar la base en el
  índice reconstruido, retirar el pin explícito de `ca-certificates` (la imagen ya lo incluye) y recertificar. **No se
  hace en este ciclo:** la referencia base no se modifica aquí.
