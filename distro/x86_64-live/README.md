# GeOS Debian Live Build

This is the current x86_64 demo-image path for GeOS.

It builds a Debian `live-build` ISO intended for:
- VMware Workstation boot testing
- laptop USB boot testing
- faculty/demo validation before the Raspberry Pi image path is finalized

## What This Build Does

- builds an `amd64` Debian live ISO
- stages the current GeOS repo into `/opt/geos` inside the image
- creates a local Python virtual environment at `/opt/geos/.venv`
- installs the runtime Python dependencies needed by GeOS
- configures `LightDM` autologin into an `Openbox` session
- launches GeOS automatically in fullscreen through the existing GUI entrypoint

## Host Requirements

Install Debian live-build tooling on the build host:

```bash
sudo apt-get update
sudo apt-get install -y live-build rsync xorriso squashfs-tools
```

## Build

From the GeOS repo root:

```bash
sudo bash distro/x86_64-live/build.sh
```

The script prints the generated ISO path at the end.

## Expected Runtime Flow

1. Debian live boot starts
2. LightDM autologins the `geos` user
3. Openbox starts
4. `/usr/local/bin/geos-launch-gui` launches GeOS
5. The GeOS shell opens fullscreen on the active display

## Post-Boot Check

Inside the live session, run:

```bash
geos-demo-health
```

This checks the expected GeOS background processes, local API endpoints, and the recent GUI session log.

## Notes

- This is the current Debian demo path, not the final Raspberry Pi production path.
- The image is designed to work in VMware Workstation and on a normal x86_64 laptop.
- If the GUI path fails during boot, check `/opt/geos/logs/gui-session.log` inside the live session.
