# Investigación — Autoridad Central Fase 1

| Punto | Hallazgo |
|---|---|
| Cliente de sync | `service.default_sync_client`: `urllib`, `POST {server_url}/v1/license/sync`, cabeceras solo `Content-Type`/`Accept`, cuerpo `{version, installation_id, license_jws, modules, requested_at}`; respuesta esperada `{version, status, server_time, expires_at, entitlements}` (`contracts/api-contracts.md` de la 010). **Sin autenticación ligada a la instalación** |
| Identidad de instalación | `Installation.installation_uuid` + par Ed25519 propio; la clave pública viaja en `GET /license/installation-request` |
| Canonicalización | `json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")` sobre el dict recibido; probado en `evidence/licencia-revision/canonicalizacion.txt` que `revision` presente solo en los paquetes nuevos no toca los bytes legacy |
| `app/core/license.py` | importa `app.core.config` (settings del cliente, exige `KONTROL_SECRET_KEY`) y `app.core.errors`: no es importable por un servicio aislado sin arrastrar la configuración del cliente → extracción del contrato puro |
| Entorno | `pyproject`/`requirements.lock` del backend; `.venv` compartido; `Dockerfile.backend` con `entrypoint.sh` (`alembic upgrade head` + `uvicorn`) |
| Compose cliente | `compose.yaml`: `frontend`, `backend`, `watchtower`; red `kontrol-net`; sin PostgreSQL propio (externa) |
| Patrón de bloqueo | `with_for_update` (identity, inventory, notifications, licensing Fase A) |
| Patrón de secretos | pydantic-settings con prefijo `KONTROL_`, validadores que fallan al inicio, `hide_input_in_errors` |
| QA | `qa/e2e_corrida.py` genera un firmante por corrida; `qa/licencia_firmada.py` firma a medida: ambos son stand-ins, no emisores |
| ADR-D0-006 | arquitectura aprobada, hospedaje pendiente; clave privada solo en la autoridad |
| D0-06 | `BUSINESS_DECISION_PENDING` → ratificado: vendor-hosted, aislado, agnóstico de proveedor |
