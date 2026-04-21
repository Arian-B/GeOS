# GeOS — Deep Technical Understanding
> For research paper writing. Last updated: 2026-03-25

---

## 🗒️ Research Paper Session Log

### Session: 2026-03-25 — Major Paper Rewrite (RL → LightGBM)

**What was done this session:**
All key sections of the IEEE research paper were rewritten to replace the old Random Forest + Q-table RL architecture with the current LightGBM-only implementation. Every section was rewritten from scratch with accurate technical content, new equations, and new tables.

| Section | Status | Key Changes |
|---|---|---|
| Abstract | ✅ Done | Removed RL, added LightGBM, 98.53% accuracy, calibration, 45 features |
| I. Introduction | ✅ Done | Humanized, bullet 3 updated to LightGBM policy engine |
| II. Related Work | ✅ Done | Added LightGBM (ke2017) + calibration (niculescu2005) citation paragraphs |
| III. System Architecture | ✅ Done | Subsystem table updated, equations added (safety guard piecewise), RL removed |
| IV. Data Collection & Feature Engineering | ✅ Done | Expanded from 8-feature to full 45-feature contract with rolling window math, streak formulas, feature group table |
| V. ML Policy Formulation | ✅ Done | Entirely new: GBDT ensemble, multiclass softmax, gradient/hessian, split gain, isotonic calibration, SHAP explainability, safety override — LightGBM hyperparameter table added |
| VI. ML-Driven Control Pipeline | ✅ Done | RL arbitration removed, 9-step inference loop, mode lock equation, reason codes, auto-trainer |
| VII. Implementation Details | ✅ Done | RL agent and reward model removed, LightGBM 3-module stack, model registry, services table |
| VIII. Experimental Setup | ✅ Done | Testbed config table, baselines updated (alternative classifiers instead of RL), Brier score added |
| IX. Results & Discussion | ✅ Done | Benchmark comparison table (5 models × 3 metrics), per-class top features, calibration improvement numbers |
| X. Conclusion | ✅ Done | LightGBM-specific, no RL, strong closing |
| XI. Future Enhancements | ✅ Done | Added Yocto/Buildroot Pi image and touchscreen UI as top priorities |
| Acknowledgment | ✅ Done | Added Mrs. R Brindha as faculty mentor |
| Bibliography | ✅ Done | Added ke2017lightgbm and niculescu2005calibration entries |
| Author Block | ✅ Done | Added B.Tech CSE and Assistant Professor designations |

**Tables added this session:**
1. GeOS Subsystems and Functional Roles (Section III)
2. Feature Vector Group Summary — 45 features (Section IV)
3. LightGBM Hyperparameter Table (Section V)
4. GeOS Core Services and Roles (Section VII)
5. Testbed Configuration (Section VIII)
6. Classifier Benchmark — 5 models × 3 metrics (Section IX)

**New biblio entries needed:**
```latex
\bibitem{ke2017lightgbm}
G. Ke et al., "LightGBM: A Highly Efficient Gradient Boosting Decision Tree," NeurIPS 2017.

\bibitem{niculescu2005calibration}
A. Niculescu-Mizil and R. Caruana, "Predicting Good Probabilities with Supervised Learning," ICML 2005.
```

---

## ⏭️ NEXT SESSION TODO (Page Reduction)

**Context:** The paper is currently ~11 pages. IEEE conference papers typically charge extra beyond 6 or 8 pages. Faculty confirmed page reduction is needed. The exact page limit was not confirmed — **ask at start of next session.**

**Page reduction strategy (execute in this order):**

1. **[ ] Confirm page limit** — ask user: is it 6 or 8 pages? And compile current LaTeX to get current page count.
2. **[ ] Remove all "Summary" subsections** — every major section ends with a `\subsection{Summary}` paragraph. These are redundant in a conference paper and together take ~0.5–0.7 pages.
3. **[ ] Merge Section VI into Section V** — "ML-Driven Control Pipeline" (Section VI) is the runtime application of the "ML Policy Formulation" (Section V). Merging saves ~0.5 pages.
4. **[ ] Convert bullet lists to inline prose** — every `\begin{itemize}` block uses 2–3× the vertical space of equivalent prose. Converting the main ones saves ~0.8–1.0 pages.
5. **[ ] Merge short subsections in Section III** — 7 subsections can become 3–4 (e.g., merge Kernel Interaction + Data Path + Service Model into one).
6. **[ ] Shorten Future Enhancements** — reduce from 8 subsections to 4 short paragraphs.
7. **[ ] Merge Dataset Storage Format into Preprocessing** (Section IV) — saves ~0.2 pages.
8. **[ ] Trim verbose opening paragraphs** — each section starts with a 2–3 sentence orientation paragraph that can be cut to 1 sentence.

