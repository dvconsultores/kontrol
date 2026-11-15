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
UAT_SIMULATE_CANDIDATE_FAILURE="${UAT_SIMULATE_CANDIDATE_FAILURE:-0}"
UAT_CANDIDATE_PORT="${UAT_CANDIDATE_PORT:-18081}"

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
BACKUP_ID="-"
VALIDATION_BACKUP_ID="-"
INSTALLATION_ID=""
CANDIDATE_VALIDATION=""
PREVIOUS_SHA=""
PREVIOUS_TAG=""
HEALTH=""
SMOKE=""
DEPLOY_RESULT="DEPLOY_FAILED"
FAILED_STAGE="-"
HIST=""
COMPOSE=()
CAND=()
FILA_REGISTRADA=0
CAND_ACTIVA=0
ETAPA="PREFLIGHT"
VAL_PATH=""

fallo() {
  local codigo=$?
  set +e
  if [[ "$codigo" == "0" ]]; then
    exit 0
  fi
  if [[ "$CAND_ACTIVA" == "1" ]]; then
    docker compose -p kontrol-cand -f deploy/uat/compose.candidate.yaml down -v --remove-orphans >/dev/null 2>&1 || true
    CAND_ACTIVA=0
  fi
  if [[ "$ETAPA" == "CANDIDATE" && "$CANDIDATE_VALIDATION" != "FAILED_SIMULATED" ]]; then
    CANDIDATE_VALIDATION="FAILED"
  fi
  if [[ "$FILA_REGISTRADA" == "0" ]]; then
    FILA_REGISTRADA=1
    FAILED_STAGE="${ETAPA}"
    registrar_fila
    copiar_informes
  fi
  if [[ "$ETAPA" == "CANDIDATE" ]]; then
    echo "[uat] DEPLOY_FAILED en el paso $paso (candidato); green $PREVIOUS_SHA sigue atendiendo" >&2
  elif [[ "$ETAPA" == "CUTOVER" ]]; then
    echo "[uat] DEPLOY_FAILED en el corte (paso $paso): recuperación manual con el respaldo $BACKUP_ID y la etiqueta $PREVIOUS_TAG (runbook §11)" >&2
  else
    echo "[uat] DEPLOY_FAILED en el paso $paso" >&2
  fi
  exit "$codigo"
}

copiar_informes() {
  if [[ -n "$UAT_REPORT_DIR" ]]; then
    mkdir -p "$UAT_REPORT_DIR"
    [[ -f "$UAT_STATE_DIR/manifest.json" ]] && cp "$UAT_STATE_DIR/manifest.json" "$UAT_REPORT_DIR/manifest.json" || true
    [[ -f "$HIST" ]] && cp "$HIST" "$UAT_REPORT_DIR/deployments.tsv" || true
    find "$UAT_STATE_DIR" -maxdepth 1 -type f -name '*.sanitized.log' -exec cp {} "$UAT_REPORT_DIR/" \; 2>/dev/null || true
  fi
}

registrar_fila() {
  [[ -n "$HIST" ]] || return 0
  local fecha
  fecha="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
    "$DEPLOY_ID" \
    "$fecha" \
    "$UAT_RELEASE_SHA" \
    "$UAT_IMAGE_TAG" \
    "${ALEMBIC_HEAD:--}" \
    "$DEPLOY_RESULT" \
    "$FAILED_STAGE" \
    "${PREVIOUS_SHA:--}" \
    "${PREVIOUS_TAG:--}" \
    "${BACKUP_ID:--}" \
    "${HEALTH:--}" \
    "${SMOKE:--}" \
    "${CANDIDATE_VALIDATION:--}" \
    "${VALIDATION_BACKUP_ID:--}" >> "$HIST"
}

