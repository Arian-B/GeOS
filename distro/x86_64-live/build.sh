#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
DISTRO_DIR="$ROOT_DIR/distro/x86_64-live"
LB_DIR="$DISTRO_DIR/live-build"

if [[ "${EUID}" -ne 0 ]]; then
  echo "This build must run as root."
  echo "Use: sudo bash distro/x86_64-live/build.sh"
  exit 1
fi

for cmd in lb rsync; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required host tool: $cmd"
    exit 1
  fi
done

mkdir -p "$LB_DIR"
cd "$LB_DIR"

lb clean --purge || true

bash "$DISTRO_DIR/sync_livebuild_assets.sh"

lb config \
  --mode debian \
  --distribution bookworm \
  --architectures amd64 \
  --binary-images iso-hybrid \
  --debian-installer none \
  --archive-areas "main contrib non-free non-free-firmware" \
  --system live \
  --bootappend-live "boot=live components username=geos hostname=geos-live quiet splash" \
  --initsystem systemd

lb build

ISO_PATH="$(find "$LB_DIR" -maxdepth 1 -type f -name '*.iso' | head -n 1)"
if [[ -n "$ISO_PATH" ]]; then
  echo "GeOS ISO built at: $ISO_PATH"
else
  echo "Build completed, but no ISO was found automatically in $LB_DIR"
fi