**Estimated total savings: ~3–3.5 pages** → from 11 to ~7–8 pages.

---

## 1. What GeOS Is

GeOS (Green Embedded Operating System) is a **custom Linux-based operating system distribution** designed for **smart agricultural embedded devices**, specifically targeting **Raspberry Pi** as the final deployment platform. It is **not a Python app pretending to be an OS** — it is a genuine Linux distro with:

- A custom systemd service graph
- A PySide6 touchscreen GUI shell (farmer-facing OS console — like a smartwatch or car dashboard)
- A full LightGBM ML pipeline for adaptive energy management
- Real kernel-level integration (CPU governor, VM swappiness)
- A/B OTA update system with boot-loop protection

### ⚠️ Two-Path Clarification (CRITICAL for paper writing)

| Path | Purpose | Mention in paper? |
|---|---|---|
| **Raspberry Pi (Yocto/Buildroot)** | Final production OS — embedded image for the actual device | ✅ YES — this is what the paper describes |
| **Debian x86_64 live image** | Faculty demo only — allows booting on a laptop temporarily | ❌ NO — do not mention in paper |

**The research paper describes GeOS as if the Raspberry Pi embedded OS is complete.** The Debian demo is a development-time workaround while the Pi hardware is not available yet. The paper's implementation, architecture, and deployment sections should only refer to the Raspberry Pi / Yocto/Buildroot path.

**Final product vision:** A bootable embedded Linux image (built with Yocto or Buildroot) that runs on Raspberry Pi with a touchscreen, giving farmers a dedicated smart farming OS with a touch-controlled interface — similar in UX concept to a car infotainment system or smartwatch OS.

**One-sentence positioning for your paper:**
> "GeOS is an adaptive ML-driven Linux OS distribution for smart farming on embedded devices, where a LightGBM-based policy model dynamically controls system energy modes in response to real-time agricultural telemetry, replacing static power management policies with a data-driven, research-defensible edge inference framework deployed on Raspberry Pi."

---

## 2. High-Level Architecture

```
┌───────────────────────────────────────────────────────────────┐
│                        GeOS OS Shell                          │
│                    (PySide6 GUI, 18 apps)                     │
└─────────────────────────────┬─────────────────────────────────┘
                              │ reads state/os_state.json (polling)
┌─────────────────────────────▼─────────────────────────────────┐
│                    core_os / Energy Controller                 │
│  [ Sensor Read → Feature Build → LightGBM Predict → Mode ]    │
│  [ Safety Guard → Apply Mode → Kernel Tune → Write State ]    │
└────────┬────────────────────┬──────────────────┬──────────────┘
         │                    │                  │
   ┌─────▼──────┐   ┌─────────▼──────┐  ┌───────▼──────────┐
   │  Sensors   │   │  ML Engine     │  │  Kernel Interface │
   │(simulator/ │   │(LightGBM       │  │(/sys/cpufreq,     │
   │ real)      │   │ policy model)  │  │ /proc/swappiness) │
   └────────────┘   └─────────┬──────┘  └──────────────────┘
                              │
                   ┌──────────▼──────────┐
                   │  Telemetry Collector │
                   │  (datasets/          │
                   │  telemetry_log.jsonl)│
                   └─────────────────────┘
                              │
                   ┌──────────▼──────────┐
                   │  Workload Manager   │
                   │  (multiprocess:     │
                   │  sensor/irrigation/ │
                   │  camera/analytics)  │
                   └─────────────────────┘
```

---

## 3. Module-by-Module Breakdown

### 3.1 `core_os/energy_controller.py` — **The Main OS Brain**

This is the central control loop of GeOS. It runs as a background service (`geos-energy-controller.service`) and executes every 0.5–5 seconds (depending on current energy mode).

**Each cycle does this exact sequence:**
1. **Sensor update** — calls `SensorState.update()` + `read()` (soil moisture, temperature, humidity, battery, battery health)
2. **System metrics** — reads `psutil.cpu_percent()`, `getloadavg()`, `virtual_memory().percent`
3. **Time** — injects `datetime.now().hour` into the data dict
4. **Network** — checks connectivity (`is_connected()`)
5. **Alert check** — raises CRITICAL/WARN alerts for thresholds:
   - `soil_moisture < 15` → CRITICAL
   - `temperature > 42` → CRITICAL
   - `battery < 15` → WARN
