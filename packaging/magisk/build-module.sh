#!/usr/bin/env sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
VERSION=${PICOCLAW_MODULE_VERSION:-$(git -C "$ROOT" describe --tags --always --dirty 2>/dev/null || echo dev)}
VERSION_CODE=$(printf '%s' "$VERSION" | tr -cd '0-9' | cut -c1-9)
[ -n "$VERSION_CODE" ] || VERSION_CODE=1
OUT_DIR=$ROOT/dist/magisk
MODULE_DIR=$ROOT/target/magisk/picoclaw
CORE=$ROOT/build/picoclaw-android-arm64
LAUNCHER=$ROOT/build/picoclaw-launcher-android-arm64

if [ ! -x "$CORE" ]; then
  echo "missing executable: $CORE" >&2
  exit 1
fi
if [ ! -x "$LAUNCHER" ]; then
  echo "missing executable: $LAUNCHER" >&2
  exit 1
fi

rm -rf "$MODULE_DIR" "$OUT_DIR"
mkdir -p "$MODULE_DIR/bin" "$MODULE_DIR/webroot" "$OUT_DIR"
if [ -d "$ROOT/packaging/magisk/system" ]; then
  cp -R "$ROOT/packaging/magisk/system" "$MODULE_DIR/"
fi
sed -e "s/@VERSION@/$VERSION/g" -e "s/@VERSION_CODE@/$VERSION_CODE/g" "$ROOT/packaging/magisk/module.prop.in" > "$MODULE_DIR/module.prop"
cp "$ROOT/packaging/magisk/customize.sh" "$ROOT/packaging/magisk/service.sh" "$ROOT/packaging/magisk/uninstall.sh" "$ROOT/packaging/magisk/action.sh" "$MODULE_DIR/"
cp -R "$ROOT/packaging/magisk/webroot/." "$MODULE_DIR/webroot/"
cp "$ROOT/packaging/magisk/bin/picoclawctl" "$ROOT/packaging/magisk/bin/picoclaw-termux" "$ROOT/packaging/magisk/bin/picoclawctl-termux" "$MODULE_DIR/bin/"
cp "$CORE" "$MODULE_DIR/bin/picoclaw"
cp "$LAUNCHER" "$MODULE_DIR/bin/picoclaw-launcher"
chmod 0755 "$MODULE_DIR/customize.sh" "$MODULE_DIR/service.sh" "$MODULE_DIR/uninstall.sh" "$MODULE_DIR/action.sh" "$MODULE_DIR/bin/"*
( cd "$MODULE_DIR" && zip -r9 "$OUT_DIR/picoclaw-magisk.zip" . )
echo "$OUT_DIR/picoclaw-magisk.zip"
