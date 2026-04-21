# sensor_simulator.py

import json
import os
import time
import random

import psutil

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVERRIDE_FILE = os.path.join(BASE_DIR, "sensors", "sensor_inputs.json")
CONTROL_FILE = os.path.join(BASE_DIR, "control", "control.json")


class SensorState:
    def __init__(self):
        self.soil_moisture = None
        self.temperature = None
        self.humidity = None
        self.battery = None
        self.battery_health = None # max capacity % (system API does not expose health)
        self._sim_soil = 52.0
        self._sim_temp = 27.0
        self._sim_humidity = 58.0

        # Initialize from system readings if available.
        self._update_from_system({})

    def _drift(self, current, low, high, max_step):
        if current is None:
            current = (low + high) / 2.0
        # Small random walk with mild pull toward center to look realistic and stable.
        center = (low + high) / 2.0
        step = random.uniform(-max_step, max_step)
        pull = (center - current) * 0.03
        next_value = current + step + pull
        return max(low, min(high, next_value))

    def _load_overrides(self):
        try:
            with open(OVERRIDE_FILE, "r") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _sensor_workload_enabled(self):
        try:
            with open(CONTROL_FILE, "r") as f:
                data = json.load(f)
            workloads = data.get("workloads", {})
            return bool(workloads.get("sensor", True))
        except Exception:
            return True

    def _read_battery_percent(self):
        batt = psutil.sensors_battery()
        if batt and batt.percent is not None:
            return float(batt.percent)
        return None

    def _read_temperature_c(self):
        try:
            temps = psutil.sensors_temperatures(fahrenheit=False)
        except Exception:
            temps = None

        if not temps:
            return None

        readings = []
        for entries in temps.values():
            for entry in entries:
                if entry.current is not None:
                    readings.append(float(entry.current))

        if not readings:
            return None

        return sum(readings) / len(readings)

    def _update_from_system(self, overrides):
        # Battery percent from the host system (Windows/Linux) unless overridden.
        if "battery" not in overrides:
            battery_percent = self._read_battery_percent()
            if battery_percent is not None:
                self.battery = battery_percent
                self.battery_health = 100
            else:
                self.battery = None
                self.battery_health = None

        # Temperature from system sensors if available unless overridden.
        if "temperature" not in overrides:
            temp_c = self._read_temperature_c()
            if temp_c is not None:
                self.temperature = temp_c
            else:
                self.temperature = None

    def update(self):
        # Load optional overrides for external sensor input.
        overrides = self._load_overrides()
        sensor_enabled = self._sensor_workload_enabled()

        if sensor_enabled and "soil_moisture" in overrides:
            try:
                self.soil_moisture = float(overrides["soil_moisture"])
            except (TypeError, ValueError):
                self.soil_moisture = None
        else:
            self.soil_moisture = None
        if sensor_enabled and "humidity" in overrides:
            try:
                self.humidity = float(overrides["humidity"])
            except (TypeError, ValueError):
                self.humidity = None
        else:
            self.humidity = None
        if sensor_enabled and "temperature" in overrides:
            try:
                self.temperature = float(overrides["temperature"])
            except (TypeError, ValueError):
                self.temperature = None
        elif not sensor_enabled:
            self.temperature = None
        if "battery" in overrides:
            try:
                self.battery = float(overrides["battery"])
                self.battery_health = 100
            except (TypeError, ValueError):
                self.battery = None
                self.battery_health = None

        # Always refresh system-based readings.
        # When sensor workload is disabled, block temperature refresh to show N/A.
        system_overrides = overrides.copy()
        if not sensor_enabled:
            system_overrides["temperature"] = None
        self._update_from_system(system_overrides)

        # Generate simulated values when workload is enabled and no override/system value is available.
        if sensor_enabled:
            if self.soil_moisture is None:
                self._sim_soil = self._drift(self._sim_soil, 18.0, 82.0, 2.4)
                self.soil_moisture = self._sim_soil

            if self.humidity is None:
                self._sim_humidity = self._drift(self._sim_humidity, 32.0, 88.0, 3.0)
                self.humidity = self._sim_humidity

            if self.temperature is None:
                self._sim_temp = self._drift(self._sim_temp, 17.0, 39.0, 0.8)
                self.temperature = self._sim_temp

        # Clamp values to safe ranges.
        if self.soil_moisture is not None:
            self.soil_moisture = max(0, min(100, float(self.soil_moisture)))
        if self.temperature is not None:
            self.temperature = max(0, min(50, float(self.temperature)))
        if self.humidity is not None:
            self.humidity = max(0, min(100, float(self.humidity)))
        if self.battery is not None:
            self.battery = max(0, min(100, float(self.battery)))
        if self.battery_health is not None:
            self.battery_health = max(0, min(100, float(self.battery_health)))

    def read(self):
        def _round_or_none(value):
            return round(value, 2) if value is not None else None

        return {
            "soil_moisture": _round_or_none(self.soil_moisture),
            "temperature": _round_or_none(self.temperature),
            "humidity": _round_or_none(self.humidity),
            "battery": _round_or_none(self.battery),
            "battery_health": _round_or_none(self.battery_health)
        }


if __name__ == "__main__":
    sensors = SensorState()

    print("[Sensors] Agricultural sensor simulator started")

    while True:
        sensors.update()
        print("[Sensors]", sensors.read())
        time.sleep(2)