6. **Control state read** — reads `control/control.json` (mode, workloads, safe_mode flags)
7. **Context augmentation** — adds workload enable/active counts, control mode flags to data dict
8. **Feature build** — passes augmented data to `PolicyFeatureBuilder.add_snapshot()` + `current_features()`
9. **Emergency / Maintenance short-circuit** — if `emergency_shutdown` or `maintenance` is set in control, force ENERGY_SAVER mode and skip ML
10. **`evaluate_control_decision()`** — full ML decision:
    - Reads `current_thresholds()` from saved model metadata
    - Calls `predict_policy(features)` → LightGBM inference
    - Checks manual override (if control mode is MANUAL, use forced mode)
    - Calls `safety_guard()` → hard battery/soil/temperature overrides
    - Applies mode lock (prevents rapid oscillations via `MODE_LOCK_COUNTER`)
    - Returns `new_mode`, `ml_suggested_mode`, `ml_confidence`, `policy_source`, `top_features`, `reason_codes`
11. **Apply mode** — if mode changed, calls `apply_mode()`:
    - Sets OS process niceness (`os.nice()`)
    - Writes `workload_config.json` (adjusts sensor_interval, camera_interval, analytics_intensity)
    - Calls `tune_for_mode()` (kernel CPU governor + swappiness)
    - Logs MODE_CHANGE event
12. **Write state** — writes full state dict to `state/os_state.json` (GUI reads this)
13. **Performance monitoring** — updates per-cycle metrics to `logs/performance_metrics.json`
14. **Sleep** — sleeps for `CURRENT_MODE["sleep_interval"]` (0.5s PERFORMANCE, 2s BALANCED, 5s ENERGY_SAVER)

### 3.2 `core_os/energy_modes.py` — **Three Energy Modes**

| Mode | cpu_nice | sleep_interval | sensor_rate |
|---|---|---|---|
| `ENERGY_SAVER` | +15 (lowest priority) | 5 sec | LOW |
| `BALANCED` | 0 (normal) | 2 sec | MEDIUM |
| `PERFORMANCE` | -5 (highest priority) | 0.5 sec | HIGH |

**Base safety thresholds:**
- `battery_energy_saver = 25%` → force ENERGY_SAVER if battery < 25%
- `soil_performance = 35%` → force PERFORMANCE if soil < 35% (critical irrigation)

These are starting values; the trained model's metadata overrides them with data-derived quantile thresholds from the actual telemetry distribution.

### 3.3 `core_os/kernel_interface.py` — **Real Linux Kernel Integration**

On a real Linux device (Raspberry Pi or the live Debian image), this module directly writes to:
- `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` — CPU frequency governor
- `/proc/sys/vm/swappiness` — VM memory swap aggressiveness

**Per-mode kernel policy:**

| Mode | Governor preference | Swappiness |
|---|---|---|
| ENERGY_SAVER | powersave → ondemand → schedutil → performance | 80 |
| BALANCED | schedutil → ondemand → powersave → performance | 60 |
| PERFORMANCE | performance → schedutil → ondemand → powersave | 30 |

The module gracefully skips tuning if sysfs paths don't exist (Windows/dev environment).

### 3.4 `core_os/boot_manager.py` — **Boot, Safe Mode, Recovery**

Runs as `geos-boot-manager.service`. Implements a **boot-loop protection and safe mode system** similar to embedded firmware update recovery.

**Boot sequence:**
1. Checks if `state/boot_success.flag` exists from the previous run
2. If it does NOT exist → marks a failed boot, increments `boot_attempts.json`
3. Calls `update_manager.handle_boot()` to commit or roll back pending update slot
4. Ensures device provisioning identity exists
5. If `≥ 2 failed boots` OR safe mode flag file present → enters RECOVERY (forces ENERGY_SAVER, disables all workloads)
6. Writes `boot_success.flag` at the end of successful startup
7. Continuously monitors for safe mode toggling at runtime (3-second polling loop)

**Safe mode behavior:** When enabled, it:
- Saves current control state to `safe_mode_restore.json`
- Switches to `MANUAL` mode, forces `ENERGY_SAVER`
- Disables all 4 workloads
- Restores from restore file when safe mode is cleared

### 3.5 `core_os/update_manager.py` — **A/B Update Slots**

Implements an **A/B dual-slot over-the-air update system** inspired by embedded OTA frameworks (similar to Android A/B, Mender, SWUpdate).

**Slot layout:**
```
system/slots/slot_a/    ← current running system files
system/slots/slot_b/    ← staged update files
system/slot_current     ← "a" or "b"
system/slot_pending.json ← pending slot to activate on next boot
```

**Update flow:**
1. Drop a `.zip` update package into `updates/incoming/`
2. `stage_update_with_policy()` verifies SHA256 and/or HMAC signature (policy-controlled)
3. Extracts into the inactive slot (always the other one from current)
4. Writes `slot_pending.json`
5. On next boot, `handle_boot()` checks if previous boot succeeded:
   - If yes → activate the pending slot (write to `slot_current`)
   - If no → roll back to `slot_last_good`
6. Protected paths (core_os, ml_engine, state, etc.) cannot be overwritten by an update package