ejecutar_smoke() {
  local base="$1"
  local etiqueta="$2"
  local rc=0
  local completo="$UAT_STATE_DIR/smoke-$etiqueta-$DEPLOY_ID.log"
  local sanitizado="$UAT_STATE_DIR/smoke-$etiqueta-$DEPLOY_ID.sanitized.log"

  set +e
  python3 deploy/uat/smoke.py "$base" > "$completo" 2>&1
  rc=$?
  set -e

  python3 -c '
import os
import re
import sys

entrada = sys.argv[1]
salida = sys.argv[2]

with open(entrada, "r", encoding="utf-8") as fh:
    texto = fh.read()

nombres = [
    "KONTROL_DB_URL",
    "KONTROL_SECRET_KEY",
    "KONTROL_MFA_KEYS",
    "KONTROL_BACKUP_KEY",
    "UAT_SMOKE_PASSWORD",
    "UAT_SMOKE_TOTP_SECRET",
    "UAT_CAND_DB_PASSWORD",
]

for nombre in nombres:
    valor = os.environ.get(nombre, "")
    if valor:
        texto = texto.replace(valor, "***")

texto = re.sub(r"(?i)bearer\s+[A-Za-z0-9._-]+", "***", texto)

with open(salida, "w", encoding="utf-8") as fh:
    fh.write(texto)
' "$completo" "$sanitizado"

  echo "::group::smoke $etiqueta"
  cat "$sanitizado"
  echo "::endgroup::"

  if [[ "$rc" != "0" ]]; then
    local ultima
    ultima="$(tail -n 1 "$sanitizado")"
    echo "::error::smoke $etiqueta: $ultima"
  fi

  if [[ -n "$UAT_REPORT_DIR" ]]; then
    mkdir -p "$UAT_REPORT_DIR"
    cp "$sanitizado" "$UAT_REPORT_DIR/" || true
  fi

  SMOKE="$(tail -n 1 "$sanitizado")"
  return "$rc"
}

trap fallo EXIT

ETAPA="PREFLIGHT"
paso=1
echo "[uat] 1/16 Preflight"
if [[ ! -f "$UAT_ENV_FILE" ]]; then
  echo "[uat] UAT_ENV_FILE no existe: $UAT_ENV_FILE" >&2
  exit 1
fi
permisos_env="$(stat -c %a "$UAT_ENV_FILE")"
if [[ "$permisos_env" != "600" && "$permisos_env" != "400" ]]; then
  echo "[uat] UAT_ENV_FILE debe tener permisos 600 o 400" >&2
  exit 1
fi
if [[ ! -f deploy/uat/compose.candidate.yaml ]]; then
  echo "[uat] Falta deploy/uat/compose.candidate.yaml" >&2
  exit 1
fi
if [[ ! -f deploy/uat/Caddyfile.candidate ]]; then
  echo "[uat] Falta deploy/uat/Caddyfile.candidate" >&2
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
export UAT_CAND_DB_PASSWORD="$(python3 -c 'import secrets;print(secrets.token_urlsafe(24))')"
export UAT_CANDIDATE_PORT="${UAT_CANDIDATE_PORT}"

COMPOSE=(docker compose -f compose.yaml -f deploy/uat/compose.uat.yaml --profile proxy)
CAND=(docker compose -p kontrol-cand -f deploy/uat/compose.candidate.yaml)

mkdir -p "$UAT_STATE_DIR"
HIST="$UAT_STATE_DIR/deployments.tsv"
if [[ ! -f "$HIST" ]]; then
  printf 'DEPLOY_ID\tDEPLOY_DATE\tGIT_SHA\tIMAGE_TAG\tALEMBIC_HEAD\tRESULT\tFAILED_STAGE\tPREVIOUS_SHA\tPREVIOUS_TAG\tBACKUP_ID\tHEALTH\tSMOKE\tCANDIDATE_VALIDATION\tVALIDATION_BACKUP_ID\n' > "$HIST"
fi

DEPLOY_ID="$(date -u +%Y%m%dT%H%M%SZ)-${UAT_IMAGE_TAG#uat-}"

while IFS=$'\t' read -r dep_id dep_date git_sha image_tag alembic_head result failed_stage previous_sha previous_tag backup_id health smoke candidate_validation validation_backup_id; do
  if [[ "$result" == "DEPLOYED" ]]; then
    PREVIOUS_SHA="${git_sha:--}"
    PREVIOUS_TAG="${image_tag:--}"
  fi
done < <(tail -n +2 "$HIST")

PREVIOUS_SHA="${PREVIOUS_SHA:-}"
PREVIOUS_TAG="${PREVIOUS_TAG:-}"

