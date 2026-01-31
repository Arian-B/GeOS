# analytics_workload.py
import time
import random

def run():
    while True:
        data = [random.random() for _ in range(200000)]
        _ = sum(data) / len(data)
        time.sleep(10)  # runs occasionally