### 3.6 `sensors/sensor_simulator.py` — **Agricultural Sensor Layer**

The sensor layer is designed as a **hybrid real + simulated** data source:

**Real sources (via psutil):**
- `battery` — `psutil.sensors_battery().percent` (works on laptops, Raspberry Pi with battery HAT)
- `temperature` — `psutil.sensors_temperatures()` (averaged across all sensor readings)

**Simulated with drift (random walk + center pull):**
- `soil_moisture` — range 18–82%, step ±2.4%, center pull 3%
- `humidity` — range 32–88%, step ±3.0%
- `temperature` — range 17–39°C, step ±0.8° (only when no real sensor available)

**Override file:** `sensors/sensor_inputs.json` — write any field here to inject a specific value (useful for demos and testing boundary conditions).

**Workload gate:** If the `sensor` workload is disabled in `control/control.json`, soil/humidity/temperature readings are suppressed (shown as N/A in GUI).

### 3.7 `telemetry/collector.py` — **Dataset Generation Engine**

Runs as `geos-telemetry.service`. Every 2 seconds:
1. Reads `state/os_state.json` (current energy mode, sensor values)
2. Reads `control/control.json` (control mode, workload enable flags)
3. Reads `workloads/workload_state.json` (which workloads are actually active)
4. Collects live `psutil` metrics (CPU%, load_avg, memory%)
5. Writes a single JSONL row to `datasets/telemetry_log.jsonl`

This file is the **raw training data** for the ML pipeline. Every row includes the `os_mode` label, which becomes the supervised training target.

### 3.8 `workloads/workload_manager.py` — **Simulated Agricultural Workloads**

Runs as `geos-workload-manager.service`. Manages 4 independent child processes:

| Workload | Simulates |
|---|---|
| `sensor` | Periodic environmental data collection (soil, humidity, temp, light) |
| `irrigation` | Pump/valve control cycles, moisture tracking |
| `camera` | Image capture intervals, field surveillance |
| `analytics` | Data processing, report generation at variable intensity |

Each workload runs as an independent `multiprocessing.Process`. The manager reads `control/control.json` every second to decide which workloads to start or stop. Uses a file-based lock (`workload_state.lock`) for safe concurrent state writes.

Workload activity density is controlled by `workloads/workload_config.json`, which is rewritten by `energy_controller.py` on every mode switch:

| Mode | sensor_interval | camera_interval | analytics_intensity |
|---|---|---|---|
| ENERGY_SAVER | 5s | 10s | LOW |
| BALANCED | 2s | 5s | MEDIUM |
| PERFORMANCE | 1s | 2s | HIGH |

---

## 4. The Full ML Pipeline

### 4.1 Feature Engineering (`ml_engine/policy_features.py`)

The `PolicyFeatureBuilder` maintains a **rolling window of the last 5 telemetry snapshots** and produces 45 features:

**Per base field × 3 stats (current, rolling mean, delta):**
- `cpu_percent`, `load_avg`, `memory_percent`, `battery`, `soil_moisture`, `temperature`, `humidity`
- → 7 × 3 = 21 features

**Time encoding (cyclical):**
- `hour` (raw), `hour_sin` = sin(2π·hour/24), `hour_cos` = cos(2π·hour/24)
- → 3 features

**Network:**
- `network_online` (binary 0/1)
- → 1 feature

**Context binary (control/workload state):**
- `control_auto`, `control_manual`, `maintenance_enabled`, `safe_mode_enabled`, `emergency_shutdown_enabled`, `irrigation_enabled`, `ventilation_enabled`, `workload_sensor_enabled`, `workload_irrigation_enabled`, `workload_camera_enabled`, `workload_analytics_enabled`
- → 11 features

**Workload counts × 3 stats:**
- `workload_enabled_count`, `workload_active_count`
- → 2 × 3 = 6 features

**Streak features (consecutive cycles meeting a threshold):**
- `battery_low_streak` (battery < 25% for N consecutive cycles)
- `soil_dry_streak` (soil < 35% for N consecutive cycles)
- `temp_high_streak` (temp > 35°C for N consecutive cycles)
- → 3 features

**Total: 45 features**

### 4.2 Training Pipeline (`ml_engine/train_policy_model.py`)

**Data splits:**
- 80% training (of which 20% is held out for calibration)
- 20% test (for final accuracy reporting)
- Label: `os_mode` (ENERGY_SAVER / BALANCED / PERFORMANCE)
- Minimum dataset size: 120 rows

**Pipeline:**
```
SimpleImputer(strategy=median) → LGBMClassifier(multiclass)
```

**LightGBM parameters (tuned via `ml_engine/tune_lightgbm.py`):**
```json
{
  "n_estimators": 300,
  "learning_rate": 0.03,
  "num_leaves": 31,
  "subsample": 0.95,
  "colsample_bytree": 0.8,
  "min_child_samples": 40,
  "force_col_wise": true
}
```

