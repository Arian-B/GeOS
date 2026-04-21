#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DISTRO_DIR="$ROOT_DIR/distro/x86_64-live"
LB_DIR="$DISTRO_DIR/live-build"
INCLUDES_DIR="$LB_DIR/config/includes.chroot"
GEOS_TARGET="$INCLUDES_DIR/opt/geos"

mkdir -p "$GEOS_TARGET"
rm -rf "$GEOS_TARGET"
mkdir -p "$GEOS_TARGET"

rsync -a --delete \
  --exclude '.git' \
  --exclude '.venv' \
  --exclude '__pycache__' \
  --exclude '*.pyc' \
  --exclude 'logs/*' \
  --exclude 'datasets/*.csv' \
  --exclude 'datasets/*.jsonl' \
  --exclude 'distro/x86_64-live/live-build/cache' \
  --exclude 'distro/x86_64-live/live-build/chroot' \
  --exclude 'distro/x86_64-live/live-build/binary*' \
  --exclude 'distro/x86_64-live/live-build/tmp' \
  "$ROOT_DIR/" "$GEOS_TARGET/"

mkdir -p "$GEOS_TARGET/logs" "$GEOS_TARGET/datasets" "$GEOS_TARGET/updates/incoming"

mkdir -p "$INCLUDES_DIR/usr/local/bin"
cp "$DISTRO_DIR/usr-local-bin/geos-launch-gui" "$INCLUDES_DIR/usr/local/bin/geos-launch-gui"
chmod +x "$INCLUDES_DIR/usr/local/bin/geos-launch-gui"
cp "$DISTRO_DIR/usr-local-bin/geos-demo-health" "$INCLUDES_DIR/usr/local/bin/geos-demo-health"
chmod +x "$INCLUDES_DIR/usr/local/bin/geos-demo-health"