if [[ -n "$PREVIOUS_TAG" ]]; then
  export UAT_GREEN_TAG="$PREVIOUS_TAG"
  en_ejecucion="$(docker inspect -f '{{.State.Running}}' kontrol-api 2>/dev/null || true)"
  if [[ "$en_ejecucion" != "true" ]]; then
    echo "[uat] Deriva de estado: kontrol-api no está en ejecución con green presente" >&2
    exit 1
  fi
  imagen_actual="$(docker inspect -f '{{.Config.Image}}' kontrol-api 2>/dev/null || true)"
  if [[ "$imagen_actual" != *":$PREVIOUS_TAG" ]]; then
    echo "[uat] Deriva de estado: kontrol-api no ejecuta la etiqueta green $PREVIOUS_TAG" >&2
    exit 1
  fi
fi

if [[ -n "$PREVIOUS_TAG" ]]; then
  volumenes_cand="$("${CAND[@]}" config --volumes)"
  if [[ -z "$volumenes_cand" ]]; then
    echo "[uat] La pila candidata no declara volúmenes" >&2
    exit 1
  fi
  while IFS= read -r vol; do
    [[ -z "$vol" ]] && continue
    if [[ "$vol" != kontrol-cand-* && "$vol" != "uat-backups" ]]; then
      echo "[uat] Volumen no permitido en la pila candidata: $vol" >&2
      exit 1
    fi
  done <<<"$volumenes_cand"
fi

paso=2
echo "[uat] 2/16 Imágenes"
"${COMPOSE[@]}" pull

paso=3
echo "[uat] 3/16 Cabeza de Alembic del árbol"
salida_heads="$(docker run --rm --entrypoint alembic "$KONTROL_IMAGE_REGISTRY/kontrol-backend:$UAT_IMAGE_TAG" heads)"
lineas_head="$(grep '(head)$' <<<"$salida_heads" || true)"
cantidad="$(grep -c '(head)$' <<<"$salida_heads" || true)"
if [[ "$cantidad" != "1" ]]; then
  echo "[uat] Se esperaba exactamente una cabeza de Alembic, se encontraron: $cantidad" >&2
  exit 1
fi
ALEMBIC_HEAD="$(awk '{print $1}' <<<"$lineas_head")"

if [[ -z "$PREVIOUS_TAG" ]]; then
  CANDIDATE_VALIDATION="FIRST_DEPLOY_NOT_APPLICABLE"
  VALIDATION_BACKUP_ID="-"
  echo "[uat] 4-10/16 sin green: no hay copia que validar"
