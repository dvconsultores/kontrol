#!/usr/bin/env bash
set -euo pipefail
umask 077

cd "$(dirname "$0")/../.."

UAT_IMAGE_TAG="${UAT_IMAGE_TAG:?UAT_IMAGE_TAG es obligatoria}"
UAT_RELEASE_SHA="${UAT_RELEASE_SHA:?UAT_RELEASE_SHA es obligatoria}"
KONTROL_IMAGE_REGISTRY="${KONTROL_IMAGE_REGISTRY:?KONTROL_IMAGE_REGISTRY es obligatoria}"
UAT_ENV_FILE="${UAT_ENV_FILE:-/etc/kontrol-uat/uat-env}"
UAT_STATE_DIR="${UAT_STATE_DIR:-/var/lib/kontrol-uat}"
UAT_REPORT_DIR="${UAT_REPORT_DIR:-}"
UAT_HEALTH_TIMEOUT="${UAT_HEALTH_TIMEOUT:-600}"

if ! [[ "$UAT_IMAGE_TAG" =~ ^uat-[0-9a-f]{7,40}$ ]]; then
  echo "[uat] UAT_IMAGE_TAG no cumple el formato esperado: ^uat-[0-9a-f]{7,40}$" >&2
  exit 1
fi

if ! [[ "$UAT_RELEASE_SHA" =~ ^[0-9a-f]{40}$ ]]; then
  echo "[uat] UAT_RELEASE_SHA no cumple el formato esperado: ^[0-9a-f]{40}$" >&2
  exit 1
fi

paso=0
DEPLOY_ID=""
ALEMBIC_HEAD=""
BACKUP_ID=""
PREVIOUS_SHA=""
PREVIOUS_TAG=""
HEALTH=""
SMOKE=""
DEPLOY_RESULT="DEPLOY_FAILED"
HIST=""
COMPOSE=()
FILA_REGISTRADA=0

fallo() {
  local codigo=$?
  set +e
  if [[ "$codigo" == "0" ]]; then
    exit 0
  fi
  if [[ "$FILA_REGISTRADA" == "0" ]]; then
    FILA_REGISTRADA=1
    registrar_fila
    copiar_informes
  fi
  echo "[uat] DEPLOY_FAILED en el paso $paso" >&2
  exit "$codigo"
}

copiar_informes() {
  if [[ -n "$UAT_REPORT_DIR" ]]; then
    mkdir -p "$UAT_REPORT_DIR"
    [[ -f "$UAT_STATE_DIR/manifest.json" ]] && cp "$UAT_STATE_DIR/manifest.json" "$UAT_REPORT_DIR/manifest.json" || true
    [[ -f "$HIST" ]] && cp "$HIST" "$UAT_REPORT_DIR/deployments.tsv" || true
  fi
}

registrar_fila() {
  [[ -n "$HIST" ]] || return 0
  local fecha
  fecha="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$DEPLOY_ID" \
    "$fecha" \
    "$UAT_RELEASE_SHA" \
    "$UAT_IMAGE_TAG" \
    "${ALEMBIC_HEAD:--}" \
    "$DEPLOY_RESULT" \
    "${PREVIOUS_SHA:--}" \
    "${BACKUP_ID:--}" \
    "${HEALTH:--}" \
    "${SMOKE:--}" >> "$HIST"
}

trap fallo EXIT

paso=1
echo "[uat] 1/12 Preflight"
if [[ ! -f "$UAT_ENV_FILE" ]]; then
  echo "[uat] UAT_ENV_FILE no existe: $UAT_ENV_FILE" >&2
  exit 1
fi
permisos_env="$(stat -c %a "$UAT_ENV_FILE")"
if [[ "$permisos_env" != "600" && "$permisos_env" != "400" ]]; then
  echo "[uat] UAT_ENV_FILE debe tener permisos 600 o 400" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$UAT_ENV_FILE"
set +a

for nombre in KONTROL_DB_URL KONTROL_SECRET_KEY KONTROL_MFA_KEYS KONTROL_BACKUP_KEY KONTROL_CORS_ORIGINS UAT_DOMAIN UAT_ACME_EMAIL; do
  if [[ -z "${!nombre:-}" ]]; then
    echo "[uat] Variable obligatoria ausente: $nombre" >&2
    exit 1
  fi
done