**Confidence calibration:** After training:
- Runs the model on the calibration split
- Collects raw `max(predict_proba())` scores and whether they were correct (binary)
- Fits `IsotonicRegression(y_min=0, y_max=1)` as a calibrator
- Saves to `ml_engine/policy_confidence_calibrator.pkl`
- In runtime, raw confidence is passed through the calibrator

**Data-derived threshold update:** After training, the model:
- Computes the 20th percentile of battery values → new `battery_energy_saver` threshold
- Computes the 35th percentile of soil moisture → new `soil_performance` threshold
- Computes the 85th percentile of temperature → new `temperature_energy_saver` threshold
- Saves these as `recommended_thresholds` in `policy_model.meta.json`
- In runtime, `energy_controller.py` reads these and merges with BASE_THRESHOLDS

**Model versioning:** Every training run produces a versioned copy in `ml_engine/model_registry/` and updates `registry_index.json`.

### 4.3 Inference (`ml_engine/lightgbm_policy.py`)

**`predict_policy(feature_row)` does:**
1. Loads model metadata to confirm `model_type == "LightGBMClassifier"`
2. Builds a DataFrame from the 45-feature dict
3. Calls `model.predict()` → mode name
4. Calls `model.predict_proba()` → raw confidence = `max(proba)`
5. Applies isotonic calibrator if available
6. Extracts **local per-decision explanations** via LightGBM contribution scores (`pred_contrib=True`):
   - Identifies which class block corresponds to the predicted class
   - Ranks features by contribution magnitude for that specific prediction
   - Returns top-3 feature contributions (name, importance, direction)
7. Returns dict with: `mode`, `confidence`, `raw_confidence`, `confidence_source`, `source`, `top_features`

**Fallback chain:** If model file missing → returns DEFAULT_MODE="BALANCED", source="FALLBACK"

### 4.4 Evaluation and Benchmarking

| Script | Purpose |
|---|---|
| `ml_engine/evaluate_policies.py` | Replay accuracy (artifact vs full dataset) + chronological holdout |
| `ml_engine/benchmark_models.py` | Stratified 5-fold CV comparing LightGBM, HistGBM, RandomForest, ExtraTrees, LogisticRegression |
| `ml_engine/ablation_study.py` | Group-level feature ablation (remove feature group, measure accuracy drop) |
| `ml_engine/rolling_backtest.py` | Expanding window temporal backtesting |
| `ml_engine/explainability_report.py` | Class-level + example LightGBM contribution summaries |
| `ml_engine/tune_lightgbm.py` | Randomized hyperparameter search, saves best params |
| `ml_engine/auto_trainer.py` | Background thread — retrains model when telemetry log mtime changes |

**Benchmark results (9,460-row dataset, stratified 5-fold CV):**

| Model | Accuracy | Macro F1 | Balanced Accuracy |
|---|---|---|---|
| **LightGBM** (tuned) | 0.9853 | 0.9663 | **0.9680** ← Winner |
| HistGradientBoosting | 0.9853 | 0.9651 | 0.9680 |
| ExtraTrees | 0.9867 | 0.9672 | 0.9672 |
| RandomForest | 0.9846 | 0.9614 | 0.9605 |
| LogisticRegression | 0.9445 | 0.8578 | 0.8386 |

**Top features from explainability report:**
- `BALANCED`: battery_delta, battery, memory_percent_avg
- `ENERGY_SAVER`: battery, battery_low_streak, hour
- `PERFORMANCE`: control_manual, battery, battery_avg

---

## 5. The GUI Shell (`gui/`)

**Framework:** PySide6 (Qt6 for Python)  
**Theme:** Retro monochrome green on dark background — embedded appliance / farm console aesthetic  
**Window:** 1240×720px, minimum 920×620px

### 5.1 App Registry (18 apps in 2 groups)

**System group (core OS modules):**
| App | Maps to | Purpose |
|---|---|---|
| Overview | `home.py` | Farm status, live mode, alerts, recommendations |
| Field Monitor | `sensors.py` | Soil, temperature, humidity, sensor health |
| Control Center | `control.py` | Manual overrides, workload toggles, safe mode |
| Advisor | `ai.py` | LightGBM explanation, confidence, top features |
| Updates | `updates_page.py` | A/B slot status, staged packages |
| Maintenance | `maintenance_page.py` | Safe mode, restart/reboot/shutdown actions |
| Power Center | `power_center.py` | Energy mode, battery, power-saving behavior |
| Water Manager | `water_manager.py` | Irrigation state, moisture recovery |
| Alerts | `alerts.py` | Event log, critical/warning history |
| Task Monitor | `task_monitor.py` | Service health, CPU/memory/load |
| Device | `settings.py` | Hardware, OS version, kernel, network, provisioning |