else
  ETAPA="CANDIDATE"

  paso=4
  echo "[uat] 4/16 Respaldo de validación desde green"
  archivo_backup_val="$UAT_STATE_DIR/backup-val-$DEPLOY_ID.log"
  "${COMPOSE[@]}" exec -T -e KONTROL_BACKUP_KEY backend python -m app.ops.backup create --dest /data/backups > "$archivo_backup_val"
  VALIDATION_BACKUP_ID="$(tail -n 1 "$archivo_backup_val" | python3 -c 'import json,sys; print(json.load(sys.stdin)["backup_id"])')"
  VAL_PATH="$(tail -n 1 "$archivo_backup_val" | python3 -c 'import json,sys; print(json.load(sys.stdin)["path"])')"

  paso=5
  echo "[uat] 5/16 Verificación del respaldo de validación"
  salida_verify="$("${COMPOSE[@]}" exec -T -e KONTROL_BACKUP_KEY backend python -m app.ops.backup verify "$VAL_PATH")"
  INSTALLATION_ID="$(tail -n 1 <<<"$salida_verify" | python3 -c 'import json,sys; print(json.load(sys.stdin)["installation_id"])')"

  paso=6
  echo "[uat] 6/16 Pila candidata: base de datos"
  docker compose -p kontrol-cand -f deploy/uat/compose.candidate.yaml down -v --remove-orphans >/dev/null 2>&1 || true
  "${CAND[@]}" pull
  "${CAND[@]}" up -d db
  CAND_ACTIVA=1
  plazo=$((SECONDS + UAT_HEALTH_TIMEOUT))
  estado_db=""
  while (( SECONDS < plazo )); do
    estado_db="$(docker inspect -f '{{.State.Health.Status}}' kontrol-cand-db 2>/dev/null || true)"
    if [[ "$estado_db" == "healthy" ]]; then
      break
    fi
    if [[ "$estado_db" == "unhealthy" ]]; then
      echo "[uat] kontrol-cand-db unhealthy" >&2
      exit 1
    fi
    sleep 5
  done
  if [[ "$estado_db" != "healthy" ]]; then
    echo "[uat] Plazo de health agotado para kontrol-cand-db" >&2
    exit 1
  fi

  paso=7
  echo "[uat] 7/16 Restauración en la copia temporal"
  archivo_restore="$UAT_STATE_DIR/restore-$DEPLOY_ID.log"
  set +e
  "${CAND[@]}" run --rm -T restore restore "$VAL_PATH" --expected-installation-id "$INSTALLATION_ID" > "$archivo_restore" 2>&1
  rc_restore=$?
  set -e
  if [[ "$rc_restore" != "0" ]]; then
    echo "[uat] Fallo en la restauración temporal (rc=$rc_restore)" >&2
    tail -n 1 "$archivo_restore" >&2 || true
    exit 1
  fi

  paso=8
  echo "[uat] 8/16 Arrancar el candidato"
  "${CAND[@]}" up -d backend frontend clamd proxy
  plazo=$((SECONDS + UAT_HEALTH_TIMEOUT))
  estado_api=""
  estado_web=""
  estado_clamd=""
  while (( SECONDS < plazo )); do
    estado_api="$(docker inspect -f '{{.State.Health.Status}}' kontrol-cand-api 2>/dev/null || true)"
    estado_web="$(docker inspect -f '{{.State.Health.Status}}' kontrol-cand-web 2>/dev/null || true)"
    estado_clamd="$(docker inspect -f '{{.State.Health.Status}}' kontrol-cand-clamd 2>/dev/null || true)"
    if [[ "$estado_api" == "healthy" && "$estado_web" == "healthy" && "$estado_clamd" == "healthy" ]]; then
      break
    fi
    if [[ "$estado_api" == "unhealthy" || "$estado_web" == "unhealthy" || "$estado_clamd" == "unhealthy" ]]; then
      echo "[uat] Candidato unhealthy (api=$estado_api, web=$estado_web, clamd=$estado_clamd)" >&2
      exit 1
    fi
    sleep 5
  done
  if [[ "$estado_api" != "healthy" || "$estado_web" != "healthy" || "$estado_clamd" != "healthy" ]]; then
    echo "[uat] Plazo de health agotado para el candidato (api=$estado_api, web=$estado_web, clamd=$estado_clamd)" >&2
    exit 1
  fi

  salida_current_cand="$("${CAND[@]}" exec -T backend alembic current)"
  if ! grep -q "$ALEMBIC_HEAD" <<<"$salida_current_cand"; then
    echo "[uat] El candidato no migró la copia a la cabeza esperada" >&2
    exit 1
  fi

  paso=9
  echo "[uat] 9/16 Smoke del candidato"
  if [[ "$UAT_SIMULATE_CANDIDATE_FAILURE" == "1" ]]; then
    CANDIDATE_VALIDATION="FAILED_SIMULATED"
    echo "[uat] fallo simulado de candidato (prueba obligatoria §10)" >&2
    exit 1
  fi
  if ! ejecutar_smoke "http://127.0.0.1:$UAT_CANDIDATE_PORT" "candidato"; then
    CANDIDATE_VALIDATION="FAILED"
    echo "[uat] Smoke del candidato falló" >&2
    exit 1
  fi
  CANDIDATE_VALIDATION="PASS"

  paso=10
  echo "[uat] 10/16 Eliminar la pila candidata"
  docker compose -p kontrol-cand -f deploy/uat/compose.candidate.yaml down -v --remove-orphans >/dev/null 2>&1 || true
  CAND_ACTIVA=0
fi

ETAPA="CUTOVER"

paso=11
echo "[uat] 11/16 Respaldo previo al corte"
export KONTROL_IMAGE_TAG="$UAT_IMAGE_TAG"
if [[ -z "$PREVIOUS_TAG" ]]; then
  BACKUP_ID="FIRST_DEPLOY_NO_PRIOR_DATA"
