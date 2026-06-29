#!/system/bin/sh
MODDIR=${0%/*}
BASE=/data/adb/picoclaw
LOGDIR=$BASE/logs
ENABLE=$BASE/enable
BIN=$MODDIR/bin/picoclaw
LAUNCHER=$MODDIR/bin/picoclaw-launcher
CONFIG=$BASE/config.json
LAUNCHER_CONFIG=$BASE/launcher-config.json
SERVICE_PID=$BASE/service.pid
LAUNCHER_PID=$BASE/launcher.pid
UPSTREAM_PID=$BASE/.picoclaw.pid
LOCKDIR=$BASE/service.lock
SERVICE_LOG=$LOGDIR/service.log
LAUNCHER_LOG=$LOGDIR/launcher.log
GATEWAY_LOG=$LOGDIR/gateway.log
LAUNCHER_HOST=${PICOCLAW_LAUNCHER_HOST:-0.0.0.0}
LAUNCHER_PORT=${PICOCLAW_LAUNCHER_PORT:-18800}

mkdir -p "$LOGDIR" "$BASE/workspace" "$BASE/tmp"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$SERVICE_LOG"; }
pid_alive() { [ -n "$1" ] && kill -0 "$1" 2>/dev/null; }
pid_from_file() { [ -f "$1" ] && sed -n '1p' "$1"; }
pid_from_json() { [ -f "$1" ] && sed -n 's/.*"PID"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$1" | head -n 1; }

kill_pid_file() {
  pid=$(pid_from_file "$1" 2>/dev/null || true)
  [ -n "$pid" ] && [ "$pid" != "$$" ] && kill "$pid" 2>/dev/null || true
}

kill_upstream_gateway() {
  pid=$(pid_from_json "$UPSTREAM_PID" 2>/dev/null || true)
  [ -n "$pid" ] && [ "$pid" != "$$" ] && kill "$pid" 2>/dev/null || true
}

acquire_lock() {
  if mkdir "$LOCKDIR" 2>/dev/null; then return 0; fi
  old_pid=$(pid_from_file "$SERVICE_PID" 2>/dev/null || true)
  if pid_alive "$old_pid"; then
    log "service already running pid=$old_pid"
    exit 0
  fi
  rm -rf "$LOCKDIR"
  mkdir "$LOCKDIR" 2>/dev/null || { log "cannot acquire service lock"; exit 1; }
}

cleanup() {
  kill_pid_file "$LAUNCHER_PID"
  kill_upstream_gateway
  rm -f "$SERVICE_PID" "$LAUNCHER_PID" "$UPSTREAM_PID"
  rmdir "$LOCKDIR" 2>/dev/null || true
}

trim_log() {
  file=$1
  [ -f "$file" ] || return 0
  size=$(wc -c < "$file" 2>/dev/null || echo 0)
  [ "$size" -le 1048576 ] && return 0
  tail -c 524288 "$file" > "$file.tmp" 2>/dev/null && mv "$file.tmp" "$file"
}

if [ "${PICOCLAW_SKIP_BOOT_WAIT:-0}" != "1" ]; then
  while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 5; done
  sleep 20
fi

acquire_lock
echo $$ > "$SERVICE_PID"
trap cleanup EXIT INT TERM
log "service started"

if [ ! -f "$ENABLE" ]; then log "disabled: $ENABLE missing"; exit 0; fi
[ -x "$BIN" ] || { log "missing binary: $BIN"; exit 1; }
[ -x "$LAUNCHER" ] || { log "missing launcher: $LAUNCHER"; exit 1; }

export HOME=$BASE
export PICOCLAW_HOME=$BASE
export PICOCLAW_CONFIG=$CONFIG
export PICOCLAW_BINARY=$BIN
export TMPDIR=$BASE/tmp
export PATH=/data/data/com.termux/files/home/bin:/data/data/com.termux/files/usr/bin:/system/bin:/system/xbin:/data/adb/ksu/bin:$PATH
unset PICOCLAW_DASHBOARD_NO_AUTH

if [ ! -f "$LAUNCHER_CONFIG" ]; then
  cat > "$LAUNCHER_CONFIG" <<'JSON'
{
  "port": 18800,
  "public": true,
  "allow_localhost_bypass": true
}
JSON
  chmod 0600 "$LAUNCHER_CONFIG"
fi

[ -f "$CONFIG" ] || log "config missing; run: picoclawctl onboard"
fail_count=0
while [ -f "$ENABLE" ]; do
  trim_log "$SERVICE_LOG"; trim_log "$LAUNCHER_LOG"; trim_log "$GATEWAY_LOG"
  launcher_pid=$(pid_from_file "$LAUNCHER_PID" 2>/dev/null || true)
  if ! pid_alive "$launcher_pid"; then
    log "starting dashboard on $LAUNCHER_HOST:$LAUNCHER_PORT"
    "$LAUNCHER" -console -no-browser -host "$LAUNCHER_HOST" -port "$LAUNCHER_PORT" "$LAUNCHER_CONFIG" >> "$LAUNCHER_LOG" 2>&1 &
    echo $! > "$LAUNCHER_PID"
    sleep 5
    if pid_alive "$(pid_from_file "$LAUNCHER_PID" 2>/dev/null || true)"; then
      fail_count=0
    else
      fail_count=$((fail_count + 1))
    fi
  fi
  if [ "$fail_count" -gt 0 ]; then
    delay=$((5 * fail_count))
    [ "$delay" -gt 60 ] && delay=60
  else
    delay=10
  fi
  sleep "$delay"
done

log "service disabled; exiting"
