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
2. Apply **machine learning and reinforcement learning** for adaptive OS-level decision-making  
3. Simulate realistic agricultural workloads without physical hardware  
4. Develop a **touch-friendly GUI** suitable for non-technical users (farmers)  
5. Prepare the system for future deployment on **Raspberry Pi embedded hardware**  

---

## Core Innovations
- Python-based ML control layer integrated with Linux user-space mechanisms  
- Reinforcement learning–based policy optimization for energy management  
- Realistic workload simulation (sensors, irrigation, analytics, surveillance)  
- Telemetry-driven dataset generation for continuous learning  
- Modular Linux-based architecture with the kernel left untouched  

---

## Architecture Overview
```
GeOS
├── core_os        # Energy controller, policies, OS state (Python)
├── ml_engine     # ML models, RL agents, policy training (Python)
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
- psutil

---

## Quick Start (Demo Mode)

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

---

## Machine Learning Pipeline

### Train the Policy Model
```bash
python3 ml_engine/train_policy_model.py
```

### Evaluate the Learned Policy
```bash
python3 ml_engine/evaluate_policies.py
```

---

## Current Status
- Approximately 70% implementation complete  
- Core OS logic, ML pipeline, and GUI implemented  
- Kernel-level integration planned for a future phase  
- Raspberry Pi deployment scheduled in the next development phase  

---

## License
MIT License (temporary)

---

## Author
**Ari**  
Computer Science and Engineering  
Focus: Systems Engineering, Embedded Linux, ML-Driven OS Design  
