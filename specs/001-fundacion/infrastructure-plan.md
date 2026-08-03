# PLAN DE INFRAESTRUCTURA — 001-FUNDACION

| Campo | Valor |
|---|---|
| Iniciativa | 001-fundacion |
| Versión | 1.0 |
| Responsable | Arquitecto de infraestructura |
| Ruta | `specs/001-fundacion/infrastructure-plan.md` |

## 1. Servicios Compose

| Servicio | Imagen/Origen | Persistencia | Health check | Restart | Red |
|---|---|---|---|---|---|
| `frontend` | Build multi-stage (Node → Nginx) | No | `curl /healthz` | `unless-stopped` | interna |
| `backend` | Build multi-stage (Python 3.13) | Temporales | `/api/v1/health/live` | `unless-stopped` | interna |
| `db` | `postgres:18` (digest) | `kontrol-db-data` | `pg_isready` | `unless-stopped` | interna |
| `reverse-proxy` | `nginx` (línea estable, digest) | No | TCP check | `unless-stopped` | pública |
| `worker` | **No en 001** (ADR-009) | — | — | — | — |

## 2. Volúmenes

| Volumen | Uso |
|---|---|
| `kontrol-db-data` | Datos PostgreSQL (obligatorio, respaldado) |
| `kontrol-storage` | Documentos/archivos (obligatorio, respaldado) |
| `kontrol-license-state` | Identidad de instalación, claves locales, licencia firmada, última fecha confiable |
| `kontrol-backups` | Respaldos |

## 3. Archivos de infraestructura esperados

- `compose.yaml` (producción).
- `compose.dev.yaml` (desarrollo).
- `.env.example`.
- `Dockerfile.backend`, `Dockerfile.frontend`, `nginx.conf`.
- `kontrol.py` (CLI).
- `scripts/install.sh`, `scripts/backup.sh`, `scripts/restore.sh`, `scripts/diagnose.sh`, `scripts/update.sh`.

## 4. Seguridad de infraestructura

- Imágenes multi-stage, no root, versionadas y fijadas.
- Sin secretos en imágenes ni en Git.
- Usuario PostgreSQL restringido; sin exposición pública de `db`.
- TLS en Nginx o proxy seguro del cliente.
- Health checks para frontend, backend y DB.
- Migraciones ejecutadas de forma controlada con respaldo y rollback.

## 5. Operación y soporte

- CLI `kontrol` con preflight, backup, pull, migrate, health y rollback.
- Diagnóstico de instalación (versión, identidad, licencia, servicios) sin exponer secretos.
- Matriz de soporte L1/L2/L3/Fiscal/Infraestructura (DOC-05 §13).

## 6. Estado

| Elemento | Estado |
|---|---|
| Servicios y volúmenes | ✔ (especificado) |
| Archivos | ✔ (especificado; implementación T-004..T-010, T-042, T-043) |
| Aprobación | Pendiente |