**Apps group (utility apps):**
| App | Purpose |
|---|---|
| Clock | World clocks, stopwatch, alarm |
| Calculator | Normal + scientific modes |
| Notes | Multiple farm notes + reminders |
| Weather | Live local weather + animated conditions |
| Calendar | Events, reminders, Gregorian calendar |
| Reports | Snapshots of operating history |
| Help | On-device quick reference |

### 5.2 Shell Architecture

**`MainWindow.py`:**
- Left: `NavBar` (tree-grouped launcher with ellipsis labels)
- Top header: animated `mode_pill` (color-coded), `status_pill` (FIELD ONLINE/OFFLINE), live clock
- Center: `QStackedWidget` containing all page widgets
- Header timer fires every 1000ms to refresh mode/status from `os_state.json`
- Page transitions: 260ms parallel `QPropertyAnimation` (slide + fade via `QParallelAnimationGroup`)
- Smart timer management: pauses timers of inactive pages, resumes on reactivation

**State consumption:** Every page reads `state/os_state.json` independently on a timer. No shared Python objects — all inter-process communication is via JSON files.

---

## 6. Inter-Process Communication (IPC) Architecture

GeOS runs as **multiple independent processes** communicating via JSON files:

| File | Written by | Read by | Purpose |
|---|---|---|---|
| `state/os_state.json` | energy_controller | GUI (all pages) | Current mode, ML outputs, sensor data |
| `control/control.json` | GUI (control page) | energy_controller, workload_manager, sensor_simulator, boot_manager | User commands and workload enables |
| `workloads/workload_config.json` | energy_controller | Individual workload processes | Activity rates per energy mode |
| `workloads/workload_state.json` | workload_manager | energy_controller, GUI | Which workloads are actually running |
| `logs/os_events.log` | energy_controller, notifications | GUI (alerts page) | Alert history |
| `datasets/telemetry_log.jsonl` | telemetry/collector | ML training pipeline | Raw labeled training data |
| `ml_engine/policy_model.pkl` | train_policy_model | lightgbm_policy (inference) | Trained model artifact |
| `ml_engine/policy_model.meta.json` | train_policy_model | lightgbm_policy, GUI | Model type, thresholds, accuracy, features |

---

## 7. OS Packaging

### 7.1 Final Product — Raspberry Pi Embedded Image (FOR PAPER)

**This is what the research paper describes.** GeOS's final delivery is a purpose-built embedded Linux image for Raspberry Pi with a touchscreen interface.

**Build tool:** Yocto Project or Buildroot (TBD — both are being evaluated)  
**Target hardware:** Raspberry Pi 4 / 5 (ARM64)  
**UI paradigm:** Touchscreen-first — similar to a car infotainment system or smartwatch OS  
**Distribution type:** Custom embedded Linux distro (not a standard Debian/Ubuntu derivative)

**Target image composition:**
- Minimal Linux kernel (ARM64) with GPIO, I2C, SPI, camera support
- PySide6 touchscreen GUI shell (fullscreen, no desktop environment needed)
- All GeOS Python services as systemd units
- LightGBM model and ML pipeline baked into the image
- Direct hardware sensor integration: I2C soil sensors, GPIO irrigation valves, camera HAT, battery HAT
- A/B OTA update slots for field updates without downtime
- Read-only root filesystem with overlay for resilience

**Boot → UI flow (target):**
1. U-Boot → Linux kernel → systemd
2. GeOS services start (energy controller, workload manager, telemetry, boot manager)
3. PySide6 GUI launches directly on framebuffer/DRM — no display manager needed
4. Farmer interacts via touchscreen — no keyboard/mouse required

### 7.2 Development Demo — Debian x86_64 (NOT FOR PAPER)

**This exists only for faculty demos while Raspberry Pi hardware is not available.**

**Build tool:** Debian `live-build` with GRUB  
**Target:** `iso-hybrid` x86_64 USB-bootable image (boots on any laptop)  
**Location:** `distro/x86_64-live/`  
**Status:** Black screen issue in QEMU — actively being debugged  

> ⚠️ Do NOT reference the Debian demo path in the research paper. The paper should only describe the Raspberry Pi / Yocto/Buildroot embedded OS path as if it is the implemented system.

**Systemd service graph (same for both paths):**
```
geos-demo.target
    ├── geos-boot-manager.service
    ├── geos-energy-controller.service
    ├── geos-workload-manager.service
    ├── geos-telemetry.service
    ├── geos-resource-daemon.service
    ├── geos-update-watcher.service
    ├── geos-workflow-api.service (port 8080)
    ├── geos-repl.service (port 9000)
    └── geos-metrics.service (port 8090)
```

