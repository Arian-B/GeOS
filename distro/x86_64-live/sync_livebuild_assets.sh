#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd)
LIVEBUILD_DIR="$SCRIPT_DIR/live-build"
INCLUDES_DIR="$LIVEBUILD_DIR/config/includes.chroot"
SYSTEMD_DST="$INCLUDES_DIR/etc/systemd/system"
AUTOSTART_DST="$INCLUDES_DIR/etc/xdg/autostart"
BIN_DST="$INCLUDES_DIR/usr/local/bin"
OPT_DST="$INCLUDES_DIR/opt/geos"

mkdir -p "$SYSTEMD_DST" "$AUTOSTART_DST" "$BIN_DST" "$OPT_DST"

cp "$SCRIPT_DIR"/systemd/* "$SYSTEMD_DST"/
cp "$SCRIPT_DIR"/xdg-autostart/* "$AUTOSTART_DST"/
cp "$SCRIPT_DIR"/usr-local-bin/* "$BIN_DST"/
chmod 755 "$BIN_DST"/geos-launch-gui "$BIN_DST"/geos-demo-exit

rm -rf "$OPT_DST"
mkdir -p "$OPT_DST"

if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'distro/x86_64-live/live-build/cache' \
    --exclude 'distro/x86_64-live/live-build/chroot' \
    --exclude 'distro/x86_64-live/live-build/binary' \
    --exclude 'distro/x86_64-live/live-build/.build' \
    --exclude 'distro/x86_64-live/live-build/.lock' \
    --exclude 'distro/x86_64-live/live-build/config/includes.chroot/opt/geos' \
    "$REPO_ROOT"/ "$OPT_DST"/
else
  cp -a "$REPO_ROOT"/. "$OPT_DST"/
  rm -rf "$OPT_DST/.git"
  rm -rf \
    "$OPT_DST/distro/x86_64-live/live-build/cache" \
    "$OPT_DST/distro/x86_64-live/live-build/chroot" \
    "$OPT_DST/distro/x86_64-live/live-build/binary" \
    "$OPT_DST/distro/x86_64-live/live-build/.build" \
    "$OPT_DST/distro/x86_64-live/live-build/.lock" \
    "$OPT_DST/distro/x86_64-live/live-build/config/includes.chroot/opt/geos"
fi
