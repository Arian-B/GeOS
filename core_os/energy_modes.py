# energy_modes.py

"""
Defines energy modes for the GeOS.
Each mode represents a system-wide energy policy.
"""

ENERGY_SAVER = {
    "name": "ENERGY_SAVER",
    "cpu_nice": 15,
    "sleep_interval": 5,
    "sensor_rate": "LOW"
}

BALANCED = {
    "name": "BALANCED",
    "cpu_nice": 0,
    "sleep_interval": 2,
    "sensor_rate": "MEDIUM"
}

PERFORMANCE = {
    "name": "PERFORMANCE",
    "cpu_nice": -5,
    "sleep_interval": 0.5,
    "sensor_rate": "HIGH"
}

# Base OS thresholds (hard safety limits)
BASE_THRESHOLDS = {
    "battery_energy_saver": 25,   # % below which system must conserve
    "soil_performance": 35        # % below which performance is critical
}