---

## 8. Hardware Integration

On a real Linux device (Raspberry Pi or x86_64 live boot):

| Integration | Implementation |
|---|---|
| CPU frequency scaling | Writes to `/sys/devices/system/cpu/cpu*/cpufreq/scaling_governor` |
| VM swappiness | Writes to `/proc/sys/vm/swappiness` |
| Battery level | `psutil.sensors_battery()` |
| Temperature | `psutil.sensors_temperatures()` |
| Network connectivity | Socket-based connectivity probe (`core_os/network.py`) |
| Process priority | `os.nice()` per energy mode |

On Windows/dev: all sysfs writes gracefully skip, psutil provides battery/temperature from the host when available.

---

## 9. Research Paper Positioning

### 9.1 Core Research Contributions

1. **ML-driven OS energy management for edge/embedded agriculture:**
   - Rather than static governors or simple rule-based thresholds, GeOS uses a trained LightGBM classifier that learns from real operational telemetry
   - The model generalizes across operating modes, workload states, time-of-day, and sensor conditions

2. **Temporal feature engineering for edge resource control:**
   - Rolling averages, deltas, and streak counters over a 5-cycle window
   - Cyclical time encoding (sin/cos) avoids day-boundary discontinuities
   - Context augmentation (workload state, control mode) makes the model situation-aware

3. **Calibrated confidence for embedded decision transparency:**
   - Isotonic regression calibrator improves Brier scores
   - Runtime provides both raw and calibrated confidence to the user (GUI Advisor page)
   - Local per-decision LightGBM contribution scores explain each prediction

4. **Safety-ML coexistence (rule-outside-model pattern):**
   - Hard safety constraints (battery < 10% → ENERGY_SAVER, soil < threshold → PERFORMANCE) always override ML outputs
   - This is a deliberate architectural pattern: ML proposes, safety layer disposes
   - Mode lock prevents unstable rapid oscillations

5. **Research-defensible model selection:**
   - Tabular ML literature (NeurIPS 2022, 2023, 2024) supports GBDT methods for structured telemetry
   - Honest benchmarking via stratified 5-fold CV (not simple train/test split)
   - LightGBM outperforms HistGBM, RandomForest, ExtraTrees, LogisticRegression on GeOS data

6. **Full OS integration (not just a Python app):**
   - Real Linux distro with systemd, Plymouth, LightDM, Openbox
   - Kernel-level integration (CPU governor, swappiness)
   - A/B slots OTA update system with SHA256/HMAC verification
   - Boot-loop protection and automatic safe mode recovery

### 9.2 Key Arguments for the Paper

**Why LightGBM over alternatives:**
- GeOS data = structured tabular telemetry (~45 features, all numeric/binary)
- Recent literature shows GBDT remains state-of-the-art for non-graph structured edge data
- LightGBM specifically: fastest training, best inference latency, feature importance built-in
- On GeOS data: LightGBM ranked 1st in stratified 5-fold CV across 5 models

**Why not GNN:**
- GeOS telemetry is not naturally graph-structured
- GNN would be appropriate if GeOS modeled farm zone adjacency, irrigation topology, or multi-node sensor networks — future work direction

**Why not RL:**
- Early GeOS prototype used a Q-table RL agent — removed because it was toy-grade
- Q-table RL is hard to explain, hard to evaluate offline, and unsafe without large exploration budgets
- LightGBM trains on labeled history (os_mode) and is directly evaluable and explainable

**Why this is an OS, not a Python app:**
- Real `systemd` service graph, not `subprocess.Popen()`
- Real CPU governor tuning via `/sys/`
- Real A/B OTA update system with slot management
- Real bootable image (Debian live ISO)
- Designed for Raspberry Pi hardware integration path

### 9.3 Current System Metrics (for paper)

| Metric | Value |
|---|---|
| Training dataset size | 9,460 rows |
| Feature count | 45 |
| Model type | `LightGBMClassifier` (multiclass, 3 classes) |
| Training accuracy | ~98.7–98.9% (validation split) |
| CV accuracy (stratified 5-fold) | 98.53% |
| CV Macro F1 | 96.63% |
| CV Balanced Accuracy | 96.80% |
| Brier score (raw) | 0.008518 |
| Brier score (calibrated) | 0.007409 |
| Inference speed | ~0.036 ms/row (LightGBM) |
| Python unit tests | 20 passing |
| Supported energy modes | 3 (ENERGY_SAVER, BALANCED, PERFORMANCE) |
| Simulated workloads | 4 (sensor, irrigation, camera, analytics) |
| GUI apps | 18 (11 System + 7 utility Apps) |

---

## 10. Future Work (per roadmap)