if [[ "${KONTROL_ENVIRONMENT:-}" == "prod" ]]; then
  echo "[uat] KONTROL_ENVIRONMENT=prod no está permitido en UAT" >&2
  exit 1
fi

docker compose version >/dev/null

export KONTROL_IMAGE_TAG="$UAT_IMAGE_TAG"
export KONTROL_ENVIRONMENT="uat"

COMPOSE=(docker compose -f compose.yaml -f deploy/uat/compose.uat.yaml --profile proxy)

mkdir -p "$UAT_STATE_DIR"
HIST="$UAT_STATE_DIR/deployments.tsv"
if [[ ! -f "$HIST" ]]; then
  printf 'DEPLOY_ID\tDEPLOY_DATE\tGIT_SHA\tIMAGE_TAG\tALEMBIC_HEAD\tRESULT\tPREVIOUS_SHA\tBACKUP_ID\tHEALTH\tSMOKE\n' > "$HIST"
fi

DEPLOY_ID="$(date -u +%Y%m%dT%H%M%SZ)-${UAT_IMAGE_TAG#uat-}"

while IFS=$'\t' read -r dep_id dep_date git_sha image_tag alembic_head result previous_sha backup_id health smoke; do
  if [[ "$result" == "DEPLOYED" ]]; then
    PREVIOUS_SHA="${git_sha:--}"
    PREVIOUS_TAG="${image_tag:--}"
  fi
done < <(tail -n +2 "$HIST")

PREVIOUS_SHA="${PREVIOUS_SHA:-}"
PREVIOUS_TAG="${PREVIOUS_TAG:-}"

paso=2
echo "[uat] 2/12 Imágenes"
"${COMPOSE[@]}" pull

paso=3
echo "[uat] 3/12 Cabeza de Alembic del árbol"
salida_heads="$(docker run --rm --entrypoint alembic "$KONTROL_IMAGE_REGISTRY/kontrol-backend:$UAT_IMAGE_TAG" heads)"
lineas_head="$(grep '(head)$' <<<"$salida_heads" || true)"
cantidad="$(grep -c '(head)$' <<<"$salida_heads" || true)"
if [[ "$cantidad" != "1" ]]; then
  echo "[uat] Se esperaba exactamente una cabeza de Alembic, se encontraron: $cantidad" >&2
  exit 1
fi
ALEMBIC_HEAD="$(awk '{print $1}' <<<"$lineas_head")"

paso=4
echo "[uat] 4/12 Respaldo previo"
if [[ -z "$PREVIOUS_TAG" ]]; then
  BACKUP_ID="FIRST_DEPLOY_NO_PRIOR_DATA"
else
  en_ejecucion="$(docker inspect -f '{{.State.Running}}' kontrol-api 2>/dev/null || true)"
  if [[ "$en_ejecucion" != "true" ]]; then
    echo "[uat] no hay backend en ejecución para el respaldo previo" >&2
    exit 1
  fi
  archivo_backup="$UAT_STATE_DIR/backup-$DEPLOY_ID.log"
  "${COMPOSE[@]}" exec -T -e KONTROL_BACKUP_KEY backend python -m app.ops.backup create --dest /data/backups > "$archivo_backup"
  BACKUP_ID="$(grep -v '^[[:space:]]*$' "$archivo_backup" | tail -n 1 | head -c 200 | tr -d '\t')"
fi

paso=5
echo "[uat] 5/12 Desplegar"
"${COMPOSE[@]}" up -d

paso=6
echo "[uat] 6/12 Esperar health de los contenedores"
plazo=$((SECONDS + UAT_HEALTH_TIMEOUT))
estado_api=""
estado_web=""
estado_clamd=""
while (( SECONDS < plazo )); do
  estado_api="$(docker inspect -f '{{.State.Health.Status}}' kontrol-api 2>/dev/null || true)"
  estado_web="$(docker inspect -f '{{.State.Health.Status}}' kontrol-web 2>/dev/null || true)"
  estado_clamd="$(docker inspect -f '{{.State.Health.Status}}' kontrol-clamd 2>/dev/null || true)"
  if [[ "$estado_api" == "healthy" && "$estado_web" == "healthy" && "$estado_clamd" == "healthy" ]]; then
    break
  fi
  if [[ "$estado_api" == "unhealthy" || "$estado_web" == "unhealthy" || "$estado_clamd" == "unhealthy" ]]; then
    echo "[uat] Contenedor unhealthy (api=$estado_api, web=$estado_web, clamd=$estado_clamd)" >&2
    exit 1
  fi
  sleep 5
