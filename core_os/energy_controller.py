# core_os/energy_controller.py

import psutil
import os
import time
import datetime

from ml_engine.rl_agent import RLAgent
from ml_engine.reward_model import compute_reward

from control.os_control import read_control
from .energy_modes import ENERGY_SAVER, BALANCED, PERFORMANCE, BASE_THRESHOLDS
from sensors.sensor_simulator import SensorState
from logs.os_logger import log_event
from ml_engine.threshold_advisor import adjust_thresholds
from state.os_state import write_state
from core_os.notifications import raise_alert
from core_os.network import is_connected


# -----------------------------
# SYSTEM STRESS CHECK
# -----------------------------
def system_under_stress():
    cpu = psutil.cpu_percent(interval=None)
    load = os.getloadavg()[0]
    return cpu > 50 or load > 1.0


# -----------------------------
# OS GLOBAL STATE
# -----------------------------
CURRENT_MODE = BALANCED
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
    os.nice(mode["cpu_nice"])
    print(f"[OS] CPU nice set to {mode['cpu_nice']}")
    print(f"[OS] Sensor rate: {mode['sensor_rate']}")
    log_event("MODE_CHANGE", mode["name"])


# -----------------------------
# SAFETY / RULE-BASED GUARD
# -----------------------------
def safety_guard(sensor_data, adjusted_thresholds):
    battery = sensor_data["battery"]
    soil = sensor_data["soil_moisture"]

    # Hard safety constraints
    if battery < 10:
        return ENERGY_SAVER

    if battery < adjusted_thresholds["battery_energy_saver"]:
        return ENERGY_SAVER

    if soil < adjusted_thresholds["soil_performance"]:
        return PERFORMANCE

    return None  # no override


# -----------------------------
# OS MAIN LOOP
# -----------------------------
def run_os():
    global CURRENT_MODE, prev_state, prev_action

    print("[OS] GeOS Energy Controller started")

    try:
        while True:
            # ---------- SENSOR DATA ----------
            sensors.update()
            data = sensors.read()

            # ---------- TIME ----------
            data["hour"] = datetime.datetime.now().hour

            # ---------- SYSTEM METRICS ----------
            data["cpu_percent"] = psutil.cpu_percent(interval=None)
            data["load_avg"] = os.getloadavg()[0]
            data["memory_percent"] = psutil.virtual_memory().percent

            # ---------- NETWORK ----------
            data["network"] = "ONLINE" if is_connected() else "OFFLINE"

            log_event("SENSOR_READ", data)
            print(f"[OS] Sensor data: {data}")

            # ---------- ALERTS ----------
            if data["soil_moisture"] < 15:
                raise_alert("CRITICAL", "Soil moisture critically low")

            if data["temperature"] > 42:
                raise_alert("CRITICAL", "Temperature dangerously high")

            if data["battery"] < 15:
                raise_alert("WARN", "Battery level low")

            # ---------- ML THRESHOLD ADVISOR ----------
            adjusted_thresholds, ml_suggestion = adjust_thresholds(
                data, BASE_THRESHOLDS
            )

            log_event("ML_PREDICTION", {"suggested_mode": ml_suggestion})
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

            # ---------- SAFETY OVERRIDE ----------
            guard_mode = safety_guard(data, adjusted_thresholds)
            new_mode = guard_mode if guard_mode else proposed_mode

            # ---------- APPLY MODE ----------
            if new_mode != CURRENT_MODE:
                CURRENT_MODE = new_mode
                apply_mode(CURRENT_MODE)

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
                "ml_suggested_mode": ml_suggestion,
                "rl_action": rl_action,
                "sensors": data
            }
            write_state(state)

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n[OS] Shutting down OS")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    run_os()
