# camera_workload.py
import time

def run():
    print("[CAMERA] Surveillance workload started")
    while True:
        # Heavy image-like computation
        for _ in range(10):
            _ = [i * i for i in range(200_000)]
        time.sleep(1)
