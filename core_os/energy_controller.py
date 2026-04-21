# core_os/energy_controller.py

import datetime
import json
import os
import sys
import time

import psutil

# Ensure project root is on sys.path when running as a script.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from control.os_control import read_control
from core_os.energy_modes import ENERGY_SAVER, BALANCED, PERFORMANCE, BASE_THRESHOLDS
from ml_engine.auto_trainer import start_auto_trainer
from ml_engine.lightgbm_policy import current_thresholds, predict_policy
from ml_engine.policy_features import PolicyFeatureBuilder
from logs.os_logger import log_event
from sensors.sensor_simulator import SensorState
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
feature_builder = PolicyFeatureBuilder()
BASE_DIR = PROJECT_ROOT
WORKLOAD_STATE_FILE = os.path.join(BASE_DIR, "workloads", "workload_state.json")


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


def _read_json(path):
    try:
        with open(path, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _augment_policy_context(data, control):
    workloads = control.get("workloads", {}) if isinstance(control.get("workloads"), dict) else {}
    workload_state = _read_json(WORKLOAD_STATE_FILE)

    data["control_auto"] = control.get("mode", "AUTO") == "AUTO"
    data["control_manual"] = control.get("mode") == "MANUAL"
    data["maintenance_enabled"] = bool(control.get("maintenance", False))
    data["safe_mode_enabled"] = bool(control.get("safe_mode", False))
    data["emergency_shutdown_enabled"] = bool(control.get("emergency_shutdown", False))
    data["irrigation_enabled"] = bool(control.get("irrigation", False))
    data["ventilation_enabled"] = bool(control.get("ventilation", False))
    data["workload_sensor_enabled"] = bool(workloads.get("sensor", True))
    data["workload_irrigation_enabled"] = bool(workloads.get("irrigation", True))
    data["workload_camera_enabled"] = bool(workloads.get("camera", True))
    data["workload_analytics_enabled"] = bool(workloads.get("analytics", True))
    data["workload_enabled_count"] = sum(
        1 for name in ("sensor", "irrigation", "camera", "analytics") if workloads.get(name)
    )
    data["workload_active_count"] = sum(
        1 for name in ("sensor", "irrigation", "camera", "analytics") if workload_state.get(name)
    )
    return data


# -----------------------------
# SAFETY / RULE-BASED GUARD
# -----------------------------
def safety_guard(sensor_data, adjusted_thresholds):
    battery = sensor_data.get("battery")
    soil = sensor_data.get("soil_moisture")
    temperature = sensor_data.get("temperature")

    # Hard safety constraints
    if battery is not None and battery < 10:
        return ENERGY_SAVER

    if battery is not None and battery < adjusted_thresholds["battery_energy_saver"]:
        return ENERGY_SAVER

    if soil is not None and soil < adjusted_thresholds["soil_performance"]:
        return PERFORMANCE

    temp_threshold = adjusted_thresholds.get("temperature_energy_saver")
    if temperature is not None and temp_threshold is not None and temperature > temp_threshold:
        return ENERGY_SAVER

    return None  # no override


def evaluate_control_decision(data, control, policy_features, current_mode, mode_lock_counter):
    mode_setting = control.get("mode", "AUTO")
    manual_override_name = control.get("manual_override_mode")
    if manual_override_name is None:
        manual_override_name = control.get("forced_mode")
    manual_override_mode = (
        _mode_from_name(manual_override_name) if mode_setting == "MANUAL" else None
    )

    adjusted_thresholds = dict(BASE_THRESHOLDS)
    adjusted_thresholds.update(current_thresholds())
    policy_decision = predict_policy(policy_features)
    ml_best_mode = policy_decision.get("mode", "BALANCED")
    ml_confidence = policy_decision.get("confidence", 0.0)
    ml_raw_confidence = policy_decision.get("raw_confidence", ml_confidence)
    ml_confidence_source = policy_decision.get("confidence_source", "MODEL_PROBABILITY")
    policy_source = policy_decision.get("source", "FALLBACK")
    top_features = policy_decision.get("top_features", [])

    if manual_override_mode is not None:
        proposed_mode = manual_override_mode
        policy_source = "MANUAL_OVERRIDE"
    else:
        proposed_mode = _mode_from_name(ml_best_mode) or BALANCED

    guard_mode = safety_guard(data, adjusted_thresholds)
    new_mode = guard_mode if guard_mode else proposed_mode
    reason_codes = []

    if manual_override_mode is not None:
        reason_codes.append("manual_override")
    if guard_mode is not None:
        reason_codes.append("safety_override")
        policy_source = "SAFETY_OVERRIDE"
    elif policy_source == "LIGHTGBM":
        reason_codes.append("lightgbm_policy")

    if guard_mode is None and mode_lock_counter > 0 and new_mode != current_mode:
        new_mode = current_mode
        reason_codes.append("mode_lock")

    return {
        "new_mode": new_mode,
        "ml_suggested_mode": ml_best_mode,
        "ml_confidence": ml_confidence,
        "ml_raw_confidence": ml_raw_confidence,
        "ml_confidence_source": ml_confidence_source,
        "policy_source": policy_source,
        "ml_thresholds": adjusted_thresholds,
        "ml_top_features": top_features,
        "ml_reason_codes": reason_codes,
    }


# -----------------------------
# OS MAIN LOOP
# -----------------------------
def run_os():
    global CURRENT_MODE, MODE_LOCK_COUNTER

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

            # ---------- ALERTS ----------
            if data.get("soil_moisture") is not None and data["soil_moisture"] < 15:
                raise_alert("CRITICAL", "Soil moisture critically low")

            if data.get("temperature") is not None and data["temperature"] > 42:
                raise_alert("CRITICAL", "Temperature dangerously high")

            if data.get("battery") is not None and data["battery"] < 15:
                raise_alert("WARN", "Battery level low")

            control = read_control()
            data = _augment_policy_context(data, control)
            feature_builder.add_snapshot(data)
            policy_features = feature_builder.current_features()

            log_event("SENSOR_READ", data)
            print(f"[OS] Sensor data: {data}")

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
                    "ml_confidence": 1.0,
                    "ml_raw_confidence": 1.0,
                    "ml_confidence_source": "RULE_BASED",
                    "policy_source": "EMERGENCY",
                    "ml_thresholds": {},
                    "sensors": data,
                    "ml_reason_codes": ["emergency_shutdown"],
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
                    "ml_confidence": 1.0,
                    "ml_raw_confidence": 1.0,
                    "ml_confidence_source": "RULE_BASED",
                    "policy_source": "MAINTENANCE",
                    "ml_thresholds": {},
                    "sensors": data,
                    "ml_reason_codes": ["maintenance_mode"],
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

            decision = evaluate_control_decision(
                data=data,
                control=control,
                policy_features=policy_features,
                current_mode=CURRENT_MODE,
                mode_lock_counter=MODE_LOCK_COUNTER,
            )
            adjusted_thresholds = decision["ml_thresholds"]
            ml_best_mode = decision["ml_suggested_mode"]
            ml_confidence = decision["ml_confidence"]
            policy_source = decision["policy_source"]
            top_features = decision["ml_top_features"]
            new_mode = decision["new_mode"]
            reason_codes = decision["ml_reason_codes"]

            log_event(
                "ML_PREDICTION",
                {
                    "suggested_mode": ml_best_mode,
                    "confidence": ml_confidence,
                    "policy_source": policy_source,
                    "top_features": top_features,
                }
            )
            log_event("ML_THRESHOLD_ADJUSTMENT", adjusted_thresholds)

            # ---------- APPLY MODE ----------
            if new_mode != CURRENT_MODE:
                CURRENT_MODE = new_mode
                apply_mode(CURRENT_MODE)
                # Lock mode transitions for a few cycles after a switch.
                MODE_LOCK_COUNTER = 3
                switched_this_cycle = True

            # ---------- WRITE OS STATE ----------
            state = {
                "current_mode": CURRENT_MODE["name"],
                "ml_suggested_mode": ml_best_mode,
                "ml_confidence": ml_confidence,
                "ml_raw_confidence": decision["ml_raw_confidence"],
                "ml_confidence_source": decision["ml_confidence_source"],
                "ml_threshold_mode": ml_best_mode,
                "policy_source": policy_source,
                "ml_thresholds": adjusted_thresholds,
                "ml_top_features": top_features,
                "ml_reason_codes": reason_codes,
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
