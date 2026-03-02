# core_os/energy_controller.py

import psutil
import os
import time
import datetime
import json
import sys

# Ensure project root is on sys.path when running as a script.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ml_engine.rl_agent import RLAgent
from ml_engine.reward_model import compute_reward

from control.os_control import read_control
from core_os.energy_modes import ENERGY_SAVER, BALANCED, PERFORMANCE, BASE_THRESHOLDS
from sensors.sensor_simulator import SensorState
from logs.os_logger import log_event
from ml_engine.threshold_advisor import adjust_thresholds
from ml_engine.policy_optimizer import predict_best_mode
from ml_engine.auto_trainer import start_auto_trainer
from state.os_state import write_state
from core_os.notifications import raise_alert
from core_os.network import is_connected
from core_os import performance_monitor
from core_os.kernel_interface import tune_for_mode


# -----------------------------
# SYSTEM STRESS CHECK
# -----------------------------
def system_under_stress():
    cpu = psutil.cpu_percent(interval=None)
    load = _safe_get_load_avg()
    return cpu > 50 or load > 1.0


# -----------------------------
# OS GLOBAL STATE
# -----------------------------
CURRENT_MODE = BALANCED
# Mode stability lock: prevents rapid oscillations between modes.
MODE_LOCK_COUNTER = 0
sensors = SensorState()

# RL AGENT
rl_agent = RLAgent()
prev_state = None
prev_action = None


# -----------------------------
# APPLY MODE (POLICY → MECHANISM)
# -----------------------------
def apply_mode(mode):
    print(f"\n[OS] Switching to mode: {mode['name']}")
    try:
        os.nice(mode["cpu_nice"])
        print(f"[OS] CPU nice set to {mode['cpu_nice']}")
    except (AttributeError, PermissionError, OSError):
        # os.nice is not available on all platforms (e.g., Windows).
        pass
    print(f"[OS] Sensor rate: {mode['sensor_rate']}")
    log_event("MODE_CHANGE", mode["name"])
    # Adaptive scaling: update workload configuration so services can align to energy mode.
    _write_workload_config(mode)
    # Performance monitoring: track mode switches.
    performance_monitor.log_mode_change(mode["name"])
    # Software-level kernel tuning (governor/swappiness) when available.
    tune_for_mode(mode["name"])


def _write_workload_config(mode):
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = os.path.join(project_root, "workloads", "workload_config.json")

    if mode["name"] == "ENERGY_SAVER":
        config = {
            "sensor_interval": 5,
            "camera_interval": 10,
            "analytics_intensity": "LOW"
        }
    elif mode["name"] == "PERFORMANCE":
        config = {
            "sensor_interval": 1,
            "camera_interval": 2,
            "analytics_intensity": "HIGH"
        }
    else:
        config = {
            "sensor_interval": 2,
            "camera_interval": 5,
            "analytics_intensity": "MEDIUM"
        }

    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except OSError:
        # If the config can't be written, workloads will fall back to defaults.
        pass


