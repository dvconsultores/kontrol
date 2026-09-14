#!/usr/bin/env bash
# KONTROL - instala el temporizador del planificador de plataforma (Spec 047 · ADR-D0-015).
# Uno por instalación de cliente (R-D0-15-9). El intervalo es operacional y
# obligatorio: ningún manejador depende de él (R-D0-15-10).
# Re-ejecutar con bash aunque se invoque con sh (sh/dash no soporta bashisms).
if [ -z "${BASH_VERSION:-}" ]; then
  exec bash "$0" "$@"
fi
set -euo pipefail

INTERVAL="${KONTROL_SCHEDULER_INTERVAL:?KONTROL_SCHEDULER_INTERVAL es obligatoria (formato systemd, p. ej. 5min)}"
INSTANCE="${KONTROL_INSTANCE:?KONTROL_INSTANCE es obligatoria: identifica la instalación de este cliente}"
DIR="$(cd "$(dirname "$0")/.." && pwd)"
PLANTILLAS="$DIR/scripts/scheduler"
DESTINO="${KONTROL_SYSTEMD_DIR:-/etc/systemd/system}"

render() {
  sed -e "s|@INTERVAL@|$INTERVAL|g" -e "s|@INSTANCE@|$INSTANCE|g" -e "s|@KONTROL_DIR@|$DIR|g" "$1"
}

render "$PLANTILLAS/kontrol-scheduler.service" > "$DESTINO/kontrol-scheduler-$INSTANCE.service"
render "$PLANTILLAS/kontrol-scheduler.timer" > "$DESTINO/kontrol-scheduler-$INSTANCE.timer"

# Con un destino alternativo (pruebas, empaquetado) solo se renderiza.
if [ -z "${KONTROL_SYSTEMD_DIR:-}" ]; then
  systemctl daemon-reload
  systemctl enable --now "kontrol-scheduler-$INSTANCE.timer"
fi
echo "kontrol-scheduler-$INSTANCE.timer · $INTERVAL"
