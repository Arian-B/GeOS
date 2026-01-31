# sensor_workload.py
import time
import random

def run():
    while True:
        # Simulate sensor polling
        soil = random.uniform(20, 60)
        temp = random.uniform(15, 40)
        humidity = random.uniform(30, 80)

        # Very light CPU work
        _ = soil * temp * humidity

        time.sleep(1)  # sensors are frequent but light