1. **Yocto/Buildroot Raspberry Pi image** — transition from Debian demo to proper embedded distro
2. **Real hardware sensor integration** — I2C soil sensors, GPIO irrigation valves, camera HAT, battery HAT on Pi
3. **Touchscreen UI polish** — optimise PySide6 GUI for finger touch targets and small display form factor
4. **Read-only rootfs with overlay** — production embedded OS resilience pattern
5. **CatBoost and TabPFN benchmarks** — additional research baselines
6. **GNN extension** — if farm zone spatial topology is modelled (multi-zone adjacency)
7. **Larger telemetry dataset** — more operating mode variation for stronger temporal generalization
8. **Multi-node deployment** — per-zone sensor nodes, centralized policy aggregation
9. **Field testing** — real agricultural environment validation on deployed Pi units

---

## 11. File Reference Quick-Map

| File | Role |
|---|---|
| `core_os/energy_controller.py` | Main OS loop, ML decision, mode application |
| `core_os/energy_modes.py` | 3 mode definitions + base thresholds |
| `core_os/kernel_interface.py` | /sys/ CPU governor + swappiness tuning |
| `core_os/boot_manager.py` | Boot recovery, safe mode, A/B slot boot |
| `core_os/update_manager.py` | A/B OTA update staging, SHA256/HMAC verification |
| `core_os/notifications.py` | Alert generation + persistent event log reads |
| `core_os/performance_monitor.py` | Performance metric tracking |
| `core_os/provisioning.py` | Device identity (hostname, device ID, label) |
| `core_os/service_supervisor.py` | Backend service lifecycle manager |
| `sensors/sensor_simulator.py` | Hybrid real+simulated sensor data |
| `telemetry/collector.py` | JSONL dataset logger (2s interval) |
| `workloads/workload_manager.py` | Multiprocess workload lifecycle manager |
| `workloads/{sensor,irrigation,camera,analytics}_workload.py` | Individual workload implementations |
| `ml_engine/policy_features.py` | 45-feature engineering contract |
| `ml_engine/lightgbm_policy.py` | LightGBM inference + local explanations |
| `ml_engine/train_policy_model.py` | Full training pipeline + calibration + registry |
| `ml_engine/dataset_builder.py` | Builds telemetry.csv from telemetry_log.jsonl |
| `ml_engine/benchmark_models.py` | Stratified CV multi-model benchmark |
| `ml_engine/evaluate_policies.py` | Replay + holdout evaluation |
| `ml_engine/ablation_study.py` | Feature group ablation |
| `ml_engine/rolling_backtest.py` | Temporal backtest |
| `ml_engine/tune_lightgbm.py` | Hyperparameter search |
| `ml_engine/explainability_report.py` | Class-level LightGBM contribution reports |
| `ml_engine/auto_trainer.py` | Background retraining on new telemetry |
| `gui/main_window.py` | OS shell layout, 18-app registry, nav, header |
| `gui/nav_bar.py` | Tree-grouped launcher sidebar |
| `gui/pages/home.py` | Overview (farm health, mode, alerts) |
| `gui/pages/sensors.py` | Field Monitor |
| `gui/pages/control.py` | Control Center (manual overrides, workloads) |
| `gui/pages/ai.py` | Advisor (ML outputs, confidence, explanations) |
| `gui/pages/settings.py` | Device (hardware, OS, kernel, network) |
| `gui/pages/alerts.py` | Alerts from event log |
| `gui/pages/task_monitor.py` | Service and workload health |
| `gui/pages/water_manager.py` | Irrigation controls |
| `gui/pages/power_center.py` | Energy mode and battery |
| `gui/pages/updates_page.py` | A/B slot update management |
| `gui/pages/maintenance_page.py` | Safe mode, restart/shutdown |
| `gui/pages/{clock,calculator,notes,weather,calendar,reports,help}_app.py` | Utility apps |
| `distro/x86_64-live/` | Debian live image build tree |
| `distro/x86_64-live/build.sh` | Main ISO build script |
| `distro/x86_64-live/systemd/` | All systemd unit files |
| `distro/x86_64-live/plymouth-theme/` | Custom boot splash |
| `control/control.json` | Runtime control state (GUI → controller) |
| `state/os_state.json` | Runtime OS state (controller → GUI) |
| `datasets/telemetry_log.jsonl` | Raw training data |
| `datasets/telemetry.csv` | Processed training dataset |
| `ml_engine/policy_model.pkl` | Active trained LightGBM model |
| `ml_engine/policy_model.meta.json` | Model metadata, thresholds, accuracy |
| `ml_engine/policy_confidence_calibrator.pkl` | Isotonic confidence calibrator |
| `ml_engine/model_registry/` | Versioned model artifact history |
| `GEOS_ROADMAP_AND_SESSION_MEMORY.md` | Persistent project memory (all decisions) |
