#!/bin/bash
# Away mode for a MacBook: keep the Mac awake on battery for a few hours with the display
# off, so the bot keeps answering while you are out. The lid must stay open: closing it
# puts the Mac to sleep whatever this script does.
#
# Usage: deploy/macos/away.sh [hours]   (default 8; whole hours)
#        deploy/macos/away.sh stop      (back home: let the Mac sleep normally again)
set -euo pipefail

PID_FILE="${TMPDIR:-/tmp}/speech-to-sheets-away.pid"
SERVICE="gui/$(id -u)/local.speech-to-sheets"

stop_away() {
  if [ -f "$PID_FILE" ] && kill "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Away mode off: the Mac sleeps normally again."
  else
    echo "Away mode was not on."
  fi
  rm -f "$PID_FILE"
}

if [ "${1:-}" = "stop" ]; then
  stop_away
  exit 0
fi

hours="${1:-8}"
case "$hours" in
  '' | *[!0-9]* | 0) echo "Usage: $0 [hours] | stop" >&2 && exit 2 ;;
esac

if ! launchctl print "$SERVICE" >/dev/null 2>&1; then
  echo "The bot service is not running; start it first: deploy/macos/service.sh start" >&2
  exit 1
fi
[ -f "$PID_FILE" ] && stop_away >/dev/null

# -i keeps the system awake but lets the display sleep; it ends by itself after -t seconds.
nohup caffeinate -i -t $((hours * 3600)) >/dev/null 2>&1 &
echo $! >"$PID_FILE"

pmset -g batt | grep -o '[0-9]*%.*' | head -1 | sed 's/^/Battery: /' || true
if [ "$(pmset -g | awk '/lowpowermode/ {print $2}')" != "1" ]; then
  echo "Tip: Low Power Mode saves more battery. Turn it on in System Settings > Battery."
fi
echo "Away mode on for $hours hours. Leave the lid open. Back home: $0 stop"
sleep 2  # let the message be read before the screen goes dark
pmset displaysleepnow