done
if [[ "$estado_api" != "healthy" || "$estado_web" != "healthy" || "$estado_clamd" != "healthy" ]]; then
  echo "[uat] Plazo de health agotado (api=$estado_api, web=$estado_web, clamd=$estado_clamd)" >&2
  exit 1
fi

paso=7
echo "[uat] 7/12 Comprobar la etiqueta de las imágenes en ejecución"
for contenedor in kontrol-api kontrol-web kontrol-clamd; do
  imagen_actual="$(docker inspect -f '{{.Config.Image}}' "$contenedor")"
  if [[ "$imagen_actual" != *":$UAT_IMAGE_TAG" ]]; then
    echo "[uat] $contenedor no ejecuta la etiqueta esperada: $imagen_actual" >&2
    exit 1
  fi
done

paso=8
echo "[uat] 8/12 Base en la cabeza"
salida_current="$("${COMPOSE[@]}" exec -T backend alembic current)"
if ! grep -q "$ALEMBIC_HEAD" <<<"$salida_current"; then
  echo "[uat] La base no está en la cabeza de Alembic esperada" >&2
  exit 1
fi

paso=9
echo "[uat] 9/12 Health público por HTTPS"
python3 deploy/uat/smoke.py --solo-health "https://$UAT_DOMAIN"
HEALTH="PASS"

paso=10
echo "[uat] 10/12 Smoke"
archivo_smoke="$UAT_STATE_DIR/smoke-$DEPLOY_ID.log"
python3 deploy/uat/smoke.py "https://$UAT_DOMAIN" > "$archivo_smoke"
cat "$archivo_smoke"
SMOKE="$(tail -n 1 "$archivo_smoke")"

paso=11
echo "[uat] 11/12 Manifiesto"
UAT_DEPLOY_ID="$DEPLOY_ID" \
UAT_GIT_SHA="$UAT_RELEASE_SHA" \
UAT_IMAGE_TAG="$UAT_IMAGE_TAG" \
UAT_DEPLOYED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
UAT_ALEMBIC_HEAD="$ALEMBIC_HEAD" \
UAT_FRONTEND_IMAGE="$KONTROL_IMAGE_REGISTRY/kontrol-frontend:$UAT_IMAGE_TAG" \
UAT_BACKEND_IMAGE="$KONTROL_IMAGE_REGISTRY/kontrol-backend:$UAT_IMAGE_TAG" \
UAT_CLAMD_IMAGE="$KONTROL_IMAGE_REGISTRY/kontrol-clamd:$UAT_IMAGE_TAG" \
UAT_PREVIOUS_SHA="$PREVIOUS_SHA" \
UAT_BACKUP_ID="$BACKUP_ID" \
UAT_HEALTH="$HEALTH" \
UAT_SMOKE="$SMOKE" \
UAT_STATE_DIR="$UAT_STATE_DIR" \
python3 -c '
import json
import os

manifest = {
    "environment": "UAT",
    "git_sha": os.environ["UAT_GIT_SHA"],
    "image_tag": os.environ["UAT_IMAGE_TAG"],
    "deployed_at": os.environ["UAT_DEPLOYED_AT"],
    "alembic_head": os.environ["UAT_ALEMBIC_HEAD"],
    "frontend_image": os.environ["UAT_FRONTEND_IMAGE"],
    "backend_image": os.environ["UAT_BACKEND_IMAGE"],
    "clamd_image": os.environ["UAT_CLAMD_IMAGE"],
    "previous_sha": os.environ["UAT_PREVIOUS_SHA"],
    "backup_id": os.environ["UAT_BACKUP_ID"],
    "health": os.environ["UAT_HEALTH"],
    "smoke": os.environ["UAT_SMOKE"],
    "deploy_id": os.environ["UAT_DEPLOY_ID"],
}

with open(os.path.join(os.environ["UAT_STATE_DIR"], "manifest.json"), "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=2)
'

DEPLOY_RESULT="DEPLOYED"

paso=12
echo "[uat] 12/12 Registrar el despliegue"
FILA_REGISTRADA=1
registrar_fila
copiar_informes

echo "[uat] DEPLOYED $UAT_IMAGE_TAG $ALEMBIC_HEAD"

trap - EXIT
