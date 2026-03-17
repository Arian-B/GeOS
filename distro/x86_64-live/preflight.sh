#!/bin/sh
set -eu

missing=0

check_cmd() {
  if command -v "$1" >/dev/null 2>&1; then
    printf 'OK      %s\n' "$1"
  else
    printf 'MISSING %s\n' "$1"
    missing=1
  fi
}

check_cmd_optional() {
  if command -v "$1" >/dev/null 2>&1; then
    printf 'OK      %s\n' "$1"
  else
    printf 'OPTION  %s\n' "$1"
  fi
}

echo "GeOS x86_64 live-build preflight"
echo

check_cmd lb
check_cmd debootstrap
check_cmd xorriso
check_cmd mksquashfs
check_cmd_optional isohybrid
check_cmd rsync

echo
echo "Workspace checks"
if [ -d "$(dirname "$0")/live-build/config" ]; then
  echo "OK      live-build config tree present"
else
  echo "MISSING live-build config tree"
  missing=1
fi

if [ -f "$(dirname "$0")/build.sh" ]; then
  echo "OK      build helper present"
else
  echo "MISSING build helper"
  missing=1
fi

echo
if [ "$missing" -ne 0 ]; then
  echo "Preflight failed."
  exit 1
fi

echo "Preflight passed."
