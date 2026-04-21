# GeOS
### An Adaptive ML-Driven Linux OS Distribution for Smart Farming on Embedded Devices

GeOS is a **Linux-based operating system distribution and control layer implemented primarily in Python**, designed for **energy-efficient, intelligent agriculture systems** running on **Raspberry Pi and other embedded Linux devices**.

Rather than replacing the Linux kernel, GeOS functions as a **Python-based embedded OS extension layer** that operates in user space, integrating tightly with Linux scheduling, telemetry, and process control mechanisms.

Unlike traditional embedded Linux systems with static policies, GeOS introduces a **machine-learning-driven control framework** that dynamically adapts system behavior based on:

- Agricultural sensor workloads  
- System-level telemetry (CPU, memory, load)  
- Energy and power constraints  
- Environmental and operational context  

---

## Project Goals
1. Design an **energy-aware OS control layer** for smart farming systems  
2. Apply **machine learning** for adaptive OS-level decision-making  
3. Simulate realistic agricultural workloads without physical hardware  
4. Develop a **touch-friendly GUI** suitable for non-technical users (farmers)  
5. Prepare the system for future deployment on **Raspberry Pi embedded hardware**  

---

## Core Innovations
- Python-based ML control layer integrated with Linux user-space mechanisms  
- LightGBM-based policy optimization for energy management  
- Realistic workload simulation (sensors, irrigation, analytics, surveillance)  
- Telemetry-driven dataset generation for continuous learning  
- Modular Linux-based architecture with the kernel left untouched  

---

## Architecture Overview
```
GeOS
├── core_os        # Energy controller, policies, OS state (Python)
├── ml_engine     # Policy models, evaluation, and training (Python)
├── workloads     # Simulated agricultural workloads
├── telemetry     # System and sensor data collection
├── gui           # Touch-friendly Qt-based GUI
├── sensors       # Sensor simulation layer
├── control       # Actuator and override logic
├── datasets      # Generated training datasets (git-ignored)
└── logs          # Runtime logs (git-ignored)
```

---

## System Requirements
- Linux OS (tested on Ubuntu via WSL; target: Raspberry Pi OS)
- Python 3.10 or higher
- PySide6 (GUI framework)
- scikit-learn
- lightgbm
- psutil

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

This path uses the project `.venv` when present and starts the fullscreen GeOS shell directly.

---

## Service-Oriented Quick Start

### 1. Start the Energy Controller
```bash
python3 -m core_os.energy_controller
```

### 2. Run the Workload Simulator
```bash
python3 workloads/workload_manager.py
```

### 3. Start Telemetry Collection
```bash
python3 telemetry/collector.py
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

## OS Packaging & Targets

GeOS is primarily targeting **embedded Linux** deployments (Raspberry Pi-class devices). Current packaging work is split into:

- **Short-term demo path (laptop USB boot)**: a Debian live ISO is produced for faculty/demo boot sessions on x86_64 laptops. This is treated as a *demo artifact*, not the long-term distro strategy.
- **Long-term production path (embedded)**: a **Yocto**-based image pipeline targeting Raspberry Pi and other embedded boards.

### Demo OS via GitHub Releases (Debian live ISO)
- The demo ISO should be published as a GitHub Release asset (do not commit ISOs into git).
- After downloading, verify integrity:
```bash
sha256sum binary.iso
```

### Yocto → Raspberry Pi (planned)
- Yocto will become the canonical way to generate reproducible embedded images and board-specific artifacts (BSP layers, image recipes, update strategy).
- Raspberry Pi is the first target board for end-to-end embedded validation.

---

## Machine Learning Pipeline

GeOS now uses a LightGBM-based policy model with rolling telemetry features.

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
This writes the best found parameters to `ml_engine/lightgbm_params.json`. Subsequent training and benchmarking reuse that parameter file automatically.

### Evaluate the Learned Policy
```bash
python3 -m ml_engine.evaluate_policies
```

### Run a Rolling Temporal Backtest
```bash
python3 -m ml_engine.rolling_backtest
```
This evaluates the current LightGBM parameter set across multiple expanding time windows.

### Benchmark Against Other Models
```bash
python3 -m ml_engine.benchmark_models
```

### Run Feature Importance Export
```bash
python3 -m ml_engine.feature_importance
```

### Generate a LightGBM Explainability Report
```bash
python3 -m ml_engine.explainability_report
```
This writes class-level and example local LightGBM contribution summaries to `ml_engine/explainability_report.json`.

### Optional: Disable Background Auto-Retraining
```bash
GEOS_DISABLE_AUTO_TRAINER=1 python3 -m core_os.energy_controller
```

---

## Current Status
- Approximately 70% implementation complete  
- Core OS logic and ML pipeline implemented; GUI is in-progress  
- Kernel-level integration planned for a future phase  
- Yocto + Raspberry Pi deployment scheduled in the next development phase  

---

## License
MIT License (temporary)

---

## Author
**Ari**  
Computer Science and Engineering  
Focus: Systems Engineering, Embedded Linux, ML-Driven OS Design  
