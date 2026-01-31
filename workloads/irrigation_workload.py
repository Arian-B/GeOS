# irrigation_workload.py
import time
import random

def run():
    while True:
        # Random irrigation event
        if random.random() < 0.2:  # 20% chance
            start = time.time()
            while time.time() - start < 2:
                # Simulate pump computation
                _ = sum(i*i for i in range(2000))
        time.sleep(3)
