#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
LIVEBUILD_DIR="$SCRIPT_DIR/live-build"

GEOS_LB_BOOTLOADER=${GEOS_LB_BOOTLOADER:-grub}
GEOS_LB_BINARY_IMAGES=${GEOS_LB_BINARY_IMAGES:-iso}

if ! command -v lb >/dev/null 2>&1; then
  echo "Error: Debian live-build ('lb') is not installed." >&2
  echo "Install live-build on the build machine, then rerun this script." >&2
  exit 1
fi

if [ "$GEOS_LB_BINARY_IMAGES" = "iso-hybrid" ] && ! command -v isohybrid >/dev/null 2>&1; then
  echo "Error: 'isohybrid' is not installed (required for --binary-images iso-hybrid)." >&2
  echo "On Ubuntu/Debian, install it with: sudo apt install syslinux-utils" >&2
  exit 1
fi

"$SCRIPT_DIR/sync_livebuild_assets.sh"

cd "$LIVEBUILD_DIR"
lb clean --purge || true
lb config noauto \
  --mode debian \
  --distribution bookworm \
  --architectures amd64 \
  --archive-areas "main contrib non-free non-free-firmware" \
  --security false \
  --firmware-chroot false \
  --firmware-binary false \
  --linux-flavours amd64 \
  --linux-packages "linux-image" \
  --memtest none \
  --bootloader "$GEOS_LB_BOOTLOADER" \
  --parent-mirror-bootstrap "http://deb.debian.org/debian/" \
  --parent-mirror-chroot "http://deb.debian.org/debian/" \
  --parent-mirror-binary "http://deb.debian.org/debian/" \
  --binary-images "$GEOS_LB_BINARY_IMAGES" \
  --debian-installer false
lb build