else
  archivo_backup="$UAT_STATE_DIR/backup-$DEPLOY_ID.log"
  "${COMPOSE[@]}" exec -T -e KONTROL_BACKUP_KEY backend python -m app.ops.backup create --dest /data/backups > "$archivo_backup"
  BACKUP_ID="$(tail -n 1 "$archivo_backup" | python3 -c 'import json,sys; print(json.load(sys.stdin)["backup_id"])')"
fi

paso=12
echo "[uat] 12/16 Desplegar"
"${COMPOSE[@]}" up -d

paso=13
echo "[uat] 13/16 Esperar health de los contenedores"
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

for contenedor in kontrol-api kontrol-web kontrol-clamd; do
  imagen_actual="$(docker inspect -f '{{.Config.Image}}' "$contenedor")"
  if [[ "$imagen_actual" != *":$UAT_IMAGE_TAG" ]]; then
    echo "[uat] $contenedor no ejecuta la etiqueta esperada: $imagen_actual" >&2
    exit 1
  fi
done

salida_current="$("${COMPOSE[@]}" exec -T backend alembic current)"
if ! grep -q "$ALEMBIC_HEAD" <<<"$salida_current"; then
  echo "[uat] La base no está en la cabeza de Alembic esperada" >&2
  exit 1
fi

paso=14
echo "[uat] 14/16 Health público HTTPS y smoke"
python3 deploy/uat/smoke.py --solo-health "https://$UAT_DOMAIN"
HEALTH="PASS"
if ! ejecutar_smoke "https://$UAT_DOMAIN" "corte"; then
  echo "[uat] Smoke del corte falló" >&2
  exit 1
fi

paso=15
echo "[uat] 15/16 Manifiesto"
UAT_DEPLOY_ID="$DEPLOY_ID" \
UAT_GIT_SHA="$UAT_RELEASE_SHA" \
UAT_IMAGE_TAG="$UAT_IMAGE_TAG" \
UAT_DEPLOYED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
UAT_ALEMBIC_HEAD="$ALEMBIC_HEAD" \
UAT_FRONTEND_IMAGE="$KONTROL_IMAGE_REGISTRY/kontrol-frontend:$UAT_IMAGE_TAG" \
UAT_BACKEND_IMAGE="$KONTROL_IMAGE_REGISTRY/kontrol-backend:$UAT_IMAGE_TAG" \
UAT_CLAMD_IMAGE="$KONTROL_IMAGE_REGISTRY/kontrol-clamd:$UAT_IMAGE_TAG" \
UAT_PREVIOUS_SHA="$PREVIOUS_SHA" \
UAT_PREVIOUS_TAG="${PREVIOUS_TAG:-}" \
UAT_BACKUP_ID="$BACKUP_ID" \
UAT_HEALTH="$HEALTH" \
UAT_SMOKE="$SMOKE" \
UAT_CANDIDATE_VALIDATION="$CANDIDATE_VALIDATION" \
UAT_VALIDATION_BACKUP_ID="$VALIDATION_BACKUP_ID" \
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
    "previous_tag": os.environ["UAT_PREVIOUS_TAG"],
    "backup_id": os.environ["UAT_BACKUP_ID"],
    "health": os.environ["UAT_HEALTH"],
    "smoke": os.environ["UAT_SMOKE"],
    "candidate_validation": os.environ["UAT_CANDIDATE_VALIDATION"],
    "validation_backup_id": os.environ["UAT_VALIDATION_BACKUP_ID"],
    "deploy_id": os.environ["UAT_DEPLOY_ID"],
}

with open(os.path.join(os.environ["UAT_STATE_DIR"], "manifest.json"), "w", encoding="utf-8") as fh:
    json.dump(manifest, fh, ensure_ascii=False, indent=2)
'

DEPLOY_RESULT="DEPLOYED"
FAILED_STAGE="-"

paso=16
echo "[uat] 16/16 Registrar el despliegue"
FILA_REGISTRADA=1
registrar_fila
copiar_informes

echo "[uat] DEPLOYED $UAT_IMAGE_TAG $ALEMBIC_HEAD"

trap - EXIT
