# os_logger.py

import time
import json
import os

# Always resolve path relative to project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_FILE = os.path.join(BASE_DIR, "logs", "os_events.log")

def log_event(event_type, data):
    entry = {
        "timestamp": time.time(),
        "event": event_type,
        "data": data
    }

    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(entry) + "\n")
