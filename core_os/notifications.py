# notifications.py
import datetime
from logs.os_logger import log_event

ACTIVE_ALERTS = []

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
    return None

def clear_alerts():
    ACTIVE_ALERTS.clear()