def _pause_workloads_safely():
    """
    Emergency throttle: keep workloads alive but greatly reduce activity.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    config_path = os.path.join(project_root, "workloads", "workload_config.json")
    config = {
        "sensor_interval": 30,
        "camera_interval": 60,
        "analytics_intensity": "LOW"
    }
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    except OSError:
        pass


def _mode_from_name(name):
    if name == "ENERGY_SAVER":
        return ENERGY_SAVER
    if name == "PERFORMANCE":
        return PERFORMANCE
    if name == "BALANCED":
        return BALANCED
    return None


def _safe_get_load_avg():
    """
    Cross-platform load average approximation to avoid OS-specific errors.
    """
    try:
        return os.getloadavg()[0]
    except (AttributeError, OSError):
        try:
            return psutil.getloadavg()[0]
        except Exception:
            cpu = psutil.cpu_percent(interval=None)
            cores = psutil.cpu_count() or 1
            return (cpu / 100.0) * cores


# -----------------------------
# SAFETY / RULE-BASED GUARD
# -----------------------------
def safety_guard(sensor_data, adjusted_thresholds):
    battery = sensor_data.get("battery")
    soil = sensor_data.get("soil_moisture")

    # Hard safety constraints
    if battery is not None and battery < 10:
        return ENERGY_SAVER

    if battery is not None and battery < adjusted_thresholds["battery_energy_saver"]:
        return ENERGY_SAVER

    if soil is not None and soil < adjusted_thresholds["soil_performance"]:
        return PERFORMANCE

    return None  # no override


# -----------------------------
# OS MAIN LOOP
# -----------------------------
def run_os():
    global CURRENT_MODE, prev_state, prev_action, MODE_LOCK_COUNTER

    print("[OS] GeOS Energy Controller started")
    # Start background ML trainer (non-blocking).
    start_auto_trainer()

    try:
        while True:
            switched_this_cycle = False
            # ---------- SENSOR DATA ----------
            sensors.update()
            data = sensors.read()

            # ---------- TIME ----------
            data["hour"] = datetime.datetime.now().hour

            # ---------- SYSTEM METRICS ----------
            data["cpu_percent"] = psutil.cpu_percent(interval=None)
            data["load_avg"] = _safe_get_load_avg()
            data["memory_percent"] = psutil.virtual_memory().percent

            # ---------- NETWORK ----------
            data["network"] = "ONLINE" if is_connected() else "OFFLINE"

            log_event("SENSOR_READ", data)
            print(f"[OS] Sensor data: {data}")

            # ---------- ALERTS ----------
            if data.get("soil_moisture") is not None and data["soil_moisture"] < 15:
                raise_alert("CRITICAL", "Soil moisture critically low")

            if data.get("temperature") is not None and data["temperature"] > 42:
                raise_alert("CRITICAL", "Temperature dangerously high")

            if data.get("battery") is not None and data["battery"] < 15:
                raise_alert("WARN", "Battery level low")

            control = read_control()

            # ----- EMERGENCY SHUTDOWN -----
            if control.get("emergency_shutdown"):
                if CURRENT_MODE != ENERGY_SAVER:
                    CURRENT_MODE = ENERGY_SAVER
                    apply_mode(CURRENT_MODE)
                    # Lock mode transitions for a few cycles after a switch.
                    MODE_LOCK_COUNTER = 3
                    switched_this_cycle = True
                # Adaptive scaling: pause workloads safely during emergency.
                _pause_workloads_safely()
                # Keep GUI state current during emergency overrides.
                state = {
                    "current_mode": CURRENT_MODE["name"],
                    "ml_suggested_mode": "EMERGENCY",
                    "rl_action": "EMERGENCY",
                    "ml_thresholds": {},
                    "sensors": data,
                    "last_ai_action_time": datetime.datetime.now().isoformat()
                }
                write_state(state)
                # Performance monitoring: update metrics without blocking.
                performance_monitor.update(
                    CURRENT_MODE["name"],
                    data.get("cpu_percent"),
                    data.get("memory_percent")
                )
                # Decrement lock once per cycle when no new switch occurred.
                if MODE_LOCK_COUNTER > 0 and not switched_this_cycle:
                    MODE_LOCK_COUNTER -= 1
                time.sleep(3)
                continue

            # ----- MAINTENANCE MODE -----
            if control.get("maintenance"):
                if CURRENT_MODE != ENERGY_SAVER:
                    CURRENT_MODE = ENERGY_SAVER
                    apply_mode(CURRENT_MODE)
                    # Lock mode transitions for a few cycles after a switch.
                    MODE_LOCK_COUNTER = 3
                    switched_this_cycle = True
                # Keep GUI state fresh while in maintenance to avoid false offline state.
                state = {
                    "current_mode": CURRENT_MODE["name"],
                    "ml_suggested_mode": "MAINTENANCE",
                    "rl_action": "MAINTENANCE",
                    "ml_thresholds": {},
                    "sensors": data,
                    "last_ai_action_time": datetime.datetime.now().isoformat()
                }
                write_state(state)
                # Performance monitoring: update metrics in maintenance mode.
                performance_monitor.update(
                    CURRENT_MODE["name"],
                    data.get("cpu_percent"),
                    data.get("memory_percent")
                )
                # Decrement lock once per cycle when no new switch occurred.
                if MODE_LOCK_COUNTER > 0 and not switched_this_cycle:
                    MODE_LOCK_COUNTER -= 1
                time.sleep(3)
                continue

            # ----- USER MANUAL OVERRIDE -----
            mode_setting = control.get("mode", "AUTO")
            manual_override_name = control.get("manual_override_mode")
            if manual_override_name is None:
                manual_override_name = control.get("forced_mode")
            manual_override_mode = (
                _mode_from_name(manual_override_name) if mode_setting == "MANUAL" else None
            )


            # ---------- ML THRESHOLD ADVISOR ----------
            adjusted_thresholds, ml_suggestion = adjust_thresholds(
                data, BASE_THRESHOLDS
            )

            # ---------- ML OPTIMIZER ----------
            ml_best_mode, ml_confidence = predict_best_mode(data)
            if ml_best_mode is None:
                ml_best_mode = ml_suggestion

            log_event(
                "ML_PREDICTION",
                {
                    "suggested_mode": ml_best_mode,
                    "confidence": ml_confidence,
                    "threshold_mode": ml_suggestion
                }
            )
            log_event("ML_THRESHOLD_ADJUSTMENT", adjusted_thresholds)

            # ---------- RL STATE ----------
            state_repr = rl_agent.discretize_state(data)
            rl_action = rl_agent.choose_action(state_repr)

            # Map RL action → mode
            if rl_action == "ENERGY_SAVER":
                proposed_mode = ENERGY_SAVER
            elif rl_action == "PERFORMANCE":
                proposed_mode = PERFORMANCE
            else:
                proposed_mode = BALANCED
            # Combine ML optimizer + RL (manual override still wins)
            if manual_override_mode is not None:
                proposed_mode = manual_override_mode
            else:
                if rl_action == ml_best_mode:
                    proposed_mode = _mode_from_name(ml_best_mode) or proposed_mode
                elif ml_confidence >= 0.6:
                    proposed_mode = _mode_from_name(ml_best_mode) or proposed_mode

            # ---------- SAFETY OVERRIDE ----------
            guard_mode = safety_guard(data, adjusted_thresholds)
            new_mode = guard_mode if guard_mode else proposed_mode

            # ---------- APPLY MODE ----------
            # Mode stability lock: prevent oscillations, but always allow safety overrides.
            if guard_mode is None and MODE_LOCK_COUNTER > 0 and new_mode != CURRENT_MODE:
                new_mode = CURRENT_MODE

            if new_mode != CURRENT_MODE:
                CURRENT_MODE = new_mode
                apply_mode(CURRENT_MODE)
                # Lock mode transitions for a few cycles after a switch.
                MODE_LOCK_COUNTER = 3
                switched_this_cycle = True

            # ---------- RL LEARNING ----------
            if prev_state is not None and prev_action is not None:
                reward = compute_reward(prev_state, prev_action)
                rl_agent.update(prev_state, prev_action, reward, state_repr)
                rl_agent.save()

            prev_state = state_repr
            prev_action = rl_action

            # ---------- WRITE OS STATE ----------
            state = {
                "current_mode": CURRENT_MODE["name"],
                "ml_suggested_mode": ml_best_mode,
                "ml_confidence": ml_confidence,
                "ml_threshold_mode": ml_suggestion,
                "rl_action": rl_action,
                "ml_thresholds": adjusted_thresholds,
                "sensors": data,
                "last_ai_action_time": datetime.datetime.now().isoformat()
            }
            write_state(state)

            # Performance monitoring: update per-cycle metrics.
            performance_monitor.update(
                CURRENT_MODE["name"],
                data.get("cpu_percent"),
                data.get("memory_percent")
            )

            # Decrement lock once per cycle when no new switch occurred.
            if MODE_LOCK_COUNTER > 0 and not switched_this_cycle:
                MODE_LOCK_COUNTER -= 1

            time.sleep(CURRENT_MODE.get("sleep_interval", 2))

    except KeyboardInterrupt:
        print("\n[OS] Shutting down OS")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    run_os()
