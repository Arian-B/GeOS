# GeOS — Current Technical Understanding
> Updated for the active repo scope on 2026-04-23

## 1. What GeOS Is

GeOS is currently a Python-based smart farming runtime and interface stack built around a Linux-oriented control model.

The active implementation includes:
- a PySide6 fullscreen shell
- a multi-process runtime launched as local services
- a LightGBM policy model for energy-mode decisions
- simulated agricultural workloads and sensors
- update/recovery scaffolding
- local workflow, metrics, and REPL interfaces

What it is not currently:
- an active ISO-building project
- an active Debian live-build project
- a VM-boot demo pipeline

Packaging and image-building are deferred for now.

## 2. High-Level Architecture

```text
GUI Shell
  -> reads state/os_state.json

Energy Controller
  -> reads sensors + system telemetry
  -> builds rolling features
  -> runs LightGBM policy inference
  -> applies safety rules / manual overrides
  -> writes shared OS state

Telemetry Collector
  -> logs labeled runtime data

Workload Manager
  -> starts/stops sensor, irrigation, camera, analytics workloads

Interfaces
  -> workflow HTTP API
  -> metrics HTTP API
  -> local REPL server
```

## 3. Core Runtime Modules

### `core_os/energy_controller.py`
- main control loop
- reads sensors, CPU, memory, load, hour, and network state
- augments control/workload context
- builds rolling policy features
- applies ML decision, manual override, and safety guard
- writes `state/os_state.json`

### `core_os/energy_modes.py`
- defines `ENERGY_SAVER`, `BALANCED`, and `PERFORMANCE`
- provides base thresholds used by the safety layer

### `core_os/kernel_interface.py`
- applies governor/swappiness tuning where Linux sysfs/procfs hooks exist
- gracefully skips unsupported platforms

### `core_os/boot_manager.py`
- boot success tracking
- safe mode handling
- recovery-state coordination
- update slot boot handling

### `core_os/update_manager.py`
- A/B-style slot staging
- protected-path enforcement
- optional SHA256 and HMAC verification

## 4. ML Understanding

GeOS uses a LightGBM-based policy model with rolling telemetry features.

Current feature contract:
- 7 numeric base signals with current, rolling average, and delta
- hour plus cyclical encoding
- control and workload context flags
- workload count features
- low/dry/high streak features

Total active feature count:
- 45 features

ML runtime behavior:
- predict best mode
- expose confidence
- expose top contributing features when available
- keep hard safety rules outside the model

Training/inference stack:
- `ml_engine/policy_features.py`
- `ml_engine/dataset_builder.py`
- `ml_engine/train_policy_model.py`
- `ml_engine/lightgbm_policy.py`
- `ml_engine/auto_trainer.py`

## 5. GUI Understanding

The GUI is a fullscreen PySide6 shell with grouped navigation and app-style pages.

Main pages include:
- overview
- sensors
- control
- advisor
- alerts
- updates
- maintenance
- task monitor
- water manager
- power center
- device/settings

There are also utility pages such as:
- clock
- calculator
- notes
- weather
- calendar
- reports
- help

## 6. Shared Runtime State

Important files:
- `control/control.json` for operator intent and workload toggles
- `state/os_state.json` for current system state
- `workloads/workload_config.json` for per-mode workload behavior
- `workloads/workload_state.json` for actual workload activity
- `datasets/telemetry_log.jsonl` for raw telemetry history

The current design is intentionally simple but file-based coordination remains one of the main implementation risks.

## 7. Active Priorities

Current priorities are:
- improve interface quality
- make user-facing language clearer
- harden service/runtime behavior
- reduce fragile state coordination issues
- keep ML outputs understandable in the UI

## 8. Explicit Scope Note

The repository no longer includes the old Debian ISO / VMware implementation path.

If deployment packaging returns later, it should be designed as a fresh effort from the then-current runtime rather than by reviving deleted image-build scaffolding.
