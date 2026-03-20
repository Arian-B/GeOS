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
PLYMOUTH_DST="$INCLUDES_DIR/usr/share/plymouth/themes/geos"

mkdir -p "$SYSTEMD_DST" "$AUTOSTART_DST" "$BIN_DST" "$OPT_DST" "$PLYMOUTH_DST"

cp "$SCRIPT_DIR"/systemd/* "$SYSTEMD_DST"/
cp "$SCRIPT_DIR"/xdg-autostart/* "$AUTOSTART_DST"/
cp "$SCRIPT_DIR"/usr-local-bin/* "$BIN_DST"/
cp "$SCRIPT_DIR"/plymouth-theme/* "$PLYMOUTH_DST"/
chmod 755 "$BIN_DST"/geos-launch-gui "$BIN_DST"/geos-demo-exit
chmod 644 "$PLYMOUTH_DST"/geos.plymouth "$PLYMOUTH_DST"/geos.script

rm -rf "$OPT_DST"
mkdir -p "$OPT_DST"

if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '*.pyo' \
    --exclude '*:Zone.Identifier' \
    --exclude 'GEOS_ROADMAP_AND_SESSION_MEMORY.md' \
    --exclude 'roadmap/' \
    --exclude 'logs/' \
    --exclude 'datasets/' \
    --exclude 'updates/' \
    --exclude 'apps/' \
    --exclude 'state/*.flag' \
    --exclude 'state/boot_attempts.json' \
    --exclude 'state/boot_state.json' \
    --exclude 'state/device.json' \
    --exclude 'state/kernel_tuning.json' \
    --exclude 'state/os_state.json' \
    --exclude 'workloads/workload_state.json' \
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
  rm -rf "$OPT_DST/.venv"
  rm -rf "$OPT_DST/roadmap"
  rm -rf "$OPT_DST/logs"
  rm -rf "$OPT_DST/datasets"
  rm -rf "$OPT_DST/updates"
  rm -rf "$OPT_DST/apps"
  rm -rf \
    "$OPT_DST/distro/x86_64-live/live-build/cache" \
    "$OPT_DST/distro/x86_64-live/live-build/chroot" \
    "$OPT_DST/distro/x86_64-live/live-build/binary" \
    "$OPT_DST/distro/x86_64-live/live-build/.build" \
    "$OPT_DST/distro/x86_64-live/live-build/.lock" \
    "$OPT_DST/distro/x86_64-live/live-build/config/includes.chroot/opt/geos"
  rm -f \
    "$OPT_DST/GEOS_ROADMAP_AND_SESSION_MEMORY.md" \
    "$OPT_DST/README.md:Zone.Identifier" \
    "$OPT_DST/state/boot_success.flag" \
    "$OPT_DST/state/boot_attempts.json" \
    "$OPT_DST/state/boot_state.json" \
    "$OPT_DST/state/device.json" \
    "$OPT_DST/state/kernel_tuning.json" \
    "$OPT_DST/state/os_state.json" \
    "$OPT_DST/workloads/workload_state.json"
fi
