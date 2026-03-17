# GeOS x86_64 Live USB Plan

Purpose:
- build a faculty-demo GeOS live image that boots from a USB pendrive on x86_64 laptops/desktops
- present GeOS as a dedicated operating system session rather than a host OS app

Reality check:
- a true bootable USB OS does not launch as a normal installer-style app inside an already-running Windows or macOS desktop
- the host machine must reboot and boot from the USB device via the firmware boot menu
- for demo polish, GeOS itself can present a retro installer/walkthrough aesthetic after boot

Recommended demo flow:
1. insert GeOS USB
2. reboot the laptop
3. choose the GeOS USB from the firmware boot menu
4. system boots into the GeOS live session automatically
5. GeOS shows a retro first-run / setup-wizard style screen after login
6. to leave GeOS, shut down or reboot and remove the USB, then boot the native OS normally

Packaging direction:
- base build path: Debian `live-build`
- session model: autologin user + lightweight desktop/session launcher
- GeOS backend managed by `systemd`
- GeOS GUI launched as a user-session autostart or kiosk entrypoint

Current build note (2026-03-17):
- with `--bootloader grub`, the legacy `live-build` toolchain on Ubuntu can fail when asked to produce `--binary-images iso-hybrid`
- default is now `--binary-images iso`; you can override if needed:
  - `sudo env GEOS_LB_BINARY_IMAGES=iso-hybrid bash distro/x86_64-live/build.sh`

Current contents:
- `SERVICE_MAP.md`
  defines the first-pass OS service graph
- `systemd/`
  contains first-pass systemd units and target
- `usr-local-bin/`
  contains startup helper scripts intended for `/usr/local/bin`
- `xdg-autostart/`
  contains the GUI autostart desktop entry
- `preflight.sh`
  checks whether the local machine has the tools needed to build the live image

Builder prerequisites (Ubuntu/Debian):
- run `bash distro/x86_64-live/preflight.sh` and install any missing tools
- typical install command on Ubuntu:
  - `sudo apt-get update && sudo apt-get install -y live-build debootstrap xorriso squashfs-tools rsync syslinux-utils`

Install/layout assumptions for this first pass:
- project payload installed under `/opt/geos`
- virtual environment under `/opt/geos/.venv`
- GUI launched with `GEOS_MANAGED_BY_SYSTEMD=1`
- backend services started by `geos-demo.target`

Open build tasks after this scaffold:
- create the actual Debian live-build tree
- decide exact package list for desktop/session manager
- add branding assets, splash, wallpaper, and retro setup-wizard UI
- add image build script that stages these units/files into the live image
