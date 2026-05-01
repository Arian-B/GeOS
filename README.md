# GeOS
### An Adaptive ML-Driven Linux OS Control Layer for Smart Farming on Embedded Devices

GeOS is a **Python-based, Linux-native adaptive control layer** for **smart agricultural edge systems**. It is designed for devices such as soil monitoring nodes, irrigation controllers, and field-surveillance units that must balance **responsiveness, energy efficiency, and workload pressure** in changing farm conditions.

Rather than modifying the Linux kernel, GeOS operates fully in **user space** and integrates with Linux-oriented scheduling, telemetry, workload control, and power-management mechanisms. The current prototype is developed and validated in a **Debian x86_64 software environment** with simulated agricultural sensors and workloads, while remaining structured for later deployment on **Raspberry Pi and similar embedded Linux targets**.

Unlike static embedded control approaches, GeOS uses a **machine-learning-driven runtime policy** that adapts system behavior from:

- Agricultural sensor telemetry
- System-level performance metrics such as CPU, memory, and load
- Battery and energy constraints
- Workload activity and operator control context
- Time-based and environmental operating conditions

---

## Project Goals
1. Design an **ML-driven OS-level energy control layer** for smart farming devices
2. Keep the system **portable across Linux environments** without kernel modification
3. Use **runtime telemetry and agricultural context** to drive adaptive mode decisions
4. Provide a **clear operator interface** for monitoring, overrides, and AI explanation
5. Support **continuous learning** through telemetry collection, retraining, and model versioning
6. Prepare the prototype for future **embedded deployment on Raspberry Pi-class hardware**

---

## Core Innovations
- Linux user-space control architecture with no kernel patching
- LightGBM-based multi-class policy engine for runtime energy-mode selection
- 45-feature rolling telemetry representation shared by training and live inference
- Two-layer decision design with **hard safety overrides above the ML policy**
- Explainable AI outputs exposed in the operator console
- Continuous telemetry logging, retraining, calibration, and model registry support

---

## Architecture Overview
```text
GeOS
├── core_os      # Control loop, boot/recovery, updates, kernel hooks
├── ml_engine    # Features, training, benchmarking, inference, explainability
├── workloads    # Simulated agricultural workloads
├── telemetry    # Runtime logging and metrics exposure
├── gui          # PySide6 fullscreen operator shell
├── sensors      # Sensor simulation and external input hooks
├── control      # Persistent control-plane state and overrides
├── interface    # Workflow API and REPL interface
├── state        # Shared runtime state
├── services     # Background service manifest
├── datasets     # Generated telemetry datasets (git-ignored)
└── logs         # Runtime logs and performance metrics (git-ignored)
```

---

## System Requirements
- Linux-oriented environment (current prototype validated in Debian x86_64 development workflow)
- Python 3.10 or higher
- PySide6
- psutil
- pandas
- numpy
- scikit-learn
- lightgbm
- joblib

---

## Quick Start (Local App Mode)

### 1. Prepare the environment
```bash
./setup_env.sh
```

### 2. Launch GeOS
```bash
./run.sh
```

This uses the project `.venv` when present and starts the fullscreen GeOS shell together with the required local background services.

---

## Service-Oriented Quick Start

### 1. Start Boot and Runtime Control
```bash
python3 -m core_os.boot_manager
python3 -m core_os.energy_controller
```

### 2. Start Workload and Telemetry Services
```bash
python3 -m workloads.workload_manager
python3 -m telemetry.collector
```

### 3. Start Local Interfaces
```bash
python3 -m interface.workflow_server
python3 -m interface.repl_server
python3 -m telemetry.metrics_server
```

### 4. Launch the GUI
```bash
python3 -m gui.app
```

### Local service endpoints
- Workflow API: `http://127.0.0.1:8080/status`
- Metrics API: `http://127.0.0.1:8090/metrics`
- REPL server: `127.0.0.1:5050`

---

## Runtime Design

The central GeOS control loop runs in `core_os.energy_controller`.

Each cycle:
1. reads environmental and system telemetry
2. augments the snapshot with control and workload context
3. builds the current 45-feature policy vector
4. runs LightGBM policy inference
5. applies hard safety and manual overrides when required
6. enforces the resulting operating mode
7. writes shared runtime state for the GUI and local services

The three operating modes are:
- `ENERGY_SAVER`
- `BALANCED`
- `PERFORMANCE`

Mode changes affect:
- process priority through `os.nice()`
- workload polling and activity configuration
- Linux-oriented governor and swappiness tuning where supported
- control-loop cadence and overall runtime behavior

---

## Current Scope

GeOS is currently a **working software prototype** focused on the runtime, ML control loop, service architecture, and operator interface.

- The active repository scope is the Python runtime stack, GUI shell, telemetry flow, workloads, updates/recovery scaffolding, and policy engine.
- The current validation environment is a Debian-style x86_64 software setup using simulated agricultural conditions.
- Future deployment on Raspberry Pi and other embedded Linux targets remains a planned next stage.
- Packaging and board-specific image engineering are not the active focus of the current repository phase.

---

## Machine Learning Pipeline

GeOS uses a LightGBM-based multi-class policy model trained on telemetry-derived feature sequences.

### Build the Training Dataset
```bash
python3 -m ml_engine.dataset_builder
```

### Train the Policy Model
```bash
python3 -m ml_engine.train_policy_model
```
This refreshes the active LightGBM artifact, writes calibrated-confidence metadata, and stores a versioned copy under `ml_engine/model_registry/`.

### Tune LightGBM Hyperparameters
```bash
python3 -m ml_engine.tune_lightgbm
```
This writes the best parameter set to `ml_engine/lightgbm_params.json`.

### Benchmark Against Other Models
```bash
python3 -m ml_engine.benchmark_models
```

### Run a Rolling Temporal Backtest
```bash
python3 -m ml_engine.rolling_backtest
```

### Export Feature Importance
```bash
python3 -m ml_engine.feature_importance
```

### Generate a LightGBM Explainability Report
```bash
python3 -m ml_engine.explainability_report
```
This writes class-level and example local contribution summaries to `ml_engine/explainability_report.json`.

### Optional: Disable Background Auto-Retraining
```bash
GEOS_DISABLE_AUTO_TRAINER=1 python3 -m core_os.energy_controller
```

---

## Current Technical Position

GeOS should currently be understood as:

> A smart farming runtime and operator environment with an ML-backed OS-level energy policy loop, implemented primarily in Python, running above Linux in user space, and validated as a software prototype using simulated agricultural workloads.

The main completed areas are:
- telemetry collection and dataset generation
- 45-feature policy engineering
- LightGBM training, calibration, and versioning
- runtime inference and safety overrides
- workload simulation and mode-based enforcement
- fullscreen PySide6 operator console
- local workflow, metrics, and REPL interfaces
- boot, recovery, and update-management scaffolding

Current engineering priorities are:
- runtime stability and service hardening
- interface clarity and polish
- stronger state coordination
- continued ML observability and explainability

---

## License
MIT License

---

## Author
**Ari**  
Computer Science and Engineering  
Focus: Systems Engineering, Embedded Linux, ML-Driven OS Design
