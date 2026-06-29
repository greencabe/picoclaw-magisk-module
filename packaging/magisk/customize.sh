#!/system/bin/sh
MODDIR=${MODPATH:-$(pwd)}
BASE=/data/adb/picoclaw

ui_print "- PicoClaw"
ui_print "- Target: Android arm64 / Magisk / KernelSU / APatch"

ARCH_VALUE="${ARCH:-$(getprop ro.product.cpu.abi 2>/dev/null)}"
case "$ARCH_VALUE" in
  *arm64*|*aarch64*) ;;
  *)
    ui_print "! Unsupported ABI: $ARCH_VALUE"
    abort "PicoClaw module needs arm64-v8a/aarch64."
    ;;
esac

for required in picoclaw picoclaw-launcher picoclawctl picoclaw-termux picoclawctl-termux; do
  [ -f "$MODDIR/bin/$required" ] || abort "Missing executable: bin/$required"
done
chmod 0755 "$MODDIR/bin/picoclaw" "$MODDIR/bin/picoclaw-launcher" "$MODDIR/bin/picoclawctl" "$MODDIR/bin/picoclaw-termux" "$MODDIR/bin/picoclawctl-termux"

mkdir -p "$BASE/logs" "$BASE/workspace" "$BASE/tmp"
chmod 0700 "$BASE" "$BASE/logs" "$BASE/workspace" "$BASE/tmp"
[ ! -f "$BASE/config.json" ] || chmod 0600 "$BASE/config.json"
[ ! -f "$BASE/launcher-config.json" ] || chmod 0600 "$BASE/launcher-config.json"
[ -f "$BASE/enable" ] || touch "$BASE/enable"

TERMUX_HOME=/data/data/com.termux/files/home
if [ -d "$TERMUX_HOME" ]; then
  mkdir -p "$TERMUX_HOME/bin"
  cp -f "$MODDIR/bin/picoclaw-termux" "$TERMUX_HOME/bin/picoclaw"
  cp -f "$MODDIR/bin/picoclawctl-termux" "$TERMUX_HOME/bin/picoclawctl"
  chmod 0755 "$TERMUX_HOME/bin/picoclaw" "$TERMUX_HOME/bin/picoclawctl"
  ui_print "- Termux command: ~/bin/picoclaw"
  ui_print "- Termux control: ~/bin/picoclawctl"
fi

ui_print "- Data dir: $BASE"
ui_print "- Dashboard: http://127.0.0.1:18800"
ui_print "- Logs: $BASE/logs/service.log"
ui_print "- Run setup after install: picoclawctl onboard"
