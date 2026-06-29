#!/system/bin/sh
BASE=/data/adb/picoclaw
kill_from_file() { [ -f "$1" ] && pid=$(sed -n '1p' "$1") && [ -n "$pid" ] && kill "$pid" 2>/dev/null || true; }
kill_from_file "$BASE/launcher.pid"
kill_from_file "$BASE/service.pid"
pid=$(sed -n 's/.*"PID"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p' "$BASE/.picoclaw.pid" 2>/dev/null | head -n 1)
[ -n "$pid" ] && kill "$pid" 2>/dev/null || true
rm -f /data/data/com.termux/files/home/bin/picoclaw /data/data/com.termux/files/home/bin/picoclawctl
