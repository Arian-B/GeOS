# live-build Scaffold

This folder is the staging area for a future Debian `live-build` tree.

Intended next steps:
1. run `../preflight.sh`
2. run `../sync_livebuild_assets.sh`
3. run `../build.sh`
4. write the resulting ISO to a USB drive
5. boot the USB from the firmware boot menu

Expected output:
- after `../build.sh` completes, the ISO artifact should appear in this folder as `live-image-*.hybrid.iso`

What is already scaffolded:
- `config/package-lists/geos.list.chroot`
- `config/hooks/normal/0200-geos-system-setup.hook.chroot`
- `config/hooks/normal/0300-geos-openbox-autostart.hook.chroot`
- `config/includes.chroot/`
  receives systemd units, launch helpers, XDG autostart files, and `/opt/geos`

Important:
- booting the resulting USB still requires a reboot and boot-menu selection on the host laptop
- the “classic installer dialog” idea should be implemented as an in-GeOS first-run wizard after boot
- the local builder must have Debian `live-build` tooling installed before `build.sh` can succeed
