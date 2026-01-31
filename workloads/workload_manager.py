# workload_manager.py
import multiprocessing
import time
from sensor_workload import run as sensor
from irrigation_workload import run as irrigation
from camera_workload import run as camera
from analytics_workload import run as analytics

def start():
    workloads = {
        "Sensor": sensor,
        "Irrigation": irrigation,
        "Camera": camera,
        "Analytics": analytics
    }

    processes = []

    print("[WORKLOAD MANAGER] Starting agricultural workloads...")

    for name, fn in workloads.items():
        p = multiprocessing.Process(target=fn, name=name)
        p.start()
        print(f"[WORKLOAD MANAGER] {name} workload started (PID={p.pid})")
        processes.append(p)

    print("[WORKLOAD MANAGER] All workloads active. Running in background.\n")

    try:
        # Keep parent process alive quietly
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n[WORKLOAD MANAGER] Shutting down workloads...")
        for p in processes:
            p.terminate()

if __name__ == "__main__":
    start()
