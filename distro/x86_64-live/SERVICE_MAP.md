# GeOS Service Map

Goal:
- replace ad hoc GUI-spawned processes with explicit OS boot services

Core boot chain:
1. `geos-boot-manager.service`
   initializes boot state, safe-mode policy, update/provisioning checks
2. `geos-energy-controller.service`
   primary runtime controller; writes current mode, ML output, and system state
3. `geos-workload-manager.service`
   manages simulated workloads based on control state
4. `geos-telemetry.service`
   records telemetry snapshots and labeled training history
5. `geos-resource-daemon.service`
   applies mode-driven resource policy changes

Support services:
- `geos-update-watcher.service`
  stages incoming update bundles
- `geos-workflow-api.service`
  HTTP workflow/provisioning/control API on port `8080`
- `geos-repl.service`
  local REPL server on port `5050`
- `geos-metrics.service`
  local metrics/health endpoint on port `8090`

Session/UI service:
- GUI should not own backend lifecycle in the distro image
- backend is booted by `systemd`
- GUI is launched separately in the autologin desktop session

Recommended boot ordering:
- `boot-manager`
- `energy-controller`
- `workload-manager`
- `telemetry`
- `resource-daemon`
- support APIs/servers
- GUI session autostart

Filesystem assumptions for live image:
- code: `/opt/geos`
- python env: `/opt/geos/.venv`
- mutable runtime state:
  - `/opt/geos/state`
  - `/opt/geos/logs`
  - `/opt/geos/datasets`
  - `/opt/geos/control`

Demo-mode environment knobs:
- `GEOS_MANAGED_BY_SYSTEMD=1`
  prevents the GUI from spawning duplicate backend services
- `GEOS_DISABLE_AUTO_TRAINER=1`
  recommended for stable live demo boots unless retraining is intentionally being shown

Important UX note:
- the desired “classic installer dialog” feel should happen after GeOS boots
- it should be implemented as a GeOS first-run wizard / retro setup screen
- it is not the same thing as booting the USB from inside Windows/macOS
