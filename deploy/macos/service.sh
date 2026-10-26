#!/bin/bash
# Run speech-to-sheets as a macOS service (a launchd agent): it starts when you log in and
# starts again if it stops. It runs a copy of this checkout, so editing the code here
# changes nothing until you run `install` again.
#
# Usage: deploy/macos/service.sh install|start|stop|restart|status|logs|uninstall
set -euo pipefail

LABEL="local.speech-to-sheets"
REPO="$(cd "$(dirname "$0")/../.." && pwd)"
DATA_DIR="${SPEECH_TO_SHEETS_HOME:-$HOME/.config/speech-to-sheets}"
APP_DIR="$HOME/.local/share/speech-to-sheets"
LOG="$HOME/Library/Logs/speech-to-sheets/bot.log"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
SERVICE="gui/$(id -u)/$LABEL"

install_app() {
  for file in config.yaml .env; do
    if [ ! -f "$DATA_DIR/$file" ]; then
      echo "Missing $DATA_DIR/$file. Put config.yaml and .env there first (see the README)." >&2
      exit 1
    fi
  done
  command -v uv >/dev/null || { echo "uv not found. Install it: brew install uv" >&2; exit 1; }
  version="$(git -C "$REPO" describe --always --dirty 2>/dev/null || echo "this checkout")"
  echo "Installing $version into $APP_DIR"
  (cd "$REPO" && UV_PROJECT_ENVIRONMENT="$APP_DIR/venv" uv sync --locked --no-dev \
    --no-editable --reinstall-package speech-to-sheets --quiet)
  chmod 700 "$DATA_DIR"
  chmod 600 "$DATA_DIR/.env"
  mkdir -p "$(dirname "$LOG")" "$(dirname "$PLIST")"
  sed -e "s|__LABEL__|$LABEL|" -e "s|__PROGRAM__|$APP_DIR/venv/bin/speech-to-sheets|" \
    -e "s|__DATA_DIR__|$DATA_DIR|" -e "s|__LOG__|$LOG|g" \
    "$REPO/deploy/macos/speech-to-sheets.plist" >"$PLIST"
  plutil -lint -s "$PLIST"
}

is_loaded() { launchctl print "$SERVICE" >/dev/null 2>&1; }

stop() {
  if is_loaded; then launchctl bootout "$SERVICE" && echo "Stopped."; else echo "Not running."; fi
}

start() {
  [ -f "$PLIST" ] || { echo "Not installed. Run: $0 install" >&2; exit 1; }
  if is_loaded; then echo "Already running. Log: $LOG"; return; fi
  from=$(($([ -f "$LOG" ] && wc -l <"$LOG" || echo 0) + 1))
  for _ in 1 2 3 4 5; do  # right after a stop, launchd may need a moment
    launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null && break
    sleep 1
  done
  echo "Started. Waiting for the startup checks (up to 90 seconds)..."
  for _ in $(seq 90); do
    sleep 1
    output="$(tail -n "+$from" "$LOG" 2>/dev/null || true)"
    if grep -q "Bolt app is running" <<<"$output"; then
      echo "Running. Log: $LOG"
      return
    fi
    if grep -q "Not started:" <<<"$output"; then
      sed -n '/Not started:/,$p' <<<"$output" >&2
      launchctl bootout "$SERVICE" 2>/dev/null || true
      echo "Stopped it so it does not retry every minute. Fix the above, then: $0 start" >&2
      exit 1
    fi
  done
  echo "Still starting after 90 seconds. Watch the log: $0 logs" >&2
}

status() {
  if is_loaded; then
    launchctl print "$SERVICE" | grep -E '^\s*(state|pid|last exit code) =' || true
  else
    echo "Not running."
  fi
  if [ -f "$LOG" ]; then echo "Last log lines:" && tail -n 5 "$LOG"; fi
}

case "${1:-}" in
  install) install_app && stop >/dev/null && start ;;
  start) start ;;
  stop) stop ;;
  restart) stop >/dev/null && start ;;
  status) status ;;
  logs) tail -n 50 -f "$LOG" ;;
  uninstall)
    stop
    rm -f "$PLIST"
    echo "Uninstalled. Kept your data in $DATA_DIR and the app copy in $APP_DIR." ;;
  *)
    echo "Usage: $0 install|start|stop|restart|status|logs|uninstall" >&2
    exit 2 ;;
esac
