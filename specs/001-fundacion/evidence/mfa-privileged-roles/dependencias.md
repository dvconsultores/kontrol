# Dependencia nueva del ciclo MFA (OQ-MFA-2 = A) — 2026-10-26

| Paquete | Versión | Licencia (metadatos) | Uso | Alcance |
|---|---|---|---|---|
| `segno` | 1.6.6 (fijada en `requirements.txt`) | BSD (`License :: OSI Approved :: BSD License`) | QR del alta como SVG en el backend (`mfa_qr.svg_data_uri`), sin servicios externos | runtime |

- Locks regenerados con `uv pip compile … --exclude-newer 2026-10-20T02:24:15.073Z --upgrade`: el único cambio de
  `requirements.lock` y `requirements-test.lock` es `+segno==1.6.6` (sin dependencias transitivas nuevas).
- `pip check`: «No broken requirements found».
- `pip-audit -r requirements.lock --no-deps --disable-pip` (pip-audit 2.10.1): «No known vulnerabilities found».
- El frontend no añade dependencias: el QR se pinta solo como `<img>` con data URI SVG validado (sin `dangerouslySetInnerHTML`).
