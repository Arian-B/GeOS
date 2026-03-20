# notifications.py
import datetime
import json
import os

from logs.os_logger import log_event

ACTIVE_ALERTS = []
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVENT_LOG = os.path.join(BASE_DIR, "logs", "os_events.log")

def raise_alert(level, message):
    alert = {
        "time": datetime.datetime.now().isoformat(timespec="seconds"),
        "level": level,  # INFO / WARN / CRITICAL
        "message": message
    }
    ACTIVE_ALERTS.append(alert)
    log_event("ALERT", alert)

def get_latest_alert():
    if ACTIVE_ALERTS:
        return ACTIVE_ALERTS[-1]
    alerts = get_active_alerts(limit=1)
    if alerts:
        return alerts[0]
    return None

def clear_alerts():
    ACTIVE_ALERTS.clear()


def get_active_alerts(limit=100):
    alerts = list(reversed(ACTIVE_ALERTS[-limit:]))
    if alerts:
        return alerts

    try:
        with open(EVENT_LOG, "r") as f:
            lines = f.readlines()
    except Exception:
        return []

    collected = []
    for raw_line in reversed(lines):
        try:
            entry = json.loads(raw_line)
        except Exception:
            continue
        if entry.get("event") != "ALERT":
            continue
        data = entry.get("data")
        if isinstance(data, dict):
            collected.append(data)
        if len(collected) >= limit:
            break
    return collected
