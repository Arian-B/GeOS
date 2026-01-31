# sensor_simulator.py

import random
import time

class SensorState:
    def __init__(self):
        self.soil_moisture = 50    # %
        self.temperature = 25     # Celsius
        self.humidity = 60        # %
        self.battery = 100
        self.battery_health = 100 # max capacity %

    def update(self):
        # Simulate realistic slow changes
        self.soil_moisture += random.uniform(-1, 1)
        self.temperature += random.uniform(-0.2, 0.2)

        # Battery aging: slow long-term degradation
        self.battery_health -= random.uniform(0.005, 0.02)
        self.battery_health = max(50, self.battery_health)

        # Battery drain depends on health
        effective_drain = random.uniform(0.8, 1.5) * (100 / self.battery_health)
        self.battery -= effective_drain
        self.battery = max(0, self.battery)


        # Clamp values
        self.soil_moisture = max(0, min(100, self.soil_moisture))
        self.temperature = max(0, min(50, self.temperature))
        self.humidity = max(0, min(100, self.humidity))

    def read(self):
        return {
            "soil_moisture": round(self.soil_moisture, 2),
            "temperature": round(self.temperature, 2),
            "humidity": round(self.humidity, 2),
            "battery": round(self.battery, 2),
            "battery_health": round(self.battery_health, 2)
        }


if __name__ == "__main__":
    sensors = SensorState()

    print("[Sensors] Agricultural sensor simulator started")

    while True:
        sensors.update()
        print("[Sensors]", sensors.read())
        time.sleep(2)
